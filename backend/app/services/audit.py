"""Audit log helper - records all inventory changes."""
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def log_action(db: AsyncSession, entity_type: str, entity_id: int, action: str, changes: dict | None = None, user: str = "staff"):
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changes=json.dumps(changes) if changes else None,
        user=user,
    )
    db.add(entry)
