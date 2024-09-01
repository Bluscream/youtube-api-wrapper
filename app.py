import asyncio, aiohttp, time, re, flask, datetime, typing
from operator import is_
import dataclasses
import subtitles

APP_NAME = "youtube-api-wrapper"
APP_BUILD = 1
APP_AUTHOR = "Bluscream"
APP_SOURCE_URL = "https://github.com/Bluscream/youtube-api-wrapper"
app = flask.Flask(__name__)

async def fetch_json(url: str):
        # try:
            app.logger.info(f"Fetching {url}")
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
            app.logger.info(f"Got {url} in {time.time() - start_time} seconds")
            return data
        # except Exception as e:
        #     app.logger.error(f"Error fetching {url}: {str(e)}")
        #     return None

# region Task
class AppTask:
    run: typing.Callable[..., typing.Awaitable[tuple[typing.Any, dict[str, typing.Any]]]] # = dummy_coroutine # takes flask.Request from flask and returns dict[str, typing.Any]
    name: str = "Unknown Task"
    description: str = "Unknown Task"
    is_default: bool = False
    result: typing.Any
    url: str
    
    def __init__(self, run: typing.Callable, name: str, description: str, is_default: bool, url: str = "") -> None:
        self.run = run;self.name = name; self.description = description; self.is_default = is_default;self.url = url
        app.logger.info(f"Initialized new {self.__class__.name}('{name}','{run}')")
    
# @dataclasses.dataclass
# class CustomTask(Task):
#     run: typing.Callable[[flask.Request], dict[str, typing.Any]|None] = None # takes flask.Request from flask and returns dict[str, typing.Any]
    
# class JSONWebAppTask(AppTask):
#     url: str

#     def __init__(self, url: str, name: str, description: str, is_default: bool) -> None:
#         super().__init__(self.run, name, description, is_default)
#         self.url = url
#         app.logger.info(f"Initialized new {self.__class__.name}('{name}','{url}')")

#     async def run(self, **kwargs) -> tuple[AppTask, dict[str,typing.Any]] | None:
#         self.result = await fetch_json(self.url.format(**kwargs))
#         return self, self.result

# endregion TASK

# region TASKS
async def task_fetch_json(self: AppTask, **kwargs) -> tuple[AppTask, dict[str,typing.Any]] | None:
    self.result = await fetch_json(self.url.format(**kwargs))
    return self, self.result
transcript_downloader = subtitles.YouTubeTranscriptDownloader()
async def task_get_transcripts(self: AppTask, **kwargs) -> tuple[AppTask, dict[str,typing.Any]] | None:
    ret = {}
    start_time = time.time()
    # TODO: Implement actual transcript fetching logic here
    print("Got", len(ret), "transcripts in", time.time() - start_time, "seconds")
    self.result = ret
    return self, ret

TASKS: list[AppTask] = [
    AppTask(name="youtube-data", description="Gets metadata from Youtube Data API v3", is_default=True, url="https://yt.lemnoslife.com/noKey/videos?part=contentDetails,id,player,recordingDetails,snippet,statistics,status,topicDetails&id={ytid}", run=task_fetch_json),
    AppTask(name="youtube-dislike", description="Gets metadata from Youtube Dislike API", is_default=True, url="https://returnyoutubedislikeapi.com/votes?videoId={ytid}", run=task_fetch_json),
    AppTask(name="youtube-sponsorblock", description="Gets metadata from Youtube Sponsorblock API", is_default=True, url="https://sponsor.ajay.app/api/skipSegments?videoID={ytid}", run=task_fetch_json),
    AppTask(name="youtube-dearrow", description="Gets metadata from Youtube DeArrow API", is_default=True, url="https://sponsor.ajay.app/api/branding?videoID={ytid}", run=task_fetch_json),
    AppTask(name="youtube-operational", description="Gets metadata from Youtube Operational API", is_default=True, url="https://yt.lemnoslife.com/videos?id={ytid}&part=chapters", run=task_fetch_json),
    AppTask(name="youtube-subtitles", description="Gets Transcripts (subtitles/captions)", is_default=True, run=task_get_transcripts),
]
# endregion Tasks

