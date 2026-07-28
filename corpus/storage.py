import json
import sqlite3

from corpus.config import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_comments (
            auction_id TEXT,
            comment_id TEXT,
            comment_json TEXT,
            PRIMARY KEY (auction_id, comment_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mined_discrepancies (
            auction_id TEXT,
            comment_id TEXT,
            flag_category TEXT,
            source_text TEXT,
            confidence REAL,
            PRIMARY KEY (auction_id, comment_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mined_auctions (
            auction_id TEXT PRIMARY KEY
        )
        """
    )
    conn.commit()
    conn.close()


def has_mined_auction(auction_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT 1 FROM mined_auctions WHERE auction_id = ? LIMIT 1", (auction_id,)
    )
    found = cur.fetchone() is not None
    conn.close()
    return found


def mark_auction_mined(auction_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO mined_auctions (auction_id) VALUES (?)", (auction_id,)
    )
    conn.commit()
    conn.close()


def has_auction(auction_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT 1 FROM raw_comments WHERE auction_id = ? LIMIT 1", (auction_id,)
    )
    found = cur.fetchone() is not None
    conn.close()
    return found


def save_comments(auction_id: str, comments: list):
    conn = sqlite3.connect(DB_PATH)
    for comment in comments:
        conn.execute(
            "INSERT OR REPLACE INTO raw_comments (auction_id, comment_id, comment_json) "
            "VALUES (?, ?, ?)",
            (auction_id, comment["id"], json.dumps(comment)),
        )
    conn.commit()
    conn.close()
    print(f"    saved {len(comments)} comments to {DB_PATH}")


def get_all_auction_ids() -> list:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT auction_id FROM raw_comments GROUP BY auction_id ORDER BY MIN(rowid)"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_comments_for_auction(auction_id: str) -> list:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT comment_json FROM raw_comments WHERE auction_id = ?", (auction_id,)
    ).fetchall()
    conn.close()
    return [json.loads(r[0]) for r in rows]


def save_mined_discrepancies(records: list):
    conn = sqlite3.connect(DB_PATH)
    for r in records:
        conn.execute(
            "INSERT OR REPLACE INTO mined_discrepancies "
            "(auction_id, comment_id, flag_category, source_text, confidence) "
            "VALUES (?, ?, ?, ?, ?)",
            (r["auction_id"], r["comment_id"], r["flag_category"], r["source_text"], r["confidence"]),
        )
    conn.commit()
    conn.close()
