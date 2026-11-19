import uuid
from typing import Any, Dict, List
from gemini_service import call_gemini_json

SPLITTER_SYSTEM_INSTRUCTION = """
Bạn là chuyên gia phân tích cấu trúc giáo án và bài giảng theo Chương trình GDPT Việt Nam.
Nhiệm vụ: Nhận diện chính xác tài liệu có 1 bài học hay nhiều bài học (nhiều tiết, nhiều chủ đề, nhiều kế hoạch bài dạy ghép liên tiếp).

NGUYÊN TẮC BẮT BUỘC:
1. KHÔNG chỉ dựa vào từ khóa "Bài 1", "Bài 2". Phải kết hợp phân tích tiêu đề, cấu trúc mục tiêu/tiến trình dạy học và sự chuyển đổi chủ đề kiến thức.
2. Mọi phần tử (block trong Word hoặc slide trong PowerPoint) thuộc bài nào phải nằm gọn trong phạm vi [start_index, end_index] của bài đó.
3. Không bỏ sót bài nào, không để chồng lấn ranh giới giữa hai bài.
4. Đánh giá độ tin cậy của việc phân chia: "high" (rõ ràng), "medium" (khá rõ), "low" (không chắc chắn, cần giáo viên xác nhận lại).
5. Trả về đúng định dạng JSON.
"""


def _build_outline_for_word(ordered_blocks: List[Dict[str, Any]]) -> str:
    """Tạo bản tóm tắt theo thứ tự block_index để Gemini nhận diện ranh giới bài học."""
    lines = []
    for blk in ordered_blocks:
        idx = blk["block_index"]
        kind = "BẢNG" if blk["kind"] == "table" else "ĐOẠN"
        style = f" ({blk['style']})" if blk.get("style") else ""
        preview = blk["text"][:180].replace("\n", " | ")
        lines.append(f"[Block {idx}] {kind}{style}: {preview}")
    text = "\n".join(lines)
    return text[:28000]  # Đủ rộng cho giáo án nhiều bài


def _build_outline_for_pptx(slides: List[Dict[str, Any]]) -> str:
    lines = []
    for s in slides:
        s_num = s["slide_number"]
        title = s.get("title") or "(Không có tiêu đề)"
        body = " | ".join(s.get("texts", []))[:180].replace("\n", " ")
        lines.append(f"[Slide {s_num}] Tiêu đề: {title} || Nội dung: {body}")
    return "\n".join(lines)[:24000]


def detect_lessons_in_document(parsed_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phân tích tài liệu Word hoặc PowerPoint để phân chia danh sách bài học độc lập.
    """
    doc_type = parsed_doc["type"]
    if doc_type == "docx":
        blocks = parsed_doc["ordered_blocks"]
        total_units = len(blocks)
        if total_units == 0:
            return {"needs_confirmation": True, "lessons": []}
        outline = _build_outline_for_word(blocks)
        unit_name = "block_index (bắt đầu từ 0 đến " + str(total_units - 1) + ")"
    else:
        slides = parsed_doc["slides"]
        total_units = len(slides)
        if total_units == 0:
            return {"needs_confirmation": True, "lessons": []}
        outline = _build_outline_for_pptx(slides)
        unit_name = "slide_number (bắt đầu từ 1 đến " + str(total_units) + ")"

    prompt = f"""
Hãy phân tích mục lục/khung nội dung của tệp `{parsed_doc['filename']}` (loại: {doc_type}) dưới đây để xác định các bài học độc lập.
Đơn vị đánh chỉ số là: {unit_name}.

KHUNG NỘI DUNG TÀI LIỆU:
\"\"\"
{outline}
\"\"\"

Trả về JSON theo đúng cấu trúc:
{{
  "total_lessons": 2,
  "needs_confirmation": false,
  "confirmation_reason": "Lý do nếu needs_confirmation = true, ngược lại để trống",
  "lessons": [
    {{
      "title": "Tên đầy đủ của bài học (ví dụ: Bài 1: Đơn thức)",
      "start_index": 0,
      "end_index": 25,
      "confidence": "high | medium | low",
      "detected_sections": ["Mục tiêu", "Khởi động", "Hình thành kiến thức", "Luyện tập"]
    }}
  ]
}}
"""
    result = call_gemini_json(prompt=prompt, system_instruction=SPLITTER_SYSTEM_INSTRUCTION)
    lessons = result.get("lessons", [])

    # Chuẩn hóa & đảm bảo an toàn chỉ số
    min_idx = 0 if doc_type == "docx" else 1
    max_idx = (total_units - 1) if doc_type == "docx" else total_units

    normalized_lessons = []
    for i, ls in enumerate(lessons):
        s_idx = max(min_idx, min(max_idx, int(ls.get("start_index", min_idx))))
        e_idx = max(s_idx, min(max_idx, int(ls.get("end_index", max_idx))))
        normalized_lessons.append({
            "lesson_id": str(uuid.uuid4())[:8],
            "order": i + 1,
            "title": ls.get("title", f"Bài {i + 1}"),
            "start_index": s_idx,
            "end_index": e_idx,
            "confidence": ls.get("confidence", "medium"),
            "detected_sections": ls.get("detected_sections", []),
            "selected": True,       # Giáo viên có thể bỏ chọn bài không muốn tích hợp
            "status": "Chưa phân tích",
            "analysis": None,       # Chứa kết quả phân tích riêng của bài này
        })

    # Nếu Gemini không tách được bài nào, tạo mặc định 1 bài bao trọn tài liệu và yêu cầu xác nhận
    if not normalized_lessons:
        normalized_lessons.append({
            "lesson_id": str(uuid.uuid4())[:8],
            "order": 1,
            "title": f"Bài 1 ({parsed_doc['filename']})",
            "start_index": min_idx,
            "end_index": max_idx,
            "confidence": "low",
            "detected_sections": [],
            "selected": True,
            "status": "Chưa phân tích",
            "analysis": None,
        })
        result["needs_confirmation"] = True
        result["confirmation_reason"] = "Không xác định rõ ranh giới bài học, vui lòng kiểm tra lại."

    # Bắt buộc xác nhận nếu có bất kỳ bài nào độ tin cậy thấp
    if any(ls["confidence"] == "low" for ls in normalized_lessons):
        result["needs_confirmation"] = True

    return {
        "total_lessons": len(normalized_lessons),
        "needs_confirmation": bool(result.get("needs_confirmation", False)),
        "confirmation_reason": result.get("confirmation_reason", ""),
        "lessons": normalized_lessons,
    }


def extract_lesson_text(parsed_doc: Dict[str, Any], start_index: int, end_index: int) -> str:
    """Trích xuất đúng văn bản thuộc phạm vi [start_index, end_index] của một bài học."""
    if parsed_doc["type"] == "docx":
        lines = []
        for blk in parsed_doc["ordered_blocks"]:
            if start_index <= blk["block_index"] <= end_index:
                lines.append(blk["text"])
        return "\n".join(lines)
    else:
        lines = []
        for s in parsed_doc["slides"]:
            if start_index <= s["slide_number"] <= end_index:
                lines.append(f"=== SLIDE {s['slide_number']} ===")
                if s["title"]:
                    lines.append(f"Tiêu đề: {s['title']}")
                lines.extend(s["texts"])
                if s["notes"]:
                    lines.append(f"Ghi chú: {s['notes']}")
        return "\n".join(lines)