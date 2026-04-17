import json
import logging
from datetime import datetime, timezone


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )


def log_event(logger: logging.Logger, event: str, **fields):
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "api",
        "event": event,
        **fields,
    }
    logger.info(json.dumps(payload, default=str))
