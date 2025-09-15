import os
import httpx
import logging
from typing import Dict, Any


AUDIT_HOST = os.getenv("AUDIT_HOST")


async def send_audit_log(audit_entry: Dict[str, Any]):
    if AUDIT_HOST:
        async with httpx.AsyncClient() as client:
            response = await client.post(AUDIT_HOST, json=audit_entry, timeout=5.0)
            response.raise_for_status()
    else:
        audit_logger = logging.getLogger("PID.audit")
        default_message = "Audit log"
        message = audit_entry.pop("message", default_message)
        audit_logger.info(message, extra=audit_entry)
