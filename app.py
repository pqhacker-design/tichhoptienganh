import copy
import uuid
import pandas as pd
import streamlit as st

from config import APP_TITLE, APP_SUBTITLE, EDUCATION_LEVELS, SUBJECTS, TEXTBOOKS
from document_reader import read_word_document, read_pptx_document
from lesson_splitter import detect_lessons_in_document, extract_lesson_text
from lesson_analyzer import analyze_lesson_content
from integration_engine import run_multi_lesson_integration
from pronunciation_service import generate_pronunciation_mp3
from vocabulary_service import search_dictionary, export_keywords_to_excel
from quality_checker import run_quality_check
from export_service import get_output_filename, export_quality_report_docx
from gemini_service import validate_api_key

st.set_page_config(page_title=APP_TITLE, page_icon="📘", layout="wide")


def init_state():
    defaults = {
        "uploaded_docs": {},
        "processed_count": 0,
        "user_api_key": "",
        "api_key_valid": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()

# --- SIDEBAR ---
with st.sidebar:
    st.title("📘 AI Bilingual")
    st.caption("Mức độ 1 – Multi-Lesson")
    st.divider()

    st.markdown("### 🔑 Cấu hình Gemini API Key")
    api_input = st.text_input(
        "Nhập API Key của bạn",
        type="password",
        value=st.session_state["user_api_key"],
        placeholder="AIzaSy...",
        help="Khóa chỉ được lưu tạm trong phiên trình duyệt hiện tại, không lưu lên máy chủ.",
    )

    if api_input != st.session_state["user_api_key"]:
        st.session_state["user_api_key"] = api_input.strip()
        st.session_state["api_key_valid"] = False

    c_btn1, c_btn2 = st.columns(2)
    if c_btn1.button("✅ Kiểm tra", use_container_width=True):
        with st.spinner("Đang kiểm tra..."):
            ok, msg = validate_api_key(st.session_state["user_api_key"])
            st.session_state["api_key_valid"] = ok
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    if c_btn2.button("🗑️ Xóa Key", use_container_width=True):
        st.session_state["user_api_key"] = ""
        st.session_state["api_key_valid"] = False
        st.rerun()

    if st.session_state["api_key_valid"]:
        st.caption("🟢 Trạng thái: **Đã kết nối**")
    elif st.session_state["user_api_key"]:
        st.caption("🟡 Trạng thái: **Đã nhập (chưa kiểm tra)**")
    else:
        st.caption("🔴 Trạng thái: **Chưa nhập API Key**")
        st.markdown("[👉 Lấy API Key tại Google AI Studio](https://aistudio.google.com/app/apikey)")

    st.divider()
    nav = st.radio(
        "Điều hướng",
        [
            "1. Trang chủ",
            "2. Tải tài liệu",
            "3. Phân tích & Tích hợp",
            "4. Kiểm duyệt nội dung",
            "5. Xuất tài liệu",
            "6. Từ điển chuyên ngành",
        ],
    )
    st.divider()
    st.metric("Tài liệu đã tải", len(st.session_state["uploaded_docs"]))
    st.metric("Tài liệu đã xuất", st.session_state["processed_count"])


# ==================== 1. TRANG CHỦ ====================
if nav == "1. Trang chủ":
    st.title(APP_TITLE)
    st.subheader(APP_SUBTITLE)
    st.info(
        "Ứng dụng hỗ trợ giáo viên từ lớp 1 đến lớp 12 tích hợp tiếng Anh trực tiếp vào "
        "giáo án Word (.docx) và bài giảng PowerPoint (.pptx) có sẵn (hỗ trợ cả **1 bài** hoặc **nhiều bài trong cùng 1 tệp**), "
        "**giữ nguyên 100% bố cục, công thức toán học, bảng biểu và hình ảnh gốc**."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 🎯 Nguyên tắc Mức độ 1")
        st.markdown(
            "- Tiếng Việt chiếm **85–95%**.\n"
            "- Mỗi bài chọn **3–5 thuật ngữ cốt lõi** riêng.\n"
            "- Không dịch cả đoạn văn hay định nghĩa dài.\n"
            "- Giáo viên kiểm duyệt trước khi xuất."
        )
    with col2:
        st.markdown("### 🧩 Xử lý nhiều bài học")
        st.markdown(
            "- Tự động nhận diện & phân chia từng bài.\n"
            "- Phân tích bộ từ khóa độc lập cho mỗi bài.\n"
            "- Chọn tích hợp 1 bài, một số bài hoặc tất cả.\n"
            "- Không lẫn thuật ngữ giữa các bài."
        )
    with col3:
        st.markdown("### 🛡️ An toàn định dạng")
        st.markdown(
            "- Chỉnh sửa trực tiếp (**In-place**) trên file gốc.\n"
            "- Chữ tiếng Anh màu **xanh dương**, IPA màu **tím**.\n"
            "- Xuất file mới `_Bilingual.docx` / `.pptx`."
        )


# ==================== 2. TẢI TÀI LIỆU ====================
elif nav == "2. Tải tài liệu":
    st.header("📂 Tải giáo án Word & Bài giảng PowerPoint")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        level = st.selectbox("Cấp học", list(EDUCATION_LEVELS.keys()), key="sel_level")
    with c2:
        grade = st.selectbox("Lớp", EDUCATION_LEVELS[level], key="sel_grade")
    with c3:
        subject = st.selectbox("Môn học", SUBJECTS, key="sel_subject")
    with c4:
        textbook = st.selectbox("Bộ sách giáo khoa", TEXTBOOKS, key="sel_textbook")

    uploaded_files = st.file_uploader(
        "Tải lên đồng thời hoặc riêng biệt file Word (.docx) và PowerPoint (.pptx)",
        type=["docx", "pptx"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        for uf in uploaded_files:
            if uf.name not in st.session_state["uploaded_docs"]:
                file_bytes = uf.read()
                ext = uf.name.rsplit(".", 1)[-1].lower()
                try:
                    parsed = read_word_document(file_bytes, uf.name) if ext == "docx" else read_pptx_document(file_bytes, uf.name)
                    st.session_state["uploaded_docs"][uf.name] = {
                        "bytes": file_bytes,
                        "size_kb": round(len(file_bytes) / 1024, 1),
                        "type": ext,
                        "parsed": parsed,
                    }
                except Exception as e:
                    st.error(f"Không thể đọc tệp {uf.name}: {e}")

    if st.session_state["uploaded_docs"]:
        st.subheader("Danh sách tệp đã nạp")
        for fname in list(st.session_state["uploaded_docs"].keys()):
            info = st.session_state["uploaded_docs"][fname]
            stats = info["parsed"]["stats"]
            cols = st.columns([4, 1.5, 3, 1])
            cols[0].write(f"📄 **{fname}**")
            cols[1].write(f"{info['size_kb']} KB")
            if info["type"] == "docx":
                cols[2].write(
                    f"✅ {stats['total_blocks']} khối | {stats['table_count']} bảng | "
                    f"{stats['math_count']} công thức | {stats['image_count']} ảnh"
                )
            else:
                cols[2].write(
                    f"✅ {stats['slide_count']} slide | {stats['table_count']} bảng | {stats['image_count']} ảnh"
                )
            if cols[3].button("🗑️ Xóa", key=f"del_{fname}"):
                del st.session_state["uploaded_docs"][fname]
                st.rerun()
    else:
        st.info("Hãy tải lên ít nhất 1 file `.docx` hoặc `.pptx` để bắt đầu.")


# ==================== 3. PHÂN TÍCH & TÍCH HỢP (MULTI-LESSON) ====================
elif nav == "3. Phân tích & Tích hợp":
    st.header("🧩 Nhận diện & Phân tích từng bài học (Multi-Lesson)")

    if not st.session_state["uploaded_docs"]:
        st.warning("Vui lòng tải tài liệu ở mục **2. Tải tài liệu** trước.")
    else:
        fname = st.selectbox("Chọn tài liệu cần xử lý", list(st.session_state["uploaded_docs"].keys()))
        doc_entry = st.session_state["uploaded_docs"][fname]
        parsed = doc_entry["parsed"]

        if st.button("🔍 Bước 1: Tự động nhận diện & phân chia bài học", type="primary"):
            with st.spinner("Gemini AI đang phân tích cấu trúc tài liệu để tách các bài học..."):
                try:
                    split_res = detect_lessons_in_document(parsed)
                    doc_entry["split_info"] = split_res
                    st.success(f"Đã nhận diện được **{split_res['total_lessons']} bài học** trong `{fname}`.")
                except Exception as e:
                    st.error(f"Lỗi khi nhận diện bài học: {e}")

        split_info = doc_entry.get("split_info")
        if split_info:
            if split_info.get("needs_confirmation"):
                st.warning(
                    f"⚠️ Cần giáo viên xác nhận ranh giới bài học: {split_info.get('confirmation_reason', 'Độ tin cậy phân chia thấp')}"
                )

            st.subheader(f"📋 Danh sách bài học trong: {fname}")
            unit_label = "Block" if parsed["type"] == "docx" else "Slide"
            max_u = max(0, parsed["stats"]["total_blocks"] - 1) if parsed["type"] == "docx" else max(1, parsed["stats"]["slide_count"])
            min_u = 0 if parsed["type"] == "docx" else 1

            for ls in split_info["lessons"]:
                c1, c2, c3, c4, c5 = st.columns([0.6, 3.2, 1.3, 1.3, 1.6])
                ls["selected"] = c1.checkbox("", value=ls["selected"], key=f"sel_{fname}_{ls['lesson_id']}")
                ls["title"] = c2.text_input("Tên bài", ls["title"], key=f"ttl_{fname}_{ls['lesson_id']}", label_visibility="collapsed")
                ls["start_index"] = c3.number_input(
                    f"{unit_label} đầu", min_value=min_u, max_value=max_u, value=ls["start_index"], key=f"st_{fname}_{ls['lesson_id']}"
                )
                ls["end_index"] = c4.number_input(
                    f"{unit_label} cuối", min_value=ls["start_index"], max_value=max_u, value=max(ls["start_index"], ls["end_index"]), key=f"en_{fname}_{ls['lesson_id']}"
                )
                c5.caption(f"Độ tin cậy: **{ls['confidence']}**\n\nTrạng thái: `{ls['status']}`")

            st.divider()
            level = st.session_state.get("sel_level", "THCS")
            grade = st.session_state.get("sel_grade", 8)
            subject = st.session_state.get("sel_subject", "Toán")
            textbook = st.session_state.get("sel_textbook", "Kết nối tri thức với cuộc sống")

            if st.button("✨ Bước 2: Phân tích tiếng Anh cho TẤT CẢ bài đã chọn", type="primary"):
                selected_lessons = [ls for ls in split_info["lessons"] if ls["selected"]]
                if not selected_lessons:
                    st.warning("Vui lòng chọn ít nhất 1 bài học để phân tích.")
                else:
                    bar = st.progress(0, text="Đang phân tích từng bài học...")
                    for i, ls in enumerate(selected_lessons):
                        bar.progress(int((i / len(selected_lessons)) * 90) + 5, text=f"Đang phân tích: {ls['title']}...")
                        try:
                            ls_text = extract_lesson_text(parsed, ls["start_index"], ls["end_index"])
                            ls["analysis"] = analyze_lesson_content(ls_text, level, grade, subject, textbook, topic_hint=ls["title"])
                            ls["status"] = "Đã phân tích"
                        except Exception as e:
                            ls["status"] = f"Lỗi: {e}"
                    bar.progress(100, text="Hoàn tất phân tích!")
                    st.success("Đã phân tích xong! Chuyển sang mục **4. Kiểm duyệt nội dung** để duyệt từng bài.")


# ==================== 4. KIỂM DUYỆT NỘI DUNG (THEO TỪNG BÀI) ====================
elif nav == "4. Kiểm duyệt nội dung":
    st.header("✅ Quản lý & Kiểm duyệt từng bài học")

    docs_with_splits = [fn for fn, d in st.session_state["uploaded_docs"].items() if d.get("split_info")]
    if not docs_with_splits:
        st.warning("Chưa có tài liệu nào được phân chia bài học. Vui lòng thực hiện ở mục **3. Phân tích & Tích hợp**.")
    else:
        fname = st.selectbox("Chọn tài liệu", docs_with_splits)
        doc_entry = st.session_state["uploaded_docs"][fname]
        lessons = doc_entry["split_info"]["lessons"]

        lesson_titles = [f"{'☑️' if ls['selected'] else '⬜'} {ls['title']} ({ls['status']})" for ls in lessons]
        sel_idx = st.selectbox("Chọn bài học cần kiểm duyệt", range(len(lessons)), format_func=lambda i: lesson_titles[i])
        ls = lessons[sel_idx]

        with st.expander("📄 Xem nội dung bài gốc (trong phạm vi đã nhận diện)"):
            st.text(extract_lesson_text(doc_entry["parsed"], ls["start_index"], ls["end_index"])[:3000])

        if not ls.get("analysis"):
            st.info("Bài học này chưa được phân tích.")
            if st.button(f"✨ Phân tích riêng bài: {ls['title']}", type="primary"):
                with st.spinner("Đang phân tích bài học..."):
                    ls_text = extract_lesson_text(doc_entry["parsed"], ls["start_index"], ls["end_index"])
                    ls["analysis"] = analyze_lesson_content(
                        ls_text,
                        st.session_state.get("sel_level", "THCS"),
                        st.session_state.get("sel_grade", 8),
                        st.session_state.get("sel_subject", "Toán"),
                        st.session_state.get("sel_textbook", "Kết nối tri thức với cuộc sống"),
                        topic_hint=ls["title"],
                    )
                    ls["status"] = "Đã phân tích"
                    st.rerun()
        else:
            res = ls["analysis"]
            accent = st.radio("Giọng phát âm:", ["US (Anh-Mỹ)", "UK (Anh-Anh)"], horizontal=True)
            acc_code = "UK" if "UK" in accent else "US"

            st.subheader(f"1. Thuật ngữ cốt lõi – {ls['title']}")
            for kw in res.get("keywords", []):
                c1, c2, c3, c4, c5 = st.columns([2.2, 2.2, 1.8, 1, 1])
                kw["vi"] = c1.text_input("VI", kw["vi"], key=f"vi_{ls['lesson_id']}_{kw['id']}", label_visibility="collapsed")
                kw["en"] = c2.text_input("EN", kw["en"], key=f"en_{ls['lesson_id']}_{kw['id']}", label_visibility="collapsed")
                kw["ipa"] = c3.text_input("IPA", kw.get("ipa", ""), key=f"ipa_{ls['lesson_id']}_{kw['id']}", label_visibility="collapsed")
                kw["approved"] = c4.checkbox("Duyệt", value=kw["approved"], key=f"ok_{ls['lesson_id']}_{kw['id']}")
                if c5.button("🔊", key=f"snd_{ls['lesson_id']}_{kw['id']}_{acc_code}"):
                    st.audio(generate_pronunciation_mp3(kw["en"], accent=acc_code), format="audio/mp3")

            with st.expander("➕ Thêm thuật ngữ thủ công cho bài này"):
                mc1, mc2, mc3 = st.columns(3)
                m_vi = mc1.text_input("Tiếng Việt", key=f"mvi_{ls['lesson_id']}")
                m_en = mc2.text_input("Tiếng Anh", key=f"men_{ls['lesson_id']}")
                m_ipa = mc3.text_input("IPA (tùy chọn)", key=f"mipa_{ls['lesson_id']}")
                if st.button("Thêm thuật ngữ", key=f"madd_{ls['lesson_id']}"):
                    if m_vi and m_en:
                        res.setdefault("keywords", []).append({
                            "id": str(uuid.uuid4())[:8],
                            "vi": m_vi.strip(),
                            "en": m_en.strip(),
                            "ipa": m_ipa.strip(),
                            "pronunciation_tip": "",
                            "context_meaning": "Giáo viên bổ sung thủ công",
                            "target_location": ls["title"],
                            "approved": True,
                            "needs_teacher_review": False,
                        })
                        st.rerun()

            st.subheader("2. Tiêu đề hoạt động song ngữ")
            for hdr in res.get("bilingual_headers", []):
                c1, c2, c3 = st.columns([3, 3, 1.5])
                hdr["vi"] = c1.text_input("Gốc", hdr["vi"], key=f"hvi_{ls['lesson_id']}_{hdr['id']}", label_visibility="collapsed")
                hdr["en"] = c2.text_input("EN", hdr["en"], key=f"hen_{ls['lesson_id']}_{hdr['id']}", label_visibility="collapsed")
                hdr["approved"] = c3.checkbox("Duyệt", value=hdr["approved"], key=f"hok_{ls['lesson_id']}_{hdr['id']}")

            st.subheader("3. Khẩu lệnh lớp học (Classroom English)")
            for cmd in res.get("classroom_english", []):
                c1, c2, c3 = st.columns([3, 3, 1.5])
                cmd["en"] = c1.text_input("EN", cmd["en"], key=f"cen_{ls['lesson_id']}_{cmd['id']}", label_visibility="collapsed")
                cmd["vi"] = c2.text_input("VI", cmd["vi"], key=f"cvi_{ls['lesson_id']}_{cmd['id']}", label_visibility="collapsed")
                cmd["approved"] = c3.checkbox("Duyệt", value=cmd["approved"], key=f"cok_{ls['lesson_id']}_{cmd['id']}")

            st.subheader("4. Kiểm tra chất lượng bài đang chọn")
            checks = run_quality_check(res, [doc_entry["parsed"]])
            st.dataframe(pd.DataFrame(checks), use_container_width=True, hide_index=True)


# ==================== 5. XUẤT TÀI LIỆU & BÁO CÁO TỪNG BÀI ====================
elif nav == "5. Xuất tài liệu":
    st.header("📥 Tích hợp trực tiếp & Báo cáo kết quả theo từng bài")

    docs_with_splits = [fn for fn, d in st.session_state["uploaded_docs"].items() if d.get("split_info")]
    if not docs_with_splits:
        st.warning("Chưa có tài liệu nào sẵn sàng xuất.")
    else:
        fname = st.selectbox("Chọn tài liệu xuất", docs_with_splits)
        doc_entry = st.session_state["uploaded_docs"][fname]
        lessons = doc_entry["split_info"]["lessons"]

        if st.button("🚀 Tích hợp các bài đã chọn vào file gốc", type="primary"):
            with st.spinner("Đang tích hợp trực tiếp vào đúng vị trí từng bài trên file gốc..."):
                out_bytes, lesson_reports, completeness = run_multi_lesson_integration(
                    doc_entry["bytes"], doc_entry["type"], lessons
                )
                doc_entry["export_result"] = {
                    "bytes": out_bytes,
                    "lesson_reports": lesson_reports,
                    "completeness": completeness,
                }
                st.session_state["processed_count"] += 1

        exp = doc_entry.get("export_result")
        if exp:
            comp = exp["completeness"]
            m1, m2, m3 = st.columns(3)
            m1.metric("Tổng bài nhận diện", comp["total_detected"])
            m2.metric("Số bài giáo viên chọn", comp["total_selected"])
            m3.metric("Số bài tích hợp thành công", comp["total_success"])

            if comp["is_complete"]:
                st.success("✅ Đã hoàn thành tích hợp đầy đủ cho toàn bộ các bài giáo viên đã chọn!")
            else:
                st.warning(
                    f"⚠️ Chưa hoàn tất toàn bộ bài đã chọn. Các bài chưa phân tích/duyệt: {', '.join(comp['unprocessed'])}"
                )

            st.subheader("📊 Báo cáo kết quả theo từng bài")
            st.dataframe(pd.DataFrame(exp["lesson_reports"]), use_container_width=True, hide_index=True)

            out_name = get_output_filename(fname, doc_entry["type"])
            mime = (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                if doc_entry["type"] == "docx"
                else "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )
            c_dl1, c_dl2 = st.columns(2)
            with c_dl1:
                st.download_button(
                    label=f"⬇️ Tải về {out_name}",
                    data=exp["bytes"],
                    file_name=out_name,
                    mime=mime,
                    type="primary",
                )
            with c_dl2:
                all_approved_kws = []
                for ls in lessons:
                    if ls.get("selected") and ls.get("analysis"):
                        for k in ls["analysis"].get("keywords", []):
                            if k.get("approved"):
                                k_copy = dict(k)
                                k_copy["target_location"] = f"{ls['title']} — {k.get('target_location', '')}"
                                all_approved_kws.append(k_copy)
                if all_approved_kws:
                    st.download_button(
                        label="📊 Tải toàn bộ danh sách từ khóa (.xlsx)",
                        data=export_keywords_to_excel(all_approved_kws),
                        file_name="Danh_sach_tu_khoa_MultiLesson.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )


# ==================== 6. TỪ ĐIỂN CHUYÊN NGÀNH ====================
elif nav == "6. Từ điển chuyên ngành":
    st.header("📖 Từ điển thuật ngữ chuyên ngành Anh – Việt")

    c1, c2 = st.columns([3, 1.5])
    q = c1.text_input("Tìm kiếm tiếng Việt hoặc tiếng Anh")
    subj = c2.selectbox("Lọc theo môn", ["Tất cả"] + SUBJECTS)

    results = search_dictionary(q, subj)
    if results:
        for idx, item in enumerate(results):
            cols = st.columns([2.2, 2.2, 2, 3.5, 1.2])
            cols[0].write(f"**{item['vi']}**")
            cols[1].write(f":blue[**{item['en']}**]")
            cols[2].caption(item.get("ipa", ""))
            cols[3].caption(item.get("example", ""))
            if cols[4].button("🔊", key=f"dict_play_{idx}"):
                mp3 = generate_pronunciation_mp3(item["en"], accent="US")
                st.audio(mp3, format="audio/mp3")
    else:
        st.info("Không tìm thấy thuật ngữ phù hợp.")