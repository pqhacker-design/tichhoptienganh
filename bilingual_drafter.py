import io
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor
from config import COLOR_BLOCK_RGB, COLOR_ENGLISH_RGB, COLOR_IPA_RGB
from document_reader import iter_word_body_blocks
from gemini_service import call_gemini_json
from word_processor import _add_styled_run, _insert_paragraph_after

GLOSSARY_SYSTEM_INSTRUCTION = """
Bạn là chuyên gia biên soạn giáo án song ngữ và thuật ngữ học thuật chuyên ngành cho Chương trình GDPT Việt Nam.
Nhiệm vụ: Quét nội dung giáo án và trích xuất toàn bộ các thuật ngữ chuyên môn cốt lõi của môn học để lập Bảng thuật ngữ chuẩn (Glossary) trước khi soạn giáo án song ngữ.
Yêu cầu:
- Chính xác tuyệt đối theo thuật ngữ chuẩn trong sách giáo khoa/tài liệu quốc tế (Cambridge/IB/US Common Core tương ứng cấp học).
- Không dịch máy móc từng chữ.
- Nếu thuật ngữ có thể gây tranh cãi, đặt "needs_review": true.
- Trả về đúng JSON.
"""

DRAFT_SYSTEM_INSTRUCTION = """
Bạn là chuyên gia soạn thảo giáo án song ngữ chuẩn sư phạm (Công văn 5512) cho giáo viên phổ thông Việt Nam.
Nhiệm vụ: Chuyển ngữ chính xác từng mục văn bản giáo án tiếng Việt sang tiếng Anh học thuật tự nhiên, súc tích, đúng phong cách sư phạm.

NGUYÊN TẮC BẮT BUỘC:
1. TUÂN THỦ TUYỆT ĐỐI Bảng thuật ngữ chuyên ngành đã khóa (Glossary) được cung cấp trong prompt.
2. Giữ nguyên 100% ký hiệu toán học, tên điểm, biến số, công thức, đơn vị đo, số thứ tự (ví dụ: ΔABC, x, y, cm, 40°, Bài 1, Hoạt động 1...).
3. KHÔNG gộp, KHÔNG bỏ sót và KHÔNG đổi `id` của bất kỳ mục nào.
4. Trả về đúng JSON dạng {"translations": [{"id": "...", "en": "..."}]}.
"""


def extract_subject_glossary(
    lesson_text: str,
    level: str,
    grade: int,
    subject: str,
    textbook: str,
) -> List[Dict[str, Any]]:
    """Bước 1: Trích xuất bảng thuật ngữ chuyên ngành để giáo viên duyệt & khóa trước khi soạn song ngữ."""
    prompt = f"""
Thông tin môn học: {level} - Lớp {grade} | Môn: {subject} | Sách: {textbook}.
Hãy trích xuất từ 8 đến 20 thuật ngữ chuyên môn quan trọng nhất xuất hiện trong giáo án sau:

\"\"\"
{lesson_text[:18000]}
\"\"\"

Trả về JSON:
{{
  "glossary": [
    {{
      "vi": "Thuật ngữ tiếng Việt",
      "en": "Thuật ngữ tiếng Anh chuẩn chuyên ngành",
      "ipa": "/phiên âm IPA/",
      "note": "Ghi chú ngữ cảnh sử dụng trong môn {subject}",
      "needs_review": false
    }}
  ]
}}
"""
    raw = call_gemini_json(prompt=prompt, system_instruction=GLOSSARY_SYSTEM_INSTRUCTION)
    items = raw.get("glossary", [])
    for it in items:
        it["id"] = str(uuid.uuid4())[:8]
        it["approved"] = True
    return items


def _translate_batch(
    items: List[Dict[str, str]],
    glossary: List[Dict[str, Any]],
    level: str,
    grade: int,
    subject: str,
) -> Dict[str, str]:
    """Dịch một lô các đoạn văn/ô bảng với bảng thuật ngữ đã khóa."""
    approved_glossary = [g for g in glossary if g.get("approved")]
    glossary_lines = "\n".join(
        f"- {g['vi']} => {g['en']}" for g in approved_glossary if g.get("vi") and g.get("en")
    ) or "(Không có bảng thuật ngữ riêng)"

    payload_lines = "\n".join(f"[{it['id']}] {it['text']}" for it in items)

    prompt = f"""
Ngữ cảnh: Giáo án môn {subject}, {level} - Lớp {grade}.

BẢNG THUẬT NGỮ CHUYÊN NGÀNH ĐÃ KHÓA (BẮT BUỘC DÙNG ĐÚNG):
{glossary_lines}

DANH SÁCH CÁC MỤC CẦN CHUYỂN NGỮ SANG TIẾNG ANH:
{payload_lines}

Trả về JSON đúng cấu trúc:
{{
  "translations": [
    {{"id": "mã id nguyên văn", "en": "Bản tiếng Anh chuẩn chuyên ngành"}}
  ]
}}
"""
    res = call_gemini_json(
        prompt=prompt,
        system_instruction=DRAFT_SYSTEM_INSTRUCTION,
        temperature=0.15,
    )
    mapping: Dict[str, str] = {}
    for tr in res.get("translations", []):
        if tr.get("id") and tr.get("en"):
            mapping[str(tr["id"])] = str(tr["en"]).strip()
    return mapping


