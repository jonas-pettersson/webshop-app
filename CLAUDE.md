# WebShop Report - Streamlit Web Application

This is a web application for generating reports from Svenska Kyrkan i Wien webshop orders. It provides a user-friendly interface for uploading WordPress/WooCommerce exports and generating Excel reports.

## Project Overview

**Purpose:** Generate packing lists, pickup schedules, validation reports and an inventory report for seasonal market orders

**Status:** Production, deployed to Streamlit Cloud

**Repository:** https://github.com/jonas-pettersson/webshop-app (**public** - never commit passwords or real customer data)

**Technology:** Python 3.10+, Streamlit, pandas, openpyxl

The app has two independent workflows (tabs):

1. **Order Reports** - packing lists, pickup lists, semla list, master list, diffs (per market type)
2. **Inventory Report (Lagerrapport)** - sales and stock per product, grouped by sales area

## Architecture

### Code Structure

```
webshop-app/
├── app.py                        # Streamlit UI: auth, uploads, session state, downloads
├── src/
│   ├── config.py                 # File names, article numbers, tax rates
│   ├── markets.py                # Market types -> which templates they use
│   ├── data_loader.py            # CSV/Excel import + normalization
│   ├── data_validator.py         # Validation checks, diffs.xlsx, inventory validation
│   ├── data_processor.py         # Merging orders/timeslots/products/packing
│   ├── report_generator.py       # Template-based Excel reports (return xlsx bytes)
│   ├── lagerrapport_processor.py # Inventory data: join, sales-area mapping, totals
│   ├── excel_utils.py            # Named ranges, row insertion, safe cell writing
│   └── pipeline.py               # End-to-end pipelines used by app.py (UI-independent)
├── templates/                    # 13 Excel templates (see Template System)
├── tests/                        # pytest suite incl. golden masters (see Testing)
├── scripts/obfuscate_test_data.py  # Creates anonymized test fixtures from real exports
├── .github/workflows/tests.yml   # CI: pytest on every push / PR
├── .streamlit/
│   ├── config.toml               # Streamlit settings
│   └── secrets.toml              # Password (not in git; see secrets.toml.example)
├── requirements.txt              # Pinned runtime dependencies (used by Streamlit Cloud)
└── requirements-dev.txt          # + pytest
```

### Module Responsibilities

- **app.py** - UI only: login, widgets, per-session state, progress, downloads. Calls `src/pipeline.py`.
- **pipeline.py** - `load_order_inputs` → `validate_order_inputs` → `build_order_reports`; `prepare_inventory` → `build_lagerrapport`; `zip_reports`. Everything returns `{filename: xlsx bytes}`.
- **data_loader.py** - Load products, orders, timeslots, packing categories, schedules, product export, products report, SKU mapping
- **data_validator.py** - `validate_data()` (order checks, `CHECKS` list), `generate_diffs_report()`, `remove_duplicate_bookings()`, `validate_inventory_data()`
- **data_processor.py** - `prepare_merge_inputs()` (dedupe/NaN-free join keys, shared with validation), `merge_all_data()`, `sort_for_reports()`
- **report_generator.py** - packlista, hämtningslista, semlelista, masterlista, lagerrapport
- **lagerrapport_processor.py** - Inner join of product export with sales report, SKU-prefix → sales area, totals
- **excel_utils.py** - Named-range lookup, `insert_row_and_copy_format()`, `set_cell_value()`, `dataframe_to_xlsx_bytes()`
- **markets.py** - `MarketProfile` per market (`JULMARKNAD`, `JULMATEN`, `PASK`, `MARKETS`); resolves the market's template paths
- **config.py** - Output/template file names, `ARTICLE_NUMBER_SEMLA`, `TAX_RATES`

## Design Rules

- **Validation warns, never blocks.** Every data problem is shown in the UI and in
  diffs.xlsx, and reports are still generated. Affected orders stay in the reports
  (bookings outside the schedule are listed as "HH:MM (ej i schema)", bookings without
  time under "Ingen tid", without date on sheet "Hämtas utan datum") instead of disappearing.
- **No shared files.** Reports are built in memory per browser session
  (`st.session_state`); Streamlit Cloud serves all users from one process. Results are
  cleared when the market type or an uploaded file changes.
- **User text is never a formula.** Write cells via `excel_utils.set_cell_value()` /
  `dataframe_to_xlsx_bytes()`, which keep strings starting with `=` as plain text.
- **Output changes are deliberate.** Golden-master tests pin every report cell; update
  snapshots only for intended changes and review the diff.

## Running Locally

```bash
pip install -r requirements.txt

# Create .streamlit/secrets.toml from the example and set a password
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

streamlit run app.py
```

The app will open at http://localhost:8501

## Workflow 1: Order Reports

### User Steps

1. **Login** - Enter password
2. **Select Market Type** - julmarknad / julmaten / pask (chooses the templates, see below)
3. **Upload Files** - 3 WordPress exports (below)
4. **Run Validation** - Metrics per check, expandable details, headline warning for
   order lines that will be missing from the lists, download diffs.xlsx
