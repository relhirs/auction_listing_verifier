import time
from dataclasses import dataclass

import requests

from corpus.config import HOST, API_VERSION


@dataclass
class TiniToken:
    farsce: str
    gi_ase: str


def get_ti_ni(session: requests.Session) -> TiniToken:
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
