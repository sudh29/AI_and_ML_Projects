# API_KEY = 'AIzaSyBWBa0nddy4Z5iHk6XBen_eXRrVjAJl8kA'
# from googleapiclient.discovery import build

import re
from youtube_transcript_api import YouTubeTranscriptApi

# Constants
VIDEO_URL = "https://www.youtube.com/watch?v=5mMpM8zK4pY"
LANGUAGE = "en"


def get_video_id(video_url):
    # Regular expression pattern to match YouTube video IDs
    pattern = r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)"
    match = re.match(pattern, video_url)
    if match:
        return match.group(1)  # Extract the video ID
    else:
        return None  # Return None if no match is found


def get_video_comments(video_id):
    # Get the transcript for the video
    transcript_text = ""
    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[LANGUAGE])
    for caption in transcript:
        # print(caption['text'])
        transcript_text += str(caption["text"]) + " "
    return transcript_text


if __name__ == "__main__":
    video_id = get_video_id(VIDEO_URL)
    print("Video ID:", video_id)

    if video_id:
        transcript_text = get_video_comments(video_id)
        # print(transcript_text)
    else:
        print("Failed to extract video ID from the provided URL.")
