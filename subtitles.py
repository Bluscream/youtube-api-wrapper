# pip install requests blackboxprotobuf bbpb
import requests
import blackboxprotobuf
import base64
import json
from typing import Dict, Any

class YouTubeTranscriptDownloader:
    url = 'https://www.youtube.com/youtubei/v1/get_transcript'
    headers = {
        'Content-Type': 'application/json'
    }
    context = {
        'client': {
            'clientName': 'WEB',
            'clientVersion': '2.20240313'
        }
    }

    @staticmethod
    def encode_protobuf(message: Dict[str, Any], typedef: Dict[str, Dict[str, str]]) -> str:
        data = blackboxprotobuf.encode_message(message, typedef)
        return base64.b64encode(data).decode('ascii')

    def get(self, videoId: str, lang = "en"):
        typedef = {
                '1': {
                    'type': 'string'
                },
                '2': {
                    'type': 'string'
                },
        }
        message = {
            '1': videoId,
            '2': YouTubeTranscriptDownloader.encode_protobuf({
                '1': 'asr',
                '2': lang,
            }, typedef),
        }
        params = YouTubeTranscriptDownloader.encode_protobuf(message, typedef)

        data = {
            'context': self.context,
            'params': params
        }

        data = requests.post(self.url, headers = self.headers, json = data).json()
        return data

if __name__ == "__main__":
    downloader = YouTubeTranscriptDownloader()
    result = downloader.get('ohtTai7AiN8')
    
    if result:
        print(json.dumps(result, indent=4))
