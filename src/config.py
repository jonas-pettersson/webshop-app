"""Configuration for WebShop Report system.

Defines market types, file naming conventions, and template mappings.
"""

from pathlib import Path

# Market types
MARKET_TYPE_JULMARKNAD = 'julmarknad'
MARKET_TYPE_JULMATEN = 'julmaten'
MARKET_TYPE_PASK = 'pask'

MARKET_TYPES = [MARKET_TYPE_JULMARKNAD, MARKET_TYPE_JULMATEN, MARKET_TYPE_PASK]

# Article numbers
ARTICLE_NUMBER_SEMLA = '#H_09#'

# Input file names (expected from WordPress exports)
INPUT_FILENAME_PRODUCTS = 'wc-product-export.csv'
INPUT_FILENAME_ORDERS = 'orders.xlsx'
INPUT_FILENAME_TIMESLOTS = 'tidsbokning.csv'
INPUT_FILENAME_PACKING_CATEGORIES = 'placeringsnycklar.xlsx'
INPUT_FILENAME_SCHEDULE = 'schedule.xlsx'

# Output file names
OUTPUT_FILENAME_PACKLISTA = 'packlista.xlsx'
OUTPUT_FILENAME_HAMTNINGSLISTA = 'hämtningslista.xlsx'
OUTPUT_FILENAME_SEMLELISTA = 'semlelista.xlsx'
OUTPUT_FILENAME_MASTERLISTA = 'masterlista.xlsx'
OUTPUT_FILENAME_DIFFS = 'diffs.xlsx'
OUTPUT_FILENAME_ALLDATA = 'allData.xlsx'
OUTPUT_FILENAME_TIMESLOTS_OUTPUT = 'tidsbokning.xlsx'

# Template file names
TEMPLATE_FILENAME_HAMTLISTA = 'hämtlista_template.xlsx'
TEMPLATE_FILENAME_SEMLELISTA = 'semlelista_template.xlsx'
TEMPLATE_FILENAME_PACKING_CATEGORIES = 'placeringsnycklar_{market_type}.xlsx'
TEMPLATE_FILENAME_SCHEDULE = 'schedule_{market_type}.xlsx'
TEMPLATE_FILENAME_PACKLISTA = 'packlista_template_{market_type}.xlsx'


def get_template_filename(base_template: str, market_type: str) -> str:
    """Get the market-specific template filename.

    Args:
        base_template: Template filename pattern with {market_type} placeholder
        market_type: One of MARKET_TYPES

    Returns:
        str: Resolved template filename

    Example:
        >>> get_template_filename('packlista_template_{market_type}.xlsx', 'julmarknad')
        'packlista_template_julmarknad.xlsx'
    """
    return base_template.format(market_type=market_type)


def get_template_path(template_dir: Path, base_template: str, market_type: str) -> Path:
    """Get the full path to a market-specific template file.

    Args:
        template_dir: Path to templates directory
        base_template: Template filename pattern with {market_type} placeholder
        market_type: One of MARKET_TYPES

    Returns:
        Path: Full path to template file
    """
    filename = get_template_filename(base_template, market_type)
    return template_dir / filename
