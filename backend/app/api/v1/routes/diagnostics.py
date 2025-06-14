"""
Diagnostics routes for monitoring application health and performance.

This module provides endpoints for:
- Detailed health checks with timing information
- Resource usage monitoring
- Connection pool status
"""

import asyncio
import gc
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any

import psutil
import redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.pool import NullPool

from app.auth_utils import get_current_admin
from app.config import get_settings
from app.db.database import get_db, get_engine
from app.storage_provider import get_storage_provider

router = APIRouter()


async def check_database_health(db) -> Dict[str, Any]:
    """Check database connectivity and performance."""
    start_time = time.time()
    try:
        # Simple query to test connection
        result = db.execute(text("SELECT 1"))
        result.scalar()
        
        # Get connection pool stats if available
        engine = get_engine()
        pool_info = {}
        if hasattr(engine.pool, 'size'):
            pool_info = {
                "pool_type": engine.pool.__class__.__name__,
                "size": getattr(engine.pool, 'size', 'N/A'),
                "checked_out": getattr(engine.pool, 'checkedout', 'N/A'),
                "overflow": getattr(engine.pool, 'overflow', 'N/A'),
                "total": getattr(engine.pool, 'total', 'N/A'),
            }
        else:
            pool_info = {"pool_type": "NullPool", "info": "No persistent connections"}
        
        return {
            "status": "healthy",
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "pool_info": pool_info,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
        }


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis connectivity and performance."""
    start_time = time.time()
    try:
        settings = get_settings()
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        redis_conn = redis.from_url(redis_url)
        
        # Test connection
        redis_conn.ping()
        
        # Get some stats
        info = redis_conn.info()
        
        redis_conn.close()
        
        return {
            "status": "healthy",
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "connected_clients": info.get("connected_clients", "N/A"),
            "used_memory_human": info.get("used_memory_human", "N/A"),
            "total_connections_received": info.get("total_connections_received", "N/A"),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
        }


async def check_storage_provider_health(storage_provider) -> Dict[str, Any]:
    """Check storage provider connectivity and performance."""
    start_time = time.time()
    try:
        # Try to list root directory (should be fast)
        list(storage_provider.list_directory(prefix=None))
        
        provider_info = {
            "provider_name": storage_provider.provider_name,
            "provider_type": storage_provider.__class__.__name__,
        }
        
        # Check if it's using singleton pattern
        if hasattr(storage_provider, '_instance'):
            provider_info["singleton"] = True
        
        return {
            "status": "healthy",
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "provider_info": provider_info,
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
        }


def get_system_metrics() -> Dict[str, Any]:
    """Get system resource usage metrics."""
    process = psutil.Process(os.getpid())
    
    # Memory info
    memory_info = process.memory_info()
    memory_percent = process.memory_percent()
    
    # CPU info
    cpu_percent = process.cpu_percent(interval=0.1)
    
    # Thread/connection info
    num_threads = process.num_threads()
    connections = process.connections()
    
    # File descriptors
    num_fds = process.num_fds() if hasattr(process, 'num_fds') else "N/A"
    
    # Garbage collection stats
    gc_stats = gc.get_stats()
    
    return {
        "memory": {
            "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            "percent": round(memory_percent, 2),
        },
        "cpu": {
            "percent": round(cpu_percent, 2),
            "num_threads": num_threads,
        },
        "connections": {
            "total": len(connections),
            "by_status": {
                status: len([c for c in connections if c.status == status])
                for status in set(c.status for c in connections)
            },
        },
        "file_descriptors": num_fds,
        "garbage_collection": {
            "collections": sum(stat.get('collections', 0) for stat in gc_stats),
            "collected": sum(stat.get('collected', 0) for stat in gc_stats),
            "uncollectable": sum(stat.get('uncollectable', 0) for stat in gc_stats),
        },
        "process": {
            "pid": os.getpid(),
            "create_time": datetime.fromtimestamp(process.create_time(), timezone.utc).isoformat(),
            "uptime_hours": round((time.time() - process.create_time()) / 3600, 2),
        },
    }


@router.get("/health/detailed")
async def detailed_health_check(
    db=Depends(get_db),
    storage_provider=Depends(get_storage_provider),
    _=Depends(get_current_admin),
):
    """
    Detailed health check with timing and resource information.
    
    This endpoint is restricted to administrators and provides comprehensive
    health information including:
    - Database connectivity and pool status
    - Redis connectivity and stats  
    - Storage provider health
    - System resource usage
    - Process information
    
    Use this to diagnose performance issues in production.
    """
    start_time = time.time()
    
    # Run health checks concurrently
    db_health, redis_health, storage_health = await asyncio.gather(
        check_database_health(db),
        check_redis_health(),
        check_storage_provider_health(storage_provider),
    )
    
    # Get system metrics
    system_metrics = get_system_metrics()
    
    total_time_ms = round((time.time() - start_time) * 1000, 2)
    
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_check_time_ms": total_time_ms,
        "checks": {
            "database": db_health,
            "redis": redis_health,
            "storage_provider": storage_health,
        },
        "system": system_metrics,
    }


@router.post("/diagnostics/gc")
async def force_garbage_collection(_=Depends(get_current_admin)):
    """
    Force garbage collection and return statistics.
    
    This can help diagnose memory leaks by forcing Python to collect
    unreachable objects and return collection statistics.
    """
    before_stats = gc.get_stats()
    before_count = len(gc.get_objects())
    
    # Force full garbage collection
    collected = gc.collect(2)  # Collect all generations
    
    after_stats = gc.get_stats()
    after_count = len(gc.get_objects())
    
    return {
        "collected_objects": collected,
        "objects_before": before_count,
        "objects_after": after_count,
        "objects_freed": before_count - after_count,
        "stats_before": before_stats,
        "stats_after": after_stats,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }