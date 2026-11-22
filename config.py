import os
from dotenv import load_dotenv

load_dotenv()

APP_TITLE = "AI BILINGUAL LESSON INTEGRATOR"
APP_SUBTITLE = "Trợ lý tích hợp tiếng Anh (3 mức độ – TT 94/2026/TT-BGDĐT) & Soạn giáo án song ngữ"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

EDUCATION_LEVELS = {
    "Tiểu học": list(range(1, 6)),
    "THCS": list(range(6, 10)),
    "THPT": list(range(10, 13)),
}

SUBJECTS = [
    "Toán",
    "Ngữ văn",
    "Tiếng Anh",
    "Khoa học tự nhiên",
    "Vật lý",
    "Hóa học",
    "Sinh học",
    "Lịch sử",
    "Địa lý",
    "Tin học",
    "Công nghệ",
    "Giáo dục công dân",
    "Giáo dục kinh tế và pháp luật",
    "Giáo dục địa phương",
    "Môn học khác",
]

TEXTBOOKS = [
    "Không lựa chọn",
    "Kết nối tri thức với cuộc sống",
    "Chân trời sáng tạo",
    "Cánh Diều",
]

# 3 mức độ tích hợp theo khung Thông tư số 94/2026/TT-BGDĐT (có thể tinh chỉnh trực tiếp tại đây)
INTEGRATION_LEVELS = {
    1: {
        "name": "Mức độ 1 – Cơ bản / Làm quen",
        "short_label": "Mức độ 1 (5–15% EN)",
        "english_ratio": "5–15% thời lượng/nội dung",
        "keyword_range": (3, 5),
        "classroom_range": (5, 8),
        "description": (
            "Tiếng Việt là ngôn ngữ giảng dạy chính (85–95%). Tích hợp 3–5 thuật ngữ cốt lõi kèm IPA, "
            "khẩu lệnh lớp học quen thuộc, tiêu đề hoạt động song ngữ và 1–2 câu hỏi củng cố ngắn. "
            "Không dịch đoạn giải thích hay định nghĩa dài."
        ),
        "prompt_rules": (
            "- Tiếng Việt chiếm 85–95%, KHÔNG dịch các đoạn văn hay định nghĩa dài.\n"
            "- Chọn đúng 3–5 thuật ngữ cốt lõi nhất kèm IPA.\n"
            "- Chọn 5–8 khẩu lệnh Classroom English ngắn gọn.\n"
            "- Song ngữ hóa tiêu đề hoạt động và đề xuất 1–2 câu hỏi củng cố ngắn.\n"
            "- Mảng `bilingual_blocks` để RỖNG [] ở Mức độ 1."
        ),
    },
    2: {
        "name": "Mức độ 2 – Trung bình / Song ngữ từng phần",
        "short_label": "Mức độ 2 (30–50% EN)",
        "english_ratio": "30–50% thời lượng/nội dung",
        "keyword_range": (6, 10),
        "classroom_range": (6, 10),
        "description": (
            "Kết hợp linh hoạt tiếng Việt và tiếng Anh (30–50% tiếng Anh). Bổ sung 6–10 thuật ngữ & cụm từ "
            "chuyên môn, câu lệnh chuyển giao nhiệm vụ song ngữ và chuyển ngữ song song các phần trọng tâm "
            "(Mục tiêu bài học, Định nghĩa/Định lý/Kết luận cốt lõi, Đề bài luyện tập chính)."
        ),
        "prompt_rules": (
            "- Tỷ lệ tiếng Anh khoảng 30–50% nội dung bài dạy.\n"
            "- Chọn 6–10 thuật ngữ và cụm từ chuyên môn trọng tâm kèm IPA.\n"
            "- Đề xuất 6–10 khẩu lệnh lớp học & câu chuyển giao nhiệm vụ học tập song ngữ.\n"
            "- Điền 4–8 mục vào `bilingual_blocks`: chọn các câu/đoạn trọng tâm trong bài (Mục tiêu, Định nghĩa, "
            "Tính chất, Kết luận, Câu hỏi/Bài tập chính) để cung cấp bản tiếng Anh học thuật chuẩn xác kèm `vi_anchor` "
            "trích nguyên văn 6–12 từ đầu của đoạn gốc."
        ),
    },
    3: {
        "name": "Mức độ 3 – Nâng cao / Chủ yếu bằng tiếng Anh",
        "short_label": "Mức độ 3 (70–100% EN)",
        "english_ratio": "70–100% thời lượng/nội dung",
        "keyword_range": (8, 15),
        "classroom_range": (8, 12),
        "description": (
            "Sử dụng tiếng Anh làm ngôn ngữ giảng dạy chủ đạo (70–100%). Hệ thống thuật ngữ chuyên ngành "
            "đầy đủ, diễn đạt toàn bộ mục tiêu, chỉ dẫn sư phạm, kiến thức trọng tâm, câu hỏi thảo luận "
            "và nhiệm vụ luyện tập – vận dụng bằng tiếng Anh học thuật chuẩn."
        ),
        "prompt_rules": (
            "- Tỷ lệ tiếng Anh đạt 70–100% nội dung giảng dạy.\n"
            "- Chọn 8–15 thuật ngữ chuyên ngành đầy đủ của bài học kèm IPA.\n"
            "- Đề xuất 8–12 câu chỉ dẫn sư phạm, dẫn dắt thảo luận và đánh giá bằng tiếng Anh học thuật.\n"
            "- Điền đầy đủ vào `bilingual_blocks` (8–15 mục trở lên): bao phủ toàn bộ Mục tiêu, Nhiệm vụ các hoạt động, "
            "Nội dung kiến thức trọng tâm, Kết luận và Bài tập luyện tập – vận dụng, đảm bảo mỗi mục có `vi_anchor` "
            "trích nguyên văn 6–12 từ đầu của đoạn gốc để chèn đúng vị trí."
        ),
    },
}

BILINGUAL_DRAFT_MODES = {
    "inline": "Chèn song ngữ trực tiếp trên file Word gốc (giữ nguyên bảng, ảnh, công thức toán)",
    "two_columns": "Tạo file Word song ngữ 2 cột Việt | Anh (khổ ngang A4, kèm bảng thuật ngữ đầu bài)",
}

# Màu sắc định dạng tích hợp (RGB)
COLOR_ENGLISH_RGB = (0, 102, 204)    # Xanh dương cho tiếng Anh tích hợp
COLOR_IPA_RGB = (128, 0, 128)        # Tím cho phiên âm IPA
COLOR_BLOCK_RGB = (0, 90, 156)       # Xanh đậm cho đoạn song ngữ Mức 2 & 3
COLOR_NOTE_BG_RGB = (240, 247, 255)  # Nền xanh nhạt cho hộp chú thích PPTX
