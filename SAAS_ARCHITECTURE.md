# SaaS Transformation Architecture

## Overview

This document describes the architectural changes made to transform the Invoice Reconciliation System from an internal tool to a multi-tenant SaaS application.

## Architecture Comparison

### Before: Internal Tool
```
Single User → Gradio UI → File System → Local Processing → Excel Output
```

**Limitations:**
- No authentication
- No multi-tenancy
- File-based storage
- Single-user access
- No API
- No audit trail

### After: SaaS Application
```
Multiple Users → API Gateway → Authentication → Multi-Tenant Database
                      ↓              ↓
                 Background Jobs  Tenant Isolation
                      ↓              ↓
                 Processing Queue → Report Storage
```

**Features:**
- ✅ JWT authentication
- ✅ Multi-tenant database
- ✅ RESTful API
- ✅ Role-based access control
- ✅ Audit logging
- ✅ Background job processing
- ✅ Usage tracking

## Key Components

### 1. Configuration Layer (`saas_config/`)

**Purpose:** Environment-based configuration with security settings.

**Files:**
- `settings.py` - Pydantic settings with environment variables
- `database.py` - SQLAlchemy engine and session management
- `security.py` - JWT, password hashing, API keys

**Key Features:**
- Environment-specific configuration (dev/staging/prod)
- Database connection pooling
- Secure credential management
- CORS configuration

### 2. Data Models (`saas_models/`)

**Purpose:** Multi-tenant database schema with tenant isolation.

**Models:**
- `Tenant` - Organizations with subscription tiers
- `User` - Users with role-based access
- `ReconciliationJob` - Job tracking with tenant isolation
- `Invoice` - Persistent invoice storage
- `AuditLog` - Complete audit trail

**Key Features:**
- UUID primary keys
- Tenant-scoped queries
- JSONB for flexible data
- Comprehensive indexing
- Foreign key relationships

### 3. API Layer (`saas_api/`)

**Purpose:** RESTful API with authentication and tenant isolation.

**Endpoints:**

#### Authentication (`/api/v1/auth`)
- `POST /register` - Register new tenant + admin user
- `POST /login` - JWT token authentication
- `POST /api-key` - Generate API key

#### Reconciliations (`/api/v1/reconciliations`)
- `POST /` - Create reconciliation job
- `GET /{job_id}` - Get job status
- `GET /` - List jobs (paginated)
- `GET /stats/summary` - Job statistics
- `DELETE /{job_id}` - Delete job

**Key Features:**
- JWT bearer authentication
- API key support
- Tenant context injection
- Role-based authorization
- Request validation with Pydantic
- Comprehensive error handling

### 4. Background Processing

**Purpose:** Async job processing without blocking API.

**Current:** FastAPI BackgroundTasks (simple, same process)
**Future:** Celery + Redis (scalable, distributed)

**Process:**
1. Upload files → S3/Local storage
2. Create job record
3. Queue for processing
4. Worker processes job
5. Store results
6. Update job status

## Multi-Tenancy Design

### Tenant Isolation

**Database Level:**
```sql
-- Every query filters by tenant_id
SELECT * FROM reconciliation_jobs 
WHERE tenant_id = :current_tenant_id;
```

**Application Level:**
```python
# Tenant context middleware
@app.middleware("http")
async def tenant_middleware(request, call_next):
    user = get_user_from_token(request)
    tenant_context.set_tenant_id(user.tenant_id)
    return await call_next(request)
```

**Storage Level:**
```
uploads/
├── {tenant_id}/
│   ├── {job_id}/
│   │   ├── evd_file.xlsx
│   │   ├── pdf_file.pdf
│   │   └── report.xlsx
```

### Subscription Tiers

| Tier | Jobs/Month | Features |
|------|-----------|----------|
| **Free** | 100 | Basic reconciliation |
| **Pro** | 1,000 | + API access, priority support |
| **Enterprise** | Unlimited | + Custom integrations, SLA |

## Security Features

### Authentication
- JWT tokens with expiration
- API keys for programmatic access
- Password hashing with bcrypt
- Refresh token support (planned)

### Authorization
- Role-based access control (RBAC)
- Tenant isolation at all layers
- Row-level security

### Data Protection
- Tenant data isolation
- Encrypted passwords
- Secure file storage
- Audit logging

## API Examples

### 1. Register New Tenant

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@company.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "organization_name": "Acme Corp"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
  "role": "admin"
}
```

### 2. Create Reconciliation Job

```bash
curl -X POST http://localhost:8000/api/v1/reconciliations \
  -H "Authorization: Bearer {access_token}" \
  -F "evd_file=@evd_data.xlsx" \
  -F "pdf_file=@invoice.pdf"
