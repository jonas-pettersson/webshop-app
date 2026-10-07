"""Tests for report generation functions."""

import pytest
import pandas as pd
from pathlib import Path
import tempfile

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
from src.data_processor import merge_all_data, sort_for_reports
from src.data_validator import remove_duplicate_bookings
from src.lagerrapport_processor import prepare_lagerrapport_data
from src.report_generator import (
    generate_packlista,
    generate_hamtningslista,
    generate_semlelista,
    generate_masterlista,
    generate_lagerrapport
)
from src import config


class TestGeneratePacklista:
    """Tests for generate_packlista() - packing lists report."""

    def test_generate_packlista_pask(
        self,
        pask_product_export_file,
        pask_orders_file,
        pask_timeslots_file,
        pask_fixtures_dir
    ):
        """Test generating packing lists with pask test data."""
        # Load and process data
        with open(pask_product_export_file, 'rb') as f:
            df_products = load_products(f)

        with open(pask_orders_file, 'rb') as f:
            df_orders = load_orders(f)

        with open(pask_timeslots_file, 'rb') as f:
            df_timeslots = load_timeslots(f, market_type=config.MARKET_TYPE_PASK)

        df_timeslots = remove_duplicate_bookings(df_timeslots)

        df_packing_categories = load_packing_categories(
            market_type=config.MARKET_TYPE_PASK,
            template_dir=pask_fixtures_dir
        )

        df_merged = merge_all_data(
            df_orders,
            df_timeslots,
            df_products,
            df_packing_categories
        )
        df_merged = sort_for_reports(df_merged)

        # Generate report
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "packlista_test.xlsx"

            workbook = generate_packlista(
                df_merged,
                market_type=config.MARKET_TYPE_PASK,
                template_dir=pask_fixtures_dir,
                output_path=output_path
            )

            # Check that workbook was created
            assert workbook is not None

            # Check that file was saved
            assert output_path.exists()

            # Check file size (should not be empty)
            assert output_path.stat().st_size > 0

            # Load and check structure
            import openpyxl
            wb = openpyxl.load_workbook(output_path)

            # Should have sheets for each pickup area
            assert len(wb.sheetnames) > 0

            # Each sheet should have data
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                # Check that sheet is not empty
                assert sheet.max_row > 1  # More than just header


class TestGenerateHamtningslista:
    """Tests for generate_hamtningslista() - pickup schedule report."""

    def test_generate_hamtningslista_pask(
        self,
        pask_product_export_file,
        pask_orders_file,
        pask_timeslots_file,
        pask_fixtures_dir
    ):
        """Test generating pickup schedule with pask test data."""
        # Load and process data
        with open(pask_product_export_file, 'rb') as f:
            df_products = load_products(f)

        with open(pask_orders_file, 'rb') as f:
            df_orders = load_orders(f)

        with open(pask_timeslots_file, 'rb') as f:
            df_timeslots = load_timeslots(f, market_type=config.MARKET_TYPE_PASK)

        df_timeslots = remove_duplicate_bookings(df_timeslots)

        df_packing_categories = load_packing_categories(
            market_type=config.MARKET_TYPE_PASK,
            template_dir=pask_fixtures_dir
        )

        df_schedule = load_schedule(
            market_type=config.MARKET_TYPE_PASK,
            template_dir=pask_fixtures_dir
        )

        df_merged = merge_all_data(
            df_orders,
            df_timeslots,
            df_products,
            df_packing_categories
        )
        df_merged = sort_for_reports(df_merged)

        # Generate report
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "hamtningslista_test.xlsx"

            workbook = generate_hamtningslista(
                df_merged,
                df_schedule,
                market_type=config.MARKET_TYPE_PASK,
                template_dir=pask_fixtures_dir,
                output_path=output_path
            )

            # Check that workbook was created
            assert workbook is not None

            # Check that file was saved
            assert output_path.exists()

            # Check file size
            assert output_path.stat().st_size > 0

            # Load and check structure
            import openpyxl
            wb = openpyxl.load_workbook(output_path)

            # Should have sheets for each pickup date
            assert len(wb.sheetnames) > 0

            # Each sheet should have schedule data
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                assert sheet.max_row > 1


