import io
import re
from typing import Any, Dict, List, Tuple
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.shared import Pt, RGBColor
from docx.text.paragraph import Paragraph
from config import COLOR_BLOCK_RGB, COLOR_ENGLISH_RGB, COLOR_IPA_RGB, INTEGRATION_LEVELS
from document_reader import iter_word_body_blocks


def _add_styled_run(
    paragraph: Paragraph,
    text: str,
    rgb: Tuple[int, int, int],
    italic: bool = False,
    bold: bool = False,
):
    run = paragraph.add_run(text)
    run.font.color.rgb = RGBColor(*rgb)
    run.italic = italic
    run.bold = bold
    for r in paragraph.runs:
        if r is not run:
            if r.font.name:
                run.font.name = r.font.name
            if r.font.size:
                run.font.size = r.font.size
            break
    return run


def _insert_paragraph_after(
    paragraph: Paragraph,
    text: str,
    rgb: Tuple[int, int, int],
    italic: bool = True,
    bold: bool = False,
) -> Paragraph:
    """Chèn một đoạn văn mới ngay sau paragraph hiện tại để không làm giãn chữ đoạn gốc."""
    new_p_xml = OxmlElement("w:p")
    paragraph._p.addnext(new_p_xml)
    new_p = Paragraph(new_p_xml, paragraph._parent)
    new_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    new_p.paragraph_format.space_before = Pt(2)
    new_p.paragraph_format.space_after = Pt(4)

    run = new_p.add_run(text)
    run.font.color.rgb = RGBColor(*rgb)
    run.italic = italic
    run.bold = bold
    for r in paragraph.runs:
        if r.font.name:
            run.font.name = r.font.name
        if r.font.size:
            run.font.size = r.font.size
        break
    return new_p


def _insert_after_match_in_runs(
    paragraph: Paragraph,
    vi_term: str,
    en_text: str,
    ipa_text: str = "",
) -> bool:
    if not vi_term or en_text.lower() in paragraph.text.lower():
        return False

    pattern = re.compile(re.escape(vi_term), re.IGNORECASE)

    for run in paragraph.runs:
        match = pattern.search(run.text)
        if match:
            before = run.text[: match.end()]
            after = run.text[match.end() :]
            run.text = before

            en_run = paragraph.add_run(f" ({en_text})")
            en_run.font.color.rgb = RGBColor(*COLOR_ENGLISH_RGB)
            if run.font.size:
                en_run.font.size = run.font.size
            if run.font.name:
                en_run.font.name = run.font.name
            run._r.addnext(en_run._r)

            last_r = en_run._r
            if ipa_text:
                ipa_run = paragraph.add_run(f" {ipa_text}")
                ipa_run.font.color.rgb = RGBColor(*COLOR_IPA_RGB)
                ipa_run.italic = True
                if run.font.size:
                    ipa_run.font.size = run.font.size
                if run.font.name:
                    ipa_run.font.name = run.font.name
                last_r.addnext(ipa_run._r)
                last_r = ipa_run._r

            if after:
                after_run = paragraph.add_run(after)
                after_run.bold = run.bold
                after_run.italic = run.italic
                after_run.underline = run.underline
                if run.font.size:
                    after_run.font.size = run.font.size
                if run.font.name:
                    after_run.font.name = run.font.name
                if run.font.color and run.font.color.rgb:
                    after_run.font.color.rgb = run.font.color.rgb
                last_r.addnext(after_run._r)
            return True

    if pattern.search(paragraph.text):
        _add_styled_run(paragraph, f" [{vi_term}: {en_text}", COLOR_ENGLISH_RGB)
        if ipa_text:
            _add_styled_run(paragraph, f" {ipa_text}", COLOR_IPA_RGB, italic=True)
        _add_styled_run(paragraph, "]", COLOR_ENGLISH_RGB)
        return True

    return False


