# 🎯 Interview Copilot - API Backend

> FastAPI backend with Gemini 2.5 Pro for Interview Copilot Extension

## 🌟 Features

- ✅ **Gemini 2.5 Pro Integration** - Powerful AI responses
- ✅ **Whisper AI Transcription** - Accurate speech-to-text
- ✅ **REST API** - Standard HTTP endpoints
- ✅ **WebSocket Support** - Real-time audio streaming
- ✅ **CORS Enabled** - Works with browser extensions
- ✅ **Async/Await** - High performance
- ✅ **Production Ready** - Can be hosted on cloud

## 📋 Requirements

- Python 3.10+
- Google Gemini API Key
- FFmpeg (for Whisper)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd api-backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional - defaults shown
GEMINI_MODEL=gemini-2.0-flash-exp
WHISPER_MODEL=base
WHISPER_LANGUAGE=pl
API_HOST=0.0.0.0
API_PORT=5000
API_DEBUG=False
CORS_ORIGINS=*
```

**Get Gemini API Key:**
1. Go to https://makersuite.google.com/app/apikey
2. Create new API key
3. Copy and paste into `.env`

### 3. Run Server

```bash
# Development (with auto-reload)
python app.py

# Or with uvicorn directly
uvicorn app:app --reload --host 0.0.0.0 --port 5000

# Production
uvicorn app:app --host 0.0.0.0 --port 5000 --workers 4
```

Server will start on: `http://localhost:5000`

## 📖 API Documentation

### Interactive Docs

Once server is running, visit:
- **Swagger UI**: http://localhost:5000/docs
- **ReDoc**: http://localhost:5000/redoc

### Endpoints

#### Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "gemini_model": "gemini-2.0-flash-exp",
  "whisper_model": "base",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Transcribe Audio
```http
POST /api/transcribe
Content-Type: application/json

{
  "audio": "base64_encoded_audio",
  "language": "pl"
}
```

#### Generate Answer
```http
POST /api/generate
Content-Type: application/json

{
  "question": "What is your experience with Python?",
  "context": {
    "cv": "Senior Python Developer...",
    "company": "Google",
    "position": "Backend Engineer"
  },
  "temperature": 0.7,
  "max_tokens": 500
}
```

#### Process Audio (Full Pipeline)
```http
POST /api/process_audio
Content-Type: application/json

{
  "audio": [0.1, 0.2, ...],  // Float32Array
  "sampleRate": 16000
}
```

**Response:**
```json
{
  "success": true,
  "question": "What is your experience?",
  "answer": "I have 5 years of experience...",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Context Management
```http
GET /api/context
POST /api/context
```

#### History
```http
GET /api/history
```

### WebSocket

Connect to: `ws://localhost:5000/ws/audio`

**Message Format:**

Send audio:
```json
{
  "type": "audio",
  "data": [0.1, 0.2, ...]
}
```

Receive transcription:
```json
{
  "type": "transcription",
  "text": "What is your experience?"
}
```

Receive answer:
```json
{
  "type": "answer",
  "answer": "I have 5 years..."
}
```

## 🧪 Testing

### Manual Testing

```bash
# Health check
curl http://localhost:5000/api/health

# Generate answer
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Why do you want to work here?",
    "context": {
      "cv": "Senior Developer with 5 years experience",
      "company": "TechCorp",
      "position": "Senior Engineer"
    }
  }'
```

### Python Testing

```python
import requests

# Test health
response = requests.get('http://localhost:5000/api/health')
print(response.json())

# Test generation
response = requests.post('http://localhost:5000/api/generate', json={
    "question": "What are your strengths?",
    "context": {
        "cv": "Python expert, team lead",
        "company": "Google",
        "position": "Tech Lead"
    }
})
print(response.json())
```

## 🚀 Deployment

### Option 1: Railway (Recommended)

1. Create account at https://railway.app
2. Connect GitHub repo
3. Add environment variables (GEMINI_API_KEY, etc.)
4. Deploy!

**Cost:** ~$5/month

### Option 2: Google Cloud Run

```bash
# Build container
docker build -t interview-copilot-api .

# Deploy to Cloud Run
gcloud run deploy interview-copilot-api \
  --image interview-copilot-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key
```

