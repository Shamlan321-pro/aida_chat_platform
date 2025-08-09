# Production Deployment Guide for AIDA Platform

This guide explains how to deploy the AIDA Platform in production mode.

## Quick Start for Production

### 1. Set Environment Variables

Create a `.env` file in your project root or set environment variables:

```bash
# Required for production
export FLASK_SECRET_KEY="your-very-long-secret-key-here-at-least-32-characters"
export GOOGLE_API_KEY="your-google-api-key"
export FLASK_DEBUG="False"
export FLASK_ENV="production"

# Optional (with defaults)
export MONGODB_URI="mongodb://localhost:27017/"
export MONGODB_DB_NAME="aida_platform"
export ERPNEXT_URL="http://localhost:8000"
export ERPNEXT_USERNAME="Administrator"
export ERPNEXT_PASSWORD="admin"
```

### 2. Start Production Server

#### Option A: Using the Production Startup Script (Recommended)
```bash
python start_production.py
```

#### Option B: Using the Main Script with Environment Variable
```bash
export FLASK_DEBUG="False"
python aida_api_server.py
```

#### Option C: Using Gunicorn (Advanced)
```bash
pip install gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 aida_api_server:app
```

## Production Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_SECRET_KEY` | Yes | - | Secret key for Flask sessions (32+ chars) |
| `GOOGLE_API_KEY` | Yes | - | Google API key for AI functionality |
| `FLASK_DEBUG` | No | False | Enable debug mode (False for production) |
| `FLASK_ENV` | No | production | Flask environment |
| `MONGODB_URI` | No | mongodb://localhost:27017/ | MongoDB connection URI |
| `MONGODB_DB_NAME` | No | aida_platform | MongoDB database name |

### Security Checklist

- [ ] Set a strong `FLASK_SECRET_KEY` (32+ characters)
- [ ] Use HTTPS in production (SSL certificates)
- [ ] Configure firewall rules
- [ ] Set up proper CORS policies
- [ ] Review and secure API endpoints
- [ ] Use production database (not SQLite)

### Performance Optimization

- [ ] Use a production WSGI server (Gunicorn, uWSGI, Waitress)
- [ ] Configure appropriate number of workers
- [ ] Set up load balancing if needed
- [ ] Configure database connection pooling
- [ ] Set up caching if applicable

## Troubleshooting

### Common Issues

1. **Server exits immediately**
   - Check if all required environment variables are set
   - Ensure MongoDB is running and accessible
   - Check log files for errors

2. **Permission errors**
   - Ensure the user running the server has proper permissions
   - Check file permissions for logs and database files

3. **Port already in use**
   - Change the port number in the configuration
   - Kill any existing processes using the port

4. **Database connection issues**
   - Verify MongoDB is running
   - Check connection string and credentials
   - Ensure network connectivity

### Log Files

The production server creates the following log files:
- `aida_production.log` - Application logs
- `error.log` - Error logs (if using Gunicorn)
- `access.log` - Access logs (if using Gunicorn)

### Monitoring

Monitor the server using:
- Health check endpoint: `GET /health`
- Application logs: `tail -f aida_production.log`
- System resources: CPU, memory, disk usage

## Systemd Service (Linux)

Create `/etc/systemd/system/aida-api.service`:

```ini
[Unit]
Description=AIDA Platform API Server
After=network.target mongod.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/path/to/aida_platform
Environment=FLASK_ENV=production
Environment=FLASK_DEBUG=False
Environment=FLASK_SECRET_KEY=your-secret-key
Environment=GOOGLE_API_KEY=your-google-api-key
ExecStart=/usr/bin/python3 start_production.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl enable aida-api
sudo systemctl start aida-api
sudo systemctl status aida-api
```

## Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

ENV FLASK_ENV=production
ENV FLASK_DEBUG=False

CMD ["python", "start_production.py"]
```

Build and run:
```bash
docker build -t aida-platform .
docker run -p 5000:5000 -e FLASK_SECRET_KEY=your-key -e GOOGLE_API_KEY=your-key aida-platform
```

## Support

For issues and support:
1. Check the log files first
2. Verify all environment variables are set
3. Test database connectivity
4. Review the troubleshooting section above