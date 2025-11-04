# PostgreSQL Integration Guide - Interview Copilot

## ✅ TAK - Aplikacja ma pełną integrację z PostgreSQL!

System logowania i rejestracji użytkowników działa w **dwóch trybach**:
- **In-Memory Mode** (`USE_DATABASE=False`) - dane w RAM (dla developmentu)
- **PostgreSQL Mode** (`USE_DATABASE=True`) - trwałe przechowywanie (dla produkcji)

---

## 📊 ARCHITEKTURA BAZY DANYCH

### **Tabela: users**
```sql
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,  -- bcrypt hash
    full_name VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
```

**Relacje:**
- `1 user` → `N interview_contexts` (konteksty rozmów)
- `1 user` → `N interview_history` (historia Q&A)

### **Tabela: interview_contexts**
```sql
CREATE TABLE interview_contexts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id) ON DELETE CASCADE,
    cv TEXT DEFAULT '',
    company VARCHAR DEFAULT '',
    position VARCHAR DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_contexts_user_id ON interview_contexts(user_id);
```

**Przechowuje:**
- CV użytkownika (max 50KB po walidacji)
- Nazwa firmy (max 200 chars)
- Stanowisko (max 200 chars)
- Custom system prompt (max 10KB)

### **Tabela: interview_history**
```sql
CREATE TABLE interview_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR REFERENCES users(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_history_user_id ON interview_history(user_id);
CREATE INDEX idx_history_created_at ON interview_history(created_at);
```

**Przechowuje:**
- Pytania zadane podczas rozmowy
- Odpowiedzi wygenerowane przez AI
- Timestamp każdej interakcji

---

## 🔄 JAK DZIAŁA REJESTRACJA I LOGOWANIE

### **1. Rejestracja Użytkownika**

**Endpoint:** `POST /api/auth/register`

**Request:**
```json
{
  "email": "jan.kowalski@example.com",
  "password": "SecurePassword123!",
  "full_name": "Jan Kowalski"
}
```

**Flow:**

```
1. Walidacja email (EmailStr - Pydantic)
   ↓
2. Sprawdzenie czy email już istnieje
   ├─ USE_DATABASE=True  → SELECT * FROM users WHERE email=...
   └─ USE_DATABASE=False → Sprawdzenie w users_db dict
   ↓
3. Hashowanie hasła (bcrypt)
   - Cost factor: auto (domyślnie 12)
   - Salt: auto-generated per user
   ↓
4. Utworzenie użytkownika
   ├─ USE_DATABASE=True  → INSERT INTO users (id, email, hashed_password, ...)
   └─ USE_DATABASE=False → Zapis w users_db[email] = {...}
   ↓
5. Generowanie JWT token
   - Payload: {"sub": user_id, "email": email, "exp": ...}
   - Algorytm: HS256 (HMAC SHA-256)
   - Ważność: 24h (configurable)
   ↓
6. Zwrócenie tokena + danych użytkownika
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "user_1730761234.567",
    "email": "jan.kowalski@example.com",
    "full_name": "Jan Kowalski",
    "is_active": true,
    "created_at": "2025-11-04T20:00:34.567000"
  }
}
```

### **2. Logowanie Użytkownika**

**Endpoint:** `POST /api/auth/login`

**Request:**
```json
{
  "email": "jan.kowalski@example.com",
  "password": "SecurePassword123!"
}
```

**Flow:**

```
1. Pobranie użytkownika z bazy
   ├─ USE_DATABASE=True  → SELECT * FROM users WHERE email=...
   └─ USE_DATABASE=False → users_db.get(email)
   ↓
2. Sprawdzenie czy użytkownik istnieje
   ├─ NIE → 401 Unauthorized "Incorrect email or password"
   └─ TAK → Kontynuuj
   ↓
3. Weryfikacja hasła
   - bcrypt.verify(plain_password, hashed_password)
   ├─ FAIL → 401 Unauthorized
   └─ OK → Kontynuuj
   ↓
4. Generowanie JWT token
   - Payload: {"sub": user_id, "email": email, "exp": ...}
   ↓
5. Zwrócenie tokena + danych użytkownika
```

**Response:** (taki sam jak przy rejestracji)

### **3. Autoryzacja z JWT Token**

