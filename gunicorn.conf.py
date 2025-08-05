# Gunicorn configuration file
import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"
backlog = 2048

# Worker processes - use fewer workers for better session handling
workers = 1  # Changed from 2 to 1 for better session consistency
worker_class = "sync"
worker_connections = 1000
timeout = 60  # Increased timeout
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