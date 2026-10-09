"""Static configuration: data source, brand rules and brand palettes."""
from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
LOCAL_FALLBACK = ROOT / "data" / "Bank-Transfers.xlsx"

# Used only when st.secrets has no BANK_TRANSFERS_URL.
DEFAULT_BANK_TRANSFERS_URL = (
    "https://www.dropbox.com/scl/fi/0xn9ax9giix53pz0fsa8o/Bank-Transfers.xlsx"
    "?rlkey=7c3oz76jdcpeeq8awnaai2wqs&dl=1"
)

TZ = ZoneInfo("Asia/Yerevan")
CACHE_TTL_SECONDS = 600

# ---------------------------------------------------------------- brands --
# iiko writes the group as "China Town" and "Նանի"; both map to UI brand keys.
BRAND_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("ChinaTown", ("china", "чайна", "չայնա")),
    ("Nani", ("նանի", "nani", "нани")),
]
BRAND_OPTIONS = ["ChinaTown", "Nani", "All brands"]
ALL_BRANDS = "All brands"
DEFAULT_BRAND = "ChinaTown"

# Palette keys: accent (pills, bars), deep (hover/strong text), soft (chips),
# tint (card hover), bg (page), line (borders).
PALETTES: dict[str, dict[str, str]] = {
    "ChinaTown": {
        "accent": "#D9383A",
        "deep": "#A8262A",
        "soft": "#FCE8E7",
        "tint": "#FFF4F3",
        "bg": "#FFF9F8",
        "line": "#F3D9D7",
        "logo": "chinatown.png",
    },
    "Nani": {
        "accent": "#E6A100",
        "deep": "#B86E00",
        "soft": "#FFF1CC",
        "tint": "#FFF9EA",
        "bg": "#FFFCF5",
        "line": "#F1E3BF",
        "logo": "nani.png",
    },
    "All brands": {
        "accent": "#2F3B4C",
        "deep": "#1C2633",
        "soft": "#EBEEF2",
        "tint": "#F6F7F9",
        "bg": "#F9F9FB",
        "line": "#E2E5EA",
        "logo": "",
    },
}

# ----------------------------------------------------------------- dates --
PRESETS = ["Yesterday", "Last 7 Days", "This Month", "Custom Range"]
DEFAULT_PRESET = "Yesterday"
CUSTOM = "Custom Range"

# ----------------------------------------------------------- invoicing --
GROUP_PERIOD = "Whole period"
GROUP_DAY = "Per day"
NO_COUNTERPARTY = "Без контрагента"
