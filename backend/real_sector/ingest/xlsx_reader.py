"""Minimal XLSX value reader that needs no Excel-engine dependency."""
from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _column(reference: str) -> int:
    value = 0
    for char in (part for part in reference if part.isalpha()):
        value = value * 26 + ord(char.upper()) - 64
    return value - 1


def read_xlsx_rows(path: Path) -> list[list[str]]:
    """Read values in the first sheet, including blank cells between values."""
    with ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.iterfind(".//m:t", NS))
                      for item in root.findall("m:si", NS)]
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    parsed, widest = [], 0
    for source_row in root.findall(".//m:sheetData/m:row", NS):
        row: dict[int, str] = {}
        for cell in source_row.findall("m:c", NS):
            column = _column(cell.get("r", "A1"))
            value_node = cell.find("m:v", NS)
            value = "" if value_node is None else value_node.text or ""
            if cell.get("t") == "s" and value:
                value = shared[int(value)]
            elif cell.get("t") == "inlineStr":
                node = cell.find(".//m:t", NS)
                value = "" if node is None else node.text or ""
            row[column] = value
            widest = max(widest, column + 1)
        parsed.append(row)
    return [[row.get(index, "") for index in range(widest)] for row in parsed]
