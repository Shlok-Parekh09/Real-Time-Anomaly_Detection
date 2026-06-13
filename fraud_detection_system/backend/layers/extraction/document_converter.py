"""
Document Converter Module
Converts Word documents to PDF for consistent X-ray analysis
"""

from __future__ import annotations

import io
import os
import platform
import subprocess
import tempfile
from pathlib import Path


def convert_word_to_pdf(word_bytes: bytes, file_name: str) -> bytes:
    """
    Convert Word document to PDF.
    
    Args:
        word_bytes: Raw bytes of the Word document
        file_name: Original filename
        
    Returns:
        PDF bytes
        
    Raises:
        RuntimeError: If conversion fails
    """
    system = platform.system()
    
    # Try different conversion methods based on platform
    if system == "Windows":
        return _convert_word_to_pdf_windows(word_bytes, file_name)
    elif system == "Linux":
        return _convert_word_to_pdf_linux(word_bytes, file_name)
    elif system == "Darwin":  # macOS
        return _convert_word_to_pdf_macos(word_bytes, file_name)
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def _convert_word_to_pdf_windows(word_bytes: bytes, file_name: str) -> bytes:
    """Convert Word to PDF on Windows using docx2pdf or comtypes."""
    try:
        # Try docx2pdf first (simpler, works with LibreOffice)
        from docx2pdf import convert
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write Word file
            word_path = temp_path / file_name
            word_path.write_bytes(word_bytes)
            
            # Convert to PDF
            pdf_path = temp_path / f"{word_path.stem}.pdf"
            convert(str(word_path), str(pdf_path))
            
            # Read PDF bytes
            if pdf_path.exists():
                return pdf_path.read_bytes()
            else:
                raise RuntimeError("PDF file was not created")
                
    except ImportError:
        # Fallback to comtypes (requires MS Word)
        try:
            import comtypes.client
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Write Word file
                word_path = temp_path / file_name
                word_path.write_bytes(word_bytes)
                
                # Convert using Word COM
                pdf_path = temp_path / f"{word_path.stem}.pdf"
                
                word = comtypes.client.CreateObject('Word.Application')
                word.Visible = False
                
                try:
                    doc = word.Documents.Open(str(word_path.absolute()))
                    doc.SaveAs(str(pdf_path.absolute()), FileFormat=17)  # 17 = PDF
                    doc.Close()
                finally:
                    word.Quit()
                
                if pdf_path.exists():
                    return pdf_path.read_bytes()
                else:
                    raise RuntimeError("PDF file was not created")
                    
        except Exception as e:
            raise RuntimeError(f"Word to PDF conversion failed: {e}")


def _convert_word_to_pdf_linux(word_bytes: bytes, file_name: str) -> bytes:
    """Convert Word to PDF on Linux using LibreOffice."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write Word file
            word_path = temp_path / file_name
            word_path.write_bytes(word_bytes)
            
            # Convert using LibreOffice
            result = subprocess.run(
                [
                    'libreoffice',
                    '--headless',
                    '--convert-to',
                    'pdf',
                    '--outdir',
                    str(temp_path),
                    str(word_path)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")
            
            # Find the generated PDF
            pdf_path = temp_path / f"{word_path.stem}.pdf"
            if pdf_path.exists():
                return pdf_path.read_bytes()
            else:
                raise RuntimeError("PDF file was not created")
                
    except FileNotFoundError:
        raise RuntimeError("LibreOffice is not installed. Install with: sudo apt-get install libreoffice")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Word to PDF conversion timed out")
    except Exception as e:
        raise RuntimeError(f"Word to PDF conversion failed: {e}")


def _convert_word_to_pdf_macos(word_bytes: bytes, file_name: str) -> bytes:
    """Convert Word to PDF on macOS using LibreOffice or textutil."""
    # Try LibreOffice first
    try:
        return _convert_word_to_pdf_linux(word_bytes, file_name)
    except RuntimeError:
        pass
    
    # Fallback to textutil (built-in macOS tool, but limited)
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write Word file
            word_path = temp_path / file_name
            word_path.write_bytes(word_bytes)
            
            # Convert using textutil
            pdf_path = temp_path / f"{word_path.stem}.pdf"
            result = subprocess.run(
                [
                    'textutil',
                    '-convert',
                    'pdf',
                    str(word_path),
                    '-output',
                    str(pdf_path)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"textutil conversion failed: {result.stderr}")
            
            if pdf_path.exists():
                return pdf_path.read_bytes()
            else:
                raise RuntimeError("PDF file was not created")
                
    except Exception as e:
        raise RuntimeError(f"Word to PDF conversion failed: {e}")


def is_word_document(file_name: str, file_bytes: bytes) -> bool:
    """Check if file is a Word document."""
    lower_name = file_name.lower()
    
    # Check extension
    if lower_name.endswith(('.doc', '.docx')):
        return True
    
    # Check magic bytes
    if file_bytes.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):  # OLE (old .doc)
        return True
    
    if file_bytes.startswith(b'PK\x03\x04'):  # ZIP (modern .docx)
        # Check if it contains word/document.xml
        try:
            import zipfile
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                return 'word/document.xml' in zf.namelist()
        except:
            pass
    
    return False
