HOST = "https://carsandbids.com"
API_VERSION = "v1"
DB_PATH = "corpus/corpus.db"
PAGE_LIMIT = 100
SLEEP_BETWEEN_PAGES = 0.5
SLEEP_BETWEEN_AUCTIONS = 1.5

# ---- CHANGE THIS if Verification 2 (checking the Response tab) found a different key ----
COMMENTS_KEY = "comments_and_bids"
# -------------------------------------------------------------------------------------------

# Python's default User-Agent (something like "python-requests/2.31.0") gets blocked
# by Cloudflare's bot detection before the request ever reaches the site's own logic --
# this is why manual DevTools testing never hit this, since a real browser always sends
# a normal-looking User-Agent automatically. This makes every request look like it's
# coming from an actual browser instead.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://carsandbids.com/",
}
