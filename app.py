"""WebShop Report Generator - Streamlit Web Application

Web interface for generating reports from Svenska Kyrkan i Wien webshop orders.

All results live in st.session_state (per browser session) and are built
in memory - nothing is written to a shared directory on the server.
"""

import hmac
import traceback
from pathlib import Path

import pandas as pd
import streamlit as st

from src import config
from src.data_validator import CHECKS
from src.markets import JULMARKNAD, MARKETS
from src.pipeline import (
    build_diffs_report,
    build_lagerrapport,
    build_order_reports,
    load_order_inputs,
    prepare_inventory,
    validate_order_inputs,
    zip_reports,
)

TEMPLATE_DIR = Path(__file__).parent / 'templates'
XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

# Download labels for generated order reports (in display order)
REPORT_LABELS = {
    config.OUTPUT_FILENAME_PACKLISTA: "📥 Packlista (Packing Lists)",
    config.OUTPUT_FILENAME_HAMTNINGSLISTA: "📥 Hämtningslista (Pickup Lists)",
    config.OUTPUT_FILENAME_SEMLELISTA: "📥 Semlelista (Semla List)",
    config.OUTPUT_FILENAME_MASTERLISTA: "📥 Masterlista (Master List)",
}

# Session state owned by each workflow; cleared when its inputs change
ORDER_STATE_KEYS = ['order_inputs', 'validation_result', 'diffs', 'reports']
INVENTORY_STATE_KEYS = ['inventory_result', 'lagerrapport']


# Page configuration
st.set_page_config(
    page_title="WebShop Report Generator",
    page_icon="📊",
    layout="wide"
)


def check_password():
    """Returns True if the user had the correct password."""
    expected = st.secrets.get("password")
    if not expected:
        st.error("Password is not configured. Set `password` in the app secrets.")
        st.stop()

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Compare bytes: compare_digest rejects non-ASCII str (e.g. 'å')
        entered = st.session_state["password"].encode('utf-8')
        if hmac.compare_digest(entered, str(expected).encode('utf-8')):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # Return True if password is correct
    if st.session_state.get("password_correct", False):
        return True

    # Show password input
    st.text_input(
        "Password",
        type="password",
        on_change=password_entered,
        key="password"
    )

    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")

    return False


def reset_if_inputs_changed(fingerprint_key: str, fingerprint: tuple, state_keys: list):
    """Clear a workflow's results when its inputs (market, uploads) change.

    Prevents generating reports from data validated for another market or
    from previously uploaded files.
    """
    if st.session_state.get(fingerprint_key) != fingerprint:
        for key in state_keys:
            st.session_state.pop(key, None)
        st.session_state[fingerprint_key] = fingerprint


def upload_id(uploaded_file):
    """Identity of an upload; changes when a (new) file is uploaded."""
    if uploaded_file is None:
        return None
    return getattr(uploaded_file, 'file_id', None) or (uploaded_file.name, uploaded_file.size)


def show_error(message: str, error: Exception):
    st.error(f"❌ {message}: {error}")
    with st.expander("Technical details"):
        st.code(traceback.format_exc())


def show_validation_results(validation_result):
    summary = validation_result.get_summary()

    st.subheader("Validation Results")

    # One metric per check
    for col, (attr, label) in zip(st.columns(len(CHECKS)), CHECKS):
        with col:
            st.metric(label, summary[attr] if summary[attr] > 0 else "✓")

    # Headline: what will be missing from the packing/pickup lists
    excluded = validation_result.excluded_order_lines
    if len(excluded) > 0:
        st.warning(
            f"⚠️ **{len(excluded)} order lines from {excluded['OrderNumber'].nunique()} "
            f"orders will not appear in packing and pickup lists.** "
            f"See details below or sheet 'Saknas i packlistor' in diffs.xlsx."
        )
        with st.expander(f"⚠️ View {len(excluded)} Order Lines Missing From Reports"):
            st.dataframe(excluded, width='stretch')

    # Wrong market selected? Most bookings won't match the schedule then.
    outside = summary['bookings_outside_schedule']
    if outside > 0 and outside >= 0.5 * len(st.session_state.order_inputs.timeslots):
        st.warning(
            f"⚠️ {outside} bookings are not in the **{st.session_state.order_inputs.market.label}** "
            f"pickup schedule. Did you select the right market type?"
        )

    # Details per check
    for attr, label in CHECKS:
        count = summary[attr]
        if count == 0:
            continue
        with st.expander(f"⚠️ View {count} {label}"):
            df = getattr(validation_result, attr)
            if attr == 'incomplete_timeslots':
                parts = [f"{df[col].isna().sum()} with missing {name}"
                         for col, name in [('Email', 'email'), ('PickUpDate', 'pickup date'),
                                           ('PickUpTime', 'pickup time')]
                         if df[col].isna().any()]
                st.info(f"ℹ️ Data quality issues: {', '.join(parts)}")
            if attr == 'bookings_outside_schedule':
                st.info("ℹ️ These bookings are added to the pickup list marked '(ej i schema)'.")
            st.dataframe(df, width='stretch')

    st.download_button(
        label="📥 Download Full Validation Report (diffs.xlsx)",
        data=st.session_state.diffs[config.OUTPUT_FILENAME_DIFFS],
        file_name=config.OUTPUT_FILENAME_DIFFS,
        mime=XLSX_MIME
    )


