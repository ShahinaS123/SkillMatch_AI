import os
from groq import Groq
from moviepy import VideoFileClip
import tempfile

def transcribe_media(uploaded_file):
    """Extracts audio from video/audio and transcribes it using Groq Whisper."""
    # Create a temporary file to save the uploaded media
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    audio_path = tmp_path
    
    try:
        # If it's a video, extract the audio first
        if uploaded_file.type.startswith("video/"):
            video = VideoFileClip(tmp_path)
            audio_path = tmp_path + ".mp3"
            video.audio.write_audiofile(audio_path, logger=None)
            video.close()

        # Transcribe using Groq Whisper (Free tier)
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_path), audio_file.read()),
                model="whisper-large-v3",
                response_format="text",
            )
            
        return transcription

    except Exception as e:
        return f"Error processing media: {e}"
        
    finally:
        # Clean up temporary files
        if os.path.exists(tmp_path): os.remove(tmp_path)
        if audio_path != tmp_path and os.path.exists(audio_path): os.remove(audio_path)