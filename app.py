from decimal import ExtendedContext
import time, json, requests, threading, logging, re
from typing import Any, Optional
from flask import Flask, request, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from subtitles import app as subtitles

APP_NAME = "youtube-api-wrapper"
APP_BUILD = 1
APP_AUTHOR = "Bluscream"
APP_SOURCE_URL = "https://github.com/Bluscream/youtube-api-wrapper"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PSDE_API_URL = "https://pietsmiet.zaanposni.com/api/video/{ytid}"
# Hardcoded list of API endpoints
API_ENDPOINTS = {
    # "youtube-data": "https://youtube.googleapis.com/youtube/v3/videos?key={yt_api_key}&part=contentDetails,id,player,recordingDetails,snippet,statistics,status,topicDetails&id={ytid}",
    "youtube-data": "https://yt.lemnoslife.com/noKey/videos?part=contentDetails,id,player,recordingDetails,snippet,statistics,status,topicDetails&id={ytid}",
    "youtube-dislike": "https://returnyoutubedislikeapi.com/votes?videoId={ytid}",
    "youtube-sponsorblock": "https://sponsor.ajay.app/api/skipSegments?videoID={ytid}",
    "youtube-dearrow": "https://sponsor.ajay.app/api/branding?videoID={ytid}",
    # "youtube-subtitles": "http://127.0.0.1:5001/?format=raw&videoID={ytid}"
    # "youtube-operational": "https://yt.lemnoslife.com/videos?id={ytid}&part=isPaidPromotion,isMemberOnly,isOriginal,isRestricted,isPremium,explicitLyrics,status,chapters",
    "youtube-operational": "https://yt.lemnoslife.com/videos?id={ytid}&part=chapters",
}
DEFAULT_TASKS = ["youtube-data","youtube-dislike","youtube-sponsorblock","youtube-dearrow","youtube-subtitles","youtube-operational"]
# region Docs
DOCS = {
    "docs": {
        "query": {
            "params": {
                "fresh": {
                    "type": "bool",
                    "default": False,
                    "description": "Invalidates the cache so a fresh result is returned"
                },
                "youtube-subtitles": {
                    "type": "bool",
                    "description": "Returns available subtitles for the given youtube video"
                }
            }
        },
        "default_tasks": DEFAULT_TASKS
    },
    "description": f"{APP_NAME} v{APP_BUILD} is written by {APP_AUTHOR} and open-sourced at {APP_SOURCE_URL}",
    "time": datetime.now()
}
for name, url in API_ENDPOINTS.items():
    DOCS["docs"]["query"]["params"][name] = {
        "type": "bool",
        "default": False,
        "description": f"Returns the response from {url}"
    }
for name in DEFAULT_TASKS:
    DOCS["docs"]["query"]["params"][name]["default"] = True
# endregion Docs

# region Cache
class AppCache:
    data: dict[str,object] = {}

    def __init__(self, max_age=600):  # 10 minutes default
        self.data = {}
        self.max_age = max_age
        self.lock = threading.Lock()
        logger.info(f"Initialized AppCache ({max_age}s)")

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
                time.sleep(self.max_age)  # Run cleanup every minute

        cleanup_thread = threading.Thread(target=cleanup_loop)
        cleanup_thread.daemon = True
        cleanup_thread.start()
cache = AppCache()
cache.run_cleanup_thread()
# endregion Cache

class BackgroundTaskManager:
    def __init__(self):
        self.event = threading.Event()
        self.result = None
        self.exception = None

    def start(self, func, *args, **kwargs):
        def wrapper():
            try:
                self.result = func(*args, **kwargs)
            except Exception as e:
                self.exception = e
            finally:
                self.event.set()

        thread = threading.Thread(target=wrapper)
        thread.start()
        return thread

    def wait(self):
        self.event.wait()
        if self.exception:
            raise self.exception # type: ignore
        return self.result

tasks = BackgroundTaskManager()

@staticmethod
def is_youtube_video_id(video_id: str):
    return video_id and bool(re.match(r"^[a-zA-Z0-9_-]{11}$", video_id, re.IGNORECASE))

@staticmethod
def is_pietsmiet_video_id(video_id: str):
    return video_id and video_id.isdigit()