**Każdy chroniony endpoint wymaga:**

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Flow weryfikacji:**
```
1. Ekstrakcja tokena z nagłówka Authorization
   ↓
2. Dekodowanie JWT
   - Weryfikacja sygnatury (HMAC SHA-256)
   - Sprawdzenie expiration date
   ├─ INVALID → 401 Unauthorized
   └─ VALID → Kontynuuj
   ↓
3. Pobranie user_id z payload
   ↓
4. Request processing z user context
```

---

## 🔐 BEZPIECZEŃSTWO

### **1. Hashowanie Haseł (bcrypt)**

✅ **Używane:**
- Algorytm: bcrypt (Blowfish cipher)
- Cost factor: 12 rounds (auto przez passlib)
- Salt: Unikalny per użytkownik (auto-generated)

❌ **NIE używane:**
- Plain text storage
- MD5/SHA1 (słabe hashe)
- Shared salts

**Przykład:**
```python
plain_password = "MyPassword123"
hashed = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyqXK1l.0rHm"
```

### **2. JWT Security**

✅ **Implementacja:**
- Algorytm: HS256 (HMAC + SHA-256)
- Secret Key: Min 32 chars (enforced w config)
- Expiration: 24h (1440 minutes)
- Payload: `{"sub": user_id, "exp": timestamp}`

⚠️ **Ważne:**
```bash
# NIGDY nie używaj domyślnego secret!
JWT_SECRET_KEY=your-secret-key-change-in-production  # ❌ REJECTED!

# Wygeneruj silny:
openssl rand -hex 32
JWT_SECRET_KEY=a7f3c2b9e8d4f1a6c3e9b2d7f4a1c8e5...  # ✅ ACCEPTED
```

### **3. Email Validation**

✅ **Pydantic EmailStr:**
- Format validation (RFC 5322)
- Domain validation
- Automatic normalization

```python
class UserCreate(BaseModel):
    email: EmailStr  # ✅ Waliduje format
    password: str
```

### **4. SQL Injection Protection**

✅ **SQLAlchemy ORM:**
- Parametryzowane zapytania
- Auto-escaping
- Type safety

```python
# ✅ BEZPIECZNE (ORM)
db.query(User).filter(User.email == email).first()

# ❌ NIEBEZPIECZNE (raw SQL - NIE używane!)
db.execute(f"SELECT * FROM users WHERE email='{email}'")
```

---

## 🚀 UŻYCIE W APLIKACJI

### **Tryb 1: Development (bez bazy)**

```bash
# .env
USE_DATABASE=False
REQUIRE_AUTH=True  # Można wyłączyć dla testów
```

**Charakterystyka:**
- ✅ Szybki start (0 dependencies)
- ✅ Nie wymaga PostgreSQL
- ⚠️ Dane tylko w RAM (gubią się po restarcie)
- ⚠️ Nie skaluje się (single instance only)

**Użycie:**
```bash
# Start aplikacji
uvicorn app:app --reload

# Zarejestruj użytkownika
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123","full_name":"Test User"}'

# Po restarcie - użytkownik znika! ⚠️
```

### **Tryb 2: Production (z PostgreSQL)**

```bash
# .env
USE_DATABASE=True
DATABASE_URL=postgresql://user:password@localhost:5432/interview_copilot
REQUIRE_AUTH=True
JWT_SECRET_KEY=<strong-64-char-secret>
```

**Charakterystyka:**
- ✅ Trwałe przechowywanie
- ✅ Skalowalność (multi-instance)
- ✅ Backupy możliwe
- ✅ Production-ready
- ⚠️ Wymaga PostgreSQL instance

**Użycie:**
```bash
# 1. Uruchom PostgreSQL (Docker)
docker run -d \
  --name interview-db \
  -e POSTGRES_DB=interview_copilot \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15-alpine

# 2. Start aplikacji
uvicorn app:app --reload

# Przy starcie - tabele utworzone automatycznie! ✅
# ✅ Database tables created

# 3. Zarejestruj użytkownika
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123","full_name":"Test User"}'

# 4. Restart aplikacji
# Użytkownik nadal istnieje! ✅

# 5. Zaloguj się
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}'
```

---

## 📝 PRZYKŁADY UŻYCIA API

### **1. Pełny flow - Rejestracja → Logowanie → Użycie**

