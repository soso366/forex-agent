"""Cerveau LLM (optionnel) : Claude relit les candidats et les positions ouvertes.

Garde-fous structurels :
- il ne peut choisir qu'un candidat déjà détecté et qualifié par le code, ou NO_TRADE ;
- il n'a aucun champ pour la taille, le levier ou le risque ;
- ses demandes de stop passent par le Risk Manager (resserrer uniquement) ;
- toute réponse invalide est ignorée et le cycle continue avec la décision déterministe.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Protocol

from ..config import resolve_path

ALLOWED_POSITION_ACTIONS = {"HOLD", "MOVE_STOP", "TAKE_PROFIT", "CLOSE"}


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class AnthropicClient:
    def __init__(self, model: str, max_tokens: int, api_key: str):
        import anthropic  # dépendance optionnelle
        self._c = anthropic.Anthropic(api_key=api_key)
        self.model, self.max_tokens = model, max_tokens

    def complete(self, system: str, user: str) -> str:
        msg = self._c.messages.create(model=self.model, max_tokens=self.max_tokens,
                                      system=system, messages=[{"role": "user", "content": user}])
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def load_prompt(cfg: dict) -> tuple[str, str]:
    """Prompt permanent + playbook, relus à chaque cycle. Renvoie (texte, empreinte)."""
    text = resolve_path(cfg, "prompt").read_text(encoding="utf-8")
    playbook = resolve_path(cfg, "playbook").read_text(encoding="utf-8")
    full = f"{text}\n\n---\n\n{playbook}"
    return full, hashlib.sha256(full.encode()).hexdigest()[:12]


class LLMBrain:
    def __init__(self, cfg: dict, client: LLMClient | None = None):
        self.cfg = cfg
        self.enabled = bool(cfg.get("llm", {}).get("enabled"))
        self.client = client
        self.status = "désactivé"
        if self.enabled and self.client is None:
            key = os.environ.get(cfg["llm"].get("api_key_env", "ANTHROPIC_API_KEY"))
            try:
                if not key:
                    raise RuntimeError("clé API absente")
                self.client = AnthropicClient(cfg["llm"]["model"], cfg["llm"]["max_tokens"], key)
            except Exception as e:
                self.enabled, self.status = False, f"indisponible ({e}) — décisions déterministes"
        if self.enabled:
            self.status = "actif"

    def review(self, payload: dict, candidate_ids: set[str], trade_ids: set[int]) -> tuple[dict | None, str]:
        if not self.enabled:
            return None, self.status
        system, _ = load_prompt(self.cfg)
        try:
            raw = self.client.complete(system, json.dumps(payload, ensure_ascii=False, default=str))
            return validate(raw, candidate_ids, trade_ids), "ok"
        except Exception as e:
            return None, f"réponse LLM ignorée : {e}"


def validate(raw: str, candidate_ids: set[str], trade_ids: set[int]) -> dict[str, Any]:
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("pas de JSON")
    data = json.loads(m.group(0))
    out: dict[str, Any] = {"new_trade": {"candidate_id": None, "reason": ""}, "positions": [], "ideas": []}
    nt = data.get("new_trade") or {}
    cid = nt.get("candidate_id")
    if cid is not None and cid not in candidate_ids:
        raise ValueError(f"candidat inconnu {cid!r} (le LLM ne peut pas inventer de trade)")
    parts = [f"{k}: {nt[k]}" for k in ("observation", "interpretation", "hypothesis", "alternative",
                                       "invalidation") if nt.get(k)]
    reason = str(nt.get("reason", ""))
    out["new_trade"] = {"candidate_id": cid,
                        "reason": (reason + (" | " + " | ".join(parts) if parts else ""))[:1500]}
    for p in data.get("positions", []) or []:
        action = str(p.get("action", "")).upper()
        tid = p.get("trade_id")
        if tid not in trade_ids or action not in ALLOWED_POSITION_ACTIONS:
            continue
        ns = p.get("new_stop")
        out["positions"].append({"trade_id": tid, "action": action,
                                 "new_stop": float(ns) if ns is not None else None,
                                 "reason": str(p.get("reason", ""))[:500]})
    out["ideas"] = [str(i)[:500] for i in (data.get("ideas") or [])][:5]
    return out
