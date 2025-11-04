"""Main FastAPI application for Interview Copilot API."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, constr
from typing import Optional, Dict
from sqlalchemy.orm import Session
import numpy as np
import base64
import json
from datetime import datetime
import time

from config import config
from core.gemini_client import GeminiClient
from core.transcription import TranscriptionEngine
from core.question_detector import QuestionDetector
from core.context_manager import ContextManager
from models import Context, HistoryEntry

# Import production features
from logger import log_info, log_error, log_warning, log_debug
from metrics import (
    request_count, request_duration, transcription_count, transcription_duration,
    generation_count, generation_duration, question_detected_count, error_count,
    get_metrics
)
from rate_limiter import rate_limit, get_limiter
from auth import (
    get_current_user, get_optional_user, get_websocket_user, TokenData, UserCredentials,
    UserCreate, User, TokenResponse, create_access_token, create_user,
    authenticate_user, get_user_by_id
)

# Database imports (conditional)
if config.use_database:
    from database import get_db, init_db, check_db_connection
    from db_operations import (
        get_context as get_context_db,
        update_context as update_context_db,
        add_history_entry,
        get_history as get_history_db
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

# HTTPS enforcement in production (when not in debug mode)
if not config.api_debug:
    from fastapi.middleware.trustedhost import TrustedHostMiddleware

    @app.middleware("http")
    async def enforce_https(request: Request, call_next):
        """Enforce HTTPS in production mode."""
        # Check if request is not already HTTPS
        if request.url.scheme != "https":
            # Check for X-Forwarded-Proto header (from reverse proxy)
            forwarded_proto = request.headers.get("X-Forwarded-Proto")
            if forwarded_proto != "https":
                # Allow health check endpoints without HTTPS
                if request.url.path not in ["/api/health", "/metrics"]:
                    log_warning(f"Non-HTTPS request blocked: {request.url}", extra={
                        "client": request.client.host if request.client else "unknown",
                        "path": request.url.path
                    })
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "HTTPS required in production mode"}
                    )
        return await call_next(request)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = time.time()

    log_info(f"Incoming request: {request.method} {request.url.path}", extra={
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host if request.client else "unknown"
    })

    response = await call_next(request)

    duration = time.time() - start_time
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    log_info(f"Request completed: {request.method} {request.url.path} - {response.status_code}", extra={
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration": duration
    })

    return response

# Add rate limiter to app state
if config.rate_limit_enabled:
    limiter = get_limiter()
    app.state.limiter = limiter

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
        log_info("✅ Gemini client initialized")

    if transcription_engine is None:
        log_info("🔄 Loading Whisper model...")
        transcription_engine = TranscriptionEngine(
            model_name=config.whisper_model,
            language=config.whisper_language
        )
        log_info("✅ Whisper model loaded")


# ============= Pydantic Models =============

class TranscribeRequest(BaseModel):
    audio: str = Field(..., max_length=10_000_000, description="Base64 encoded audio (max ~10MB)")
    language: constr(max_length=10) = "pl"

class TranscribeResponse(BaseModel):
    text: str
    language: str
    timestamp: str

class GenerateRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000, description="Question text (max 5000 chars)")
    context: Dict[str, str]
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(500, ge=1, le=2000)

class GenerateResponse(BaseModel):
    answer: str
    timestamp: str

class ProcessAudioRequest(BaseModel):
    audio: list = Field(..., max_items=1_000_000, description="Float32Array as list (max 1M samples ~60s)")
    sampleRate: Optional[int] = Field(16000, ge=8000, le=48000)

class ProcessAudioResponse(BaseModel):
    success: bool
    question: Optional[str] = None
    answer: Optional[str] = None
    timestamp: Optional[str] = None
    transcription: Optional[str] = None

class ContextRequest(BaseModel):
    cv: str = Field(..., max_length=50_000, description="CV text (max 50KB)")
    company: str = Field(..., min_length=1, max_length=200, description="Company name")
    position: str = Field(..., min_length=1, max_length=200, description="Job position")
    custom_system_prompt: Optional[str] = Field("", max_length=10_000, description="Custom system prompt (max 10KB)")

class ContextResponse(BaseModel):
    cv: str
    company: str
    position: str
    custom_system_prompt: str

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
        "health": "/api/health"
    }


# ============= Authentication Endpoints =============

@app.post("/api/auth/register", response_model=TokenResponse)
@rate_limit()
async def register(user_data: UserCreate, db: Session = Depends(get_db) if config.use_database else None):
    """Register a new user."""
    try:
        log_info(f"User registration attempt: {user_data.email}")

        # Create user
        user = await create_user(user_data, db)

        # Create access token
        access_token = create_access_token(data={"sub": user.id})

        log_info(f"User registered successfully: {user.email}")
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user
        )

    except HTTPException as e:
        log_warning(f"Registration failed: {e.detail}", extra={"email": user_data.email})
        error_count.labels(error_type="registration_failed", endpoint="/api/auth/register").inc()
        raise
    except Exception as e:
        log_error(f"Registration error: {str(e)}", extra={"email": user_data.email})
        error_count.labels(error_type="registration_error", endpoint="/api/auth/register").inc()
        raise HTTPException(status_code=500, detail=f"Registration error: {str(e)}")


@app.post("/api/auth/login", response_model=TokenResponse)
@rate_limit()
async def login(credentials: UserCredentials, db: Session = Depends(get_db) if config.use_database else None):
    """Authenticate user and return JWT token."""
    try:
        log_info(f"Login attempt: {credentials.email}")

        # Authenticate user
        user = await authenticate_user(credentials.email, credentials.password, db)

        if not user:
            log_warning(f"Login failed: invalid credentials", extra={"email": credentials.email})
            error_count.labels(error_type="login_failed", endpoint="/api/auth/login").inc()
            raise HTTPException(status_code=401, detail="Incorrect email or password")

        # Create access token
        access_token = create_access_token(data={"sub": user.id})

        log_info(f"Login successful: {credentials.email}")
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Login error: {str(e)}", extra={"email": credentials.email})
        error_count.labels(error_type="login_error", endpoint="/api/auth/login").inc()
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")


@app.get("/api/auth/me", response_model=User)
@rate_limit()
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    log_debug(f"User info requested: {current_user.id}")
    return current_user


# ============= Metrics Endpoint =============

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return await get_metrics()


@app.get("/api/health", response_model=HealthResponse)
@rate_limit("100/minute")
async def health_check():
    """Health check endpoint."""
    # Initialize engines to check if they work
    try:
        initialize_engines()
        gemini_ok = gemini_client.check_connection() if gemini_client else False

        # Check database connection if enabled
        if config.use_database:
            try:
                db_ok = check_db_connection()
            except Exception as e:
                log_warning(f"Database health check failed: {e}")
                db_ok = False

        status = "healthy" if gemini_ok else "degraded"

        log_debug(f"Health check: {status}")
        return HealthResponse(
            status=status,
            version="2.0.0",
            gemini_model=config.gemini_model,
            whisper_model=config.whisper_model,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        log_error(f"Health check error: {e}")
        error_count.labels(error_type="health_check_error", endpoint="/api/health").inc()
        return HealthResponse(
            status="unhealthy",
            version="2.0.0",
            gemini_model=config.gemini_model,
            whisper_model=config.whisper_model,
            timestamp=datetime.utcnow().isoformat()
        )


@app.post("/api/transcribe", response_model=TranscribeResponse)
@rate_limit()
async def transcribe_audio(
    request: TranscribeRequest,
    current_user: User = Depends(get_optional_user)
):
    """Transcribe audio to text."""
    initialize_engines()

    start_time = time.time()

    try:
        log_info(f"Transcription request received", extra={
            "user_id": current_user.id if current_user else "anonymous",
            "language": request.language
        })

        # Decode base64 audio
        audio_bytes = base64.b64decode(request.audio)
        audio_array = np.frombuffer(audio_bytes, dtype=np.float32)

        # Transcribe
        text = transcription_engine.transcribe(audio_array)

        if not text:
            log_warning("Transcription failed: empty result")
            error_count.labels(error_type="empty_transcription", endpoint="/api/transcribe").inc()
            raise HTTPException(status_code=400, detail="Failed to transcribe audio")

        # Track metrics
        transcription_count.inc()
        transcription_duration.observe(time.time() - start_time)

        log_info(f"Transcription successful: {len(text)} characters")

        return TranscribeResponse(
            text=text,
            language=request.language,
            timestamp=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Transcription error: {str(e)}")
        error_count.labels(error_type="transcription_error", endpoint="/api/transcribe").inc()
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


@app.post("/api/generate", response_model=GenerateResponse)
@rate_limit()
async def generate_answer(
    request: GenerateRequest,
    current_user: User = Depends(get_optional_user)
):
    """Generate answer for a question."""
    initialize_engines()

    start_time = time.time()

    try:
        log_info(f"Generation request received", extra={
            "user_id": current_user.id if current_user else "anonymous",
            "question_length": len(request.question)
        })

        # Build system prompt
        system_prompt = context_manager.build_system_prompt(
            cv=request.context.get("cv", ""),
            company=request.context.get("company", ""),
            position=request.context.get("position", ""),
            custom_system_prompt=request.context.get("custom_system_prompt", "")
        )

        # Generate response
        answer = await gemini_client.generate_response_async(
            system_prompt=system_prompt,
            user_prompt=request.question,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        if not answer:
            log_warning("Generation failed: empty result")
            error_count.labels(error_type="empty_generation", endpoint="/api/generate").inc()
            raise HTTPException(status_code=500, detail="Failed to generate answer")

        # Track metrics
        generation_count.inc()
        generation_duration.observe(time.time() - start_time)

        log_info(f"Generation successful: {len(answer)} characters")

        return GenerateResponse(
            answer=answer,
            timestamp=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Generation error: {str(e)}")
        error_count.labels(error_type="generation_error", endpoint="/api/generate").inc()
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")


@app.post("/api/process_audio", response_model=ProcessAudioResponse)
@rate_limit()
async def process_audio(
    request: ProcessAudioRequest,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db) if config.use_database else None
):
    """Process audio: transcribe + detect question + generate answer."""
    initialize_engines()

    start_time = time.time()
    session_id = current_user.id if current_user else "anonymous"

    try:
        # Convert list to numpy array
        audio_array = np.array(request.audio, dtype=np.float32)

        # Normalize if needed
        if audio_array.max() > 1.0:
            audio_array = audio_array / 32768.0

        log_info(f"Processing audio: {len(audio_array)} samples", extra={
            "user_id": session_id,
            "sample_count": len(audio_array)
        })

        # Transcribe
        transcription_start = time.time()
        text = transcription_engine.transcribe(audio_array)
        transcription_count.inc()
        transcription_duration.observe(time.time() - transcription_start)

        if not text:
            log_debug("Empty transcription result")
            return ProcessAudioResponse(
                success=True,
                question=None,
                answer=None
            )

        log_info(f"Transcribed: {text[:100]}...", extra={
            "user_id": session_id,
            "text_length": len(text)
        })

        # Check if it's a question
        is_question = question_detector.is_question(text)

        if is_question:
            log_info("Question detected!", extra={"user_id": session_id})
            question_detected_count.inc()

            # Get context from database or in-memory
            if config.use_database and db:
                context_data = get_context_db(session_id, db) or Context()
            else:
                context_data = contexts.get(session_id, Context())

            # Build system prompt
            system_prompt = context_manager.build_system_prompt(
                cv=context_data.cv,
                company=context_data.company,
                position=context_data.position,
                custom_system_prompt=context_data.custom_system_prompt
            )

            # Generate answer
            generation_start = time.time()
            answer = await gemini_client.generate_response_async(
                system_prompt=system_prompt,
                user_prompt=text,
                temperature=0.7,
                max_tokens=500
            )
            generation_count.inc()
            generation_duration.observe(time.time() - generation_start)

            if answer:
                log_info(f"Answer generated: {len(answer)} characters", extra={
                    "user_id": session_id,
                    "answer_length": len(answer)
                })

                # Save to history
                timestamp = datetime.utcnow().isoformat()
                if config.use_database and db:
                    add_history_entry(session_id, text, answer, db)
                else:
                    if session_id not in history:
                        history[session_id] = []
                    history[session_id].append({
                        "question": text,
                        "answer": answer,
                        "timestamp": timestamp
                    })

                return ProcessAudioResponse(
                    success=True,
                    question=text,
                    answer=answer,
                    timestamp=timestamp
                )
            else:
                log_warning("Answer generation returned empty result")
                return ProcessAudioResponse(
                    success=True,
                    question=text,
                    answer=None
                )
        else:
            log_debug("Not a question", extra={"user_id": session_id})
            return ProcessAudioResponse(
                success=True,
                question=None,
                answer=None,
                transcription=text
            )

    except Exception as e:
        log_error(f"Error processing audio: {str(e)}", extra={"user_id": session_id})
        error_count.labels(error_type="process_audio_error", endpoint="/api/process_audio").inc()
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/api/context", response_model=ContextResponse)
@rate_limit()
async def get_context(
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db) if config.use_database else None
):
    """Get interview context."""
    session_id = current_user.id if current_user else "anonymous"

    # Get context from database or in-memory
    if config.use_database and db:
        context_data = get_context_db(session_id, db) or Context()
    else:
        context_data = contexts.get(session_id, Context())

    log_debug(f"Context retrieved", extra={"user_id": session_id})

    return ContextResponse(
        cv=context_data.cv,
        company=context_data.company,
        position=context_data.position,
        custom_system_prompt=context_data.custom_system_prompt
    )


@app.post("/api/context", response_model=dict)
@rate_limit()
async def update_context(
    request: ContextRequest,
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db) if config.use_database else None
):
    """Update interview context."""
    session_id = current_user.id if current_user else "anonymous"

    context_data = Context(
        cv=request.cv,
        company=request.company,
        position=request.position,
        custom_system_prompt=request.custom_system_prompt or ""
    )

    # Update context in database or in-memory
    if config.use_database and db:
        update_context_db(session_id, context_data, db)
    else:
        contexts[session_id] = context_data

    log_info(f"Context updated: {request.company} - {request.position}", extra={
        "user_id": session_id,
        "company": request.company,
        "position": request.position
    })

    return {"success": True, "message": "Context updated"}


@app.get("/api/history", response_model=dict)
@rate_limit()
async def get_history(
    current_user: User = Depends(get_optional_user),
    db: Session = Depends(get_db) if config.use_database else None
):
    """Get interview history."""
    session_id = current_user.id if current_user else "anonymous"

    # Get history from database or in-memory
    if config.use_database and db:
        history_data = get_history_db(session_id, db)
    else:
        history_data = history.get(session_id, [])

    log_debug(f"History retrieved: {len(history_data)} entries", extra={
        "user_id": session_id,
        "entry_count": len(history_data)
    })

    return {
        "success": True,
        "history": history_data
    }


@app.post("/api/start", response_model=dict)
@rate_limit()
async def start_session(current_user: User = Depends(get_optional_user)):
    """Start interview session."""
    initialize_engines()

    session_id = current_user.id if current_user else "anonymous"
    log_info(f"Session started", extra={"user_id": session_id})

    return {
        "success": True,
        "message": "Session started"
    }


@app.post("/api/stop", response_model=dict)
@rate_limit()
async def stop_session(current_user: User = Depends(get_optional_user)):
    """Stop interview session."""
    session_id = current_user.id if current_user else "anonymous"
    log_info(f"Session stopped", extra={"user_id": session_id})

    return {
        "success": True,
        "message": "Session stopped"
    }


# ============= WebSocket Endpoint =============

@app.websocket("/ws/audio")
async def websocket_audio_stream(websocket: WebSocket, token: Optional[str] = None):
    """
    WebSocket endpoint for real-time audio streaming.

    Authentication:
        - Pass JWT token as query parameter: ws://host/ws/audio?token=YOUR_JWT_TOKEN
        - Or send auth message as first message: {"type": "auth", "token": "YOUR_JWT_TOKEN"}
        - If REQUIRE_AUTH is False, authentication is optional
    """
    await websocket.accept()

    initialize_engines()

    # Authenticate user from query param token
    user = await get_websocket_user(token)

    # If auth is required and no valid token, close connection
    if config.require_auth and not user:
        log_warning("WebSocket connection rejected: authentication required")
        await websocket.send_json({
            "type": "error",
            "message": "Authentication required. Provide token as query parameter: ?token=YOUR_JWT_TOKEN"
        })
        await websocket.close(code=1008)  # Policy violation
        return

    session_id = user.user_id if user else "anonymous"
    log_info(f"WebSocket connected: {session_id}")

    try:
        while True:
            # Receive audio data
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "audio":
                # Process audio chunk
                audio_data = np.array(message["data"], dtype=np.float32)

                # Transcribe
                transcription_start = time.time()
                text = transcription_engine.transcribe(audio_data)
                transcription_count.inc()
                transcription_duration.observe(time.time() - transcription_start)

                if text:
                    log_debug(f"WebSocket transcription: {text[:50]}...", extra={
                        "user_id": session_id,
                        "text_length": len(text)
                    })

                    # Send transcription
                    await websocket.send_json({
                        "type": "transcription",
                        "text": text
                    })

                    # Check if question
                    if question_detector.is_question(text):
                        question_detected_count.inc()
                        log_info("WebSocket question detected", extra={"user_id": session_id})

                        await websocket.send_json({
                            "type": "question_detected",
                            "question": text
                        })

                        # Get context
                        context_data = contexts.get(session_id, Context())
                        system_prompt = context_manager.build_system_prompt(
                            cv=context_data.cv,
                            company=context_data.company,
                            position=context_data.position,
                            custom_system_prompt=context_data.custom_system_prompt
                        )

                        # Generate answer
                        generation_start = time.time()
                        answer = await gemini_client.generate_response_async(
                            system_prompt=system_prompt,
                            user_prompt=text,
                            temperature=0.7,
                            max_tokens=500
                        )
                        generation_count.inc()
                        generation_duration.observe(time.time() - generation_start)

                        if answer:
                            log_info(f"WebSocket answer generated: {len(answer)} characters", extra={
                                "user_id": session_id
                            })

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
                    position=context_data.get("position", ""),
                    custom_system_prompt=context_data.get("custom_system_prompt", "")
                )

                log_info("WebSocket context updated", extra={
                    "user_id": session_id,
                    "company": context_data.get("company", ""),
                    "position": context_data.get("position", "")
                })

                await websocket.send_json({
                    "type": "status",
                    "message": "Context updated"
                })

    except WebSocketDisconnect:
        log_info("WebSocket disconnected", extra={"user_id": session_id})
    except Exception as e:
        log_error(f"WebSocket error: {str(e)}", extra={"user_id": session_id})
        error_count.labels(error_type="websocket_error", endpoint="/ws/audio").inc()
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
    log_info(f"🔐 Auth Required: {config.require_auth}")
    log_info(f"🛡️ Rate Limiting: {config.rate_limit_enabled}")
    log_info(f"💾 Database: {config.use_database}")
    log_info("=" * 60)

    # Validate config
    if not config.validate():
        log_warning("⚠️  WARNING: Configuration validation failed!")

    # Initialize database if enabled
    if config.use_database:
        try:
            log_info("Initializing database...")
            init_db()
            if check_db_connection():
                log_info("✅ Database connected successfully")
            else:
                log_error("❌ Database connection failed")
        except Exception as e:
            log_error(f"❌ Database initialization error: {str(e)}")


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
