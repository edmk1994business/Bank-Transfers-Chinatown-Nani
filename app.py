"""Bank Transfers · Invoicing desk (ChinaTown & Nani).

Standalone Streamlit app for the accountant: inspects non-cash bank-transfer
orders (Փոխանցումով) from the iiko export `Bank-Transfers.xlsx` and prepares
per-counterparty invoice lines for Armenian e-Invoicing.

Run:  streamlit run app.py
"""
from __future__ import annotations

import hashlib
from functools import partial

import streamlit as st

from bank_transfers import dates, ui
from bank_transfers.config import (
    ALL_BRANDS, ASSETS, BRAND_OPTIONS, CUSTOM, DEFAULT_BRAND, GROUP_DAY, GROUP_PERIOD, PICK, PRESETS,
    RANGE_PRESETS,
)
from bank_transfers.data import clear_cache, load_transfers
from bank_transfers.export import (
    all_invoices_xlsx, invoice_csv, invoice_xlsx, safe_filename, tsv_b64,
)
from bank_transfers.invoices import (
    build_invoices, filter_rows, fmt_date, fmt_int, kpis, period_label, search_invoices,
)
from bank_transfers.theme import APP_JS, build_css

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

st.set_page_config(
    page_title="Bank Transfers · Invoicing",
    page_icon=str(ASSETS / "chinatown.png"),
    layout="wide",
    initial_sidebar_state="auto",
)

ss = st.session_state
ss.setdefault("brand", DEFAULT_BRAND)
ss.setdefault("grouping", GROUP_PERIOD)
dates.init_state()

# ?refresh=1 (used by the RPA after it overwrites the Dropbox file)
if st.query_params.get("refresh") == "1":
    clear_cache()
    del st.query_params["refresh"]

brand = ss.brand
st.html(build_css(brand))
with st.container(key="btjs"):
    st.html(APP_JS, unsafe_allow_javascript=True)

# ------------------------------------------------------------------ data --
try:
    with st.spinner("Loading Bank-Transfers.xlsx…"):
        res = load_transfers()
except Exception as exc:  # noqa: BLE001
    st.error(f"**Could not load the bank-transfer file.** {exc}")
    st.info("Check `BANK_TRANSFERS_URL` in the app secrets (a Dropbox share link ending in `dl=1`).")
    st.stop()

df_all = res.df
brand_rows = df_all if brand == ALL_BRANDS else df_all[df_all["brand"] == brand]
latest = max(brand_rows["date"]) if len(brand_rows) else None
pay_types = sorted(df_all["pay_type"].unique())

# --------------------------------------------------------------- sidebar --
with st.sidebar:
    st.html(ui.sidebar_brand(brand))

    with st.container(key="sbsec_1"):
        st.html(ui.section_title(1, "Brand"))
        st.radio("Brand", BRAND_OPTIONS, key="brand", horizontal=True, label_visibility="collapsed")

    with st.container(key="sbsec_2"):
        st.html(ui.section_title(2, "Period"))
        st.radio("Period", PRESETS, key="sb_preset", horizontal=True, label_visibility="collapsed",
                 on_change=dates.on_preset, args=("sb_preset",))
        if ss.d_preset == CUSTOM:
            st.date_input("Custom range", key="sb_range", format="DD.MM.YYYY", on_change=dates.on_sidebar_range)
        elif ss.d_preset == PICK:
            st.date_input("Pick date", key="sb_day", format="DD.MM.YYYY", max_value=dates.today(),
                          on_change=dates.on_day, args=("sb_day",))
        st.caption(f"{fmt_date(ss.d_start)} – {fmt_date(ss.d_end)}")

    with st.container(key="sbsec_3"):
        st.html(ui.section_title(3, "Invoice grouping"))
        st.radio("Invoice grouping", [GROUP_PERIOD, GROUP_DAY], key="grouping", horizontal=True,
                 label_visibility="collapsed")

    pay_filter = None
    if len(pay_types) > 1:
        ss.setdefault("pay_type", "All types")
        if ss.pay_type not in ["All types", *pay_types]:
            ss.pay_type = "All types"
        with st.container(key="sbsec_4"):
            st.html(ui.section_title(4, "Payment type"))
            st.radio("Payment type", ["All types", *pay_types], key="pay_type", horizontal=True,
                     label_visibility="collapsed")
        pay_filter = None if ss.pay_type == "All types" else ss.pay_type

    rep = res.report
    if rep.reconciles is True:
        check = '<span class="ok">✓ matches iiko «Итого»</span>'
    elif rep.reconciles is False:
        check = f'<span class="warn">Δ {fmt_int(rep.parsed_total - rep.file_total)} ֏ vs «Итого»</span>'
    else:
        check = "no «Итого» row to check"
    span = (f"{fmt_date(min(df_all['date']))} – {fmt_date(max(df_all['date']))}" if len(df_all) else "—")
    with st.container(key="sbsec_data"):
        st.html(
            f'<div class="data-card"><div class="sec-title" style="margin-bottom:6px">Data</div>'
            f"Source: <b>{res.source}</b> · loaded {res.loaded_at:%H:%M}<br>"
            f"File covers: <b>{span}</b><br>"
            f"Rows: <b>{len(df_all):,}</b> · total {fmt_int(rep.parsed_total)} ֏<br>{check}</div>"
        )
        if res.error:
            st.caption("Dropbox unavailable - showing the local copy.", help=res.error[:400])
        if st.button("Refresh data", icon=":material/refresh:", width="stretch"):
            clear_cache()
            st.rerun()

