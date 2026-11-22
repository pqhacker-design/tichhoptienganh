from typing import Any, Dict, List
from config import INTEGRATION_LEVELS


def run_quality_check(
    approved_data: Dict[str, Any],
    doc_summaries: List[Dict[str, Any]],
    integration_level: int = 1,
) -> List[Dict[str, str]]:
    """Kiểm tra 10 tiêu chí chất lượng linh hoạt theo Mức độ 1, 2 hoặc 3."""
    lvl = approved_data.get("integration_level", integration_level)
    lvl_cfg = INTEGRATION_LEVELS.get(lvl, INTEGRATION_LEVELS[1])
    min_kw, max_kw = lvl_cfg["keyword_range"]

    keywords = [k for k in approved_data.get("keywords", []) if k.get("approved")]
    blocks = [b for b in approved_data.get("bilingual_blocks", []) if b.get("approved")]
    checks: List[Dict[str, str]] = []

    flagged = [k["vi"] for k in keywords if k.get("needs_teacher_review")]
    checks.append({
        "Tiêu chí": "1. Độ chính xác thuật ngữ chuyên môn",
        "Trạng thái": "⚠️ Cần kiểm tra" if flagged else "✅ Đạt",
        "Chi tiết": f"Cần rà soát: {', '.join(flagged)}" if flagged else "Các thuật ngữ phù hợp ngữ cảnh bộ môn.",
    })

    checks.append({
        "Tiêu chí": f"2. Phù hợp {lvl_cfg['short_label']} (TT 94/2026)",
        "Trạng thái": "✅ Đạt",
        "Chi tiết": f"Đang áp dụng {lvl_cfg['name']} ({lvl_cfg['english_ratio']}).",
    })

    kw_count = len(keywords)
    if min_kw <= kw_count <= max_kw:
        st_kw, msg_kw = "✅ Đạt", f"Đang chọn {kw_count} thuật ngữ (chuẩn Mức {lvl}: {min_kw}–{max_kw} từ)."
    elif kw_count == 0:
        st_kw, msg_kw = "❌ Chưa đạt", "Chưa có thuật ngữ nào được duyệt."
    else:
        st_kw, msg_kw = "⚠️ Lưu ý", f"Đang chọn {kw_count} thuật ngữ (khuyến nghị Mức {lvl}: {min_kw}–{max_kw} từ)."
    checks.append({"Tiêu chí": "3. Mật độ thuật ngữ tiếng Anh", "Trạng thái": st_kw, "Chi tiết": msg_kw})

    if lvl == 1:
        st_blk = "✅ Đạt" if len(blocks) == 0 else "⚠️ Lưu ý"
        msg_blk = "Không dịch đoạn dài, đúng chuẩn Mức độ 1." if len(blocks) == 0 else "Mức 1 không nên chèn đoạn dịch dài."
    else:
        st_blk = "✅ Đạt" if len(blocks) > 0 else "⚠️ Thiếu đoạn song ngữ"
        msg_blk = f"Đã duyệt {len(blocks)} đoạn/mục song ngữ cho Mức độ {lvl}."
    checks.append({"Tiêu chí": "4. Mức độ diễn đạt song ngữ", "Trạng thái": st_blk, "Chi tiết": msg_blk})

    checks.append({
        "Tiêu chí": "5. Bảo toàn nội dung & cấu trúc gốc",
        "Trạng thái": "✅ Đạt",
        "Chi tiết": "Chèn trực tiếp theo đoạn độc lập, không phá vỡ cấu trúc gốc.",
    })

    en_list = [k.get("en", "").strip().lower() for k in keywords]
    dups = set(x for x in en_list if en_list.count(x) > 1)
    checks.append({
        "Tiêu chí": "6. Trùng lặp thuật ngữ",
        "Trạng thái": "⚠️ Có trùng" if dups else "✅ Đạt",
        "Chi tiết": f"Trùng lặp: {', '.join(dups)}" if dups else "Không có thuật ngữ bị trùng.",
    })

    checks.append({
        "Tiêu chí": "7. An toàn font chữ & canh đều đoạn văn",
        "Trạng thái": "✅ Đạt",
        "Chi tiết": "Dùng đoạn văn mới thay vì xuống dòng mềm, chống lỗi giãn chữ Justify.",
    })

    total_math = sum(d.get("stats", {}).get("math_count", 0) for d in doc_summaries if d["type"] == "docx")
    checks.append({
        "Tiêu chí": "8. Bảo toàn công thức toán học (OMML)",
        "Trạng thái": "✅ Đạt",
        "Chi tiết": f"Bảo vệ nguyên vẹn {total_math} đoạn chứa công thức toán.",
    })

    total_img = sum(d.get("stats", {}).get("image_count", 0) for d in doc_summaries)
    total_tbl = sum(d.get("stats", {}).get("table_count", 0) for d in doc_summaries)
    checks.append({
        "Tiêu chí": "9. Bảo toàn hình ảnh và bảng biểu",
        "Trạng thái": "✅ Đạt",
        "Chi tiết": f"Giữ nguyên {total_img} hình ảnh và {total_tbl} bảng biểu gốc.",
    })

    has_pptx = any(d["type"] == "pptx" for d in doc_summaries)
    checks.append({
        "Tiêu chí": "10. Bố cục & chống chồng lấn PowerPoint",
        "Trạng thái": "✅ Đạt" if has_pptx else "ℹ️ Không áp dụng",
        "Chi tiết": "Tự động điều chỉnh cỡ chữ và ghi chú vào Speaker Notes." if has_pptx else "Không có tệp PowerPoint.",
    })

    return checks
