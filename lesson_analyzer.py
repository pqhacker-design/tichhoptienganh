import uuid
from typing import Any, Dict, List
from gemini_service import call_gemini_json

SYSTEM_INSTRUCTION = """
Bạn là chuyên gia giáo dục song ngữ theo Chương trình GDPT 2018 của Việt Nam.
Nhiệm vụ: Phân tích giáo án/bài giảng và đề xuất tích hợp tiếng Anh theo MỨC ĐỘ 1 (Cơ bản / Làm quen).

NGUYÊN TẮC BẮT BUỘC:
1. Tiếng Việt chiếm 85–95%, KHÔNG dịch toàn bộ giáo án hay định nghĩa dài.
2. Chỉ chọn từ 3 đến 5 thuật ngữ chuyên môn cốt lõi nhất, chính xác theo ngữ cảnh môn học và phù hợp cấp học.
3. Chọn 5–8 khẩu lệnh lớp học (Classroom English) ngắn gọn, phù hợp với các hoạt động thực tế trong bài.
4. Đề xuất tiêu đề song ngữ cho các hoạt động có trong bài (giữ nguyên tiếng Việt, thêm tiếng Anh).
5. Đề xuất chú thích/nhãn tiếng Anh cho hình vẽ/sơ đồ (nếu có) và 1–2 câu hỏi/hoạt động củng cố ngắn.
6. Cung cấp phiên âm IPA chuẩn (Anh-Anh hoặc Anh-Mỹ) và hướng dẫn đọc dễ hiểu cho giáo viên Việt Nam.
7. Nếu thuật ngữ nào có thể gây nhầm lẫn chuyên môn, đặt "needs_teacher_review": true.
8. Trả về ĐÚNG định dạng JSON yêu cầu, không thêm văn bản thừa.
"""


def _chunk_text(text: str, max_chars: int = 18000) -> str:
    """Tối ưu độ dài văn bản gửi lên Gemini để tiết kiệm token mà vẫn giữ đủ trọng tâm."""
    if len(text) <= max_chars:
        return text
    head = text[: int(max_chars * 0.7)]
    tail = text[-int(max_chars * 0.25) :]
    return head + "\n\n[... ĐÃ LƯỢC BỚT PHẦN GIỮA DO TÀI LIỆU DÀI ...]\n\n" + tail


def analyze_lesson_content(
    combined_text: str,
    level: str,
    grade: int,
    subject: str,
    textbook: str,
    topic_hint: str = "",
) -> Dict[str, Any]:
    """Gửi nội dung giáo án cho Gemini phân tích và chuẩn hóa dữ liệu duyệt."""
    trimmed_text = _chunk_text(combined_text)

    prompt = f"""
Thông tin bài dạy:
- Cấp học: {level} - Lớp {grade}
- Môn học: {subject}
- Bộ sách giáo khoa: {textbook}
- Chủ đề (nếu giáo viên nhập): {topic_hint or "Tự xác định từ nội dung"}

NỘI DUNG TÀI LIỆU:
\"\"\"
{trimmed_text}
\"\"\"

Hãy phân tích và trả về JSON theo đúng cấu trúc sau:
{{
  "lesson_topic": "Tên chủ đề bài học",
  "core_knowledge": ["Kiến thức trọng tâm 1", "Kiến thức trọng tâm 2"],
  "keywords": [
    {{
      "vi": "Thuật ngữ tiếng Việt xuất hiện nguyên văn trong tài liệu",
      "en": "Thuật ngữ tiếng Anh chuẩn chuyên môn",
      "ipa": "/phiên âm IPA/",
      "pronunciation_tip": "Gợi ý đọc ngắn gọn",
      "context_meaning": "Nghĩa theo ngữ cảnh môn học",
      "target_location": "Ví dụ: Tiêu đề bài / Hình thành kiến thức / Slide 2",
      "repeat_locations": ["Luyện tập", "Củng cố"],
      "needs_teacher_review": false
    }}
  ],
  "classroom_english": [
    {{
      "group": "Chào hỏi & Bắt đầu | Điều khiển hoạt động | Động viên",
      "en": "Câu khẩu lệnh tiếng Anh",
      "vi": "Nghĩa tiếng Việt",
      "target_location": "Ví dụ: Hoạt động 1: Khởi động (Hoạt động của GV)"
    }}
  ],
  "bilingual_headers": [
    {{
      "vi": "Tiêu đề hoạt động gốc trong bài (ví dụ: Khởi động, Luyện tập)",
      "en": "Tiêu đề tiếng Anh tương ứng (ví dụ: Warm-up, Practice)",
      "target_location": "Tiêu đề hoạt động"
    }}
  ],
  "diagram_labels": [
    {{
      "vi": "Tên thành phần hình vẽ/sơ đồ",
      "en": "Nhãn tiếng Anh",
      "target_location": "Hình vẽ / Slide minh họa"
    }}
  ],
  "practice_activities": [
    {{
      "type": "Matching | Trắc nghiệm thuật ngữ | Phát âm đồng thanh | Câu hỏi củng cố",
      "title": "Tên hoạt động ngắn",
      "content": "Nội dung câu hỏi hoặc trò chơi ngắn (1-2 câu) dùng đúng các thuật ngữ đã chọn",
      "target_location": "Hoạt động Luyện tập / Vận dụng"
    }}
  ]
}}
"""
    raw = call_gemini_json(prompt=prompt, system_instruction=SYSTEM_INSTRUCTION)

    # Gắn ID duy nhất và trạng thái mặc định approved=True để giáo viên kiểm duyệt
    for kw in raw.get("keywords", []):
        kw["id"] = str(uuid.uuid4())[:8]
        kw["approved"] = True
        kw["category"] = "keyword"

    for cmd in raw.get("classroom_english", []):
        cmd["id"] = str(uuid.uuid4())[:8]
        cmd["approved"] = True
        cmd["category"] = "classroom"

    for hdr in raw.get("bilingual_headers", []):
        hdr["id"] = str(uuid.uuid4())[:8]
        hdr["approved"] = True
        hdr["category"] = "header"

    for lbl in raw.get("diagram_labels", []):
        lbl["id"] = str(uuid.uuid4())[:8]
        lbl["approved"] = True
        lbl["category"] = "diagram"

    for act in raw.get("practice_activities", []):
        act["id"] = str(uuid.uuid4())[:8]
        act["approved"] = True
        act["category"] = "practice"

    return raw