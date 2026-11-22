import io
import re
from typing import Any, Dict, List, Tuple
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt
from config import COLOR_BLOCK_RGB, COLOR_ENGLISH_RGB, COLOR_NOTE_BG_RGB


def _append_english_run(paragraph, text: str, rgb: Tuple[int, int, int], font_size_pt: float = 14.0, italic: bool = False):
    run = paragraph.add_run()
    run.text = text
    run.font.color.rgb = RGBColor(*rgb)
    run.font.size = Pt(max(10.0, font_size_pt))
    run.font.italic = italic
    return run


def _get_paragraph_font_size(paragraph, default_pt: float = 18.0) -> float:
    for r in paragraph.runs:
        if r.font.size:
            return r.font.size.pt
    return default_pt


def _add_callout_box(slide, lines: List[str], slide_width, slide_height):
    box_w = Inches(4.2)
    box_h = Inches(min(1.8, 0.35 * len(lines) + 0.3))
    left = slide_width - box_w - Inches(0.25)
    top = slide_height - box_h - Inches(0.2)

    textbox = slide.shapes.add_textbox(left, top, box_w, box_h)
    fill = textbox.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(*COLOR_NOTE_BG_RGB)

    tf = textbox.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        _append_english_run(p, line, COLOR_ENGLISH_RGB, font_size_pt=11.0, italic=(i > 0))


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def integrate_pptx_multi_lesson(
    file_bytes: bytes,
    lessons: List[Dict[str, Any]],
    integration_level: int = 1,
) -> Tuple[bytes, List[Dict[str, Any]]]:
    """Tích hợp trực tiếp nhiều bài học vào PowerPoint gốc theo Mức độ 1, 2 hoặc 3."""
    prs = Presentation(io.BytesIO(file_bytes))
    lesson_reports: List[Dict[str, Any]] = []
    active_lessons = []

    for ls in lessons:
        if not ls.get("selected"):
            lesson_reports.append({
                "Bài học": ls["title"],
                "Phạm vi": f"Slide {ls['start_index']}–{ls['end_index']}",
                "Mức độ": f"Mức {integration_level}",
                "Số từ khóa": 0,
                "Số vị trí tích hợp": 0,
                "Trạng thái": "Giữ nguyên (Không chọn)",
            })
            continue
        if not ls.get("analysis"):
            lesson_reports.append({
                "Bài học": ls["title"],
                "Phạm vi": f"Slide {ls['start_index']}–{ls['end_index']}",
                "Mức độ": f"Mức {integration_level}",
                "Số từ khóa": 0,
                "Số vị trí tích hợp": 0,
                "Trạng thái": "Chưa phân tích / Chưa duyệt",
            })
            continue

        analysis = ls["analysis"]
        ls_level = analysis.get("integration_level", integration_level)
        active_lessons.append({
            "meta": ls,
            "level": ls_level,
            "start": ls["start_index"],
            "end": ls["end_index"],
            "keywords": [k for k in analysis.get("keywords", []) if k.get("approved")],
            "headers": [h for h in analysis.get("bilingual_headers", []) if h.get("approved")],
            "bilingual_blocks": [b for b in analysis.get("bilingual_blocks", []) if b.get("approved")],
            "diagrams": [d for d in analysis.get("diagram_labels", []) if d.get("approved")],
            "commands": [c for c in analysis.get("classroom_english", []) if c.get("approved")],
            "used_blocks": set(),
            "positions_integrated": 0,
        })

    for s_idx, slide in enumerate(prs.slides):
        slide_num = s_idx + 1
        owner = None
        for al in active_lessons:
            if al["start"] <= slide_num <= al["end"]:
                owner = al
                break
        if owner is None:
            continue

        has_picture = any(sh.shape_type == 13 for sh in slide.shapes)
        slide_matched_blocks: List[str] = []

        for shape in slide.shapes:
            if shape.has_text_frame:
                for p in list(shape.text_frame.paragraphs):
                    p_text = p.text.strip()
                    if not p_text:
                        continue
                    en_size = max(11.0, _get_paragraph_font_size(p, 18.0) - 2.0)

                    for h in owner["headers"]:
                        vi_h, en_h = h.get("vi", "").strip(), h.get("en", "").strip()
                        if vi_h and en_h and re.search(re.escape(vi_h), p_text, re.IGNORECASE):
                            if en_h.lower() not in p_text.lower():
                                _append_english_run(p, f" ({en_h})", COLOR_ENGLISH_RGB, font_size_pt=en_size)
                                owner["positions_integrated"] += 1
                                break

                    for k in owner["keywords"]:
                        vi_k, en_k = k.get("vi", "").strip(), k.get("en", "").strip()
                        if vi_k and en_k and re.search(re.escape(vi_k), p_text, re.IGNORECASE):
                            if en_k.lower() not in p_text.lower():
                                _append_english_run(p, f" ({en_k})", COLOR_ENGLISH_RGB, font_size_pt=en_size)
                                owner["positions_integrated"] += 1

                    # Mức độ 2 & 3: chèn đoạn song ngữ ngắn ngay trong text_frame nếu khớp anchor
                    if owner["level"] >= 2:
                        norm_p = _norm(p_text)
                        for blk in owner["bilingual_blocks"]:
                            if blk["id"] in owner["used_blocks"]:
                                continue
                            anchor = _norm(blk.get("vi_anchor", ""))[:35]
                            if anchor and anchor in norm_p:
                                new_p = shape.text_frame.add_paragraph()
                                _append_english_run(
                                    new_p,
                                    f"→ {blk['en_text']}",
                                    COLOR_BLOCK_RGB,
                                    font_size_pt=max(10.5, en_size - 1.5),
                                    italic=(owner["level"] == 2),
                                )
                                owner["used_blocks"].add(blk["id"])
                                slide_matched_blocks.append(blk["en_text"])
                                owner["positions_integrated"] += 1

            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        c_text = cell.text.strip()
                        if not c_text:
                            continue
                        for k in owner["keywords"]:
                            vi_k, en_k = k.get("vi", "").strip(), k.get("en", "").strip()
                            if vi_k and en_k and re.search(re.escape(vi_k), c_text, re.IGNORECASE):
                                if en_k.lower() not in c_text.lower():
                                    p0 = cell.text_frame.paragraphs[0]
                                    _append_english_run(p0, f" ({en_k})", COLOR_ENGLISH_RGB, font_size_pt=11.0)
                                    owner["positions_integrated"] += 1

        if has_picture and owner["diagrams"]:
            lines = ["Keywords / Labels:"] + [f"• {d['vi']}: {d['en']}" for d in owner["diagrams"][:4]]
            _add_callout_box(slide, lines, prs.slide_width, prs.slide_height)
            owner["positions_integrated"] += 1

        # Ghi chú cho giáo viên ở slide mở đầu bài (Mức 2 & 3 bổ sung kịch bản giảng dạy tiếng Anh)
        if slide_num == owner["start"]:
            notes_tf = slide.notes_slide.notes_text_frame
            extra_notes = []
            if owner["commands"]:
                extra_notes.append(
                    f"[Classroom English – Mức độ {owner['level']}]:\n"
                    + "\n".join(f"- {c['en']} ({c['vi']})" for c in owner["commands"][:8])
                )
            if owner["level"] == 3 and owner["bilingual_blocks"]:
                extra_notes.append(
                    "[English Teaching Script]:\n"
                    + "\n".join(f"- {b['en_text']}" for b in owner["bilingual_blocks"][:5])
                )
            if extra_notes:
                notes_tf.text = (notes_tf.text or "") + "\n\n" + "\n\n".join(extra_notes)

    for al in active_lessons:
        lesson_reports.append({
            "Bài học": al["meta"]["title"],
            "Phạm vi": f"Slide {al['start']}–{al['end']}",
            "Mức độ": f"Mức {al['level']}",
            "Số từ khóa": len(al["keywords"]),
            "Số vị trí tích hợp": al["positions_integrated"],
            "Trạng thái": "Hoàn thành",
        })

    out_stream = io.BytesIO()
    prs.save(out_stream)
    return out_stream.getvalue(), lesson_reports
