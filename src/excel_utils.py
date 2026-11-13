"""Excel helpers: template workbooks, row insertion, safe cell writing.

ReportTemplate wraps the template system (named ranges, a 'template' sheet
that is copied per report sheet, row insertion with formatting).
"""

import io
from copy import copy

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.utils.cell import coordinate_to_tuple


def excel_value(value):
    """Convert a pandas/python value into something openpyxl can write.

    Missing values (None, NaN, NaT) become None, i.e. an empty cell.
    """
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def set_cell_value(cell, value):
    """Write a value into a cell, never letting user text become a formula.

    openpyxl stores any string starting with '=' as a formula. Customer
    names/notes come from the public webshop, so such strings are forced
    to plain text (displayed exactly as typed).
    """
    cell.value = excel_value(value)
    if isinstance(cell.value, str) and cell.value.startswith('='):
        cell.data_type = 's'


def neutralize_formulas(workbook: Workbook) -> None:
    """Turn every formula cell into plain text.

    Only for workbooks built from data (pandas.to_excel), which never
    contain intended formulas - not for templates.
    """
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.data_type == 'f':
                    cell.data_type = 's'


def workbook_to_bytes(workbook: Workbook) -> bytes:
    """Serialize a workbook to .xlsx bytes (no file on disk)."""
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def dataframe_to_xlsx_bytes(sheets: dict, align_widths: bool = False) -> bytes:
    """Write {sheet_name: DataFrame} to .xlsx bytes, formula-safe.

    Args:
        sheets: Ordered mapping of sheet name to DataFrame (index is written,
            same as DataFrame.to_excel defaults)
        align_widths: Auto-fit column widths on every sheet
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name)
        workbook = writer.book
        neutralize_formulas(workbook)
        if align_widths:
            for sheet in workbook.worksheets:
                align_cell_width_for(sheet)
    return buffer.getvalue()


class ReportTemplate:
    """An Excel template whose sheet 'template' is copied for each report sheet.

    The template defines named ranges (e.g. 'FullName', 'ArticleNumber').
    fill(sheet, 'FullName', value, row_offset=3) writes into the cell the
    name points at, shifted down by row_offset rows. Unknown names are
    ignored, so a template may leave out fields it doesn't show.

    Usage:
        tpl = ReportTemplate(path)
        sheet = tpl.new_sheet('PO_123')
        tpl.fill(sheet, 'FullName', 'Anna')
        data = tpl.to_bytes()     # removes the 'template' sheet
    """

    SHEET_NAME = 'template'

    def __init__(self, path):
        self.workbook = load_workbook(filename=path)
        self.sheet = self.workbook[self.SHEET_NAME]
        # name -> (row, column) of the first cell on the template sheet
        self._positions = {}
        for name, defined_name in self.workbook.defined_names.items():
            for sheet_title, coordinate in defined_name.destinations:
                if sheet_title == self.sheet.title:
                    row, column = coordinate_to_tuple(coordinate.replace('$', ''))
                    self._positions[name] = (row, column)
                    break

    def row(self, name: str) -> int:
        """Template row of a named cell."""
        return self._positions[name][0]

    def new_sheet(self, title: str):
        """Copy the template sheet into a new sheet with the given title."""
        sheet = self.workbook.copy_worksheet(self.sheet)
        sheet.title = title
        return sheet

    def fill(self, sheet, name: str, value, row_offset: int = 0) -> None:
        """Write value into the named cell, row_offset rows below its template position."""
        if name not in self._positions:
            return
        row, column = self._positions[name]
        set_cell_value(sheet.cell(row=row + row_offset, column=column), value)

    def fill_many(self, sheet, record, names, row_offset: int = 0) -> None:
        """fill() for several names, taking each value from record[name]."""
        for name in names:
            self.fill(sheet, name, record[name], row_offset)

    def insert_row(self, sheet, source_row: int, target_row: int) -> None:
        """Insert a row in sheet, formatted like template row source_row."""
        insert_row_and_copy_format(self.sheet, sheet, source_row, target_row)

    def copy_row_heights(self, sheet, source_row: int, target_row: int, count: int) -> None:
        """Give count rows from target_row the heights of the template rows from source_row."""
        for j in range(count):
            sheet.row_dimensions[target_row + j].height =                 self.sheet.row_dimensions[source_row + j].height

    def to_bytes(self) -> bytes:
        """Remove the template sheet and return the finished .xlsx."""
        self.workbook.remove(self.sheet)
        return workbook_to_bytes(self.workbook)


def get_merged_cells_or_none(sheet, row, column):
    """Check if a cell is part of a merged cell range.

    Args:
        sheet: openpyxl Worksheet object
        row: Row number (1-indexed)
        column: Column number (1-indexed)

    Returns:
        MergedCellRange object if cell is merged, None otherwise
    """
    cell = sheet.cell(row, column)

    for merged_cell in sheet.merged_cells.ranges:
        if cell.coordinate in merged_cell:
            return merged_cell

    return None


def insert_row_and_copy_format(template, sheet, source_row, target_row):
    """Insert a row in the sheet and copy all formatting from the template.

    This preserves cell styles, row height, and merged cell ranges from the template.
    Critical for maintaining Excel report appearance.

    Args:
        template: Template worksheet (source of formatting)
        sheet: Target worksheet (where row is inserted)
        source_row: Row number in template to copy formatting from
        target_row: Row number in sheet where new row should be inserted
    """
    sheet.insert_rows(idx=target_row)
    sheet.row_dimensions[target_row].height = template.row_dimensions[source_row].height

    # Copy cell styles and handle merged cells
    for col in range(1, 11):  # Assuming max 10 columns
        sheet.cell(row=target_row, column=col)._style = template.cell(row=source_row, column=col)._style

        merged_cells = get_merged_cells_or_none(template, source_row, col)
        if merged_cells is not None and col == merged_cells.bounds[0]:
            # Only process the first column of a merged range
            merged_cells_copy = copy(merged_cells)
            if target_row > source_row:
                merged_cells_copy.shift(row_shift=target_row - source_row)
                sheet.merge_cells(range_string=(merged_cells_copy.coord))


def align_cell_width_for(sheet):
    """Auto-adjust column widths based on cell content.

    Iterates through all cells and sets column width to accommodate the longest
    content in each column.

    Args:
        sheet: openpyxl Worksheet object
    """
    dims = {}

    for row in sheet.rows:
        for cell in row:
            if cell.value:
                dims[cell.column_letter] = max(
                    (dims.get(cell.column_letter, 0), len(str(cell.value)))
                )

    for col, value in dims.items():
        sheet.column_dimensions[col].width = value * 1.23
