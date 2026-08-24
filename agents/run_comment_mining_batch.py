import json
import sys
from collections import defaultdict
from pathlib import Path

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
from agents.comment_mining_agent import (
    should_review,
    raw_client,
    build_batch_request,
    parse_batch_result,
)

BATCH_STATE_PATH = Path(__file__).parent.parent / "corpus" / "batch_state.json"


def submit():
    init_db()
    auction_ids = get_all_auction_ids()
    pending_auction_ids = [a for a in auction_ids if not has_mined_auction(a)]

    if not pending_auction_ids:
        print("No unmined auctions -- nothing to submit.")
        return

    requests = []
    custom_id_map = {}
    auction_expected_counts = defaultdict(int)

    for auction_id in pending_auction_ids:
        comments = get_comments_for_auction(auction_id)
        for comment in comments:
            if comment.get("type") != 1:
                continue
            text = comment.get("text")
            if not should_review(text):
                continue
            custom_id = f"{auction_id}__{comment['id']}"
            requests.append(build_batch_request(custom_id, text))
            custom_id_map[custom_id] = {
                "auction_id": auction_id,
                "comment_id": comment["id"],
                "source_text": text,
            }
            auction_expected_counts[auction_id] += 1

    if not requests:
        print("No comments passed the prefilter across any unmined auction -- nothing to submit.")
        return

    print(f"About to submit a batch of {len(requests)} comment classifications "
          f"across {len(auction_expected_counts)} auctions.")
    batch = raw_client.messages.batches.create(requests=requests)
    print(f"Batch created: {batch.id} (status: {batch.processing_status})")

    state = {
        "batch_id": batch.id,
        "custom_id_map": custom_id_map,
        "auction_ids": list(auction_expected_counts.keys()),
        "auction_expected_counts": auction_expected_counts,
    }
    with open(BATCH_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
    print(f"Saved batch state to {BATCH_STATE_PATH}. Run `fetch` later to process results.")


def fetch():
    if not BATCH_STATE_PATH.exists():
        print(f"No pending batch found at {BATCH_STATE_PATH}. Run `submit` first.")
        return

    with open(BATCH_STATE_PATH) as f:
        state = json.load(f)

    batch = raw_client.messages.batches.retrieve(state["batch_id"])
    print(f"Batch {batch.id}: {batch.processing_status} "
          f"(succeeded={batch.request_counts.succeeded}, "
          f"errored={batch.request_counts.errored}, "
          f"processing={batch.request_counts.processing})")

    if batch.processing_status != "ended":
        print("Batch not finished yet -- check back later.")
        return

    init_db()
    custom_id_map = state["custom_id_map"]
    auction_processed_counts = defaultdict(int)
    records_by_auction = defaultdict(list)

    for result in raw_client.messages.batches.results(batch.id):
        info = custom_id_map.get(result.custom_id)
        if info is None:
            print(f"    WARNING: unrecognized custom_id {result.custom_id}, skipping")
            continue

        auction_processed_counts[info["auction_id"]] += 1

        if result.result.type != "succeeded":
            print(f"    {result.custom_id}: {result.result.type}, skipping")
            continue

        classification = parse_batch_result(result.result.message)
        if classification.is_confirmed_discrepancy:
            records_by_auction[info["auction_id"]].append({
                "auction_id": info["auction_id"],
                "comment_id": info["comment_id"],
                "flag_category": classification.flag_category,
                "source_text": info["source_text"],
                "confidence": classification.confidence,
            })

    total_confirmed = 0
    for auction_id in state["auction_ids"]:
        records = records_by_auction.get(auction_id, [])
        if records:
            save_mined_discrepancies(records)
        total_confirmed += len(records)

        expected = state["auction_expected_counts"].get(auction_id, 0)
        processed = auction_processed_counts.get(auction_id, 0)
        if processed >= expected:
            mark_auction_mined(auction_id)
        else:
            print(f"    {auction_id}: only {processed}/{expected} comments resolved, "
                  f"not marking mined yet")

    print(f"\nProcessed batch. Total confirmed discrepancies: {total_confirmed}")
    BATCH_STATE_PATH.unlink()
    print(f"Removed {BATCH_STATE_PATH} -- batch fully processed.")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("submit", "fetch"):
        print("Usage: python -m agents.run_comment_mining_batch [submit|fetch]")
        sys.exit(1)
    if sys.argv[1] == "submit":
        submit()
    else:
        fetch()
