import io
from typing import Any, Dict, List
from docx import Document
from vocabulary_service import export_keywords_to_excel


def get_output_filename(original_name: str, ext: str) -> str:
    base = original_name.rsplit(".", 1)[0]
    return f"{base}_Bilingual.{ext}"


def export_quality_report_docx(checks: List[Dict[str, str]], lesson_topic: str) -> bytes:
    """Xuất báo cáo kiểm tra chất lượng tích hợp ra file Word (.docx)."""
    doc = Document()
    doc.add_heading(f"BÁO CÁO KIỂM TRA CHẤT LƯỢNG TÍCH HỢP SONG NGỮ", level=1)
    doc.add_paragraph(f"Chủ đề bài học: {lesson_topic}")

    tbl = doc.add_table(rows=1, cols=3)
    tbl.style = "Table Grid"
    tbl.rows[0].cells[0].text = "Tiêu chí"
    tbl.rows[0].cells[1].text = "Trạng thái"
    tbl.rows[0].cells[2].text = "Chi tiết"

    for c in checks:
        row = tbl.add_row().cells
        row[0].text = c["Tiêu chí"]
        row[1].text = c["Trạng thái"]
        row[2].text = c["Chi tiết"]

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()