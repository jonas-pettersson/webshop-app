# WebShop Report Tests

This directory contains automated regression tests for the WebShop Report application.

## Test Structure

```
tests/
├── conftest.py                    # Shared pytest fixtures
├── fixtures/                      # Test data files
│   └── pask/                      # Test data for pask market type
│       ├── orders.xlsx
│       ├── tidsbokning.csv
│       ├── wc-product-export.csv
│       ├── wc-products-report-export.csv
│       ├── placeringsnycklar.xlsx
│       └── schedule.xlsx
├── test_data_loader.py            # Tests for CSV/Excel loading
├── test_data_processor.py         # Tests for data merging
├── test_data_validator.py         # Tests for data validation
├── test_inventory_report.py       # Tests for inventory report
└── test_report_generator.py       # Tests for all report generation
```

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
# Test data loading
pytest tests/test_data_loader.py

# Test inventory report
pytest tests/test_inventory_report.py

# Test report generation
pytest tests/test_report_generator.py
```

### Run Tests with Coverage

```bash
pytest --cov=src --cov-report=html
```

This generates a coverage report in `htmlcov/index.html`.

### Run Specific Test Classes or Functions

```bash
# Run a specific test class
pytest tests/test_data_loader.py::TestLoadProducts

# Run a specific test function
pytest tests/test_data_loader.py::TestLoadProducts::test_load_products_pask
```

## Test Coverage

The test suite covers:

### 1. **Data Loading** (`test_data_loader.py`)
   - Loading products, orders, timeslots from CSV/Excel
   - Loading templates (packing categories, schedules)
   - **Decimal notation handling** (English dots vs German commas)
   - Loading inventory report data

### 2. **Data Processing** (`test_data_processor.py`)
   - Merging orders, timeslots, products, packing categories
   - Correct sorting of merged data
   - Handling missing timeslots (LEFT join behavior)

### 3. **Data Validation** (`test_data_validator.py`)
   - Detecting orders without timeslots
   - Detecting timeslots without orders
   - Finding duplicate bookings
   - Identifying missing products
   - Finding missing packing categories
   - Validating inventory data (missing prices)

### 4. **Inventory Report** (`test_inventory_report.py`)
   - SKU to sales area mapping
   - Tax rate calculation
   - Full inventory data processing
   - **Regression test for decimal notation fix**
   - Integration tests with real test data

### 5. **Report Generation** (`test_report_generator.py`)
   - Generating packing lists (packlista)
   - Generating pickup schedules (hämtningslista)
   - Generating semla lists (semlelista)
   - Generating master lists (masterlista)
   - Generating inventory reports (lagerrapport)
   - **Full end-to-end pipeline tests**

## Test Data

### Current Coverage
- ✅ **pask** - Complete test dataset with all required files

### Future Coverage
- ⏳ **julmarknad** - Pending test data
- ⏳ **julmaten** - Pending test data

To add test data for other market types:
1. Create directory: `tests/fixtures/{market_type}/`
2. Add the same set of files as in `pask/`
3. Tests will automatically work with new fixtures

## Key Tests

### Decimal Notation Fix (Critical)

The most important regression test is in `test_data_loader.py::TestLoadProductExport::test_decimal_notation_handling`:

```python
def test_decimal_notation_handling(self, tmp_path):
    """Test that both English (dot) and German (comma) decimal notation work."""
```

This test ensures that:
- Prices like "12,50" (German) parse correctly as 12.50
- Prices like "12.50" (English) parse correctly as 12.50
- Both formats work in calculations

### Full Pipeline Tests

The `TestFullPipeline` class in `test_report_generator.py` runs complete end-to-end tests:
- Loads all test data
- Processes and validates
- Generates all reports
- Verifies output files are created and valid

## Adding New Tests

When adding features or fixing bugs:

1. **Add test data** to `fixtures/pask/` if needed
2. **Write a test** in the appropriate test file
3. **Run the test** to ensure it passes
4. **Commit both** test code and test data

Example:
```python
def test_new_feature(self, pask_fixtures_dir):
    """Test description."""
    # Load test data
    # Process
    # Assert expected behavior
```

## Continuous Integration

Tests are designed to run in CI/CD pipelines:
- No external dependencies required
- All test data committed to repo
- Fast execution (< 1 minute for full suite)
- Clear pass/fail output

## Troubleshooting

### Test Failures

If tests fail:
1. Check that test data files are present in `fixtures/pask/`
2. Ensure dependencies are installed: `pip install -r requirements-dev.txt`
3. Run with verbose output: `pytest -vv`
4. Check specific test: `pytest tests/test_file.py::TestClass::test_method -vv`

### Missing Test Data

If you see errors about missing files:
```
FileNotFoundError: [Errno 2] No such file or directory: 'tests/fixtures/pask/orders.xlsx'
```

Ensure all test files are present in the fixtures directory.

## Test Philosophy

These tests follow the principle of **testing behavior, not implementation**:
- Tests verify that reports are generated correctly
- Tests check that data is processed as expected
- Tests use real (anonymized) production data
- Tests don't mock core business logic

This ensures tests catch real regressions and remain valuable as the code evolves.
