import json
import time
from typing import Any, Dict, List, Tuple
import streamlit as st
from google import genai
from google.genai import types
from config import GEMINI_MODEL

# Danh sách model dự phòng khi model chính bị quá tải (503/429)
FALLBACK_MODELS: List[str] = [
    GEMINI_MODEL,
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
]


def get_api_key() -> str:
    """Chỉ lấy API Key do người dùng nhập trong phiên làm việc hiện tại."""
    return (st.session_state.get("user_api_key") or "").strip()


def get_gemini_client(api_key: str = "") -> genai.Client:
    key = (api_key or get_api_key()).strip()
    if not key:
        raise ValueError(
            "Bạn chưa nhập Gemini API Key. Vui lòng nhập khóa ở thanh bên trái để sử dụng."
        )
    return genai.Client(
        api_key=key,
        http_options=types.HttpOptions(api_version="v1beta"),
    )


def validate_api_key(api_key: str) -> Tuple[bool, str]:
    """Kiểm tra nhanh xem API Key người dùng nhập có hoạt động không."""
    key = (api_key or "").strip()
    if not key:
        return False, "Vui lòng nhập API Key."
    client = get_gemini_client(key)
    last_err = ""
    for model_name in dict.fromkeys(FALLBACK_MODELS):
        try:
            client.models.generate_content(
                model=model_name,
                contents="Reply with OK",
                config=types.GenerateContentConfig(max_output_tokens=5),
            )
            return True, f"Kết nối thành công! (Đang dùng model: {model_name})"
        except Exception as e:
            last_err = str(e)
            if "503" in last_err or "UNAVAILABLE" in last_err:
                continue
            return False, f"API Key không hợp lệ hoặc đã hết hạn mức: {e}"
    return False, f"Máy chủ Gemini đang quá tải tạm thời, vui lòng thử lại sau: {last_err}"


def call_gemini_json(
    prompt: str,
    system_instruction: str,
    temperature: float = 0.2,
    max_output_tokens: int = 8192,
    retries_per_model: int = 2,
) -> Dict[str, Any]:
    """Gọi Gemini API có tự động retry và chuyển model dự phòng khi gặp lỗi 503/429."""
    client = get_gemini_client()
    models_to_try = list(dict.fromkeys(FALLBACK_MODELS))
    last_error = None

    for model_name in models_to_try:
        for attempt in range(retries_per_model):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                        response_mime_type="application/json",
                    ),
                )
                raw_text = (response.text or "").strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[-1]
                    if raw_text.endswith("```"):
                        raw_text = raw_text[:-3].strip()
                return json.loads(raw_text)

            except json.JSONDecodeError as e:
                last_error = f"Gemini ({model_name}) trả về JSON không hợp lệ: {e}"
                break  # Chuyển model khác

            except Exception as e:
                err_str = str(e)
                last_error = f"[{model_name}] {err_str}"
                # Nếu quá tải (503) hoặc chạm giới hạn tốc độ (429) -> đợi rồi thử lại
                if any(code in err_str for code in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")):
                    time.sleep(2 * (attempt + 1))
                    continue
                # Lỗi khác (ví dụ sai API key) -> dừng ngay
                raise RuntimeError(f"Lỗi khi gọi Gemini API: {e}")

    raise RuntimeError(
        f"Tất cả các model Gemini hiện đang quá tải. Vui lòng thử lại sau 15–30 giây. Chi tiết: {last_error}"
    )
