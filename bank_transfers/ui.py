"""HTML building blocks (header identity, KPI grid, counterparty cards)."""
from __future__ import annotations

from datetime import date
from html import escape

from .config import ALL_BRANDS, NO_COUNTERPARTY
from .invoices import Invoice, amount_key, fmt_int, fmt_price, fmt_qty, norm_text, period_label
from .theme import brand_logo

BANK_ICON = '<i class="ico ico-bank"></i>'
COPY_ICON = '<i class="ico ico-copy"></i>'


def _logos(brand: str, size: int = 112) -> str:
    brands = ["ChinaTown", "Nani"] if brand == ALL_BRANDS else [brand]
    return "".join(f'<img src="{brand_logo(b, size)}" alt="{b}">' for b in brands if brand_logo(b, size))


def sidebar_brand(brand: str) -> str:
    return (
        f'<div class="sb-brand"><div class="logos">{_logos(brand, 96)}</div>'
        f'<div><div class="t1">Bank Transfers</div><div class="t2">Invoicing desk · ChinaTown &amp; Nani</div></div></div>'
    )


def section_title(n: int, title: str) -> str:
    return f'<div class="sec-title"><span class="sec-num">{n}</span>{escape(title)}</div>'


def header_identity(brand: str, start: date, end: date, data_through: date | None) -> str:
    who = "ChinaTown + Nani" if brand == ALL_BRANDS else brand
    days = (end - start).days + 1
    through = (
        f'<span class="chip neutral">Data through {data_through:%d %b %Y}</span>' if data_through else ""
    )
    return (
        f'<div class="hdr-id"><div class="logos">{_logos(brand)}</div><div style="min-width:0">'
        f'<div class="eyebrow">Invoicing desk · {escape(who)}</div>'
        f'<div class="hdr-title">Bank Transfer Orders</div>'
        f'<div class="hdr-sub"><span class="chip">{BANK_ICON}'
        f'Փոխանցումով</span><span class="chip neutral">{period_label(start, end)} · {days} day{"s" if days != 1 else ""}</span>'
        f"{through}</div></div></div>"
    )


def kpi_grid(k: dict) -> str:
    top = (
        f'Top: <b>{escape(k["top"][0])}</b> · {k["top"][1]:.0%}' if k.get("top") else "No counterparties"
    )
    unit = "checks" if k["order_unit"] == "checks" else "orders"
    aov_note = (
        f'÷ <b>{fmt_int(k["orders"])}</b> {unit}'
        + ("" if unit == "checks" else ' <span title="One transfer order = one counterparty on one day">(counterparty-days)</span>')
    )
    cards = [
        ("Total transfer sales (֏)", f'{fmt_int(k["sales"])}<span class="cur">֏</span>',
         f'<b>{k["days"]}</b> day{"s" if k["days"] != 1 else ""} with transfers · after discount'),
        ("Total items sold", fmt_qty(k["qty"]), f'<b>{k["dishes"]}</b> different items'),
        ("Counterparties count", str(k["counterparties"]), top),
        ("Average order value", f'{fmt_int(k["aov"])}<span class="cur">֏</span>' if k["orders"] else "—", aov_note),
    ]
    body = "".join(
        f'<div class="kpi"><div class="kpi-label">{lbl}</div><div class="kpi-value">{val}</div>'
        f'<div class="kpi-sub">{sub}</div></div>'
        for lbl, val, sub in cards
    )
    return f'<div class="kpi-grid">{body}</div>'


def section_head(n: int, per_day: bool) -> str:
    hint = "One card per counterparty per day" if per_day else "One card per counterparty for the period"
    return (
        f'<div class="sec-head"><h3>Counterparties<span class="count" data-sum="cards">{n}</span></h3>'
        f'<span class="hint">{hint} · tap a card to see its invoice lines</span></div>'
    )


def checks_count(invoices: list[Invoice]) -> int:
    """Unique (counterparty, date, brand) combinations = transfer orders/checks.
    Cards are keyed by (counterparty, brand[, date]) so their day counts add up exactly."""
    return sum(len(i.dates) for i in invoices)


def summary_strip(invoices: list[Invoice], query: str) -> str:
    """Filtered totals beside the search box; the browser script keeps them live while typing."""
    n = checks_count(invoices)
    qty = sum(i.qty for i in invoices)
    amount = sum(i.amount for i in invoices)
    return (
        f'<div class="sumstrip" data-q="{escape(norm_text(query))}">'
        f'<div class="sum"><span class="lbl">Checks / Invoices</span><span class="val" data-sum="checks">{n}</span></div>'
        f'<div class="sum"><span class="lbl">Items QTY</span><span class="val" data-sum="qty">{fmt_qty(qty)}</span></div>'
        f'<div class="sum amount"><span class="lbl">Invoice sales</span><span class="val">'
        f'<span data-sum="amount">{fmt_int(amount)}</span><span class="cur">֏</span></span></div></div>'
    )


def no_match(query: str, n: int) -> str:
    hidden = "" if (query.strip() and n == 0) else " hidden"
    return (
        f'<div class="nomatch" data-nomatch{hidden}>No counterparty, item or amount matches '
        f'«<span class="q">{escape(query.strip())}</span>». Clear the search to see all cards.</div>'
    )