def order_reports_tab():
    # Step 1: Configuration
    st.header("1️⃣ Configuration")

    col1, col2 = st.columns([1, 2])

    with col1:
        market_key = st.selectbox(
            "Market Type",
            options=list(MARKETS),
            format_func=lambda key: MARKETS[key].label,
            key='market_key',
            help="Chooses the packing categories, packing-list layout and pickup "
                 "schedule. The WordPress exports are the same for all markets."
        )
        market = MARKETS[market_key]

    with col2:
        files = ', '.join(f'`{p.name}`' for p in market.template_files(TEMPLATE_DIR))
        st.info(f"**Templates:** {files}")

    st.divider()

    # Step 2: File Upload
    st.header("2️⃣ Upload Files")

    st.markdown("Upload the exported files from WordPress:")

    col1, col2, col3 = st.columns(3)

    with col1:
        products_file = st.file_uploader(
            "Products (CSV)",
            type=['csv'],
            key='products',
            help="wc-product-export.csv from WordPress"
        )

    with col2:
        orders_file = st.file_uploader(
            "Orders (Excel)",
            type=['xlsx'],
            key='orders',
            help="orders.xlsx from WooCommerce"
        )

    with col3:
        timeslots_file = st.file_uploader(
            "Time Slots (CSV)",
            type=['csv'],
            key='timeslots',
            help="tidsbokning.csv from WP Time Slots"
        )

    st.info("ℹ️ Packing categories and schedule are loaded automatically from templates")

    reset_if_inputs_changed(
        'order_fingerprint',
        (market.key, upload_id(products_file), upload_id(orders_file), upload_id(timeslots_file)),
        ORDER_STATE_KEYS,
    )

    st.divider()

    if not (products_file and orders_file and timeslots_file):
        st.info("👆 Please upload all three required files to continue")
        return

    # Step 3: Validation and Processing
    st.header("3️⃣ Validation & Processing")

    if st.button("▶️ Run Validation", type="primary", width='stretch'):
        for key in ORDER_STATE_KEYS:
            st.session_state.pop(key, None)

        with st.spinner("Loading data..."):
            try:
                st.session_state.order_inputs = load_order_inputs(
                    products_file, orders_file, timeslots_file, market, TEMPLATE_DIR
                )
                st.success("✅ Data loaded successfully!")
            except Exception as e:
                show_error("Error loading data", e)
                st.stop()

        with st.spinner("Running validation..."):
            try:
                result = validate_order_inputs(st.session_state.order_inputs)
                st.session_state.diffs = build_diffs_report(result)
                st.session_state.validation_result = result
                st.success("✅ Validation complete!")
            except Exception as e:
                show_error("Error during validation", e)
                st.stop()

    if 'validation_result' not in st.session_state:
        return

    validation_result = st.session_state.validation_result
    show_validation_results(validation_result)

    st.divider()

    # Step 4: Generate Reports
    st.header("4️⃣ Generate Reports")

    if validation_result.has_errors():
        st.warning("⚠️ Validation issues detected. Review them before proceeding, or continue anyway.")

    if st.button("🚀 Generate All Reports", type="primary", width='stretch'):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def progress(percent, message):
            progress_bar.progress(percent)
            status_text.text(message)

        try:
            st.session_state.reports = build_order_reports(
                st.session_state.order_inputs, TEMPLATE_DIR, progress
            )
            st.success("🎉 All reports generated successfully!")
        except Exception as e:
            show_error("Error generating reports", e)
            st.stop()

    # Step 5: Download
    reports = st.session_state.get('reports')
    if not reports:
        return

    st.divider()
    st.header("5️⃣ Download Reports")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Individual Reports")
        for filename, label in REPORT_LABELS.items():
            if filename in reports:
                st.download_button(label=label, data=reports[filename],
                                   file_name=filename, mime=XLSX_MIME)

    with col2:
        st.subheader("Download All")
        st.download_button(
            label="📦 Download All Reports (ZIP)",
            data=zip_reports({**st.session_state.diffs, **reports}),
            file_name=f'webshop_reports_{st.session_state.order_inputs.market.key}.zip',
            mime='application/zip',
            type="primary"
        )


