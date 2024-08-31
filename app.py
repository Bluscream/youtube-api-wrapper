from decimal import ExtendedContext
import time, json, requests, threading, logging, re
from typing import Any, Optional
from flask import Flask, request, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed
# from subtitles import YouTubeTranscriptDownloader
from youtube_transcript_api import YouTubeTranscriptApi, Transcript
from youtube_transcript_api.formatters import TextFormatter, JSONFormatter, WebVTTFormatter, SRTFormatter, Formatter
from youtube_transcript_api._errors import NoTranscriptFound

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# transcript = YouTubeTranscriptDownloader()

PSDE_API_URL = "https://pietsmiet.zaanposni.com/api/video/{ytid}"
# Hardcoded list of API endpoints
API_ENDPOINTS = {
    "youtube-data": "https://yt.lemnoslife.com/noKey/videos?part=contentDetails,id,player,recordingDetails,snippet,statistics,status,topicDetails&id={ytid}",
    "youtube-dislike": "https://returnyoutubedislikeapi.com/votes?videoId={ytid}",
    "youtube-sponsorblock": "https://sponsor.ajay.app/api/skipSegments?videoID={ytid}",
    "youtube-dearrow": "https://sponsor.ajay.app/api/branding?videoID={ytid}",
    # "youtube-subtitles": "http://127.0.0.1:5001/?format=raw&videoID={ytid}"
    # "youtube-operational": "https://yt.lemnoslife.com/videos?id={ytid}&part=isPaidPromotion,isMemberOnly,isOriginal,isRestricted,isPremium,explicitLyrics,status,chapters",
    "youtube-operational": "https://yt.lemnoslife.com/videos?id={ytid}&part=chapters",
}

class AppCache:
    data: dict[str,object] = {}

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
        if self.exception: raise self.exception # type: ignore
        return self.result

tasks = BackgroundTaskManager()

@staticmethod
def is_youtube_video_id(video_id: str):
    return video_id and bool(re.match(r'^[a-zA-Z0-9_-]{11}$', video_id, re.IGNORECASE))

@staticmethod
def is_pietsmiet_video_id(video_id: str):
    return video_id and video_id.isdigit()

def fetch_data(url: str, yt_video_id: str) -> dict[str, Any] | None:
    try:
        # String format the videoId into the API URL
        url = url.format(ytid=yt_video_id)
        app.logger.info(f"Fetching {url}", extra={'flush': True})
        start_time = time.time()
        response = requests.get(url)
        response.raise_for_status()
        app.logger.info(f"Got {url} in {time.time() - start_time} seconds", extra={'flush': True})
        return response.json()
    except Exception as e:
        app.logger.error(f"Error fetching {url}: {str(e)}", extra={'flush': True})
        return None

def get_transcripts(yt_video_id: str, langs: list[str]):
    ret = {}
    start_time = time.time()
    print("Got", len(ret),"transcripts in",time.time() - start_time,"seconds")
    return ret

cache = AppCache()
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
            res: dict[str, Any] | None = fetch_data(PSDE_API_URL, yt_video_id)
            if not res:
                app.logger.error(f"pietsmiet.de VideoId \"{yt_video_id}\" can not resolve to youtube video!")
                return jsonify({"error": "cannot resolve 'videoId'"}), 400
            yt_video_id = res["secondaryHref"].split('/')[-1]
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

    transcripts_task = tasks.start(get_transcripts, "get_transcripts")

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

    try: combined_response["youtube-transcript"] = tasks.wait()
    except Exception as ex:
        app.logger.exception(ex)
        app.logger.error(f"Failed to get transcript for video {yt_video_id}: {ex}")
    # custom_thread.join()

    # Calculate the total execution time
    combined_response["time"] = time.time() - start_time

    # Combine the responses
    combined_response = {k: v for k, v in combined_response.items() if v}

    # Cache the response
    cache.data[yt_video_id] = combined_response

    return jsonify(combined_response)

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=7077)
