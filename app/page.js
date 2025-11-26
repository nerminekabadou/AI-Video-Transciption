"use client";

import { useState, useRef } from 'react';

// Custom SVG Icons
const Upload = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
    <polyline points="17 8 12 3 7 8"/>
    <line x1="12" y1="3" x2="12" y2="15"/>
  </svg>
);

const Send = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"/>
    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
);

const Video = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="23 7 16 12 23 17 23 7"/>
    <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
  </svg>
);

const AlertCircle = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <line x1="12" y1="8" x2="12" y2="12"/>
    <line x1="12" y1="16" x2="12.01" y2="16"/>
  </svg>
);

const CheckCircle2 = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <path d="m9 12 2 2 4-4"/>
  </svg>
);

const Loader2 = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="animate-spin">
    <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
  </svg>
);

export default function Home() {
  const [video, setVideo] = useState(null);
  const [videoPreview, setVideoPreview] = useState(null);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [transcriptionId, setTranscriptionId] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('idle'); // idle, uploading, processing, success, error
  const [uploadProgress, setUploadProgress] = useState(0);
  const [askStatus, setAskStatus] = useState('idle');
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setVideo(file);
      setVideoPreview(URL.createObjectURL(file));
      setUploadStatus('idle');
      setTranscriptionId(null);
      setAnswer('');
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!video) {
      setError('Please select a video file first');
      return;
    }

    const formData = new FormData();
    formData.append('file', video);

    try {
      setUploadStatus('uploading');
      setUploadProgress(0);
      setError('');
      console.log('Starting video upload...', video.name, `(${(video.size / 1024 / 1024).toFixed(2)} MB)`);
      
      // Upload the file
      const uploadResponse = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });

      if (!uploadResponse.ok) {
        const errorData = await uploadResponse.json();
        throw new Error(errorData.detail || 'Upload failed');
      }
      
      const uploadData = await uploadResponse.json();
      const jobId = uploadData.jobId;
      console.log('Upload successful! Job ID:', jobId);
      
      // Poll for processing status
      setUploadStatus('processing');
      setUploadProgress(30);
      
      await pollProcessingStatus(jobId);
      
    } catch (err) {
      console.error('Upload error:', err);
      setError(err.message || 'Failed to upload video. Please try again.');
      setUploadStatus('error');
    }
  };

  const pollProcessingStatus = async (jobId) => {
    const maxAttempts = 60; // 5 minutes max (60 * 5 seconds)
    let attempts = 0;
    
    // Helper function to delay
    const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
    
    const poll = async () => {
      try {
        attempts++;
        console.log(`Polling attempt ${attempts}/${maxAttempts} for job ${jobId}`);
        
        const response = await fetch(`http://localhost:8000/status/${jobId}`);
        
        if (!response.ok) {
          throw new Error('Failed to check processing status');
        }
        
        const data = await response.json();
        console.log('Status response:', data);
        
        if (data.status === 'completed') {
          setTranscriptionId(data.transcriptionId);
          setUploadProgress(100);
          setUploadStatus('success');
          console.log('Processing completed!');
        } else if (data.status === 'failed') {
          throw new Error(data.error || 'Processing failed');
        } else if (data.status === 'processing') {
          // Update progress (gradually increase from 30% to 90%)
          const progress = Math.min(30 + (attempts * 1.2), 90);
          setUploadProgress(progress);
          console.log(`Processing... Progress: ${progress}%`);
          
          if (attempts < maxAttempts) {
            // Wait 5 seconds before next poll
            await delay(5000);
            await poll(); // Recursively poll again
          } else {
            throw new Error('Processing timeout - please try with a shorter video');
          }
        }
      } catch (err) {
        console.error('Polling error:', err);
        setError(err.message);
        setUploadStatus('error');
      }
    };
    
    await poll();
  };

  const handleAskQuestion = async () => {
    if (!transcriptionId) {
      setError('Please upload a video first');
      return;
    }

    if (!question.trim()) {
      setError('Please enter a question');
      return;
    }

    try {
      setAskStatus('loading');
      setError('');
      
      const response = await fetch('http://localhost:8000/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcriptionId, question }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to get answer');
      }
      const data = await response.json();
      
      setAnswer(data.answer);
      setAskStatus('success');
    } catch (err) {
      console.error('Full error:', err);
      setError(err.message || 'Failed to get answer. Please try again.');
      setAskStatus('error');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAskQuestion();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="container mx-auto px-4 py-12 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-purple-500/20 rounded-2xl mb-4">
            <Video className="w-8 h-8 text-purple-400" />
          </div>
          <h1 className="text-4xl font-bold text-white mb-3">
            Video Intelligence
          </h1>
          <p className="text-slate-400 text-lg">
            Upload a video and ask questions about its content
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/20 overflow-hidden">
          {/* Upload Section */}
          <div className="p-8 border-b border-white/10">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
              <Upload className="w-5 h-5" />
              Upload Video
            </h2>
            
            <div className="space-y-4">
              {/* File Input */}
              <div 
                onClick={() => fileInputRef.current?.click()}
                className="relative border-2 border-dashed border-purple-400/50 rounded-2xl p-8 text-center cursor-pointer hover:border-purple-400 hover:bg-white/5 transition-all duration-300"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/*"
                  onChange={handleFileChange}
                  className="hidden"
                />
                
                {videoPreview ? (
                  <div className="space-y-3">
                    <CheckCircle2 className="w-12 h-12 text-green-400 mx-auto" />
                    <p className="text-white font-medium">{video.name}</p>
                    <p className="text-sm text-slate-400">
                      {(video.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <Video className="w-12 h-12 text-purple-400 mx-auto" />
                    <p className="text-white font-medium">Click to select a video</p>
                    <p className="text-sm text-slate-400">
                      or drag and drop your video here
                    </p>
                  </div>
                )}
              </div>

              {/* Upload Button */}
              <button
                onClick={handleUpload}
                disabled={!video || uploadStatus === 'uploading' || uploadStatus === 'processing' || uploadStatus === 'success'}
                className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white font-semibold py-4 px-6 rounded-xl hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 shadow-lg shadow-purple-500/30"
              >
                <div className="flex items-center justify-center gap-2">
                  {uploadStatus === 'uploading' ? (
                    <>
                      <Loader2 />
                      <span>Uploading Video...</span>
                    </>
                  ) : uploadStatus === 'processing' ? (
                    <>
                      <Loader2 />
                      <span>Processing Video... {uploadProgress}%</span>
                    </>
                  ) : uploadStatus === 'success' ? (
                    <>
                      <CheckCircle2 />
                      <span>Video Processed Successfully</span>
                    </>
                  ) : (
                    <>
                      <Upload />
                      <span>Process Video</span>
                    </>
                  )}
                </div>
              </button>

              {/* Progress Bar */}
              {(uploadStatus === 'uploading' || uploadStatus === 'processing') && (
                <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden">
                  <div 
                    className="bg-gradient-to-r from-purple-500 to-pink-500 h-full transition-all duration-500 ease-out"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Question Section */}
          <div className="p-8">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
              <Send className="w-5 h-5" />
              Ask a Question
            </h2>

            <div className="space-y-4">
              {/* Question Input */}
              <div className="relative">
                <input
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="What would you like to know about the video?"
                  disabled={uploadStatus !== 'success'}
                  className="w-full bg-white/5 border border-white/20 rounded-xl py-4 px-6 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                />
              </div>

              {/* Ask Button */}
              <button
                onClick={handleAskQuestion}
                disabled={uploadStatus !== 'success' || askStatus === 'loading' || !question.trim()}
                className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-semibold py-4 px-6 rounded-xl hover:from-blue-600 hover:to-cyan-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center gap-2 shadow-lg shadow-blue-500/30"
              >
                {askStatus === 'loading' ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Thinking...
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5" />
                    Ask Question
                  </>
                )}
              </button>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mt-6 bg-red-500/20 border border-red-500/50 rounded-xl p-4 flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-red-200 text-sm">{error}</p>
              </div>
            )}

            {/* Answer Display */}
            {answer && (
              <div className="mt-6 bg-gradient-to-br from-purple-500/20 to-pink-500/20 border border-purple-400/30 rounded-xl p-6 animate-in fade-in duration-500">
                <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-green-400" />
                  Answer
                </h3>
                <p className="text-slate-200 leading-relaxed">{answer}</p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-8">
          <p className="text-slate-500 text-sm">
            Powered by AI • Secure & Private
          </p>
        </div>
      </div>
    </div>
  );
}