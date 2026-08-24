from collections import Counter

from dotenv import load_dotenv

load_dotenv()

from corpus.storage import (
    init_db,
    get_all_auction_ids,
    get_comments_for_auction,
    save_mined_discrepancies,
    has_mined_auction,
    mark_auction_mined,
)
from agents.comment_mining_agent import should_review, mine_discrepancies


def run():
    init_db()
    auction_ids = get_all_auction_ids()

    if not auction_ids:
        print("No auctions found in raw_comments -- nothing to mine.")
        return

    total_comments = 0
    total_sent_to_claude = 0
    total_confirmed = 0
    category_counts = Counter()

    for i, auction_id in enumerate(auction_ids, 1):
        if has_mined_auction(auction_id):
            print(f"[{i}/{len(auction_ids)}] {auction_id}: already mined, skipping")
            continue

        comments = get_comments_for_auction(auction_id)
        real_comments = [c for c in comments if c.get("type") == 1]

        sent = [c for c in real_comments if should_review(c.get("text"))]

        print(f"[{i}/{len(auction_ids)}] {auction_id}: "
              f"{len(comments)} comments total, {len(sent)} passed the prefilter")

        records = mine_discrepancies(auction_id, comments)
        if records:
            save_mined_discrepancies(records)
        mark_auction_mined(auction_id)

        print(f"    confirmed discrepancies: {len(records)}")

        total_comments += len(comments)
        total_sent_to_claude += len(sent)
        total_confirmed += len(records)
        for r in records:
            category_counts[r["flag_category"]] += 1

    print("\n=== Summary ===")
    print(f"Total comments processed: {total_comments}")
    print(f"Total sent to Claude: {total_sent_to_claude}")
    print(f"Total confirmed discrepancies: {total_confirmed}")
    print("By flag_category:")
    for category, count in category_counts.most_common():
        print(f"  {category}: {count}")


if __name__ == "__main__":
    run()
