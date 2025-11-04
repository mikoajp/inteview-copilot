"""Main FastAPI application for Interview Copilot API."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import numpy as np
import base64
import json
from datetime import datetime, timedelta

from config import config
from core.gemini_client import GeminiClient
from core.transcription import TranscriptionEngine
from core.question_detector import QuestionDetector
from core.context_manager import ContextManager
from models import Context, HistoryEntry
from auth import (
    get_current_user, get_optional_user, TokenData, UserCredentials,
    UserCreate, User, TokenResponse, create_access_token, create_user,
    authenticate_user
)

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
        print("🔄 Initializing Gemini client...")
        gemini_client = GeminiClient(
            api_key=config.gemini_api_key,
            model=config.gemini_model
        )
    
    if transcription_engine is None:
        print("🔄 Loading Whisper model...")
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
    auth_required: bool


# ============= Helper Functions =============

def get_session_id(user: Optional[TokenData]) -> str:
    """Get session ID from user token or default."""
    if user and user.user_id:
        return user.user_id
    return "default"


# ============= REST Endpoints =============

# ============= Authentication Endpoints =============

@app.post("/api/auth/register", response_model=dict)
async def register(user_data: UserCreate):
    """Register new user."""
    try:
        user = create_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name
        )

        return {
            "success": True,
            "message": "User registered successfully",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration error: {str(e)}")


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(credentials: UserCredentials):
    """Login and get JWT token."""
    user = authenticate_user(credentials.email, credentials.password)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=config.jwt_access_token_expire_minutes * 60  # Convert to seconds
    )


@app.get("/api/auth/me", response_model=User)
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """Get current user information."""
    from auth import get_user_by_id

    user = get_user_by_id(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user

@app.get("/", response_model=dict)
async def root():
    """Root endpoint."""
    return {
        "message": "Interview Copilot API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }


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
            timestamp=datetime.utcnow().isoformat(),
            auth_required=config.require_auth
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            version="2.0.0",
            gemini_model=config.gemini_model,
            whisper_model=config.whisper_model,
            timestamp=datetime.utcnow().isoformat(),
            auth_required=config.require_auth
        )


@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    request: TranscribeRequest,
    current_user: Optional[TokenData] = Depends(get_optional_user)
):
    """Transcribe audio to text."""
    if config.require_auth and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

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
async def generate_answer(
    request: GenerateRequest,
    current_user: Optional[TokenData] = Depends(get_optional_user)
):
    """Generate answer for a question."""
    if config.require_auth and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

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
async def process_audio(
    request: ProcessAudioRequest,
    current_user: Optional[TokenData] = Depends(get_optional_user)
):
    """Process audio: transcribe + detect question + generate answer."""
    if config.require_auth and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    initialize_engines()

    try:
        # Convert list to numpy array
        audio_array = np.array(request.audio, dtype=np.float32)

        # Normalize if needed
        if audio_array.max() > 1.0:
            audio_array = audio_array / 32768.0

        print(f"🎤 Processing audio: {len(audio_array)} samples")

        # Transcribe
        text = transcription_engine.transcribe(audio_array)

        if not text:
            return ProcessAudioResponse(
                success=True,
                question=None,
                answer=None
            )

        print(f"📝 Transcribed: {text}")

        # Check if it's a question
        is_question = question_detector.is_question(text)

        if is_question:
            print("❓ Question detected!")

            # Get context from session
            session_id = get_session_id(current_user)
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
                print(f"💡 Answer generated: {answer[:100]}...")
                
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
            print("ℹ️ Not a question")
            return ProcessAudioResponse(
                success=True,
                question=None,
                answer=None,
                transcription=text
            )
    
    except Exception as e:
        print(f"❌ Error processing audio: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/api/context", response_model=ContextResponse)
async def get_context(current_user: Optional[TokenData] = Depends(get_optional_user)):
    """Get interview context."""
    if config.require_auth and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    session_id = get_session_id(current_user)
    context_data = contexts.get(session_id, Context())

    return ContextResponse(
        cv=context_data.cv,
        company=context_data.company,
        position=context_data.position
    )


@app.post("/api/context", response_model=dict)
async def update_context(
    request: ContextRequest,
    current_user: Optional[TokenData] = Depends(get_optional_user)
):
    """Update interview context."""
    if config.require_auth and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    session_id = get_session_id(current_user)

    contexts[session_id] = Context(
        cv=request.cv,
        company=request.company,
        position=request.position
    )
    
    print(f"✅ Context updated: {request.company} - {request.position}")
    
    return {"success": True, "message": "Context updated"}


@app.get("/api/history", response_model=dict)
async def get_history(current_user: Optional[TokenData] = Depends(get_optional_user)):
    """Get interview history."""
    if config.require_auth and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    session_id = get_session_id(current_user)

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
    print("🔌 WebSocket connected")
    
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
        print("🔌 WebSocket disconnected")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        await websocket.close()


# ============= Startup/Shutdown Events =============

@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print("=" * 60)
    print("🎯 INTERVIEW COPILOT API SERVER")
    print("=" * 60)
    print(f"📍 Version: 2.0.0")
    print(f"🤖 Gemini Model: {config.gemini_model}")
    print(f"🎤 Whisper Model: {config.whisper_model}")
    print("=" * 60)
    
    # Validate config
    if not config.validate():
        print("⚠️  WARNING: Configuration validation failed!")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    print("👋 Shutting down Interview Copilot API...")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.api_debug
    )
