import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


DB_PATH = Path(__file__).parent.parent / "data" / "listings.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            listing_url TEXT,
            agents_run TEXT NOT NULL,
            extraction_ms INTEGER,
            vin_ms INTEGER,
            photo_ms INTEGER,
            editorial_ms INTEGER,
            synthesis_ms INTEGER,
            total_ms INTEGER,
            extraction_input_tokens INTEGER DEFAULT 0,
            extraction_output_tokens INTEGER DEFAULT 0,
            vin_input_tokens INTEGER DEFAULT 0,
            vin_output_tokens INTEGER DEFAULT 0,
            photo_input_tokens INTEGER DEFAULT 0,
            photo_output_tokens INTEGER DEFAULT 0,
            editorial_input_tokens INTEGER DEFAULT 0,
            editorial_output_tokens INTEGER DEFAULT 0,
            synthesis_input_tokens INTEGER DEFAULT 0,
            synthesis_output_tokens INTEGER DEFAULT 0,
            total_cost_usd REAL DEFAULT 0.0,
            flag_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            warning_count INTEGER DEFAULT 0,
            info_count INTEGER DEFAULT 0,
            recommended_action TEXT,
            overall_score REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            note TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flag_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            run_id INTEGER,
            field_name TEXT NOT NULL,
            severity TEXT NOT NULL,
            judgment TEXT NOT NULL,
            editor_note TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_flag_feedback(run_id: int, field_name: str, severity: str,
                       judgment: str, editor_note: str = ""):
    conn = get_connection()
    conn.execute("""
        INSERT INTO flag_feedback (timestamp, run_id, field_name, severity, judgment, editor_note)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.utcnow().isoformat(), run_id, field_name, severity, judgment, editor_note))
    conn.commit()
    conn.close()


def get_flag_feedback_summary() -> dict:
    conn = get_connection()
    rows = conn.execute("SELECT judgment, field_name FROM flag_feedback").fetchall()
    conn.close()

    counts = {"correct": 0, "false_positive": 0, "already_known": 0, "custom": 0}
    by_field: dict = {}

    for row in rows:
        j, f = row["judgment"], row["field_name"]
        if j in counts:
            counts[j] += 1
        if f not in by_field:
            by_field[f] = {"correct": 0, "false_positive": 0, "already_known": 0, "custom": 0}
        if j in by_field[f]:
            by_field[f][j] += 1

    return {
        "total_feedback": len(rows),
        "correct": counts["correct"],
        "false_positive": counts["false_positive"],
        "already_known": counts["already_known"],
        "custom": counts["custom"],
        "by_field": by_field,
    }


# --- Cost calculation ---
_MODEL_PRICING = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-opus-4-5":   {"input": 15.0, "output": 75.0},
}
_DEFAULT_MODEL = "claude-sonnet-4-6"


# The Message Batches API bills at half the standard per-token rate. Every
# eval pipeline call (eval/eval_runner.py) goes through that API, not the
# standard synchronous endpoint, so its real cost is half of what the
# standard rates below would suggest. Interactive calls (app.py, live in
# the Streamlit tool) are not batched and are billed at the full rate.
_BATCH_DISCOUNT = 0.5


def calculate_cost(input_tokens: int, output_tokens: int, model: str = _DEFAULT_MODEL,
                    batch: bool = False) -> float:
    pricing = _MODEL_PRICING.get(model, _MODEL_PRICING[_DEFAULT_MODEL])
    cost = (input_tokens / 1_000_000 * pricing["input"]) + \
           (output_tokens / 1_000_000 * pricing["output"])
    return cost * _BATCH_DISCOUNT if batch else cost


# --- Logging a run ---
class RunLogger:
    def __init__(self, listing_url: Optional[str] = None):
        self.listing_url = listing_url
        self.timestamp = datetime.utcnow().isoformat()
        self.agents_run = []
        self.timings = {}
        self.tokens = {}
        self._start_times = {}

    def start_agent(self, agent_name: str):
        self._start_times[agent_name] = time.time()

    def end_agent(self, agent_name: str, input_tokens: int = 0, output_tokens: int = 0, model: Optional[str] = None):
        elapsed_ms = int((time.time() - self._start_times[agent_name]) * 1000)
        self.timings[agent_name] = elapsed_ms
        self.tokens[agent_name] = {
            "input": input_tokens,
            "output": output_tokens,
            "model": model or _DEFAULT_MODEL,
        }
        self.agents_run.append(agent_name)

    def save(self, flag_count: int, error_count: int, warning_count: int,
             info_count: int, recommended_action: str, overall_score: float):

        total_ms = sum(self.timings.values())

        # Calculate total cost across all agents
        total_cost = sum(
            calculate_cost(v["input"], v["output"], v["model"])
            for v in self.tokens.values()
        )

        def t(agent): return self.timings.get(agent)
        def tok(agent, kind): return self.tokens.get(agent, {}).get(kind, 0)

        initialize_db()
        conn = get_connection()
        conn.execute("""
            INSERT INTO runs (
                timestamp, listing_url, agents_run,
                extraction_ms, vin_ms, photo_ms, editorial_ms, synthesis_ms, total_ms,
                extraction_input_tokens, extraction_output_tokens,
                vin_input_tokens, vin_output_tokens,
                photo_input_tokens, photo_output_tokens,
                editorial_input_tokens, editorial_output_tokens,
                synthesis_input_tokens, synthesis_output_tokens,
                total_cost_usd,
                flag_count, error_count, warning_count, info_count,
                recommended_action, overall_score
            ) VALUES (
                ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?,
                ?, ?, ?, ?,
                ?, ?
            )
        """, (
            self.timestamp,
            self.listing_url,
            ", ".join(self.agents_run),
            t("extraction"), t("vin"), t("photo"), t("editorial"), t("synthesis"),
            total_ms,
            tok("extraction", "input"), tok("extraction", "output"),
            tok("vin", "input"), tok("vin", "output"),
            tok("photo", "input"), tok("photo", "output"),
            tok("editorial", "input"), tok("editorial", "output"),
            tok("synthesis", "input"), tok("synthesis", "output"),
            total_cost,
            flag_count, error_count, warning_count, info_count,
            recommended_action, overall_score
        ))
        conn.commit()
        conn.close()
        print(f"Run logged. Total cost: ${total_cost:.4f} | Time: {total_ms}ms | Action: {recommended_action}")


# --- Summary query ---
def _compute_stats(conn: sqlite3.Connection, where: str = "", params: tuple = ()) -> Optional[dict]:
    count = conn.execute(f"SELECT COUNT(*) as c FROM runs {where}", params).fetchone()["c"]
    if count == 0:
        return None

    overview = conn.execute(f"""
        SELECT SUM(total_cost_usd) as total_spend, AVG(total_cost_usd) as avg_cost,
               MIN(timestamp) as earliest, MAX(timestamp) as latest
        FROM runs {where}
    """, params).fetchone()

    perf = conn.execute(f"""
        SELECT AVG(total_ms) as avg_total_ms,
               AVG(extraction_ms) as extraction, AVG(vin_ms) as vin,
               AVG(photo_ms) as photo, AVG(editorial_ms) as editorial,
               AVG(synthesis_ms) as synthesis
        FROM runs {where}
    """, params).fetchone()

    avg_total_s = (perf["avg_total_ms"] or 0) / 1000
    raw_timings = {a: (perf[a] or 0) / 1000
                   for a in ["extraction", "vin", "photo", "editorial", "synthesis"]}
    agent_timings = sorted(
        [(a, {"seconds": s, "pct": (s / avg_total_s * 100) if avg_total_s else 0})
         for a, s in raw_timings.items()],
        key=lambda x: x[1]["seconds"], reverse=True
    )

    quality = conn.execute(f"""
        SELECT
            SUM(CASE WHEN overall_score >= 0.8 THEN 1 ELSE 0 END) as good,
            SUM(CASE WHEN overall_score >= 0.6 AND overall_score < 0.8 THEN 1 ELSE 0 END) as acceptable,
            SUM(CASE WHEN overall_score < 0.6 THEN 1 ELSE 0 END) as poor,
            AVG(overall_score) as avg_overall_score,
            AVG(flag_count) as avg_flags,
            AVG(error_count) as avg_errors,
            AVG(warning_count) as avg_warnings,
            AVG(info_count) as avg_infos,
            SUM(error_count) as total_errors,
            SUM(warning_count) as total_warnings,
            SUM(info_count) as total_infos
        FROM runs {where}
    """, params).fetchone()

    actions = conn.execute(f"""
        SELECT recommended_action, COUNT(*) as count
        FROM runs {where} GROUP BY recommended_action ORDER BY count DESC
    """, params).fetchall()

    tok = conn.execute(f"""
        SELECT AVG(extraction_input_tokens) as ext_in, AVG(extraction_output_tokens) as ext_out,
               AVG(photo_input_tokens) as photo_in, AVG(photo_output_tokens) as photo_out,
               AVG(editorial_input_tokens) as ed_in, AVG(editorial_output_tokens) as ed_out,
               AVG(synthesis_input_tokens) as syn_in, AVG(synthesis_output_tokens) as syn_out
        FROM runs {where}
    """, params).fetchone()

    p = _MODEL_PRICING["claude-sonnet-4-6"]
    def _cost(i, o): return ((i or 0) / 1_000_000 * p["input"]) + ((o or 0) / 1_000_000 * p["output"])
    raw_costs = {
        "extraction": _cost(tok["ext_in"],   tok["ext_out"]),
        "editorial":  _cost(tok["ed_in"],    tok["ed_out"]),
        "synthesis":  _cost(tok["syn_in"],   tok["syn_out"]),
        "photo":      _cost(tok["photo_in"], tok["photo_out"]),
        "vin":        0.0,
    }

    return {
        "total_runs":       count,
        "total_spend":      overview["total_spend"] or 0,
        "avg_cost":         overview["avg_cost"] or 0,
        "date_range":       (overview["earliest"], overview["latest"]),
        "avg_total_s":      avg_total_s,
        "agent_timings":    agent_timings,
        "score_good":       quality["good"] or 0,
        "score_acceptable": quality["acceptable"] or 0,
        "score_poor":       quality["poor"] or 0,
        "avg_overall_score": quality["avg_overall_score"] or 0,
        "avg_flags":        quality["avg_flags"] or 0,
        "avg_errors":       quality["avg_errors"] or 0,
        "avg_warnings":     quality["avg_warnings"] or 0,
        "avg_infos":        quality["avg_infos"] or 0,
        "total_errors":     quality["total_errors"] or 0,
        "total_warnings":   quality["total_warnings"] or 0,
        "total_infos":      quality["total_infos"] or 0,
        "action_breakdown": {r["recommended_action"]: r["count"] for r in actions},
        "agent_costs":      sorted(raw_costs.items(), key=lambda x: x[1], reverse=True),
    }


def get_latest_run() -> Optional[dict]:
    initialize_db()
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM runs ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_summary_dict() -> dict:
    initialize_db()
    conn = get_connection()
    all_stats = _compute_stats(conn)
    conn.close()

    if all_stats is None:
        return {"total_runs": 0}

    latest = get_latest_run()
    if latest:
        latest_keys = {
            "latest_cost":               latest.get("total_cost_usd"),
            "latest_total_s":            (latest.get("total_ms") or 0) / 1000,
            "latest_overall_score":      latest.get("overall_score"),
            "latest_recommended_action": latest.get("recommended_action"),
            "latest_error_count":        latest.get("error_count"),
            "latest_warning_count":      latest.get("warning_count"),
            "latest_info_count":         latest.get("info_count"),
            "latest_flag_count":         latest.get("flag_count"),
            "latest_agent_times":        {
                a: (latest.get(f"{a}_ms") or 0) / 1000
                for a in ["extraction", "vin", "photo", "editorial", "synthesis"]
            },
            "latest_timestamp":          latest.get("timestamp"),
        }
    else:
        latest_keys = {k: None for k in [
            "latest_cost", "latest_total_s", "latest_overall_score",
            "latest_recommended_action", "latest_error_count", "latest_warning_count",
            "latest_info_count", "latest_flag_count", "latest_agent_times", "latest_timestamp",
        ]}

    return {**all_stats, **latest_keys}


def print_summary():
    d = get_summary_dict()
    print("\n=== OBSERVABILITY SUMMARY ===")
    print("\n--- Overview ---")
    print(f"Total runs: {d['total_runs']}")
    if d["total_runs"] == 0:
        print("No runs yet.")
        return
    print(f"Total spend: ${d['total_spend']:.4f}")
    print(f"Average cost per listing: ${d['avg_cost']:.4f}")
    print(f"Date range: {d['date_range'][0]} to {d['date_range'][1]}")
    print("\n--- Performance ---")
    print(f"Average total runtime: {d['avg_total_s']:.2f}s")
    for agent, v in d["agent_timings"]:
        print(f"  {agent}: {v['seconds']:.1f}s ({v['pct']:.0f}%)")
    print("\n--- Quality ---")
    print(f"Average overall score: {d['avg_overall_score']:.2f}")
    print(f"Average flags per listing: {d['avg_flags']:.1f}")
    print(f"  ERROR: {d['avg_errors']:.1f}/run")
    print(f"  WARNING: {d['avg_warnings']:.1f}/run")
    print(f"  INFO: {d['avg_infos']:.1f}/run")
    # TODO: per-flag-type breakdown requires a flags table
    print("\n--- Cost by agent (avg per listing) ---")
    for agent, cost in d["agent_costs"]:
        print(f"  {agent}: ${cost:.4f}")


if __name__ == "__main__":
    print_summary()