def inventory_tab():
    st.header("📊 Inventory Report (Lagerrapport)")
    st.markdown("Generate inventory analysis by combining product catalog with sales data.")

    st.divider()

    # Step 1: File Upload
    st.header("1️⃣ Upload Files")

    st.markdown("Upload the exported files from WordPress:")

    col1, col2 = st.columns(2)

    with col1:
        product_export_file = st.file_uploader(
            "Product Export (CSV)",
            type=['csv'],
            key='inventory_product_export',
            help="wc-product-export.csv - Full product catalog"
        )

    with col2:
        products_report_file = st.file_uploader(
            "Products Report (CSV)",
            type=['csv'],
            key='inventory_products_report',
            help="wc-products-report-export.csv - Sales report"
        )

    reset_if_inputs_changed(
        'inventory_fingerprint',
        (upload_id(product_export_file), upload_id(products_report_file)),
        INVENTORY_STATE_KEYS,
    )

    st.divider()

    if not (product_export_file and products_report_file):
        st.info("👆 Please upload both required files to continue")
        return

    # Step 2: Load and Validate
    st.header("2️⃣ Validation & Processing")

    if st.button("▶️ Load and Validate Data", type="primary", width='stretch', key='validate_inventory'):
        for key in INVENTORY_STATE_KEYS:
            st.session_state.pop(key, None)

        with st.spinner("Loading inventory data..."):
            try:
                st.session_state.inventory_result = prepare_inventory(
                    product_export_file, products_report_file, TEMPLATE_DIR
                )
                n = len(st.session_state.inventory_result.inventory)
                st.success(f"✅ Data loaded successfully! {n} products with sales activity")
            except Exception as e:
                show_error("Error loading data", e)

    inventory_result = st.session_state.get('inventory_result')
    if inventory_result is None:
        return

    st.divider()
    validation = inventory_result.validation

    if validation['warnings']:
        st.warning("⚠️ Validation Warnings")
        for warning in validation['warnings']:
            st.write(warning)

        if validation['sku_mismatches']:
            with st.expander(f"SKU Mismatches ({len(validation['sku_mismatches'])})"):
                st.write("SKUs in sales report but not in product export:")
                st.dataframe(pd.DataFrame({'SKU': validation['sku_mismatches']}))

        if len(validation['unmapped_skus']) > 0:
            with st.expander(f"Unmapped SKUs ({len(validation['unmapped_skus'])})"):
                st.write("Products with unknown sales area:")
                st.dataframe(validation['unmapped_skus'][['SKU', 'Product title', 'Category (SKUT)']])

        if len(validation['missing_prices']) > 0:
            with st.expander(f"Missing Prices ({len(validation['missing_prices'])})"):
                st.write("Products with missing price data:")
                st.dataframe(validation['missing_prices'][['SKU', 'Product title', 'Regular price']])

        if len(validation['missing_stock']) > 0:
            with st.expander(f"Missing Stock ({len(validation['missing_stock'])})"):
                st.write("Products with missing stock data:")
                st.dataframe(validation['missing_stock'][['SKU', 'Product title', 'Stock']])
    else:
        st.success("✅ All validation checks passed!")

    st.divider()

    # Step 3: Generate Report
    st.header("3️⃣ Generate Report")

    if st.button("▶️ Generate Lagerrapport", type="primary", width='stretch', key='generate_inventory'):
        with st.spinner("Generating lagerrapport..."):
            try:
                st.session_state.lagerrapport = build_lagerrapport(
                    inventory_result.inventory, TEMPLATE_DIR
                )
                st.success("✅ Lagerrapport generated successfully!")
            except Exception as e:
                show_error("Error generating report", e)

    # Step 4: Download
    lagerrapport = st.session_state.get('lagerrapport')
    if lagerrapport:
        st.divider()
        st.header("4️⃣ Download Report")
        st.download_button(
            label="📥 Download Lagerrapport",
            data=lagerrapport[config.OUTPUT_FILENAME_LAGERRAPPORT],
            file_name=config.OUTPUT_FILENAME_LAGERRAPPORT,
            mime=XLSX_MIME,
            type="primary",
            width='stretch'
        )


def main():
    """Main application logic."""

    # Check authentication
    if not check_password():
        st.stop()

    st.session_state.setdefault('market_key', JULMARKNAD.key)

    # Header
    st.title("📊 WebShop Report Generator")
    st.markdown("Generate reports for Svenska Kyrkan i Wien webshop orders")

    st.divider()

    # Create tabs for different workflows
    tabs = st.tabs(["📦 Order Reports", "📊 Inventory Report"])

    with tabs[0]:
        order_reports_tab()

    with tabs[1]:
        inventory_tab()


if __name__ == "__main__":
    main()
