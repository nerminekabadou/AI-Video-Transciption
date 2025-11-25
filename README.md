# Video AI App

A modern web application that allows you to upload videos, extract audio transcripts, and ask questions about the video content using AI.

## Features

- **Video Upload**: Upload video files with a modern drag-and-drop interface
- **Audio Transcription**: Automatically extracts audio and transcribes it using Google Cloud Speech-to-Text
- **AI Q&A**: Ask questions about the video content and get AI-powered answers using Mistral-7B model
- **Real-time Status**: Track video processing progress with live status updates
- **Modern UI**: Beautiful gradient interface built with Tailwind CSS

## Tech Stack

### Frontend
- **Next.js 16** - React framework
- **React 19** - UI library
- **Tailwind CSS** - Styling
- **Axios** - HTTP client
- **react-dropzone** - File upload component

### Backend
- **FastAPI** - Python web framework
- **Google Cloud Speech-to-Text** - Audio transcription
- **Google Cloud Storage** - File storage (for large files)
- **HuggingFace API** - AI question answering (Mistral-7B-Instruct)
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

Create a `requirements.txt` file with the following content:

```txt
fastapi==0.104.1
uvicorn==0.24.0
python-multipart==0.0.6
google-cloud-speech==2.23.0
google-cloud-storage==2.14.0
requests==2.31.0
```

Then install:

```bash
pip install -r requirements.txt
```

### 4. Configure Google Cloud

1. Create a Google Cloud project
2. Enable the **Speech-to-Text API** and **Cloud Storage API**
3. Create a service account and download the JSON key file
4. Set the environment variable:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
   ```
5. Create a Cloud Storage bucket and update `bucket_name` in `main.py` (line 26)

### 5. Configure HuggingFace API

1. Get your API key from [HuggingFace](https://huggingface.co/settings/tokens)
2. Update the `YOUR_HUGGINGFACE_API_KEY` in `main.py` (line 222)

## Running the Application

### Start the Backend Server

```bash
python main.py
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

Update these values in `main.py`:

- **Line 26**: `bucket_name = "your_bucket_name"` - Your Google Cloud Storage bucket name
- **Line 222**: `'Authorization': 'Bearer YOUR_HUGGINGFACE_API_KEY'` - Your HuggingFace API key

## Notes

- Video files are temporarily stored during processing and automatically deleted afterward
- For videos longer than 1 minute or larger than 10MB, the audio is uploaded to Google Cloud Storage for processing
- The app uses in-memory storage for job status (consider using Redis or a database for production)
