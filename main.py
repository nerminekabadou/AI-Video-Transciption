from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uuid
import asyncio
from typing import Dict
import google.cloud.speech as speech
from google.cloud import storage
import requests
import subprocess
import tempfile

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Google Cloud Storage
bucket_name = "your_bucket_name"

# Speech-to-text client setup
speech_client = speech.SpeechClient()

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
    Converts to WAV format with proper settings for Google Speech-to-Text
    """
    try:
        command = [
            'ffmpeg',
            '-i', video_path,           # Input video file
            '-vn',                       # No video
            '-acodec', 'pcm_s16le',     # Audio codec
            '-ar', '16000',              # Sample rate 16kHz
            '-ac', '1',                  # Mono channel
            '-y',                        # Overwrite output file
            audio_path
        ]
        
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
        raise Exception(f"FFmpeg error: {e.stderr.decode()}")
    except FileNotFoundError:
        raise Exception("FFmpeg not found. Please install ffmpeg: apt-get install ffmpeg or brew install ffmpeg")
    except Exception as e:
        raise Exception(f"Audio extraction error: {str(e)}")

def transcribe_audio(audio_file_path: str):
    """
    Transcribe audio file using Google Speech-to-Text API
    """
    try:
        # Check file size
        file_size = os.path.getsize(audio_file_path)
        
        with open(audio_file_path, 'rb') as audio_file:
            content = audio_file.read()

        audio = speech.RecognitionAudio(content=content)
        
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            enable_automatic_punctuation=True,
            model='video',  # Optimized for video
        )

        # For files larger than 10MB or longer than 1 minute, use long_running_recognize
        if file_size > 10 * 1024 * 1024:  # 10MB
            # Upload to Google Cloud Storage for long audio
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            blob_name = f"temp_audio_{uuid.uuid4()}.wav"
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(audio_file_path)
            
            gcs_uri = f"gs://{bucket_name}/{blob_name}"
            audio = speech.RecognitionAudio(uri=gcs_uri)
            
            operation = speech_client.long_running_recognize(config=config, audio=audio)
            response = operation.result(timeout=600)  # 10 minute timeout
            
            # Clean up GCS file
            blob.delete()
        else:
            # Use synchronous recognition for shorter files
            response = speech_client.recognize(config=config, audio=audio)
        
        # Combine all transcription results
        transcript = ""
        for result in response.results:
            transcript += result.alternatives[0].transcript + " "
        
        if not transcript.strip():
            raise Exception("No speech detected in video. Please ensure the video has clear audio.")
        
        return transcript.strip()
    
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

        # Query the Mistral model via HuggingFace API
        headers = {
            'Authorization': 'Bearer YOUR_HUGGINGFACE_API_KEY'
        }
        
        # Create a focused prompt
        prompt = f"""Based on this video transcript, answer the question concisely and accurately.

Transcript: {transcription[:2000]}...

Question: {question}

Answer:"""
        
        payload = {
            'inputs': prompt,
            'parameters': {
                'max_new_tokens': 250,
                'temperature': 0.7,
                'top_p': 0.9,
                'return_full_text': False
            }
        }
        
        response = requests.post(
            'https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1',
            headers=headers, 
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(f"HuggingFace API error: {response.text}")

        result = response.json()
        
        if isinstance(result, list) and len(result) > 0:
            answer = result[0].get('generated_text', 'No answer generated')
        else:
            answer = result.get('generated_text', 'No answer generated')
        
        return {"answer": answer}
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error getting answer: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)