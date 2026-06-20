import os
import gc

# moviepy 1.x uses moviepy.editor; moviepy >= 2.0 uses moviepy directly.
# requirements.txt pins 1.0.3, so try 1.x first.
try:
    from moviepy.editor import VideoFileClip
except (ImportError, AttributeError): # pragma: no cover
    from moviepy import VideoFileClip

def extract_audio_from_video(video_path, audio_path):
    video = None
    try:
        video = VideoFileClip(video_path)
        if video.audio is None:
            print("No audio track found in video.")
            return False
        video.audio.write_audiofile(audio_path, verbose=False, logger=None)
        return True
    except Exception as e:
        print(f"Error extracting audio: {e}")
        return False
    finally:
        if video is not None:
            try:
                video.close()
            except Exception:
                pass

def convert_media(file_path, is_video=False):
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found."
        
    target_audio_path = file_path
    try:
        if is_video:
            target_audio_path = file_path + ".temp.wav"
            success = extract_audio_from_video(file_path, target_audio_path)
            if not success:
                return "Failed to extract audio from video."

        # Import locally to avoid slow startup for scripts not using media
        from faster_whisper import WhisperModel
        
        # Load faster-whisper model (int8 compute type is very memory efficient)
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(target_audio_path, beam_size=5)
        
        text = " ".join([segment.text for segment in segments]).strip()
        if not text:
            return ""
        return text
    except Exception as e:
        return f"Error transcribing media: {str(e)}"
    finally:
        # Explicit garbage collection to prevent memory leaks from Whisper
        try:
            del model
        except UnboundLocalError:
            pass
        gc.collect()
        
        # Cleanup temp audio if we created one
        if is_video and target_audio_path != file_path and os.path.exists(target_audio_path):
            try:
                os.remove(target_audio_path)
            except Exception:
                pass