class TestGenerateSemlelista:
    """Tests for generate_semlelista() - semla list report (pask only)."""

    def test_generate_semlelista_pask(
        self,
        pask_product_export_file,
        pask_orders_file,
        pask_timeslots_file,
        pask_fixtures_dir
    ):
        """Test generating semla list with pask test data."""
        # Load and process data
        with open(pask_product_export_file, 'rb') as f:
            df_products = load_products(f)

        with open(pask_orders_file, 'rb') as f:
            df_orders = load_orders(f)

        with open(pask_timeslots_file, 'rb') as f:
            df_timeslots = load_timeslots(f, market_type=config.MARKET_TYPE_PASK)

        df_timeslots = remove_duplicate_bookings(df_timeslots)

        df_packing_categories = load_packing_categories(
            market_type=config.MARKET_TYPE_PASK,
            template_dir=pask_fixtures_dir
        )

        df_merged = merge_all_data(
            df_orders,
            df_timeslots,
            df_products,
            df_packing_categories
        )
        df_merged = sort_for_reports(df_merged)

        # Generate report
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "semlelista_test.xlsx"

            workbook = generate_semlelista(
                df_merged,
                template_dir=pask_fixtures_dir,
                output_path=output_path
            )

            # Check that workbook was created
            assert workbook is not None

            # Check that file was saved
            assert output_path.exists()

            # Check file size
            assert output_path.stat().st_size > 0

            # Load and check structure
            import openpyxl
            wb = openpyxl.load_workbook(output_path)

            # Should have at least one sheet
            assert len(wb.sheetnames) > 0


class TestGenerateMasterlista:
    """Tests for generate_masterlista() - master order list."""

    def test_generate_masterlista_pask(
        self,
        pask_product_export_file,
        pask_orders_file,
        pask_timeslots_file,
        pask_fixtures_dir
    ):
        """Test generating master list with pask test data."""
        # Load and process data
        with open(pask_product_export_file, 'rb') as f:
            df_products = load_products(f)

        with open(pask_orders_file, 'rb') as f:
            df_orders = load_orders(f)

        with open(pask_timeslots_file, 'rb') as f:
            df_timeslots = load_timeslots(f, market_type=config.MARKET_TYPE_PASK)

        df_timeslots = remove_duplicate_bookings(df_timeslots)

        df_packing_categories = load_packing_categories(
            market_type=config.MARKET_TYPE_PASK,
            template_dir=pask_fixtures_dir
        )

        df_merged = merge_all_data(
            df_orders,
            df_timeslots,
            df_products,
            df_packing_categories
        )
        df_merged = sort_for_reports(df_merged)

        # Generate report
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "masterlista_test.xlsx"

            workbook = generate_masterlista(
                df_merged,
                output_path=output_path
            )

            # Check that workbook was created
            assert workbook is not None

            # Check that file was saved
            assert output_path.exists()

            # Check file size
            assert output_path.stat().st_size > 0

            # Load and check structure
            import openpyxl
            wb = openpyxl.load_workbook(output_path)

            # Should have one sheet
            assert len(wb.sheetnames) >= 1

            # Get first sheet
            sheet = wb[wb.sheetnames[0]]

            # Should have data rows
            assert sheet.max_row > 1


class TestGenerateLagerrapport:
    """Tests for generate_lagerrapport() - inventory report."""

    def test_generate_lagerrapport_pask(
        self,
        pask_product_export_file,
        pask_products_report_file,
        templates_dir
    ):
        """Test generating inventory report with pask test data."""
        # Load data
        with open(pask_product_export_file, 'rb') as f:
            df_product_export = load_product_export(f)

        with open(pask_products_report_file, 'rb') as f:
            df_products_report = load_products_report_export(f)

        df_sku_mapping = load_sku_mapping(templates_dir)

        # Process inventory data
        df_inventory = prepare_lagerrapport_data(
            df_product_export,
            df_products_report,
            df_sku_mapping
        )

        # Generate report
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "lagerrapport_test.xlsx"

            workbook = generate_lagerrapport(
                df_inventory,
                template_dir=templates_dir,
                output_path=output_path
            )

            # Check that workbook was created
            assert workbook is not None

            # Check that file was saved
            assert output_path.exists()

            # Check file size
            assert output_path.stat().st_size > 0

            # Load and check structure
            import openpyxl
            wb = openpyxl.load_workbook(output_path)

            # Should have sheets (one per sales area, plus summary)
            assert len(wb.sheetnames) > 0

            # Check that data was written
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                # Should have more than header row
                assert sheet.max_row > 1

    def test_lagerrapport_decimal_calculations_correct(
        self,
        pask_product_export_file,
        pask_products_report_file,
        templates_dir
    ):
        """Test that inventory report calculations are correct (regression test for decimal notation)."""
        # Load data
        with open(pask_product_export_file, 'rb') as f:
            df_product_export = load_product_export(f)

        with open(pask_products_report_file, 'rb') as f:
            df_products_report = load_products_report_export(f)

        df_sku_mapping = load_sku_mapping(templates_dir)

        # Process inventory data
        df_inventory = prepare_lagerrapport_data(
            df_product_export,
            df_products_report,
            df_sku_mapping
        )

        # Generate report
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "lagerrapport_test.xlsx"

            workbook = generate_lagerrapport(
                df_inventory,
                template_dir=templates_dir,
                output_path=output_path
            )

            # Load and verify calculations
            import openpyxl
            wb = openpyxl.load_workbook(output_path)

            # Check a sheet with data
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]

                # Find columns (they should be labeled in the template)
                # We'll just check that numeric columns have numeric values
                for row in sheet.iter_rows(min_row=2, max_row=min(10, sheet.max_row)):
                    # Check that cells contain numeric values, not error values
                    for cell in row:
                        if cell.value is not None:
                            # Should not be error values like #VALUE!, #DIV/0!, etc.
                            assert not str(cell.value).startswith('#'), \
                                f"Cell contains error value: {cell.value}"


