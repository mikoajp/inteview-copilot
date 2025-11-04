# Railway Deployment Configuration Guide

## Environment Variables for Railway

### ✅ REQUIRED (Minimum to run)
```bash
GEMINI_API_KEY=your-gemini-api-key-here
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
```

### 🔧 RECOMMENDED (Production settings)
```bash
# API Configuration
API_DEBUG=False
API_HOST=0.0.0.0
# API_PORT - Railway sets this automatically via $PORT

# CORS - Update with your frontend domain
CORS_ORIGINS=*

# Authentication
REQUIRE_AUTH=True
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# AI Models
GEMINI_MODEL=gemini-2.0-flash-exp
WHISPER_MODEL=base
WHISPER_LANGUAGE=pl

# Rate Limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_STORAGE=memory
```

### 💾 OPTIONAL - Database (for OPTION 2/3)
```bash
USE_DATABASE=True
DATABASE_URL=${{Postgres.DATABASE_URL}}  # Auto-set by Railway when you add PostgreSQL
```

### 🔴 OPTIONAL - Redis (for OPTION 3)
```bash
RATE_LIMIT_STORAGE=redis
REDIS_URL=${{Redis.REDIS_URL}}  # Auto-set by Railway when you add Redis
```

---

## Quick Setup Commands

### Option 1: Basic (No Database)
```bash
railway variables set GEMINI_API_KEY="your-key"
railway variables set JWT_SECRET_KEY="$(openssl rand -hex 32)"
railway variables set API_DEBUG="False"
railway variables set REQUIRE_AUTH="True"
railway variables set USE_DATABASE="False"
railway variables set WHISPER_MODEL="base"
```

### Option 2: With PostgreSQL
```bash
# First, add PostgreSQL service in Railway Dashboard
# Then run:
railway variables set GEMINI_API_KEY="your-key"
railway variables set JWT_SECRET_KEY="$(openssl rand -hex 32)"
railway variables set API_DEBUG="False"
railway variables set REQUIRE_AUTH="True"
railway variables set USE_DATABASE="True"
railway variables set WHISPER_MODEL="base"
# DATABASE_URL is auto-set by Railway
```

### Option 3: Full Production (PostgreSQL + Redis)
```bash
# First, add PostgreSQL + Redis services in Railway Dashboard
# Then run:
railway variables set GEMINI_API_KEY="your-key"
railway variables set JWT_SECRET_KEY="$(openssl rand -hex 32)"
railway variables set API_DEBUG="False"
railway variables set REQUIRE_AUTH="True"
railway variables set USE_DATABASE="True"
railway variables set RATE_LIMIT_STORAGE="redis"
railway variables set WHISPER_MODEL="base"
# DATABASE_URL and REDIS_URL are auto-set by Railway
```

---

## Deployment Checklist

- [ ] Generate strong JWT_SECRET_KEY (minimum 32 characters)
- [ ] Get Gemini API key from Google AI Studio
- [ ] Set all required environment variables
- [ ] Choose Whisper model based on Railway plan (tiny/base for Starter)
- [ ] Add PostgreSQL service (if using OPTION 2/3)
- [ ] Add Redis service (if using OPTION 3)
- [ ] Update CORS_ORIGINS with your frontend domain
- [ ] Test health endpoint: `https://your-app.up.railway.app/api/health`
- [ ] Test authentication endpoints
- [ ] Monitor logs in Railway dashboard
- [ ] Check Prometheus metrics: `https://your-app.up.railway.app/metrics`

---

## Troubleshooting

### Issue: App crashes with "JWT_SECRET_KEY is too short"
**Solution:** Generate proper secret:
```bash
openssl rand -hex 32
railway variables set JWT_SECRET_KEY="<paste-output>"
```

### Issue: Out of memory errors
**Solution:**
- Use smaller Whisper model: `railway variables set WHISPER_MODEL="tiny"`
- Or upgrade Railway plan

### Issue: Database connection errors
**Solution:**
- Verify PostgreSQL service is running
- Check `DATABASE_URL` is set automatically
- Ensure `USE_DATABASE=True`

### Issue: Slow cold starts
**Solution:**
- Upgrade to paid Railway plan (no sleeping)
- Or accept 30-60s initial load time

### Issue: CORS errors from frontend
**Solution:**
```bash
railway variables set CORS_ORIGINS="https://your-frontend.com"
```

---

## Performance Optimization for Railway

1. **Whisper Model Selection:**
   - Starter plan ($5/mo): Use `tiny` or `base`
   - Developer plan ($20/mo): Use `small`

2. **Database Pooling:**
   - Already configured (pool_size=10, max_overflow=20)

3. **Rate Limiting:**
   - Memory storage OK for single instance
   - Use Redis for multiple instances

4. **Monitoring:**
   - Check Railway metrics dashboard
   - Access Prometheus metrics: `/metrics`
   - View structured logs in Railway dashboard

---

## Security Notes for Railway

✅ **Automatically secured:**
- HTTPS enabled by default
- Environment variables encrypted
- Isolated network for services

⚠️ **You must configure:**
- Strong JWT_SECRET_KEY (min 32 chars)
- Proper CORS_ORIGINS (not wildcard * in production)
- Gemini API key from trusted source

🔒 **Additional recommendations:**
- Enable Railway's IP allowlist if needed
- Regularly rotate JWT_SECRET_KEY
- Monitor authentication logs
- Set up alerts for error spikes

---

## Cost Estimation

### Option 1: Basic
- API Service: $5/mo (Starter plan)
- **Total: $5/mo**

### Option 2: With PostgreSQL
- API Service: $5/mo
- PostgreSQL: $5-10/mo (depends on storage)
- **Total: $10-15/mo**

### Option 3: Full Production
- API Service: $5-20/mo (depending on RAM needs)
- PostgreSQL: $5-10/mo
- Redis: $5/mo
- **Total: $15-35/mo**

### Free Trial
- $5 credit (lasts ~1 month for basic usage)
- Good for testing and MVP

---

## Next Steps After Deployment

1. **Monitor for 24 hours:**
   - Check Railway logs
   - Verify no crashes
   - Monitor memory usage

2. **Performance testing:**
   - Test transcription with real audio
   - Measure response times
   - Check cold start duration

3. **Security audit:**
   - Verify HTTPS is working
   - Test authentication flows
   - Check rate limiting

4. **Frontend integration:**
   - Update API URL in frontend
   - Test WebSocket connection with token
   - Verify CORS configuration

5. **Set up alerts:**
   - Railway notification settings
   - Error tracking (optional: Sentry)
   - Uptime monitoring (optional: UptimeRobot)

---

## Support & Resources

- Railway Docs: https://docs.railway.app/
- Railway Discord: https://discord.gg/railway
- Project GitHub: https://github.com/mikoajp/inteview-copilot
- API Documentation: `https://your-app.up.railway.app/docs`

---

Generated for Interview Copilot v2.0
Last updated: 2025-11-04
