"""
Agent memory system — pure Python, no external build dependencies.

Architecture:
- Short-term: sliding window of last N messages (always in context)
- Long-term: simple TF-IDF-style keyword search over past messages
             (no Rust/C++ build tools required — works on any platform)

For production, swap _SimpleVectorStore with ChromaDB or Pinecone.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class _SimpleVectorStore:
    """
    Lightweight keyword-based memory store.
    Uses TF-IDF cosine similarity — no external dependencies.
    Persists to a JSON file for durability across restarts.
    """

    def __init__(self, store_path: str) -> None:
        self._path = store_path
        self._docs: List[Dict] = []  # [{id, text, metadata}]
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._docs = json.load(f)
            except Exception:
                self._docs = []

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._docs[-500:], f)  # keep last 500
        except Exception as e:
            logger.debug("Memory save failed: %s", e)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r'\b\w+\b', text.lower())

    @staticmethod
    def _tf(tokens: List[str]) -> Dict[str, float]:
        count = Counter(tokens)
        total = len(tokens) or 1
        return {t: c / total for t, c in count.items()}

    def _idf(self, term: str) -> float:
        n = len(self._docs) or 1
        df = sum(1 for d in self._docs if term in d.get("tokens", []))
        return math.log((n + 1) / (df + 1)) + 1

    def _score(self, query_tokens: List[str], doc: Dict) -> float:
        doc_tokens = doc.get("tokens", [])
        if not doc_tokens:
            return 0.0
        doc_tf = self._tf(doc_tokens)
        score = 0.0
        for t in set(query_tokens):
            if t in doc_tf:
                score += doc_tf[t] * self._idf(t)
        return score

    def add(self, doc_id: str, text: str, metadata: Optional[Dict] = None) -> None:
        tokens = self._tokenize(text)
        self._docs.append({
            "id": doc_id,
            "text": text,
            "tokens": tokens,
            "metadata": metadata or {},
        })
        self._save()

    def search(self, query: str, n: int = 3) -> List[str]:
        if not self._docs:
            return []
        query_tokens = self._tokenize(query)
        scored: List[Tuple[float, str]] = [
            (self._score(query_tokens, d), d["text"])
            for d in self._docs
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [text for score, text in scored[:n] if score > 0]

    def clear(self) -> None:
        self._docs = []
        if os.path.exists(self._path):
            os.remove(self._path)


class AgentMemory:
    """
    Per-agent memory store.
    - Short-term: sliding window of last N messages
    - Long-term: keyword-based vector store (JSON-persisted)
    """

    def __init__(self, agent_id: str, window_size: int = 10, persist_dir: str = "./memory_data") -> None:
        self.agent_id = agent_id
        self.window_size = window_size
        self._short_term: List[dict] = []
        store_path = os.path.join(persist_dir, f"agent_{agent_id[:8]}.json")
        self._store = _SimpleVectorStore(store_path)

    def add_message(self, role: str, content: str, message_id: str) -> None:
        entry = {"role": role, "content": content, "id": message_id}
        self._short_term.append(entry)

        # Keep sliding window
        if len(self._short_term) > self.window_size * 2:
            self._short_term = self._short_term[-self.window_size * 2:]

        # Store in long-term memory
        self._store.add(
            doc_id=message_id,
            text=f"{role}: {content}",
            metadata={"role": role, "agent_id": self.agent_id},
        )

    def get_recent_messages(self) -> List[dict]:
        return self._short_term[-self.window_size:]

    def search_memory(self, query: str, n_results: int = 3) -> List[str]:
        return self._store.search(query, n=n_results)

    def clear(self) -> None:
        self._short_term = []
        self._store.clear()


# Global memory store
_memory_store: Dict[str, AgentMemory] = {}


def get_memory(agent_id: str, window_size: int = 10) -> AgentMemory:
    if agent_id not in _memory_store:
        from backend.core.config import settings
        persist_dir = getattr(settings, "chroma_persist_dir", "./memory_data")
        _memory_store[agent_id] = AgentMemory(agent_id, window_size, persist_dir)
    return _memory_store[agent_id]
