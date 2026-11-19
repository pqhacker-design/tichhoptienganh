import io
import re
from typing import Any, Dict, List, Tuple
from docx import Document
from docx.shared import RGBColor
from config import COLOR_ENGLISH_RGB, COLOR_IPA_RGB
from document_reader import iter_word_body_blocks


def _add_styled_run(paragraph, text: str, rgb: Tuple[int, int, int], italic: bool = False, bold: bool = False):
    run = paragraph.add_run(text)
    run.font.color.rgb = RGBColor(*rgb)
    run.italic = italic
    run.bold = bold
    return run


def _insert_after_match_in_runs(paragraph, vi_term: str, en_text: str, ipa_text: str = "") -> bool:
    """
    Chèn tiếng Anh ngay sau thuật ngữ tiếng Việt trong cùng run (nếu tìm thấy),
    bảo toàn toàn bộ các run khác và XML công thức/hình ảnh.
    """
    if not vi_term or en_text.lower() in paragraph.text.lower():
        return False

    pattern = re.compile(re.escape(vi_term), re.IGNORECASE)

    # Trường hợp 1: Thuật ngữ nằm gọn trong một run (giữ nguyên 100% XML khác)
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

    # Trường hợp 2: Thuật ngữ bị tách qua nhiều run nhưng đoạn có chứa thuật ngữ
    if pattern.search(paragraph.text):
        _add_styled_run(paragraph, f" [{vi_term}: {en_text}", COLOR_ENGLISH_RGB)
        if ipa_text:
            _add_styled_run(paragraph, f" {ipa_text}", COLOR_IPA_RGB, italic=True)
        _add_styled_run(paragraph, "]", COLOR_ENGLISH_RGB)
        return True

    return False


def integrate_word_multi_lesson(
    file_bytes: bytes,
    lessons: List[Dict[str, Any]],
) -> Tuple[bytes, List[Dict[str, Any]]]:
    """
    Tích hợp trực tiếp nhiều bài học vào cùng một file Word gốc.
    - Chỉ tích hợp vào các bài có selected=True và analysis != None.
    - Mỗi bài chỉ tác động đúng trong phạm vi [start_index, end_index].
    - Bài không được chọn được giữ nguyên 100%.
    """
    doc = Document(io.BytesIO(file_bytes))
    lesson_reports: List[Dict[str, Any]] = []
    active_lessons = []

    for ls in lessons:
        if not ls.get("selected"):
            lesson_reports.append({
                "Bài học": ls["title"],
                "Phạm vi": f"Block {ls['start_index']}–{ls['end_index']}",
                "Số từ khóa": 0,
                "Số vị trí tích hợp": 0,
                "Trạng thái": "Giữ nguyên (Không chọn)",
            })
            continue
        if not ls.get("analysis"):
            lesson_reports.append({
                "Bài học": ls["title"],
                "Phạm vi": f"Block {ls['start_index']}–{ls['end_index']}",
                "Số từ khóa": 0,
                "Số vị trí tích hợp": 0,
                "Trạng thái": "Chưa phân tích / Chưa duyệt",
            })
            continue

        analysis = ls["analysis"]
        kws = [k for k in analysis.get("keywords", []) if k.get("approved")]
        hdrs = [h for h in analysis.get("bilingual_headers", []) if h.get("approved")]
        cmds = [c for c in analysis.get("classroom_english", []) if c.get("approved")]
        pracs = [p for p in analysis.get("practice_activities", []) if p.get("approved")]

        active_lessons.append({
            "meta": ls,
            "start": ls["start_index"],
            "end": ls["end_index"],
            "keywords": kws,
            "headers": hdrs,
            "commands": cmds,
            "practices": pracs,
            "kw_hits": {k["vi"]: 0 for k in kws},
            "used_cmds": set(),
            "positions_integrated": 0,
        })

    # Duyệt toàn bộ body đúng 1 lần theo block_index
    for block_idx, (kind, obj) in enumerate(iter_word_body_blocks(doc)):
        owner = None
        for al in active_lessons:
            if al["start"] <= block_idx <= al["end"]:
                owner = al
                break
        if owner is None:
            continue

        target_paragraphs = []
        if kind == "paragraph":
            target_paragraphs.append(obj)
        elif kind == "table":
            for row in obj.rows:
                for cell in row.cells:
                    target_paragraphs.extend(cell.paragraphs)

        for p in target_paragraphs:
            text = p.text.strip()
            if not text:
                continue

            # 1. Tiêu đề hoạt động song ngữ (chỉ dùng bộ của owner)
            for h in owner["headers"]:
                vi_h, en_h = h.get("vi", "").strip(), h.get("en", "").strip()
                if vi_h and en_h and len(text) < 120:
                    if re.search(re.escape(vi_h), text, re.IGNORECASE) and en_h.lower() not in text.lower():
                        _add_styled_run(p, f" ({en_h})", COLOR_ENGLISH_RGB, bold=True)
                        owner["positions_integrated"] += 1

                        for cmd in owner["commands"]:
                            if cmd["id"] not in owner["used_cmds"]:
                                _add_styled_run(
                                    p,
                                    f"\n[Classroom English: {cmd['en']} — {cmd['vi']}]",
                                    COLOR_ENGLISH_RGB,
                                    italic=True,
                                )
                                owner["used_cmds"].add(cmd["id"])
                                owner["positions_integrated"] += 1
                                break
                        break

            # 2. Thuật ngữ cốt lõi (chỉ dùng bộ của owner, lặp tối đa 3 lần trong bài)
            for k in owner["keywords"]:
                vi_k, en_k, ipa_k = k.get("vi", "").strip(), k.get("en", "").strip(), k.get("ipa", "").strip()
                if not vi_k or not en_k or owner["kw_hits"][vi_k] >= 3:
                    continue
                ipa_to_add = ipa_k if owner["kw_hits"][vi_k] == 0 else ""
                if _insert_after_match_in_runs(p, vi_k, en_k, ipa_to_add):
                    owner["kw_hits"][vi_k] += 1
                    owner["positions_integrated"] += 1

    # Bổ sung phụ lục tổng hợp theo từng bài ở cuối tài liệu
    if active_lessons:
        doc.add_paragraph("")
        p_head = doc.add_paragraph()
        _add_styled_run(
            p_head,
            "PHỤ LỤC TỪ KHÓA & HOẠT ĐỘNG CỦNG CỐ THEO TỪNG BÀI (MỨC ĐỘ 1)",
            COLOR_ENGLISH_RGB,
            bold=True,
        )
        for al in active_lessons:
            p_lt = doc.add_paragraph()
            _add_styled_run(p_lt, f"▶ {al['meta']['title']}", COLOR_ENGLISH_RGB, bold=True)
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
            for act in al["practices"]:
                p_a = doc.add_paragraph()
                _add_styled_run(p_a, f"• [{act.get('type', 'Practice')}] {act.get('title', '')}: ", COLOR_ENGLISH_RGB, bold=True)
                p_a.add_run(act.get("content", ""))
                al["positions_integrated"] += 1

            lesson_reports.append({
                "Bài học": al["meta"]["title"],
                "Phạm vi": f"Block {al['start']}–{al['end']}",
                "Số từ khóa": len(al["keywords"]),
                "Số vị trí tích hợp": al["positions_integrated"],
                "Trạng thái": "Hoàn thành",
            })

    out_stream = io.BytesIO()
    doc.save(out_stream)
    return out_stream.getvalue(), lesson_reports