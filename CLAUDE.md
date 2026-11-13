# WebShop Report - Streamlit Web Application

This is a web application for generating reports from Svenska Kyrkan i Wien webshop orders. It provides a user-friendly interface for uploading WordPress/WooCommerce exports and generating Excel reports.

## Project Overview

**Purpose:** Generate packing lists, pickup schedules, and validation reports for seasonal market orders

**Status:** Production, deployed to Streamlit Cloud

**Repository:** https://github.com/jonas-pettersson/webshop-app

**Technology:** Python, Streamlit, pandas, openpyxl

## Architecture

### Code Structure

```
webshop-app/
├── app.py                      # Main Streamlit UI (520 lines)
├── src/
│   ├── config.py              # Market types, file naming (67 lines)
│   ├── excel_utils.py         # Excel template manipulation (142 lines)
│   ├── data_loader.py         # CSV/Excel import (178 lines)
│   ├── data_validator.py      # Data validation (213 lines)
│   ├── data_processor.py      # Data merging
│   ├── report_generator.py    # Excel report generation (returns xlsx bytes)
│   ├── lagerrapport_processor.py  # Inventory report data
│   └── pipeline.py            # End-to-end pipelines used by app.py (UI-independent)
├── templates/                  # 12 Excel templates (market-specific)
├── .streamlit/
│   ├── config.toml            # Streamlit settings
│   └── secrets.toml           # Password (not in git)
├── requirements.txt            # Python dependencies
└── README.md
```

**Total:** ~1,540 lines of business logic + 520 lines UI

### Module Responsibilities

- **config.py** - Market type constants, file naming conventions
- **excel_utils.py** - Named range manipulation, row insertion with formatting
- **data_loader.py** - Load products, orders, timeslots, packing categories, schedules
- **data_validator.py** - Validate data relationships, generate diffs.xlsx
- **data_processor.py** - Merge all datasets into unified DataFrame
- **report_generator.py** - Generate all 4 report types using templates
- **app.py** - Streamlit UI, authentication, file upload, progress tracking

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set password in .streamlit/secrets.toml
# (Default: svenskakyrkan2024)

