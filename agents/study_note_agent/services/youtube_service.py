from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)
from youtube_transcript_api.formatters import TextFormatter


def extract_video_id(video_url: str) -> str:
    """Extract a YouTube video ID from a URL, or return the input as a bare ID."""
    parsed = urlparse(video_url)
    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        return parsed.path.lstrip("/")
    if (
        parsed.hostname in ("youtube.com", "www.youtube.com")
        and parsed.path == "/watch"
    ):
        query = parse_qs(parsed.query)
        return query.get("v", [video_url])[0] or video_url
    return video_url


def get_transcript(video_url: str, language: str = "en") -> str:
    """
    Get transcript from a YouTube video URL or ID.
    """
    video_id = extract_video_id(video_url)

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