def _normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def integrate_word_multi_lesson(
    file_bytes: bytes,
    lessons: List[Dict[str, Any]],
    integration_level: int = 1,
) -> Tuple[bytes, List[Dict[str, Any]]]:
    """
    Tích hợp trực tiếp nhiều bài học vào cùng một file Word gốc theo Mức độ 1, 2 hoặc 3.
    """
    doc = Document(io.BytesIO(file_bytes))
    lesson_reports: List[Dict[str, Any]] = []
    active_lessons = []

    for ls in lessons:
        if not ls.get("selected"):
            lesson_reports.append({
                "Bài học": ls["title"],
                "Phạm vi": f"Block {ls['start_index']}–{ls['end_index']}",
                "Mức độ": f"Mức {integration_level}",
                "Số từ khóa": 0,
                "Số vị trí tích hợp": 0,
                "Trạng thái": "Giữ nguyên (Không chọn)",
            })
            continue
        if not ls.get("analysis"):
            lesson_reports.append({
                "Bài học": ls["title"],
                "Phạm vi": f"Block {ls['start_index']}–{ls['end_index']}",
                "Mức độ": f"Mức {integration_level}",
                "Số từ khóa": 0,
                "Số vị trí tích hợp": 0,
                "Trạng thái": "Chưa phân tích / Chưa duyệt",
            })
            continue

        analysis = ls["analysis"]
        ls_level = analysis.get("integration_level", integration_level)
        kws = [k for k in analysis.get("keywords", []) if k.get("approved")]
        hdrs = [h for h in analysis.get("bilingual_headers", []) if h.get("approved")]
        cmds = [c for c in analysis.get("classroom_english", []) if c.get("approved")]
        blocks = [b for b in analysis.get("bilingual_blocks", []) if b.get("approved")]
        pracs = [p for p in analysis.get("practice_activities", []) if p.get("approved")]

        active_lessons.append({
            "meta": ls,
            "level": ls_level,
            "start": ls["start_index"],
            "end": ls["end_index"],
            "keywords": kws,
            "headers": hdrs,
            "commands": cmds,
            "bilingual_blocks": blocks,
            "practices": pracs,
            "kw_hits": {k["vi"]: 0 for k in kws},
            "used_cmds": set(),
            "used_blocks": set(),
            "positions_integrated": 0,
        })

    # Cố định danh sách block gốc trước khi chèn đoạn mới
    original_blocks = list(iter_word_body_blocks(doc))

    for block_idx, (kind, obj) in enumerate(original_blocks):
        owner = None
        for al in active_lessons:
            if al["start"] <= block_idx <= al["end"]:
                owner = al
                break
        if owner is None:
            continue

        target_paragraphs: List[Paragraph] = []
        if kind == "paragraph":
            target_paragraphs.append(obj)
        elif kind == "table":
            seen_tcs = set()
            for row in obj.rows:
                for cell in row.cells:
                    if cell._tc not in seen_tcs:
                        seen_tcs.add(cell._tc)
                        target_paragraphs.extend(cell.paragraphs)

        for p in target_paragraphs:
            text = p.text.strip()
            if not text:
                continue
            norm_text = _normalize_text(text)

            # 1. Tiêu đề hoạt động song ngữ + Khẩu lệnh lớp học
            for h in owner["headers"]:
                vi_h, en_h = h.get("vi", "").strip(), h.get("en", "").strip()
                if vi_h and en_h and len(text) < 120:
                    if re.search(re.escape(vi_h), text, re.IGNORECASE) and en_h.lower() not in text.lower():
                        _add_styled_run(p, f" ({en_h})", COLOR_ENGLISH_RGB, bold=True)
                        owner["positions_integrated"] += 1

                        for cmd in owner["commands"]:
                            if cmd["id"] not in owner["used_cmds"]:
                                _insert_paragraph_after(
                                    p,
                                    f"[Classroom English: {cmd['en']} — {cmd['vi']}]",
                                    COLOR_ENGLISH_RGB,
                                    italic=True,
                                )
                                owner["used_cmds"].add(cmd["id"])
                                owner["positions_integrated"] += 1
                                break
                        break

            # 2. Thuật ngữ cốt lõi (Keywords)
            max_repeats = 3 if owner["level"] == 1 else 4
            for k in owner["keywords"]:
                vi_k = k.get("vi", "").strip()
                en_k = k.get("en", "").strip()
                ipa_k = k.get("ipa", "").strip()
                if not vi_k or not en_k or owner["kw_hits"][vi_k] >= max_repeats:
                    continue
                ipa_to_add = ipa_k if owner["kw_hits"][vi_k] == 0 else ""
                if _insert_after_match_in_runs(p, vi_k, en_k, ipa_to_add):
                    owner["kw_hits"][vi_k] += 1
                    owner["positions_integrated"] += 1

            # 3. Các đoạn song ngữ trọng tâm (áp dụng cho Mức độ 2 và Mức độ 3)
            if owner["level"] >= 2:
                for blk in owner["bilingual_blocks"]:
                    if blk["id"] in owner["used_blocks"]:
                        continue
                    anchor = _normalize_text(blk.get("vi_anchor", ""))
                    en_block = blk.get("en_text", "").strip()
                    if not anchor or not en_block:
                        continue
                    # Khớp theo đoạn mỏ neo (tối thiểu 15 ký tự hoặc toàn bộ anchor nếu ngắn)
                    anchor_key = anchor[:40]
                    if anchor_key in norm_text:
                        prefix = f"[{blk.get('section_type', 'English')}] " if owner["level"] == 2 else ""
                        _insert_paragraph_after(
                            p,
                            f"→ {prefix}{en_block}",
                            COLOR_BLOCK_RGB,
                            italic=False,
                        )
                        owner["used_blocks"].add(blk["id"])
                        owner["positions_integrated"] += 1

    # Phụ lục tổng hợp cuối tài liệu
    if active_lessons:
        lvl_name = INTEGRATION_LEVELS.get(integration_level, INTEGRATION_LEVELS[1])["name"].upper()
        doc.add_paragraph("")
        p_head = doc.add_paragraph()
        _add_styled_run(
            p_head,
            f"PHỤ LỤC TÍCH HỢP TIẾNG ANH ({lvl_name} – TT 94/2026/TT-BGDĐT)",
            COLOR_ENGLISH_RGB,
            bold=True,
        )
        for al in active_lessons:
            p_lt = doc.add_paragraph()
            _add_styled_run(p_lt, f"▶ {al['meta']['title']} (Mức độ {al['level']})", COLOR_ENGLISH_RGB, bold=True)
            if al["keywords"]:
                tbl = doc.add_table(rows=1, cols=3)
                tbl.style = "Table Grid"
                tbl.rows[0].cells[0].text = "Tiếng Việt"
                tbl.rows[0].cells[1].text = "Tiếng Anh"
                tbl.rows[0].cells[2].text = "Phiên âm IPA"
                for k in al["keywords"]:
                    rc = tbl.add_row().cells
                    rc[0].text = k.get("vi", "")
                    _add_styled_run(rc[1].paragraphs[0], k.get("en", ""), COLOR_ENGLISH_RGB, bold=True)
                    _add_styled_run(rc[2].paragraphs[0], k.get("ipa", ""), COLOR_IPA_RGB, italic=True)

            # Nếu còn đoạn song ngữ Mức 2/3 chưa khớp tự động trong bài -> đưa vào phụ lục để không mất nội dung
            unplaced_blocks = [b for b in al["bilingual_blocks"] if b["id"] not in al["used_blocks"]]
            if unplaced_blocks:
                p_ub = doc.add_paragraph()
                _add_styled_run(p_ub, "Nội dung song ngữ bổ sung (Mức độ 2/3):", COLOR_BLOCK_RGB, bold=True)
                for b in unplaced_blocks:
                    p_b = doc.add_paragraph()
                    _add_styled_run(p_b, f"• [{b.get('section_type', 'English')}] ", COLOR_BLOCK_RGB, bold=True)
                    _add_styled_run(p_b, b.get("en_text", ""), COLOR_BLOCK_RGB)
                    al["positions_integrated"] += 1

            for act in al["practices"]:
                p_a = doc.add_paragraph()
                _add_styled_run(
                    p_a,
                    f"• [{act.get('type', 'Practice')}] {act.get('title', '')}: ",
                    COLOR_ENGLISH_RGB,
                    bold=True,
                )
                p_a.add_run(act.get("content", ""))
                al["positions_integrated"] += 1

            lesson_reports.append({
                "Bài học": al["meta"]["title"],
                "Phạm vi": f"Block {al['start']}–{al['end']}",
                "Mức độ": f"Mức {al['level']}",
                "Số từ khóa": len(al["keywords"]),
                "Số vị trí tích hợp": al["positions_integrated"],
                "Trạng thái": "Hoàn thành",
            })

    out_stream = io.BytesIO()
    doc.save(out_stream)
    return out_stream.getvalue(), lesson_reports