# Run application
streamlit run app.py
```

The app will open at http://localhost:8501

## User Workflow

1. **Login** - Enter password
2. **Select Market Type** - Choose julmarknad/julmaten/pask
3. **Upload Files** - Upload 3 WordPress exports:
   - wc-product-export.csv (products)
   - orders.xlsx (orders)
   - tidsbokning.csv (timeslots)
4. **Run Validation** - Check data integrity
5. **Review Issues** - Expandable details for each validation type
6. **Generate Reports** - Create all Excel reports
7. **Download** - Individual files or ZIP of all reports

## Input Files

### Required Uploads (from WordPress)

1. **wc-product-export.csv** - Product catalog
   - Export from WordPress Products → Export
   - Columns: SKU, Short description, Regular price

2. **orders.xlsx** - Customer orders
   - Export from WooCommerce → Export Order
   - 14 columns including order details, items, billing info

3. **tidsbokning.csv** - Pickup time bookings
   - Export from WP Time Slots Booking Form → Export to CSV
   - Encoding: latin_1

### Automatic (from templates/)

4. **placeringsnycklar_{market_type}.xlsx** - Packing categories
5. **schedule_{market_type}.xlsx** - Authorized pickup times

## Generated Reports

1. **diffs.xlsx** - Data validation (10 sheets, all warnings - generation is never blocked):
   - Orders without timeslots (incl. orders without email)
   - Timeslots without orders
   - Incomplete timeslots (missing email, date or time)
   - Duplicate bookings
   - Missing products
   - Missing packing categories
   - Bookings outside the pickup schedule
   - Duplicate products (SKU) / duplicate packing categories
   - "Saknas i packlistor": every order line excluded from the reports, with reason

2. **packlista.xlsx** - Packing lists:
   - One sheet per order
   - Grouped by pickup area
   - Formatted using templates with named ranges

3. **hämtningslista.xlsx** - Pickup schedules:
   - One sheet per pickup date
   - Organized by time slots
   - Shows all scheduled times (empty or filled)

4. **semlelista.xlsx** - Semla list (pask only):
   - Special product filtering
   - Grouped by date and hour

5. **masterlista.xlsx** - Master order list:
   - Simple consolidated view
   - One row per order

6. **allData.xlsx** - Debug dump of merged data

## Template System

Reports use sophisticated Excel template manipulation:

- **Named Ranges** - Templates define ranges like `ArticleNumber`, `FullName`, `PickUpTime`
- **Dynamic Row Insertion** - `insertRowAndCopyFormat()` duplicates rows with formatting
- **Format Preservation** - Maintains cell styles, merged cells, row heights
- **Market-Specific** - Different templates per market type

Templates in `templates/`:
- hämtlista_template.xlsx (pickup lists)
- semlelista_template.xlsx (semla list)
- packlista_template_{market_type}.xlsx (3 files)
- placeringsnycklar_{market_type}.xlsx (3 files)
- schedule_{market_type}.xlsx (3 files)

## Data Processing Pipeline

1. **Load** - Import CSV/Excel files
2. **Normalize** - Lowercase emails, create keys
3. **Validate** - Check relationships, generate diffs
4. **Clean** - Remove duplicate bookings (after reporting)
5. **Merge** - Sequential joins: Orders → Timeslots → Products → Packing
6. **Sort** - By PickUpDate, PickUpTime, PackingCategoryIndex
7. **Generate** - Create Excel reports using templates

## Authentication

Simple password protection using `st.secrets`:

```python
# .streamlit/secrets.toml (not in git)
password = "your-secure-password"
```

For deployment, set password in Streamlit Cloud secrets.

## Deployment

**Platform:** Streamlit Cloud (free tier)

**Repository:** https://github.com/jonas-pettersson/webshop-app

**Setup:**
1. Push code to GitHub (private repo)
2. Go to https://share.streamlit.io
3. Select repository
4. Set main file: `app.py`
5. Add password in Secrets
6. Deploy

**Auto-deployment:** Pushes to main branch trigger redeployment

See `DEPLOYMENT.md` for detailed instructions.

## Known Issues

None currently. (Missing pickup dates/times used to drop orders or crash the semlelista;
since Nov 2026 they are reported as incomplete timeslots and the orders still appear in
the reports - see `tests/test_edge_cases.py`.)

## Design Rules

- **Validation warns, never blocks.** Every data problem is shown in the UI and in
  diffs.xlsx, and reports are still generated. Affected orders stay in the reports
  (bookings outside the schedule are listed as "HH:MM (ej i schema)", bookings without
  time under "Ingen tid") instead of disappearing.
- **No shared files.** Reports are built in memory per browser session
  (`st.session_state`); Streamlit Cloud serves all users from one process.
- **User text is never a formula.** Write cells via `excel_utils.set_cell_value()` /
  `dataframe_to_xlsx_bytes()`, which keep strings starting with `=` as plain text.

## Testing

### Automated Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Runs in CI on every push (`.github/workflows/tests.yml`). `tests/test_golden_master.py`
pins every report's cell content; after an intended output change, run
`UPDATE_GOLDEN=1 pytest tests/test_golden_master.py` and review `git diff tests/golden/`.
See `tests/README.md`.

### Manual Testing

Test the application by uploading real WordPress/WooCommerce exports through the web interface:
1. Select market type (julmarknad/julmaten/pask)
2. Upload the three required CSV/Excel files
3. Run validation and review any errors
4. Generate and download reports

### Validation

During development, the app was validated against the original Jupyter notebook using historical production data (November 2024 Christmas market, March 2025 Easter market) to ensure identical behavior:
- Same validation errors detected
- Same reports generated
- Same Excel formatting

The app is now production-ready and standalone.

## Maintenance

### Updating Templates

1. Modify Excel files in `templates/`
2. Commit changes to git
3. Push to GitHub
4. Streamlit Cloud auto-redeploys

### Adding New Market Type

1. Add constant to `src/config.py`
2. Add templates to `templates/` directory:
   - `packlista_template_{new_type}.xlsx`
   - `placeringsnycklar_{new_type}.xlsx`
   - `schedule_{new_type}.xlsx`
3. No code changes needed (data-driven)

### Password Changes

**Local:** Edit `.streamlit/secrets.toml`

**Production:** Update in Streamlit Cloud app settings → Secrets

## Migration from Notebook

This application was extracted from a Jupyter notebook in September 2026:

- Original: Jupyter notebook (1,670 lines, single file)
- Extracted to: 6 modules (~1,540 lines) + Streamlit UI (520 lines)
- Behavior: Identical to notebook
- Maintenance: Easier (modular, version controlled)
- Deployment: Web-accessible (vs. local Jupyter)

The original notebook is maintained separately as a reference and backup system.

## Dependencies

Core libraries (see `requirements.txt`):
- `streamlit>=1.32.0` - Web UI framework
- `pandas>=2.0.0` - Data manipulation
- `openpyxl>=3.1.0` - Excel file generation
- `numpy>=1.24.0` - Array operations

## Future Enhancements

Potential improvements (not yet implemented):

1. **WordPress Integration** - Fetch data directly via WooCommerce REST API
2. **Multi-user Support** - User accounts with `streamlit-authenticator`
3. **Historical Reports** - Store and view past generated reports
4. **Email Notifications** - Send reports to stakeholders automatically
5. **Data Entry Interface** - Edit/correct data before report generation

## Contact

For issues or questions about this application, refer to the GitHub repository.