def _collect_doc_items(
    doc: Document,
    start_block: Optional[int] = None,
    end_block: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Thu thập toàn bộ đoạn văn và ô bảng (tránh lặp merged cells) trong phạm vi chỉ định."""
    blocks = list(iter_word_body_blocks(doc))
    items: List[Dict[str, Any]] = []

    for b_idx, (kind, obj) in enumerate(blocks):
        if start_block is not None and b_idx < start_block:
            continue
        if end_block is not None and b_idx > end_block:
            continue

        if kind == "paragraph":
            txt = obj.text.strip()
            if txt:
                items.append({
                    "id": f"p_{b_idx}",
                    "kind": "paragraph",
                    "block_index": b_idx,
                    "obj": obj,
                    "text": txt,
                    "is_heading": bool(obj.style and "Heading" in obj.style.name) or (len(txt) < 90 and txt.isupper()),
                })
        elif kind == "table":
            seen_tcs = set()
            for r_idx, row in enumerate(obj.rows):
                for c_idx, cell in enumerate(row.cells):
                    if cell._tc in seen_tcs:
                        continue
                    seen_tcs.add(cell._tc)
                    c_txt = cell.text.strip()
                    if c_txt:
                        items.append({
                            "id": f"t_{b_idx}_{r_idx}_{c_idx}",
                            "kind": "cell",
                            "block_index": b_idx,
                            "obj": cell,
                            "text": c_txt,
                            "is_heading": (r_idx == 0),
                        })
    return items


def _run_batch_translation(
    items: List[Dict[str, Any]],
    glossary: List[Dict[str, Any]],
    level: str,
    grade: int,
    subject: str,
    batch_size: int = 18,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> Dict[str, str]:
    translations: Dict[str, str] = {}
    total = len(items)
    if total == 0:
        return translations

    for start in range(0, total, batch_size):
        batch = items[start : start + batch_size]
        if progress_callback:
            pct = min(0.95, (start / total) * 0.9 + 0.05)
            progress_callback(pct, f"Đang chuyển ngữ song ngữ mục {start + 1}–{min(start + batch_size, total)} / {total}...")
        batch_input = [{"id": x["id"], "text": x["text"]} for x in batch]
        batch_map = _translate_batch(batch_input, glossary, level, grade, subject)
        translations.update(batch_map)

    if progress_callback:
        progress_callback(1.0, "Hoàn tất chuyển ngữ song ngữ!")
    return translations


def draft_bilingual_word_inline(
    file_bytes: bytes,
    glossary: List[Dict[str, Any]],
    level: str,
    grade: int,
    subject: str,
    start_block: Optional[int] = None,
    end_block: Optional[int] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Kiểu 1: Soạn giáo án song ngữ trực tiếp trên file Word gốc.
    Chèn bản dịch tiếng Anh chuẩn ngay dưới từng đoạn văn và trong từng ô bảng,
    bảo toàn 100% ảnh, bảng biểu, công thức toán học và không gây giãn chữ.
    """
    doc = Document(io.BytesIO(file_bytes))
    items = _collect_doc_items(doc, start_block, end_block)
    translations = _run_batch_translation(
        items, glossary, level, grade, subject, progress_callback=progress_callback
    )

    inserted_count = 0
    for it in items:
        en_txt = translations.get(it["id"])
        if not en_txt:
            continue

        if it["kind"] == "paragraph":
            _insert_paragraph_after(
                it["obj"],
                en_txt,
                COLOR_BLOCK_RGB,
                italic=not it["is_heading"],
                bold=it["is_heading"],
            )
            inserted_count += 1
        elif it["kind"] == "cell":
            cell = it["obj"]
            new_p = cell.add_paragraph()
            new_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            new_p.paragraph_format.space_before = Pt(2)
            new_p.paragraph_format.space_after = Pt(2)
            _add_styled_run(
                new_p,
                en_txt,
                COLOR_BLOCK_RGB,
                italic=not it["is_heading"],
                bold=it["is_heading"],
            )
            inserted_count += 1

    # Thêm bảng thuật ngữ chuyên ngành đã khóa ở cuối tài liệu
    approved_glossary = [g for g in glossary if g.get("approved")]
    if approved_glossary:
        doc.add_paragraph("")
        p_h = doc.add_paragraph()
        _add_styled_run(
            p_h,
            f"BẢNG THUẬT NGỮ CHUYÊN NGÀNH ĐÃ ÁP DỤNG – MÔN {subject.upper()} (SUBJECT GLOSSARY)",
            COLOR_ENGLISH_RGB,
            bold=True,
        )
        tbl = doc.add_table(rows=1, cols=4)
        tbl.style = "Table Grid"
        tbl.rows[0].cells[0].text = "Tiếng Việt"
        tbl.rows[0].cells[1].text = "Tiếng Anh chuyên ngành"
        tbl.rows[0].cells[2].text = "Phiên âm IPA"
        tbl.rows[0].cells[3].text = "Ghi chú ngữ cảnh"
        for g in approved_glossary:
            rc = tbl.add_row().cells
            rc[0].text = g.get("vi", "")
            _add_styled_run(rc[1].paragraphs[0], g.get("en", ""), COLOR_ENGLISH_RGB, bold=True)
            _add_styled_run(rc[2].paragraphs[0], g.get("ipa", ""), COLOR_IPA_RGB, italic=True)
            rc[3].text = g.get("note", "")

    out = io.BytesIO()
    doc.save(out)
    return out.getvalue(), {"total_items": len(items), "translated_items": inserted_count, "glossary_count": len(approved_glossary)}


def draft_bilingual_word_two_columns(
    file_bytes: bytes,
    glossary: List[Dict[str, Any]],
    level: str,
    grade: int,
    subject: str,
    lesson_title: str = "KẾ HOẠCH BÀI DẠY SONG NGỮ",
    start_block: Optional[int] = None,
    end_block: Optional[int] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Kiểu 2: Xuất giáo án song ngữ 2 cột song song (Việt | Anh) trên khổ giấy A4 ngang,
    kèm bảng thuật ngữ chuyên ngành ở đầu giáo án.
    """
    src_doc = Document(io.BytesIO(file_bytes))
    items = _collect_doc_items(src_doc, start_block, end_block)
    translations = _run_batch_translation(
        items, glossary, level, grade, subject, progress_callback=progress_callback
    )

    out_doc = Document()
    # Thiết lập A4 ngang để 2 cột rộng rãi, dễ đọc
    section = out_doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Cm(29.7)
    section.page_height = Cm(21.0)
    section.left_margin = Cm(1.5)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)

    p_title = out_doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_t = p_title.add_run(f"GIÁO ÁN SONG NGỮ / BILINGUAL LESSON PLAN\n{lesson_title}")
    r_t.bold = True
    r_t.font.size = Pt(14)
    r_t.font.color.rgb = RGBColor(*COLOR_ENGLISH_RGB)

    p_meta = out_doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.add_run(f"Môn / Subject: {subject}  |  Cấp học / Level: {level} – Lớp / Grade {grade}")

    # 1. Bảng thuật ngữ chuyên ngành đầu bài
    approved_glossary = [g for g in glossary if g.get("approved")]
    if approved_glossary:
        p_g = out_doc.add_paragraph()
        _add_styled_run(p_g, "I. BẢNG THUẬT NGỮ CHUYÊN NGÀNH (SUBJECT TERMINOLOGY GLOSSARY)", COLOR_ENGLISH_RGB, bold=True)
        g_tbl = out_doc.add_table(rows=1, cols=4)
        g_tbl.style = "Table Grid"
        g_tbl.rows[0].cells[0].text = "Tiếng Việt"
        g_tbl.rows[0].cells[1].text = "English Term"
        g_tbl.rows[0].cells[2].text = "IPA"
        g_tbl.rows[0].cells[3].text = "Ngữ cảnh / Context"
        for g in approved_glossary:
            rc = g_tbl.add_row().cells
            rc[0].text = g.get("vi", "")
            _add_styled_run(rc[1].paragraphs[0], g.get("en", ""), COLOR_ENGLISH_RGB, bold=True)
            _add_styled_run(rc[2].paragraphs[0], g.get("ipa", ""), COLOR_IPA_RGB, italic=True)
            rc[3].text = g.get("note", "")
        out_doc.add_paragraph("")

    # 2. Bảng nội dung giáo án 2 cột Việt | Anh
    p_main = out_doc.add_paragraph()
    _add_styled_run(p_main, "II. TIẾN TRÌNH DẠY HỌC SONG NGỮ (BILINGUAL LESSON PROCEDURE)", COLOR_ENGLISH_RGB, bold=True)

    main_tbl = out_doc.add_table(rows=1, cols=2)
    main_tbl.style = "Table Grid"
    hdr = main_tbl.rows[0].cells
    _add_styled_run(hdr[0].paragraphs[0], "NỘI DUNG TIẾNG VIỆT (BẢN GỐC)", (0, 0, 0), bold=True)
    _add_styled_run(hdr[1].paragraphs[0], "ENGLISH VERSION (CHUẨN THUẬT NGỮ CHUYÊN NGÀNH)", COLOR_ENGLISH_RGB, bold=True)

    translated_count = 0
    for it in items:
        row_cells = main_tbl.add_row().cells
        p_vi = row_cells[0].paragraphs[0]
        r_vi = p_vi.add_run(it["text"])
        r_vi.bold = it["is_heading"]
        r_vi.font.size = Pt(11)

        en_txt = translations.get(it["id"], "")
        if en_txt:
            translated_count += 1
        p_en = row_cells[1].paragraphs[0]
        r_en = _add_styled_run(p_en, en_txt, COLOR_BLOCK_RGB, bold=it["is_heading"])
        r_en.font.size = Pt(11)

    out = io.BytesIO()
    out_doc.save(out)
    return out.getvalue(), {"total_items": len(items), "translated_items": translated_count, "glossary_count": len(approved_glossary)}
