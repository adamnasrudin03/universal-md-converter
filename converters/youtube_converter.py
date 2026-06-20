from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import urllib.parse

def convert_youtube(url):
    """
    Ekstrak transkrip dari YouTube video menggunakan youtube-transcript-api.
    Prioritas bahasa: Indonesia ('id'), lalu English ('en').
    """
    try:
        # Extract video ID from URL
        parsed_url = urllib.parse.urlparse(url)
        video_id = None
        
        if "youtu.be" in parsed_url.netloc:
            video_id = parsed_url.path.strip('/')
        elif "youtube.com" in parsed_url.netloc:
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if "v" in query_params:
                video_id = query_params["v"][0]
                
        if not video_id:
            return "Error extracting YouTube: Invalid URL format, could not find video ID."

        # Fetch transcript, prioritizing Indonesian, then English
        transcript_list = YouTubeTranscriptApi().list(video_id)
        
        try:
            transcript_obj = transcript_list.find_transcript(['id', 'en'])
        except Exception:
            # If id or en not found, fallback to the first available transcript
            available = [t.language_code for t in transcript_list]
            if not available:
                return "Error extracting YouTube: No transcripts available for this video."
            transcript_obj = transcript_list.find_transcript(available)
            
        transcript = transcript_obj.fetch()
        
        # Format transcript to plain text
        formatter = TextFormatter()
        text_content = formatter.format_transcript(transcript)
        
        if not text_content.strip():
            return "Error extracting YouTube: Transcript is empty."
            
        return text_content
        
    except Exception as e:
        return f"Error extracting YouTube: {str(e)}"
