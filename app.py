"""WebShop Report Generator - Streamlit Web Application

Web interface for generating reports from Svenska Kyrkan i Wien webshop orders.
"""

import hmac
import io
import shutil
import zipfile
from pathlib import Path

import streamlit as st
import pandas as pd

from src import config
from src.data_loader import (
    load_products,
    load_orders,
    load_timeslots,
    load_packing_categories,
    load_schedule,
    load_product_export,
    load_products_report_export,
    load_sku_mapping
)
from src.data_validator import (
    validate_data,
    generate_diffs_report,
    remove_duplicate_bookings,
    validate_inventory_data
)
from src.data_processor import merge_all_data, sort_for_reports
from src.report_generator import (
    generate_packlista,
    generate_hamtningslista,
    generate_semlelista,
    generate_masterlista,
    generate_lagerrapport
)
from src.lagerrapport_processor import prepare_lagerrapport_data


# Page configuration
st.set_page_config(
    page_title="WebShop Report Generator",
    page_icon="📊",
    layout="wide"
)


def check_password():
    """Returns True if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
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


def init_session_state():
    """Initialize session state variables."""
    if 'market_type' not in st.session_state:
        st.session_state.market_type = config.MARKET_TYPE_JULMARKNAD
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = {}
    if 'validation_result' not in st.session_state:
        st.session_state.validation_result = None
    if 'reports_generated' not in st.session_state:
        st.session_state.reports_generated = False


def main():
    """Main application logic."""

    # Check authentication
    if not check_password():
        st.stop()

    # Initialize session state
    init_session_state()

    # Header
    st.title("📊 WebShop Report Generator")
    st.markdown("Generate reports for Svenska Kyrkan i Wien webshop orders")

    st.divider()

    # Create tabs for different workflows
    tabs = st.tabs(["📦 Order Reports", "📊 Inventory Report"])

    with tabs[0]:
        # ===== ORDER REPORTS WORKFLOW =====

        # Step 1: Configuration
        st.header("1️⃣ Configuration")

        col1, col2 = st.columns([1, 2])

        with col1:
            market_type = st.selectbox(
                "Market Type",
                options=config.MARKET_TYPES,
                index=config.MARKET_TYPES.index(st.session_state.market_type),
                help="Select the type of market event"
            )
            st.session_state.market_type = market_type

        with col2:
            st.info(f"**Selected:** {market_type.capitalize()}")

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

        # Check if all files are uploaded
        all_files_uploaded = (
            products_file is not None and
            orders_file is not None and
            timeslots_file is not None
        )

        st.divider()

        # Step 3: Validation and Processing
        if all_files_uploaded:
            st.header("3️⃣ Validation & Processing")

            if st.button("▶️ Run Validation", type="primary", use_container_width=True):
                with st.spinner("Loading data..."):
                    try:
                        # Load uploaded files
                        df_products = load_products(products_file)
                        df_orders = load_orders(orders_file)
                        df_timeslots = load_timeslots(timeslots_file, market_type)

                        # Load templates
                        template_dir = Path('templates')
                        df_packing = load_packing_categories(market_type, template_dir)
                        df_schedule = load_schedule(market_type, template_dir)

                        # Store in session state
                        st.session_state.df_products = df_products
                        st.session_state.df_orders = df_orders
                        st.session_state.df_timeslots = df_timeslots
                        st.session_state.df_packing = df_packing
                        st.session_state.df_schedule = df_schedule

                        st.success("✅ Data loaded successfully!")

                    except Exception as e:
                        st.error(f"❌ Error loading data: {str(e)}")
                        st.stop()

                with st.spinner("Running validation..."):
                    try:
                        # Run validation
                        validation_result = validate_data(
                            st.session_state.df_orders,
                            st.session_state.df_timeslots,
                            st.session_state.df_products,
                            st.session_state.df_packing
                        )

                        st.session_state.validation_result = validation_result

                        # Generate diffs report
                        outputs_dir = Path('outputs')
                        outputs_dir.mkdir(exist_ok=True)

                        diffs_path = outputs_dir / config.OUTPUT_FILENAME_DIFFS
                        generate_diffs_report(validation_result, diffs_path)

                        st.success("✅ Validation complete!")

                    except Exception as e:
                        st.error(f"❌ Error during validation: {str(e)}")
                        st.stop()

            # Display validation results if available
            if st.session_state.validation_result is not None:
                validation_result = st.session_state.validation_result
                summary = validation_result.get_summary()

                st.subheader("Validation Results")

                # Create columns for each validation type
                col1, col2, col3, col4, col5 = st.columns(5)

                with col1:
                    if summary['orders_no_timeslot'] > 0:
                        st.metric("Orders w/o Timeslot", summary['orders_no_timeslot'], delta=None, delta_color="off")
                    else:
                        st.metric("Orders w/o Timeslot", "✓", delta=None)
    
                with col2:
                    if summary['timeslots_no_order'] > 0:
                        st.metric("Timeslots w/o Order", summary['timeslots_no_order'], delta=None, delta_color="off")
                    else:
                        st.metric("Timeslots w/o Order", "✓", delta=None)
    
                with col3:
                    if summary['duplicate_bookings'] > 0:
                        st.metric("Duplicate Bookings", summary['duplicate_bookings'], delta=None, delta_color="off")
                    else:
                        st.metric("Duplicate Bookings", "✓", delta=None)
    
                with col4:
                    if summary['missing_products'] > 0:
                        st.metric("Missing Products", summary['missing_products'], delta=None, delta_color="off")
                    else:
                        st.metric("Missing Products", "✓", delta=None)
    
                with col5:
                    if summary['missing_categories'] > 0:
                        st.metric("Missing Categories", summary['missing_categories'], delta=None, delta_color="off")
                    else:
                        st.metric("Missing Categories", "✓", delta=None)
    
                # Show details in expanders
                if summary['orders_no_timeslot'] > 0:
                    with st.expander(f"⚠️ View {summary['orders_no_timeslot']} Orders Without Timeslot"):
                        st.dataframe(validation_result.orders_no_timeslot, use_container_width=True)
    
                if summary['timeslots_no_order'] > 0:
                    with st.expander(f"⚠️ View {summary['timeslots_no_order']} Timeslots Without Order"):
                        st.dataframe(validation_result.timeslots_no_order, use_container_width=True)
    
                if summary['duplicate_bookings'] > 0:
                    with st.expander(f"⚠️ View {summary['duplicate_bookings']} Duplicate Bookings"):
                        st.dataframe(validation_result.duplicate_bookings, use_container_width=True)
    
                if summary['missing_products'] > 0:
                    with st.expander(f"⚠️ View {summary['missing_products']} Missing Products"):
                        st.dataframe(validation_result.missing_products, use_container_width=True)
    
                if summary['missing_categories'] > 0:
                    with st.expander(f"⚠️ View {summary['missing_categories']} Missing Categories"):
                        st.dataframe(validation_result.missing_categories, use_container_width=True)
    
                # Download diffs report
                st.download_button(
                    label="📥 Download Full Validation Report (diffs.xlsx)",
                    data=open('outputs/diffs.xlsx', 'rb').read(),
                    file_name='diffs.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
    
                st.divider()
    
                # Step 4: Generate Reports
                st.header("4️⃣ Generate Reports")
    
                if validation_result.has_errors():
                    st.warning("⚠️ Validation issues detected. Review them before proceeding, or continue anyway.")
    
                if st.button("🚀 Generate All Reports", type="primary", use_container_width=True):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
    
                    try:
                        # Remove duplicates from timeslots
                        status_text.text("Removing duplicate bookings...")
                        df_timeslots_clean = remove_duplicate_bookings(st.session_state.df_timeslots)
                        progress_bar.progress(10)
    
                        # Merge all data
                        status_text.text("Merging datasets...")
                        df_all_data = merge_all_data(
                            st.session_state.df_orders,
                            df_timeslots_clean,
                            st.session_state.df_products,
                            st.session_state.df_packing
                        )
                        df_all_data = sort_for_reports(df_all_data)
                        progress_bar.progress(25)
    
                        outputs_dir = Path('outputs')
                        template_dir = Path('templates')
    
                        # Save allData for debugging
                        status_text.text("Saving merged data...")
                        df_all_data.to_excel(outputs_dir / config.OUTPUT_FILENAME_ALLDATA, engine='openpyxl')
                        progress_bar.progress(30)
    
                        # Generate packlista
                        status_text.text("Generating packing lists...")
                        generate_packlista(
                            df_all_data,
                            template_dir,
                            outputs_dir / config.OUTPUT_FILENAME_PACKLISTA,
                            market_type
                        )
                        progress_bar.progress(50)
    
                        # Generate hämtningslista
                        status_text.text("Generating pickup lists...")
                        generate_hamtningslista(
                            df_all_data,
                            st.session_state.df_schedule,
                            template_dir,
                            outputs_dir / config.OUTPUT_FILENAME_HAMTNINGSLISTA
                        )
                        progress_bar.progress(70)
    
                        # Generate semlelista (only for pask)
                        if market_type == config.MARKET_TYPE_PASK:
                            status_text.text("Generating semla list...")
                            generate_semlelista(
                                df_all_data,
                                template_dir,
                                outputs_dir / config.OUTPUT_FILENAME_SEMLELISTA
                            )
                        progress_bar.progress(85)
    
                        # Generate masterlista
                        status_text.text("Generating master list...")
                        generate_masterlista(
                            df_all_data,
                            outputs_dir / config.OUTPUT_FILENAME_MASTERLISTA
                        )
                        progress_bar.progress(100)
    
                        status_text.text("✅ All reports generated successfully!")
                        st.session_state.reports_generated = True
    
                        st.success("🎉 All reports generated successfully!")
    
                    except Exception as e:
                        st.error(f"❌ Error generating reports: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
                        st.stop()
    
                # Download section
                if st.session_state.reports_generated:
                    st.divider()
                    st.header("5️⃣ Download Reports")
    
                    col1, col2 = st.columns(2)
    
                    with col1:
                        # Individual downloads
                        st.subheader("Individual Reports")
    
                        if Path('outputs/packlista.xlsx').exists():
                            st.download_button(
                                label="📥 Packlista (Packing Lists)",
                                data=open('outputs/packlista.xlsx', 'rb').read(),
                                file_name='packlista.xlsx',
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                            )
    
                        if Path('outputs/hämtningslista.xlsx').exists():
                            st.download_button(
                                label="📥 Hämtningslista (Pickup Lists)",
                                data=open('outputs/hämtningslista.xlsx', 'rb').read(),
                                file_name='hämtningslista.xlsx',
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                            )
    
                        if market_type == config.MARKET_TYPE_PASK and Path('outputs/semlelista.xlsx').exists():
                            st.download_button(
                                label="📥 Semlelista (Semla List)",
                                data=open('outputs/semlelista.xlsx', 'rb').read(),
                                file_name='semlelista.xlsx',
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                            )
    
                        if Path('outputs/masterlista.xlsx').exists():
                            st.download_button(
                                label="📥 Masterlista (Master List)",
                                data=open('outputs/masterlista.xlsx', 'rb').read(),
                                file_name='masterlista.xlsx',
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                            )
    
                    with col2:
                        # Download all as ZIP
                        st.subheader("Download All")
    
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for report_file in Path('outputs').glob('*.xlsx'):
                                zip_file.write(report_file, arcname=report_file.name)
    
                        st.download_button(
                            label="📦 Download All Reports (ZIP)",
                            data=zip_buffer.getvalue(),
                            file_name=f'webshop_reports_{market_type}.zip',
                            mime='application/zip',
                            type="primary"
                        )
    
            else:
                st.info("👆 Please upload all three required files to continue")

    with tabs[1]:
        # ===== INVENTORY REPORT WORKFLOW =====

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

        # Check if both files are uploaded
        inventory_files_uploaded = (
            product_export_file is not None and
            products_report_file is not None
        )

        st.divider()

        # Step 2: Load and Validate
        if inventory_files_uploaded:
            st.header("2️⃣ Validation & Processing")

            if st.button("▶️ Load and Validate Data", type="primary", use_container_width=True, key='validate_inventory'):
                with st.spinner("Loading inventory data..."):
                    try:
                        # Load uploaded files
                        df_product_export = load_product_export(product_export_file)
                        df_products_report = load_products_report_export(products_report_file)

                        # Load SKU mapping from templates
                        template_dir = Path('templates')
                        df_sku_mapping = load_sku_mapping(template_dir)

                        # Process inventory data
                        df_inventory = prepare_lagerrapport_data(
                            df_product_export,
                            df_products_report,
                            df_sku_mapping
                        )

                        # Validate
                        validation = validate_inventory_data(
                            df_product_export,
                            df_products_report,
                            df_inventory
                        )

                        # Store in session state
                        st.session_state.df_inventory = df_inventory
                        st.session_state.inventory_validation = validation
                        st.session_state.inventory_data_validated = True

                        st.success(f"✅ Data loaded successfully! {len(df_inventory)} products with sales activity")

                    except Exception as e:
                        st.error(f"❌ Error loading data: {str(e)}")
                        st.exception(e)

            # Show validation results if available
            if st.session_state.get('inventory_data_validated', False):
                st.divider()
                validation = st.session_state.inventory_validation

                if validation['warnings']:
                    st.warning("⚠️ Validation Warnings")
                    for warning in validation['warnings']:
                        st.write(warning)

                    # Show details in expanders
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

                if st.button("▶️ Generate Lagerrapport", type="primary", use_container_width=True, key='generate_inventory'):
                    with st.spinner("Generating lagerrapport..."):
                        try:
                            # Create outputs directory
                            Path('outputs').mkdir(exist_ok=True)

                            # Generate report
                            template_dir = Path('templates')
                            output_path = Path('outputs') / config.OUTPUT_FILENAME_LAGERRAPPORT

                            generate_lagerrapport(
                                st.session_state.df_inventory,
                                template_dir,
                                output_path
                            )

                            st.session_state.lagerrapport_generated = True
                            st.success("✅ Lagerrapport generated successfully!")

                        except Exception as e:
                            st.error(f"❌ Error generating report: {str(e)}")
                            st.exception(e)

                # Step 4: Download
                if st.session_state.get('lagerrapport_generated', False):
                    st.divider()
                    st.header("4️⃣ Download Report")

                    if Path('outputs/lagerrapport.xlsx').exists():
                        st.download_button(
                            label="📥 Download Lagerrapport",
                            data=open('outputs/lagerrapport.xlsx', 'rb').read(),
                            file_name='lagerrapport.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            type="primary",
                            use_container_width=True
                        )

        else:
            st.info("👆 Please upload both required files to continue")


if __name__ == "__main__":
    main()
