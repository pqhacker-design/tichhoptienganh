import os
from dotenv import load_dotenv

load_dotenv()

APP_TITLE = "AI BILINGUAL LESSON INTEGRATOR"
APP_SUBTITLE = "Trợ lý tích hợp tiếng Anh vào giáo án Word & PowerPoint (Mức độ 1 – Cơ bản / Làm quen)"

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

# Màu sắc định dạng tích hợp (RGB)
COLOR_ENGLISH_RGB = (0, 102, 204)    # Xanh dương cho tiếng Anh tích hợp
COLOR_IPA_RGB = (128, 0, 128)        # Tím cho phiên âm IPA
COLOR_NOTE_BG_RGB = (240, 247, 255)  # Nền xanh nhạt cho hộp chú thích PPTX

# Khẩu lệnh chuẩn theo 3 nhóm
CLASSROOM_ENGLISH_BANK = {
    "Chào hỏi & Bắt đầu": [
        {"en": "Good morning, class!", "vi": "Chào buổi sáng cả lớp!"},
        {"en": "Let's start our lesson!", "vi": "Chúng ta bắt đầu bài học nhé!"},
        {"en": "Open your notebook!", "vi": "Các em mở vở ra nào!"},
        {"en": "Look at the board!", "vi": "Các em nhìn lên bảng nhé!"},
    ],
    "Điều khiển hoạt động": [
        {"en": "Work in pairs!", "vi": "Làm việc theo cặp nhé!"},
        {"en": "Work in groups!", "vi": "Làm việc theo nhóm nhé!"},
        {"en": "Raise your hand!", "vi": "Giơ tay lên nào!"},
        {"en": "Listen carefully!", "vi": "Lắng nghe thật kỹ nhé!"},
        {"en": "Time's up!", "vi": "Hết giờ rồi!"},
    ],
    "Động viên": [
        {"en": "Good job!", "vi": "Làm tốt lắm!"},
        {"en": "Well done!", "vi": "Xuất sắc lắm!"},
        {"en": "Excellent!", "vi": "Tuyệt vời!"},
        {"en": "Try again!", "vi": "Thử lại lần nữa nhé!"},
    ],
}

# Ánh xạ tiêu đề hoạt động chuẩn Công văn 5512
BILINGUAL_HEADER_MAP = {
    "khởi động": "Warm-up",
    "hình thành kiến thức": "Knowledge Formation",
    "luyện tập": "Practice",
    "vận dụng": "Application",
    "hoạt động nhóm": "Group Work",
    "hoạt động cá nhân": "Individual Work",
    "bài tập về nhà": "Homework",
    "hướng dẫn về nhà": "Homework",
    "từ khóa": "Keywords",
    "mục tiêu": "Learning Objectives",
}