5. **Generate Reports** - Always possible, also with validation warnings
6. **Download** - Individual files or ZIP (diffs + all reports + allData)

### Input Files

**Uploads (from WordPress):**

1. **wc-product-export.csv** - Product catalog
   - Export from WordPress Products → Export
   - Columns used: SKU, Short description, Regular price

2. **orders.xlsx** - Customer orders
   - Export from WooCommerce → Export Order
   - 14 columns used, including order details, items, billing info, `pa_packn_kategori`

3. **tidsbokning.csv** - Pickup time bookings
   - Export from WP Time Slots Booking Form → Export to CSV
   - Encoding: latin_1

**Automatic (from templates/, per market type):**

4. **placeringsnycklar_{market_type}.xlsx** - Packing categories → pickup area; row order = packing order. Blank rows are separators and ignored.
5. **schedule_{market_type}.xlsx** - Pickup slots (`Dag`, `Tid`). Update every season.

### Market Type

All WordPress exports have the same format (there are two WordPress instances:
one for julmaten, one shared by julmarknad and påskmarknad). The market type only
selects templates, which differ per market (`src/markets.py`):

| Template | Differs by |
|---|---|
| `placeringsnycklar_*` | categories (`julpynt` jul only, `semla` påsk only), pickup-area labels, order |
| `packlista_template_*` | footer labels |
| `schedule_*` | pickup dates/times |

The semlelista is generated whenever semla (`#H_09#`) was ordered, i.e. in practice at påsk.

### Generated Reports

1. **diffs.xlsx** - Data validation (10 sheets, all warnings):
   - Orders without timeslots (incl. orders without email)
   - Timeslots without orders
   - Incomplete timeslots (missing email, date or time)
   - Duplicate bookings (the first row of the export is used)
   - Missing products
   - Missing packing categories
   - Bookings outside the pickup schedule
   - Duplicate products (SKU) / duplicate packing categories (first occurrence is used)
   - "Saknas i packlistor": every order line excluded from the reports, with reason

2. **packlista.xlsx** - One sheet per order (`PO_<nr>`), lines grouped by pickup area

3. **hämtningslista.xlsx** - One sheet per pickup date, every scheduled slot (empty or filled), plus flagged off-schedule / no-time slots

4. **semlelista.xlsx** - Semla orders (`#H_09#`) grouped by date and hour (only if semla was ordered)

5. **masterlista.xlsx** - One row per order

6. **allData.xlsx** - Debug dump of merged data

### Data Processing Pipeline

1. **Load** - Import CSV/Excel files, lowercase emails, create packing keys
2. **Validate** - All checks incl. schedule; diffs.xlsx
3. **Clean** - Remove duplicate bookings (after reporting)
4. **Merge** - Inner joins: Orders → Timeslots (Email) → Products (SKU) → Packing (category key).
   Lines without a match are excluded and listed in "Saknas i packlistor".
5. **Sort** - By PickUpDate, PickUpTime, PackingCategoryIndex (missing values last)
6. **Generate** - Excel reports from templates

## Workflow 2: Inventory Report (Lagerrapport)

### User Steps

1. Open the **📊 Inventory Report** tab (no market type needed)
2. Upload **wc-product-export.csv** and **wc-products-report-export.csv**
3. **Load and Validate Data** - shows warnings
4. **Generate Lagerrapport** and download

### Input Files

1. **wc-product-export.csv** - Full product catalog. Columns used: SKU, Name, Regular price, Stock, Tax status, Tax class
2. **wc-products-report-export.csv** - WooCommerce products sales report. Columns used: Product title, SKU, Items sold, N. Revenue, Category, Stock
3. **templates/sku_sales_area_mapping.xlsx** (automatic) - sheet `Mapping`, columns `SKU_Prefix`, `Sales_Area` (e.g. `#BK_` → Böcker)

Numbers accept both `12.50` and `12,50`.

### Processing (`lagerrapport_processor.prepare_lagerrapport_data`)

1. **Inner join** sales report + product export on SKU (only products with sales activity)
2. **Sales area** (`Category (SKUT)`) from SKU prefix; first matching prefix in the mapping wins, no match → `Unknown`
3. **Totals** - `Total sales = Regular price × Items sold`; `Total tax = Regular price × tax rate` (see Known Issues)
4. **Stock** from the product export
5. **Sort** by sales area, then SKU

Tax rates (`config.TAX_RATES`, Austrian VAT): `reduzierter-preis` 10%, `zero-rate` 0%, everything else 20%.

### Validation (`validate_inventory_data`, warnings only)

- SKUs in the sales report but not in the product export
- Products with unknown sales area (add the prefix to the mapping)
- Missing prices / missing stock

### Output

