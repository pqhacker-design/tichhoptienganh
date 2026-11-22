import uuid
import pandas as pd
import streamlit as st

from config import (
    APP_SUBTITLE,
    APP_TITLE,
    BILINGUAL_DRAFT_MODES,
    EDUCATION_LEVELS,
    INTEGRATION_LEVELS,
    SUBJECTS,
    TEXTBOOKS,
)
from bilingual_drafter import (
    draft_bilingual_word_inline,
    draft_bilingual_word_two_columns,
    extract_subject_glossary,
)
from document_reader import read_pptx_document, read_word_document
from export_service import get_output_filename
from gemini_service import validate_api_key
from integration_engine import run_multi_lesson_integration
from lesson_analyzer import analyze_lesson_content
from lesson_splitter import detect_lessons_in_document, extract_lesson_text
from pronunciation_service import generate_pronunciation_mp3
from quality_checker import run_quality_check
from vocabulary_service import export_keywords_to_excel, search_dictionary

st.set_page_config(page_title=APP_TITLE, page_icon="📘", layout="wide")


def init_state():
    defaults = {
        "uploaded_docs": {},
        "processed_count": 0,
        "user_api_key": "",
        "api_key_valid": False,
        "integration_level": 1,
        "draft_glossaries": {},   # key -> list of glossary dicts
        "draft_outputs": {},      # key -> {bytes, filename, stats}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()

# --- SIDEBAR ---
with st.sidebar:
    st.title("📘 AI Bilingual")
    st.caption("TT 94/2026/TT-BGDĐT • 3 Mức độ")
    st.divider()

    st.markdown("### 🔑 Gemini API Key")
    api_input = st.text_input(
        "Nhập API Key của bạn",
        type="password",
        value=st.session_state["user_api_key"],
        placeholder="AIzaSy...",
        help="Khóa chỉ lưu tạm trong phiên làm việc hiện tại của trình duyệt.",
    )
    if api_input != st.session_state["user_api_key"]:
        st.session_state["user_api_key"] = api_input.strip()
        st.session_state["api_key_valid"] = False

    c_b1, c_b2 = st.columns(2)
    if c_b1.button("✅ Kiểm tra", use_container_width=True):
        with st.spinner("Đang kiểm tra..."):
            ok, msg = validate_api_key(st.session_state["user_api_key"])
            st.session_state["api_key_valid"] = ok
            (st.success if ok else st.error)(msg)
    if c_b2.button("🗑️ Xóa Key", use_container_width=True):
        st.session_state["user_api_key"] = ""
        st.session_state["api_key_valid"] = False
        st.rerun()

    if st.session_state["api_key_valid"]:
        st.caption("🟢 Trạng thái: **Đã kết nối**")
    elif st.session_state["user_api_key"]:
        st.caption("🟡 Trạng thái: **Đã nhập (chưa kiểm tra)**")
    else:
        st.caption("🔴 Trạng thái: **Chưa nhập API Key**")
        st.markdown("[👉 Lấy API Key miễn phí tại Google AI Studio](https://aistudio.google.com/app/apikey)")

    st.divider()
    nav = st.radio(
        "Điều hướng",
        [
            "1. Trang chủ",
            "2. Tải tài liệu & Chọn mức độ",
            "3. Phân tích & Tích hợp",
            "4. Kiểm duyệt nội dung",
            "5. Xuất tài liệu tích hợp",
            "6. Soạn giáo án song ngữ",
            "7. Từ điển chuyên ngành",
        ],
    )
    st.divider()
    cur_lvl = st.session_state["integration_level"]
    st.caption(f"🎯 Đang chọn: **{INTEGRATION_LEVELS[cur_lvl]['short_label']}**")
    st.metric("Tài liệu đã tải", len(st.session_state["uploaded_docs"]))
    st.metric("Tài liệu đã xuất", st.session_state["processed_count"])


# ==================== 1. TRANG CHỦ ====================
if nav == "1. Trang chủ":
    st.title(APP_TITLE)
    st.subheader(APP_SUBTITLE)

    st.markdown("### 🎯 3 Mức độ tích hợp theo Thông tư số 94/2026/TT-BGDĐT")
    cols = st.columns(3)
    for idx, lvl_id in enumerate((1, 2, 3)):
        cfg = INTEGRATION_LEVELS[lvl_id]
        with cols[idx]:
            st.info(f"**{cfg['name']}**\n\n*{cfg['english_ratio']}*\n\n{cfg['description']}")

    st.success(
        "**Tính năng mới – Soạn giáo án song ngữ (Mục 6):** Chuyển thể trực tiếp giáo án Word đã có sang "
        "giáo án song ngữ Việt – Anh chuẩn thuật ngữ chuyên ngành (hỗ trợ cả kiểu **chèn trực tiếp trên file gốc** "
        "và kiểu **bảng 2 cột Việt | Anh khổ ngang A4**)."
    )


# ==================== 2. TẢI TÀI LIỆU & CHỌN MỨC ĐỘ ====================
elif nav == "2. Tải tài liệu & Chọn mức độ":
    st.header("📂 Tải giáo án & Chọn mức độ tích hợp")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        level = st.selectbox("Cấp học", list(EDUCATION_LEVELS.keys()), key="sel_level")
    with c2:
        grade = st.selectbox("Lớp", EDUCATION_LEVELS[level], key="sel_grade")
    with c3:
        subject = st.selectbox("Môn học", SUBJECTS, key="sel_subject")
    with c4:
        textbook = st.selectbox("Bộ sách giáo khoa", TEXTBOOKS, key="sel_textbook")

    st.subheader("🎚️ Chọn mức độ tích hợp (Thông tư 94/2026/TT-BGDĐT)")
    sel_lvl = st.radio(
        "Mức độ áp dụng cho các bài dạy",
        options=[1, 2, 3],
        index=st.session_state["integration_level"] - 1,
        format_func=lambda x: f"{INTEGRATION_LEVELS[x]['name']} ({INTEGRATION_LEVELS[x]['english_ratio']})",
        horizontal=True,
    )
    st.session_state["integration_level"] = sel_lvl
    st.caption(f"ℹ️ {INTEGRATION_LEVELS[sel_lvl]['description']}")

    st.divider()
    uploaded_files = st.file_uploader(
        "Tải lên file Word (.docx) và/hoặc PowerPoint (.pptx)",
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


# ==================== 3. PHÂN TÍCH & TÍCH HỢP ====================
elif nav == "3. Phân tích & Tích hợp":
    st.header("🧩 Nhận diện & Phân tích từng bài học (Multi-Lesson)")

    if not st.session_state["uploaded_docs"]:
        st.warning("Vui lòng tải tài liệu ở mục **2. Tải tài liệu & Chọn mức độ** trước.")
    else:
        fname = st.selectbox("Chọn tài liệu cần xử lý", list(st.session_state["uploaded_docs"].keys()))
        doc_entry = st.session_state["uploaded_docs"][fname]
        parsed = doc_entry["parsed"]

        int_lvl = st.selectbox(
            "Mức độ tích hợp áp dụng cho lần phân tích này",
            options=[1, 2, 3],
            index=st.session_state["integration_level"] - 1,
            format_func=lambda x: f"{INTEGRATION_LEVELS[x]['name']} ({INTEGRATION_LEVELS[x]['english_ratio']})",
        )
        st.session_state["integration_level"] = int_lvl

        if st.button("🔍 Bước 1: Tự động nhận diện & phân chia bài học", type="primary"):
            with st.spinner("Gemini AI đang phân tích cấu trúc tài liệu..."):
                try:
                    split_res = detect_lessons_in_document(parsed)
                    doc_entry["split_info"] = split_res
                    st.success(f"Đã nhận diện được **{split_res['total_lessons']} bài học** trong `{fname}`.")
                except Exception as e:
                    st.error(f"Lỗi khi nhận diện bài học: {e}")

        split_info = doc_entry.get("split_info")
        if split_info:
            if split_info.get("needs_confirmation"):
                st.warning(f"⚠️ Cần giáo viên xác nhận ranh giới: {split_info.get('confirmation_reason', '')}")

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
                c5.caption(f"Độ tin cậy: **{ls['confidence']}**\n\n`{ls['status']}`")

            st.divider()
            level = st.session_state.get("sel_level", "THCS")
            grade = st.session_state.get("sel_grade", 8)
            subject = st.session_state.get("sel_subject", "Toán")
            textbook = st.session_state.get("sel_textbook", "Kết nối tri thức với cuộc sống")

            if st.button(f"✨ Bước 2: Phân tích theo Mức độ {int_lvl} cho TẤT CẢ bài đã chọn", type="primary"):
                selected_lessons = [ls for ls in split_info["lessons"] if ls["selected"]]
                if not selected_lessons:
                    st.warning("Vui lòng chọn ít nhất 1 bài học.")
                else:
                    bar = st.progress(0, text="Đang phân tích từng bài học...")
                    for i, ls in enumerate(selected_lessons):
                        bar.progress(int((i / len(selected_lessons)) * 90) + 5, text=f"Đang phân tích Mức {int_lvl}: {ls['title']}...")
                        try:
                            ls_text = extract_lesson_text(parsed, ls["start_index"], ls["end_index"])
                            ls["analysis"] = analyze_lesson_content(
                                ls_text, level, grade, subject, textbook,
                                topic_hint=ls["title"],
                                integration_level=int_lvl,
                            )
                            ls["status"] = f"Đã phân tích (Mức {int_lvl})"
                        except Exception as e:
                            ls["status"] = f"Lỗi: {e}"
                    bar.progress(100, text="Hoàn tất phân tích!")
                    st.success("Đã phân tích xong! Chuyển sang mục **4. Kiểm duyệt nội dung** để rà soát.")


# ==================== 4. KIỂM DUYỆT NỘI DUNG ====================
elif nav == "4. Kiểm duyệt nội dung":
    st.header("✅ Quản lý & Kiểm duyệt từng bài học")

    docs_with_splits = [fn for fn, d in st.session_state["uploaded_docs"].items() if d.get("split_info")]
    if not docs_with_splits:
        st.warning("Chưa có tài liệu nào được phân chia bài học.")
    else:
        fname = st.selectbox("Chọn tài liệu", docs_with_splits)
        doc_entry = st.session_state["uploaded_docs"][fname]
        lessons = doc_entry["split_info"]["lessons"]

        lesson_titles = [f"{'☑️' if ls['selected'] else '⬜'} {ls['title']} ({ls['status']})" for ls in lessons]
        sel_idx = st.selectbox("Chọn bài học cần kiểm duyệt", range(len(lessons)), format_func=lambda i: lesson_titles[i])
        ls = lessons[sel_idx]

        with st.expander("📄 Xem nội dung bài gốc"):
            st.text(extract_lesson_text(doc_entry["parsed"], ls["start_index"], ls["end_index"])[:3000])

        if not ls.get("analysis"):
            st.info("Bài học này chưa được phân tích.")
            int_lvl = st.session_state["integration_level"]
            if st.button(f"✨ Phân tích riêng bài này (Mức độ {int_lvl})", type="primary"):
                with st.spinner("Đang phân tích..."):
                    ls_text = extract_lesson_text(doc_entry["parsed"], ls["start_index"], ls["end_index"])
                    ls["analysis"] = analyze_lesson_content(
                        ls_text,
                        st.session_state.get("sel_level", "THCS"),
                        st.session_state.get("sel_grade", 8),
                        st.session_state.get("sel_subject", "Toán"),
                        st.session_state.get("sel_textbook", "Kết nối tri thức với cuộc sống"),
                        topic_hint=ls["title"],
                        integration_level=int_lvl,
                    )
                    ls["status"] = f"Đã phân tích (Mức {int_lvl})"
                    st.rerun()
        else:
            res = ls["analysis"]
            ls_lvl = res.get("integration_level", 1)
            st.info(f"Bài học này đang được phân tích theo **{INTEGRATION_LEVELS[ls_lvl]['name']}**")

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

            if ls_lvl >= 2:
                st.subheader(f"4. Các đoạn/mục song ngữ trọng tâm (Mức độ {ls_lvl})")
                for blk in res.get("bilingual_blocks", []):
                    with st.expander(f"{'✅' if blk['approved'] else '❌'} [{blk.get('section_type', '')}] {blk.get('vi_anchor', '')[:60]}...", expanded=True):
                        c1, c2 = st.columns([5, 1])
                        blk["en_text"] = c1.text_area("Nội dung tiếng Anh chèn vào", blk["en_text"], key=f"blk_en_{ls['lesson_id']}_{blk['id']}", height=70)
                        blk["approved"] = c2.checkbox("Duyệt", value=blk["approved"], key=f"blk_ok_{ls['lesson_id']}_{blk['id']}")

            st.subheader("5. Kiểm tra chất lượng (10 tiêu chí)")
            checks = run_quality_check(res, [doc_entry["parsed"]], integration_level=ls_lvl)
            st.dataframe(pd.DataFrame(checks), use_container_width=True, hide_index=True)


# ==================== 5. XUẤT TÀI LIỆU TÍCH HỢP ====================
elif nav == "5. Xuất tài liệu tích hợp":
    st.header("📥 Tích hợp trực tiếp & Báo cáo kết quả theo từng bài")

    docs_with_splits = [fn for fn, d in st.session_state["uploaded_docs"].items() if d.get("split_info")]
    if not docs_with_splits:
        st.warning("Chưa có tài liệu nào sẵn sàng xuất.")
    else:
        fname = st.selectbox("Chọn tài liệu xuất", docs_with_splits)
        doc_entry = st.session_state["uploaded_docs"][fname]
        lessons = doc_entry["split_info"]["lessons"]
        int_lvl = st.session_state["integration_level"]

        if st.button("🚀 Tích hợp các bài đã chọn vào file gốc", type="primary"):
            with st.spinner("Đang tích hợp trực tiếp vào file gốc..."):
                out_bytes, lesson_reports, completeness = run_multi_lesson_integration(
                    doc_entry["bytes"], doc_entry["type"], lessons, integration_level=int_lvl
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
                st.success("✅ Đã hoàn thành tích hợp đầy đủ cho toàn bộ các bài đã chọn!")
            else:
                st.warning(f"⚠️ Các bài chưa phân tích/duyệt: {', '.join(comp['unprocessed'])}")

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
                all_kws = []
                for ls in lessons:
                    if ls.get("selected") and ls.get("analysis"):
                        for k in ls["analysis"].get("keywords", []):
                            if k.get("approved"):
                                k_copy = dict(k)
                                k_copy["target_location"] = f"{ls['title']} — {k.get('target_location', '')}"
                                all_kws.append(k_copy)
                if all_kws:
                    st.download_button(
                        label="📊 Tải danh sách từ khóa (.xlsx)",
                        data=export_keywords_to_excel(all_kws),
                        file_name="Danh_sach_tu_khoa_Bilingual.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )


# ==================== 6. SOẠN GIÁO ÁN SONG NGỮ ====================
elif nav == "6. Soạn giáo án song ngữ":
    st.header("🌐 Soạn giáo án song ngữ từ giáo án Word đã có")
    st.caption(
        "Chuyển thể toàn bộ giáo án tiếng Việt sang giáo án song ngữ Việt – Anh theo đúng thuật ngữ chuyên ngành môn học "
        "(quy trình 2 bước: Khóa bảng thuật ngữ chuẩn → Biên soạn đồng bộ)."
    )

    word_docs = [fn for fn, d in st.session_state["uploaded_docs"].items() if d["type"] == "docx"]
    if not word_docs:
        st.warning("Vui lòng tải lên ít nhất 1 file giáo án Word (`.docx`) ở mục **2. Tải tài liệu & Chọn mức độ**.")
    else:
        fname = st.selectbox("Chọn giáo án Word gốc", word_docs, key="draft_fname")
        doc_entry = st.session_state["uploaded_docs"][fname]
        parsed = doc_entry["parsed"]

        level = st.session_state.get("sel_level", "THCS")
        grade = st.session_state.get("sel_grade", 8)
        subject = st.session_state.get("sel_subject", "Toán")
        textbook = st.session_state.get("sel_textbook", "Kết nối tri thức với cuộc sống")

        # Hỗ trợ chọn toàn bộ file hoặc chỉ 1 bài cụ thể (nếu đã tách bài ở mục 3)
        start_blk, end_blk = None, None
        scope_title = fname.rsplit(".", 1)[0]
        if doc_entry.get("split_info"):
            lessons = doc_entry["split_info"]["lessons"]
            scope_opts = ["Toàn bộ tài liệu"] + [ls["title"] for ls in lessons]
            sel_scope = st.selectbox("Phạm vi biên soạn song ngữ", scope_opts)
            if sel_scope != "Toàn bộ tài liệu":
                ls_match = next(ls for ls in lessons if ls["title"] == sel_scope)
                start_blk, end_blk = ls_match["start_index"], ls_match["end_index"]
                scope_title = ls_match["title"]

        draft_key = f"{fname}__{scope_title}"

        # --- BƯỚC 1: KHÓA BẢNG THUẬT NGỮ CHUYÊN NGÀNH ---
        st.subheader("Bước 1: Trích xuất & Khóa bảng thuật ngữ chuyên ngành")
        if st.button("📚 Trích xuất thuật ngữ chuyên ngành từ giáo án", type="primary"):
            with st.spinner(f"Đang trích xuất thuật ngữ chuẩn môn {subject}..."):
                try:
                    src_text = (
                        extract_lesson_text(parsed, start_blk, end_blk)
                        if start_blk is not None
                        else parsed["full_text"]
                    )
                    glossary = extract_subject_glossary(src_text, level, grade, subject, textbook)
                    st.session_state["draft_glossaries"][draft_key] = glossary
                    st.success(f"Đã trích xuất {len(glossary)} thuật ngữ chuyên ngành. Hãy kiểm tra và chỉnh sửa trước khi biên soạn.")
                except Exception as e:
                    st.error(f"Lỗi trích xuất thuật ngữ: {e}")

        glossary = st.session_state["draft_glossaries"].get(draft_key)
        if glossary is not None:
            for g in glossary:
                c1, c2, c3, c4 = st.columns([2.2, 2.5, 1.8, 1])
                g["vi"] = c1.text_input("VI", g["vi"], key=f"gvi_{draft_key}_{g['id']}", label_visibility="collapsed")
                g["en"] = c2.text_input("EN", g["en"], key=f"gen_{draft_key}_{g['id']}", label_visibility="collapsed")
                g["ipa"] = c3.text_input("IPA", g.get("ipa", ""), key=f"gipa_{draft_key}_{g['id']}", label_visibility="collapsed")
                g["approved"] = c4.checkbox("Khóa", value=g["approved"], key=f"gok_{draft_key}_{g['id']}")

            with st.expander("➕ Bổ sung thuật ngữ chuyên ngành thủ công"):
                ac1, ac2, ac3 = st.columns(3)
                n_vi = ac1.text_input("Thuật ngữ Tiếng Việt", key=f"nvi_{draft_key}")
                n_en = ac2.text_input("Thuật ngữ Tiếng Anh chuẩn", key=f"nen_{draft_key}")
                n_ipa = ac3.text_input("IPA (tùy chọn)", key=f"nipa_{draft_key}")
                if st.button("Thêm vào bảng thuật ngữ", key=f"nadd_{draft_key}"):
                    if n_vi and n_en:
                        glossary.append({
                            "id": str(uuid.uuid4())[:8],
                            "vi": n_vi.strip(),
                            "en": n_en.strip(),
                            "ipa": n_ipa.strip(),
                            "note": "Giáo viên bổ sung",
                            "approved": True,
                        })
                        st.rerun()

            st.divider()
            # --- BƯỚC 2: CHỌN KIỂU TRÌNH BÀY & BIÊN SOẠN ---
            st.subheader("Bước 2: Chọn kiểu trình bày & Soạn giáo án song ngữ")
            draft_mode = st.radio(
                "Chọn định dạng giáo án song ngữ đầu ra",
                options=list(BILINGUAL_DRAFT_MODES.keys()),
                format_func=lambda k: BILINGUAL_DRAFT_MODES[k],
            )

            if st.button("✍️ Tiến hành soạn giáo án song ngữ", type="primary"):
                prog = st.progress(0.0, text="Khởi tạo quá trình chuyển ngữ theo thuật ngữ đã khóa...")

                def _cb(pct: float, msg: str):
                    prog.progress(pct, text=msg)

                try:
                    if draft_mode == "inline":
                        out_bytes, stats = draft_bilingual_word_inline(
                            doc_entry["bytes"], glossary, level, grade, subject,
                            start_block=start_blk, end_block=end_blk, progress_callback=_cb,
                        )
                        suffix = "SongNgu_Goc"
                    else:
                        out_bytes, stats = draft_bilingual_word_two_columns(
                            doc_entry["bytes"], glossary, level, grade, subject,
                            lesson_title=scope_title,
                            start_block=start_blk, end_block=end_blk, progress_callback=_cb,
                        )
                        suffix = "SongNgu_2Cot"

                    out_fname = f"{scope_title}_{suffix}.docx"
                    st.session_state["draft_outputs"][draft_key] = {
                        "bytes": out_bytes,
                        "filename": out_fname,
                        "stats": stats,
                    }
                    st.session_state["processed_count"] += 1
                    st.success(
                        f"✅ Đã soạn xong giáo án song ngữ! Chuyển ngữ thành công "
                        f"**{stats['translated_items']}/{stats['total_items']}** mục theo **{stats['glossary_count']}** thuật ngữ chuẩn."
                    )
                except Exception as e:
                    prog.empty()
                    st.error(f"Lỗi trong quá trình soạn giáo án song ngữ: {e}")

            draft_out = st.session_state["draft_outputs"].get(draft_key)
            if draft_out:
                st.download_button(
                    label=f"⬇️ Tải giáo án song ngữ ({draft_out['filename']})",
                    data=draft_out["bytes"],
                    file_name=draft_out["filename"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                )


# ==================== 7. TỪ ĐIỂN CHUYÊN NGÀNH ====================
elif nav == "7. Từ điển chuyên ngành":
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
                st.audio(generate_pronunciation_mp3(item["en"], accent="US"), format="audio/mp3")
    else:
        st.info("Không tìm thấy thuật ngữ phù hợp.")
