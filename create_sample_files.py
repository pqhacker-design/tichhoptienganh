from docx import Document
from pptx import Presentation


def create_sample_word_multi_lesson():
    doc = Document()

    # --- BÀI 1 ---
    doc.add_heading("BÀI 1: TAM GIÁC CÂN", level=1)
    doc.add_paragraph("Môn: Toán – Lớp 7 (Kết nối tri thức với cuộc sống)")
    doc.add_heading("Hoạt động 1: Khởi động", level=2)
    doc.add_paragraph("Giáo viên yêu cầu học sinh quan sát mái nhà có dạng tam giác cân.")
    doc.add_heading("Hoạt động 2: Hình thành kiến thức", level=2)
    doc.add_paragraph("Trong tam giác cân ABC tại A: AB và AC là hai cạnh bên bằng nhau; BC là cạnh đáy; góc A là góc ở đỉnh; góc B và góc C là hai góc ở đáy.")

    tbl = doc.add_table(rows=2, cols=2)
    tbl.style = "Table Grid"
    tbl.rows[0].cells[0].text = "Hoạt động của giáo viên"
    tbl.rows[0].cells[1].text = "Hoạt động của học sinh"
    tbl.rows[1].cells[0].text = "Yêu cầu học sinh đo hai góc ở đáy của tam giác cân."
    tbl.rows[1].cells[1].text = "Thực hiện đo và rút ra nhận xét hai góc ở đáy bằng nhau."

    doc.add_heading("Hoạt động 3: Luyện tập", level=2)
    doc.add_paragraph("Cho tam giác cân ABC tại A có góc ở đỉnh bằng 40 độ. Tính số đo hai góc ở đáy.")

    # --- BÀI 2 ---
    doc.add_heading("BÀI 2: ĐƯỜNG TRUNG TRỰC CỦA ĐOẠN THẲNG", level=1)
    doc.add_heading("Hoạt động 1: Khởi động", level=2)
    doc.add_paragraph("Làm thế nào để xác định điểm cách đều hai đầu mút của một đoạn thẳng?")
    doc.add_heading("Hoạt động 2: Hình thành kiến thức", level=2)
    doc.add_paragraph("Đường thẳng vuông góc với một đoạn thẳng tại trung điểm của nó được gọi là đường trung trực của đoạn thẳng ấy.")
    doc.add_heading("Hoạt động 3: Luyện tập", level=2)
    doc.add_paragraph("Vẽ đoạn thẳng AB dài 6 cm và dựng đường trung trực đi qua trung điểm M của AB.")

    doc.save("Giao_an_Nhieu_bai_Toan7.docx")
    print("Đã tạo file mẫu: Giao_an_Nhieu_bai_Toan7.docx")


def create_sample_pptx_multi_lesson():
    prs = Presentation()

    # Bài 1 (Slide 1-2)
    s1 = prs.slides.add_slide(prs.slide_layouts[0])
    s1.shapes.title.text = "BÀI 1: TAM GIÁC CÂN"
    s1.placeholders[1].text = "Hoạt động 1: Khởi động"

    s2 = prs.slides.add_slide(prs.slide_layouts[1])
    s2.shapes.title.text = "Hình thành kiến thức"
    s2.placeholders[1].text_frame.text = "Tam giác cân có hai cạnh bên và hai góc ở đáy bằng nhau."

    # Bài 2 (Slide 3-4)
    s3 = prs.slides.add_slide(prs.slide_layouts[0])
    s3.shapes.title.text = "BÀI 2: ĐƯỜNG TRUNG TRỰC CỦA ĐOẠN THẲNG"
    s3.placeholders[1].text = "Hoạt động 1: Khởi động"

    s4 = prs.slides.add_slide(prs.slide_layouts[1])
    s4.shapes.title.text = "Hình thành kiến thức"
    s4.placeholders[1].text_frame.text = "Đường trung trực vuông góc với đoạn thẳng tại trung điểm của nó."

    prs.save("Bai_giang_Nhieu_bai_Toan7.pptx")
    print("Đã tạo file mẫu: Bai_giang_Nhieu_bai_Toan7.pptx")


if __name__ == "__main__":
    create_sample_word_multi_lesson()
    create_sample_pptx_multi_lesson()