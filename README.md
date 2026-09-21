# WebShop Report Web Application

Web application for generating reports from Svenska Kyrkan i Wien webshop orders.

## Status

🚧 **In Development** - Building Streamlit UI

### Completed
- ✅ Project structure created
- ✅ Excel templates copied (12 files)
- ✅ Excel utilities extracted (`src/excel_utils.py`)
- ✅ Configuration module created (`src/config.py`)
- ✅ Data loader module extracted (`src/data_loader.py`)
- ✅ Data validation module extracted (`src/data_validator.py`)
- ✅ Data processor module extracted (`src/data_processor.py`)
- ✅ Report generator module extracted (`src/report_generator.py`)

### In Progress
- ⏳ Streamlit UI (`app.py`)
- ⏳ Authentication
- ⏳ Testing

## Project Structure

```
webshop-app/
├── src/
│   ├── __init__.py
│   ├── config.py          # Market types and file naming
│   ├── excel_utils.py     # Excel template manipulation
│   └── data_loader.py     # Data loading from uploads
├── tests/
│   └── __init__.py
├── .streamlit/
│   └── config.toml        # Streamlit configuration
├── uploads/               # Temporary uploaded files
├── outputs/               # Generated reports
├── templates/             # Excel templates (symlink to ../WebShopReport/templates/)
├── requirements.txt       # Python dependencies
└── README.md
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

Default password: `svenskakyrkan2024` (change in `.streamlit/secrets.toml`)

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

## Testing

Test with historical data from the notebook project:

```bash
# Files are in:
../WebShopReport/input/2024_11_20/
```

Upload `orders.xlsx`, `wc-product-export.csv`, and `tidsbokning.csv` through the web interface.

Compare generated reports to notebook outputs for validation.

## Next Steps

1. ✅ Test locally with historical data
2. ⏳ Compare outputs to notebook-generated reports
3. ⏳ Fix any discrepancies
4. ⏳ Commit to git and push to GitHub
5. ⏳ Deploy to Streamlit Cloud
6. ⏳ Add custom domain via DNSimple
