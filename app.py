import time, json, requests

from flask import Flask, request, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread




# Hardcoded list of API endpoints
API_ENDPOINTS = {
    "youtube-data": "https://yt.lemnoslife.com/noKey/videos?part=statistics&id={ytid}",
    "youtube-dislike": "https://returnyoutubedislikeapi.com/votes?videoId={ytid}",
    "youtube-sponsorblock": "https://sponsor.ajay.app/api/skipSegments?videoID={ytid}",
    "youtube-dearrow": "https://sponsor.ajay.app/api/branding?videoID={ytid}"
}

class Cache(Thread):
    data = {} # Simple cache dictionary
    def __init__(self, interval=300):  # 5 minutes interval
        super().__init__()
        self.interval = interval
        self.daemon = True  # Set as daemon so it exits when main program finishes
        self.run()

    def run(self):
        while True:
            time.sleep(self.interval)
            self.data = {}
            print("Cache cleaned")

def is_youtube_video_id(id: str): return id and len(id) == 11 and id.startswith(('3', '9'))

def fetch_data(endpoint, yt_video_id: str):
    try:
        # String format the videoId into the API URL
        url = API_ENDPOINTS[endpoint].format(ytid=yt_video_id)
        
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {endpoint}: {str(e)}")
        return None

cache = Cache(interval=300)

app = Flask(__name__)
@app.route('/', methods=['GET'])
def combine_responses():
    start_time = time.time()

    # Get the YouTube video ID from the request body
    yt_video_id = request.args.get('videoId')

    # Validate the video ID
    # if not is_youtube_video_id(yt_video_id): return jsonify({"error": "missing or invalid 'videoId'"}), 400

    combined_response = {} # Create a dictionary to store the fetched data

    # Check cache first
    if yt_video_id in cache.data:
        print(f"Cached response found for {yt_video_id}")
        combined_response["time"] = time.time() - start_time
        combined_response.update(cache.data.get(yt_video_id))
        return jsonify(combined_response)

    # Use ThreadPoolExecutor to make concurrent requests
    with ThreadPoolExecutor(max_workers=len(API_ENDPOINTS)) as executor:
        future_to_url = {executor.submit(fetch_data, endpoint, yt_video_id): endpoint for endpoint in API_ENDPOINTS}
        
        for future in as_completed(future_to_url):
            endpoint = future_to_url[future]
            try:
                result = future.result()
                if result:
                    combined_response[endpoint] = result
            except Exception as exc:
                print(f"Fetching {endpoint} generated an exception: {exc}")

    # Calculate the total execution time
    combined_response["time"] = time.time() - start_time

    # Combine the responses
    combined_response = {k: v for k, v in combined_response.items() if v}

    # Cache the response
    cache.data[yt_video_id] = combined_response

    return jsonify(combined_response)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