def counterparty_card(inv: Invoice, rank: int, show_brand: bool, per_day: bool, html_key: str) -> str:
    name = escape(inv.counterparty)
    name_cls = "cp-name" + (" muted" if inv.counterparty == NO_COUNTERPARTY else "")
    meta: list[str] = []
    if show_brand:
        logo = brand_logo(inv.brand, 48)
        meta.append(f'<span class="chip neutral">{f"<img src={logo!r} alt=>" if logo else ""}{escape(inv.brand)}</span>')
    if per_day:
        meta.append(f"<span>{inv.dates[0]:%a, %d %b %Y}</span>")
    else:
        nd = len(inv.dates)
        meta.append(f"<span>{nd} transfer day{'s' if nd != 1 else ''}</span>")
        meta.append('<span class="dot"></span>')
        meta.append(f"<span>{period_label(inv.dates[0], inv.dates[-1])}</span>")
    meta.append('<span class="dot"></span>')
    meta.append(f'<span class="share" title="Share of transfer sales in the selected period">{inv.share:.1%}</span>')
    meta.append('<span class="hitchip" hidden></span>')

    pays = "".join(f'<span class="pay">{BANK_ICON}{escape(p)}</span>' for p in inv.pay_types)
    stats = (
        f'<div class="cp-stats">'
        f'<div class="stat"><span class="lbl">Items QTY</span><span class="val">{fmt_qty(inv.qty)}</span></div>'
        f'<div class="stat amount"><span class="lbl">Invoice amount</span>'
        f'<span class="val">{fmt_int(inv.amount)}<span class="cur">֏</span></span></div>'
        f"{pays}</div>"
    )

    rows = []
    for r in inv.items.itertuples():
        am = f'<div class="dish-am">{escape(r.am)}</div>' if r.am else ""
        rows.append(
            f'<tr data-dish="{escape(norm_text(r.dish))}" data-amt="{amount_key(r.amount)}">'
            f'<td class="item"><div class="dish-en">{escape(r.en)}</div>{am}</td>'
            f'<td class="num" data-label="QTY">{fmt_qty(r.qty)}</td>'
            f'<td class="num" data-label="Unit price">{fmt_price(r.unit_price)}</td>'
            f'<td class="num" data-label="Total ֏">{fmt_int(r.amount)}</td></tr>'
        )
    days = "" if per_day else (
        '<div class="days">Transfer days: '
        + " · ".join(f"<b>{d:%d.%m}</b>" for d in inv.dates)
        + "</div>"
    )
    table = (
        '<div class="tbl-wrap"><table class="items"><thead><tr>'
        '<th>Item Name (Блюдо)</th><th class="num">Quantity (QTY)</th>'
        '<th class="num">Unit Price (AMD)</th><th class="num">Total Amount (AMD)</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'<tfoot><tr><td class="lbl">Invoice total · {len(inv.items)} line{"s" if len(inv.items) != 1 else ""}</td>'
        f'<td class="num" data-label="QTY">{fmt_qty(inv.qty)}</td><td class="blank"></td>'
        f'<td class="num" data-label="Total ֏">{fmt_int(inv.amount)}</td></tr></tfoot></table></div>'
    )
    return (
        f'<details class="cp" data-key="{escape(html_key)}" data-name="{escape(norm_text(inv.counterparty))}" '
        f'data-amount="{amount_key(inv.amount)}" data-total="{inv.amount:.2f}" data-qty="{inv.qty:g}" data-days="{len(inv.dates)}"><summary>'
        f'<span class="chev" aria-hidden="true"></span><span class="cp-rank">{rank:02d}</span>'
        f'<div class="cp-id"><div class="{name_cls}">{name}</div><div class="cp-meta">{"".join(meta)}</div></div>'
        f"{stats}</summary>"
        f'<div class="cp-body">{days}{table}</div></details>'
    )


def export_head(inv: Invoice, period: str) -> str:
    n = len(inv.items)
    return (
        f'<div class="exp-head">{escape(inv.counterparty)}</div>'
        f'<div class="exp-sub">{escape(inv.brand)} · {escape(period)} · <b>{fmt_int(inv.amount)} ֏</b> · '
        f'{n} line{"s" if n != 1 else ""}</div>'
    )


def copy_button(b64: str, rows: int) -> str:
    return (
        f'<button type="button" class="copy-btn" data-copy="{b64}" data-rows="{rows}">{COPY_ICON}'
        f'<span class="lbl">Copy {rows} item row{"s" if rows != 1 else ""}</span></button>'
    )


COPY_NOTE = (
    '<div class="copy-note">Copies <b>Item · QTY · Unit price · Total</b> as tab-separated rows - paste into '
    "Excel or the e-Invoicing item grid. CSV is UTF-8, so Armenian names open correctly in Excel.</div>"
)


def empty_state(brand: str, start: date, end: date, latest: date | None) -> str:
    who = "ChinaTown and Nani" if brand == ALL_BRANDS else brand
    tail = f"The latest transfer in the file is on <b>{latest:%a, %d %b %Y}</b>." if latest else "The file has no transfers for this brand."
    return (
        f'<div class="empty"><div class="big">No bank-transfer orders in this period</div>'
        f"{escape(who)} · {period_label(start, end)}<br>{tail}</div>"
    )
