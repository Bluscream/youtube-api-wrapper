from flask import Flask, request, jsonify
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time

app = Flask(__name__)

# Hardcoded list of API endpoints
API_ENDPOINTS = {
    "youtube-data": "https://yt-dl.org/api/v2.json",
    "youtube-dislike": "https://dislike.yt/api/v1/video",
    "youtube-sponsorblock": "https://sponsor.ajay.app/api/skipSegments",
    "youtube-dearrow": "https://dearrows.com/api/v1/video"
}

def fetch_data(endpoint, yt_video_id):
    try:
        if endpoint == "youtube-data":
            url = f"{API_ENDPOINTS[endpoint]}?id={yt_video_id}"
        elif endpoint in ["youtube-dislike", "youtube-sponsorblock"]:
            url = f"{API_ENDPOINTS[endpoint]}?videoId={yt_video_id}"
        else:
            url = f"{API_ENDPOINTS[endpoint]}?videoID={yt_video_id}"

        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {endpoint}: {str(e)}")
        return None

@app.route('/combine', methods=['POST'])
def combine_responses():
    start_time = time.time()

    # Get the YouTube video ID from the request body
    data = request.json
    yt_video_id = data.get('videoId')

    if not yt_video_id:
        return jsonify({"error": "Missing 'videoId' in the request"}), 400

    # Create a dictionary to store the fetched data
    combined_response = {}

    # Use ThreadPoolExecutor to make concurrent requests
    with ThreadPoolExecutor(max_workers=len(API_ENDPOINTS)) as executor:
        future_to_url = {executor.submit(fetch_data, endpoint, yt_video_id): endpoint for endpoint in API_ENDPOINTS}
        
        for future in as_completed(future_to_url):
            endpoint = future_to_url[future]
            try:
                result = future.result()
                if result:
                    combined_response[endpoint] = result
            except Exception as exc:
                print(f"Fetching {endpoint} generated an exception: {exc}")

    # Calculate the total execution time
    end_time = time.time()
    total_time = end_time - start_time

    # Check if any of the requests timed out
    if total_time > 5:
        return jsonify({"error": "Request timed out after 5 seconds"}), 408

    # Combine the responses
    combined_response = {k: v for k, v in combined_response.items() if v}

    return jsonify(combined_response)

if __name__ == '__main__':
    app.run(debug=True)
