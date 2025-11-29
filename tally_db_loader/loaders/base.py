"""
Base database loader utilities.

Provides connection management and common database operations.
"""
from __future__ import annotations
import psycopg
from psycopg.rows import dict_row
from contextlib import contextmanager
from typing import Generator, Optional, Any
from loguru import logger
from ..config import TallyLoaderConfig


def get_connection(config: Optional[TallyLoaderConfig] = None):
    """
    Create a database connection.
    
    Returns a psycopg connection configured for the tally_db schema.
    """
    config = config or TallyLoaderConfig.from_env()
    conn = psycopg.connect(config.db_url, autocommit=True, row_factory=dict_row)
    return conn


@contextmanager
def transaction(conn) -> Generator:
    """
    Context manager for database transactions.
    
    Automatically commits on success, rolls back on exception.
    """
    # For psycopg3, we need to use the connection's transaction context
    with conn.transaction():
        yield


class DatabaseLoader:
    """
    Base class for database loading operations.
    
    Provides common functionality:
    - Connection management
    - Batch upsert operations
    - Checkpoint management
    - Logging
    """
    
    def __init__(self, config: Optional[TallyLoaderConfig] = None):
        self.config = config or TallyLoaderConfig.from_env()
        self._conn = None
    
    @property
    def conn(self):
        """Get or create database connection."""
        if self._conn is None or self._conn.closed:
            self._conn = get_connection(self.config)
        return self._conn
    
    def close(self):
        """Close database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    def ensure_schema(self):
        """Create schema if it doesn't exist."""
        schema = self.config.db_schema
        with self.conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    
    def execute_ddl(self, ddl_path: str):
        """Execute DDL from a SQL file."""
        from pathlib import Path
        
        ddl_file = Path(ddl_path)
        if not ddl_file.exists():
            raise FileNotFoundError(f"DDL file not found: {ddl_path}")
        
        ddl = ddl_file.read_text(encoding="utf-8")
        with self.conn.cursor() as cur:
            cur.execute(ddl)
        logger.info(f"Executed DDL from {ddl_path}")
    
    def truncate_table(self, table_name: str):
        """Truncate a table (removes all rows)."""
        with self.conn.cursor() as cur:
            cur.execute(f"TRUNCATE TABLE {table_name} CASCADE")
        logger.debug(f"Truncated table {table_name}")
    
    def get_row_count(self, table_name: str) -> int:
        """Get row count for a table."""
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
            result = cur.fetchone()
            return result["cnt"] if result else 0
    
    def upsert_batch(
        self,
        table_name: str,
        rows: list[dict],
        key_columns: list[str],
        update_columns: list[str] | None = None,
    ) -> tuple[int, int]:
        """
        Upsert a batch of rows.
        
        Args:
            table_name: Full table name (with schema)
            rows: List of row dictionaries
            key_columns: Columns for conflict detection
            update_columns: Columns to update on conflict (None = all non-key)
            
        Returns:
            Tuple of (inserted_count, updated_count)
        """
        if not rows:
            return 0, 0
        
        # Get all columns from first row
        all_columns = list(rows[0].keys())
        
        # Determine update columns
        if update_columns is None:
            update_columns = [c for c in all_columns if c not in key_columns]
        
        # Build INSERT statement
        columns_str = ", ".join(all_columns)
        placeholders = ", ".join([f"%({c})s" for c in all_columns])
        
        # Build ON CONFLICT clause
        key_str = ", ".join(key_columns)
        update_str = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_columns])
        
        sql = f"""
            INSERT INTO {table_name} ({columns_str})
            VALUES ({placeholders})
            ON CONFLICT ({key_str})
            DO UPDATE SET {update_str}
        """
        
        inserted = 0
        updated = 0
        
        with self.conn.cursor() as cur:
            for row in rows:
                cur.execute(sql, row)
                # Note: In PostgreSQL, we can't easily distinguish insert vs update
                # in ON CONFLICT DO UPDATE. For now, count all as processed.
                inserted += 1
        
        return inserted, updated
    
    def insert_batch(self, table_name: str, rows: list[dict]) -> int:
        """
        Insert a batch of rows (no upsert, will fail on duplicates).
        
        Args:
            table_name: Full table name (with schema)
            rows: List of row dictionaries
            
        Returns:
            Number of rows inserted
        """
        if not rows:
            return 0
        
        all_columns = list(rows[0].keys())
        columns_str = ", ".join(all_columns)
        placeholders = ", ".join([f"%({c})s" for c in all_columns])
        
        sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        
        with self.conn.cursor() as cur:
            cur.executemany(sql, rows)
        
        return len(rows)
    
    def get_checkpoint(self, entity_name: str) -> dict | None:
        """Get sync checkpoint for an entity."""
        schema = self.config.db_schema
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT entity_name, last_alter_id, last_sync_at, row_count, status
                FROM {schema}.sync_checkpoint
                WHERE entity_name = %s
                """,
                (entity_name,),
            )
            return cur.fetchone()
    
    def update_checkpoint(
        self,
        entity_name: str,
        last_alter_id: int | None = None,
        row_count: int = 0,
        status: str = "completed",
        error_message: str | None = None,
    ):
        """Update sync checkpoint for an entity."""
        schema = self.config.db_schema
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {schema}.sync_checkpoint
                    (entity_name, last_alter_id, last_sync_at, row_count, status, error_message)
                VALUES (%s, %s, NOW(), %s, %s, %s)
                ON CONFLICT (entity_name) DO UPDATE SET
                    last_alter_id = EXCLUDED.last_alter_id,
                    last_sync_at = EXCLUDED.last_sync_at,
                    row_count = EXCLUDED.row_count,
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message
                """,
                (entity_name, last_alter_id, row_count, status, error_message),
            )
    
    def log_sync(
        self,
        sync_type: str,
        entity_name: str | None = None,
        rows_processed: int = 0,
        rows_inserted: int = 0,
        rows_updated: int = 0,
        status: str = "running",
        error_message: str | None = None,
    ) -> int:
        """Log a sync operation and return the log ID."""
        schema = self.config.db_schema
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {schema}.sync_log
                    (sync_type, entity_name, rows_processed, rows_inserted, rows_updated, status, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (sync_type, entity_name, rows_processed, rows_inserted, rows_updated, status, error_message),
            )
            result = cur.fetchone()
            return result["id"] if result else 0
    
    def update_sync_log(
        self,
        log_id: int,
        rows_processed: int | None = None,
        rows_inserted: int | None = None,
        rows_updated: int | None = None,
        status: str | None = None,
        error_message: str | None = None,
    ):
        """Update an existing sync log entry."""
        schema = self.config.db_schema
        
        updates = []
        params = []
        
        if rows_processed is not None:
            updates.append("rows_processed = %s")
            params.append(rows_processed)
        if rows_inserted is not None:
            updates.append("rows_inserted = %s")
            params.append(rows_inserted)
        if rows_updated is not None:
            updates.append("rows_updated = %s")
            params.append(rows_updated)
        if status is not None:
            updates.append("status = %s")
            params.append(status)
            if status in ("completed", "failed"):
                updates.append("completed_at = NOW()")
                updates.append("duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))")
        if error_message is not None:
            updates.append("error_message = %s")
            params.append(error_message)
        
        if not updates:
            return
        
        params.append(log_id)
        
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE {schema}.sync_log
                SET {", ".join(updates)}
                WHERE id = %s
                """,
                params,
            )

