# Quick Start Guide

## Running Locally

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your password:**
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   - Edit `.streamlit/secrets.toml` and set `password = "..."`
   - Never commit this file (the repository is public)

3. **Run the application:**
   ```bash
   streamlit run app.py
   ```

4. **Open in browser:**
   - The app will automatically open at http://localhost:8501
   - Enter the password to access the application

## Using the Application

The app has two tabs: **📦 Order Reports** (steps below) and **📊 Inventory Report**.

### Step 1: Select Market Type
Choose from:
- `julmarknad` - Christmas market
- `julmaten` - Christmas food
- `pask` - Easter market

### Step 2: Upload Files
Upload three files exported from WordPress:
1. **Products (CSV)** - `wc-product-export.csv`
2. **Orders (Excel)** - `orders.xlsx`
3. **Time Slots (CSV)** - `tidsbokning.csv`

### Step 3: Run Validation
Click "Run Validation" to:
- Check for orders without time bookings, and time bookings without orders
- Find incomplete and duplicate bookings
- Find bookings outside the pickup schedule
- Verify products exist in catalog (and have unique SKUs)
- Verify packing categories are defined

All findings are warnings. A headline shows how many order lines will be missing
from the packing lists; details are in `diffs.xlsx`. You can always continue.

### Step 4: Generate Reports
Click "Generate All Reports" to create:
- **Packlista** - Packing lists (one sheet per order)
- **Hämtningslista** - Pickup schedules (one sheet per date)
- **Semlelista** - Semla list (only for pask market)
- **Masterlista** - Master list of all orders

### Step 5: Download
Download individual reports or all reports as a ZIP file.

## Inventory Report (Lagerrapport)

1. Open the **📊 Inventory Report** tab
2. Upload `wc-product-export.csv` (product catalog) and `wc-products-report-export.csv` (sales report).
   The sales report may be exported in English or German - both work.
3. Click "Load and Validate Data" and review the warnings (e.g. SKUs with unknown sales area)
4. Click "Generate Lagerrapport" and download `lagerrapport.xlsx`

Sales areas come from SKU prefixes in `templates/sku_sales_area_mapping.xlsx`.

## Testing with Real Data

Test the application using exports from your WordPress/WooCommerce site:

1. Export products from WordPress Products → Export → `wc-product-export.csv`
2. Export orders from WooCommerce → Export Order → `orders.xlsx`
3. Export time slots from WP Time Slots Booking Form → Export to CSV → `tidsbokning.csv`

Upload these files through the web interface and generate reports.

The application was validated during development using historical production data to ensure correctness.

## Troubleshooting

### "No module named 'streamlit'"
Install dependencies: `pip install -r requirements.txt`

### "The bookings don't match the ... schedule"
Check the selected market type, and that `templates/schedule_{market_type}.xlsx` has this season's dates

### Password not working
Check `.streamlit/secrets.toml` exists and has the correct password

### Validation errors appearing
Review the validation report to check for data issues (missing products, duplicate bookings, etc.)
