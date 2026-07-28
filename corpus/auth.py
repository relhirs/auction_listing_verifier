import time
from dataclasses import dataclass

import requests

from corpus.config import HOST, API_VERSION


@dataclass
class TiniToken:
    farsce: str
    gi_ase: str


def get_ti_ni(session: requests.Session) -> TiniToken:
    """Unsigned bootstrap call -- no signature needed for this specific request.

    Must reuse the same Session as later comment requests: this call sets an
    _sstk_ session cookie that the API's signature-verification middleware
    requires on every signed request. A bare requests.get() here drops that
    cookie and every following request 400s with "No Session token found".
    """
    timestamp = str(int(time.time() * 1000))
    url = f"{HOST}/{API_VERSION}/auth/ti_ni?timestamp={timestamp}"
    resp = session.get(url)
    resp.raise_for_status()
    data = resp.json()
    if "__farsce" not in data or "_gi_ase" not in data:
        raise ValueError(
            f"ti_ni response didn't contain the expected fields. "
            f"Actual keys returned: {list(data.keys())}"
        )
    return TiniToken(farsce=data["__farsce"], gi_ase=data["_gi_ase"])
