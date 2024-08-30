import time, json, requests, threading

from flask import Flask, request, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed

# Hardcoded list of API endpoints
API_ENDPOINTS = {
    "youtube-data": "https://yt.lemnoslife.com/noKey/videos?part=statistics&id={ytid}",
    "youtube-dislike": "https://returnyoutubedislikeapi.com/votes?videoId={ytid}",
    "youtube-sponsorblock": "https://sponsor.ajay.app/api/skipSegments?videoID={ytid}",
    "youtube-dearrow": "https://sponsor.ajay.app/api/branding?videoID={ytid}",
    "youtube-subtitles": "http://127.0.0.1:5001/?format=raw&videoId={ytid}"
}

class Cache:
    def __init__(self, max_age=600):  # 10 minutes default
        self.data = {}
        self.max_age = max_age
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            if key in self.data:
                value, timestamp = self.data[key]
                if time.time() - timestamp < self.max_age:
                    return value
            return None

    def set(self, key, value):
        with self.lock:
            self.data[key] = (value, time.time())

    def delete(self, key):
        with self.lock:
            if key in self.data:
                del self.data[key]

    def clean_old_entries(self):
        now = time.time()
        keys_to_delete = []
        for key, (value, timestamp) in self.data.items():
            if now - timestamp >= self.max_age:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del self.data[key]

    def run_cleanup_thread(self):
        def cleanup_loop():
            while True:
                self.clean_old_entries()
                time.sleep(60)  # Run cleanup every minute

        cleanup_thread = threading.Thread(target=cleanup_loop)
        cleanup_thread.daemon = True
        cleanup_thread.start()

def is_youtube_video_id(id: str): return id # and len(id) == 11 and id.startswith(('3', '9'))

def fetch_data(url, yt_video_id: str):
    try:
        # String format the videoId into the API URL
        url = url.format(ytid=yt_video_id)
        print("Fetching", url, flush=True)
        response = requests.get(url)
        response.raise_for_status()
        print("Got", url, flush=True)
        return response.json()
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        return None



cache = Cache()
cache.run_cleanup_thread()

app = Flask(__name__)
@app.route('/', methods=['GET'])
def combine_responses():
    start_time = time.time()

    # Get the YouTube video ID from the request body
    yt_video_id = request.args.get('videoId')

    # Validate the video ID
    if not is_youtube_video_id(yt_video_id): return jsonify({"error": "missing or invalid 'videoId'"}), 400

    combined_response = {} # Create a dictionary to store the fetched data

    # Check cache first
    if yt_video_id in cache.data:
        print(f"Cached response found for {yt_video_id}", flush=True)
        combined_response["time"] = time.time() - start_time
        combined_response.update(cache.data.get(yt_video_id))
        return jsonify(combined_response)

    # Use ThreadPoolExecutor to make concurrent requests
    with ThreadPoolExecutor(max_workers=len(API_ENDPOINTS)) as executor:
        future_to_url = {executor.submit(fetch_data, url, yt_video_id): (name, url) for (name, url) in API_ENDPOINTS.items()}
        
        for future in as_completed(future_to_url):
            endpoint = future_to_url[future]
            try:
                result = future.result()
                if result:
                    combined_response[endpoint] = result
            except Exception as exc:
                print(f"Fetching {endpoint} generated an exception: {exc}", flush=True)

    # Calculate the total execution time
    combined_response["time"] = time.time() - start_time

    # Combine the responses
    combined_response = {k: v for k, v in combined_response.items() if v}

    # Cache the response
    cache.data[yt_video_id] = combined_response

    return jsonify(combined_response)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
