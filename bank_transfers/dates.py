"""Date presets and the single shared date state (d_preset / d_start / d_end).

Single-day presets (Yesterday, Pick Date) drive one "Pick date" input;
range presets (Last 7 Days, This Month, Custom Range) drive Start / End inputs.
Header and sidebar widgets all mirror the same canonical state.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import streamlit as st

from .config import CUSTOM, DEFAULT_PRESET, PICK, PRESETS, TZ


def today() -> date:
    return datetime.now(TZ).date()


def yesterday() -> date:
    return today() - timedelta(days=1)


def preset_range(preset: str, t: date | None = None) -> tuple[date, date]:
    t = t or today()
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
_FIXED = (CUSTOM, PICK)  # user-chosen dates, never recomputed


def init_state() -> None:
    ss = st.session_state
    ss._pill_clicked = False  # callbacks of this rerun are done; reset the guard
    if "d_preset" not in ss or ss.d_preset not in PRESETS:
        ss.d_preset = DEFAULT_PRESET
        ss.d_start, ss.d_end = preset_range(DEFAULT_PRESET)
    if ss.d_preset not in _FIXED:  # keep rolling presets current (e.g. after midnight)
        ss.d_start, ss.d_end = preset_range(ss.d_preset)
    for k in _PRESET_WIDGETS:
        if ss.get(k) not in PRESETS:
            ss[k] = ss.d_preset
    ss.setdefault("hd_start", ss.d_start)
    ss.setdefault("hd_end", ss.d_end)
    ss.setdefault("sb_range", (ss.d_start, ss.d_end))
    ss.setdefault("hd_day", ss.d_start)
    ss.setdefault("sb_day", ss.d_start)


def _apply(preset: str, start: date, end: date) -> None:
    ss = st.session_state
    if start > end:
        start, end = end, start
    ss.d_preset, ss.d_start, ss.d_end = preset, start, end
    for k in _PRESET_WIDGETS:
        ss[k] = preset
    ss.hd_start, ss.hd_end = start, end
    ss.sb_range = (start, end)
    ss.hd_day = ss.sb_day = start


def _single_day(day: date) -> None:
    """One exact day: shown as Yesterday when it is yesterday, else as Pick Date."""
    _apply("Yesterday" if day == yesterday() else PICK, day, day)


def on_preset(src: str) -> None:
    ss = st.session_state
    p = ss[src]
    if p is None:
        return
    ss._pill_clicked = True  # a pill click beats a date field blurred by the same click
    if p == CUSTOM:
        _apply(CUSTOM, ss.d_start, ss.d_end)
    elif p == PICK:
        # keep the current day if one is selected, otherwise start from yesterday
        day = ss.d_start if ss.d_start == ss.d_end else yesterday()
        _apply(PICK, day, day)
    else:
        _apply(p, *preset_range(p))


def on_day(src: str) -> None:
    ss = st.session_state
    if ss.get("_pill_clicked"):
        return
    day = ss[src]
    if day:
        _single_day(day)


def on_header_dates() -> None:
    ss = st.session_state
    if ss.get("_pill_clicked"):
        return
    if ss.hd_start and ss.hd_end:
        _apply(CUSTOM, ss.hd_start, ss.hd_end)


def on_sidebar_range() -> None:
    r = st.session_state.sb_range
    if isinstance(r, (tuple, list)) and len(r) == 2:  # ignore half-picked ranges
        _apply(CUSTOM, r[0], r[1])


def jump_to(day: date) -> None:
    _single_day(day)
