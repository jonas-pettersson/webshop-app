"""Configuration for WebShop Report system.

File names, article numbers and tax rates. Market types: see markets.py.
"""

# Article numbers
ARTICLE_NUMBER_SEMLA = '#H_09#'

# Output file names
OUTPUT_FILENAME_PACKLISTA = 'packlista.xlsx'
OUTPUT_FILENAME_HAMTNINGSLISTA = 'hämtningslista.xlsx'
OUTPUT_FILENAME_SEMLELISTA = 'semlelista.xlsx'
OUTPUT_FILENAME_MASTERLISTA = 'masterlista.xlsx'
OUTPUT_FILENAME_DIFFS = 'diffs.xlsx'
OUTPUT_FILENAME_ALLDATA = 'allData.xlsx'
OUTPUT_FILENAME_LAGERRAPPORT = 'lagerrapport.xlsx'

# Tax rates (Austrian VAT)
TAX_RATES = {
    'reduzierter-preis': 0.10,  # Reduced rate 10%
    'zero-rate': 0.00,          # Zero rate 0%
    'parent': 0.20,             # Standard rate 20%
    None: 0.20,                 # Default to standard
    'nan': 0.20                 # Handle pandas NaN
}

# Lagerrapport templates
TEMPLATE_FILENAME_SKU_MAPPING = 'sku_sales_area_mapping.xlsx'
TEMPLATE_FILENAME_LAGERRAPPORT = 'lagerrapport_template.xlsx'

# Template file names
TEMPLATE_FILENAME_HAMTLISTA = 'hämtlista_template.xlsx'
TEMPLATE_FILENAME_SEMLELISTA = 'semlelista_template.xlsx'
