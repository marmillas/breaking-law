import pytest
from breaking_law.documents.parsing import DocumentParser


PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
    b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 44 >>\nstream\n"
    b"BT /F1 12 Tf 100 700 Td (Hello PDF) Tj ET\n"
    b"endstream\nendobj\n"
    b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    b"xref\n0 6\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"0000000266 00000 n \n"
    b"0000000360 00000 n \n"
    b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
    b"startxref\n438\n%%EOF\n"
)


def test_parse_txt(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Hello world", encoding="utf-8")
    parser = DocumentParser()
    text = parser.parse_txt(str(file_path))
    assert text == "Hello world"


def test_parse_pdf(tmp_path):
    file_path = tmp_path / "sample.pdf"
    file_path.write_bytes(PDF_BYTES)
    parser = DocumentParser()
    text = parser.parse_pdf(str(file_path))
    assert "Hello PDF" in text


def test_ocr_disabled_raises():
    parser = DocumentParser(ocr_enabled=False)
    with pytest.raises(Exception) as exc_info:
        parser.parse_with_ocr("some_file.pdf")
    assert "OCR is disabled" in str(exc_info.value)
