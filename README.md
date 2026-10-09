Bank Transfers · Invoicing desk (ChinaTown & Nani)
A standalone Streamlit app for the accountant. It shows the non-cash bank-transfer
orders (`Փոխանցումով`) from the iiko export `Bank-Transfers.xlsx`, grouped by
counterparty (`Контрагент`). For each counterparty it has the invoice lines ready
to copy into Armenian e-Invoicing.
What's on the page
Sidebar filters
1 · Brand: ChinaTown · Nani · All brands. The brand also changes the colour theme.
2 · Period: Yesterday · Last 7 Days · This Month · Custom Range.
The app opens on ChinaTown and Yesterday.
3 · Invoice grouping:
Whole period gives one card per counterparty.
Per day gives one card per counterparty per day.
A payment-type filter appears only if the file has more than one type.
Data card: source, load time, the date span the file covers, and a check that the parsed total matches iiko's «Итого» row.
Header: logos, quick-period pills and Start/End dates. These stay in sync with the sidebar.
4 KPI cards:
Total transfer sales (֏)
Total items sold
Counterparties count
Average order value: sales ÷ orders. An order is one counterparty on one day for one brand, because the export has no check numbers. If a `Номер чека` column is ever added, AOV switches to real checks automatically.
Search + filtered totals (above the cards):
One search box matches counterparty names, item names (English or Armenian) and amounts, for example `Meri`, `Dolma`, `Կունգ`, `46,000`.
Cards filter on every keystroke, with no Enter needed. Clearing the box (or its ✕) brings every card back.
Item matches are highlighted, and their cards open with a "N matching lines" badge.
Next to the box: Checks / Invoices, Items QTY and Invoice sales (֏) for the cards on screen.
Streamlit commits the text after a 250 ms pause (`live=`), so Export all (Excel) always matches the filtered view.
Counterparty cards:
The expand chevron sits on the far left, then the number and the name in bold.
The right side shows items QTY, invoice amount and the payment badge. Share and transfer days are under the name.
Click a card to open its item table: Item Name (Блюдо) · Quantity · Unit Price (AMD) · Total Amount (AMD). Dish names are regular weight, with English on top and Armenian below.
Each line is one dish at one exact unit price, so QTY × unit price = total on every line. A dish sold at two prices (for example, with a contract discount) gets two lines.
With All brands, a counterparty that bought from both restaurants gets one card per brand, because each brand issues its own invoice.
Copy / Export Invoice Summary (CSV/Excel) under every card:
Copy N item rows puts the rows on the clipboard, tab-separated (name, qty, unit price, total), ready to paste into Excel or the e-Invoicing grid.
CSV is UTF-8 with BOM, so Armenian and Cyrillic open correctly in Excel.
Excel gives a formatted invoice sheet with header info and a total row.
Export all (Excel): exactly the cards on screen (brand, period and search).
The Summary sheet has the filter context, the three totals and one row per invoice.
The Invoice lines sheet has every line (item, QTY, unit price, total) with a total row.
Repository layout
```
app.py                       # page layout
bank_transfers/
  config.py                  # URL, brand rules, palettes, presets
  parser.py                  # iiko OLAP parser (pure pandas, unit-tested)
  data.py                    # Dropbox download + caching (10 min)
  invoices.py                # filters, KPIs, invoice building
  export.py                  # CSV / Excel / clipboard payloads
  dates.py                   # shared date state (d_preset / d_start / d_end)
  theme.py                   # brand tokens, CSS, one-time JS
  ui.py                      # HTML blocks (header, KPI grid, cards)
assets/chinatown.png, nani.png
.streamlit/config.toml, secrets.toml.example
tests/                       # python -m pytest -q
requirements.txt
```
Deploy (GitHub → Streamlit Cloud)
Push this folder to a new GitHub repo, e.g. `bank-transfers-app`.
On share.streamlit.io, choose New app, pick the repo and set main file `app.py`.
Go to App settings → Secrets and paste:
```toml
   BANK_TRANSFERS_URL = "https://www.dropbox.com/scl/fi/0xn9ax9giix53pz0fsa8o/Bank-Transfers.xlsx?rlkey=7c3oz76jdcpeeq8awnaai2wqs&dl=1"
   ```
Links ending in `dl=0` are converted to `dl=1` automatically.
To force a fresh read after the file is overwritten, open the app with `?refresh=1` or press Refresh data. Otherwise the data is re-read every 10 minutes.
Local run: `pip install -r requirements.txt && streamlit run app.py`.
If Dropbox can't be reached, the app falls back to `data/Bank-Transfers.xlsx` when that file exists. The sidebar then says "Local file".
How the iiko export is parsed
The header row is found by `Учетный день`. Columns are matched by keyword:
Группа
Учетный день
Блюдо
Тип оплаты
Контрагент
Количество блюд
Сумма со скидкой
If a header is missing, the parser falls back to positions A–G.
These subtotal rows are removed: `… всего` at every level and `Итого`.
Parent dimensions (group, date, dish, payment type) are forward-filled. The counterparty is not forward-filled; a blank one shows as «Без контрагента».
Group names are mapped to brands: `China Town` → ChinaTown, `Նանի` → Nani.
Dates can be Excel dates, `YYYY-MM-DD` or `DD.MM.YYYY`. Numbers can be in the `1 234,50` style.
Streamlit is pinned to 1.64.0, because the pill CSS targets its react-aria radio markup (`stRadioOption[data-selected]`).
