# SaaS Deployment Guide

## Quick Start

### Development Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd invoice_reconciliation_v1.0_stable
```

2. **Run setup script:**
```bash
./setup_saas.sh
```

3. **Start the API server:**
```bash
source venv/bin/activate
python -m saas_api.main
```

4. **Access API documentation:**
```
http://localhost:8000/docs
```

### Production Deployment

## Prerequisites

- **Server:** Linux (Ubuntu 20.04+ recommended)
- **Python:** 3.9+
- **Database:** PostgreSQL 13+
- **Cache:** Redis 6+ (optional but recommended)
- **Web Server:** Nginx
- **Process Manager:** Supervisor or systemd

## Step-by-Step Production Setup

### 1. Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv nginx postgresql postgresql-contrib redis-server

# Create application user
sudo useradd -m -s /bin/bash invoiceapp
sudo su - invoiceapp
```

### 2. Setup Application

```bash
# Clone repository
git clone <repository-url> /home/invoiceapp/app
cd /home/invoiceapp/app

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements-saas.txt
pip install gunicorn
```

### 3. Configure Database

```bash
# Create PostgreSQL database
sudo -u postgres psql
```

```sql
CREATE DATABASE invoice_reconciliation;
CREATE USER invoiceapp WITH ENCRYPTED PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE invoice_reconciliation TO invoiceapp;
\q
```

### 4. Configure Environment

```bash
# Create production .env
nano /home/invoiceapp/app/.env
```

```env
ENVIRONMENT=production
DEBUG=False

API_HOST=0.0.0.0
API_PORT=8000

DATABASE_URL=postgresql://invoiceapp:your-secure-password@localhost:5432/invoice_reconciliation
REDIS_URL=redis://localhost:6379/0

SECRET_KEY=your-random-secret-key-here
JWT_SECRET_KEY=your-random-jwt-secret-here

CORS_ORIGINS=["https://yourdomain.com"]

LOG_LEVEL=INFO
```

**Generate secure keys:**
```bash
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
```

### 5. Initialize Database

```bash
source venv/bin/activate
python3 -c "from saas_config import init_db; init_db()"
```

### 6. Configure Gunicorn

Create `/home/invoiceapp/app/gunicorn_config.py`:

```python
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
keepalive = 5

# Logging
accesslog = "/home/invoiceapp/app/logs/gunicorn_access.log"
errorlog = "/home/invoiceapp/app/logs/gunicorn_error.log"
loglevel = "info"

# Process naming
proc_name = "invoice_reconciliation_api"

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190
```

### 7. Configure Supervisor

Create `/etc/supervisor/conf.d/invoice-api.conf`:

```ini
[program:invoice-api]
directory=/home/invoiceapp/app
command=/home/invoiceapp/app/venv/bin/gunicorn saas_api.main:app -c gunicorn_config.py
user=invoiceapp
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/invoiceapp/app/logs/supervisor.log
environment=PATH="/home/invoiceapp/app/venv/bin"
```

Start the service:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start invoice-api
```

### 8. Configure Nginx

Create `/etc/nginx/sites-available/invoice-api`:

```nginx
upstream invoice_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Client body size (for file uploads)
    client_max_body_size 50M;
    
    # Proxy settings
    location / {
        proxy_pass http://invoice_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    # Static files (if any)
    location /static {
        alias /home/invoiceapp/app/static;
        expires 30d;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/invoice-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 9. Setup SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 10. Setup Celery Workers (Optional but Recommended)

Create `/etc/supervisor/conf.d/invoice-worker.conf`:

```ini
[program:invoice-worker]
directory=/home/invoiceapp/app
command=/home/invoiceapp/app/venv/bin/celery -A saas_workers.celery_app worker --loglevel=info
user=invoiceapp
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/invoiceapp/app/logs/celery_worker.log
environment=PATH="/home/invoiceapp/app/venv/bin"
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start invoice-worker
```

### 11. Setup Monitoring (Optional)

#### Health Check Endpoint
```bash
curl https://yourdomain.com/health
```

#### Log Monitoring
```bash
tail -f /home/invoiceapp/app/logs/gunicorn_error.log
tail -f /home/invoiceapp/app/logs/supervisor.log
```

#### Database Monitoring
```bash
sudo -u postgres psql -d invoice_reconciliation -c "SELECT COUNT(*) FROM tenants;"
```

## Post-Deployment

### 1. Create First Tenant

```bash
curl -X POST https://yourdomain.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@company.com",
    "password": "SecurePassword123!",
    "first_name": "Admin",
    "last_name": "User",
    "organization_name": "Company Name"
  }'
```

### 2. Test Authentication

```bash
curl -X POST https://yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@company.com",
    "password": "SecurePassword123!"
  }'
```

### 3. Setup Backup

Create `/home/invoiceapp/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/home/invoiceapp/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U invoiceapp invoice_reconciliation | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Backup uploads
tar -czf "$BACKUP_DIR/uploads_$DATE.tar.gz" /home/invoiceapp/app/uploads

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

Add to crontab:
```bash
0 2 * * * /home/invoiceapp/backup.sh
```

## Maintenance

### Update Application

```bash
sudo su - invoiceapp
cd /home/invoiceapp/app
git pull
source venv/bin/activate
pip install -r requirements-saas.txt
sudo supervisorctl restart invoice-api
```

### Check Status

```bash
sudo supervisorctl status
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis
```

### View Logs

```bash
# Application logs
tail -f /home/invoiceapp/app/logs/gunicorn_error.log

# Nginx logs
tail -f /var/log/nginx/error.log

# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-13-main.log
```

## Scaling

### Horizontal Scaling

1. **Load Balancer:** Use AWS ALB or Nginx
2. **Multiple API Servers:** Deploy on multiple instances
3. **Shared Database:** Use managed PostgreSQL (AWS RDS, Azure Database)
4. **Shared Storage:** Use S3 for file uploads
5. **Distributed Cache:** Use Redis Cluster

### Vertical Scaling

1. **Increase Workers:** Adjust `gunicorn_config.py` workers
2. **Database Resources:** Increase PostgreSQL connections
3. **Server Resources:** Upgrade CPU/RAM

## Troubleshooting

### API Not Responding
```bash
sudo supervisorctl status invoice-api
sudo supervisorctl restart invoice-api
```

### Database Connection Issues
```bash
sudo systemctl status postgresql
# Check DATABASE_URL in .env
```

### High Memory Usage
```bash
# Check worker processes
ps aux | grep gunicorn
# Reduce workers in gunicorn_config.py
```

### Slow Responses
```bash
# Check database queries
sudo -u postgres psql -d invoice_reconciliation -c "SELECT * FROM pg_stat_activity;"
# Add database indexes if needed
```

## Security Checklist

- [ ] Use strong SECRET_KEY and JWT_SECRET_KEY
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure firewall (UFW)
- [ ] Set proper file permissions
- [ ] Enable rate limiting
- [ ] Regular security updates
- [ ] Database backups
- [ ] Monitor logs for suspicious activity
- [ ] Use environment variables for secrets
- [ ] Disable DEBUG mode in production

## Support

For issues or questions:
- Documentation: SAAS_ARCHITECTURE.md
- API Docs: https://yourdomain.com/docs
- Logs: /home/invoiceapp/app/logs/

---

**Last Updated:** 2026-02-25
