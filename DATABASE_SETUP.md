# Database Setup Guide

This guide explains how to set up PostgreSQL database for Interview Copilot.

## Prerequisites

- PostgreSQL 12+ installed
- Python dependencies installed (`pip install -r requirements.txt`)

## Quick Start

### 1. Install PostgreSQL

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

#### macOS
```bash
brew install postgresql
brew services start postgresql
```

#### Windows
Download and install from [PostgreSQL official website](https://www.postgresql.org/download/windows/)

### 2. Create Database

```bash
# Switch to postgres user (Linux/macOS)
sudo -u postgres psql

# Or connect directly (if configured)
psql -U postgres

# Create database
CREATE DATABASE interview_copilot;

# Create user (optional)
CREATE USER interview_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE interview_copilot TO interview_user;

# Exit
\q
```

### 3. Configure Application

Edit `.env` file:

```env
USE_DATABASE=True
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/interview_copilot

# Or with custom user
DATABASE_URL=postgresql://interview_user:your_password@localhost:5432/interview_copilot
```

### 4. Initialize Database

The application will automatically create tables on startup. Just run:

```bash
python app.py
```

You should see:
```
✅ Database tables created
✅ Database connection successful
```

## Database Schema

### Tables

#### users
- `id` (String, Primary Key)
- `email` (String, Unique)
- `hashed_password` (String)
- `full_name` (String, Optional)
- `is_active` (Boolean)
- `created_at` (DateTime)
- `updated_at` (DateTime)

#### interview_contexts
- `id` (Integer, Primary Key, Auto-increment)
- `user_id` (String, Foreign Key → users.id)
- `cv` (Text)
- `company` (String)
- `position` (String)
- `created_at` (DateTime)
- `updated_at` (DateTime)

#### interview_history
- `id` (Integer, Primary Key, Auto-increment)
- `user_id` (String, Foreign Key → users.id)
- `question` (Text)
- `answer` (Text)
- `created_at` (DateTime)

## Docker Setup

If using Docker with PostgreSQL:

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: interview_copilot
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build: .
    environment:
      USE_DATABASE: "True"
      DATABASE_URL: "postgresql://postgres:postgres@postgres:5432/interview_copilot"
    depends_on:
      - postgres
    ports:
      - "5000:5000"

volumes:
  postgres_data:
```

Run with:
```bash
docker-compose up -d
```

## Troubleshooting

### Connection refused
- Ensure PostgreSQL is running: `sudo systemctl status postgresql` (Linux)
- Check PostgreSQL port: `sudo netstat -plnt | grep 5432`

### Authentication failed
- Verify credentials in DATABASE_URL
- Check PostgreSQL authentication config: `/etc/postgresql/*/main/pg_hba.conf`

### Tables not created
- Check application logs for errors
- Manually create tables: See `db_models.py` for schema

### Migration Issues
- Drop all tables:
  ```sql
  DROP TABLE interview_history, interview_contexts, users CASCADE;
  ```
- Restart application to recreate tables

## Switching Between Modes

### In-Memory (Default)
```env
USE_DATABASE=False
```
Data stored in memory (lost on restart)

### PostgreSQL
```env
USE_DATABASE=True
DATABASE_URL=postgresql://...
```
Data persisted in PostgreSQL database

## Production Recommendations

1. **Use connection pooling** (already configured in `database.py`)
2. **Enable SSL** for database connections
3. **Regular backups**:
   ```bash
   pg_dump interview_copilot > backup.sql
   ```
4. **Use environment-specific credentials**
5. **Monitor connection pool usage**

## Security Notes

- Never commit `.env` file with real credentials
- Use strong passwords for database users
- Restrict database access to application server only
- Enable SSL/TLS for production databases
- Regular security updates for PostgreSQL
