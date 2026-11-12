from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd


class AgentCache:
    """Persistent event-level cache that prevents accidental per-bar LLM calls."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS agent_cache (
                agent TEXT NOT NULL,
                scope_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                output_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (agent, scope_key, fingerprint)
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def get(self, agent: str, scope_key: str, fingerprint: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT output_json FROM agent_cache WHERE agent=? AND scope_key=? AND fingerprint=?",
                (agent, scope_key, fingerprint),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, agent: str, scope_key: str, fingerprint: str, output: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO agent_cache(agent, scope_key, fingerprint, output_json) VALUES (?, ?, ?, ?)",
                (agent, scope_key, fingerprint, json.dumps(output, sort_keys=True, default=str)),
            )


class ResearchAgents:
    """Non-authoritative research assistants, invoked only for discrete events.

    `provider` is an optional callable suitable for any external LLM adapter. Its
    output is advisory; deterministic strategy/risk code never consumes it as an
    entry, exit, size, stop, or kill override.
    """

    def __init__(
        self,
        cache: AgentCache,
        provider: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.cache = cache
        self.provider = provider

    @staticmethod
    def _fingerprint(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:24]

    def _once(
        self,
        agent: str,
        scope_key: str,
        payload: dict[str, Any],
        fallback: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        fingerprint = self._fingerprint(payload)
        cached = self.cache.get(agent, scope_key, fingerprint)
        if cached is not None:
            return {**cached, "cached": True}
        output = self.provider(agent, payload) if self.provider else fallback(payload)
        output = {**output, "advisory_only": True, "cached": False}
        self.cache.put(agent, scope_key, fingerprint, output)
        return output

    def data_quality(self, symbol: str, pull_id: str, quality: dict[str, Any]) -> dict[str, Any]:
        return self._once(
            "data_quality", f"{symbol.upper()}:{pull_id}", quality,
            lambda value: {
                "status": "PASS" if not any(value.get(k, 0) for k in ("duplicates", "missing_values", "nonpositive_prices")) else "BLOCK",
                "issues": [k for k in ("duplicates", "missing_values", "nonpositive_prices") if value.get(k, 0)],
            },
        )

    def event_news(self, symbol: str, event_id: str, event: dict[str, Any]) -> dict[str, Any]:
        def fallback(value: dict[str, Any]) -> dict[str, Any]:
            text = f"{value.get('title', '')} {value.get('summary', '')}".lower()
            severe = any(word in text for word in ("fraud", "bankruptcy", "investigation", "guidance cut", "acquisition"))
            return {
                "severity": "UNKNOWN_BUT_RISKY" if severe else "LOW_IMPACT",
                "no_trade_recommended": severe,
                "summary": str(value.get("summary", value.get("title", "")))[:500],
            }
        return self._once("event_news", f"{symbol.upper()}:{event_id}", event, fallback)

    def regime(self, symbol: str, date: str | pd.Timestamp, inputs: dict[str, Any]) -> dict[str, Any]:
        day = pd.Timestamp(date).strftime("%Y-%m-%d")
        return self._once(
            "regime", f"{symbol.upper()}:{day}", inputs,
            lambda value: {
                "classification": value.get("deterministic_regime", "UNKNOWN"),
                "contradictions": [],
                "disable_recommended": value.get("deterministic_regime") in {"PANIC_SELL", "VOL_EXPANSION", "EVENT_RISK", "UNKNOWN"},
            },
        )

    def strategy_review(self, candidate_id: str, candidate: dict[str, Any]) -> dict[str, Any]:
        return self._once(
            "strategy_review", candidate_id, candidate,
            lambda value: {
                "summary": f"Deterministic candidate score {value.get('score', 'unknown')}",
                "contradictions": [],
                "disable_recommended": False,
            },
        )

    def post_trade(self, trade_id: str, trade: dict[str, Any]) -> dict[str, Any]:
        return self._once(
            "post_trade", trade_id, trade,
            lambda value: {
                "summary": f"Trade closed for {value.get('pnl', 'unknown')} after costs.",
                "error_tags": [],
                "rule_change_authorized": False,
            },
        )

