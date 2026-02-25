# Migration from Internal Tool to SaaS

## Overview

This document describes how to migrate from the existing internal tool to the new multi-tenant SaaS architecture.

## What Changed?

### Architecture Evolution

**Before (v1.0 - Internal Tool):**
- Single-user Gradio web interface
- File-based storage (JSON, Excel)
- No authentication
- No multi-tenancy
- Manual file uploads only
- Synchronous processing

**After (v2.0 - SaaS Application):**
- Multi-tenant REST API
- Database storage (PostgreSQL)
- JWT authentication & RBAC
- Tenant isolation at all layers
- API + Web interface
- Async background processing

### Backward Compatibility

✅ **The internal tool (v1.0) continues to work unchanged!**

All existing files remain functional:
- `app.py` - Gradio web interface
- `run_reconciliation.py` - CLI workflow
- `evd_extraction_project/` - EVD extraction
- `pdf_extraction_project/` - PDF extraction
- `reconciliation_project/` - Core reconciliation logic

### New Components (v2.0)

**Added directories:**
- `saas_config/` - Configuration management
- `saas_models/` - Database models
- `saas_api/` - REST API endpoints
- `saas_workers/` - Background job processing (future)

**Added files:**
- `requirements-saas.txt` - SaaS dependencies
- `SAAS_ARCHITECTURE.md` - Architecture documentation
- `DEPLOYMENT_GUIDE.md` - Production deployment
- `.env.example` - Environment configuration template
- `setup_saas.sh` - Automated setup script

## Migration Paths

### Option 1: Keep Using Internal Tool (No Migration)

**When to use:**
- Single user or small team
- Local processing only
- No need for API access
- Manual file uploads work fine

**How to use:**
```bash
# Continue using as before
python app.py  # Web interface
# OR
python run_reconciliation.py  # CLI
```

**No changes required!**

### Option 2: Gradual Migration (Hybrid)

**When to use:**
- Testing SaaS features
- Keeping internal tool as backup
- Transitioning gradually

**Setup:**

1. **Install SaaS dependencies:**
```bash
pip install -r requirements-saas.txt
```

2. **Run setup:**
```bash
./setup_saas.sh
```

3. **Start API server (separate terminal):**
```bash
python -m saas_api.main
```

4. **Continue using internal tool:**
```bash
python app.py  # Still works!
```

**Result:** Both systems run independently.

### Option 3: Full SaaS Migration

**When to use:**
- Multi-tenant requirements
- API access needed
- Cloud deployment
- Multiple users/organizations

**Migration steps:**

1. **Setup infrastructure:**
```bash
# Install PostgreSQL
sudo apt install postgresql

# Create database
sudo -u postgres createdb invoice_reconciliation

# Set environment
export DATABASE_URL="postgresql://user:pass@localhost/invoice_reconciliation"
```

2. **Install and configure:**
```bash
./setup_saas.sh
```

3. **Initialize database:**
```bash
python -c "from saas_config import init_db; init_db()"
```

4. **Start API server:**
```bash
python -m saas_api.main
```

5. **Register tenants:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@company.com",
    "password": "SecurePass123!",
    "first_name": "Admin",
    "last_name": "User",
    "organization_name": "Company Name"
  }'
```

6. **Migrate existing data (optional):**
```python
# Script to import existing JSON files into database
from saas_config import get_db_context
from saas_models import Tenant, User, ReconciliationJob
import json

with get_db_context() as db:
    # Create tenant for existing data
    tenant = Tenant(name="legacy", email="legacy@company.com")
    db.add(tenant)
    db.flush()
    
    # Import historical jobs
    # ... import logic here
```

## Data Migration

### Existing Data Locations

**Internal Tool (v1.0):**
- EVD files: `input_evd/`
- PDF files: `input_pdf/`
- Results: `output/`
- Temp files: Gradio temp directory

**SaaS (v2.0):**
- Uploads: `uploads/{tenant_id}/{job_id}/`
- Reports: `reports/{tenant_id}/{job_id}/`
- Database: PostgreSQL tables
- Temp: `temp/`

### Migration Script (Optional)

Create `migrate_data.py`:

```python
"""
Migrate existing data to SaaS database.
Run after SaaS setup is complete.
"""

import json
from pathlib import Path
from datetime import datetime
from saas_config import get_db_context
from saas_models import Tenant, User, ReconciliationJob, JobStatus

