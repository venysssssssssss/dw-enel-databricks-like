import pandas as pd
from pathlib import Path
import hashlib
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class PositiveCache:
    def __init__(self, cache_path: str = "data/rag_train/positive_cache.parquet"):
        self.cache_path = Path(cache_path)
        self.df = None
        self._load()

    def _load(self):
        if self.cache_path.exists():
            try:
                self.df = pd.read_parquet(self.cache_path)
                logger.info(f"Positive cache loaded with {len(self.df)} entries.")
            except Exception as e:
                logger.error(f"Error loading positive cache: {e}")
                self.df = None

    def lookup(self, question: str) -> Optional[Dict[str, Any]]:
        if self.df is None or self.df.empty:
            return None
            
        q_norm = self._normalize(question)
        q_hash = hashlib.sha256(q_norm.encode()).hexdigest()
        
        match = self.df[self.df["hash"] == q_hash]
        if not match.empty:
            return match.iloc[0].to_dict()
        return None

    def _normalize(self, q: str) -> str:
        q = q.lower().strip()
        import re
        q = re.sub(r'\s+', ' ', q)
        return q