```bash
# 1. Rejestracja
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jan@example.com",
    "password": "MySecurePass123!",
    "full_name": "Jan Kowalski"
  }')

echo $REGISTER_RESPONSE
# {"access_token":"eyJ...","token_type":"bearer","user":{...}}

# Wyciągnij token
TOKEN=$(echo $REGISTER_RESPONSE | jq -r '.access_token')

# 2. Sprawdź swoje dane
curl -X GET http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"

# Response:
# {
#   "id": "user_1730761234.567",
#   "email": "jan@example.com",
#   "full_name": "Jan Kowalski",
#   "is_active": true,
#   "created_at": "2025-11-04T20:00:34.567000"
# }

# 3. Ustaw kontekst rozmowy
curl -X POST http://localhost:5000/api/context \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cv": "Senior Python Developer z 5-letnim doświadczeniem...",
    "company": "Google",
    "position": "Senior Backend Engineer"
  }'

# 4. Przetwórz pytanie rekrutera
curl -X POST http://localhost:5000/api/process_audio \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "audio": [...],  // Float32Array
    "sampleRate": 16000
  }'

# Response:
# {
#   "success": true,
#   "question": "Opowiedz mi o swoim doświadczeniu z Pythonem",
#   "answer": "Mam 5 lat doświadczenia w Python development...",
#   "timestamp": "2025-11-04T20:05:00.123456"
# }

# 5. Pobierz historię
curl -X GET http://localhost:5000/api/history \
  -H "Authorization: Bearer $TOKEN"

# Response:
# {
#   "success": true,
#   "history": [
#     {
#       "question": "Opowiedz mi o swoim doświadczeniu z Pythonem",
#       "answer": "Mam 5 lat doświadczenia...",
#       "timestamp": "2025-11-04T20:05:00.123456"
#     }
#   ]
# }
```

### **2. WebSocket z autentykacją**

```javascript
// Frontend - JavaScript/TypeScript
const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...";

// Połącz z tokenem w query params
const ws = new WebSocket(`ws://localhost:5000/ws/audio?token=${token}`);

ws.onopen = () => {
  console.log("Connected!");

  // Wyślij audio chunk
  ws.send(JSON.stringify({
    type: "audio",
    data: audioFloat32Array
  }));
};

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);

  switch(response.type) {
    case "transcription":
      console.log("Transkrypcja:", response.text);
      break;

    case "question_detected":
      console.log("Wykryto pytanie:", response.question);
      break;

    case "answer":
      console.log("Sugestia odpowiedzi:", response.answer);
      displayAnswer(response.answer);
      break;

    case "error":
      console.error("Błąd:", response.message);
      break;
  }
};

ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};
```

---

## 🗄️ OPERACJE BAZODANOWE

### **Dostępne funkcje (db_operations.py):**

```python
# Użytkownicy
create_user_db(db, user_id, email, hashed_password, full_name)
get_user_by_email(db, email)
get_user_by_id(db, user_id)

# Kontekst rozmowy
get_context(db, user_id) → Context
update_context(db, user_id, cv, company, position)

# Historia Q&A
add_history_entry(db, user_id, question, answer)
get_history(db, user_id, limit=100) → List[Dict]
clear_history(db, user_id) → int  # Liczba usuniętych wpisów
```

### **Przykład użycia w kodzie:**

```python
from database import get_db
from db_operations import create_user_db, get_user_by_email

# Dependency injection FastAPI
def my_endpoint(db: Session = Depends(get_db)):
    # Sprawdź czy użytkownik istnieje
    user = get_user_by_email(db, "jan@example.com")

    if user:
        print(f"Użytkownik {user.email} istnieje!")
        print(f"ID: {user.id}")
        print(f"Utworzony: {user.created_at}")
```

---

## 🔧 KONFIGURACJA RAILWAY Z POSTGRESQL

### **Krok 1: Dodaj PostgreSQL w Railway**

1. Otwórz Railway Dashboard
2. Kliknij **"New Service"** → **"Database"** → **"PostgreSQL"**
3. Railway automatycznie utworzy bazę i ustawi `DATABASE_URL`

### **Krok 2: Zaktualizuj zmienne środowiskowe**

```bash
# Railway automatycznie ustawi:
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Ty ustaw tylko:
USE_DATABASE=True
```

### **Krok 3: Deploy**

Railway zredeploy-uje aplikację i:
- ✅ Automatycznie utworzy tabele (`init_db()` przy starcie)
- ✅ Połączy się z PostgreSQL
- ✅ Użytkownicy będą zapisywani w bazie

### **Weryfikacja:**

```bash
# Health check powinien pokazać DB connection
curl https://twoja-app.up.railway.app/api/health

