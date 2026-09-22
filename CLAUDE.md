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
│   ├── data_processor.py      # Data merging (40 lines)
│   └── report_generator.py    # Excel report generation (379 lines)
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

1. **diffs.xlsx** - Data validation (5 sheets):
   - Orders without timeslots
   - Timeslots without orders
   - Duplicate bookings
   - Missing products
   - Missing packing categories

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

1. **Date sorting with missing data** - Both this app and the original notebook have an issue where validation sorting fails if dates are missing/NaN. Decision: Wait for real julmarknad data to determine if this is a data entry error (should be reported) or expected edge case (should be handled).

## Testing

### With Historical Data

Test files are in `../WebShopReport/input/`:
- `2024_11_20/` - julmarknad data
- `2025_03_25/` - pask data

Upload through web interface and compare generated reports to notebook outputs.

### Validation

The app behavior should match the original Jupyter notebook exactly. Use historical data to verify:
- Same validation errors detected
- Same reports generated
- Same Excel formatting

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

This application was extracted from the Jupyter notebook in September 2026:

- Original: `../WebShopReport/Report.ipynb` (1,670 lines, single file)
- Extracted to: 6 modules (~1,540 lines) + Streamlit UI (520 lines)
- Behavior: Identical to notebook
- Maintenance: Easier (modular, version controlled)
- Deployment: Web-accessible (vs. local Jupyter)

The notebook remains as a reference and backup system.

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

For issues or questions about this application, refer to the GitHub repository or the original notebook documentation in `../WebShopReport/CLAUDE.md`.
