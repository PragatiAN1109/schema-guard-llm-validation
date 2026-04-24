"""
SQLite database — extended schema with record_results, rule_violations,
plus dashboard aggregation and audit log queries.

Tables:
    validation_runs  — one row per single-record validation
    record_results   — per-record results within batch runs
    batch_runs       — one row per batch execution
    rule_violations  — individual rule violations linked to records
"""

import sqlite3
import json
import time
import threading
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "schemaguard.db"
_lock = threading.Lock()


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS validation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            input_payload TEXT DEFAULT '{}',
            structural_valid INTEGER NOT NULL,
            semantic_valid INTEGER NOT NULL,
            confidence_score REAL NOT NULL,
            decision TEXT NOT NULL,
            violated_rules TEXT DEFAULT '[]',
            explanation TEXT DEFAULT '',
            processing_time_ms REAL DEFAULT 0,
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS record_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT NOT NULL,
            record_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            structural_valid INTEGER NOT NULL,
            semantic_valid INTEGER NOT NULL,
            confidence_score REAL NOT NULL,
            decision TEXT NOT NULL,
            decision_reason TEXT DEFAULT '',
            violated_rules TEXT DEFAULT '[]',
            explanation TEXT DEFAULT '',
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS batch_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            total_records INTEGER NOT NULL,
            trusted INTEGER NOT NULL,
            flagged INTEGER NOT NULL,
            quarantined INTEGER NOT NULL,
            mean_confidence REAL NOT NULL,
            drift_detected INTEGER DEFAULT 0,
            drift_alerts TEXT DEFAULT '[]',
            processing_time_ms REAL NOT NULL,
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rule_violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL,
            batch_id TEXT,
            rule_id TEXT NOT NULL,
            rule_name TEXT NOT NULL,
            severity TEXT NOT NULL,
            fields TEXT DEFAULT '[]',
            message TEXT DEFAULT '',
            domain TEXT NOT NULL,
            created_at REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_vr_domain ON validation_runs(domain);
        CREATE INDEX IF NOT EXISTS idx_vr_decision ON validation_runs(decision);
        CREATE INDEX IF NOT EXISTS idx_vr_created ON validation_runs(created_at);
        CREATE INDEX IF NOT EXISTS idx_br_created ON batch_runs(created_at);
        CREATE INDEX IF NOT EXISTS idx_rr_batch ON record_results(batch_id);
        CREATE INDEX IF NOT EXISTS idx_rv_record ON rule_violations(record_id);
        CREATE INDEX IF NOT EXISTS idx_rv_rule ON rule_violations(rule_id);
    """)
    conn.close()


# ── Single validation persistence ──

def save_validation_run(result: dict):
    now = time.time()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """INSERT INTO validation_runs
                   (record_id, domain, input_payload, structural_valid, semantic_valid,
                    confidence_score, decision, violated_rules, explanation, processing_time_ms, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    result.get("record_id", ""),
                    result.get("domain", ""),
                    json.dumps(result.get("input_payload", {})),
                    1 if result.get("structural_valid") else 0,
                    1 if result.get("semantic_valid") else 0,
                    result.get("confidence_score", 0),
                    result.get("decision", "quarantined"),
                    json.dumps(result.get("violated_rules", [])),
                    result.get("explanation", ""),
                    result.get("audit_entry", {}).get("processing_time_ms", 0),
                    now,
                ),
            )
            for v in result.get("violated_rules", []):
                conn.execute(
                    """INSERT INTO rule_violations
                       (record_id, batch_id, rule_id, rule_name, severity, fields, message, domain, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (result.get("record_id",""), None, v.get("rule_id",""), v.get("rule_name",""),
                     v.get("severity",""), json.dumps(v.get("fields",[])), v.get("message",""),
                     result.get("domain",""), now),
                )
            conn.commit()
        finally:
            conn.close()


# ── Batch persistence ──

def save_batch_run(result: dict):
    now = time.time()
    summary = result.get("summary", {})
    drift = result.get("drift_summary") or {}
    batch_id = result.get("batch_id", "")
    domain = result.get("domain", "")

    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """INSERT INTO batch_runs
                   (batch_id, domain, total_records, trusted, flagged, quarantined,
                    mean_confidence, drift_detected, drift_alerts, processing_time_ms, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (batch_id, domain, result.get("total_records",0),
                 summary.get("trusted",0), summary.get("flagged",0), summary.get("quarantined",0),
                 summary.get("mean_confidence",0), 1 if drift.get("drift_detected") else 0,
                 json.dumps(drift.get("alerts",[])), summary.get("processing_time_ms",0), now),
            )
            for r in result.get("results", []):
                conn.execute(
                    """INSERT INTO record_results
                       (batch_id, record_id, domain, structural_valid, semantic_valid,
                        confidence_score, decision, decision_reason, violated_rules, explanation, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (batch_id, r.get("record_id",""), domain,
                     1 if r.get("structural_valid") else 0, 1 if r.get("semantic_valid") else 0,
                     r.get("confidence_score",0), r.get("decision","quarantined"),
                     r.get("decision_reason",""), json.dumps(r.get("violated_rules",[])),
                     r.get("explanation",""), now),
                )
                for v in r.get("violated_rules", []):
                    conn.execute(
                        """INSERT INTO rule_violations
                           (record_id, batch_id, rule_id, rule_name, severity, fields, message, domain, created_at)
                           VALUES (?,?,?,?,?,?,?,?,?)""",
                        (r.get("record_id",""), batch_id, v.get("rule_id",""), v.get("rule_name",""),
                         v.get("severity",""), json.dumps(v.get("fields",[])), v.get("message",""),
                         domain, now),
                    )
            conn.commit()
        finally:
            conn.close()


# ── Queries ──

def get_recent_validations(limit: int = 20) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM validation_runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_recent_batches(limit: int = 10) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM batch_runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_violations(limit: int = 50, rule_id: str = None, domain: str = None) -> list[dict]:
    conn = _connect()
    try:
        q = "SELECT * FROM rule_violations WHERE 1=1"
        params = []
        if rule_id:
            q += " AND rule_id = ?"; params.append(rule_id)
        if domain:
            q += " AND domain = ?"; params.append(domain)
        q += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(q, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_audit_logs(limit: int = 50, domain: str = None, decision: str = None) -> list[dict]:
    conn = _connect()
    try:
        q = "SELECT record_id, domain, structural_valid, semantic_valid, confidence_score, decision, explanation, created_at FROM validation_runs WHERE 1=1"
        params = []
        if domain:
            q += " AND domain = ?"; params.append(domain)
        if decision:
            q += " AND decision = ?"; params.append(decision)
        q += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(q, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_dashboard_stats() -> dict:
    conn = _connect()
    try:
        total = conn.execute("SELECT COUNT(*) FROM validation_runs").fetchone()[0]
        trusted = conn.execute("SELECT COUNT(*) FROM validation_runs WHERE decision='trusted'").fetchone()[0]
        flagged = conn.execute("SELECT COUNT(*) FROM validation_runs WHERE decision='flagged'").fetchone()[0]
        quarantined = conn.execute("SELECT COUNT(*) FROM validation_runs WHERE decision='quarantined'").fetchone()[0]
        avg_conf = conn.execute("SELECT AVG(confidence_score) FROM validation_runs").fetchone()[0] or 0
        total_batches = conn.execute("SELECT COUNT(*) FROM batch_runs").fetchone()[0]
        total_violations = conn.execute("SELECT COUNT(*) FROM rule_violations").fetchone()[0]

        top_rules = conn.execute(
            "SELECT rule_id, severity, COUNT(*) as cnt FROM rule_violations GROUP BY rule_id ORDER BY cnt DESC LIMIT 5"
        ).fetchall()

        recent = conn.execute(
            "SELECT record_id, domain, decision, confidence_score, created_at FROM validation_runs ORDER BY created_at DESC LIMIT 10"
        ).fetchall()

        by_domain = conn.execute(
            "SELECT domain, COUNT(*) as cnt, AVG(confidence_score) as avg_conf FROM validation_runs GROUP BY domain"
        ).fetchall()

        return {
            "total_validations": total,
            "trusted": trusted,
            "flagged": flagged,
            "quarantined": quarantined,
            "avg_confidence": round(avg_conf, 4),
            "total_batches": total_batches,
            "total_violations": total_violations,
            "top_violated_rules": [{"rule_id": r[0], "severity": r[1], "count": r[2]} for r in top_rules],
            "recent_activity": [dict(r) for r in recent],
            "by_domain": [{"domain": r[0], "count": r[1], "avg_confidence": round(r[2], 4)} for r in by_domain],
        }
    finally:
        conn.close()


def get_stats() -> dict:
    return get_dashboard_stats()


def _row_to_dict(row) -> dict:
    d = dict(row)
    for k in ("violated_rules", "drift_alerts", "fields"):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except:
                pass
    return d
