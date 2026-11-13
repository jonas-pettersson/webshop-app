"""End-to-end report pipelines, independent of the Streamlit UI.

Everything is built in memory and returned as {filename: xlsx bytes}, so
concurrent users of the web app never share or see each other's files.
"""

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional

import pandas as pd

from . import config
from .data_loader import (
    load_orders,
    load_packing_categories,
    load_product_export,
    load_products,
    load_products_report_export,
    load_schedule,
    load_sku_mapping,
    load_timeslots,
)
from .data_processor import merge_all_data, sort_for_reports
from .data_validator import (
    ValidationResult,
    generate_diffs_report,
    remove_duplicate_bookings,
    validate_data,
    validate_inventory_data,
)
from .excel_utils import dataframe_to_xlsx_bytes
from .lagerrapport_processor import prepare_lagerrapport_data
from .report_generator import (
    generate_hamtningslista,
    generate_lagerrapport,
    generate_masterlista,
    generate_packlista,
    generate_semlelista,
)

Reports = Dict[str, bytes]
ProgressCallback = Callable[[int, str], None]


@dataclass
class OrderInputs:
    """All datasets needed for the order reports of one market."""
    market_type: str
    products: pd.DataFrame
    orders: pd.DataFrame
    timeslots: pd.DataFrame
    packing: pd.DataFrame
    schedule: pd.DataFrame


def load_order_inputs(products_file, orders_file, timeslots_file,
                      market_type: str, template_dir: Path) -> OrderInputs:
    """Load the three uploads plus the market's packing/schedule templates."""
    return OrderInputs(
        market_type=market_type,
        products=load_products(products_file),
        orders=load_orders(orders_file),
        timeslots=load_timeslots(timeslots_file, market_type),
        packing=load_packing_categories(market_type, template_dir),
        schedule=load_schedule(market_type, template_dir),
    )


def validate_order_inputs(inputs: OrderInputs) -> ValidationResult:
    return validate_data(inputs.orders, inputs.timeslots, inputs.products,
                         inputs.packing, inputs.schedule)


def build_diffs_report(result: ValidationResult) -> Reports:
    return {config.OUTPUT_FILENAME_DIFFS: generate_diffs_report(result)}


def build_order_reports(inputs: OrderInputs, template_dir: Path,
                        progress: Optional[ProgressCallback] = None) -> Reports:
    """Merge the data and generate all order reports.

    Args:
        inputs: Loaded datasets (see load_order_inputs)
        template_dir: Path to templates directory
        progress: Optional callback(percent, message) for UI progress

    Returns:
        {output filename: xlsx bytes}, in display order
    """
    def step(percent, message):
        if progress:
            progress(percent, message)

    step(0, "Removing duplicate bookings...")
    timeslots = remove_duplicate_bookings(inputs.timeslots)

    step(10, "Merging datasets...")
    all_data = sort_for_reports(
        merge_all_data(inputs.orders, timeslots, inputs.products, inputs.packing)
    )

    reports: Reports = {}

    step(25, "Generating packing lists...")
    reports[config.OUTPUT_FILENAME_PACKLISTA] = generate_packlista(
        all_data, template_dir, inputs.market_type)

    step(50, "Generating pickup lists...")
    reports[config.OUTPUT_FILENAME_HAMTNINGSLISTA] = generate_hamtningslista(
        all_data, inputs.schedule, template_dir)

    if inputs.market_type == config.MARKET_TYPE_PASK:
        step(70, "Generating semla list...")
        reports[config.OUTPUT_FILENAME_SEMLELISTA] = generate_semlelista(all_data, template_dir)

    step(80, "Generating master list...")
    reports[config.OUTPUT_FILENAME_MASTERLISTA] = generate_masterlista(all_data)

    step(90, "Saving merged data...")
    reports[config.OUTPUT_FILENAME_ALLDATA] = dataframe_to_xlsx_bytes({'Sheet1': all_data})

    step(100, "✅ All reports generated successfully!")
    return reports


@dataclass
class InventoryResult:
    inventory: pd.DataFrame
    validation: dict


def prepare_inventory(product_export_file, products_report_file,
                      template_dir: Path) -> InventoryResult:
    product_export = load_product_export(product_export_file)
    products_report = load_products_report_export(products_report_file)
    inventory = prepare_lagerrapport_data(product_export, products_report,
                                          load_sku_mapping(template_dir))
    validation = validate_inventory_data(product_export, products_report, inventory)
    return InventoryResult(inventory=inventory, validation=validation)


def build_lagerrapport(inventory: pd.DataFrame, template_dir: Path) -> Reports:
    return {config.OUTPUT_FILENAME_LAGERRAPPORT: generate_lagerrapport(inventory, template_dir)}


def zip_reports(reports: Reports) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, data in reports.items():
            zf.writestr(name, data)
    return buffer.getvalue()
