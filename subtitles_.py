# pip install requests bbpb
import base64, json
import requests, blackboxprotobuf
from typing import Dict, Any

class YouTubeTranscriptDownloader:
    """Class for downloading youtube transcripts
    """
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
        """Encode a given message dict with a given typedef dict to base64-encoded protobuf

        Args:
            message (Dict[str, Any]): Message dictionary to encode
            typedef (Dict[str, Dict[str, str]]): Clone of the message dictionary, but instead of values it has types as strings

        Returns:
            str: base64 encoded protobuf message
        """
        data = blackboxprotobuf.encode_message(message, typedef)
        return base64.b64encode(data).decode('ascii')

    def get(self, videoId: str, lang = "en", automatic = True):
        """Gets a transcript in youtube's proprietary json form for a video by it's ID

        Args:
            videoId (str): Youtube Video ID
            lang (str, optional): 2 Letter language code. Defaults to "en".
            automatic (bool, optional): Wether to get the automatically generated captions. Defaults to True

        Returns:
            _type_: Transcript as json dict
        """
        lang_dict = { '1': 'asr', '2': lang} if automatic else { '2': lang}
        lang_type = { '1': { 'type': 'string' },'2': { 'type': 'string' } } if automatic else { '2': { 'type': 'string' } }
        message = {
            '1': videoId,
            '2': YouTubeTranscriptDownloader.encode_protobuf(lang_dict, lang_type),
        }
        msg_type = { '1': { 'type': 'string' }, '2': { 'type': 'string' } }
        params = YouTubeTranscriptDownloader.encode_protobuf(message, msg_type)

        data = {
            'context': self.context,
            'params': params
        }
        print("Getting transcript for video",videoId,"in language",lang,"(automatic)" if automatic else "")
        data = requests.post(self.url, headers = self.headers, json = data).json()
        return data

if __name__ == "__main__": # Example usage
    from sys import argv
    downloader = YouTubeTranscriptDownloader()
    videoId = argv[-1] if len(argv) > 1 else input("Video ID:")
    lang = input("Language (2 letter lowercase):") or "en"
    automatic = True if input("Automaticly generated? (empty=No)") else False
    result = downloader.get(videoId, lang, automatic)
    
    if result:
        txt = json.dumps(result, indent=4)
        print(txt)
        with open("transcript.json", 'w') as f:
            # Writing data to a file
            f.write(txt)
