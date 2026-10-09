"""Loading Bank-Transfers.xlsx from Dropbox (Streamlit secrets) with caching."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

from .config import CACHE_TTL_SECONDS, DEFAULT_BANK_TRANSFERS_URL, LOCAL_FALLBACK, TZ
from .parser import ParseReport, parse_bank_transfers


@dataclass
class LoadResult:
    df: pd.DataFrame
    report: ParseReport
    source: str          # "Dropbox" | "Local file"
    loaded_at: datetime
    error: str | None = None


def source_url() -> str:
    try:
        url = st.secrets.get("BANK_TRANSFERS_URL", "") or ""
    except Exception:  # noqa: BLE001 - no secrets.toml at all
        url = ""
    return direct_link(url.strip() or DEFAULT_BANK_TRANSFERS_URL)


def direct_link(url: str) -> str:
    """Dropbox share links need dl=1 to return the file instead of the preview page."""
    if "dropbox.com" not in url:
        return url
    if re.search(r"[?&]dl=0", url):
        return re.sub(r"([?&])dl=0", r"\1dl=1", url)
    if "dl=1" not in url:
        return url + ("&" if "?" in url else "?") + "dl=1"
    return url


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _download(url: str) -> tuple[bytes, str]:
    resp = requests.get(url, timeout=45)
    resp.raise_for_status()
    body = resp.content
    if body[:2] != b"PK":  # xlsx is a zip; anything else is an HTML/login page
        raise ValueError("Dropbox did not return an .xlsx file - check that the link is shared and ends with dl=1.")
    return body, datetime.now(TZ).isoformat()


@st.cache_data(show_spinner=False, max_entries=4)
def _parse(digest: str, _body: bytes) -> tuple[pd.DataFrame, ParseReport]:  # digest keys the cache
    return parse_bank_transfers(_body)


def load_transfers() -> LoadResult:
    url = source_url()
    err = None
    try:
        body, stamp = _download(url)
        source = "Dropbox"
        loaded_at = datetime.fromisoformat(stamp)
    except Exception as exc:  # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}"
        if not LOCAL_FALLBACK.exists():
            raise RuntimeError(f"Could not load Bank-Transfers.xlsx from Dropbox ({err}).") from exc
        body = LOCAL_FALLBACK.read_bytes()
        source = "Local file"
        loaded_at = datetime.fromtimestamp(LOCAL_FALLBACK.stat().st_mtime, TZ)
    df, report = _parse(hashlib.md5(body).hexdigest(), body)
    return LoadResult(df=df, report=report, source=source, loaded_at=loaded_at, error=err)


def clear_cache() -> None:
    _download.clear()
    _parse.clear()
