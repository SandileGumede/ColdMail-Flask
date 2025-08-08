# Gunicorn configuration file
import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"
backlog = 2048

# Worker processes - use single worker for better session handling
workers = 1
worker_class = "sync"
worker_connections = 1000
timeout = 180  # Increased timeout for database operations
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "pitchai"

# Server mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (not needed for Render as they handle HTTPS)
keyfile = None
certfile = None

# Preload app for better performance and session handling
preload_app = True

# Worker timeout for database operations
worker_tmp_dir = "/dev/shm"  # Use shared memory for better performance

# Enable worker recycling
max_requests = 1000
max_requests_jitter = 50

# Additional settings for Flask apps
raw_env = [
    "FLASK_ENV=production",
    "FLASK_DEBUG=0"
]

# Enable graceful reload
graceful_timeout = 60  # Increased graceful timeout

# Disable access logging for better performance (optional)
# accesslog = None

# Worker initialization
def on_starting(server):
    """Called just after the server is started"""
    server.log.info("Starting PitchAI server...")

def on_reload(server):
    """Called to reload the server"""
    server.log.info("Reloading PitchAI server...")

def worker_int(worker):
    """Called just after a worker has been initialized"""
    worker.log.info("Worker initialized")

def pre_fork(server, worker):
    """Called just before a worker has been forked"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    """Called just after a worker has initialized the application"""
    worker.log.info("Worker initialized")

def worker_abort(worker):
    """Called when a worker received SIGABRT signal"""
    worker.log.info("Worker received SIGABRT") 