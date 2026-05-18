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
    if lower_name.endswith(".xls") or document_bytes.startswith(OLE_MAGIC):
        return "excel"
    if lower_type.startswith("image/") or lower_name.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")):
        return "image"
    if document_bytes.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(document_bytes)) as archive:
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
            from pypdf import PdfReader

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


def recover_previous_version(document_bytes: bytes, file_name: str, content_type: str = "") -> dict[str, Any]:
    file_type = detect_file_type(file_name, content_type, document_bytes)
    if file_type == "pdf":
        return _pdf_recovered_version(document_bytes)
    if file_type == "excel":
        return _excel_recovered_version(document_bytes, file_name)
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


def _detect_pdf_masking(document_bytes: bytes) -> list[dict[str, Any]]:
    decoded = document_bytes.decode("latin-1", errors="ignore")
    signals: list[dict[str, Any]] = []
    redaction_hits = len(re.findall(r"/Subtype\s*/Redact|/Redact|redact", decoded, flags=re.IGNORECASE))
    annotation_hits = len(re.findall(r"/Annots|\b/Annot\b", decoded))
    white_fill_hits = len(re.findall(r"\b1\s+1\s+1\s+rg\b|\b1\s+1\s+1\s+RG\b", decoded))

    if redaction_hits or white_fill_hits > 4:
        signals.append(
            make_signal(
                "Masking",
                "medium",
                f"{max(redaction_hits, white_fill_hits)} masking indicator(s)",
                "The PDF contains redaction objects or repeated white fill operations that can be used to cover original text.",
                [f"Redaction markers: {redaction_hits}", f"White fill operations: {white_fill_hits}"],
                0.68,
            )
        )
    if annotation_hits:
        signals.append(
            make_signal(
                "Annotations",
                "low",
                f"{annotation_hits} annotation marker(s)",
                "Annotations can be legitimate, but they also indicate a later interactive layer was added to the document.",
                [f"Annotation object markers: {annotation_hits}"],
                0.55,
            )
        )
    return signals


def _detect_pdf_fonts(document_bytes: bytes) -> list[dict[str, Any]]:
    decoded = document_bytes.decode("latin-1", errors="ignore")
    fonts = re.findall(r"/BaseFont\s*/([A-Za-z0-9+._-]+)", decoded)
    unique_fonts = sorted(set(fonts))
    subset_count = sum(1 for font in unique_fonts if "+" in font[:8])
    if len(unique_fonts) >= 8 or subset_count >= 4:
        return [
            make_signal(
                "Font Anomaly",
                "medium",
                "Document contains an anomalous font mix",
                "The PDF uses many font programs or subset fonts, a common side effect when pages are assembled from multiple sources.",
                [f"Unique fonts: {len(unique_fonts)}", f"Subset fonts: {subset_count}", f"Sample: {', '.join(unique_fonts[:6])}"],
                0.62,
            )
        ]
    return []


