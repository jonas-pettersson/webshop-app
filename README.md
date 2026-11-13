# WebShop Report Generator

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://svenska-kyrkan-webshop-reports.streamlit.app/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Streamlit web application for generating packing lists, pickup schedules, validation reports and an inventory report from WooCommerce/WordPress webshop orders. Built for Svenska Kyrkan i Wien's seasonal markets (Christmas and Easter).

🔗 **Live Demo:** [svenska-kyrkan-webshop-reports.streamlit.app](https://svenska-kyrkan-webshop-reports.streamlit.app/)

## Features

- 🔐 **Password-protected** web interface
- 📤 **File upload** for WordPress/WooCommerce exports
- ✅ **Data validation** with comprehensive error reporting
- 📊 **Excel report generation** with professional formatting
- 📥 **Bulk download** of all reports as ZIP
- 📦 **Inventory report** (lagerrapport) with sales per product and sales area
- 🛡️ **Nothing silently dropped** - every data issue is reported, reports are still generated
- 🎯 **Market-specific** templates (Christmas, Easter markets)
- 🚀 **Zero-installation** - runs entirely in the browser

## Tech Stack

- **Framework:** [Streamlit](https://streamlit.io/) - Web UI
- **Data Processing:** [Pandas](https://pandas.pydata.org/) - Data manipulation
- **Excel Generation:** [OpenPyXL](https://openpyxl.readthedocs.io/) - Template-based reports
- **Deployment:** [Streamlit Cloud](https://streamlit.io/cloud) - Free hosting

## Architecture

```
webshop-app/
├── app.py                        # Streamlit UI
├── src/
│   ├── pipeline.py               # End-to-end report pipelines (UI-independent)
│   ├── config.py                 # Market types & constants
│   ├── data_loader.py            # CSV/Excel import
│   ├── data_validator.py         # Data validation
│   ├── data_processor.py         # Data merging
│   ├── report_generator.py       # Excel report creation
│   ├── lagerrapport_processor.py # Inventory report data
│   └── excel_utils.py            # Template manipulation
├── templates/                    # 13 Excel templates
├── tests/                        # pytest suite incl. golden-master snapshots
├── .streamlit/
│   ├── config.toml               # Streamlit settings
│   └── secrets.toml              # Password (not in git)
└── requirements.txt              # Pinned Python dependencies
```

## Quick Start

### Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jonas-pettersson/webshop-app.git
   cd webshop-app
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up password:**
   ```bash
   # Copy example secrets file
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   # Edit .streamlit/secrets.toml and set your password
   ```

4. **Run the application:**
   ```bash
   streamlit run app.py
   ```

5. **Open browser:** http://localhost:8501

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

### Try the Live Demo

Visit the deployed application: [svenska-kyrkan-webshop-reports.streamlit.app](https://svenska-kyrkan-webshop-reports.streamlit.app/)

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

The suite runs in GitHub Actions on every push. Golden-master tests compare every
generated report cell by cell against snapshots built from obfuscated test data, so
any unintended output change fails the build. See [tests/README.md](tests/README.md).

The application was originally validated against historical production data to ensure
identical behavior to the original Jupyter notebook implementation.

## Use Cases

This application is ideal for:

- **Church organizations** running seasonal markets
- **Small businesses** managing pickup orders
- **Event organizers** coordinating order fulfillment
- **Non-profits** with WooCommerce-based sales

The template system makes it adaptable to different organizational needs.

## Project Background

This application was extracted from a Jupyter notebook (1,670 lines) into a modular, web-accessible system in September 2026.

**Benefits of web version:**
- ✅ No local installation required
- ✅ Accessible from any device
- ✅ User-friendly interface
- ✅ Password protection
- ✅ Easier maintenance and updates

## Contributing

Contributions are welcome! This project is useful for organizations with similar reporting needs.

**Ideas for contributions:**
- Additional market types or templates
- WordPress/WooCommerce API integration
- Multi-language support
- Email notifications
- Historical report storage

See [CLAUDE.md](CLAUDE.md) for detailed architecture documentation.

## License

MIT License - See LICENSE file for details

## Acknowledgments

Built for Svenska Kyrkan i Wien's seasonal market operations. Demonstrates practical application of Python data processing and web deployment for real-world organizational needs.
