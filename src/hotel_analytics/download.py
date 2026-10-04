"""Fetch the source CSV once and check it is the exact file the results were produced from."""

import hashlib
import urllib.request

from .config import RAW_CSV

URL = "https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2020/2020-02-11/hotels.csv"
SHA256 = "7c2ae42a7353905ea136e5c2287f17c92c5435826598bfbb8491c6f0c7b1fc06"


def _sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_raw_data() -> None:
    if not RAW_CSV.exists():
        RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL, RAW_CSV)
    actual = _sha256(RAW_CSV)
    if actual != SHA256:
        raise RuntimeError(f"{RAW_CSV} does not match the expected file (sha256 {actual}). Delete it and rerun.")