def migrate_historical_data(evd_dir, pdf_dir, output_dir, tenant_id):
    """
    Import historical reconciliation data into SaaS database.
    
    Args:
        evd_dir: Path to EVD files
        pdf_dir: Path to PDF files
        output_dir: Path to output files
        tenant_id: Target tenant UUID
    """
    with get_db_context() as db:
        # Get tenant
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Get first admin user
        user = db.query(User).filter(
            User.tenant_id == tenant_id,
            User.role == "admin"
        ).first()
        
        # Process each EVD/PDF pair
        evd_files = list(Path(evd_dir).glob("*.json"))
        
        for evd_file in evd_files:
            # Load data
            with open(evd_file) as f:
                evd_data = json.load(f)
            
            # Create job record
            job = ReconciliationJob(
                tenant_id=tenant.id,
                user_id=user.id,
                status=JobStatus.COMPLETED,
                evd_data=evd_data,
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            db.add(job)
            
            print(f"Imported: {evd_file.name}")
        
        db.commit()
        print(f"Migration complete: {len(evd_files)} jobs imported")

# Usage:
# migrate_historical_data("input_evd", "input_pdf", "output", "tenant-uuid-here")
```

## API Access

### For Developers

**Authentication:**
```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "user@company.com", "password": "password"}
)
token = response.json()["access_token"]

# Use token
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "http://localhost:8000/api/v1/reconciliations",
    headers=headers
)
```

**Create job:**
```python
# Upload files
files = {
    "evd_file": open("data.xlsx", "rb"),
    "pdf_file": open("invoice.pdf", "rb")
}
response = requests.post(
    "http://localhost:8000/api/v1/reconciliations",
    headers=headers,
    files=files
)
job_id = response.json()["id"]

# Check status
response = requests.get(
    f"http://localhost:8000/api/v1/reconciliations/{job_id}",
    headers=headers
)
print(response.json()["status"])
```

### For End Users

**Web Interface (Future):**
- React/Vue frontend connecting to API
- Or enhanced Gradio with authentication
- Available in next release

**Current:** Use API directly or keep using internal tool.

## Configuration

### Environment Variables

**Development (.env):**
```env
ENVIRONMENT=development
DEBUG=True
DATABASE_URL=sqlite:///./invoice_reconciliation.db
```

**Production (.env):**
```env
ENVIRONMENT=production
DEBUG=False
DATABASE_URL=postgresql://user:pass@localhost/invoice_reconciliation
SECRET_KEY=random-secret-here
JWT_SECRET_KEY=random-jwt-secret-here
```

## Troubleshooting

### "Module not found" errors

```bash
# Make sure SaaS dependencies are installed
pip install -r requirements-saas.txt
```

### Database errors

```bash
# Reinitialize database
python -c "from saas_config import init_db; init_db()"
```

### Internal tool still works?

Yes! Internal tool (v1.0) is completely independent:
```bash
python app.py  # Works without any SaaS setup
```

## Feature Comparison

| Feature | Internal Tool (v1.0) | SaaS (v2.0) |
|---------|---------------------|------------|
| **User Interface** | Gradio web UI | REST API + (Future: React UI) |
| **Authentication** | None | JWT + API keys |
| **Multi-tenancy** | No | Yes |
| **Database** | No (files only) | PostgreSQL |
| **API Access** | No | Yes |
| **Background Jobs** | Synchronous | Async (BackgroundTasks) |
| **User Management** | N/A | Roles: admin, manager, viewer |
| **Audit Logging** | No | Yes |
| **Usage Tracking** | No | Yes (per tenant) |
| **Subscription Tiers** | N/A | Free, Pro, Enterprise |
| **Scalability** | Single instance | Horizontal scaling |
| **File Storage** | Local temp | Tenant-isolated directories |
| **Setup** | `python app.py` | `./setup_saas.sh` |

## Recommendations

**Use Internal Tool (v1.0) if:**
- ✅ Single user
- ✅ Local processing
- ✅ No API needed
- ✅ Simple use case

**Use SaaS (v2.0) if:**
- ✅ Multiple users/tenants
- ✅ API access required
- ✅ Cloud deployment
- ✅ User management needed
- ✅ Audit trail required
- ✅ Scalability important

**Both can coexist!** They share the same core reconciliation logic.

## Support

- **Internal Tool:** See `README.md`
- **SaaS:** See `SAAS_ARCHITECTURE.md` and `DEPLOYMENT_GUIDE.md`
- **API Docs:** http://localhost:8000/docs (when running)

## Next Steps

1. **Try SaaS locally:**
   ```bash
   ./setup_saas.sh
   python -m saas_api.main
   ```

2. **Read documentation:**
   - `SAAS_ARCHITECTURE.md` - Architecture details
   - `DEPLOYMENT_GUIDE.md` - Production setup

3. **Register first tenant:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register ...
   ```

4. **Test API:**
   Visit http://localhost:8000/docs

---

**Questions?** Check the documentation or raise an issue.
