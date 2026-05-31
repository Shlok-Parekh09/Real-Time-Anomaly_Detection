from __future__ import annotations

import difflib
import io
import json
import os
import re
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime
from typing import Any
from xml.etree import ElementTree as ET


PDF_EOF_MARKER = b"%%EOF"
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
OOXML_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
CORE_NS = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
}


def detect_file_type(file_name: str, content_type: str, document_bytes: bytes) -> str:
    lower_name = (file_name or "").lower()
    lower_type = (content_type or "").lower()

    if document_bytes.startswith(b"%PDF") or lower_name.endswith(".pdf"):
        return "pdf"
    if lower_name.endswith((".xlsx", ".xlsm", ".xltx", ".xltm")):
        return "excel"
    if lower_name.endswith((".docx", ".docm", ".dotx", ".dotm")):
        return "word"
    if lower_name.endswith(".doc"):
        return "word"
    if lower_name.endswith(".xls"):
        return "excel"
    if document_bytes.startswith(OLE_MAGIC):
        if lower_name.endswith(".doc"):
            return "word"
        return "excel"
    if lower_type.startswith("image/") or lower_name.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")):
        return "image"
    if lower_type.startswith("text/") or lower_name.endswith((".csv", ".tsv", ".txt")):
        return "text"
    if document_bytes.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(document_bytes)) as archive:
                if "word/document.xml" in archive.namelist():
                    return "word"
                if "xl/workbook.xml" in archive.namelist():
                    return "excel"
        except zipfile.BadZipFile:
            pass
    return "unknown"


def _decode_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="ignore")


def _compact_text(value: str, max_len: int = 220) -> str:
    cleaned = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(cleaned) <= max_len:
        return cleaned
    return f"{cleaned[: max_len - 3]}..."


def _parse_pdf_date(value: str | None) -> datetime | None:
    if not value:
        return None
    match = re.search(r"D:(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?", value)
    if not match:
        return None
    defaults = [1970, 1, 1, 0, 0, 0]
    parts = [int(part) if part else defaults[index] for index, part in enumerate(match.groups())]
    try:
        return datetime(parts[0], parts[1], parts[2], parts[3], parts[4], parts[5])
    except ValueError:
        return None


