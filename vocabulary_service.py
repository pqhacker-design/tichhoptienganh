import io
from typing import Any, Dict, List
import pandas as pd

# Kho thuật ngữ mẫu cốt lõi theo môn học (có thể mở rộng thêm từ bài phân tích)
BUILTIN_DICTIONARY: List[Dict[str, str]] = [
    {"subject": "Toán", "level": "THCS", "vi": "Tam giác cân", "en": "Isosceles triangle", "ipa": "/aɪˈsɒs.ə.liːz ˈtraɪ.æŋ.ɡəl/", "example": "An isosceles triangle has two equal sides."},
    {"subject": "Toán", "level": "THCS", "vi": "Cạnh đáy", "en": "Base", "ipa": "/beɪs/", "example": "BC is the base of triangle ABC."},
    {"subject": "Toán", "level": "THCS", "vi": "Góc ở đỉnh", "en": "Vertex angle", "ipa": "/ˈvɜː.teks ˈæŋ.ɡəl/", "example": "Angle A is the vertex angle."},
    {"subject": "Toán", "level": "THCS", "vi": "Phương trình bậc nhất", "en": "Linear equation", "ipa": "/ˈlɪn.i.ər ɪˈkweɪ.ʒən/", "example": "Solve the linear equation 2x + 3 = 7."},
    {"subject": "Khoa học tự nhiên", "level": "THCS", "vi": "Quang hợp", "en": "Photosynthesis", "ipa": "/ˌfəʊ.təʊˈsɪn.θə.sɪs/", "example": "Plants make food through photosynthesis."},
    {"subject": "Vật lý", "level": "THCS", "vi": "Vận tốc", "en": "Velocity", "ipa": "/vəˈlɒs.ə.ti/", "example": "Calculate the average velocity of the car."},
    {"subject": "Hóa học", "level": "THCS", "vi": "Phản ứng hóa học", "en": "Chemical reaction", "ipa": "/ˈkem.ɪ.kəl riˈæk.ʃən/", "example": "Burning wood is a chemical reaction."},
    {"subject": "Sinh học", "level": "THCS", "vi": "Tế bào", "en": "Cell", "ipa": "/sel/", "example": "The cell is the basic unit of life."},
    {"subject": "Tin học", "level": "THCS", "vi": "Thuật toán", "en": "Algorithm", "ipa": "/ˈæl.ɡə.rɪ.ðəm/", "example": "Write an algorithm to sort the list."},
    {"subject": "Địa lý", "level": "THCS", "vi": "Khí hậu nhiệt đới", "en": "Tropical climate", "ipa": "/ˈtrɒp.ɪ.kəl ˈklaɪ.mət/", "example": "Vietnam has a tropical monsoon climate."},
    {"subject": "Lịch sử", "level": "THCS", "vi": "Cách mạng công nghiệp", "en": "Industrial Revolution", "ipa": "/ɪnˈdʌs.tri.əl ˌrev.əˈluː.ʃən/", "example": "The Industrial Revolution began in Britain."},
]


def search_dictionary(query: str, subject: str = "Tất cả", custom_terms: List[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    all_terms = list(BUILTIN_DICTIONARY)
    if custom_terms:
        all_terms.extend(custom_terms)

    q = (query or "").strip().lower()
    results = []
    for item in all_terms:
        if subject != "Tất cả" and item.get("subject") != subject:
            continue
        if not q or q in item.get("vi", "").lower() or q in item.get("en", "").lower():
            results.append(item)
    return results


def export_keywords_to_excel(keywords: List[Dict[str, Any]]) -> bytes:
    rows = []
    for k in keywords:
        rows.append({
            "Tiếng Việt": k.get("vi", ""),
            "Tiếng Anh": k.get("en", ""),
            "Phiên âm IPA": k.get("ipa", ""),
            "Gợi ý phát âm": k.get("pronunciation_tip", ""),
            "Nghĩa chuyên môn": k.get("context_meaning", ""),
            "Vị trí tích hợp": k.get("target_location", ""),
        })
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Keywords")
    return buf.getvalue()