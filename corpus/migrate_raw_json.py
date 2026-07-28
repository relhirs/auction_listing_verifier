"""
One-off migration: load the old corpus_raw/*.json files (auction_id +
comments list) into the raw_comments table in corpus/corpus.db.

Run: python -m corpus.migrate_raw_json
"""

import glob
import json
import os

from corpus.storage import init_db, save_comments

RAW_DIR = "corpus_raw"


def migrate():
    init_db()
    files = sorted(glob.glob(os.path.join(RAW_DIR, "*.json")))
    if not files:
        print(f"No JSON files found in {RAW_DIR}/ -- nothing to migrate.")
        return

    for path in files:
        with open(path) as f:
            data = json.load(f)
        auction_id = data["auction_id"]
        comments = data["comments"]
        save_comments(auction_id, comments)
        print(f"migrated {auction_id}: {len(comments)} comments from {path}")

    print("\nMigration finished.")


if __name__ == "__main__":
    migrate()
