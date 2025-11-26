from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uuid
import asyncio
from typing import Dict
# import google.cloud.speech as speech
# from google.cloud import storage
import requests
import subprocess
import tempfile
import shutil
import shlex
import assemblyai as aai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure AssemblyAI API key from environment variable
assemblyai_api_key = os.getenv("ASSEMBLYAI_API_KEY")
if not assemblyai_api_key:
    raise ValueError("ASSEMBLYAI_API_KEY environment variable is not set")
aai.settings.api_key = assemblyai_api_key

# Configure Google Cloud Storage
# bucket_name = "your_bucket_name"

# Speech-to-text client setup
# speech_client = speech.SpeechClient()

# Store job status in memory (use Redis or database in production)
job_status: Dict[str, dict] = {}

# Endpoint to upload video
@app.post("/upload")
async def upload_video(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    try:
        # Validate file type
        if not file.content_type.startswith('video/'):
            return JSONResponse(
                status_code=400,
                content={"detail": "File must be a video"}
            )
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Save video file temporarily
        video_file_path = f"./temp_{job_id}_{file.filename}"
        with open(video_file_path, "wb") as buffer:
            buffer.write(await file.read())
        
        # Initialize job status
        job_status[job_id] = {
            "status": "processing",
            "transcriptionId": None,
            "error": None
        }
        
        # Process video in background
        background_tasks.add_task(process_video, job_id, video_file_path)
        
        return {"jobId": job_id, "message": "Video upload started"}
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error uploading video: {str(e)}"}
        )

async def process_video(job_id: str, video_file_path: str):
    audio_file_path = None
    try:
        # Extract audio from video
        audio_file_path = video_file_path.replace(os.path.splitext(video_file_path)[1], '.wav')
        
        # Use ffmpeg to extract audio
        extract_audio_from_video(video_file_path, audio_file_path)
        
        # Transcribe audio
        transcription = await asyncio.to_thread(transcribe_audio, audio_file_path)
        
        # Update job status
        job_status[job_id] = {
            "status": "completed",
            "transcriptionId": transcription,
            "error": None
        }
        
    except Exception as e:
        job_status[job_id] = {
            "status": "failed",
            "transcriptionId": None,
            "error": str(e)
        }
    
    finally:
        # Clean up temp files
        if os.path.exists(video_file_path):
            os.remove(video_file_path)
        if audio_file_path and os.path.exists(audio_file_path):
            os.remove(audio_file_path)

def extract_audio_from_video(video_path: str, audio_path: str):
    """
    Extract audio from video using ffmpeg
    Converts to WAV format with proper settings for AssemblyAI
    """
    try:
        # Resolve ffmpeg executable and handle possible extra args in FFMPEG_PATH
        ffmpeg_env = os.getenv("FFMPEG_PATH", "").strip()

        if ffmpeg_env:
            # On Windows users may paste a quoted path or include extra flags.
            # Use shlex.split with posix=False to preserve Windows-style parsing.
            try:
                ffmpeg_cmd = shlex.split(ffmpeg_env, posix=False)
            except Exception:
                # Fallback: use raw string as single command
                ffmpeg_cmd = [ffmpeg_env.strip('"')]

            # If the executable isn't an absolute path, try to locate it
            exe = ffmpeg_cmd[0]
            if not os.path.isabs(exe) and shutil.which(exe):
                ffmpeg_cmd[0] = shutil.which(exe)
        else:
            # Try to find ffmpeg on PATH
            ff = shutil.which('ffmpeg')
            if not ff:
                raise FileNotFoundError('FFmpeg not found in PATH and FFMPEG_PATH not set')
            ffmpeg_cmd = [ff]

        # Use absolute paths to avoid any relative path issues
        video_abs = os.path.abspath(video_path)
        audio_abs = os.path.abspath(audio_path)

        command = (
            ffmpeg_cmd
            + ['-i', video_abs, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', '-y', audio_abs]
        )

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=300  # 5 minute timeout for extraction
        )
        
        if not os.path.exists(audio_path):
            raise Exception("Audio extraction failed - output file not created")
            
    except subprocess.TimeoutExpired:
        raise Exception("Audio extraction timed out - video may be too long")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors='ignore') if e.stderr else ''
        stdout = e.stdout.decode(errors='ignore') if e.stdout else ''
        raise Exception(f"FFmpeg error (exit {e.returncode}): {stderr or stdout}")
    except FileNotFoundError as e:
        raise Exception(
            "FFmpeg not found. Install ffmpeg or set the `FFMPEG_PATH` environment variable to the ffmpeg executable."
        )
    except Exception as e:
        raise Exception(f"Audio extraction error: {str(e)}")

def transcribe_audio(audio_file_path: str):
    """
    Transcribe audio file using AssemblyAI
    Much simpler than Google Cloud!
    """
    try:
        transcriber = aai.Transcriber()
        
        # AssemblyAI automatically handles file upload and transcription
        transcript = transcriber.transcribe(audio_file_path)
        
        # Check for errors
        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"Transcription failed: {transcript.error}")
        
        # Check if speech was detected
        if not transcript.text or len(transcript.text.strip()) == 0:
            raise Exception("No speech detected in video. Please ensure the video has clear audio.")
        
        return transcript.text
    
    except Exception as e:
        raise Exception(f"Transcription error: {str(e)}")

# Endpoint to check processing status
@app.get("/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in job_status:
        return JSONResponse(
            status_code=404,
            content={"detail": "Job not found"}
        )
    
    return job_status[job_id]

# Endpoint to answer question
@app.post("/ask")
async def ask_question(data: dict):
    try:
        transcription = data.get('transcriptionId')
        question = data.get('question')

        if not transcription or not question:
            return JSONResponse(
                status_code=400,
                content={"detail": "Missing transcription or question"}
            )

        # Use Groq API
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            return JSONResponse(
                status_code=500,
                content={"detail": "GROQ_API_KEY environment variable is not set"}
            )
        
        headers = {
            'Authorization': f'Bearer {groq_api_key}', 
            'Content-Type': 'application/json'
        }
        
        # Limit transcript to avoid token limits
        max_transcript_length = 4000
        truncated_transcript = transcription[:max_transcript_length]
        
        payload = {
            'model': 'llama-3.3-70b-versatile',  # Free and powerful
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a helpful assistant that answers questions about video content based on transcripts. Provide clear, concise answers.'
                },
                {
                    'role': 'user',
                    'content': f"Video Transcript:\n{truncated_transcript}\n\nQuestion: {question}\n\nPlease answer based only on the transcript above."
                }
            ],
            'max_tokens': 500,
            'temperature': 0.7
        }
        
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )

        print(f"Groq Status: {response.status_code}")

        if response.status_code != 200:
            print(f"Groq Error: {response.text}")
            raise Exception(f"Groq API error ({response.status_code}): {response.text}")

        result = response.json()
        answer = result['choices'][0]['message']['content']
        
        return {"answer": answer}
        
    except requests.exceptions.Timeout:
        return JSONResponse(
            status_code=500,
            content={"detail": "Request timed out. Please try again."}
        )
    except Exception as e:
        print(f"Error in ask_question: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error: {str(e)}"}
        )
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)