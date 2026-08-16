import redis

from src.config import settings
from src.db.session import engine


async def health_check():
    """
    Check Redis and postgresql connectivity.
    """

    status = {"redis": False, "postgres": False, "status": "healthy"}

    #Redis check

    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        status["redis"] = True

    except Exception:
        status["status"] = "offline"

    # PostgreSQL check
    try:
        conn = engine.connect()
        conn.execute("SELECT 1")
        conn.close()
        status["postgres"] = True
    except Exception:
        status["status"] = "degraded"
    
    if not status["redis"] or not status["postgres"]:
        # Optionally raise HTTP 503
        pass
    return status