import requests
import blackboxprotobuf
import base64
import json

class TranscriptDownloader:
    VIDEO_ID = 'ohtTai7AiN8ll '
    
    def __init__(self):
        self.message = {
            '1': 'asr',
            '2': 'en',
        }
        self.typedef = {
            '1': {'type': 'string'},
            '2': {'type': 'string'}
        }

    def get(self, video_id):
        self.VIDEO_ID = video_id
        
        # Generate the initial message and typedef
        two = self._generate_base64_protobuf(self.message, self.typedef)
        
        # Update the message with the VIDEO_ID
        self.message = {
            '1': self.VIDEO_ID,
            '2': two,
        }
        
        # Generate the final params
        params = self._generate_base64_protobuf(self.message, self.typedef)
        
        url = 'https://www.youtube.com/youtubei/v1/get_transcript'
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            'context': {
                'client': {
                    'clientName': 'WEB',
                    'clientVersion': '2.20240313'
                }
            },
            'params': params
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"An error occurred: {e}")
            return None

    @staticmethod
    def _generate_base64_protobuf(message, typedef):
        data = blackboxprotobuf.encode_message(message, typedef)
        return base64.b64encode(data).decode('ascii')

# Usage example
transcript_downloader = TranscriptDownloader()
result = transcript_downloader.get('ohtTai7AiN8ll ')
if result:
    print(json.dumps(result, indent=4))
else:
    print("Failed to retrieve the transcript.")
