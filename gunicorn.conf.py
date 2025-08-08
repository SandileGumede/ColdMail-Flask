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
timeout = 120  # Increased timeout for database operations
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
graceful_timeout = 30

# Disable access logging for better performance (optional)
# accesslog = None 