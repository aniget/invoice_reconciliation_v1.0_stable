# Invoice Reconciliation SaaS - Quick Start Guide

## 🚀 What's New in v2.0?

The Invoice Reconciliation System has been transformed from an internal tool to a **multi-tenant SaaS application** with:

- ✅ **Multi-tenancy** - Multiple organizations with isolated data
- ✅ **Authentication** - JWT tokens + API keys
- ✅ **REST API** - Comprehensive API with OpenAPI docs
- ✅ **Database** - PostgreSQL with full audit trail
- ✅ **Role-Based Access** - Admin, Manager, Viewer roles
- ✅ **Background Jobs** - Async processing
- ✅ **Usage Tracking** - Subscription tiers and limits
- ✅ **Production-Ready** - Scalable architecture

**Important:** The original internal tool (v1.0) still works! See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [API Endpoints](#api-endpoints)
4. [Configuration](#configuration)
5. [Deployment](#deployment)
6. [Examples](#examples)

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 13+ (or SQLite for development)
- Redis (optional, for Celery)

### 1. Installation

```bash
# Clone repository
git clone <repository-url>
cd invoice_reconciliation_v1.0_stable

# Run setup script
./setup_saas.sh
```

The setup script will:
- Create virtual environment
- Install dependencies
- Generate secure keys
- Create `.env` file
- Initialize database
- Create storage directories

### 2. Start API Server

```bash
# Activate virtual environment
source venv/bin/activate

# Start server
python -m saas_api.main
```

Server starts at: `http://localhost:8000`

### 3. Access API Documentation

Visit: `http://localhost:8000/docs`

Interactive Swagger UI with all endpoints documented.

### 4. Register Your First Tenant

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@company.com",
    "password": "SecurePassword123!",
    "first_name": "John",
    "last_name": "Doe",
    "organization_name": "Acme Corporation"
  }'
```

Response includes your JWT access token.

## Architecture Overview

### System Design

```
┌─────────────────────────────────────────────────────────┐
│                   Client Applications                    │
│              (Web UI, Mobile, Scripts)                   │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────┐
│                     FastAPI Server                        │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │   Auth      │  │ Reconciliation│  │   Health       │  │
│  │  Endpoints  │  │   Endpoints   │  │   Endpoints    │  │
│  └─────────────┘  └──────────────┘  └────────────────┘  │
└───────────────────────┬───────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  PostgreSQL  │ │  Background  │ │File Storage  │
│   Database   │ │    Jobs      │ │ (Uploads)    │
└──────────────┘ └──────────────┘ └──────────────┘
```

### Key Components

1. **Configuration Layer** (`saas_config/`)
   - Environment-based settings
   - Database connection management
   - Security utilities (JWT, password hashing)

2. **Data Models** (`saas_models/`)
   - `Tenant` - Organizations
   - `User` - Users with RBAC
   - `ReconciliationJob` - Processing jobs
   - `Invoice` - Invoice records
   - `AuditLog` - Activity tracking

3. **API Layer** (`saas_api/`)
   - Authentication endpoints
   - Reconciliation endpoints
   - Job management
   - Health checks

4. **Core Processing** (existing)
   - EVD extraction
   - PDF extraction
   - Reconciliation engine
   - Report generation

## API Endpoints

### Authentication

#### Register Tenant
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "admin@company.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "organization_name": "Acme Corp"
}
```

#### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@company.com",
  "password": "SecurePass123!"
}
```

#### Generate API Key
```http
POST /api/v1/auth/api-key
Authorization: Bearer {access_token}
```

### Reconciliation

#### Create Job
```http
POST /api/v1/reconciliations
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

evd_file: <excel file>
pdf_file: <pdf file>
```

#### Get Job Status
```http
GET /api/v1/reconciliations/{job_id}
Authorization: Bearer {access_token}
```

#### List Jobs
```http
GET /api/v1/reconciliations?page=1&page_size=20&status_filter=completed
Authorization: Bearer {access_token}
```

#### Get Statistics
```http
GET /api/v1/reconciliations/stats/summary
Authorization: Bearer {access_token}
```

#### Delete Job
```http
DELETE /api/v1/reconciliations/{job_id}
Authorization: Bearer {access_token}
```

### Health Check
```http
GET /health
```

## Configuration

### Environment Variables

Create `.env` file (or use `.env.example` as template):

```env
# Environment
ENVIRONMENT=development
DEBUG=True

# Database
DATABASE_URL=postgresql://user:pass@localhost/invoice_reconciliation

# Security
SECRET_KEY=your-random-secret-key
JWT_SECRET_KEY=your-random-jwt-secret
JWT_EXPIRATION_MINUTES=1440

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# Storage
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=50

# Features
ENABLE_OCR=False
```

### Database Options

**Development (SQLite):**
```env
DATABASE_URL=sqlite:///./invoice_reconciliation.db
```

**Production (PostgreSQL):**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/invoice_reconciliation
```

## Deployment

### Development

```bash
./setup_saas.sh
source venv/bin/activate
python -m saas_api.main
```

### Production

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for:
- PostgreSQL setup
- Nginx configuration
- SSL certificates
- Supervisor/systemd
- Celery workers
- Monitoring

Quick production start:

```bash
# Install dependencies
pip install gunicorn

# Run with Gunicorn
gunicorn saas_api.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## Examples

### Python Client

```python
import requests

# Base URL
BASE_URL = "http://localhost:8000/api/v1"

# 1. Register
response = requests.post(
    f"{BASE_URL}/auth/register",
    json={
        "email": "user@company.com",
        "password": "SecurePass123!",
        "first_name": "Jane",
        "last_name": "Smith",
        "organization_name": "Example Inc"
    }
)
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Create reconciliation job
files = {
    "evd_file": ("data.xlsx", open("data.xlsx", "rb")),
    "pdf_file": ("invoice.pdf", open("invoice.pdf", "rb"))
}
response = requests.post(
    f"{BASE_URL}/reconciliations",
    headers=headers,
    files=files
)
job_id = response.json()["id"]
print(f"Job created: {job_id}")

# 3. Check job status
import time
while True:
    response = requests.get(
        f"{BASE_URL}/reconciliations/{job_id}",
        headers=headers
    )
    job = response.json()
    print(f"Status: {job['status']}")
    
    if job["status"] in ["completed", "failed"]:
        break
    
    time.sleep(5)

# 4. Get statistics
response = requests.get(
    f"{BASE_URL}/reconciliations/stats/summary",
    headers=headers
)
stats = response.json()
print(f"Total jobs: {stats['total_jobs']}")
print(f"Match rate: {stats['completed']}/{stats['total_jobs']}")
```

### cURL Examples

```bash
# Store token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}' \
  | jq -r '.access_token')

# Create job
curl -X POST http://localhost:8000/api/v1/reconciliations \
  -H "Authorization: Bearer $TOKEN" \
  -F "evd_file=@data.xlsx" \
  -F "pdf_file=@invoice.pdf"

# List jobs
curl http://localhost:8000/api/v1/reconciliations \
  -H "Authorization: Bearer $TOKEN"

# Get stats
curl http://localhost:8000/api/v1/reconciliations/stats/summary \
  -H "Authorization: Bearer $TOKEN"
```

## Subscription Tiers

| Tier | Jobs/Month | API Access | Support | Price |
|------|-----------|------------|---------|-------|
| **Free** | 100 | ✅ | Community | $0 |
| **Pro** | 1,000 | ✅ | Email | $29/mo |
| **Enterprise** | Unlimited | ✅ | Priority | Contact |

Configure limits in `.env`:
```env
FREE_TIER_JOBS_PER_MONTH=100
PRO_TIER_JOBS_PER_MONTH=1000
```

## Security

### Authentication Methods

1. **JWT Tokens** - For user sessions
2. **API Keys** - For programmatic access

### Best Practices

- ✅ Use HTTPS in production
- ✅ Set strong SECRET_KEY and JWT_SECRET_KEY
- ✅ Enable rate limiting
- ✅ Regular security updates
- ✅ Monitor audit logs
- ✅ Use environment variables for secrets

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "environment": "production"
}
```

### Logs

```bash
# Application logs
tail -f logs/app.log

# Gunicorn logs (production)
tail -f logs/gunicorn_error.log
```

### Database Queries

```sql
-- Check tenant count
SELECT COUNT(*) FROM tenants WHERE is_active = true;

-- Check job statistics
SELECT status, COUNT(*) 
FROM reconciliation_jobs 
GROUP BY status;

-- Recent jobs
SELECT * FROM reconciliation_jobs 
ORDER BY created_at DESC 
LIMIT 10;
```

## Troubleshooting

### Common Issues

**"Module not found"**
```bash
pip install -r requirements-saas.txt
```

**"Database connection error"**
```bash
# Check DATABASE_URL in .env
# Ensure PostgreSQL is running
sudo systemctl status postgresql
```

**"Permission denied"**
```bash
chmod +x setup_saas.sh
```

**"Port already in use"**
```bash
# Change port in .env
API_PORT=8001
```

## Migration

### From Internal Tool (v1.0)

The SaaS version is **additive**, not replacing. Both can coexist:

- **Keep using v1.0:** `python app.py` (no changes needed)
- **Try v2.0 SaaS:** `./setup_saas.sh && python -m saas_api.main`

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed migration paths.

## Documentation

- **[SAAS_ARCHITECTURE.md](SAAS_ARCHITECTURE.md)** - Detailed architecture
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Production deployment
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Migration from v1.0
- **API Docs** - http://localhost:8000/docs (interactive)

## Support

### Resources
- API Documentation: http://localhost:8000/docs
- Architecture Guide: SAAS_ARCHITECTURE.md
- Deployment Guide: DEPLOYMENT_GUIDE.md

### Getting Help
- Check documentation
- Review logs
- Test with health endpoint
- Check database connectivity

## Roadmap

### Completed ✅
- Multi-tenant architecture
- JWT authentication
- REST API
- Database models
- Background processing
- Audit logging
- Documentation

### Next Steps 📋
- [ ] Celery workers for scalability
- [ ] React/Vue frontend
- [ ] Webhook notifications
- [ ] Advanced analytics
- [ ] SSO integration (SAML/OIDC)
- [ ] Kubernetes deployment

## License

MIT License - See LICENSE file

---

**Version:** 2.0.0  
**Status:** Production Ready  
**Architecture:** Multi-tenant SaaS  

**Need help?** Check the documentation or visit http://localhost:8000/docs
