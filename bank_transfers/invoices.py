"""Filtering, KPIs and per-counterparty invoice building (pure pandas)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

import pandas as pd

from .config import ALL_BRANDS
from .parser import split_dish


@dataclass
class Invoice:
    key: str
    counterparty: str
    brand: str
    pay_types: list[str]
    dates: list[date]
    qty: float
    amount: float
    share: float
    items: pd.DataFrame  # dish, en, am, qty, unit_price, amount

    @property
    def period_label(self) -> str:
        return period_label(min(self.dates), max(self.dates))


def filter_rows(df: pd.DataFrame, brand: str, start: date, end: date, pay_type: str | None = None) -> pd.DataFrame:
    m = (df["date"] >= start) & (df["date"] <= end)
    if brand != ALL_BRANDS:
        m &= df["brand"] == brand
    if pay_type:
        m &= df["pay_type"] == pay_type
    return df.loc[m]


def order_count(df: pd.DataFrame) -> tuple[int, str]:
    """Orders/checks. Real check numbers if the export has them, else one order
    per counterparty per day per brand (one transfer order -> one invoice)."""
    if df.empty:
        return 0, "orders"
    if "check_no" in df and df["check_no"].astype(str).str.len().gt(0).any():
        return int(df[["brand", "date", "check_no"]].drop_duplicates().shape[0]), "checks"
    return int(df[["brand", "date", "counterparty"]].drop_duplicates().shape[0]), "orders"


def kpis(df: pd.DataFrame) -> dict:
    sales = float(df["amount"].sum())
    qty = float(df["qty"].sum())
    orders, unit = order_count(df)
    by_cp = df.groupby("counterparty")["amount"].sum().sort_values(ascending=False)
    top = (by_cp.index[0], float(by_cp.iloc[0] / sales) if sales else 0.0) if len(by_cp) else None
    return {
        "sales": sales,
        "qty": qty,
        "counterparties": int(df["counterparty"].nunique()),
        "orders": orders,
        "order_unit": unit,
        "aov": sales / orders if orders else 0.0,
        "days": int(df["date"].nunique()),
        "dishes": int(df["dish"].nunique()),
        "top": top,
    }


def _items(rows: pd.DataFrame) -> pd.DataFrame:
    """One invoice line per (dish, exact unit price) so qty x price == total."""
    r = rows[["dish", "qty", "amount"]].copy()
    r["unit_price"] = (r["amount"] / r["qty"].where(r["qty"] != 0)).fillna(r["amount"]).round(2)
    it = r.groupby(["dish", "unit_price"], as_index=False, sort=False)[["qty", "amount"]].sum()
    it = it.sort_values(["amount", "dish"], ascending=[False, True]).reset_index(drop=True)
    names = it["dish"].map(split_dish)
    it["en"] = names.map(lambda t: t[0])
    it["am"] = names.map(lambda t: t[1])
    return it[["dish", "en", "am", "qty", "unit_price", "amount"]]


def build_invoices(df: pd.DataFrame, per_day: bool = False, sort: str = "Amount") -> list[Invoice]:
    if df.empty:
        return []
    total = float(df["amount"].sum()) or 1.0
    keys = ["counterparty", "brand"] + (["date"] if per_day else [])
    out: list[Invoice] = []
    for k, rows in df.groupby(keys, sort=False):
        k = k if isinstance(k, tuple) else (k,)
        cp, brand = k[0], k[1]
        dates = sorted(rows["date"].unique())
        key = "|".join([cp, brand] + ([dates[0].isoformat()] if per_day else []))
        out.append(Invoice(
            key=key, counterparty=cp, brand=brand,
            pay_types=sorted(rows["pay_type"].unique()), dates=dates,
            qty=float(rows["qty"].sum()), amount=float(rows["amount"].sum()),
            share=float(rows["amount"].sum()) / total, items=_items(rows),
        ))
    if sort == "Name":
        out.sort(key=lambda i: (i.counterparty.lower(), i.brand, i.dates[0]))
    elif sort == "Items":
        out.sort(key=lambda i: (-i.qty, -i.amount))
    elif sort == "Date":
        out.sort(key=lambda i: (i.dates[0], -i.amount))
    else:
        out.sort(key=lambda i: (-i.amount, i.counterparty.lower()))
    return out


# ---------------------------------------------------------------- search --
# Same rules as the browser-side instant filter in theme.APP_JS, so the
# summary totals and the Excel export always match what is on screen.
_NUMERIC_Q = re.compile(r"[0-9\s,.'֏]+")


def norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def amount_key(x: float) -> str:
    return str(int(round(float(x))))


def query_digits(q: str) -> str:
    """'46,000' / '46 000 ֏' -> '46000'; non-numeric queries -> ''."""
    return re.sub(r"[^0-9]", "", q) if _NUMERIC_Q.fullmatch(q) else ""


def search_match(inv: Invoice, query: str) -> tuple[bool, list[int]]:
    """Match counterparty name, item names or amounts (invoice total / line totals)."""
    q = norm_text(query)
    if not q:
        return True, []
    d = query_digits(q)
    name_hit = q in norm_text(inv.counterparty)
    total_hit = bool(d) and d in amount_key(inv.amount)
    rows = [
        i for i, r in enumerate(inv.items.itertuples())
        if q in norm_text(r.dish) or (bool(d) and d in amount_key(r.amount))
    ]
    return name_hit or total_hit or bool(rows), rows


def search_invoices(invoices: list[Invoice], query: str) -> list[Invoice]:
    return [i for i in invoices if search_match(i, query)[0]]


# ------------------------------------------------------------ formatting --
def fmt_int(x: float) -> str:
    return f"{x:,.0f}"


def fmt_qty(x: float) -> str:
    return f"{x:,.0f}" if float(x).is_integer() else f"{x:,.3f}".rstrip("0").rstrip(".")


def fmt_price(x: float) -> str:
    return f"{x:,.0f}" if round(x, 2).is_integer() else f"{x:,.2f}"


def fmt_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def period_label(start: date, end: date) -> str:
    if start == end:
        return start.strftime("%a, %d %b %Y")
    if start.year == end.year:
        return f"{start:%d %b} – {end:%d %b %Y}"
    return f"{start:%d %b %Y} – {end:%d %b %Y}"
