"""Parser for the iiko OLAP export `Bank-Transfers.xlsx`.

Pure pandas (no Streamlit) so it can be unit-tested.

The iiko export is pivot-style:
  * a few title rows, then a header row that contains `Учетный день`;
  * row dimensions (Группа > Учетный день > Блюдо > Тип оплаты > Контрагент)
    are written only on the first row of each block;
  * every level has a subtotal row such as `China Town всего`,
    `01.10.2026 всего`, `<dish> всего`, and the grand total row `Итого`.

The parser finds the header, drops subtotal rows, forward-fills the parent
dimensions and returns one clean row per (brand, day, dish, payment type,
counterparty).  A flat export (all values repeated) passes through unchanged.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from .config import BRAND_RULES, NO_COUNTERPARTY

# canonical name -> (keywords, positional fallback index from the spec A..G)
COLUMN_RULES: dict[str, tuple[tuple[str, ...], int | None]] = {
    "group": (("группа", "group", "ресторан"), 0),
    "date": (("учетный день", "учётный день", "дата", "date"), 1),
    "dish": (("блюдо", "dish", "item"), 2),
    "pay_type": (("тип оплаты", "payment type", "оплата"), 3),
    "counterparty": (("контрагент", "counterparty", "client"), 4),
    "qty": (("количество блюд", "количество", "qty", "quantity"), 5),
    "amount": (("сумма со скидкой", "сумма со скидки", "sales after", "amount"), 6),
    # optional: lets AOV use real check numbers if the report ever adds them
    "check_no": (("номер чека", "номер заказа", "check no", "order no"), None),
}
REQUIRED = ("group", "date", "dish", "pay_type", "counterparty", "qty", "amount")
DIMENSIONS = ("group", "date", "dish", "pay_type", "counterparty")

_SUBTOTAL_RE = re.compile(r"(\s|^)(всего|итого|total)\s*$", re.IGNORECASE)
_DISH_RE = re.compile(r"^\s*\((?P<en>[^()]+)\)\s*(?P<am>.*)$")


@dataclass
class ParseReport:
    header_row: int | None = None
    columns: dict[str, str] = field(default_factory=dict)
    raw_rows: int = 0
    subtotal_rows: int = 0
    data_rows: int = 0
    file_total: float | None = None      # value of the iiko `Итого` row, if any
    parsed_total: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def reconciles(self) -> bool | None:
        if self.file_total is None:
            return None
        return abs(self.file_total - self.parsed_total) < 0.5


# ------------------------------------------------------------ helpers --
def _norm(value) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _is_blank(value) -> bool:
    return _norm(value) == ""


def to_number(value) -> float:
    """Convert iiko numbers ('1 234,50', '1,234.5', 1234.5, '') to float."""
    if value is None:
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool):
        return float(value)
    s = _norm(value).replace(" ", "").replace(" ", "")
    s = s.replace("֏", "").replace("դր", "").replace("AMD", "")
    if s in ("", "-", "—"):
        return np.nan
    if "," in s and "." in s:
        s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if re.fullmatch(r"-?\d+,\d{1,2}", s) else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return np.nan


def to_date(value) -> date | None:
    """Accept datetime, Excel serial, 'YYYY-MM-DD', 'DD.MM.YYYY', 'DD/MM/YYYY'."""
    if value is None or _is_blank(value):
        return None
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float, np.integer, np.floating)):
        if 20000 < float(value) < 80000:  # Excel serial date
            return date(1899, 12, 30) + timedelta(days=int(value))
        return None
    s = _norm(value)
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mo, d = map(int, m.groups())
        return _safe_date(y, mo, d)
    m = re.match(r"^(\d{1,2})[./](\d{1,2})[./](\d{4})", s)
    if m:
        d, mo, y = map(int, m.groups())
        return _safe_date(y, mo, d)
    return None


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def map_brand(group: str) -> str:
    g = _norm(group).lower()
    for brand, keys in BRAND_RULES:
        if any(k in g for k in keys):
            return brand
    return _norm(group) or "Unknown"


def split_dish(name: str) -> tuple[str, str]:
    """'(Kung Pao Chicken) Կունգ Պաո' -> ('Kung Pao Chicken', 'Կունգ Պաո')."""
    s = _norm(name)
    m = _DISH_RE.match(s)
    if m and m.group("am"):
        return m.group("en").strip(), m.group("am").strip()
    if m:
        return m.group("en").strip(), ""
    return s, ""


def read_excel_fast(data: bytes) -> pd.DataFrame:
    """Read the first sheet with no header. calamine is ~10x faster than openpyxl."""
    try:
        return pd.read_excel(io.BytesIO(data), header=None, engine="calamine")
    except Exception:  # noqa: BLE001 - calamine missing or file quirk
        return pd.read_excel(io.BytesIO(data), header=None, engine="openpyxl")


# -------------------------------------------------------------- parser --
def _find_header_row(raw: pd.DataFrame, scan: int = 40) -> int | None:
    for i in range(min(scan, len(raw))):
        cells = [_norm(v).lower() for v in raw.iloc[i].tolist()]
        if any(c.startswith("учетный день") or c.startswith("учётный день") for c in cells):
            return i
    # English / renamed header fallback: a row holding at least 4 known labels
    for i in range(min(scan, len(raw))):
        cells = [_norm(v).lower() for v in raw.iloc[i].tolist()]
        hits = sum(
            any(c.startswith(k) for k in COLUMN_RULES[name][0] for c in cells if c)
            for name in REQUIRED
        )
        if hits >= 4:
            return i
    return None


def _match_columns(headers: list[str]) -> dict[str, int]:
    """Keyword match: exact > starts-with > contains, never the same column twice."""
    lowered = [_norm(h).lower().rstrip(",") for h in headers]
    taken: set[int] = set()
    found: dict[str, int] = {}
    for name, (keys, _) in COLUMN_RULES.items():
        best: tuple[int, int] | None = None  # (score, index)
        for idx, h in enumerate(lowered):
            if idx in taken or not h:
                continue
            base = h.split(",")[0].strip()
            for k in keys:
                score = 3 if base == k else 2 if base.startswith(k) else 1 if k in h else 0
                if score and (best is None or score > best[0]):
                    best = (score, idx)
        if best:
            found[name] = best[1]
            taken.add(best[1])
    return found


def parse_bank_transfers(data: bytes | pd.DataFrame) -> tuple[pd.DataFrame, ParseReport]:
    raw = data if isinstance(data, pd.DataFrame) else read_excel_fast(data)
    raw = raw.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
    raw.columns = range(raw.shape[1])
    rep = ParseReport()

    hdr = _find_header_row(raw)
    if hdr is None:
        rep.warnings.append("Header row not found - using column order A..G from the spec.")
        headers = [""] * raw.shape[1]
        body = raw
    else:
        rep.header_row = hdr
        headers = [_norm(v) for v in raw.iloc[hdr].tolist()]
        body = raw.iloc[hdr + 1:].reset_index(drop=True)

    cols = _match_columns(headers)
    for name in REQUIRED:
        if name not in cols:
            pos = COLUMN_RULES[name][1]
            if pos is not None and pos < raw.shape[1] and pos not in cols.values():
                cols[name] = pos
                if hdr is not None:
                    rep.warnings.append(f"Column for '{name}' matched by position ({_col_letter(pos)}).")
    missing = [n for n in REQUIRED if n not in cols]
    if missing:
        raise ValueError(f"Bank-Transfers.xlsx: could not find columns {missing}. Headers: {headers}")
    rep.columns = {n: (headers[i] or _col_letter(i)) for n, i in cols.items()}

    df = pd.DataFrame({n: body[i] for n, i in cols.items()})
    rep.raw_rows = len(df)

    # --- grand total + subtotal rows ------------------------------------
    dims = [d for d in DIMENSIONS if d in df]
    text = df[dims].map(_norm)
    is_grand = text.apply(lambda r: any(v.lower() in ("итого", "total", "grand total") for v in r), axis=1)
    if is_grand.any():
        totals = df.loc[is_grand, "amount"].map(to_number).dropna()
        if len(totals):
            rep.file_total = float(totals.iloc[-1])
    is_sub = text.apply(lambda r: any(bool(_SUBTOTAL_RE.search(v)) for v in r if v), axis=1)
    drop = is_grand | is_sub
    rep.subtotal_rows = int(drop.sum())
    df = df.loc[~drop].copy()

    # --- forward-fill parent dimensions (not the leaf) -------------------
    order = sorted(dims, key=lambda d: cols[d])
    leaf = order[-1]
    for d in order[:-1]:
        df[d] = df[d].map(lambda v: np.nan if _is_blank(v) else v).ffill()

    df["qty"] = df["qty"].map(to_number)
    df["amount"] = df["amount"].map(to_number)
    df = df.loc[df["qty"].notna() | df["amount"].notna()].copy()
    df[["qty", "amount"]] = df[["qty", "amount"]].fillna(0.0)

    df["date"] = df["date"].map(to_date)
    bad_dates = int(df["date"].isna().sum())
    if bad_dates:
        rep.warnings.append(f"{bad_dates} row(s) without a readable date were skipped.")
        df = df.loc[df["date"].notna()]

    df["group"] = df["group"].map(_norm)
    df["brand"] = df["group"].map(map_brand)
    df["dish"] = df["dish"].map(_norm).replace("", "—")
    df["pay_type"] = df["pay_type"].map(_norm).replace("", "—")
    df[leaf] = df[leaf].map(_norm)
    df["counterparty"] = df["counterparty"].map(_norm).replace("", NO_COUNTERPARTY)
    if "check_no" in df:
        df["check_no"] = df["check_no"].map(_norm)

    # Drop the iiko "дата всего"-style leftovers that have no numbers at all
    df = df.loc[(df["qty"] != 0) | (df["amount"] != 0)]

    keep = ["brand", "group", "date", "dish", "pay_type", "counterparty", "qty", "amount"]
    if "check_no" in df:
        keep.append("check_no")
    out = df[keep].reset_index(drop=True)
    rep.data_rows = len(out)
    rep.parsed_total = float(out["amount"].sum())
    return out, rep


def _col_letter(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s
