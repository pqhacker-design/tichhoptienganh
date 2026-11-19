import io
import re
from typing import Any, Dict, List
from docx import Document
from docx.document import Document as _Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from pptx import Presentation

ACTIVITY_PATTERNS = [
    ("Khởi động", r"khởi động|mở đầu|đặt vấn đề"),
    ("Hình thành kiến thức", r"hình thành kiến thức|kiến thức mới|khám phá"),
    ("Luyện tập", r"luyện tập|thực hành"),
    ("Vận dụng", r"vận dụng|mở rộng"),
    ("Hướng dẫn về nhà", r"về nhà|dặn dò|tự học"),
]


def _detect_activity(text: str) -> str:
    lower = text.lower()
    for name, pattern in ACTIVITY_PATTERNS:
        if re.search(pattern, lower):
            return name
    return ""


def _paragraph_has_math(paragraph) -> bool:
    xml = paragraph._element.xml
    return ("oMath" in xml) or ("oMathPara" in xml)


def _paragraph_has_image(paragraph) -> bool:
    xml = paragraph._element.xml
    return ("w:drawing" in xml) or ("w:pict" in xml)


def iter_word_body_blocks(doc: _Document):
    """Duyệt tuần tự đoạn văn và bảng biểu theo ĐÚNG thứ tự xuất hiện trong file Word."""
    body = doc.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield ("paragraph", Paragraph(child, doc))
        elif isinstance(child, CT_Tbl):
            yield ("table", Table(child, doc))


def read_word_document(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Đọc giáo án Word theo đúng thứ tự tuyến tính (ordered_blocks) để phân chia nhiều bài."""
    doc = Document(io.BytesIO(file_bytes))
    ordered_blocks: List[Dict[str, Any]] = []
    detected_activities: List[str] = []
    math_count = 0
    image_count = 0
    table_count = 0
    para_count = 0

    for block_idx, (kind, obj) in enumerate(iter_word_body_blocks(doc)):
        if kind == "paragraph":
            text = obj.text.strip()
            has_math = _paragraph_has_math(obj)
            has_img = _paragraph_has_image(obj)
            if has_math:
                math_count += 1
            if has_img:
                image_count += 1
            if text:
                para_count += 1
                act = _detect_activity(text)
                if act and act not in detected_activities:
                    detected_activities.append(act)
                ordered_blocks.append({
                    "block_index": block_idx,
                    "kind": "paragraph",
                    "style": obj.style.name if obj.style else "",
                    "text": text,
                    "has_math": has_math,
                    "has_image": has_img,
                })
        elif kind == "table":
            table_count += 1
            rows_txt = []
            for row in obj.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    row_line = " | ".join(cells)
                    rows_txt.append(row_line)
                    act = _detect_activity(row_line)
                    if act and act not in detected_activities:
                        detected_activities.append(act)
            tbl_text = "\n".join(rows_txt)
            if tbl_text:
                ordered_blocks.append({
                    "block_index": block_idx,
                    "kind": "table",
                    "style": "Table",
                    "text": tbl_text,
                    "has_math": False,
                    "has_image": False,
                })

    full_text = "\n".join(b["text"] for b in ordered_blocks)
    return {
        "filename": filename,
        "type": "docx",
        "ordered_blocks": ordered_blocks,
        "detected_activities": detected_activities,
        "stats": {
            "paragraph_count": para_count,
            "table_count": table_count,
            "math_count": math_count,
            "image_count": image_count,
            "total_blocks": len(ordered_blocks),
        },
        "full_text": full_text,
    }


def read_pptx_document(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Đọc nội dung từng slide PowerPoint: tiêu đề, text, bảng, ghi chú, hình ảnh."""
    prs = Presentation(io.BytesIO(file_bytes))
    slides_info: List[Dict[str, Any]] = []
    image_count = 0
    chart_count = 0
    table_count = 0

    for s_idx, slide in enumerate(prs.slides):
        title_text = ""
        texts: List[str] = []
        tables: List[List[str]] = []
        has_picture = False
        has_chart = False

        if slide.shapes.title and slide.shapes.title.has_text_frame:
            title_text = slide.shapes.title.text.strip()

        for shape in slide.shapes:
            if shape.has_text_frame:
                txt = shape.text_frame.text.strip()
                if txt and txt != title_text:
                    texts.append(txt)
            if shape.has_table:
                table_count += 1
                t_rows = []
                for row in shape.table.rows:
                    t_rows.append(" | ".join(c.text.strip() for c in row.cells if c.text.strip()))
                tables.append(t_rows)
            if shape.shape_type == 13:  # PICTURE
                has_picture = True
                image_count += 1
            if shape.has_chart:
                has_chart = True
                chart_count += 1

        notes_text = ""
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            notes_text = slide.notes_slide.notes_text_frame.text.strip()

        slides_info.append({
            "slide_index": s_idx,
            "slide_number": s_idx + 1,
            "title": title_text,
            "texts": texts,
            "tables": tables,
            "notes": notes_text,
            "has_picture": has_picture,
            "has_chart": has_chart,
        })

    full_text_lines = []
    for s in slides_info:
        full_text_lines.append(f"=== SLIDE {s['slide_number']} ===")
        if s["title"]:
            full_text_lines.append(f"Tiêu đề: {s['title']}")
        for t in s["texts"]:
            full_text_lines.append(t)
        if s["has_picture"]:
            full_text_lines.append("[Slide có hình ảnh/sơ đồ minh họa]")
        if s["notes"]:
            full_text_lines.append(f"Ghi chú: {s['notes']}")

    return {
        "filename": filename,
        "type": "pptx",
        "slides": slides_info,
        "stats": {
            "slide_count": len(slides_info),
            "table_count": table_count,
            "image_count": image_count,
            "chart_count": chart_count,
        },
        "full_text": "\n".join(full_text_lines),
    }