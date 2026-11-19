import json
from typing import Any, Dict, Tuple
import streamlit as st
from google import genai
from google.genai import types
from config import GEMINI_MODEL


def get_api_key() -> str:
    """Chỉ lấy API Key do người dùng nhập trong phiên làm việc hiện tại."""
    return (st.session_state.get("user_api_key") or "").strip()


def get_gemini_client(api_key: str = "") -> genai.Client:
    key = (api_key or get_api_key()).strip()
    if not key:
        raise ValueError(
            "Bạn chưa nhập Gemini API Key. Vui lòng nhập khóa ở thanh bên trái để sử dụng."
        )
    return genai.Client(api_key=key)


def validate_api_key(api_key: str) -> Tuple[bool, str]:
    """Kiểm tra nhanh xem API Key người dùng nhập có hoạt động không."""
    key = (api_key or "").strip()
    if not key:
        return False, "Vui lòng nhập API Key."
    try:
        client = genai.Client(api_key=key)
        client.models.generate_content(
            model=GEMINI_MODEL,
            contents="Reply with OK",
            config=types.GenerateContentConfig(max_output_tokens=5),
        )
        return True, "Kết nối thành công! API Key hợp lệ."
    except Exception as e:
        return False, f"API Key không hợp lệ hoặc đã hết hạn mức: {e}"


def call_gemini_json(
    prompt: str,
    system_instruction: str,
    temperature: float = 0.2,
    max_output_tokens: int = 8192,
) -> Dict[str, Any]:
    """Gọi Gemini API và ép kiểu trả về JSON hợp lệ."""
    client = get_gemini_client()
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
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
        raise RuntimeError(f"Gemini trả về dữ liệu JSON không hợp lệ: {e}")
    except Exception as e:
        raise RuntimeError(f"Lỗi khi gọi Gemini API: {e}")