def fetch_data(url: str, yt_video_id: str) -> dict[str, Any] | None:
    try:
        # String format the videoId into the API URL
        url = url.format(ytid=yt_video_id)
        app.logger.info(f"Fetching {url}", extra={"flush": True})
        start_time = time.time()
        response = requests.get(url)
        response.raise_for_status()
        app.logger.info(f"Got {url} in {time.time() - start_time} seconds", extra={"flush": True})
        return response.json()
    except Exception as e:
        app.logger.error(f"Error fetching {url}: {str(e)}", extra={"flush": True})
        return None

def get_transcripts(yt_video_id: str, langs: list[tuple[str,str]], fetch = False):
    start_time = time.time()
    ret = subtitles.add_video(None, yt_video_id, [], langs, False) # type: ignore
    print("Got", len(ret),"transcripts in",time.time() - start_time,"seconds")
    return ret

# region Flask
app = Flask(__name__)
@app.route("/", methods=["GET"])
def get_main():
    
    start_time = time.time()
    
    # full_info = request.args.get("fullInfo", default=False, type=bool)

    # Get the YouTube video ID from the request body
    yt_video_id = request.args.get("videoId", "", str)
    fresh = request.args.get("fresh", False, bool)

    # Validate the video ID
    if not is_youtube_video_id(yt_video_id):
        if is_pietsmiet_video_id(yt_video_id):
            res: dict[str, Any] | None = fetch_data(PSDE_API_URL, yt_video_id)
            if not res:
                app.logger.error(f"pietsmiet.de VideoId \"{yt_video_id}\" can not resolve to youtube video!")
                return jsonify({"error": "cannot resolve 'videoId'"}), 400
            yt_video_id = res["secondaryHref"].split("/")[-1]
        else:
            app.logger.error(f"VideoId \"{yt_video_id}\" is neither youtube nor pietsmiet")
            return jsonify({"error": "missing or invalid 'videoId' (supports youtube and pietsmiet.de)"}), 400

    combined_response = {} # Create a dictionary to store the fetched data

    # Check cache first
    if not fresh and yt_video_id in cache.data:
        app.logger.info(f"Cached response found for {yt_video_id}")
        combined_response.update(cache.data.get(yt_video_id)) # type: ignore
        combined_response["time"] = time.time() - start_time
        return jsonify(combined_response)

    tasks.start(get_transcripts, yt_video_id, [("English", "en")]) # todo: langs

    # Use ThreadPoolExecutor to make concurrent requests
    with ThreadPoolExecutor(max_workers=len(API_ENDPOINTS)) as executor:
        future_to_url = {executor.submit(fetch_data, url, yt_video_id): (name, url) for (name, url) in API_ENDPOINTS.items()}
        
        for future in as_completed(future_to_url):
            name, url = future_to_url[future]
            try:
                result = future.result()
                if result:
                    combined_response[name] = result
            except Exception as ex:
                app.logger.error(f"Fetching {url} generated an exception: {ex}")

    try: combined_response["youtube-transcripts"] = tasks.wait()
    except Exception as ex:
        app.logger.exception(ex)
        app.logger.error(f"Failed to get transcript for video {yt_video_id}: {ex}")
    # custom_thread.join()

    # Calculate the total execution time
    combined_response["time"] = time.time() - start_time

    # Combine the responses
    # combined_response = {k: v for k, v in combined_response.items() if v}

    # Cache the response
    cache.data[yt_video_id] = combined_response

    return jsonify(combined_response)

@app.route("/caption", methods=["GET"])
@app.route("/subtitle", methods=["GET"])
@app.route('/transcript', methods=['GET'])
def get_transcript():
    
    # try:
    _video_id = request.args.get('videoId')
    _format = request.args.get('format', 'vtt')
    _lang = request.args.get('lang', 'en')
    if _video_id and _format and _lang:
        return subtitles.get_transcript(_video_id, _lang, _format) # type: ignore
    else:
        return jsonify({"error": "Need 'videoId' and 'lang'!"}), 400

@app.route("/about", methods=["GET"])
@app.route("/docs", methods=["GET"])
def get_about():
    return jsonify(DOCS)

#endregion Flask

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=7077)