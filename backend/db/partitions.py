"""
Sovereign Postgres Partition Manager v13.1.0.
Automates the creation of child tables for the partitioned 'audit_log'.
"""

import logging
from datetime import datetime, timezone
from sqlalchemy import text
from backend.db.postgres_db import get_write_session

logger = logging.getLogger(__name__)

async def ensure_audit_partitions():
    """
    Ensures partitions exist for the current month and the next month.
    Prevents INSERT failures in 'audit_log' which is partitioned by RANGE.
    """
    now = datetime.now(timezone.utc)
    
    # Calculate current month and next month ranges
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Next month calculation
    if current_month_start.month == 12:
        next_month_start = current_month_start.replace(year=current_month_start.year + 1, month=1)
    else:
        next_month_start = current_month_start.replace(month=current_month_start.month + 1)
        
    if next_month_start.month == 12:
        following_month_start = next_month_start.replace(year=next_month_start.year + 1, month=1)
    else:
        following_month_start = next_month_start.replace(month=next_month_start.month + 1)

    ranges = [
        (current_month_start, next_month_start),
        (next_month_start, following_month_start)
    ]

    async with get_write_session() as session:
        for start, end in ranges:
            partition_name = f"audit_log_y{start.year}m{start.month:02d}"
            start_str = start.strftime('%Y-%m-%d')
            end_str = end.strftime('%Y-%m-%d')
            
            # Sub-table creation for Postgres Range Partitioning
            sql = f"""
            CREATE TABLE IF NOT EXISTS {partition_name} 
            PARTITION OF audit_log 
            FOR VALUES FROM ('{start_str}') TO ('{end_str}');
            """
            try:
                await session.execute(text(sql))
                logger.info(f"[Partitions] Ensured partition: {partition_name} ({start_str} to {end_str})")
            except Exception as e:
                logger.error(f"[Partitions] Failed to create partition {partition_name}: {e}")
                # Don't raise, try the next one
