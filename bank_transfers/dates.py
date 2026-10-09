"""Date presets and the single shared date state (d_preset / d_start / d_end)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import streamlit as st

from .config import CUSTOM, DEFAULT_PRESET, PRESETS, TZ


def today() -> date:
    return datetime.now(TZ).date()


def preset_range(preset: str, t: date | None = None) -> tuple[date, date]:
    t = t or today()
    if preset == "Today":
        return t, t
    if preset == "Yesterday":
        y = t - timedelta(days=1)
        return y, y
    if preset == "Last 7 Days":
        return t - timedelta(days=6), t
    if preset == "This Month":
        return t.replace(day=1), t
    raise ValueError(preset)


# Widgets that mirror the canonical state: sidebar + header controls.
_PRESET_WIDGETS = ("sb_preset", "hd_preset")


def init_state() -> None:
    ss = st.session_state
    if "d_preset" not in ss or ss.d_preset not in PRESETS:
        ss.d_preset = DEFAULT_PRESET
        ss.d_start, ss.d_end = preset_range(DEFAULT_PRESET)
    if ss.d_preset != CUSTOM:  # keep rolling presets current (e.g. after midnight)
        ss.d_start, ss.d_end = preset_range(ss.d_preset)
    for k in _PRESET_WIDGETS:
        if ss.get(k) not in PRESETS:
            ss[k] = ss.d_preset
    ss.setdefault("hd_start", ss.d_start)
    ss.setdefault("hd_end", ss.d_end)
    ss.setdefault("sb_range", (ss.d_start, ss.d_end))


def _apply(preset: str, start: date, end: date) -> None:
    ss = st.session_state
    if start > end:
        start, end = end, start
    ss.d_preset, ss.d_start, ss.d_end = preset, start, end
    for k in _PRESET_WIDGETS:
        ss[k] = preset
    ss.hd_start, ss.hd_end = start, end
    ss.sb_range = (start, end)


def on_preset(src: str) -> None:
    p = st.session_state[src]
    if p is None:
        return
    if p == CUSTOM:
        _apply(CUSTOM, st.session_state.d_start, st.session_state.d_end)
    else:
        _apply(p, *preset_range(p))


def on_header_dates() -> None:
    ss = st.session_state
    if ss.hd_start and ss.hd_end:
        _apply(CUSTOM, ss.hd_start, ss.hd_end)


def on_sidebar_range() -> None:
    r = st.session_state.sb_range
    if isinstance(r, (tuple, list)) and len(r) == 2:  # ignore half-picked ranges
        _apply(CUSTOM, r[0], r[1])


def jump_to(day: date) -> None:
    _apply(CUSTOM, day, day)