def _detect_image_copy_move(document_bytes: bytes) -> list[dict[str, Any]]:
    try:
        import cv2
        import numpy as np
    except ImportError:
        return [
            make_signal(
                "Image Engine",
                "low",
                "Copy-move check unavailable",
                "Install opencv-python-headless and numpy to enable image copy-move detection.",
                [],
                0.2,
            )
        ]

    try:
        nparr = np.frombuffer(document_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return []
        orb = cv2.ORB_create(nfeatures=1200)
        keypoints, descriptors = orb.detectAndCompute(img, None)
        if descriptors is None or len(keypoints) < 20:
            return []

        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = matcher.knnMatch(descriptors, descriptors, k=4)
        clusters: Counter[tuple[int, int]] = Counter()
        for match_list in matches:
            candidates = [match for match in match_list if match.queryIdx != match.trainIdx]
            if len(candidates) < 2:
                continue
            best, second = candidates[:2]
            if best.distance > 32 or best.distance > 0.75 * second.distance:
                continue
            point_a = keypoints[best.queryIdx].pt
            point_b = keypoints[best.trainIdx].pt
            dx = point_b[0] - point_a[0]
            dy = point_b[1] - point_a[1]
            if (dx * dx + dy * dy) ** 0.5 <= 40:
                continue
            clusters[(round(dx / 16), round(dy / 16))] += 1

        strongest = max(clusters.values(), default=0)
        threshold = max(18, int(len(keypoints) * 0.04))
        if strongest >= threshold:
            return [
                make_signal(
                    "Copy-Move",
                    "high",
                    "Repeated image region detected",
                    "Keypoints with the same displacement indicate a region may have been cloned or pasted elsewhere in the document image.",
                    [f"Matched keypoint cluster: {strongest}", f"Threshold: {threshold}"],
                    0.78,
                )
            ]
    except Exception as exc:
        return [
            make_signal(
                "Image Engine",
                "low",
                "Copy-move check failed",
                f"The image copy-move detector could not complete: {exc}",
                [],
                0.25,
            )
        ]
    return []


def _detect_xlsx_signals(document_bytes: bytes, file_name: str) -> list[dict[str, Any]]:
    if document_bytes.startswith(OLE_MAGIC):
        return []
    snapshot = _extract_xlsx_snapshot(document_bytes)
    signals: list[dict[str, Any]] = []
    hidden = snapshot.get("hidden_sheets", [])
    formulas = snapshot.get("formulas", [])
    external_links = snapshot.get("external_links", [])
    comments = snapshot.get("comments", [])

    if hidden:
        signals.append(
            make_signal(
                "Hidden Workbook Content",
                "medium",
                f"{len(hidden)} hidden sheet(s)",
                "Hidden or very hidden sheets can conceal calculations, old values, or staging data used to alter the submitted workbook.",
                hidden[:8],
                0.72,
            )
        )
    if external_links:
        signals.append(
            make_signal(
                "External Links",
                "medium",
                f"{len(external_links)} external link part(s)",
                "External workbook links can pull values from files not included in the submission.",
                external_links[:8],
                0.66,
            )
        )
    if len(formulas) >= 10:
        signals.append(
            make_signal(
                "Formula Layer",
                "low",
                f"{len(formulas)} formula cells",
                "Formula cells are not suspicious by themselves, but cached values and formulas should be reviewed for financial documents.",
                [
                    f"{item.get('sheet')}!{item.get('cell')} = {item.get('formula')}"
                    for item in formulas[:8]
                ],
                0.48,
            )
        )
    if comments:
        signals.append(
            make_signal(
                "Comments",
                "low",
                f"{len(comments)} comment part(s)",
                "Workbook comments may contain review notes or remnants from prior edits.",
                comments[:8],
                0.42,
            )
        )
    return signals


def analyze_forensic_signals(
    document_bytes: bytes,
    file_name: str,
    content_type: str,
    metadata: dict[str, Any],
    metadata_anomalies: list[str],
    validation_anomalies: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    file_type = detect_file_type(file_name, content_type, document_bytes)
    recovered_version = recover_previous_version(document_bytes, file_name, content_type)
    signals: list[dict[str, Any]] = []

    if recovered_version.get("available"):
        signals.append(
            make_signal(
                "X-ray",
                "high",
                "Previous version has been recovered",
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
        lowered = anomaly.lower()
        if "software" in lowered:
            name = "Software"
            severity = "medium"
        elif "date" in lowered:
            name = "Dates"
            severity = "low"
        else:
            name = "Metadata"
            severity = "low"
        signals.append(
            make_signal(
                name,
                severity,
                anomaly,
                "Hidden metadata does not match the expected lifecycle for a clean source document.",
                [anomaly],
                0.64,
            )
        )

    for anomaly in validation_anomalies:
        signals.append(
            make_signal(
                "Validation",
                "high",
                "Financial consistency check failed",
                anomaly,
                [anomaly],
                0.74,
            )
        )

    if file_type == "pdf":
        signals.extend(_detect_pdf_masking(document_bytes))
        signals.extend(_detect_pdf_fonts(document_bytes))
    elif file_type == "excel":
        signals.extend(_detect_xlsx_signals(document_bytes, file_name))
    elif file_type == "image":
        signals.extend(_detect_image_copy_move(document_bytes))

    deduped: dict[str, dict[str, Any]] = {}
    for signal in sorted(signals, key=lambda item: _severity_rank(item["severity"]), reverse=True):
        key = f"{signal['name']}::{signal['summary']}"
        if key not in deduped:
            deduped[key] = signal

    feature_summary = {
        "file_type": file_type,
        "signal_count": len(deduped),
        "high_severity": sum(1 for item in deduped.values() if item["severity"] == "high"),
        "medium_severity": sum(1 for item in deduped.values() if item["severity"] == "medium"),
        "low_severity": sum(1 for item in deduped.values() if item["severity"] == "low"),
    }
    return list(deduped.values()), recovered_version, feature_summary


def calculate_risk_score(signals: list[dict[str, Any]]) -> float:
    if not signals:
        return 4.0
    weights = {"high": 28.0, "medium": 15.0, "low": 7.0}
    score = 0.0
    for signal in signals:
        confidence = float(signal.get("confidence", 0.7))
        score += weights.get(signal.get("severity", "low"), 7.0) * (0.65 + confidence * 0.35)
    return round(min(100.0, score), 1)


def _local_explanation(
    file_name: str,
    risk_score: float,
    trust_score: float,
    signals: list[dict[str, Any]],
    recovered_version: dict[str, Any],
) -> dict[str, str]:
    if signals:
        lead = signals[0]
        summary = f"{file_name} scored {trust_score:.1f}/100 trust because {lead['summary'].lower()}."
    else:
        summary = f"{file_name} scored {trust_score:.1f}/100 trust with no major forensic signals."

    if recovered_version.get("available"):
        likely = recovered_version.get("summary", "The X-ray scan recovered a previous version from the file internals.")
    elif signals:
        likely = "The strongest alteration indicators are: " + "; ".join(signal["summary"] for signal in signals[:3])
    else:
        likely = "No clear alteration path was detected from the local forensic checks."

    if risk_score >= 70:
        action = "Reject or escalate to manual fraud review before accepting the document."
    elif risk_score >= 30:
        action = "Hold for underwriter review and compare against source statements or issuer records."
    else:
        action = "Accept only after standard identity and source verification."

    return {
        "summary": summary,
        "likely_alteration": likely,
        "recommended_action": action,
        "limitations": "Local fallback explanation. Set CEREBRAS_API_KEY on the backend to generate richer Cerebras narratives.",
        "generated_by": "local_fallback",
    }


def generate_cerebras_explanation(
    *,
    file_name: str,
    risk_score: float,
    trust_score: float,
    signals: list[dict[str, Any]],
    recovered_version: dict[str, Any],
    validation_status: str,
    extracted_text: str,
    api_key: str | None = None,
) -> dict[str, str]:
    fallback = _local_explanation(file_name, risk_score, trust_score, signals, recovered_version)
    resolved_api_key = (api_key or os.getenv("CEREBRAS_API_KEY", "")).strip()
    if not resolved_api_key:
        return fallback

    model = os.getenv("CEREBRAS_MODEL", "gpt-oss-120b").strip() or "gpt-oss-120b"
    prompt = {
        "file_name": file_name,
        "risk_score": risk_score,
        "trust_score": trust_score,
        "signals": signals[:8],
        "recovered_version": {
            "available": recovered_version.get("available"),
            "summary": recovered_version.get("summary"),
            "changes": recovered_version.get("changes", [])[:12],
        },
        "validation_status": validation_status,
        "text_excerpt": _compact_text(extracted_text, 1600),
    }
    body = {
        "model": model,
        "temperature": 0.2,
        "max_completion_tokens": 550,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a document fraud forensics analyst. Explain findings in concise, "
                    "non-accusatory language for a bank underwriter. Return only JSON with keys "
                    "summary, likely_alteration, recommended_action, limitations."
                ),
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=True)},
        ],
    }

    request = urllib.request.Request(
        "https://api.cerebras.ai/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {resolved_api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        parsed = json.loads(match.group(0) if match else content)
        return {
            "summary": str(parsed.get("summary") or fallback["summary"]),
            "likely_alteration": str(parsed.get("likely_alteration") or fallback["likely_alteration"]),
            "recommended_action": str(parsed.get("recommended_action") or fallback["recommended_action"]),
            "limitations": str(parsed.get("limitations") or "Generated from file-level forensic signals; verify against issuer records."),
            "generated_by": f"cerebras:{model}",
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError, json.JSONDecodeError, ValueError) as exc:
        fallback["limitations"] = f"{fallback['limitations']} Cerebras call failed: {exc}"
        return fallback
