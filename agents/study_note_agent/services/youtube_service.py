from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)
from youtube_transcript_api.formatters import TextFormatter


def get_transcript(video_url: str, language: str = "en") -> str:
    """
    Get transcript from a YouTube video URL or ID.
    """
    # Extract video ID from URL if full URL is passed
    if "watch?v=" in video_url:
        video_id = video_url.split("watch?v=")[-1].split("&")[0]
    elif "youtu.be/" in video_url:
        video_id = video_url.split("youtu.be/")[-1].split("?")[0]
    else:
        video_id = video_url  # assume it's already an ID

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
        formatter = TextFormatter()
        return formatter.format_transcript(transcript)

    except TranscriptsDisabled:
        raise Exception("Transcripts are disabled for this video.")

    except NoTranscriptFound:
        # Try fetching any available transcript
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        available = [t.language_code for t in transcript_list]
        raise Exception(f"No '{language}' transcript found. Available: {available}")

    except Exception as e:
        raise Exception(f"Failed to fetch transcript: {e}")


if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    transcript = get_transcript(url)
    print(transcript)

    # Optionally save to file
    with open("transcript.txt", "w") as f:
        f.write(transcript)
    print("Saved to transcript.txt")
