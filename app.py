import time, json, requests, threading
from flask import Flask, request, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ... (rest of the imports remain unchanged)

# Hardcoded list of API endpoints
API_ENDPOINTS = {
    "youtube-data": "https://yt.lemnoslife.com/noKey/videos?part=contentDetails,id,player,recordingDetails,snippet,statistics,status,topicDetails&id={ytid}",
    "youtube-dislike": "https://returnyoutubedislikeapi.com/votes?videoId={ytid}",
    "youtube-sponsorblock": "https://sponsor.ajay.app/api/skipSegments?videoID={ytid}",
    "youtube-dearrow": "https://sponsor.ajay.app/api/branding?videoID={ytid}",
    # "youtube-subtitles": "http://127.0.0.1:5001/?format=raw&videoID={ytid}"
    "youtube-operational-id": "https://yt.lemnoslife.com/videos?id={ytid}&part=id",
    "youtube-operational-status": "https://yt.lemnoslife.com/videos?id={ytid}&part=status",
    "youtube-operational-contentDetails": "https://yt.lemnoslife.com/videos?id={ytid}&part=contentDetails",
    "youtube-operational-music": "https://yt.lemnoslife.com/videos?id={ytid}&part=music",
    "youtube-operational-short": "https://yt.lemnoslife.com/videos?id={ytid}&part=short",
    "youtube-operational-musics": "https://yt.lemnoslife.com/videos?id={ytid}&part=musics",
    "youtube-operational-isPaidPromotion": "https://yt.lemnoslife.com/videos?id={ytid}&part=isPaidPromotion",
    "youtube-operational-isPremium": "https://yt.lemnoslife.com/videos?id={ytid}&part=isPremium",
    "youtube-operational-isMemberOnly": "https://yt.lemnoslife.com/videos?id={ytid}&part=isMemberOnly",
    "youtube-operational-mostReplayed": "https://yt.lemnoslife.com/videos?id={ytid}&part=mostReplayed",
    "youtube-operational-qualities": "https://yt.lemnoslife.com/videos?id={ytid}&part=qualities",
    "youtube-operational-chapters": "https://yt.lemnoslife.com/videos?id={ytid}&part=chapters",
    "youtube-operational-isOriginal": "https://yt.lemnoslife.com/videos?id={ytid}&part=isOriginal",
    "youtube-operational-isRestricted": "https://yt.lemnoslife.com/videos?id={ytid}&part=isRestricted",
    "youtube-operational-snippet": "https://yt.lemnoslife.com/videos?id={ytid}&part=snippet",
    "youtube-operational-clip": "https://yt.lemnoslife.com/videos?id={ytid}&part=clip",
    "youtube-operational-activity": "https://yt.lemnoslife.com/videos?id={ytid}&part=activity",
    "youtube-operational-explicitLyrics": "https://yt.lemnoslife.com/videos?id={ytid}&part=explicitLyrics",
    "youtube-operational-statistics": "https://yt.lemnoslife.com/videos?id={ytid}&part=statistics",
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
        self.data = {}

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
        app.logger.info(f"Fetching {url}", extra={'flush': True})
        response = requests.get(url)
        response.raise_for_status()
        app.logger.info(f"Got {url}", extra={'flush': True})
        return response.json()
    except Exception as e:
        app.logger.error(f"Error fetching {url}: {str(e)}", extra={'flush': True})
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
        app.logger.info(f"Cached response found for {yt_video_id}", flush=True)
        combined_response["time"] = time.time() - start_time
        combined_response.update(cache.data.get(yt_video_id))
        return jsonify(combined_response)

    # Use ThreadPoolExecutor to make concurrent requests
    with ThreadPoolExecutor(max_workers=len(API_ENDPOINTS)) as executor:
        future_to_url = {executor.submit(fetch_data, url, yt_video_id): (name, url) for (name, url) in API_ENDPOINTS.items()}
        
        for future in as_completed(future_to_url):
            name, url = future_to_url[future]
            try:
                result = future.result()
                if result:
                    combined_response[name] = result
            except Exception as exc:
                app.logger.error(f"Fetching {url} generated an exception: {exc}", flush=True)

    # Calculate the total execution time
    combined_response["time"] = time.time() - start_time

    # Combine the responses
    combined_response = {k: v for k, v in combined_response.items() if v}

    # Cache the response
    cache.data[yt_video_id] = combined_response

    return jsonify(combined_response)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