# ---------------------------------------------------------------- header --
start, end = ss.d_start, ss.d_end
with st.container(key="hdr"):
    left, right = st.columns([1.1, 1], vertical_alignment="center", gap="medium")
    with left:
        st.html(ui.header_identity(brand, start, end, latest))
    with right:
        st.radio("Quick period", PRESETS, key="hd_preset", horizontal=True, label_visibility="collapsed",
                 on_change=dates.on_preset, args=("hd_preset",))
        # Range presets -> Start / End inputs.  Yesterday / Pick Date -> one "Pick date" input.
        with st.container(key="hd_dates"):
            c1, c2 = st.columns(2, gap="small", wrap=False)
            if ss.d_preset in RANGE_PRESETS:
                c1.date_input("Start date", key="hd_start", format="DD.MM.YYYY", on_change=dates.on_header_dates)
                c2.date_input("End date", key="hd_end", format="DD.MM.YYYY", on_change=dates.on_header_dates)
            else:
                c1.date_input("Pick date", key="hd_day", format="DD.MM.YYYY", max_value=dates.today(),
                              on_change=dates.on_day, args=("hd_day",))

# ------------------------------------------------------------------- KPIs --
view = filter_rows(df_all, brand, start, end, pay_filter)
st.html(ui.kpi_grid(kpis(view)))

if view.empty:
    st.html(ui.empty_state(brand, start, end, latest))
    if latest is not None:
        st.button(f"Show {latest:%d %b %Y}", icon=":material/event:", type="primary",
                  on_click=dates.jump_to, args=(latest,))
    st.stop()

# -------------------------------------------------------- counterparties --
@st.fragment
def counterparties(view, brand: str, start, end, per_day: bool) -> None:
    """Search reruns only this fragment. Every card is always rendered; the browser
    script hides non-matching ones on each keystroke, while the committed query
    (live, after a short pause) drives the totals strip and the Excel export."""
    all_invoices = build_invoices(view, per_day=per_day)
    with st.container(key="toolbar"):
        t1, t2, t3 = st.columns([1.2, 1.6, 0.8], vertical_alignment="center", gap="small")
        query = t1.text_input(
            "Search", key="q", type="search", live="250ms", label_visibility="collapsed",
            placeholder="Search counterparty, item or amount…",
        ) or ""
        shown = search_invoices(all_invoices, query)
        with t2:
            st.html(ui.summary_strip(shown, query))
        t3.download_button(
            "Export all (Excel)", type="primary", icon=":material/download:", width="stretch",
            data=partial(all_invoices_xlsx, shown, start, end, per_day, brand, query),
            file_name=safe_filename("Bank_transfers", brand.replace(" ", ""), fmt_date(start), fmt_date(end),
                                    f"search-{query.strip()}" if query.strip() else "") + ".xlsx",
            mime=XLSX, on_click="ignore", key="exp_all",
        )

    st.html(ui.section_head(len(shown), per_day))
    st.html(ui.no_match(query, len(shown)))

    show_brand = brand == ALL_BRANDS
    for rank, inv in enumerate(all_invoices, 1):
        h = hashlib.md5(inv.key.encode("utf-8")).hexdigest()[:12]
        period = fmt_date(inv.dates[0]) if per_day else f"{fmt_date(start)} – {fmt_date(end)}"
        base = safe_filename("Invoice", inv.counterparty, inv.brand,
                             inv.dates[0].isoformat() if per_day else f"{start:%Y%m%d}-{end:%Y%m%d}")
        with st.container(key=f"cp_{h}"):
            st.html(ui.counterparty_card(inv, rank, show_brand, per_day, h))
            with st.popover("Copy / Export Invoice Summary (CSV/Excel)", icon=":material/ios_share:", key=f"pop_{h}"):
                st.html(ui.export_head(inv, period))
                st.html(ui.copy_button(tsv_b64(inv), len(inv.items)))
                d1, d2 = st.columns(2, gap="small")
                d1.download_button("CSV", data=partial(invoice_csv, inv, start, end), file_name=base + ".csv",
                                   mime="text/csv", on_click="ignore", icon=":material/description:",
                                   key=f"csv_{h}", width="stretch")
                d2.download_button("Excel", data=partial(invoice_xlsx, inv, start, end), file_name=base + ".xlsx",
                                   mime=XLSX, on_click="ignore", icon=":material/table_view:",
                                   key=f"xlsx_{h}", width="stretch")
                st.html(ui.COPY_NOTE)


counterparties(view, brand, start, end, ss.grouping == GROUP_DAY)

st.html(
    f'<div class="foot">Source: Bank-Transfers.xlsx (iiko OLAP) · amounts after discount, AMD · '
    f"{period_label(start, end)} · refreshed every 10 min</div>"
)
