# Video AI App

A modern web application that allows you to upload videos, extract audio transcripts, and ask questions about the video content using AI.

## Features

- **Video Upload**: Upload video files with a modern drag-and-drop interface
- **Audio Transcription**: Automatically extracts audio and transcribes it using AssemblyAI
- **AI Q&A**: Ask questions about the video content and get AI-powered answers using Groq API (Llama 3.3 70B)
- **Real-time Status**: Track video processing progress with live status updates
- **Modern UI**: Beautiful gradient interface built with Tailwind CSS
 - **Troubleshooting & Windows**: Includes guidance for FFmpeg on Windows and common issues

## Tech Stack

### Frontend
- **Next.js 16** - React framework
- **React 19** - UI library
- **Tailwind CSS** - Styling
- **Axios** - HTTP client
- **react-dropzone** - File upload component

### Backend
- **FastAPI** - Python web framework
- **AssemblyAI** - Audio transcription service
- **Groq API** - AI question answering (Llama 3.3 70B)
- **FFmpeg** - Audio extraction from video

## Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** (v18 or higher)
- **Python** (v3.8 or higher)
- **FFmpeg** - Required for audio extraction
  - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt-get install ffmpeg`

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/nerminekabadou/AI-Video-Transciption.git
cd video-ai-app
```

### 2. Install Frontend Dependencies

```bash
npm install
```

### 3. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory with the following content:

```env
# AssemblyAI API Key
# Get your API key from https://www.assemblyai.com/app/account
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here

# Groq API Key
# Get your API key from https://console.groq.com/keys
GROQ_API_KEY=your_groq_api_key_here

# Optional: FFmpeg Path
# Only set this if ffmpeg is not in your system PATH
# Leave empty to use system PATH
# Windows example: FFMPEG_PATH=C:\path\to\ffmpeg.exe
# Linux/Mac: FFMPEG_PATH=/usr/local/bin/ffmpeg
FFMPEG_PATH=
```

Notes on `FFMPEG_PATH` (Windows)
- If `ffmpeg.exe` is installed and available on your PATH, you can leave `FFMPEG_PATH` empty.
- If you installed FFmpeg in a custom location on Windows, set `FFMPEG_PATH` to the path of `ffmpeg.exe` (no surrounding quotes), for example:
  - `FFMPEG_PATH=C:\\ffmpeg\\bin\\ffmpeg.exe`
  - You may also include extra flags if needed, e.g. `C:\\ffmpeg\\bin\\ffmpeg.exe -hide_banner -loglevel error`
- If you set `FFMPEG_PATH` with backslashes, escape them in the `.env` or use forward slashes: `C:/ffmpeg/bin/ffmpeg.exe`.

**Getting API Keys:**

1. **AssemblyAI API Key**:
   - Sign up at [AssemblyAI](https://www.assemblyai.com/)
   - Go to your [account settings](https://www.assemblyai.com/app/account)
   - Copy your API key

2. **Groq API Key**:
   - Sign up at [Groq](https://console.groq.com/)
   - Navigate to [API Keys](https://console.groq.com/keys)
   - Create a new API key and copy it

## Running the Application

### Start the Backend Server

You can start the backend in one of two equivalent ways:

- Direct Python (runs the app using the builtin uvicorn invocation in `main.py`):

```powershell
python main.py
```

- Or with Uvicorn for autoreload during development:

```powershell
uvicorn main:app --reload
```

The FastAPI server will run on `http://localhost:8000`

### Start the Frontend Development Server

In a new terminal:

```bash
npm run dev
```

The Next.js app will run on `http://localhost:3000`

Open [http://localhost:3000](http://localhost:3000) in your browser to use the application.

## Usage

1. **Upload a Video**: Click the upload area or drag and drop a video file
2. **Process Video**: Click "Process Video" to start transcription
3. **Wait for Processing**: The app will extract audio and transcribe it (this may take a few minutes)
4. **Ask Questions**: Once processing is complete, enter your question and click "Ask Question"
5. **Get Answers**: The AI will analyze the transcript and provide an answer


## API Endpoints

### `POST /upload`
Upload a video file for processing.

**Request**: Multipart form data with `file` field
**Response**: 
```json
{
  "jobId": "uuid",
  "message": "Video upload started"
}
```

### `GET /status/{job_id}`
Check the processing status of an uploaded video.

**Response**:
```json
{
  "status": "processing|completed|failed",
  "transcriptionId": "transcript text",
  "error": null
}
```

### `POST /ask`
Ask a question about the video transcript.

**Request**:
```json
{
  "transcriptionId": "transcript text",
  "question": "Your question here"
}
```

**Response**:
```json
{
  "answer": "AI-generated answer"
}
```

## Configuration

All configuration is done through environment variables in the `.env` file. Make sure to:

1. Create a `.env` file in the root directory (see step 4 in Installation)
2. Add your API keys:
   - `ASSEMBLYAI_API_KEY` - Your AssemblyAI API key
   - `GROQ_API_KEY` - Your Groq API key
   - `FFMPEG_PATH` - Optional, only if ffmpeg is not in your system PATH

3. Add `.env` to `.gitignore` to keep keys secure. If your repo does not already ignore `.env`, please add it.

## Notes

- Video files are temporarily stored during processing and automatically deleted afterward
- The app uses in-memory storage for job status (consider using Redis or a database for production)
- Make sure to add `.env` to your `.gitignore` file to keep your API keys secure
- AssemblyAI offers free tier transcription with generous limits
- Groq API provides fast inference with free tier access

## Troubleshooting

- Windows FFmpeg errors (e.g. "[WinError 87] Paramètre incorrect"):
  - Ensure `ffmpeg.exe` exists at the path specified in `FFMPEG_PATH` or is available on your PATH.
  - In PowerShell you can set the env var for the session and run the server:

```powershell
$env:FFMPEG_PATH='C:\\path\\to\\ffmpeg.exe'
python main.py
```

  - If you see errors from FFmpeg, check the backend `/status/{jobId}` `error` field — it contains the FFmpeg stderr to help diagnose the issue.

- If uploads fail with large videos:
  - Try a smaller sample file to confirm extraction works.
  - Increase the extraction timeout in `main.py` or limit upload sizes on the frontend.

- Job persistence:
  - Jobs are stored in-memory. Restarting the backend clears jobs. For production use, replace the in-memory store with Redis or a database.
