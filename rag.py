"""
RAG Pyramid — three-layer SQLite store.

Layer 1  events     raw window/URL events (high volume, short retention)
Layer 2  sessions   compressed activity summaries (medium volume)
Layer 3  snapshots  personality snapshots (low volume, long retention)

Ollama inference pulls from all three layers for a multi-resolution
view of the user: recent raw signals + historical patterns + prior profiles.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "rag.db"

# How many items to pull per layer when building the inference context
CONTEXT_EVENTS    = 30
CONTEXT_SESSIONS  = 15
CONTEXT_SNAPSHOTS = 3


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id        INTEGER PRIMARY KEY,
                ts        TEXT,
                app       TEXT,
                title     TEXT,
                url       TEXT,
                duration  REAL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id        INTEGER PRIMARY KEY,
                start_ts  TEXT,
                end_ts    TEXT,
                type      TEXT,
                summary   TEXT
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                id        INTEGER PRIMARY KEY,
                ts        TEXT,
                profile   TEXT
            );
        """)


# ── Layer 1 ──────────────────────────────────────────────────────────────────

def insert_event(app: str, title: str, url: str | None, duration: float):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO events (ts, app, title, url, duration) VALUES (?,?,?,?,?)",
            (datetime.now().isoformat(), app, title, url, duration),
        )


# ── Layer 2 ──────────────────────────────────────────────────────────────────

_SESSION_GAP = 300  # seconds — idle gap that closes a session

_RULES: list[tuple[str, list[str]]] = [
    ("coding",        ["github", "stackoverflow", "vscode", "code", "localhost", "terminal", "cmd", "powershell"]),
    ("learning",      ["youtube", "coursera", "udemy", "khan", "docs.", "tutorial", "lecture", "learn"]),
    ("entertainment", ["netflix", "twitch", "hulu", "spotify", "reddit", "twitter", "instagram", "tiktok"]),
    ("research",      ["arxiv", "scholar", "wikipedia", "pubmed", "notion", "obsidian"]),
    ("communication", ["gmail", "outlook", "slack", "discord", "teams", "zoom", "meet"]),
    ("browsing",      ["chrome", "firefox", "edge", "google", "bing"]),
]

_session_buffer: list[dict] = []
_last_event_ts: datetime | None = None


def push_event(app: str, title: str, url: str | None, duration: float):
    global _last_event_ts
    now = datetime.now()

    if _last_event_ts and (now - _last_event_ts).total_seconds() > _SESSION_GAP:
        _flush_session()

    _session_buffer.append({"app": app, "title": title, "url": url, "duration": duration, "ts": now})
    _last_event_ts = now
    insert_event(app, title, url, duration)


def _flush_session():
    if not _session_buffer:
        return
    scores: dict[str, float] = {}
    for ev in _session_buffer:
        hay = " ".join(filter(None, [ev["app"], ev["title"], ev["url"]])).lower()
        for label, kws in _RULES:
            scores[label] = scores.get(label, 0) + sum(ev["duration"] for kw in kws if kw in hay)
    stype = max(scores, key=scores.get) if scores else "general"
    total = sum(e["duration"] for e in _session_buffer) / 60
    apps = list(dict.fromkeys(e["app"] for e in _session_buffer))[:4]
    titles = [e["title"] for e in _session_buffer if e["title"]][:3]
    urls = [e["url"] for e in _session_buffer if e["url"]][:3]
    parts = [f"{stype.capitalize()} session (~{total:.0f} min). Apps: {', '.join(apps)}."]
    if titles:
        parts.append(f"Viewed: {'; '.join(titles)}.")
    if urls:
        parts.append(f"URLs: {'; '.join(urls)}.")
    summary = " ".join(parts)
    with _conn() as conn:
        conn.execute(
            "INSERT INTO sessions (start_ts, end_ts, type, summary) VALUES (?,?,?,?)",
            (_session_buffer[0]["ts"].isoformat(), _session_buffer[-1]["ts"].isoformat(), stype, summary),
        )
    _session_buffer.clear()


def force_flush():
    _flush_session()


# ── Layer 3 ──────────────────────────────────────────────────────────────────

def insert_snapshot(profile: dict):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO snapshots (ts, profile) VALUES (?,?)",
            (datetime.now().isoformat(), json.dumps(profile)),
        )


def latest_snapshot() -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT profile FROM snapshots ORDER BY id DESC LIMIT 1").fetchone()
    return json.loads(row["profile"]) if row else None


# ── Context builder ───────────────────────────────────────────────────────────

def build_context() -> str:
    with _conn() as conn:
        raw = conn.execute(
            "SELECT app, title, url, duration FROM events ORDER BY id DESC LIMIT ?",
            (CONTEXT_EVENTS,),
        ).fetchall()
        sess = conn.execute(
            "SELECT type, summary FROM sessions ORDER BY id DESC LIMIT ?",
            (CONTEXT_SESSIONS,),
        ).fetchall()
        snaps = conn.execute(
            "SELECT ts, profile FROM snapshots ORDER BY id DESC LIMIT ?",
            (CONTEXT_SNAPSHOTS,),
        ).fetchall()

    parts = []

    if raw:
        parts.append("=== RECENT ACTIVITY (Layer 1) ===")
        for r in reversed(raw):
            line = f"[{r['app']}] {r['title']}"
            if r["url"]:
                line += f" | {r['url']}"
            line += f" ({r['duration']:.0f}s)"
            parts.append(line)

    if sess:
        parts.append("\n=== SESSION HISTORY (Layer 2) ===")
        for s in reversed(sess):
            parts.append(f"[{s['type'].upper()}] {s['summary']}")

    if snaps:
        parts.append("\n=== PRIOR PROFILES (Layer 3) ===")
        for s in snaps:
            p = json.loads(s["profile"])
            parts.append(
                f"[{s['ts'][:16]}] O:{p['ocean']['openness']:.2f} "
                f"C:{p['ocean']['conscientiousness']:.2f} "
                f"E:{p['ocean']['extraversion']:.2f} "
                f"A:{p['ocean']['agreeableness']:.2f} "
                f"N:{p['ocean']['neuroticism']:.2f} | "
                f"Animal: {p.get('spirit_animal','?')}"
            )

    return "\n".join(parts)
