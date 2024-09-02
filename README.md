Im working on an API thats helps services which are crossposting to youtube, by returning all the metadata that those services are (usually) lacking (e.g. chapters+sponsorblock, metrics like views, likes+returnYTdislike, subtitles and more).
Initially i made it for the pietsmiet.de source because all videos on there have a youtube equivalent that i can use but it should be usable by other crossposting sites like odysee, etc aslong as you have a way to get the equivalent youtube video id. It is still a work in progress and bound to change and improve, and sadly due to the youtube api proxy being painfully slow it still works a while for a uncached (10 min cache) request to go through, but its already quite a bit faster than requesting all these APIs one by one from a home connection because its hosted in a datacenter and does the requests asynchronously.

- https://ytapi.minopia.de/?videoId=79644
- https://ytapi2.minopia.de/?videoId=dSThjhMV7vo
- https://ytapi.minopia.de/transcript?videoId=dSThjhMV7vo&lang=de&format=srt
- https://ytapi2.minopia.de/transcript?videoId=dSThjhMV7vo&format=vtt

https://github.com/Bluscream/youtube-api-wrapper