def _severity_rank(severity: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(severity, 0)


def make_signal(
    name: str,
    severity: str,
    summary: str,
    description: str,
    evidence: list[str] | None = None,
    confidence: float = 0.75,
    recovered_version_available: bool = False,
) -> dict[str, Any]:
    signal_id = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "signal"
    return {
        "id": signal_id,
        "name": name,
        "severity": severity,
        "summary": summary,
        "description": description,
        "evidence": evidence or [],
        "confidence": max(0.0, min(1.0, confidence)),
        "recovered_version_available": recovered_version_available,
    }


def _extract_pdf_text(document_bytes: bytes) -> tuple[str, list[str]]:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore[no-redef]
        except ImportError:
            return _extract_pdf_text_fallback(document_bytes), ["PDF parser unavailable; used lightweight byte extraction."]

    try:
        reader = PdfReader(io.BytesIO(document_bytes))
        text = "\n".join((page.extract_text() or "").strip() for page in reader.pages)
        return text.strip(), []
    except Exception as exc:
        fallback = _extract_pdf_text_fallback(document_bytes)
        return fallback, [f"PDF parser failed; used fallback extraction: {exc}"]


def _extract_pdf_text_fallback(document_bytes: bytes) -> str:
    decoded = document_bytes.decode("latin-1", errors="ignore")
    fragments: list[str] = []
    for match in re.finditer(r"\((.*?)\)\s*Tj", decoded, flags=re.DOTALL):
        fragments.append(match.group(1))
    for match in re.finditer(r"\[(.*?)\]\s*TJ", decoded, flags=re.DOTALL):
        fragments.extend(re.findall(r"\((.*?)\)", match.group(1), flags=re.DOTALL))
    text = "\n".join(fragment.replace("\\(", "(").replace("\\)", ")") for fragment in fragments)
    return _compact_text(text, 4000)


def _read_zip_text(archive: zipfile.ZipFile, name: str) -> str:
    return archive.read(name).decode("utf-8", errors="ignore")


def _xml_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _column_index(cell_ref: str) -> int:
    letters = re.sub(r"[^A-Z]", "", cell_ref.upper())
    value = 0
    for char in letters:
        value = value * 26 + (ord(char) - ord("A") + 1)
    return max(0, value - 1)


def _row_index(cell_ref: str) -> int:
    match = re.search(r"\d+", cell_ref)
    return max(0, int(match.group(0)) - 1) if match else 0


def _extract_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(_read_zip_text(archive, "xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall(".//main:si", OOXML_NS):
        strings.append(_xml_text(item))
    return strings


def _extract_xlsx_snapshot(document_bytes: bytes) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "sheets": [],
        "shared_strings": [],
        "used_shared_string_indexes": set(),
        "unused_shared_strings": [],
        "formulas": [],
        "hidden_sheets": [],
        "external_links": [],
        "comments": [],
        "core_properties": {},
        "notes": [],
    }

    try:
        with zipfile.ZipFile(io.BytesIO(document_bytes)) as archive:
            names = archive.namelist()
            snapshot["shared_strings"] = _extract_shared_strings(archive)

            if "docProps/core.xml" in names:
                try:
                    root = ET.fromstring(_read_zip_text(archive, "docProps/core.xml"))
                    props: dict[str, str] = {}
                    for key in ("creator", "lastModifiedBy", "created", "modified"):
                        found = root.find(f".//{{*}}{key}")
                        if found is not None and found.text:
                            props[key] = found.text.strip()
                    snapshot["core_properties"] = props
                except ET.ParseError:
                    snapshot["notes"].append("Could not parse workbook core properties.")

            workbook_sheets: dict[str, dict[str, str]] = {}
            if "xl/workbook.xml" in names:
                try:
                    root = ET.fromstring(_read_zip_text(archive, "xl/workbook.xml"))
                    for sheet in root.findall(".//main:sheet", OOXML_NS):
                        rid = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id", "")
                        name = sheet.attrib.get("name", "Sheet")
                        state = sheet.attrib.get("state", "visible")
                        workbook_sheets[rid] = {"name": name, "state": state}
                        if state != "visible":
                            snapshot["hidden_sheets"].append(f"{name} ({state})")
                except ET.ParseError:
                    snapshot["notes"].append("Could not parse workbook sheet list.")

            rel_targets: dict[str, str] = {}
            rel_path = "xl/_rels/workbook.xml.rels"
            if rel_path in names:
                try:
                    root = ET.fromstring(_read_zip_text(archive, rel_path))
                    for rel in root:
                        rid = rel.attrib.get("Id", "")
                        target = rel.attrib.get("Target", "")
                        rel_targets[rid] = target
                except ET.ParseError:
                    pass

            sheet_paths = sorted(name for name in names if re.match(r"xl/worksheets/sheet\d+\.xml$", name))
            target_to_title = {
                ("xl/" + target.lstrip("/")).replace("xl/xl/", "xl/"): info["name"]
                for rid, target in rel_targets.items()
                for info in [workbook_sheets.get(rid, {})]
                if info
            }

            for index, sheet_path in enumerate(sheet_paths, start=1):
                try:
                    root = ET.fromstring(_read_zip_text(archive, sheet_path))
                except ET.ParseError:
                    continue

                title = target_to_title.get(sheet_path, f"Sheet {index}")
                cells: list[dict[str, Any]] = []
                max_row = 0
                max_col = 0
                for cell in root.findall(".//main:c", OOXML_NS):
                    ref = cell.attrib.get("r", "")
                    value_node = cell.find("main:v", OOXML_NS)
                    formula_node = cell.find("main:f", OOXML_NS)
                    inline_node = cell.find("main:is", OOXML_NS)
                    raw_value = value_node.text if value_node is not None and value_node.text is not None else ""
                    cell_type = cell.attrib.get("t", "")
                    value = raw_value

                    if cell_type == "s" and raw_value.isdigit():
                        shared_index = int(raw_value)
                        snapshot["used_shared_string_indexes"].add(shared_index)
                        if shared_index < len(snapshot["shared_strings"]):
                            value = snapshot["shared_strings"][shared_index]
                    elif cell_type == "inlineStr":
                        value = _xml_text(inline_node)

                    formula = formula_node.text.strip() if formula_node is not None and formula_node.text else ""
                    if formula:
                        snapshot["formulas"].append(
                            {
                                "sheet": title,
                                "cell": ref,
                                "formula": formula,
                                "cached_value": value,
                            }
                        )
                    if value or formula:
                        cells.append({"ref": ref, "value": value, "formula": formula})
                        max_row = max(max_row, _row_index(ref))
                        max_col = max(max_col, _column_index(ref))

                grid_rows = min(max_row + 1, 30)
                grid_cols = min(max_col + 1, 12)
                grid = [["" for _ in range(grid_cols)] for _ in range(grid_rows)]
                for cell in cells:
                    row = _row_index(cell["ref"])
                    col = _column_index(cell["ref"])
                    if row < grid_rows and col < grid_cols:
                        grid[row][col] = cell["formula"] and f"={cell['formula']}" or str(cell["value"])

                snapshot["sheets"].append(
                    {
                        "name": title,
                        "cells": cells[:250],
                        "preview_grid": grid,
                    }
                )

            snapshot["external_links"] = [name for name in names if name.startswith("xl/externalLinks/")]
            snapshot["comments"] = [
                name
                for name in names
                if name.startswith("xl/comments") or "threadedComments" in name
            ]

            used = snapshot["used_shared_string_indexes"]
            shared = snapshot["shared_strings"]
            snapshot["unused_shared_strings"] = [
                text
                for index, text in enumerate(shared)
                if index not in used and len(_compact_text(text, 120)) >= 4
            ][:60]
    except zipfile.BadZipFile:
        snapshot["notes"].append("Workbook container is not a readable XLSX/OOXML zip package.")
    except Exception as exc:
        snapshot["notes"].append(f"Workbook extraction failed: {exc}")

    snapshot["used_shared_string_indexes"] = sorted(snapshot["used_shared_string_indexes"])
    return snapshot


def extract_document_text(document_bytes: bytes, file_name: str, content_type: str = "") -> dict[str, Any]:
    file_type = detect_file_type(file_name, content_type, document_bytes)
    notes: list[str] = []

    if file_type == "pdf":
        text, pdf_notes = _extract_pdf_text(document_bytes)
        return {
            "text": text,
            "confidence_score": 100.0 if text else 0.0,
            "source": "local_pdf_parser",
            "notes": pdf_notes,
        }

    if file_type == "word":
        if document_bytes.startswith(OLE_MAGIC):
            strings = [_compact_text(s.decode("latin-1", errors="ignore"), 120) for s in re.findall(rb"[\x20-\x7e]{4,}", document_bytes)]
            text = "\n".join(strings[:300])
            return {
                "text": text,
                "confidence_score": 60.0 if text else 0.0,
                "source": "legacy_doc_string_scan",
                "notes": ["Legacy .doc support is limited to safe string extraction. Convert to .docx for better parsing."],
            }
        
        try:
            from docx import Document
            doc = Document(io.BytesIO(document_bytes))
            text = "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())
            return {
                "text": text,
                "confidence_score": 95.0 if text else 0.0,
                "source": "docx_parser",
                "notes": [],
            }
        except ImportError:
            return {
                "text": "",
                "confidence_score": 0.0,
                "source": "error",
                "notes": ["python-docx is not installed. Text extraction for .docx failed."],
            }
        except Exception as exc:
            return {
                "text": "",
                "confidence_score": 0.0,
                "source": "error",
                "notes": [f"Word document parsing failed: {exc}"],
            }

    if file_type == "excel":
        if document_bytes.startswith(OLE_MAGIC):
            strings = [_compact_text(s.decode("latin-1", errors="ignore"), 120) for s in re.findall(rb"[\x20-\x7e]{4,}", document_bytes)]
            text = "\n".join(strings[:300])
            return {
                "text": text,
                "confidence_score": 55.0 if text else 0.0,
                "source": "legacy_xls_string_scan",
                "notes": ["Legacy .xls support is limited to safe string extraction. Convert to .xlsx for cell-level X-ray recovery."],
            }
        snapshot = _extract_xlsx_snapshot(document_bytes)

        lines: list[str] = []
        for sheet in snapshot.get("sheets", []):
            lines.append(f"[{sheet.get('name', 'Sheet')}]")
            for row in sheet.get("preview_grid", [])[:30]:
                cleaned = [str(cell).strip() for cell in row if str(cell).strip()]
                if cleaned:
                    lines.append(" | ".join(cleaned))
        notes.extend(snapshot.get("notes", []))
        return {
            "text": "\n".join(lines),
            "confidence_score": 92.0 if lines else 20.0,
            "source": "xlsx_package_parser",
            "notes": notes,
        }

    if file_type == "image":
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            return {
                "text": "",
                "confidence_score": None,
                "source": "local_image_ocr",
                "notes": ["Image OCR unavailable: install pytesseract, Pillow, and Tesseract OCR."],
            }

        try:
            image = Image.open(io.BytesIO(document_bytes)).convert("RGB")
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        except Exception as exc:
            return {
                "text": "",
                "confidence_score": None,
                "source": "local_image_ocr",
                "notes": [f"Image OCR failed: {exc}"],
            }

        line_words: dict[tuple[int, int, int], list[str]] = {}
        confidences: list[float] = []
        rows = zip(
            ocr_data.get("text", []),
            ocr_data.get("conf", []),
            ocr_data.get("block_num", []),
            ocr_data.get("par_num", []),
            ocr_data.get("line_num", []),
        )
        for text, confidence, block_num, par_num, line_num in rows:
            cleaned = str(text).strip()
            if cleaned:
                line_words.setdefault((int(block_num), int(par_num), int(line_num)), []).append(cleaned)
            try:
                numeric_confidence = float(confidence)
            except (TypeError, ValueError):
                continue
            if numeric_confidence >= 0:
                confidences.append(numeric_confidence)

        average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        extracted_lines = [" ".join(words) for _, words in sorted(line_words.items())]
        return {
            "text": "\n".join(extracted_lines),
            "confidence_score": average_confidence,
            "source": "local_image_ocr",
            "notes": [],
        }

    if file_type == "text":
        decoded = _decode_text(document_bytes)
        lines = [_compact_text(line, 600) for line in decoded.splitlines()]
        text = "\n".join(line for line in lines if line)
        return {
            "text": text[:4000],
            "confidence_score": 100.0 if text else 0.0,
            "source": "plain_text_parser",
            "notes": [],
        }

    return {
        "text": _compact_text(_decode_text(document_bytes), 4000),
        "confidence_score": 25.0,
        "source": "generic_text_scan",
        "notes": ["File type is not fully supported; used generic text extraction."],
    }


def extract_metadata(document_bytes: bytes, file_name: str = "", content_type: str = "") -> tuple[dict[str, Any], list[str]]:
    file_type = detect_file_type(file_name, content_type, document_bytes)
    anomalies: list[str] = []
    metadata: dict[str, Any] = {"file_type": file_type, "size_bytes": len(document_bytes)}

    if file_type == "pdf":
        eof_count = document_bytes.count(PDF_EOF_MARKER)
        metadata["pdf_revision_markers"] = eof_count
        metadata["pdf_prev_pointers"] = len(re.findall(rb"/Prev\s+\d+", document_bytes))
        try:
            try:
                from pypdf import PdfReader
            except ImportError:
                from PyPDF2 import PdfReader

            reader = PdfReader(io.BytesIO(document_bytes))
            metadata["page_count"] = len(reader.pages)
            for key, value in (reader.metadata or {}).items():
                if value is not None:
                    metadata[str(key).lstrip("/")] = str(value)
        except Exception as exc:
            anomalies.append(f"PDF metadata extraction was limited: {exc}")

        producer = " ".join(
            str(metadata.get(key, "")) for key in ("Producer", "Creator", "ModDate")
        ).lower()
        suspicious_software = ("photoshop", "illustrator", "gimp", "canva", "quartz pdfcontext", "pdfcontext")
        if any(signature in producer for signature in suspicious_software):
            anomalies.append("Suspicious PDF metadata: editing software signature detected.")

        created = _parse_pdf_date(str(metadata.get("CreationDate", "")))
        modified = _parse_pdf_date(str(metadata.get("ModDate", "")))
        if created and modified and abs((modified - created).total_seconds()) > 60:
            anomalies.append("PDF creation date and modification date do not match.")
        return metadata, anomalies

    if file_type == "excel":
        if document_bytes.startswith(OLE_MAGIC):
            metadata["format"] = "Legacy Excel binary workbook"
            anomalies.append("Legacy .xls file: only limited internal recovery is available.")
            return metadata, anomalies
        snapshot = _extract_xlsx_snapshot(document_bytes)

        metadata.update(snapshot.get("core_properties", {}))
        metadata["sheet_count"] = len(snapshot.get("sheets", []))
        metadata["hidden_sheets"] = snapshot.get("hidden_sheets", [])
        metadata["formula_count"] = len(snapshot.get("formulas", []))
        metadata["unused_shared_string_count"] = len(snapshot.get("unused_shared_strings", []))
        metadata["external_link_count"] = len(snapshot.get("external_links", []))
        metadata["comment_part_count"] = len(snapshot.get("comments", []))

        if metadata["hidden_sheets"]:
            anomalies.append("Workbook contains hidden or very hidden sheets.")
        if metadata["external_link_count"]:
            anomalies.append("Workbook contains external link references.")
        if metadata["unused_shared_string_count"]:
            anomalies.append("Workbook contains unreferenced shared strings that may reveal prior cell contents.")
        return metadata, anomalies

    if file_type == "image":
        try:
            from PIL import Image
        except ImportError:
            return metadata, ["Image metadata extraction unavailable: install Pillow."]
        try:
            image = Image.open(io.BytesIO(document_bytes))
            metadata["image_format"] = image.format
            metadata["dimensions"] = f"{image.width} x {image.height}"
            exif = image.getexif()
            if exif is not None:
                for tag_id, value in exif.items():
                    if tag_id == 305:
                        metadata["Software"] = str(value)
                        if any(name in str(value).lower() for name in ("photoshop", "illustrator", "gimp", "canva")):
                            anomalies.append(f"Suspicious metadata: editing software signature detected ({value}).")
        except Exception as exc:
            anomalies.append(f"Failed to extract image metadata: {exc}")
        return metadata, anomalies

    return metadata, anomalies


def _pdf_recovered_version(document_bytes: bytes) -> dict[str, Any]:
    eof_offsets = [match.end() for match in re.finditer(re.escape(PDF_EOF_MARKER), document_bytes)]
    if len(eof_offsets) < 2:
        return {
            "available": False,
            "title": "No previous PDF revision recovered",
            "summary": "The PDF does not contain multiple end-of-file markers or incremental update pointers.",
            "method": "PDF xref scan",
            "preview_text": "",
            "sections": [],
            "changes": [],
            "confidence": 0.0,
        }

    previous_bytes = document_bytes[: eof_offsets[-2]]
    previous_text, previous_notes = _extract_pdf_text(previous_bytes)
    current_text, current_notes = _extract_pdf_text(document_bytes)

    previous_lines = [line.strip() for line in previous_text.splitlines() if line.strip()]
    current_lines = [line.strip() for line in current_text.splitlines() if line.strip()]
    diff = list(difflib.unified_diff(previous_lines, current_lines, fromfile="recovered_previous", tofile="submitted", lineterm=""))
    added = [_compact_text(line[1:], 180) for line in diff if line.startswith("+") and not line.startswith("+++")]
    removed = [_compact_text(line[1:], 180) for line in diff if line.startswith("-") and not line.startswith("---")]

    changes: list[dict[str, str]] = []
    for idx, value in enumerate(removed[:10]):
        changes.append(
            {
                "field": f"Removed text #{idx + 1}",
                "previous_value": value,
                "current_value": "Not present in submitted revision",
                "type": "removed",
            }
        )
    for idx, value in enumerate(added[:10]):
        changes.append(
            {
                "field": f"Added text #{idx + 1}",
                "previous_value": "Not present in recovered revision",
                "current_value": value,
                "type": "added",
            }
        )

    sections = [
        {
            "title": "Recovered previous revision text",
            "items": previous_lines[:20] or ["Previous revision bytes were recovered, but text extraction found no readable text."],
        }
    ]
    if previous_notes or current_notes:
        sections.append({"title": "Parser notes", "items": previous_notes + current_notes})

    summary = (
        f"X-ray recovered an earlier PDF body before the final incremental update. "
        f"{len(removed)} removed and {len(added)} added text line(s) were identified."
    )
    return {
        "available": True,
        "title": "Recovered previous PDF revision",
        "summary": summary,
        "method": "PDF incremental update recovery",
        "preview_text": "\n".join(previous_lines[:40]),
        "sections": sections,
        "changes": changes,
        "confidence": 0.86 if changes else 0.72,
    }


def _excel_recovered_version(document_bytes: bytes, file_name: str) -> dict[str, Any]:
    if document_bytes.startswith(OLE_MAGIC):
        return {
            "available": False,
            "title": "Legacy XLS recovery limited",
            "summary": "The uploaded .xls workbook is a binary OLE file. The backend accepts it, but full previous-version recovery requires conversion to .xlsx.",
            "method": "Legacy XLS byte scan",
            "preview_text": "",
            "sections": [],
            "changes": [],
            "confidence": 0.15,
        }

    snapshot = _extract_xlsx_snapshot(document_bytes)
    unused = [_compact_text(text, 160) for text in snapshot.get("unused_shared_strings", []) if _compact_text(text, 160)]
    formulas = snapshot.get("formulas", [])
    hidden = snapshot.get("hidden_sheets", [])

    changes: list[dict[str, str]] = []
    for idx, text in enumerate(unused[:18]):
        changes.append(
            {
                "field": f"Recovered cell text #{idx + 1}",
                "previous_value": text,
                "current_value": "No current cell reference",
                "type": "removed",
            }
        )
    for item in formulas[:8]:
        changes.append(
            {
                "field": f"{item.get('sheet')}!{item.get('cell')}",
                "previous_value": f"Formula: ={item.get('formula')}",
                "current_value": f"Cached value: {item.get('cached_value') or '(blank)'}",
                "type": "formula",
            }
        )

    sections: list[dict[str, Any]] = []
    if unused:
        sections.append({"title": "Unreferenced shared strings", "items": unused[:30]})
    if hidden:
        sections.append({"title": "Hidden workbook areas", "items": hidden})
    if formulas:
        sections.append(
            {
                "title": "Formula-bearing cells",
                "items": [
                    f"{item.get('sheet')}!{item.get('cell')} = {item.get('formula')} -> {item.get('cached_value') or '(blank)'}"
                    for item in formulas[:20]
                ],
            }
        )

    available = bool(unused)
    if available:
        summary = (
            "X-ray recovered workbook text fragments that are still present in sharedStrings.xml "
            "but no longer referenced by live cells. These fragments often expose overwritten cell values."
        )
        title = "Recovered previous workbook fragments"
        confidence = 0.8
    elif hidden or formulas:
        summary = "No deleted cell text was recovered, but the workbook contains hidden areas or formula/cached-value traces worth reviewing."
        title = "Workbook internal traces found"
        confidence = 0.45
    else:
        summary = "No previous workbook fragments were recovered from the OOXML package."
        title = "No previous workbook version recovered"
        confidence = 0.0

    return {
        "available": available,
        "title": title,
        "summary": summary,
        "method": "OOXML shared-string and workbook package scan",
        "preview_text": "\n".join(unused[:40]),
        "sections": sections,
        "changes": changes,
        "confidence": confidence,
    }


def _word_recovered_version(document_bytes: bytes, file_name: str) -> dict[str, Any]:
    """Recover previous version information from Word documents."""
    if document_bytes.startswith(OLE_MAGIC):
        return {
            "available": False,
            "title": "Legacy DOC recovery limited",
            "summary": "The uploaded .doc file is a binary OLE file. Full previous-version recovery requires conversion to .docx.",
            "method": "Legacy DOC byte scan",
            "preview_text": "",
            "sections": [],
            "changes": [],
            "confidence": 0.15,
        }

    try:
        with zipfile.ZipFile(io.BytesIO(document_bytes)) as archive:
            names = archive.namelist()
            
            # Extract revision tracking information
            changes: list[dict[str, str]] = []
            sections: list[dict[str, Any]] = []
            recovered_text: list[str] = []
            
            # Check for tracked changes in document.xml
            if "word/document.xml" in names:
                doc_xml = _read_zip_text(archive, "word/document.xml")
                root = ET.fromstring(doc_xml)
                
                # Find deleted text (w:delText or w:del)
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                deleted_elements = root.findall(".//w:del", ns) + root.findall(".//w:delText", ns)
                
                for idx, elem in enumerate(deleted_elements[:20]):
                    deleted_text = _xml_text(elem)
                    if deleted_text.strip():
                        recovered_text.append(deleted_text.strip())
                        changes.append({
                            "field": f"Deleted text #{idx + 1}",
                            "previous_value": _compact_text(deleted_text, 180),
                            "current_value": "Removed from document",
                            "type": "removed",
                        })
                
                # Find inserted text (w:ins)
                inserted_elements = root.findall(".//w:ins", ns)
                for idx, elem in enumerate(inserted_elements[:20]):
                    inserted_text = _xml_text(elem)
                    if inserted_text.strip():
                        changes.append({
                            "field": f"Inserted text #{idx + 1}",
                            "previous_value": "Not in previous version",
                            "current_value": _compact_text(inserted_text, 180),
                            "type": "added",
                        })
            
            # Check for comments
            if "word/comments.xml" in names:
                comments_xml = _read_zip_text(archive, "word/comments.xml")
                comment_root = ET.fromstring(comments_xml)
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                comment_elements = comment_root.findall(".//w:comment", ns)
                
                comment_texts = []
                for comment in comment_elements[:15]:
                    comment_text = _xml_text(comment)
                    if comment_text.strip():
                        comment_texts.append(_compact_text(comment_text, 160))
                
                if comment_texts:
                    sections.append({
                        "title": "Document comments",
                        "items": comment_texts
                    })
            
            # Check core properties for revision information
            if "docProps/core.xml" in names:
                try:
                    core_xml = _read_zip_text(archive, "docProps/core.xml")
                    core_root = ET.fromstring(core_xml)
                    props_items = []
                    
                    for key in ("creator", "lastModifiedBy", "created", "modified", "revision"):
                        found = core_root.find(f".//{{{CORE_NS.get('cp', '')}|{CORE_NS.get('dc', '')}|{CORE_NS.get('dcterms', '')}}}{key}")
                        if found is None:
                            found = core_root.find(f".//{{*}}{key}")
                        if found is not None and found.text:
                            props_items.append(f"{key}: {found.text.strip()}")
                    
                    if props_items:
                        sections.append({
                            "title": "Document properties",
                            "items": props_items
                        })
                except ET.ParseError:
                    pass
            
            # Build result
            available = bool(changes)
            if available:
                if recovered_text:
                    sections.insert(0, {
                        "title": "Recovered deleted text",
                        "items": recovered_text[:30]
                    })
                summary = (
                    f"X-ray recovered tracked changes from the Word document. "
                    f"Found {len([c for c in changes if c['type'] == 'removed'])} deleted and "
                    f"{len([c for c in changes if c['type'] == 'added'])} inserted text fragments."
                )
                title = "Recovered previous Word document version"
                confidence = 0.82
            else:
                summary = "No tracked changes or deleted text were recovered from the Word document."
                title = "No previous Word version recovered"
                confidence = 0.0
            
            return {
                "available": available,
                "title": title,
                "summary": summary,
                "method": "OOXML revision tracking scan",
                "preview_text": "\n".join(recovered_text[:40]),
                "sections": sections,
                "changes": changes,
                "confidence": confidence,
            }
    
    except zipfile.BadZipFile:
        return {
            "available": False,
            "title": "Invalid Word document",
            "summary": "The document is not a valid OOXML package.",
            "method": "X-ray revision scan",
            "preview_text": "",
            "sections": [],
            "changes": [],
            "confidence": 0.0,
        }
    except Exception as exc:
        return {
            "available": False,
            "title": "Word recovery failed",
            "summary": f"Failed to recover previous version: {exc}",
            "method": "X-ray revision scan",
            "preview_text": "",
            "sections": [],
            "changes": [],
            "confidence": 0.0,
        }


def recover_previous_version(document_bytes: bytes, file_name: str, content_type: str = "") -> dict[str, Any]:
    file_type = detect_file_type(file_name, content_type, document_bytes)
    if file_type == "pdf":
        return _pdf_recovered_version(document_bytes)
    if file_type == "excel":
        return _excel_recovered_version(document_bytes, file_name)
    if file_type == "word":
        return _word_recovered_version(document_bytes, file_name)
    return {
        "available": False,
        "title": "No previous version recovered",
        "summary": "This file type does not usually retain recoverable document revisions in the uploaded bytes.",
        "method": "X-ray revision scan",
        "preview_text": "",
        "sections": [],
        "changes": [],
        "confidence": 0.0,
    }


def _normalise_signal(signal: dict[str, Any]) -> dict[str, Any]:
    name = str(signal.get("name") or signal.get("type") or "Forensic Signal")
    severity = str(signal.get("severity") or "low").lower()
    if severity not in {"high", "medium", "low"}:
        severity = "low"
    evidence = signal.get("evidence") or []
    if not isinstance(evidence, list):
        evidence = [str(evidence)]
    return {
        "id": str(signal.get("id") or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "signal"),
        "name": name,
        "severity": severity,
        "summary": str(signal.get("summary") or signal.get("description") or name),
        "description": str(signal.get("description") or signal.get("summary") or name),
        "evidence": [str(item) for item in evidence if str(item).strip()],
        "confidence": max(0.0, min(1.0, float(signal.get("confidence", 0.7)))),
        "recovered_version_available": bool(signal.get("recovered_version_available", False)),
    }


def _signal_from_metadata_anomaly(anomaly: str) -> dict[str, Any]:
    lowered = anomaly.lower()
    if "software" in lowered:
        name = "Editing Software Detected"
        severity = "high"
        summary = "Editing software was detected on the following pages"
        description = "Document metadata shows traces of PDF editing software."
    elif "date" in lowered:
        name = "Suspicious Date Timeline"
        severity = "medium"
        summary = "Document dates are inconsistent with a normal timeline"
        description = "Creation and modification dates suggest the document was backdated or altered."
    else:
        name = "Hidden Metadata Anomaly"
        severity = "low"
        summary = "An unusual entry was found in the document's hidden metadata"
        description = "The internal metadata contains unexpected values."
    
    # Format evidence for table rendering in frontend
    evidence_str = str(anomaly)
    if "software" in lowered:
        evidence = ["table:Page|Edited With", f"1|{evidence_str}"]
    else:
        evidence = [evidence_str]

    return make_signal(name, severity, summary, description, evidence, 0.68)


def _signal_from_validation_anomaly(anomaly: str) -> dict[str, Any]:
    lowered = anomaly.lower()
    if "rounding" in lowered or "rounded" in lowered:
        return make_signal("Suspiciously Rounded Figures", "high", "Multiple financial amounts are rounded to whole numbers", "Financial statements usually contain precise cents. Rounding suggests manual typing.", [anomaly], 0.82)
    if "repeated identical deposit" in lowered:
        return make_signal("Repeated Identical Deposits", "high", "The same deposit amount appears multiple times", "This pattern is common when transactions are copied and pasted.", [anomaly], 0.86)
    if "balance inconsistency" in lowered or "does not match" in lowered:
        return make_signal("Balance Mismatch", "high", "The financial totals do not add up correctly", "Starting balance plus activity does not equal the ending balance.", ["table:Discrepancy|Details", f"Math Error|{anomaly}"], 0.88)
    if "suspicious activity pattern" in lowered or "missing standard expenses" in lowered:
        return make_signal("Missing Expected Transactions", "medium", "Missing common transaction categories typically seen in real accounts", "Lack of everyday expenses suggests selective editing.", [anomaly], 0.72)
    if "backdated transactions" in lowered or "weekend" in lowered:
        return make_signal("Unusual Transaction Dates", "medium", "Transactions appear on abnormal dates", "Transactions processed on weekends or holidays indicate manual data entry.", [anomaly], 0.7)
    if "vague deposit descriptions" in lowered:
        return make_signal("Vague Deposit Descriptions", "low", "Deposits lack specific source descriptions", "Legitimate deposits usually have detailed references.", [anomaly], 0.62)
    if "net pay (" in lowered or "exceeds gross" in lowered:
        return make_signal("Payslip Calculation Error", "high", "Net pay is higher than gross pay", "Net pay must be lower than gross pay. This proves the numbers were altered.", [anomaly], 0.9)
    if "deductions:" in lowered:
        return make_signal("Abnormal Tax Deductions", "medium", "Tax amounts are outside normal ranges", "The deductions do not match standard tax rates.", [anomaly], 0.7)
    if "missing mandatory payslip fields" in lowered:
        return make_signal("Incomplete Payslip", "high", "Missing legally required fields", "Missing employer details or tax numbers suggests a fabricated document.", [anomaly], 0.84)
    if "inconsistent account" in lowered or "inconsistent sort" in lowered:
        return make_signal("Account Number Edits", "high", "Account Number was modified as follows", "Identifiers are inconsistent across different pages.", ["table:Location|Account Details", f"Mismatch|{anomaly}"], 0.86)
    return make_signal("Document Validation Finding", "medium", "An inconsistency was found during validation", "The document failed one or more standard validation checks.", [anomaly], 0.68)


def _signal_from_pdf_indicator(indicator: dict[str, Any]) -> dict[str, Any]:
    indicator_type = str(indicator.get("type") or "pdf_indicator")
    raw_description = str(indicator.get("description") or indicator_type.replace("_", " "))
    evidence_list = indicator.get("evidence") or [raw_description]
    if not isinstance(evidence_list, list):
        evidence_list = [str(evidence_list)]

    if indicator_type == "editing_software":
        name = "Editing Software Detected"
        summary = "Editing Software was detected on the following pages"
        description = "The PDF file structure contains traces of editing software."
        evidence = ["table:Page|Edited With"]
        for ev in evidence_list:
            evidence.append(f"1|{ev}")
    elif indicator_type == "font_inconsistency":
        name = "Font Inconsistency Detected"
        summary = "Different fonts or sizes were found within uniform text"
        description = "This mismatch indicates specific text fields were modified."
        evidence = ["table:Page|Font Anomaly"]
        for ev in evidence_list:
            evidence.append(f"1|{ev}")
    elif indicator_type == "text_overlay":
        name = "Text Overlay Detected"
        summary = "Text layers are stacked on top of each other"
        description = "Suggests new values were pasted over the original content."
        evidence = evidence_list
    elif indicator_type == "incremental_updates":
        name = "Multiple Edit Revisions"
        summary = "This PDF has been saved multiple times with changes"
        description = "Multiple rounds of editing on a final document is suspicious."
        evidence = evidence_list
    elif indicator_type == "poor_text_quality":
        name = "Low Text Quality"
        summary = "The text appears to be from a scan or low-quality source"
        description = "Often indicates the document was physically altered and scanned."
        evidence = evidence_list
    elif indicator_type == "missing_financial_data":
        name = "Sparse Financial Content"
        summary = "Contains fewer financial data points than expected"
        description = "Indicates the document is fabricated with minimal detail."
        evidence = evidence_list
    else:
        name = indicator_type.replace("_", " ").title()
        summary = raw_description
        description = raw_description
        evidence = evidence_list

    return make_signal(
        name,
        str(indicator.get("severity") or "medium").lower(),
        summary,
        description,
        evidence,
        0.78 if indicator.get("severity") == "high" else 0.64,
    )


def _signal_from_image_indicator(indicator: dict[str, Any]) -> dict[str, Any]:
    indicator_type = str(indicator.get("type") or "image_indicator")
    raw_description = str(indicator.get("description") or indicator_type.replace("_", " "))
    cv_confidence = float(indicator.get("confidence", 0.0))

    if indicator_type == "compression_artifacts":
        name = "Compression Artifacts Detected"
        summary = "Uneven JPEG compression patterns indicate parts of this image were edited"
        description = (
            "Different regions of this image show different levels of JPEG compression quality. "
            "When part of an image is edited and re-saved, the edited area gets compressed differently "
            "from the untouched regions. Our analysis detected these inconsistencies, which suggest "
            "that specific areas of the document image were modified."
        )
    elif indicator_type == "cloning_detected":
        name = "Copy-Paste Pattern Found"
        summary = "Duplicate pixel patterns were found, suggesting content was copied within the image"
        description = (
            "Computer vision analysis found regions of this image that are pixel-level duplicates of "
            "other regions. This 'copy-paste' pattern is a classic sign of image manipulation—areas "
            "of the document may have been duplicated to cover up original content or to replicate "
            "transaction entries."
        )
    elif indicator_type == "noise_inconsistency":
        name = "Image Noise Inconsistency"
        summary = "Some areas of this image have different noise patterns than the rest"
        description = (
            "Every camera or scanner produces a consistent noise pattern across the entire image. "
            "When parts of the image are edited or replaced, those areas have a different noise profile. "
            "Our analysis detected noise inconsistencies that suggest portions of this document were "
            "digitally altered."
        )
    elif indicator_type == "text_misalignment":
        name = "Text Alignment Issues"
        summary = "Text in this document is not properly aligned, suggesting manual insertion"
        description = (
            "The text in this image shows alignment inconsistencies—characters or lines are slightly "
            "tilted, shifted, or spaced differently compared to the rest of the document. This happens "
            "when text is manually added or replaced using image editing software rather than being "
            "part of the original printed or generated document."
        )
    elif indicator_type == "resolution_inconsistency":
        name = "Resolution Mismatch"
        summary = "Different parts of this image have different resolutions or sharpness levels"
        description = (
            "The image contains regions with noticeably different resolution or sharpness. This occurs "
            "when content from a different source is pasted into the document image, or when specific "
            "areas are enlarged, sharpened, or blurred to hide edits."
        )
    elif indicator_type == "color_anomalies":
        name = "Color Anomaly Detected"
        summary = "Unusual color patterns were found that suggest digital manipulation"
        description = (
            "The color distribution in parts of this image does not match the rest of the document. "
            "When content is edited, the replacement often has slightly different brightness, contrast, "
            "or color temperature. These subtle differences are not visible to the naked eye but are "
            "detectable by computer vision analysis."
        )
    else:
        name = indicator_type.replace("_", " ").title()
        summary = raw_description
        description = raw_description

    evidence = [
        raw_description,
        f"Computer-vision confidence: {cv_confidence:.0%}",
    ]
    return make_signal(
        name,
        str(indicator.get("severity") or "medium").lower(),
        summary,
        description,
        evidence,
        cv_confidence if cv_confidence > 0 else 0.65,
    )


def _dedupe_signals(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for raw_signal in sorted((_normalise_signal(signal) for signal in signals), key=lambda item: _severity_rank(item["severity"]), reverse=True):
        key = f"{raw_signal['name']}::{raw_signal['summary']}"
        if key in deduped:
            existing = deduped[key]
            existing["confidence"] = max(float(existing.get("confidence", 0.0)), float(raw_signal.get("confidence", 0.0)))
            existing_evidence = list(existing.get("evidence", []))
            for item in raw_signal.get("evidence", []):
                if item not in existing_evidence:
                    existing_evidence.append(item)
            existing["evidence"] = existing_evidence
        else:
            deduped[key] = raw_signal
    return list(deduped.values())


def _build_analysis_narrative(
    *,
    file_name: str,
    risk_score: float,
    signals: list[dict[str, Any]],
    recovered_version: dict[str, Any],
    validation_status: str,
    extracted_text: str,
) -> dict[str, str]:
    high = sum(1 for signal in signals if signal.get("severity") == "high")
    medium = sum(1 for signal in signals if signal.get("severity") == "medium")
    low = sum(1 for signal in signals if signal.get("severity") == "low")

    if signals:
        top_signal = signals[0]
        summary = (
            f"{file_name} was analyzed with local forensic checks. "
            f"The engine found {len(signals)} evidence-backed signal(s): {high} high, {medium} medium, and {low} low severity. "
            f"Top finding: {top_signal.get('summary')}."
        )
        likely_alteration = top_signal.get("description", "Review the listed evidence for the most likely alteration path.")
    else:
        summary = (
            f"{file_name} was analyzed with local forensic checks. "
            "No fraud indicators were detected in the available metadata, extracted text, or file structure."
        )
        likely_alteration = "No specific alteration was detected from the submitted bytes."

    if recovered_version.get("available"):
        likely_alteration = f"{likely_alteration} X-ray recovery also found prior-version evidence: {recovered_version.get('summary')}"

    if high or risk_score >= 70:
        recommended_action = "reject or escalate for fraud review before accepting the document"
    elif medium or risk_score >= 25:
        recommended_action = "manual review required before a final decision"
    else:
        recommended_action = "accept only after normal business verification"

    limitations = (
        f"{validation_status} Analysis is based on uploaded file bytes, metadata, extracted text length "
        f"{len(extracted_text)}, and available local parsers; it does not verify the issuer directly."
    )
    return {
        "ai_summary": summary,
        "ai_alteration": likely_alteration,
        "ai_recommendation": recommended_action,
        "ai_limitations": limitations,
    }


def analyze_forensic_signals(
    document_bytes: bytes,
    file_name: str,
    content_type: str,
    metadata: dict[str, Any],
    metadata_anomalies: list[str],
    validation_anomalies: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """
    Analyze document for fraud using deterministic local evidence.

    AI can be layered on by callers, but this backend result never depends on a
    canned response or a fixed fallback score. Every signal below is derived
    from metadata, extracted text, file-structure recovery, or computer-vision
    checks that ran against the uploaded bytes.
    """
    file_type = detect_file_type(file_name, content_type, document_bytes)
    text_result = extract_document_text(document_bytes, file_name, content_type)
    extracted_text = text_result.get("text", "")
    recovered_version = recover_previous_version(document_bytes, file_name, content_type)

    signals: list[dict[str, Any]] = []
    advanced_analysis: dict[str, Any] = {}

    if recovered_version.get("available"):
        signals.append(
            make_signal(
                "X-ray Recovery",
                "high",
                "Previous version evidence was recovered",
                recovered_version.get("summary", "A prior document state was recovered from internal file history."),
                [
                    f"Method: {recovered_version.get('method')}",
                    f"Changes recovered: {len(recovered_version.get('changes', []))}",
                ],
                float(recovered_version.get("confidence", 0.75)),
                recovered_version_available=True,
            )
        )

    for anomaly in metadata_anomalies:
        signals.append(_signal_from_metadata_anomaly(anomaly))

    for anomaly in validation_anomalies:
        signals.append(_signal_from_validation_anomaly(anomaly))

    if file_type == "pdf":
        try:
            from advanced_pdf_analysis import get_comprehensive_pdf_analysis

            pdf_analysis = get_comprehensive_pdf_analysis(document_bytes)
            advanced_analysis["pdf"] = {
                "available": bool(pdf_analysis.get("pymupdf_analysis", {}).get("available") or pdf_analysis.get("pdfminer_analysis", {}).get("available")),
                "risk_score": pdf_analysis.get("risk_score", 0),
                "total_indicators": pdf_analysis.get("total_indicators", 0),
            }
            for indicator in pdf_analysis.get("fraud_indicators", []):
                signals.append(_signal_from_pdf_indicator(indicator))
        except Exception as exc:
            advanced_analysis["pdf"] = {"available": False, "error": str(exc)}

    if file_type == "image":
        try:
            from advanced_image_analysis import analyze_image_with_opencv

            image_analysis = analyze_image_with_opencv(document_bytes)
            advanced_analysis["image"] = {
                "available": image_analysis.get("available", False),
                "risk_score": image_analysis.get("risk_score", 0),
                "total_indicators": image_analysis.get("total_indicators", 0),
                "dimensions": image_analysis.get("image_dimensions"),
            }
            for indicator in image_analysis.get("fraud_indicators", []):
                signals.append(_signal_from_image_indicator(indicator))
        except Exception as exc:
            advanced_analysis["image"] = {"available": False, "error": str(exc)}

    if not extracted_text.strip():
        notes = text_result.get("notes") or []
        evidence = [str(note) for note in notes] or ["No machine-readable text was extracted from the uploaded document."]
        signals.append(
            make_signal(
                "Text Extraction Limited",
                "low",
                "No machine-readable text was extracted",
                "The backend could not inspect document wording or numeric fields, so the report relies on metadata and file-structure checks.",
                evidence,
                0.38,
            )
        )

    try:
        from real_estate_fraud_signals import detect_real_estate_fraud_signals

        real_estate_signals = detect_real_estate_fraud_signals(
            document_bytes,
            extracted_text,
            metadata,
            file_type
        )
        signals.extend(real_estate_signals)
        advanced_analysis["real_estate_signal_count"] = len(real_estate_signals)
    except Exception as e:
        advanced_analysis["real_estate_error"] = str(e)

    # RAG Engine Integration
    try:
        from rag_engine import analyze_with_rag
        rag_signals = analyze_with_rag(extracted_text)
        signals.extend(rag_signals)
        advanced_analysis["rag_signal_count"] = len(rag_signals)
    except Exception as e:
        advanced_analysis["rag_error"] = str(e)

    deduped = _dedupe_signals(signals)

    highlight_coordinates = []
    try:
        from text_coordinate_extractor import get_smart_highlight_regions
        highlight_coordinates = get_smart_highlight_regions(
            document_bytes,
            file_type,
            deduped,
            extracted_text
        )
        print(f"[HIGHLIGHTING] Extracted {len(highlight_coordinates)} highlight regions for {file_type}")
        if highlight_coordinates:
            print(f"[HIGHLIGHTING] Sample region: {highlight_coordinates[0]}")
    except Exception as e:
        print(f"[HIGHLIGHTING] Text coordinate extraction failed: {e}")
        import traceback
        traceback.print_exc()

    risk_score = calculate_risk_score(deduped)
    narrative = _build_analysis_narrative(
        file_name=file_name,
        risk_score=risk_score,
        signals=deduped,
        recovered_version=recovered_version,
        validation_status="; ".join(str(note) for note in text_result.get("notes", [])[:2]) or "Local validation completed.",
        extracted_text=extracted_text,
    )

    feature_summary = {
        "file_type": file_type,
        "signal_count": len(deduped),
        "total_signals": len(deduped),
        "high_severity": sum(1 for item in deduped if item["severity"] == "high"),
        "medium_severity": sum(1 for item in deduped if item["severity"] == "medium"),
        "low_severity": sum(1 for item in deduped if item["severity"] == "low"),
        "risk_score": risk_score,
        "trust_score": round(max(0.0, 100.0 - risk_score), 1),
        "analysis_method": "deterministic_local_forensics",
        "metadata_anomaly_count": len(metadata_anomalies),
        "validation_anomaly_count": len(validation_anomalies),
        "text_source": text_result.get("source"),
        "text_confidence": text_result.get("confidence_score"),
        "text_length": len(extracted_text),
        "recovered_version_available": recovered_version.get("available", False),
        "recovered_changes_count": len(recovered_version.get("changes", [])),
        "advanced_analysis": advanced_analysis,
        "highlight_coordinates": highlight_coordinates,
        **narrative,
    }
    return deduped, recovered_version, feature_summary


def calculate_risk_score(signals: list[dict[str, Any]]) -> float:
    if not signals:
        return 0.0
    weights = {"high": 28.0, "medium": 15.0, "low": 7.0}
    score = 0.0
    for signal in signals:
        confidence = float(signal.get("confidence", 0.7))
        score += weights.get(signal.get("severity", "low"), 7.0) * (0.65 + confidence * 0.35)
    return round(min(100.0, score), 1)


def generate_openrouter_explanation(
    *,
    file_name: str,
    risk_score: float,
    trust_score: float,
    signals: list[dict[str, Any]],
    recovered_version: dict[str, Any],
    validation_status: str,
    extracted_text: str,
    api_key: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, str]:
    """
    Generate a deterministic explanation from local forensic signals.
    """
    narrative = _build_analysis_narrative(
        file_name=file_name,
        risk_score=risk_score,
        signals=signals,
        recovered_version=recovered_version,
        validation_status=validation_status,
        extracted_text=extracted_text,
    )
    return {
        "summary": narrative["ai_summary"],
        "likely_alteration": narrative["ai_alteration"],
        "recommended_action": narrative["ai_recommendation"],
        "limitations": narrative["ai_limitations"],
        "generated_by": "deterministic_local_forensics",
    }




def enrich_signal_descriptions(
    signals: list[dict[str, Any]],
    *,
    file_name: str,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """
    Descriptions are generated by the local signal builders.
    """
    return signals

