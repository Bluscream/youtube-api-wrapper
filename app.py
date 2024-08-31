from decimal import ExtendedContext
import time, json, requests, threading, logging, re
from typing import Any, Optional
from flask import Flask, request, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed
from subtitles import YouTubeTranscriptDownloader

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

transcript = YouTubeTranscriptDownloader()

PSDE_API_URL = "https://pietsmiet.zaanposni.com/api/video/{ytid}"

TASKS = {
    "youtube-data": (getJson, "https://yt.lemnoslife.com/noKey/videos?part=contentDetails,id,player,recordingDetails,snippet,statistics,status,topicDetails&id={ytid}"),
    "youtube-dislike": (getJson, "https://returnyoutubedislikeapi.com/votes?videoId={ytid}"),
    "youtube-sponsorblock": (getJson, "https://sponsor.ajay.app/api/skipSegments?videoID={ytid}"),
    "youtube-dearrow": (getJson, "https://sponsor.ajay.app/api/branding?videoID={ytid}"),
    "youtube-operational": (getJson, "https://yt.lemnoslife.com/videos?id={ytid}&part=chapters"),
}

class Cache:
    data: dict[str, object] = {}
    def __init__(self, max_age=600):  # 10 minutes default
        self.data = {}
        self.max_age = max_age
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            if key in self.data:
                return self.data.get(key)
            return None

    def set(self, key, value):
        with self.lock:
            self.data[key] = value

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

class CustomOperationThread(threading.Thread):
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self.exception = None

    def run(self):
        try:
            self.result = self.func(*self.args, **self.kwargs)
        except Exception as e:
            self.exception = e

    def join(self, timeout=None):
        super().join(timeout)
        if self.exception:
            raise self.exception

@staticmethod
def is_youtube_video_id(id: str):
    return id and bool(re.match(r'^[a-zA-Z0-9_-]{11}$', id, re.IGNORECASE))

@staticmethod
def is_pietsmiet_video_id(id: str):
    return id and id.isdigit()

def getJson(url_template: str, **kwargs: dict[str, Any]) -> dict[str, Any] | None:
    try:
        url = url_template.format(**kwargs)
        app.logger.info(f"Fetching {url}", extra={'flush': True})
        start_time = time.time()
        response = requests.get(url)
        response.raise_for_status()
        app.logger.info(f"Got {url} in {time.time() - start_time} seconds", extra={'flush': True})
        return response.json()
    except Exception as e:
        app.logger.error(f"Error fetching {url_template}: {str(e)}", extra={'flush': True})
        return None

cache = Cache()
cache.run_cleanup_thread()

app = Flask(__name__)
@app.route('/', methods=['GET'])
def combine_responses():
    start_time = time.time()

    # Get the YouTube video ID from the request body
    yt_video_id = request.args.get('videoId', "")
    fresh = request.args.get('fresh', False)

    # Validate the video ID
    if not is_youtube_video_id(yt_video_id):
        if is_pietsmiet_video_id(yt_video_id):
            res: dict[str, Any] = fetch_data(PSDE_API_URL, yt_video_id)
            yt_video_id = res["secondaryHref"].split('/')[-1]
        else:
            app.logger.error(f"VideoId \"{yt_video_id}\" is neither youtube nor pietsmiet")
            return jsonify({"error": "missing or invalid 'videoId' (supports youtube and pietsmiet.de)"}), 400

    combined_response = {} # Create a dictionary to store the fetched data

    # Check cache first
    if not fresh and yt_video_id in cache.data:
        app.logger.info(f"Cached response found for {yt_video_id}")
        combined_response.update(cache.data.get(yt_video_id))
        combined_response["time"] = time.time() - start_time
        return jsonify(combined_response)

    # Use ThreadPoolExecutor to make concurrent requests
    with ThreadPoolExecutor(max_workers=len(TASKS)) as executor:
        future_to_task = {executor.submit(url_template=getJson, *task): task for task in TASKS.values()}
        
        for future in as_completed(future_to_task):
            name, url_template = next(iter(future_to_task[future]))
            try:
                result = future.result()
                if result:
                    combined_response[name] = result
            except Exception as ex:
                app.logger.error(f"Fetching {url_template} generated an exception: {ex}")

    try: 
        combined_response["youtube-transcript"] = transcript.get(yt_video_id)
    except Exception as ex:
        app.logger.exception(ex)
        app.logger.error(f"Failed to get transcript for video {yt_video_id}: {ex}")

    # Calculate the total execution time
    combined_response["time"] = time.time() - start_time

    # Combine the responses
    combined_response = {k: v for k, v in combined_response.items() if v}

    # Cache the response
    cache.data[yt_video_id] = combined_response

    return jsonify(combined_response)

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=7077)