# Zarejestruj użytkownika
curl -X POST https://twoja-app.up.railway.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@railway.com",
    "password": "RailwayTest123",
    "full_name": "Railway User"
  }'

# Restart aplikacji w Railway Dashboard
# ... wait for restart ...

# Zaloguj się (użytkownik nadal istnieje!)
curl -X POST https://twoja-app.up.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@railway.com",
    "password": "RailwayTest123"
  }'

# ✅ Sukces = PostgreSQL działa!
```

---

## 📊 MONITORING

### **Prometheus Metrics:**

```bash
# Liczba rejestracji/logowań
curl http://localhost:5000/metrics | grep auth

# Przykładowe metryki:
request_count{method="POST",endpoint="/api/auth/register",status="200"} 15
request_count{method="POST",endpoint="/api/auth/login",status="200"} 42
request_count{method="POST",endpoint="/api/auth/login",status="401"} 3
error_count{error_type="registration_failed",endpoint="/api/auth/register"} 2
error_count{error_type="login_failed",endpoint="/api/auth/login"} 3
```

### **Structured Logs:**

```json
{
  "timestamp": "2025-11-04T20:00:34.567Z",
  "level": "INFO",
  "message": "User registration attempt: jan@example.com",
  "email": "jan@example.com"
}

{
  "timestamp": "2025-11-04T20:00:35.123Z",
  "level": "INFO",
  "message": "User registered successfully: jan@example.com",
  "email": "jan@example.com"
}

{
  "timestamp": "2025-11-04T20:01:12.789Z",
  "level": "INFO",
  "message": "Login attempt: jan@example.com",
  "email": "jan@example.com"
}

{
  "timestamp": "2025-11-04T20:01:13.012Z",
  "level": "INFO",
  "message": "Login successful: jan@example.com",
  "email": "jan@example.com"
}
```

---

## ❓ FAQ

### **Q: Czy mogę migrować z in-memory do PostgreSQL?**
A: Nie automatycznie. Użytkownicy z in-memory są gubieni po restarcie. Po włączeniu PostgreSQL, użytkownicy muszą się zarejestrować ponownie.

### **Q: Czy hasła są bezpieczne?**
A: TAK. Używamy bcrypt z auto-generated salts. Plain text hasła nigdy nie są przechowywane.

### **Q: Co się stanie jeśli PostgreSQL padnie?**
A: Aplikacja zwróci 500 errors dla endpointów wymagających DB. Health check pokaże "unhealthy". Rozważ fallback do in-memory lub circuit breaker.

### **Q: Czy mogę używać innych baz (MySQL, MongoDB)?**
A: Kod używa SQLAlchemy, więc MySQL/MariaDB będzie działać po zmianie DATABASE_URL. MongoDB wymagałoby przepisania ORM layer.

### **Q: Jak zresetować hasło użytkownika?**
A: Endpoint nie jest zaimplementowany. Możesz dodać:
```python
@app.post("/api/auth/reset-password")
async def reset_password(email: EmailStr, new_password: str, db: Session = Depends(get_db)):
    # Implementation here
```

### **Q: Czy użytkownicy mogą się wylogować?**
A: JWT są stateless - "wylogowanie" odbywa się client-side (usunięcie tokena). Dla true logout, potrzeba blacklist tokenów w Redis.

---

## 🎯 PODSUMOWANIE

✅ **Aplikacja MA pełną integrację PostgreSQL:**
- System rejestracji użytkowników
- System logowania z JWT
- Przechowywanie kontekstu rozmów
- Historia pytań i odpowiedzi
- Bezpieczne hashowanie haseł (bcrypt)
- Email validation
- Dual-mode: in-memory + PostgreSQL

✅ **Gotowe do użycia:**
- Railway (+ dodaj PostgreSQL service)
- Render
- Heroku
- Docker Compose (postgres service included)
- Lokalne PostgreSQL

✅ **Production-ready security:**
- bcrypt password hashing
- JWT with strong secret enforcement
- SQL injection protection (ORM)
- Email validation
- Input size limits

---

Masz pytania o konkretny aspekt integracji? Mogę wyjaśnić szczegóły!
