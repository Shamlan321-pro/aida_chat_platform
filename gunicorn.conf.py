# Gunicorn configuration file for Aida Mocxha AI Agent API
# Usage: gunicorn -c gunicorn.conf.py production_server:application

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
# Using single worker to avoid shared state issues with active_agents dictionary
# For high-traffic production, consider implementing Redis-based session storage
workers = 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Preload application for better performance
preload_app = True

# Logging
accesslog = "access.log"
errorlog = "error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'aida_mocxha_api'

# Server mechanics
daemon = False
pidfile = 'aida_api.pid'
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment and configure for HTTPS)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Environment variables
raw_env = [
    'FLASK_ENV=production',
]

# Worker process lifecycle hooks
def on_starting(server):
    server.log.info("Aida Mocxha API server is starting...")

def on_reload(server):
    server.log.info("Aida Mocxha API server is reloading...")

def when_ready(server):
    server.log.info("Aida Mocxha API server is ready. Listening on: %s", server.address)

def worker_int(worker):
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    worker.log.info("Worker received SIGABRT signal")