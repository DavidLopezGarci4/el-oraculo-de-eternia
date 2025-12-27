import logging
import json
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from src.domain.models import KaizenInsightModel

logger = logging.getLogger("audit_logger")

class AuditLogger:
    """
    Captures qualitative insights during scraping for the Kaizen Learning Log.
    """
    def __init__(self, db: Session):
        self.db = db

    def log_insight(
        self, 
        spider_name: str, 
        insight_type: str, 
        content: str, 
        pattern: Optional[str] = None,
        solution: Optional[str] = None,
        severity: str = "info"
    ):
        """
        Records a qualitative finding in the database.
        """
        insight = KaizenInsightModel(
            spider_name=spider_name,
            insight_type=insight_type,
            content=content,
            pattern_observed=pattern,
            proposed_solution=solution,
            severity=severity
        )
        try:
            self.db.add(insight)
            self.db.commit()
            logger.info(f"🧠 Kaizen Insight logged for {spider_name}: {insight_type}")
            
            # Also append to a markdown file for easy agent access across sessions
            self._append_to_brain_log(spider_name, insight_type, content, pattern, solution)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to log Kaizen insight: {e}")

    def _append_to_brain_log(self, spider, type, content, pattern, solution):
        """
        Maintains the quantitative markdown log in the .gemini/antigravity/brain dir.
        """
        import os
        # Path derived from environment or fallback
        brain_dir = os.environ.get("GEMINI_BRAIN_PATH", "c:/Users/dace8/.gemini/antigravity/brain/c8253c79-6713-4b80-994b-fcc3cfb22b08")
        brain_path = os.path.join(brain_dir, "kaizen_learning_log.md")
        
        entry = f"\n### [{datetime.now().strftime('%Y-%m-%d %H:%M')}] {spider} - {type.upper()}\n"
        entry += f"- **Content:** {content}\n"
        if pattern: entry += f"- **Pattern:** `{pattern}`\n"
        if solution: entry += f"- **Proposed Solution:** {solution}\n"
        entry += "---\n"
        
        try:
            # Create file if not exists
            if not os.path.exists(brain_path):
                with open(brain_path, "w", encoding="utf-8") as f:
                    f.write("# Kaizen Learning Log: Memoria de Aprendizaje del Oráculo\n")
                    f.write("Este archivo centraliza hallazgos cualitativos para mejorar los agentes.\n\n")
            
            with open(brain_path, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            logger.warning(f"Could not append to brain log: {e}")
