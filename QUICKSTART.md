# Quick Start Guide

## Running Locally

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your password:**
   - The password is already set in `.streamlit/secrets.toml` to `svenskakyrkan2024`
   - Change it if needed by editing that file

3. **Run the application:**
   ```bash
   streamlit run app.py
   ```

4. **Open in browser:**
   - The app will automatically open at http://localhost:8501
   - Enter the password to access the application

## Using the Application

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
- Check for orders without time bookings
- Check for time bookings without orders
- Find duplicate bookings
- Verify products exist in catalog
- Verify packing categories are defined

### Step 4: Generate Reports
Click "Generate All Reports" to create:
- **Packlista** - Packing lists (one sheet per order)
- **Hämtningslista** - Pickup schedules (one sheet per date)
- **Semlelista** - Semla list (only for pask market)
- **Masterlista** - Master list of all orders

### Step 5: Download
Download individual reports or all reports as a ZIP file.

## Testing with Historical Data

Use the test data from the notebook project:

```bash
# Files are in:
../WebShopReport/input/2024_11_20/
```

Upload these files:
- `orders.xlsx`
- `wc-product-export.csv`
- `tidsbokning.csv`

Compare the generated reports to the notebook's output to verify correctness.

## Troubleshooting

### "No module named 'streamlit'"
Install dependencies: `pip install -r requirements.txt`

### "FileNotFoundError: templates/"
Make sure you're running from the webshop-app directory

### Password not working
Check `.streamlit/secrets.toml` exists and has the correct password

### Reports don't match notebook output
This is expected initially. Run side-by-side comparison using historical data.
