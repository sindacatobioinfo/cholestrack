"""
This will make sure the Celery app is always imported when
Django starts so that shared_task will use this app.
"""

# Import celery app, but gracefully handle import errors
# (e.g., during migrations when celery might not be needed)
try:
    from .celery_app import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # If celery isn't installed or there's an import issue,
    # we can still run Django commands like migrations
    pass
