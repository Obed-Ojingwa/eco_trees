import hashlib
import logging
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.core.config import settings


logger = logging.getLogger(__name__)


def _migration_checksum(content: bytes) -> str:
    normalized = content.replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def _migration_checksum_matches(checksum: str, content: bytes) -> bool:
    normalized = content.replace(b"\r\n", b"\n")
    windows_content = normalized.replace(b"\n", b"\r\n")
    return checksum in {
        hashlib.sha256(normalized).hexdigest(),
        hashlib.sha256(windows_content).hexdigest(),
    }


def migrate(migration_dir: Path | None = None) -> list[str]:
    if not settings.migration_database_url:
        raise RuntimeError("DB_MIGRATION_URL must be set to run database migrations.")
    directory = migration_dir or settings.migration_dir
    applied: list[str] = []
    with psycopg.connect(settings.migration_database_url, row_factory=dict_row) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name text PRIMARY KEY,
                checksum text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        conn.commit()
        for path in sorted(directory.glob("*.sql")):
            content = path.read_bytes()
            checksum = _migration_checksum(content)
            with conn.transaction():
                existing = conn.execute(
                    "SELECT checksum FROM schema_migrations WHERE name = %s",
                    (path.name,),
                ).fetchone()
                if existing:
                    if not _migration_checksum_matches(
                        existing["checksum"],
                        content,
                    ):
                        raise RuntimeError(f"Applied migration changed: {path.name}")
                    continue
                conn.execute(content.decode("utf-8"))
                conn.execute(
                    "INSERT INTO schema_migrations (name, checksum) VALUES (%s, %s)",
                    (path.name, checksum),
                )
            applied.append(path.name)
            logger.info("database migration applied: %s", path.name)
    return applied


if __name__ == "__main__":
    migrate()
