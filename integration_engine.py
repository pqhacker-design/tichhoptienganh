from typing import Any, Dict, List, Tuple
from word_processor import integrate_word_multi_lesson
from powerpoint_processor import integrate_pptx_multi_lesson


def run_multi_lesson_integration(
    file_bytes: bytes,
    file_type: str,
    lessons: List[Dict[str, Any]],
) -> Tuple[bytes, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Thực hiện tích hợp Multi-Lesson và trả về:
    - out_bytes: file gốc đã tích hợp
    - lesson_reports: báo cáo từng bài
    - completeness: đối chiếu tính đầy đủ trước khi xuất
    """
    if file_type == "docx":
        out_bytes, lesson_reports = integrate_word_multi_lesson(file_bytes, lessons)
    elif file_type == "pptx":
        out_bytes, lesson_reports = integrate_pptx_multi_lesson(file_bytes, lessons)
    else:
        raise ValueError(f"Định dạng không hỗ trợ: {file_type}")

    total_detected = len(lessons)
    total_selected = sum(1 for ls in lessons if ls.get("selected"))
    total_success = sum(1 for r in lesson_reports if r["Trạng thái"] == "Hoàn thành")
    unprocessed = [r["Bài học"] for r in lesson_reports if r["Trạng thái"] == "Chưa phân tích / Chưa duyệt"]

    completeness = {
        "total_detected": total_detected,
        "total_selected": total_selected,
        "total_success": total_success,
        "unprocessed": unprocessed,
        "is_complete": (total_selected > 0) and (total_success == total_selected),
    }
    return out_bytes, lesson_reports, completeness