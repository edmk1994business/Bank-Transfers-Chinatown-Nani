"""Build a mock iiko OLAP export shaped like Bank-Transfers.xlsx (pivot style).

Usage:  python tests/make_sample.py data/Bank-Transfers.xlsx
Only for local testing - the real file comes from Dropbox.
"""
from __future__ import annotations

import random
import sys
from collections import defaultdict
from datetime import date, timedelta

from openpyxl import Workbook

random.seed(7)

MENU = {
    "China Town": [
        ("(Kung Pao Chicken) Կունգ Պաո հավ", 3500),
        ("(Egg Fried Rice) Տապակած բրինձ ձվով", 2200),
        ("(Spring Rolls) Գարնանային ռուլետ", 1800),
        ("(Sweet and Sour Pork) Քաղցր-թթու խոզ", 3900),
        ("(Wonton Soup) Վոնթոն ապուր", 2400),
        ("(Dim Sum Set) Դիմ սամ սեթ", 4600),
        ("(Jasmine Tea) Հասմիկի թեյ", 900),
        ("Coca-Cola 0.5", 700),
    ],
    "Նանի": [
        ("(Pork Khorovats) Խոզի խորոված", 4200),
        ("(Dolma) Տոլմա", 2900),
        ("(Lavash) Լավաշ", 300),
        ("(Ghapama) Ղափամա", 5200),
        ("(Tan) Թան", 600),
        ("(Gata) Գաթա", 1200),
        ("(Ishkhan Trout) Իշխան", 6100),
    ],
}
CLIENTS = {
    "China Town": ["Meridian", "Doping", "Arka Logistics", "Viva Group", "Sunrise LLC"],
    "Նանի": ["Meridian", "Ararat Consulting", "Doping", "Hayk Tours"],
}
PAY = "Փոխանցումով"


def build_rows(start: date, end: date):
    rows = []  # (group, day, dish, pay, client, qty, amount)
    d = start
    while d <= end:
        for group in MENU:
            if random.random() < 0.45:
                d += timedelta(0)
                for client in random.sample(CLIENTS[group], k=random.randint(1, 2)):
                    for dish, price in random.sample(MENU[group], k=random.randint(2, 5)):
                        qty = random.randint(1, 8)
                        disc = 0.9 if client == "Meridian" else 1.0  # 10% contract discount
                        rows.append((group, d, dish, PAY, client, qty, round(qty * price * disc)))
        d += timedelta(days=1)
    # one row with no counterparty, to exercise the fallback label
    rows.append(("China Town", end, "(Jasmine Tea) Հասմիկի թեյ", PAY, None, 2, 1800))
    return rows


def write_pivot(path: str, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "OLAP"
    ws.append(["OLAP Отчет по продажам"])
    ws.append([f"Период: {rows[0][1]:%d.%m.%Y} - {rows[-1][1]:%d.%m.%Y}"])
    ws.append(["Формат отчета: Bank Transfers"])
    ws.append([])
    ws.append(["Группа", "Учетный день", "Блюдо", "Тип оплаты", "Контрагент",
               "Количество блюд", "Сумма со скидкой, դր"])

    tree = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    for g, d, dish, pay, cl, q, a in rows:
        tree[g][d][dish][pay].append((cl, q, a))

    gt_q = gt_a = 0
    for g in sorted(tree):
        gq = ga = 0
        first_g = True
        for d in sorted(tree[g]):
            dq = da = 0
            first_d = True
            for dish in sorted(tree[g][d]):
                iq = ia = 0
                first_i = True
                for pay in tree[g][d][dish]:
                    pq = pa = 0
                    first_p = True
                    agg = defaultdict(lambda: [0, 0])
                    for cl, q, a in tree[g][d][dish][pay]:
                        agg[cl][0] += q
                        agg[cl][1] += a
                    for cl, (q, a) in agg.items():
                        ws.append([
                            g if first_g else None,
                            d if first_d else None,  # real Excel date cell
                            dish if first_i else None,
                            pay if first_p else None,
                            cl, q, a,
                        ])
                        first_g = first_d = first_i = first_p = False
                        pq += q; pa += a
                    ws.append([None, None, None, f"{pay} всего", None, pq, pa])
                    iq += pq; ia += pa
                ws.append([None, None, f"{dish} всего", None, None, iq, ia])
                dq += iq; da += ia
            ws.append([None, f"{d:%d.%m.%Y} всего", None, None, None, dq, da])
            gq += dq; ga += da
        ws.append([f"{g} всего", None, None, None, None, gq, ga])
        gt_q += gq; gt_a += ga
    ws.append(["Итого", None, None, None, None, gt_q, gt_a])
    for row in ws.iter_rows(min_row=6, min_col=2, max_col=2):
        for c in row:
            if isinstance(c.value, date):
                c.number_format = "yyyy-mm-dd"
    wb.save(path)
    return gt_q, gt_a


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "data/Bank-Transfers.xlsx"
    rows = build_rows(date(2026, 8, 1), date(2026, 10, 8))
    q, a = write_pivot(out, rows)
    print(f"wrote {out}: {len(rows)} leaf rows, qty={q}, amount={a}")
