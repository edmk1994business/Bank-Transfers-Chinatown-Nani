"""Parser tests against a mock pivot export. Run: python -m pytest -q"""
from __future__ import annotations

import io
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bank_transfers.parser import parse_bank_transfers, split_dish, to_date, to_number  # noqa: E402
import make_sample  # noqa: E402


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    path = tmp_path_factory.mktemp("x") / "Bank-Transfers.xlsx"
    rows = make_sample.build_rows(date(2026, 9, 1), date(2026, 10, 8))
    q, a = make_sample.write_pivot(str(path), rows)
    return path.read_bytes(), rows, q, a


def test_totals_reconcile_with_itogo(sample):
    data, rows, q, a = sample
    df, rep = parse_bank_transfers(data)
    assert rep.header_row is not None  # index after blank rows are dropped
    assert rep.file_total == a
    assert rep.reconciles is True
    assert df["qty"].sum() == q
    assert df["amount"].sum() == a
    assert not df["dish"].str.contains("всего").any()
    assert not df["counterparty"].str.contains("всего").any()


def test_forward_fill_matches_source(sample):
    data, rows, *_ = sample
    df, _ = parse_bank_transfers(data)
    src = pd.DataFrame(rows, columns=["group", "date", "dish", "pay", "cp", "qty", "amount"])
    src["cp"] = src["cp"].fillna("Без контрагента")
    exp = src.groupby(["group", "date", "cp"])["amount"].sum().sort_index()
    got = df.groupby(["group", "date", "counterparty"])["amount"].sum().sort_index()
    got.index.names = exp.index.names
    pd.testing.assert_series_equal(exp, got, check_dtype=False)
    assert set(df["brand"]) == {"ChinaTown", "Nani"}


def test_flat_export_and_text_numbers():
    raw = pd.DataFrame([
        ["Группа", "Учетный день", "Блюдо", "Тип оплаты", "Контрагент", "Количество блюд", "Сумма со скидкой, դր"],
        ["Նանի", "01.10.2026", "(Dolma) Տոլմա", "Փոխանցումով", "Doping", "3", "8 700,00"],
        ["Նանի", "2026-10-01", "(Tan) Թան", "Փոխանցումով", "Doping", 2, 1200],
        ["Итого", None, None, None, None, 5, 9900],
    ])
    df, rep = parse_bank_transfers(raw)
    assert list(df["amount"]) == [8700.0, 1200.0]
    assert set(df["date"]) == {date(2026, 10, 1)}
    assert rep.reconciles is True


def test_helpers():
    assert to_number("1 234,50") == 1234.5
    assert to_number("1,234.5") == 1234.5
    assert to_number("12,000") == 12000
    assert to_date("2026-10-09") == date(2026, 10, 9)
    assert to_date("09.10.2026") == date(2026, 10, 9)
    assert to_date(46304) == date(2026, 10, 9)
    assert split_dish("(Kung Pao Chicken) Կունգ Պաո հավ") == ("Kung Pao Chicken", "Կունգ Պաո հավ")
    assert split_dish("Coca-Cola 0.5") == ("Coca-Cola 0.5", "")