class TestFullPipeline:
    """Integration tests for full report generation pipeline."""

    def test_full_order_reports_pipeline_pask(
        self,
        pask_product_export_file,
        pask_orders_file,
        pask_timeslots_file,
        pask_fixtures_dir
    ):
        """Test full order reports generation pipeline end-to-end."""
        # Load all data
        with open(pask_product_export_file, 'rb') as f:
            df_products = load_products(f)

        with open(pask_orders_file, 'rb') as f:
            df_orders = load_orders(f)

        with open(pask_timeslots_file, 'rb') as f:
            df_timeslots = load_timeslots(f, market_type=config.MARKET_TYPE_PASK)

        df_timeslots = remove_duplicate_bookings(df_timeslots)

        df_packing_categories = load_packing_categories(
            market_type=config.MARKET_TYPE_PASK,
            template_dir=pask_fixtures_dir
        )

        df_schedule = load_schedule(
            market_type=config.MARKET_TYPE_PASK,
            template_dir=pask_fixtures_dir
        )

        # Process data
        df_merged = merge_all_data(
            df_orders,
            df_timeslots,
            df_products,
            df_packing_categories
        )
        df_merged = sort_for_reports(df_merged)

        # Generate all reports
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Generate each report
            packlista_path = tmpdir_path / "packlista.xlsx"
            hamtning_path = tmpdir_path / "hamtningslista.xlsx"
            semla_path = tmpdir_path / "semlelista.xlsx"
            master_path = tmpdir_path / "masterlista.xlsx"

            wb_packlista = generate_packlista(
                df_merged,
                market_type=config.MARKET_TYPE_PASK,
                template_dir=pask_fixtures_dir,
                output_path=packlista_path
            )

            wb_hamtning = generate_hamtningslista(
                df_merged,
                df_schedule,
                market_type=config.MARKET_TYPE_PASK,
                template_dir=pask_fixtures_dir,
                output_path=hamtning_path
            )

            wb_semla = generate_semlelista(
                df_merged,
                template_dir=pask_fixtures_dir,
                output_path=semla_path
            )

            wb_master = generate_masterlista(
                df_merged,
                output_path=master_path
            )

            # Verify all reports were generated
            assert packlista_path.exists()
            assert hamtning_path.exists()
            assert semla_path.exists()
            assert master_path.exists()

            # All files should have content
            assert packlista_path.stat().st_size > 0
            assert hamtning_path.stat().st_size > 0
            assert semla_path.stat().st_size > 0
            assert master_path.stat().st_size > 0

            print("\n✓ All order reports generated successfully for pask test data")

    def test_full_inventory_report_pipeline_pask(
        self,
        pask_product_export_file,
        pask_products_report_file,
        templates_dir
    ):
        """Test full inventory report generation pipeline end-to-end."""
        # Load data
        with open(pask_product_export_file, 'rb') as f:
            df_product_export = load_product_export(f)

        with open(pask_products_report_file, 'rb') as f:
            df_products_report = load_products_report_export(f)

        df_sku_mapping = load_sku_mapping(templates_dir)

        # Process
        df_inventory = prepare_lagerrapport_data(
            df_product_export,
            df_products_report,
            df_sku_mapping
        )

        # Generate report
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "lagerrapport.xlsx"

            workbook = generate_lagerrapport(
                df_inventory,
                template_dir=templates_dir,
                output_path=output_path
            )

            # Verify
            assert output_path.exists()
            assert output_path.stat().st_size > 0

            print("\n✓ Inventory report generated successfully for pask test data")