**lagerrapport.xlsx** - one sheet `Content`, one row per product with columns:
SKU, Product title, Category (SKUT), Category, Regular price, Items sold, Stock,
Tax class, Total sales, Total tax.

## Template System

Reports use Excel template manipulation:

- **Named Ranges** - Templates define ranges like `ArticleNumber`, `FullName`, `PickUpTime`; code fills cells by name, so layout changes need no code changes
- **Dynamic Row Insertion** - `insert_row_and_copy_format()` duplicates template rows with formatting (columns A–J only)
- **Format Preservation** - Cell styles, merged cells, row heights
- Each template workbook has a sheet named `template`, which is copied and then removed

Templates in `templates/` (13 files):
- `packlista_template_{market_type}.xlsx` (3)
- `placeringsnycklar_{market_type}.xlsx` (3)
- `schedule_{market_type}.xlsx` (3)
- `hämtlista_template.xlsx` - pickup lists
- `semlelista_template.xlsx` - semla list
- `lagerrapport_template.xlsx` - inventory report (named ranges `SKU` … `TotalTax`)
- `sku_sales_area_mapping.xlsx` - SKU prefix → sales area

## Authentication

Simple password protection using `st.secrets`:

```toml
# .streamlit/secrets.toml (not in git)
password = "your-secure-password"
```

For deployment, set the password in Streamlit Cloud secrets. Never write the real
password in any tracked file - the repository is public.

## Deployment

**Platform:** Streamlit Cloud (free tier), Python 3.10+ (Streamlit 1.64 requirement)

**Auto-deployment:** Every push to `main` redeploys with `requirements.txt`

See `DEPLOYMENT.md` for setup and secrets.

## Known Issues

1. **Lagerrapport tax and mapping rules unconfirmed** - `Total tax` is `price × rate`
   (not multiplied by items sold; not `gross × r/(1+r)` if prices include VAT), tax class
   `parent` is treated as 20%, and SKU prefixes use first match instead of longest match.
   Open question for the owners; fix together with tests once confirmed.

(Missing pickup dates/times used to drop orders or crash the semlelista; since Nov 2026
they are reported as incomplete timeslots and the orders still appear in the reports -
see `tests/test_edge_cases.py`.)

## Testing

### Automated Tests

```bash
pip install -r requirements-dev.txt
ruff check .   # lint (config: ruff.toml)
pytest
```

Both run in CI on every push (`.github/workflows/tests.yml`). Test data in
`tests/fixtures/pask/` is obfuscated (`scripts/obfuscate_test_data.py`).

- `test_golden_master.py` pins every report's cell content. After an intended output
  change: `UPDATE_GOLDEN=1 pytest tests/test_golden_master.py`, then review
  `git diff tests/golden/`.
- `test_edge_cases.py` - missing dates/times, off-schedule bookings, formula injection
- `test_loader_robustness.py` - reordered/missing columns, encodings, odd values in exports
- `test_app_smoke.py` - Streamlit `AppTest`: login, both tabs end to end, wrong-file errors

See `tests/README.md`.

### Manual Testing

Before each market, run the app with that market's real exports and compare against the
previous run. History: the app was validated against the original Jupyter notebook with
production data (November 2024 Christmas market, March 2025 Easter market).

## Maintenance

### Updating Templates

1. Modify Excel files in `templates/` (keep named ranges and the `template` sheet)
2. Run `pytest` - layout template changes show up as golden-master diffs
3. Commit and push; Streamlit Cloud auto-redeploys

New season: update `schedule_{market_type}.xlsx` (the app warns if most bookings don't
match the selected market's schedule).

### Adding New Market Type

1. Add a `MarketProfile(...)` line to `src/markets.py` and include it in `MARKETS`
2. Add templates to `templates/` (`test_every_market_has_its_templates` checks they exist):
   - `packlista_template_{new_type}.xlsx`
   - `placeringsnycklar_{new_type}.xlsx`
   - `schedule_{new_type}.xlsx`

### Password Changes

**Local:** Edit `.streamlit/secrets.toml`

**Production:** Streamlit Cloud app settings → Secrets

### Dependency Updates

`requirements.txt` pins minor versions (`streamlit==1.64.*`, `pandas==2.3.*`,
`openpyxl==3.1.*`). Bump deliberately, run `pytest`, then push.

## Migration from Notebook

Extracted from a Jupyter notebook (1,670 lines, single file) in September 2026. Report
output matches the notebook, except for the deliberate fixes listed in the git history
(Nov 2026: no silent order loss, extra diffs sheets). The notebook is kept separately as
a reference.

## Future Enhancements

Potential improvements (not yet implemented):

1. **WordPress Integration** - Fetch data directly via WooCommerce REST API
2. **Multi-user Support** - User accounts with `streamlit-authenticator`
3. **Historical Reports** - Store and view past generated reports
4. **Email Notifications** - Send reports to stakeholders automatically
5. **Data Entry Interface** - Edit/correct data before report generation

## Contact

For issues or questions about this application, refer to the GitHub repository.
