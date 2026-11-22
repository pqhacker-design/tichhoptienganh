import uuid
from typing import Any, Dict
from config import INTEGRATION_LEVELS
from gemini_service import call_gemini_json


def _build_system_instruction(integration_level: int) -> str:
    lvl_cfg = INTEGRATION_LEVELS.get(integration_level, INTEGRATION_LEVELS[1])
    return f"""
Bạn là chuyên gia giáo dục song ngữ theo Chương trình GDPT 2018 và Thông tư số 94/2026/TT-BGDĐT của Việt Nam.
Nhiệm vụ: Phân tích giáo án/bài giảng và đề xuất tích hợp tiếng Anh theo **{lvl_cfg['name']}** ({lvl_cfg['english_ratio']}).

YÊU CẦU BẮT BUỘC CỦA MỨC ĐỘ {integration_level}:
{lvl_cfg['prompt_rules']}

NGUYÊN TẮC CHUNG:
1. Thuật ngữ tiếng Anh phải chính xác tuyệt đối theo chuyên ngành của môn học và phù hợp cấp học (không dịch word-by-word máy móc).
2. Không thêm kiến thức ngoài chương trình hoặc làm sai lệch nội dung chuyên môn gốc.
3. Cung cấp phiên âm IPA chuẩn và gợi ý phát âm ngắn gọn cho giáo viên.
4. Nếu thuật ngữ nào có nhiều cách dịch hoặc cần giáo viên rà soát lại, đặt "needs_teacher_review": true.
5. Trả về ĐÚNG định dạng JSON yêu cầu, không thêm văn bản ngoài JSON.
"""


def _chunk_text(text: str, max_chars: int = 18000) -> str:
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
    integration_level: int = 1,
) -> Dict[str, Any]:
    """Phân tích nội dung bài dạy theo Mức độ 1, 2 hoặc 3."""
    trimmed_text = _chunk_text(combined_text)
    lvl_cfg = INTEGRATION_LEVELS.get(integration_level, INTEGRATION_LEVELS[1])

    prompt = f"""
Thông tin bài dạy:
- Cấp học: {level} - Lớp {grade}
- Môn học: {subject}
- Bộ sách giáo khoa: {textbook}
- Chủ đề: {topic_hint or "Tự xác định từ nội dung"}
- Mức độ tích hợp áp dụng: {lvl_cfg['name']} ({lvl_cfg['english_ratio']})

NỘI DUNG BÀI DẠY:
\"\"\"
{trimmed_text}
\"\"\"

Hãy phân tích và trả về JSON theo đúng cấu trúc sau:
{{
  "integration_level": {integration_level},
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
      "group": "Chào hỏi & Bắt đầu | Điều khiển hoạt động | Chuyển giao nhiệm vụ | Động viên",
      "en": "Câu khẩu lệnh / chỉ dẫn sư phạm tiếng Anh",
      "vi": "Nghĩa tiếng Việt",
      "target_location": "Ví dụ: Hoạt động 1: Khởi động"
    }}
  ],
  "bilingual_headers": [
    {{
      "vi": "Tiêu đề hoạt động gốc trong bài (ví dụ: Khởi động, Luyện tập)",
      "en": "Tiêu đề tiếng Anh tương ứng (ví dụ: Warm-up, Practice)",
      "target_location": "Tiêu đề hoạt động"
    }}
  ],
  "bilingual_blocks": [
    {{
      "section_type": "Mục tiêu | Định nghĩa / Kết luận | Chuyển giao nhiệm vụ | Bài tập / Câu hỏi",
      "vi_anchor": "Trích NGUYÊN VĂN 6–12 từ đầu tiên của đoạn văn tiếng Việt cần chèn bản song ngữ ngay dưới",
      "en_text": "Bản diễn đạt tiếng Anh học thuật tương ứng chuẩn thuật ngữ chuyên ngành",
      "target_location": "Tên phần/hoạt động tương ứng"
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
      "type": "Matching | Trắc nghiệm thuật ngữ | Thảo luận ngắn | Câu hỏi củng cố",
      "title": "Tên hoạt động",
      "content": "Nội dung câu hỏi hoặc hoạt động phù hợp với Mức độ {integration_level}",
      "target_location": "Hoạt động Luyện tập / Vận dụng"
    }}
  ]
}}
"""
    raw = call_gemini_json(
        prompt=prompt,
        system_instruction=_build_system_instruction(integration_level),
    )

    raw["integration_level"] = integration_level

    # Đảm bảo Mức 1 không chèn đoạn dịch dài
    if integration_level == 1:
        raw["bilingual_blocks"] = []

    for key, cat in (
        ("keywords", "keyword"),
        ("classroom_english", "classroom"),
        ("bilingual_headers", "header"),
        ("bilingual_blocks", "bilingual_block"),
        ("diagram_labels", "diagram"),
        ("practice_activities", "practice"),
    ):
        for item in raw.get(key, []):
            item["id"] = str(uuid.uuid4())[:8]
            item["approved"] = True
            item["category"] = cat

    return raw
