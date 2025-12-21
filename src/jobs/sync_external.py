import logging
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.collectors import personal_collection
from src.core.logger import setup_logging

def run_sync_job():
    """
    Wrapper to run the legacy ActionFigure411 scraper/updater.
    This ensures it runs within the App's environment and logging context.
    """
    log_file = Path("logs/external_sync.log")
    log_file.parent.mkdir(exist_ok=True)
    
    # Setup file handler specifically for this job
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)
    
    print("[START] Starting ActionFigure411 Sync Job...")
    print(f"[INFO] Logs will be written to {log_file.absolute()}")
    
    try:
        personal_collection.main()
        print("[SUCCESS] Sync Job Completed.")
    except Exception as e:
        print(f"[ERROR] Sync Job Failed: {e}")
        logging.error(f"Sync Job Failed: {e}", exc_info=True)
    finally:
        root_logger.removeHandler(file_handler)

if __name__ == "__main__":
    run_sync_job()
