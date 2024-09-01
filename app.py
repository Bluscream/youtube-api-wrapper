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

TASKS = {
    "youtube-data": (getJson, "https://yt.lemnoslife.com/noKey/videos?part=contentDetails,id,player,recordingDetails,snippet,statistics,status,topicDetails&id={ytid}"),
    "youtube-dislike": (getJson, "https://returnyoutubedislikeapi.com/votes?videoId={ytid}"),
    "youtube-sponsorblock": (getJson, "https://sponsor.ajay.app/api/skipSegments?videoID={ytid}"),
    "youtube-dearrow": (getJson, "https://sponsor.ajay.app/api/branding?videoID={ytid}"),
    # "youtube-subtitles": (getJson, "http://127.0.0.1:5001/?format=raw&videoID={ytid}"),
    # "youtube-operational": (getJson, "https://yt.lemnoslife.com/videos?id={ytid}&part=isPaidPromotion,isMemberOnly,isOriginal,isRestricted,isPremium,explicitLyrics,status,chapters"),
    "youtube-operational": (getJson, "https://yt.lemnoslife.com/videos?id={ytid}&part=chapters"),
}