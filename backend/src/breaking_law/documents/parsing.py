"""
Document parsing infrastructure for legal platform.

Handles extraction of text content from PDF, DOCX, and image files.
Uses pypdf for text-selectable PDFs, python-docx for Word documents,
and Tesseract OCR as a fallback for scanned PDFs and images.
"""

import io
import os
import tempfile
from typing import List, Optional

import pypdf
import docx
import pytesseract
from PIL import Image


def _pdf_pages_to_images(file_path: str) -> List[Image.Image]:
    """
    Convert PDF pages to PIL Images for OCR processing.

    Requires pdf2image and poppler to be installed.
    Raises ImportError if pdf2image is not available.
    """
    try:
        from pdf2image import convert_from_path
    except ImportError as exc:
        raise ImportError(
            "pdf2image is required for OCR on PDF files. "
            "Install it with: pip install pdf2image"
        ) from exc

    return convert_from_path(file_path, dpi=200)


class DocumentParser:
    """Handles parsing of various document formats with OCR fallback."""

    def __init__(
        self,
        ocr_enabled: bool = True,
        tesseract_path: str = "/usr/bin/tesseract",
        lang: str = "spa+eng",
    ):
        """
        Initialize the document parser.

        Args:
            ocr_enabled: Whether to enable OCR fallback for scanned documents.
            tesseract_path: Path to the Tesseract executable.
            lang: Tesseract language pack(s) to use.
        """
        self.ocr_enabled = ocr_enabled
        self.lang = lang
        if ocr_enabled:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def parse_pdf(self, file_path: str) -> str:
        """
        Parse a PDF file using pypdf for text-selectable documents.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Extracted text content.

        Raises:
            Exception: If parsing fails.
        """
        try:
            text_parts: List[str] = []
            with open(file_path, "rb") as file:
                pdf_reader = pypdf.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n".join(text_parts)
        except Exception as exc:
            raise Exception(f"Error parsing PDF: {exc}") from exc

    def parse_docx(self, file_path: str) -> str:
        """
        Parse a DOCX file using python-docx.

        Args:
            file_path: Path to the DOCX file.

        Returns:
            Extracted text content with paragraph structure preserved.

        Raises:
            Exception: If parsing fails.
        """
        try:
            document = docx.Document(file_path)
            paragraphs: List[str] = []
            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    paragraphs.append(paragraph.text)
            return "\n".join(paragraphs)
        except Exception as exc:
            raise Exception(f"Error parsing DOCX: {exc}") from exc

    def parse_txt(self, file_path: str) -> str:
        """
        Parse a plain text file.

        Args:
            file_path: Path to the text file.

        Returns:
            File contents as string.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 if UTF-8 fails
            with open(file_path, "r", encoding="latin-1") as file:
                return file.read()

    def parse_with_ocr(self, file_path: str) -> str:
        """
        Parse a document or image using OCR.

        For PDFs, converts pages to images first.
        For images, processes directly with Tesseract.

        Args:
            file_path: Path to the file.

        Returns:
            Extracted text content.

        Raises:
            Exception: If OCR processing fails.
        """
        if not self.ocr_enabled:
            raise Exception("OCR is disabled")

        try:
            if file_path.lower().endswith(".pdf"):
                images = _pdf_pages_to_images(file_path)
                text_parts: List[str] = []
                for image in images:
                    page_text = pytesseract.image_to_string(image, lang=self.lang)
                    text_parts.append(page_text)
                return "\n".join(text_parts)
            else:
                image = Image.open(file_path)
                return pytesseract.image_to_string(image, lang=self.lang)
        except Exception as exc:
            raise Exception(f"Error in OCR processing: {exc}") from exc

    def parse_with_ocr_fallback(self, file_path: str, mime_type: Optional[str] = None) -> str:
        """
        Parse document with OCR fallback for scanned PDFs and images.

        Strategy:
        1. Try format-specific parser first.
        2. If no text extracted, try OCR fallback.
        3. If OCR also fails, raise exception.

        Args:
            file_path: Path to the file.
            mime_type: Optional MIME type hint.

        Returns:
            Extracted text content.

        Raises:
            Exception: If all parsing strategies fail.
        """
        # Determine format from mime_type or extension
        lower_path = file_path.lower()
        if mime_type:
            fmt = mime_type.lower()
        elif lower_path.endswith(".pdf"):
            fmt = "application/pdf"
        elif lower_path.endswith(".docx"):
            fmt = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif lower_path.endswith(".txt"):
            fmt = "text/plain"
        else:
            fmt = "unknown"

        # Try primary parser
        text = ""
        try:
            if "pdf" in fmt:
                text = self.parse_pdf(file_path)
            elif "wordprocessingml" in fmt or "docx" in fmt:
                text = self.parse_docx(file_path)
            elif "text/plain" in fmt or lower_path.endswith(".txt"):
                text = self.parse_txt(file_path)
        except Exception:
            text = ""

        if text.strip():
            return text

        # Fallback to OCR
        if self.ocr_enabled:
            try:
                return self.parse_with_ocr(file_path)
            except Exception as exc:
                raise Exception(
                    f"Primary parser produced no text and OCR fallback failed: {exc}"
                ) from exc

        raise Exception("Primary parser produced no text and OCR is disabled")

    def process_document(
        self,
        file_path: str,
        mime_type: Optional[str] = None,
    ) -> dict:
        """
        Process a document and return structured result.

        Args:
            file_path: Path to the document file.
            mime_type: Optional MIME type hint.

        Returns:
            Dict with keys: success (bool), text (str), error (str|None).
        """
        try:
            text = self.parse_with_ocr_fallback(file_path, mime_type)
            return {"success": True, "text": text, "error": None}
        except Exception as exc:
            return {"success": False, "text": "", "error": str(exc)}
