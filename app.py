"""Main FastAPI application for Interview Copilot API."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import numpy as np
import base64
import json
from datetime import datetime

from config import config
from core.gemini_client import GeminiClient
from core.transcription import TranscriptionEngine
from core.question_detector import QuestionDetector
from core.context_manager import ContextManager
from models import Context, HistoryEntry
from logger import log_info, log_error, log_warning, log_debug
from metrics import get_metrics
import time

# Initialize FastAPI app
app = FastAPI(
    title="Interview Copilot API",
    description="AI-powered interview assistance API with Gemini 2.5 Pro",
    version="2.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins.split(",") if config.cors_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances (lazy loaded)
gemini_client: Optional[GeminiClient] = None
transcription_engine: Optional[TranscriptionEngine] = None
question_detector: QuestionDetector = QuestionDetector()
context_manager: ContextManager = ContextManager()

# In-memory storage (replace with database in production)
contexts: Dict[str, Context] = {}
history: Dict[str, list] = {}


def initialize_engines():
    """Initialize AI engines (lazy loading)."""
    global gemini_client, transcription_engine
    
    if gemini_client is None:
        log_info("🔄 Initializing Gemini client...")
        gemini_client = GeminiClient(
            api_key=config.gemini_api_key,
            model=config.gemini_model
        )
    
    if transcription_engine is None:
        log_info("🔄 Loading Whisper model...")
        transcription_engine = TranscriptionEngine(
            model_name=config.whisper_model,
            language=config.whisper_language
        )


# ============= Pydantic Models =============

class TranscribeRequest(BaseModel):
    audio: str  # base64 encoded audio
    language: Optional[str] = "pl"

class TranscribeResponse(BaseModel):
    text: str
    language: str
    timestamp: str

class GenerateRequest(BaseModel):
    question: str
    context: Dict[str, str]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 500

class GenerateResponse(BaseModel):
    answer: str
    timestamp: str

class ProcessAudioRequest(BaseModel):
    audio: list  # Float32Array as list
    sampleRate: Optional[int] = 16000

class ProcessAudioResponse(BaseModel):
    success: bool
    question: Optional[str] = None
    answer: Optional[str] = None
    timestamp: Optional[str] = None
    transcription: Optional[str] = None

class ContextRequest(BaseModel):
    cv: str
    company: str
    position: str

class ContextResponse(BaseModel):
    cv: str
    company: str
    position: str

class HealthResponse(BaseModel):
    status: str
    version: str
    gemini_model: str
    whisper_model: str
    timestamp: str


# ============= REST Endpoints =============

@app.get("/", response_model=dict)
async def root():
    """Root endpoint."""
    return {
        "message": "Interview Copilot API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "metrics": "/metrics"
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return await get_metrics()


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    # Initialize engines to check if they work
    try:
        initialize_engines()
        gemini_ok = gemini_client.check_connection() if gemini_client else False
        
        return HealthResponse(
            status="healthy" if gemini_ok else "degraded",
            version="2.0.0",
            gemini_model=config.gemini_model,
            whisper_model=config.whisper_model,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            version="2.0.0",
            gemini_model=config.gemini_model,
            whisper_model=config.whisper_model,
            timestamp=datetime.utcnow().isoformat()
        )


@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(request: TranscribeRequest):
    """Transcribe audio to text."""
    initialize_engines()
    
    try:
        # Decode base64 audio
        audio_bytes = base64.b64decode(request.audio)
        audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
        
        # Transcribe
        text = transcription_engine.transcribe(audio_array)
        
        if not text:
            raise HTTPException(status_code=400, detail="Failed to transcribe audio")
        
        return TranscribeResponse(
            text=text,
            language=request.language,
            timestamp=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_answer(request: GenerateRequest):
    """Generate answer for a question."""
    initialize_engines()
    
    try:
        # Build system prompt
        system_prompt = context_manager.build_system_prompt(
            cv=request.context.get("cv", ""),
            company=request.context.get("company", ""),
            position=request.context.get("position", "")
        )
        
        # Generate response
        answer = await gemini_client.generate_response_async(
            system_prompt=system_prompt,
            user_prompt=request.question,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        if not answer:
            raise HTTPException(status_code=500, detail="Failed to generate answer")
        
        return GenerateResponse(
            answer=answer,
            timestamp=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")


@app.post("/api/process_audio", response_model=ProcessAudioResponse)
async def process_audio(request: ProcessAudioRequest):
    """Process audio: transcribe + detect question + generate answer."""
    initialize_engines()
    
    try:
        # Convert list to numpy array
        audio_array = np.array(request.audio, dtype=np.float32)
        
        # Normalize if needed
        if audio_array.max() > 1.0:
            audio_array = audio_array / 32768.0
        
        log_info(f"🎤 Processing audio: {len(audio_array)} samples")
        
        # Transcribe
        text = transcription_engine.transcribe(audio_array)
        
        if not text:
            return ProcessAudioResponse(
                success=True,
                question=None,
                answer=None
            )
        
        log_info(f"📝 Transcribed: {text}")
        
        # Check if it's a question
        is_question = question_detector.is_question(text)
        
        if is_question:
            log_info("❓ Question detected!")
            
            # Get context from session (in production, use database)
            session_id = "default"  # In production, get from auth
            context_data = contexts.get(session_id, Context())
            
            # Build system prompt
            system_prompt = context_manager.build_system_prompt(
                cv=context_data.cv,
                company=context_data.company,
                position=context_data.position
            )
            
            # Generate answer
            answer = await gemini_client.generate_response_async(
                system_prompt=system_prompt,
                user_prompt=text,
                temperature=0.7,
                max_tokens=500
            )
            
            if answer:
                log_info(f"💡 Answer generated: {answer[:100]}...")
                
                # Save to history
                if session_id not in history:
                    history[session_id] = []
                
                history[session_id].append({
                    "question": text,
                    "answer": answer,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                return ProcessAudioResponse(
                    success=True,
                    question=text,
                    answer=answer,
                    timestamp=datetime.utcnow().isoformat()
                )
            else:
                return ProcessAudioResponse(
                    success=True,
                    question=text,
                    answer=None
                )
        else:
            log_info("ℹ️ Not a question")
            return ProcessAudioResponse(
                success=True,
                question=None,
                answer=None,
                transcription=text
            )
    
    except Exception as e:
        log_info(f"❌ Error processing audio: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/api/context", response_model=ContextResponse)
async def get_context():
    """Get interview context."""
    session_id = "default"  # In production, get from auth
    context_data = contexts.get(session_id, Context())
    
    return ContextResponse(
        cv=context_data.cv,
        company=context_data.company,
        position=context_data.position
    )


@app.post("/api/context", response_model=dict)
async def update_context(request: ContextRequest):
    """Update interview context."""
    session_id = "default"  # In production, get from auth
    
    contexts[session_id] = Context(
        cv=request.cv,
        company=request.company,
        position=request.position
    )
    
    log_info(f"✅ Context updated: {request.company} - {request.position}")
    
    return {"success": True, "message": "Context updated"}


@app.get("/api/history", response_model=dict)
async def get_history():
    """Get interview history."""
    session_id = "default"  # In production, get from auth
    
    return {
        "success": True,
        "history": history.get(session_id, [])
    }


@app.post("/api/start", response_model=dict)
async def start_session():
    """Start interview session."""
    initialize_engines()
    
    return {
        "success": True,
        "message": "Session started"
    }


@app.post("/api/stop", response_model=dict)
async def stop_session():
    """Stop interview session."""
    return {
        "success": True,
        "message": "Session stopped"
    }


# ============= WebSocket Endpoint =============

@app.websocket("/ws/audio")
async def websocket_audio_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time audio streaming."""
    await websocket.accept()
    log_info("🔌 WebSocket connected")
    
    initialize_engines()
    
    session_id = "default"  # In production, get from auth
    
    try:
        while True:
            # Receive audio data
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "audio":
                # Process audio chunk
                audio_data = np.array(message["data"], dtype=np.float32)
                
                # Transcribe
                text = transcription_engine.transcribe(audio_data)
                
                if text:
                    # Send transcription
                    await websocket.send_json({
                        "type": "transcription",
                        "text": text
                    })
                    
                    # Check if question
                    if question_detector.is_question(text):
                        await websocket.send_json({
                            "type": "question_detected",
                            "question": text
                        })
                        
                        # Get context
                        context_data = contexts.get(session_id, Context())
                        system_prompt = context_manager.build_system_prompt(
                            cv=context_data.cv,
                            company=context_data.company,
                            position=context_data.position
                        )
                        
                        # Generate answer
                        answer = await gemini_client.generate_response_async(
                            system_prompt=system_prompt,
                            user_prompt=text,
                            temperature=0.7,
                            max_tokens=500
                        )
                        
                        if answer:
                            await websocket.send_json({
                                "type": "answer",
                                "answer": answer
                            })
            
            elif message["type"] == "context":
                # Update context
                context_data = message["data"]
                contexts[session_id] = Context(
                    cv=context_data.get("cv", ""),
                    company=context_data.get("company", ""),
                    position=context_data.get("position", "")
                )
                await websocket.send_json({
                    "type": "status",
                    "message": "Context updated"
                })
    
    except WebSocketDisconnect:
        log_info("🔌 WebSocket disconnected")
    except Exception as e:
        log_info(f"❌ WebSocket error: {e}")
        await websocket.close()


# ============= Startup/Shutdown Events =============

@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    log_info("=" * 60)
    log_info("🎯 INTERVIEW COPILOT API SERVER")
    log_info("=" * 60)
    log_info(f"📍 Version: 2.0.0")
    log_info(f"🤖 Gemini Model: {config.gemini_model}")
    log_info(f"🎤 Whisper Model: {config.whisper_model}")
    log_info("=" * 60)
    
    # Validate config
    if not config.validate():
        log_info("⚠️  WARNING: Configuration validation failed!")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    log_info("👋 Shutting down Interview Copilot API...")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.api_debug
    )