### Option 3: VPS (DigitalOcean, Linode)

```bash
# Install dependencies
apt update && apt install -y python3.10 python3-pip ffmpeg

# Clone repo
git clone your-repo
cd api-backend

# Install
pip install -r requirements.txt

# Run with supervisor/systemd
uvicorn app:app --host 0.0.0.0 --port 5000
```

### Docker

```bash
# Build
docker build -t interview-copilot-api .

# Run
docker run -p 5000:5000 \
  -e GEMINI_API_KEY=your_key \
  interview-copilot-api
```

## 📊 Architecture

```
┌────────────────────────────────────────┐
│     Browser Extension (JavaScript)      │
│  • Audio capture                        │
│  • WebSocket client                     │
└───────────────┬────────────────────────┘
                │ HTTP/WebSocket
┌───────────────▼────────────────────────┐
│     FastAPI Backend (Python)           │
│  • REST endpoints                       │
│  • WebSocket server                     │
└───────────────┬────────────────────────┘
                │
        ┌───────┴────────┐
        │                │
┌───────▼──────┐  ┌─────▼──────┐
│  Whisper AI  │  │ Gemini 2.5 │
│ (Local STT)  │  │ (Cloud LLM)│
└──────────────┘  └────────────┘
```

## 🔐 Security

### API Key Protection

**DO NOT:**
- ❌ Commit `.env` to git
- ❌ Expose API key in frontend
- ❌ Share API key publicly

**DO:**
- ✅ Use environment variables
- ✅ Add `.env` to `.gitignore`
- ✅ Rotate keys regularly
- ✅ Use rate limiting in production

### Production Settings

```env
# Production .env
API_DEBUG=False
REQUIRE_API_KEY=True
CORS_ORIGINS=https://yourdomain.com
RATE_LIMIT_PER_MINUTE=30
```

## 🐛 Troubleshooting

### Gemini API Error

**Problem:** `401 Unauthorized`

**Solution:**
```bash
# Check API key
echo $GEMINI_API_KEY

# Test API key
curl -H "Content-Type: application/json" \
  -H "x-goog-api-key: YOUR_KEY" \
  https://generativelanguage.googleapis.com/v1/models
```

### Whisper Loading Error

**Problem:** `Failed to load Whisper model`

**Solution:**
```bash
# Install FFmpeg
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
choco install ffmpeg
```

### CORS Error

**Problem:** Browser blocks requests

**Solution:**
```env
# In .env, set specific origins
CORS_ORIGINS=https://yourextension.com,http://localhost:3000
```

### Port Already in Use

**Problem:** `Address already in use`

**Solution:**
```bash
# Find process using port 5000
# Linux/macOS
lsof -i :5000

# Windows
netstat -ano | findstr :5000

# Kill process or use different port
API_PORT=5001
```

## 📈 Performance

### Benchmarks (Single Core)

- **Transcription (3s audio):** ~2-5 seconds
- **Gemini Generation:** ~1-3 seconds
- **End-to-end:** ~3-8 seconds

### Optimization Tips

1. **Use GPU for Whisper:**
```python
transcription_engine = TranscriptionEngine(
    model_name="base",
    language="pl",
    fp16=True  # Requires GPU
)
```

2. **Use smaller Whisper model:**
```env
WHISPER_MODEL=tiny  # Fastest
```

3. **Increase workers:**
```bash
uvicorn app:app --workers 4
```

4. **Use Redis for caching** (future enhancement)

## 🔄 Migration from LM Studio

If migrating from old backend (LM Studio):

1. **Environment variables changed:**
```env
# Old
LM_STUDIO_HOST=localhost
LM_STUDIO_PORT=1234

# New
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.0-flash-exp
```

2. **No local LLM needed** - Gemini is cloud-based

3. **Better performance** - Gemini is faster and more accurate

4. **No setup hassle** - No need to download/run LM Studio

## 📚 Additional Resources

- [Gemini API Documentation](https://ai.google.dev/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Whisper Documentation](https://github.com/openai/whisper)

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Add tests
4. Submit pull request

## 📄 License

MIT License - See parent project for details

---

**Ready to deploy! 🚀**

For questions or issues, check the main project README.
