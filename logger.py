import logging
import json
import sys
from datetime import datetime

# Configurar logger
logger = logging.getLogger("motu_logger")
logger.setLevel(logging.INFO)

# Evitar duplicar handlers
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def log_structured(event_name: str, source: str, **kwargs):
    """
    Emits a structured JSON log entry.
    usage: log_structured("SCRAPE_ATTEMPT", "ActionToys", status="SUCCESS", items=50)
    """
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_name,
        "source": source,
        **kwargs
    }
    logger.info(json.dumps(entry))
