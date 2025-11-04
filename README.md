# 🎯 Interview Copilot - Production Ready API

> **FastAPI backend with Google Gemini 2.5 Pro for AI-powered interview assistance**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

### Core Functionality
- 🎤 **Real-time Audio Transcription** - OpenAI Whisper for accurate speech-to-text
- 🤖 **AI Answer Generation** - Google Gemini 2.5 Pro for intelligent responses
- 🔍 **Question Detection** - Automatic detection of interview questions (19 markers PL/EN)
- 📝 **Context Management** - CV, company, and position-aware responses
- 🎨 **Custom Prompts** - User-customizable system prompts for personalized AI behavior

### Production Features
- 🔐 **JWT Authentication** - Secure user authentication with Bearer tokens
- 💾 **PostgreSQL Database** - Persistent storage with SQLAlchemy ORM
- ⏱️ **Rate Limiting** - Protection against abuse (30 req/min default)
- 📊 **Structured Logging** - JSON logs for easy integration with ELK/Datadog
- 📈 **Prometheus Metrics** - `/metrics` endpoint for monitoring
- 🌐 **REST API + WebSocket** - Flexible communication options
- 🐳 **Docker Ready** - Full containerization support

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Google Gemini API Key ([Get one here](https://makersuite.google.com/app/apikey))
- FFmpeg (for Whisper audio processing)

### Installation

```bash
# Clone repository
git clone https://github.com/mikoajp/inteview-copilot
cd inteview-copilot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Run Locally

```bash
# Development mode (in-memory storage, no auth)
python app.py

# Production mode (requires PostgreSQL and auth)
# Set USE_DATABASE=True and REQUIRE_AUTH=True in .env
python app.py
```

API will be available at: http://localhost:5000

- **Docs**: http://localhost:5000/docs (Swagger UI)
- **Health**: http://localhost:5000/api/health
- **Metrics**: http://localhost:5000/metrics

## 📋 Configuration

All configuration via environment variables. See [.env.example](.env.example) for full list.

### Key Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | Required | Google Gemini API key |
| `USE_DATABASE` | False | Enable PostgreSQL (True/False) |
| `REQUIRE_AUTH` | True | Require JWT authentication |
| `RATE_LIMIT_ENABLED` | True | Enable rate limiting |
| `RATE_LIMIT_PER_MINUTE` | 30 | Max requests per minute |

### Development vs Production

**Development:**
```env
USE_DATABASE=False
REQUIRE_AUTH=False
API_DEBUG=True
```

**Production:**
```env
USE_DATABASE=True
REQUIRE_AUTH=True
API_DEBUG=False
JWT_SECRET_KEY=your-strong-random-secret
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

## 📚 Documentation

- **[Database Setup Guide](DATABASE_SETUP.md)** - PostgreSQL configuration
- **[Custom Prompts Guide](CUSTOM_PROMPTS.md)** - Customize AI behavior
- **[API Documentation](http://localhost:5000/docs)** - Interactive Swagger UI

## 🔒 Security

- ✅ JWT Bearer token authentication
- ✅ bcrypt password hashing
- ✅ Rate limiting per IP/user
- ✅ SQL injection protection (SQLAlchemy ORM)
- ✅ CORS configuration
- ✅ Input validation (Pydantic)

**Before deploying to production:**
1. Change `JWT_SECRET_KEY` to a strong random string
2. Set `REQUIRE_AUTH=True`
3. Limit `CORS_ORIGINS` to your domain
4. Enable HTTPS/SSL
5. Use strong database passwords

## 🐳 Docker Deployment

### Docker Compose (Recommended)

```bash
# Start all services (app, PostgreSQL, Redis)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Standalone Docker

```bash
# Build image
docker build -t interview-copilot .

# Run container
docker run -d \
  -p 5000:5000 \
  -e GEMINI_API_KEY=your_key \
  -e USE_DATABASE=False \
  interview-copilot
```

## ☁️ Cloud Deployment

### Railway.app (Easiest)

```bash
npm install -g @railway/cli
railway login
railway init
railway add postgresql
railway add redis
railway variables set GEMINI_API_KEY=xxx
railway up
```

### Google Cloud Run

```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/interview-copilot
gcloud run deploy interview-copilot \
  --image gcr.io/PROJECT_ID/interview-copilot \
  --platform managed \
  --region us-central1 \
  --set-env-vars "GEMINI_API_KEY=xxx,..."
```

See [deployment docs](docs/deployment.md) for more options.

## 🔌 API Endpoints

### Authentication

```bash
# Register user
POST /api/auth/register
{
  "email": "user@example.com",
  "password": "securepassword",
  "full_name": "John Doe"
}

# Login
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "securepassword"
}

# Get current user
GET /api/auth/me
Authorization: Bearer <token>
```

### Core Features

```bash
# Transcribe audio
POST /api/transcribe
{
  "audio": "base64_encoded_audio",
  "language": "pl"
}

# Generate answer
POST /api/generate
{
  "question": "What is your experience?",
  "context": {
    "cv": "...",
    "company": "Google",
    "position": "Senior Engineer",
    "custom_system_prompt": "Optional custom prompt"
  }
}

# Process audio (transcribe + detect + generate)
POST /api/process_audio
{
  "audio": [0.1, 0.2, ...],
  "sampleRate": 16000
}

# Update context
POST /api/context
{
  "cv": "Your CV content",
  "company": "Company Name",
  "position": "Position Title",
  "custom_system_prompt": "Custom AI instructions"
}

# Get history
GET /api/history
```

### WebSocket

```javascript
const ws = new WebSocket('ws://localhost:5000/ws/audio');

// Send audio
ws.send(JSON.stringify({
  type: 'audio',
  data: audioFloatArray
}));

// Receive responses
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  // msg.type: 'transcription', 'question_detected', 'answer'
};
```

## 📊 Monitoring

### Prometheus Metrics

Available at `/metrics`:

- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `transcriptions_total` - Total transcriptions
- `generations_total` - Total answer generations
- `questions_detected_total` - Questions detected
- `errors_total` - Errors by type

### Structured Logs

JSON formatted logs with context:

```json
{
  "@timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "message": "Request completed",
  "method": "POST",
  "url": "/api/process_audio",
  "status_code": 200,
  "duration": "2.45s"
}
```

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# With coverage
pytest --cov=. --cov-report=html
```

## 📈 Performance

Typical response times:
- Transcription (3s audio): 2-5s
- Answer generation: 1-3s
- Question detection: <100ms
- End-to-end: 3-8s

Bottlenecks:
- Whisper transcription (CPU-bound)
- Gemini API latency

Optimizations:
- Use GPU for Whisper
- Cache frequently asked questions
- Redis for rate limit storage

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/)
- [Google Gemini](https://ai.google.dev/)
- [OpenAI Whisper](https://github.com/openai/whisper)

## 📞 Support

- Issues: [GitHub Issues](https://github.com/mikoajp/inteview-copilot/issues)
- Documentation: [docs/](docs/)

---

**Built with ❤️ for better interview preparation**