```

Response:
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "status": "pending",
  "created_at": "2026-02-25T15:00:00Z",
  "evd_invoice_count": null,
  "pdf_invoice_count": null
}
```

### 3. Check Job Status

```bash
curl -X GET http://localhost:8000/api/v1/reconciliations/{job_id} \
  -H "Authorization: Bearer {access_token}"
```

Response:
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "status": "completed",
  "created_at": "2026-02-25T15:00:00Z",
  "evd_invoice_count": 25,
  "pdf_invoice_count": 24,
  "matches_count": 20,
  "mismatches_count": 4,
  "match_rate": 80.0,
  "report_file_path": "/reports/770e8400.../report.xlsx"
}
```

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐
│   Tenant    │
│ ----------- │
│ id (PK)     │
│ name        │◄───────┐
│ email       │        │
│ tier        │        │
└─────────────┘        │
                       │
       ┌───────────────┘
       │
       │
┌──────▼──────┐       ┌──────────────────┐
│    User     │       │ ReconciliationJob │
│ ----------- │       │ ---------------   │
│ id (PK)     │       │ id (PK)           │
│ tenant_id   ├──────►│ tenant_id (FK)    │
│ email       │       │ user_id (FK)      │
│ role        │       │ status            │
│ password    │       │ evd_file_path     │
│ api_key     │       │ pdf_file_path     │
└─────────────┘       │ result_data       │
                      └──────┬────────────┘
                             │
                             │
                      ┌──────▼─────┐
                      │  Invoice   │
                      │ ---------- │
                      │ id (PK)    │
                      │ tenant_id  │
                      │ job_id     │
                      │ invoice_#  │
                      │ amount     │
                      │ vendor     │
                      └────────────┘
```

## Migration from Internal Tool

### Step 1: Database Setup

```bash
# Install PostgreSQL
# Create database
createdb invoice_reconciliation

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost/invoice_reconciliation"
export SECRET_KEY="your-secret-key"
export JWT_SECRET_KEY="your-jwt-secret"
```

### Step 2: Run Migrations

```bash
# Initialize database
python -m saas_api.main

# Or use Alembic
alembic upgrade head
```

### Step 3: Start API Server

```bash
# Development
python -m saas_api.main

# Production with Gunicorn
gunicorn saas_api.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Step 4: Register First Tenant

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{...}'
```

## Deployment Considerations

### Environment Variables

Required:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Application secret
- `JWT_SECRET_KEY` - JWT signing key

Optional:
- `ENVIRONMENT` - dev/staging/production
- `DEBUG` - Enable debug mode
- `CORS_ORIGINS` - Allowed origins
- `REDIS_URL` - Redis for Celery (production)

### Production Checklist

- [ ] Use PostgreSQL (not SQLite)
- [ ] Set strong SECRET_KEY and JWT_SECRET_KEY
- [ ] Disable DEBUG mode
- [ ] Configure CORS properly
- [ ] Use HTTPS
- [ ] Set up Celery workers
- [ ] Configure Redis for job queue
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure backup strategy
- [ ] Set up log aggregation
- [ ] Configure rate limiting
- [ ] Set up alerting

## Future Enhancements

### Phase 2: Scalability
- [ ] Celery for background jobs
- [ ] Redis for caching
- [ ] S3 for file storage
- [ ] CDN for report delivery
- [ ] Database read replicas
- [ ] Load balancing

### Phase 3: Features
- [ ] Webhook notifications
- [ ] Email notifications
- [ ] Scheduled jobs
- [ ] Batch API endpoints
- [ ] Advanced analytics
- [ ] Custom reporting templates

### Phase 4: Enterprise
- [ ] SSO integration (SAML/OIDC)
- [ ] Advanced RBAC
- [ ] Custom workflows
- [ ] White-labeling
- [ ] Multi-region deployment
- [ ] Compliance certifications

## Backward Compatibility

The existing internal tool (`app.py`, `run_reconciliation.py`) continues to work unchanged. The new SaaS infrastructure is additive, not replacing.

**Internal Tool:** For local/single-user use
**SaaS API:** For multi-tenant cloud deployment

Both use the same core reconciliation logic from `reconciliation_project/`.

## Testing

```bash
# Install test dependencies
pip install -r requirements-saas.txt

# Run tests
pytest

# Run with coverage
pytest --cov=saas_api --cov=saas_models --cov=saas_config
```

## Support

For questions or issues:
- Documentation: This file + inline code comments
- Architecture: See ARCHITECTURE.md
- API Docs: http://localhost:8000/docs (when running)

---

**Version:** 2.0.0  
**Last Updated:** 2026-02-25
