import logging
import os
from typing import Any, Dict

import httpx

AUDIT_HOST = os.getenv("AUDIT_HOST")
LOG_AUDIT_STREAM = os.getenv("LOG_AUDIT_STREAM", "segittur_audit")


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
