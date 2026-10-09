"""Design system: brand tokens + the full CSS for the invoicing app.

Targets Streamlit ==1.64.0 (react-aria radio/date markup). Selectors use
`data-testid` hooks and `st-key-*` classes so they survive emotion hash changes.
"""
from __future__ import annotations

import base64
import io
from urllib.parse import quote
from functools import lru_cache

from .config import ASSETS, PALETTES

INK = "#171A1F"
MUTED = "#6B7280"


# ----------------------------------------------------------- colour utils --
def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _lum(hex_color: str) -> float:
    def ch(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _rgb(hex_color)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def on_color(bg: str) -> str:
    """Readable text colour on a filled pill: white if it reaches 4.5:1, else ink."""
    white = 1.05 / (_lum(bg) + 0.05)
    return "#FFFFFF" if white >= 4.5 else "#1F1300"


# ------------------------------------------------------------------ logos --
@lru_cache(maxsize=8)
def logo_data_uri(filename: str, size: int = 96) -> str:
    """Small PNG data URI so logos can sit inside st.html cards."""
    if not filename:
        return ""
    path = ASSETS / filename
    if not path.exists():
        return ""
    try:
        from PIL import Image, ImageChops

        im = Image.open(path).convert("RGB")
        # Trim plain margins (the ChinaTown mark sits small on a white square),
        # then re-pad to a square so it stays legible at 40-50 px.
        bgc = im.getpixel((0, 0))
        bbox = ImageChops.difference(im, Image.new("RGB", im.size, bgc)).convert("L").point(
            lambda v: 255 if v > 24 else 0).getbbox()
        if bbox and (bbox[2] - bbox[0]) < im.width * 0.8:
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            side = int(max(w, h) * 1.28)
            sq = Image.new("RGB", (side, side), bgc)
            sq.paste(im.crop(bbox), ((side - w) // 2, (side - h) // 2))
            im = sq
        im.thumbnail((size, size))
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        raw = buf.getvalue()
    except Exception:  # noqa: BLE001 - Pillow missing: ship the original
        raw = path.read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode()


def brand_logo(brand: str, size: int = 96) -> str:
    return logo_data_uri(PALETTES.get(brand, {}).get("logo", ""), size)


# ------------------------------------------------------------------ icons --
# st.html strips inline <svg>, so icons are CSS masks (percent-encoded SVG).
_SVG = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' " \
       "stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'>{}</svg>"
ICONS = {
    "bank": "<path d='M3 10h18L12 4 3 10z'/><path d='M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 20h18'/>",
    "copy": "<rect x='9' y='9' width='11' height='11' rx='2.5'/><path d='M5 15V6a2 2 0 0 1 2-2h9'/>",
    "filter": "<path d='M4 6h16M7 12h10M10 18h4'/>",
    "cal": "<rect x='3.5' y='5' width='17' height='15.5' rx='2.5'/><path d='M3.5 10h17M8 3v4M16 3v4'/>",
}


def _icon_vars() -> str:
    return " ".join(
        f'--ico-{k}:url("data:image/svg+xml,{quote(_SVG.format(v), safe="")}");' for k, v in ICONS.items()
    )


# -------------------------------------------------------------------- CSS --
HIDE_STREAMLIT_CHROME = """
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="stHeader"] {display: none !important;}
[data-testid="stToolbar"] {display: none !important;}
.viewerBadge_container__1s52n, .stAppViewerFooter {display: none !important;}

div[class*="stAppToolbar"],
div[data-testid="stDecoration"],
[data-testid="stStatusWidget"] {
    display: none !important;
}

.block-container {
    padding-bottom: 5rem !important;
}
"""


def build_css(brand: str) -> str:
    p = PALETTES[brand]
    acc, deep, soft, tint, bg, line = (p[k] for k in ("accent", "deep", "soft", "tint", "bg", "line"))
    r, g, b = _rgb(acc)
    strip = (
        "linear-gradient(90deg,#D9383A 0%,#D9383A 50%,#E6A100 50%,#E6A100 100%)"
        if brand == "All brands" else acc
    )
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Armenian:wght@400;500;600;700&display=swap');

:root {{
  --acc:{acc}; --deep:{deep}; --soft:{soft}; --tint:{tint}; --bg:{bg}; --line:{line};
  --on:{on_color(acc)}; --acc-rgb:{r},{g},{b}; --ink:{INK}; --muted:{MUTED};
  --strip:{strip};
  {_icon_vars()}
  --card:#FFFFFF; --hair:#EEF0F3; --radius:16px;
  --shadow:0 1px 2px rgba(16,24,40,.04),0 4px 14px -6px rgba(16,24,40,.08);
  --font:'Inter','Noto Sans Armenian',system-ui,-apple-system,'Segoe UI',sans-serif;
}}
{HIDE_STREAMLIT_CHROME}

/* ---------- icons ---------- */
.ico {{ display:inline-block; flex:none; width:14px; height:14px; background:currentColor;
  -webkit-mask:var(--m) center/contain no-repeat; mask:var(--m) center/contain no-repeat; }}
.ico-bank {{ --m:var(--ico-bank); }} .ico-copy {{ --m:var(--ico-copy); width:16px; height:16px; }}
.ico-cal {{ --m:var(--ico-cal); }}

/* ---------- base ---------- */
.stApp, [data-testid="stAppViewContainer"] {{ background: var(--bg); }}
.stApp, .stApp p, .stApp label, .stApp input, .stApp button, .stApp td, .stApp th,
.stApp summary, .stApp div[data-testid="stMarkdownContainer"] {{ font-family: var(--font); }}
html, body, [data-testid="stMain"] {{ overflow-x: clip; }}
.block-container {{ padding-top: 1.25rem !important; max-width: 1240px; }}
[data-testid="stMainBlockContainer"] {{ padding-left: 1.4rem; padding-right: 1.4rem; }}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"] {{ padding-left: .8rem; padding-right: .8rem; padding-top: .8rem !important; }}
}}

.st-key-btjs, .st-key-btjs * {{ display:none !important; }}
[data-testid="stLayoutWrapper"]:has(> .st-key-btjs) {{ display:none !important; }}
[data-testid="stElementContainer"]:has(.st-key-btjs) {{ display:none !important; }}

/* ---------- pills: every horizontal st.radio becomes a pill row ---------- */
[data-testid="stRadioGroup"] {{ display:flex; flex-wrap:wrap; gap:6px !important; }}
[data-testid="stRadioOption"] {{
  background:#fff; border:1px solid var(--line); border-radius:999px;
  padding:6px 13px !important; margin:0 !important; min-height:0;
  cursor:pointer; transition:background .15s, border-color .15s, box-shadow .15s, transform .1s;
}}
[data-testid="stRadioOption"] > div {{ gap:0 !important; }}
[data-testid="stRadioOption"] > div > div:not([data-testid="stMarkdownContainer"]) {{ display:none !important; }}
[data-testid="stRadioOption"] p {{ margin:0 !important; font-size:13px !important; font-weight:600; color:var(--ink); line-height:1.25; white-space:nowrap; }}
[data-testid="stRadioOption"]:hover {{ border-color:var(--acc); background:var(--tint); }}
[data-testid="stRadioOption"]:active {{ transform:scale(.97); }}
[data-testid="stRadioOption"][data-selected="true"] {{
  background:var(--acc); border-color:var(--acc);
  box-shadow:0 3px 10px -4px rgba(var(--acc-rgb),.75);
}}
[data-testid="stRadioOption"][data-selected="true"] p {{ color:var(--on) !important; }}
[data-testid="stRadio"] > label[data-testid="stWidgetLabel"] p {{ font-size:12px; color:var(--muted); font-weight:600; }}

/* ---------- inputs ---------- */
[data-testid="stDateInputField"], [data-testid="stTextInputRootElement"] {{
  border-radius:12px !important; background:#fff !important; border-color:var(--line) !important;
}}
[data-testid="stDateInputField"]:focus-within, [data-testid="stTextInputRootElement"]:focus-within {{
  border-color:var(--acc) !important; box-shadow:0 0 0 3px rgba(var(--acc-rgb),.14) !important;
}}
[data-testid="stDateInput"] label p, [data-testid="stTextInput"] label p {{ font-size:12px; font-weight:600; color:var(--muted); }}

/* ---------- buttons ---------- */
.stApp button[kind="secondary"], .stApp button[data-testid="stPopoverButton"],
.stApp [data-testid="stDownloadButton"] button {{
  border-radius:11px; border:1px solid var(--line); background:#fff; color:var(--ink);
  font-weight:600; transition:all .15s;
}}
.stApp button[kind="secondary"]:hover, .stApp button[data-testid="stPopoverButton"]:hover,
.stApp [data-testid="stDownloadButton"] button:hover {{
  border-color:var(--acc); color:var(--deep); background:var(--tint);
}}
.stApp button[kind="primary"], .stApp [data-testid="stDownloadButton"] button[kind="primary"] {{
  background:var(--acc); border-color:var(--acc); color:var(--on); border-radius:11px; font-weight:700;
}}
.stApp button[kind="primary"]:hover {{ background:var(--deep); border-color:var(--deep); color:#fff; }}
.stApp button p {{ font-size:13.5px; }}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {{ background:#FFFFFF; border-right:1px solid var(--line); }}
[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {{ height:.5rem; min-height:.5rem; padding:0; }}
[data-testid="stSidebarUserContent"] {{ padding-top:.4rem; }}
.sb-brand {{ display:flex; align-items:center; gap:10px; padding:2px 2px 10px; }}
.sb-brand .logos {{ display:flex; }}
.sb-brand img {{ width:38px; height:38px; border-radius:10px; object-fit:cover; border:1px solid var(--line); background:#fff; }}
.sb-brand .logos {{ gap:4px; }}
.sb-brand .t1 {{ font-weight:800; font-size:15px; color:var(--ink); letter-spacing:-.01em; line-height:1.15; }}
.sb-brand .t2 {{ font-size:11.5px; color:var(--muted); }}
[class*="st-key-sbsec_"] {{
  background:var(--tint); border:1px solid var(--line); border-radius:14px;
  padding:12px 12px 13px; gap:.55rem;
}}
.sec-title {{ display:flex; align-items:center; gap:8px; font-size:12px; font-weight:700;
  text-transform:uppercase; letter-spacing:.07em; color:var(--ink); }}
.sec-num {{ width:20px; height:20px; border-radius:7px; background:var(--acc); color:var(--on);
  display:inline-grid; place-items:center; font-size:11px; font-weight:800; letter-spacing:0; }}
.data-card {{ font-size:12px; color:var(--muted); line-height:1.6; }}
.data-card b {{ color:var(--ink); font-weight:600; }}
.ok {{ color:#0F7B45; font-weight:600; }} .warn {{ color:#B42318; font-weight:600; }}

/* ---------- header ---------- */
.st-key-hdr {{
  background:var(--card); border:1px solid var(--line); border-radius:20px;
  padding:18px 20px 16px; box-shadow:var(--shadow); position:relative; overflow:hidden; gap:.6rem;
}}
.st-key-hdr::before {{ content:""; position:absolute; inset:0 0 auto 0; height:4px; background:var(--strip); }}
.hdr-id {{ display:flex; align-items:center; gap:14px; min-width:0; }}
.hdr-id .logos {{ display:flex; flex:none; }}
.hdr-id img {{ width:54px; height:54px; border-radius:14px; object-fit:cover; border:1px solid var(--line); background:#fff; }}
.hdr-id .logos {{ gap:6px; }}
.eyebrow {{ font-size:11px; font-weight:700; letter-spacing:.12em; text-transform:uppercase; color:var(--deep); }}
.hdr-title {{ font-size:26px; font-weight:800; letter-spacing:-.02em; color:var(--ink); line-height:1.15; margin:1px 0 3px; }}
.hdr-sub {{ font-size:13px; color:var(--muted); display:flex; gap:6px; flex-wrap:wrap; align-items:center; }}
.chip {{ display:inline-flex; align-items:center; gap:6px; border-radius:999px; padding:3px 10px;
  font-size:12px; font-weight:600; background:var(--soft); color:var(--deep); white-space:nowrap; }}
.chip.neutral {{ background:#F3F4F6; color:#4B5563; }}
.chip img {{ width:16px; height:16px; border-radius:4px; }}
@media (max-width: 640px) {{
  .st-key-hdr {{ padding:16px 14px 14px; border-radius:16px; }}
  .hdr-id {{ align-items:flex-start; gap:11px; }}
  .hdr-id img {{ width:40px; height:40px; border-radius:11px; }}
  .hdr-title {{ font-size:21px; }}
  .eyebrow {{ font-size:10px; letter-spacing:.08em; }}
  .hdr-sub {{ gap:5px; }}
  .chip {{ font-size:11.5px; padding:3px 9px; }}
}}

/* ---------- KPI cards ---------- */
.kpi-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin:4px 0 6px; }}
@media (max-width: 980px) {{ .kpi-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }} }}
.kpi {{ background:var(--card); border:1px solid var(--line); border-radius:var(--radius); padding:15px 16px 14px;
  box-shadow:var(--shadow); position:relative; overflow:hidden; min-width:0; transition:transform .2s; -webkit-tap-highlight-color:transparent; }}
.kpi::after {{ content:""; position:absolute; left:0; top:14px; bottom:14px; width:3px; border-radius:0 3px 3px 0; background:var(--acc); }}
.kpi:hover, .kpi:active {{ animation:kpiPulse 2s ease-out infinite; }}
@keyframes kpiPulse {{
  0% {{ box-shadow:0 0 0 0 rgba(var(--acc-rgb),.38); }}
  70% {{ box-shadow:0 0 0 11px rgba(var(--acc-rgb),0); }}
  100% {{ box-shadow:0 0 0 0 rgba(var(--acc-rgb),0); }}
}}
.kpi-label {{ font-size:11px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }}
.kpi-value {{ font-size:27px; font-weight:800; letter-spacing:-.02em; color:var(--ink); margin:6px 0 4px;
  font-variant-numeric:tabular-nums; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.kpi-value .cur {{ font-size:.62em; font-weight:700; color:var(--muted); margin-left:3px; }}
.kpi-sub {{ font-size:12px; color:var(--muted); line-height:1.4; }}
.kpi-sub b {{ color:var(--ink); font-weight:600; }}
@media (max-width: 640px) {{
  .kpi {{ padding:12px 12px 11px; }}
  .kpi-value {{ font-size:20px; }}
  .kpi-label {{ font-size:10px; letter-spacing:.06em; }}
  .kpi-sub {{ font-size:11px; }}
}}

/* ---------- section heading ---------- */
.sec-head {{ display:flex; align-items:baseline; justify-content:space-between; gap:10px; flex-wrap:wrap; margin:14px 0 0; }}
.sec-head h3 {{ font-size:19px; font-weight:800; letter-spacing:-.01em; color:var(--ink); margin:0; padding:0; }}
.sec-head h3 .count {{ display:inline-grid; place-items:center; min-width:24px; height:24px; padding:0 7px; margin-left:6px;
  border-radius:999px; background:var(--acc); color:var(--on); font-size:12px; vertical-align:3px; }}
.sec-head .hint {{ font-size:12.5px; color:var(--muted); }}

/* ---------- counterparty cards ---------- */
[class*="st-key-cp_"] {{
  background:var(--card); border:1px solid var(--line); border-radius:var(--radius);
  box-shadow:var(--shadow); gap:0; overflow:hidden; transition:border-color .15s, box-shadow .15s;
}}
[class*="st-key-cp_"]:hover {{ border-color:rgba(var(--acc-rgb),.45); }}
[class*="st-key-cp_"]:has(details[open]) {{ border-color:rgba(var(--acc-rgb),.55); box-shadow:0 10px 28px -14px rgba(var(--acc-rgb),.45); }}
[class*="st-key-cp_"] > [data-testid="stLayoutWrapper"],
[class*="st-key-cp_"] > [data-testid="stElementContainer"]:has([data-testid="stPopover"]) {{
  padding:10px 16px 14px; border-top:1px dashed var(--hair); width:100%;
}}
[class*="st-key-cp_"] [data-testid="stPopover"] {{ width:fit-content; }}
[class*="st-key-cp_"] button[data-testid="stPopoverButton"] {{ background:var(--tint); border-color:var(--line); width:auto; padding-left:14px; padding-right:12px; }}
@media (max-width: 640px) {{
  [class*="st-key-cp_"] [data-testid="stPopover"], [class*="st-key-cp_"] button[data-testid="stPopoverButton"] {{ width:100%; }}
}}
[class*="st-key-cp_"] button[data-testid="stPopoverButton"] p {{ font-size:13px; }}
[class*="st-key-cp_"] [data-testid="stIconMaterial"] {{ color:var(--deep); }}

details.cp {{ margin:0; }}
details.cp > summary {{
  list-style:none; cursor:pointer; display:grid; align-items:center; gap:10px 16px;
  grid-template-columns:auto minmax(0,1fr) auto auto; padding:15px 16px; -webkit-tap-highlight-color:transparent;
}}
details.cp > summary::-webkit-details-marker {{ display:none; }}
details.cp > summary:hover {{ background:var(--tint); }}
.cp-rank {{ width:32px; height:32px; border-radius:10px; background:var(--soft); color:var(--deep);
  font-weight:800; font-size:12px; display:grid; place-items:center; font-variant-numeric:tabular-nums; }}
.cp-id {{ min-width:0; }}
.cp-name {{ font-weight:700; font-size:16.5px; color:var(--ink); letter-spacing:-.01em; line-height:1.25;
  overflow-wrap:anywhere; }}
.cp-meta {{ font-size:12.5px; color:var(--muted); display:flex; gap:6px; align-items:center; flex-wrap:wrap; margin-top:3px; }}
.cp-meta .dot {{ width:3px; height:3px; border-radius:50%; background:#C3C7CE; }}
.cp-stats {{ display:flex; align-items:center; gap:18px; }}
.stat {{ display:flex; flex-direction:column; align-items:flex-end; }}
.stat .lbl {{ font-size:10.5px; font-weight:700; letter-spacing:.07em; text-transform:uppercase; color:var(--muted); }}
.stat .val {{ font-size:15px; font-weight:700; color:var(--ink); font-variant-numeric:tabular-nums; white-space:nowrap; }}
.stat.amount .val {{ font-size:18px; font-weight:800; }}
.stat .val .cur {{ font-size:.75em; color:var(--muted); margin-left:2px; }}
.pay {{ display:inline-flex; align-items:center; gap:5px; border-radius:999px; padding:4px 10px;
  background:var(--soft); color:var(--deep); font-size:12px; font-weight:600; white-space:nowrap; }}
.pay .ico {{ width:13px; height:13px; }}
.share {{ border-radius:999px; padding:2px 8px; background:#F3F4F6; color:#4B5563; font-size:11.5px; font-weight:600; }}
.chev {{ width:30px; height:30px; border-radius:50%; border:1px solid var(--line); display:grid; place-items:center;
  background:#fff; transition:transform .2s ease, background .15s; }}
.chev::before {{ content:""; width:7px; height:7px; border-right:2px solid var(--muted); border-bottom:2px solid var(--muted);
  transform:translateY(-2px) rotate(45deg); }}
details.cp[open] .chev {{ transform:rotate(180deg); background:var(--soft); }}

.cp-body {{ padding:0 16px 6px; animation:fadeIn .18s ease-out; }}
@keyframes fadeIn {{ from {{ opacity:0; transform:translateY(-3px); }} to {{ opacity:1; transform:none; }} }}
.cp-body .days {{ font-size:12px; color:var(--muted); padding:2px 0 10px; }}
.cp-body .days b {{ color:var(--ink); font-weight:600; }}
.tbl-wrap {{ border:1px solid var(--hair); border-radius:12px; overflow:hidden; margin-bottom:10px; }}
table.items {{ width:100%; border-collapse:collapse; font-size:14px; }}
table.items th {{ text-align:left; font-size:10.5px; font-weight:700; letter-spacing:.07em; text-transform:uppercase;
  color:var(--muted); background:var(--tint); padding:10px 12px; border-bottom:1px solid var(--line); white-space:nowrap; }}
table.items td {{ padding:10px 12px; border-bottom:1px solid var(--hair); color:var(--ink); font-weight:400; vertical-align:top; }}
table.items tbody tr:last-child td {{ border-bottom:none; }}
table.items tbody tr:hover td {{ background:#FAFBFC; }}
table.items .num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
table.items .idx {{ color:#9CA3AF; width:28px; font-variant-numeric:tabular-nums; }}
.dish-en {{ font-weight:400; color:var(--ink); line-height:1.35; }}
.dish-am {{ font-weight:400; color:var(--muted); font-size:12.5px; line-height:1.35; margin-top:1px; }}
table.items tfoot td {{ background:var(--tint); font-weight:700; border-top:1px solid var(--line); border-bottom:none; }}
@media (max-width: 760px) {{
  details.cp > summary {{ grid-template-columns:auto minmax(0,1fr) auto; grid-template-areas:"rank id chev" "stats stats stats"; padding:13px 13px; }}
  .cp-rank {{ grid-area:rank; }} .cp-id {{ grid-area:id; }} .chev {{ grid-area:chev; }}
  .cp-meta .dot {{ display:none; }} .cp-meta {{ gap:4px 8px; }}
  .cp-stats {{ grid-area:stats; justify-content:space-between; gap:10px; flex-wrap:wrap;
    background:var(--tint); border-radius:12px; padding:8px 11px; }}
  .stat {{ align-items:flex-start; }}
  .stat.amount .val {{ font-size:16px; }}
  .cp-body {{ padding:0 12px 4px; }}
  [class*="st-key-cp_"] > [data-testid="stLayoutWrapper"],
  [class*="st-key-cp_"] > [data-testid="stElementContainer"]:has([data-testid="stPopover"]) {{ padding:8px 12px 12px; }}
}}
@media (max-width: 560px) {{
  table.items thead {{ display:none; }}
  table.items, table.items tbody, table.items tfoot {{ display:block; }}
  table.items tr {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:4px 8px; padding:10px 12px; border-bottom:1px solid var(--hair); }}
  table.items tbody tr:last-child {{ border-bottom:none; }}
  table.items td {{ padding:0; border:none !important; background:none !important; }}
  table.items td.idx {{ display:none; }}
  table.items td.item {{ grid-column:1 / -1; padding-bottom:4px; }}
  table.items td.num {{ text-align:left; }}
  table.items td.num::before {{ content:attr(data-label); display:block; font-size:10px; font-weight:700;
    letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin-bottom:1px; }}
  table.items tfoot tr {{ background:var(--tint); }}
  table.items tfoot td.lbl {{ grid-column:1 / -1; }}
  table.items tfoot td.blank {{ display:none; }}
}}

/* ---------- popover (export) ---------- */
[data-testid="stPopoverBody"] {{ border-radius:16px !important; border:1px solid var(--line) !important;
  box-shadow:0 18px 40px -16px rgba(16,24,40,.28) !important; }}
.exp-head {{ font-size:14px; font-weight:700; color:var(--ink); }}
.exp-sub {{ font-size:12px; color:var(--muted); margin-top:2px; }}
.copy-btn {{ display:inline-flex; align-items:center; gap:8px; width:100%; justify-content:center;
  border:1px solid var(--acc); background:var(--acc); color:var(--on); border-radius:11px; padding:9px 14px;
  font:700 13.5px var(--font); cursor:pointer; transition:background .15s, transform .1s; }}
.copy-btn:hover {{ background:var(--deep); color:#fff; }}
.copy-btn:active {{ transform:scale(.98); }}
.copy-btn.done {{ background:#0F7B45; border-color:#0F7B45; color:#fff; }}
.copy-note {{ font-size:11.5px; color:var(--muted); line-height:1.45; margin-top:6px; }}

/* ---------- empty state / footer ---------- */
.empty {{ background:var(--card); border:1px dashed var(--line); border-radius:var(--radius); padding:34px 20px;
  text-align:center; color:var(--muted); }}
.empty .big {{ font-size:17px; font-weight:700; color:var(--ink); margin-bottom:4px; }}
.foot {{ font-size:11.5px; color:#9CA3AF; text-align:center; margin-top:22px; }}

/* ---------- floating "Filters" opener (header is hidden) ---------- */
#ns-filters {{
  position:fixed; z-index:999990; top:14px; left:14px; display:none; align-items:center; gap:7px;
  border:1px solid var(--line); background:#fff; color:var(--ink); border-radius:999px; padding:8px 14px 8px 11px;
  font:700 13px var(--font); box-shadow:0 8px 24px -10px rgba(16,24,40,.35); cursor:pointer;
}}
#ns-filters:hover {{ border-color:var(--acc); color:var(--deep); }}
#ns-filters .ico {{ --m:var(--ico-filter); width:16px; height:16px; }}
body:has([data-testid="stSidebar"][aria-expanded="false"]) #ns-filters {{ display:inline-flex; }}
@media (max-width: 640px) {{
  #ns-filters {{ top:auto; left:auto; right:14px; bottom:16px; background:var(--acc); color:var(--on); border-color:var(--acc);
    padding:11px 16px 11px 13px; }}
}}
</style>
"""


# One-time JS: copy buttons, remembered open cards, the floating Filters button.
APP_JS = """
<script>
(function () {
  if (window.__btInit) return; window.__btInit = true;
  var KEY = 'bt-open-cards';
  function openSet() { try { return new Set(JSON.parse(sessionStorage.getItem(KEY) || '[]')); } catch (e) { return new Set(); } }
  function saveSet(s) { try { sessionStorage.setItem(KEY, JSON.stringify(Array.from(s))); } catch (e) {} }

  // remember which counterparty cards are open across reruns
  document.addEventListener('toggle', function (e) {
    var d = e.target; if (!d.matches || !d.matches('details.cp[data-key]')) return;
    var s = openSet(); if (d.open) s.add(d.dataset.key); else s.delete(d.dataset.key); saveSet(s);
  }, true);
  function restore(root) {
    var s = openSet();
    (root.querySelectorAll ? root : document).querySelectorAll('details.cp[data-key]:not([data-restored])').forEach(function (d) {
      d.setAttribute('data-restored', '1'); if (s.has(d.dataset.key)) d.open = true;
    });
  }

  // copy invoice rows (base64 UTF-8 payload) to the clipboard
  function b64utf8(b) { var bin = atob(b); var bytes = new Uint8Array(bin.length);
    for (var i = 0; i !== bin.length; i++) bytes[i] = bin.charCodeAt(i); return new TextDecoder().decode(bytes); }
  function fallbackCopy(text) { var ta = document.createElement('textarea'); ta.value = text;
    ta.style.position = 'fixed'; ta.style.opacity = '0'; document.body.appendChild(ta); ta.select();
    var ok = false; try { ok = document.execCommand('copy'); } catch (e) {} document.body.removeChild(ta); return ok; }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-copy]'); if (!b) return;
    e.preventDefault(); var text = b64utf8(b.getAttribute('data-copy'));
    var label = b.querySelector('.lbl'); var orig = label ? label.textContent : '';
    function done(ok) { b.classList.toggle('done', ok);
      if (label) label.textContent = ok ? 'Copied ' + b.getAttribute('data-rows') + ' rows ✓' : 'Copy failed – use CSV';
      setTimeout(function () { b.classList.remove('done'); if (label) label.textContent = orig; }, 1800); }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(fallbackCopy(text)); });
    } else { done(fallbackCopy(text)); }
  });

  // floating Filters button: re-opens the sidebar when Streamlit's header is hidden
  function ensureFilters() {
    if (document.getElementById('ns-filters')) return;
    var btn = document.createElement('button'); btn.id = 'ns-filters'; btn.type = 'button';
    // no literal tags in this script: Streamlit drops st.html scripts that contain them
    var icon = document.createElement('i'); icon.className = 'ico';
    var txt = document.createElement('span'); txt.textContent = 'Filters';
    btn.appendChild(icon); btn.appendChild(txt);
    btn.addEventListener('click', function () {
      var t = document.querySelector('[data-testid="stExpandSidebarButton"]')
           || document.querySelector('[data-testid="stSidebarCollapsedControl"] button');
      if (t) t.click();
    });
    document.body.appendChild(btn);
  }

  restore(document); ensureFilters();
  new MutationObserver(function () { restore(document); ensureFilters(); })
    .observe(document.body, { childList: true, subtree: true });
})();
</script>
"""
