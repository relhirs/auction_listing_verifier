import hashlib

from corpus.config import API_VERSION
from corpus.auth import TiniToken


def sign_request(path: str, tini: TiniToken, timestamp_ms: str) -> str:
    string_to_hash = f"{tini.farsce}_{timestamp_ms}_/{API_VERSION}/{path}{tini.gi_ase}"
    return hashlib.sha1(string_to_hash.encode("utf-8")).hexdigest()


def self_test() -> bool:
    """
    Paste in ONE set of real, manually-captured values here.
    This reproduces the exact by-hand test from before, just in code.
    """
    farsce = "5353ffcd-2736-4be6-b1a8-90fdc1d44fe4"
    gi_ase = "5c23e10f-d7d6-40e2-bc27-193859c4c5b5"
    timestamp = "1785094051573"
    auction_id = "KmeERw6p"
    expected_signature = "4286015fa895e782e079d04431d5a6375660f0e3"

    tini = TiniToken(farsce=farsce, gi_ase=gi_ase)
    path = f"autos/auctions/{auction_id}/comments"
    computed = sign_request(path, tini, timestamp)

    print("String that was hashed would use these pieces:")
    print(f"  farsce:    {farsce}")
    print(f"  timestamp: {timestamp}")
    print(f"  path:      {path}")
    print(f"  gi_ase:    {gi_ase}")
    print(f"Computed signature: {computed}")
    print(f"Expected signature: {expected_signature}")
    match = computed == expected_signature
    print(f"Match: {match}")
    return match


if __name__ == "__main__":
    print("=== self-test the signature formula ===\n")
    if not self_test():
        print("\nSelf-test FAILED.")
    else:
        print("\nSelf-test PASSED.")
