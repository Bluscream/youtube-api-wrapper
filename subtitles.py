from decimal import ExtendedContext
import time, json, requests, threading, logging, re
from typing import Any, Optional
from flask import Flask, request, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed
# from subtitles import YouTubeTranscriptDownloader
from youtube_transcript_api import YouTubeTranscriptApi, Transcript
from youtube_transcript_api.formatters import TextFormatter, JSONFormatter, WebVTTFormatter, SRTFormatter, Formatter
from youtube_transcript_api._errors import NoTranscriptFound # typing: ignore

class YouTubeTranscriptDownloader:
    def __init__(self) -> None:
        pass