PSDE_API_URL = "https://pietsmiet.zaanposni.com/api/video/{ytid}"

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
        }
    },
    "description": f"{APP_NAME} v{APP_BUILD} is written by {APP_AUTHOR} and open-sourced at {APP_SOURCE_URL}",
    "time": datetime.datetime.now()
}
for task in TASKS:
    DOCS["docs"]["query"]["params"][task.name] = {
        "type": "bool",
        "default": task.is_default,
        "description": task.description
    }
    if hasattr(task, "url"):
        DOCS["docs"]["query"]["params"][task.name]["url"] = task.url
        
# endregion Docs

# region Cache
class AppCache:
    data: dict[str, object] = {}

    def __init__(self, max_age=600):  # 10 minutes default
        self.data = {}
        self.max_age = max_age
        self.lock = asyncio.Lock()
        app.logger.info(f"Initialized {self.__class__.__name__}")

    async def get(self, key):
        async with self.lock:
            if key in self.data:
                return self.data.get(key)
            return None

    async def set(self, key, value):
        async with self.lock:
            self.data[key] = value

    async def delete(self, key):
        async with self.lock:
            if key in self.data:
                del self.data[key]

    async def clean_old_entries(self):
        app.logger.warning(f"Purging Cache with {len(self.data)} items!")
        self.data = {}

    async def run_cleanup_thread(self):
        while True:
            await self.clean_old_entries()
            await asyncio.sleep(600)  # Run cleanup every minute

cache = AppCache()
# endregion Cache

async def is_youtube_video_id(video_id: str):
    return video_id and bool(re.match(r"^[a-zA-Z0-9_-]{11}$", video_id, re.IGNORECASE))

async def is_pietsmiet_video_id(video_id: str):
    return video_id and video_id.isdigit()

# region Routes    
@app.route('/', methods=['GET'])
async def route_get_main():
    combined_response = {}
    start_time = time.time()
    yt_video_id = flask.request.args.get('videoId', '', str)
    fresh = flask.request.args.get('fresh', False, bool)

    if not await is_youtube_video_id(yt_video_id):
        if await is_pietsmiet_video_id(yt_video_id):
            res = await fetch_json(PSDE_API_URL.format(ytid=yt_video_id))
            if not res:
                app.logger.error(f"pietsmiet.de VideoId \"{yt_video_id}\" can not resolve to youtube video!")
                return flask.jsonify({"error": "cannot resolve 'videoId'"}), 400
            yt_video_id = res["secondaryHref"].split('/')[-1]
        else:
            app.logger.error(f"VideoId \"{yt_video_id}\" is neither youtube nor pietsmiet")
            return flask.jsonify({"error": "missing or invalid 'videoId' (supports youtube and pietsmiet.de)"}), 400

    # tasks = TASKS.copy()
    if not fresh and yt_video_id in cache.data:
        app.logger.info(f"Cached response found for {yt_video_id}")
        return flask.jsonify(cache.data[yt_video_id])

    # async with aiohttp.ClientSession():
    tasks_list = [
        asyncio.create_task(task.run(self=task, ytid=yt_video_id)) for task in TASKS # typing: ignore
    ]
    done, _ = await asyncio.wait(tasks_list, return_when=asyncio.ALL_COMPLETED)
    _task: asyncio.Task[tuple[AppTask, dict[str, typing.Any]]]
    for _task in done:
        if _task.exception():
            app.logger.error(f"Task {_task} raised an exception: {_task.exception()}")
        else:
            task, result = _task.result()
            if result:
                combined_response[task.name] = result
    
    combined_response["time"] = time.time() - start_time

    cache.data[yt_video_id] = combined_response

    return flask.jsonify(combined_response)

@app.route('/about', methods=['GET'])
@app.route('/docs', methods=['GET'])
async def route_get_about():
    return flask.jsonify(DOCS)
# endregion Routes

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(cache.run_cleanup_thread())
    app.run(host='0.0.0.0', port=7077) # asyncio.run(get_main())
