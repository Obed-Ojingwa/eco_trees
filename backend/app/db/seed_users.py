import json
import os
from uuid import uuid4

from app.core.security import hash_secret
from app.db.pool import connection


def seed_users() -> int:
    raw_users = os.getenv("DEMO_USERS_JSON", "")
    if not raw_users:
        raise RuntimeError("Set DEMO_USERS_JSON to a JSON array of synthetic demo users.")
    users = json.loads(raw_users)
    if not isinstance(users, list):
        raise ValueError("DEMO_USERS_JSON must be a JSON array.")

    inserted = 0
    with connection() as conn, conn.transaction():
        for item in users:
            role = item.get("role")
            if role not in {"auditor", "buyer", "bank_viewer", "admin"}:
                raise ValueError("Seeded non-farmer roles must be auditor, buyer, bank_viewer, or admin.")
            if not item.get("email") or not item.get("password") or not item.get("display_name"):
                raise ValueError("Each seeded user requires email, password, and display_name.")
            result = conn.execute(
                """
                INSERT INTO users (id, role, display_name, email, password_hash)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
                """,
                (
                    uuid4(),
                    role,
                    item["display_name"],
                    item["email"].lower(),
                    hash_secret(item["password"]),
                ),
            )
            inserted += result.rowcount
    return inserted


if __name__ == "__main__":
    print(f"Inserted {seed_users()} synthetic demo user(s).")
