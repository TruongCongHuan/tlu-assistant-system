#!/usr/bin/env python3
"""Tạo báo cáo kỹ thuật RAG (server-only) dạng DOCX.

Sau khi migrate logic RAG local lên server, báo cáo chỉ trình bày:
  - FastAPI RAG API + ChromaDB + Gemini
  - Docker Compose triển khai
  - Flutter client gọi SSE (không còn on-device RAG)

Usage:
    python3 scripts/build_rag_report_docx.py

Output:
    document/BAO_CAO_KY_THUAT_RAG.docx
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "document" / "BAO_CAO_KY_THUAT_RAG.docx"

FONT = "Times New Roman"
PT13 = Pt(13)
PT14 = Pt(14)
PT16 = Pt(16)
PT18 = Pt(18)


def _setup_margins(doc: Document) -> None:
    for sec in doc.sections:
        sec.top_margin = Cm(2)
        sec.bottom_margin = Cm(2)
        sec.left_margin = Cm(3)
        sec.right_margin = Cm(1.5)


def _para(doc, text="", size=PT13, bold=False, italic=False,
          align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_before=Pt(0), space_after=Pt(6)):
    p = doc.add_paragraph()
    if text:
        r = p.add_run(text)
        r.font.name = FONT
        r.font.size = size
        r.font.bold = bold
        r.font.italic = italic
    pf = p.paragraph_format
    pf.alignment = align
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.5
    pf.space_before = space_before
    pf.space_after = space_after


def _chapter(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text.upper())
    r.font.name = FONT
    r.font.size = PT16
    r.font.bold = True
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.5
    pf.space_before = Pt(12)
    pf.space_after = Pt(6)


def _section(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name = FONT
    r.font.size = PT14
    r.font.bold = True
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.5
    pf.space_before = Pt(6)
    pf.space_after = Pt(3)


def _subsection(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name = FONT
    r.font.size = PT13
    r.font.bold = True
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.5
    pf.space_before = Pt(3)
    pf.space_after = Pt(3)


def _body(doc, text):
    _para(doc, text)


def _bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    r = p.add_run(text)
    r.font.name = FONT
    r.font.size = PT13
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.5
    pf.space_before = Pt(0)
    pf.space_after = Pt(3)


def _code(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name = "Courier New"
    r.font.size = Pt(10)
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    pf.space_before = Pt(3)
    pf.space_after = Pt(3)
    pf.left_indent = Cm(0.5)


def _table(doc, caption, headers, rows):
    if caption:
        _para(doc, caption, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
              space_before=Pt(6), space_after=Pt(3))
    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    try:
        tbl.style = "Table Grid"
    except KeyError:
        pass
    for ci, h in enumerate(headers):
        cell = tbl.rows[0].cells[ci]
        cell.text = h
        for cp in cell.paragraphs:
            cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in cp.runs:
                r.font.name = FONT
                r.font.size = Pt(11)
                r.bold = True
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = tbl.rows[ri + 1].cells[ci]
            cell.text = str(val)
            for cp in cell.paragraphs:
                for r in cp.runs:
                    r.font.name = FONT
                    r.font.size = Pt(11)
    _para(doc, "")


def _page_break(doc):
    doc.add_page_break()


def _footer(doc):
    for section in doc.sections:
        footer = section.footer
        footer.is_linked_to_previous = False
        para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        para.clear()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run()
        run.font.name = FONT
        run.font.size = PT13
        fc_b = OxmlElement("w:fldChar")
        fc_b.set(qn("w:fldCharType"), "begin")
        run._r.append(fc_b)
        ir = para.add_run()
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = " PAGE "
        ir._r.append(instr)
        er = para.add_run()
        fc_e = OxmlElement("w:fldChar")
        fc_e.set(qn("w:fldCharType"), "end")
        er._r.append(fc_e)


def _cover(doc):
    _para(doc, "TRƯỜNG ĐẠI HỌC THĂNG LONG", size=PT14, bold=True,
          align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(6))
    _para(doc, "KHOA CÔNG NGHỆ THÔNG TIN", bold=True,
          align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(24))
    _para(doc, "BÁO CÁO KỸ THUẬT", size=PT18, bold=True,
          align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(6))
    _para(doc, "MÔ HÌNH AI, XỬ LÝ DỮ LIỆU, CHUNKING, EMBEDDING VÀ RAG",
          size=PT16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(12))
    _para(doc, "Đề tài: Phát triển hệ thống trợ lý AI học vụ tích hợp quản lý sinh viên",
          bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(6))
    _para(doc, "TLU AI Assistant — Kiến trúc RAG Server (FastAPI + ChromaDB + Gemini)",
          italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(36))
    _para(doc, "Sinh viên: TRƯƠNG CÔNG HUẤN — Mã SV: A33941",
          bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(3))
    _para(doc, "Giảng viên hướng dẫn: ThS. NGÔ MẠNH CƯỜNG",
          bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(36))
    _para(doc, "Hà Nội, 2026", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    _page_break(doc)


def _muc_luc(doc):
    _chapter(doc, "MỤC LỤC")
    entries = [
        "1. Bức tranh toàn cảnh: RAG là gì và tại sao dùng nó?",
        "2. Dữ liệu: Sổ tay sinh viên K38",
        "3. Bước 1 — Chunking: Chia nhỏ tài liệu thành các đoạn",
        "4. Bước 2 — Embedding: Chuyển văn bản thành vector số",
        "5. Bước 3 — Vector Store: ChromaDB lưu trữ và tìm kiếm",
        "6. Bước 4 — Query Expansion: Mở rộng câu hỏi",
        "7. Bước 5 — Multi-Query Retrieval: Tìm kiếm đa truy vấn",
        "8. Bước 6 — Generation: LLM sinh câu trả lời (streaming SSE)",
        "9. Kiến trúc RAG Server và luồng tích hợp hệ thống",
        "10. Bộ đánh giá (Eval Harness) và thực nghiệm ablation",
        "11. Pipeline tổng hợp: Từ câu hỏi đến câu trả lời",
        "12. Triển khai server với Docker Compose",
        "13. Tóm tắt đóng góp kỹ thuật và kết quả",
        "14. Bảng từ khóa kỹ thuật (Glossary)",
    ]
    for e in entries:
        _body(doc, e)
    _page_break(doc)


def _ch1(doc):
    _chapter(doc, "1. BỨC TRANH TOÀN CẢNH: RAG LÀ GÌ VÀ TẠI SAO DÙNG NÓ?")
    _section(doc, "1.1. Vấn đề với LLM thuần")
    _body(doc,
          "Khi dùng ChatGPT hay Gemini để hỏi \"Sinh viên TLU bị cảnh báo học tập khi GPA "
          "bao nhiêu?\", LLM có thể trả lời sai vì không được huấn luyện trên Sổ tay sinh "
          "viên TLU. Hiện tượng này gọi là hallucination (ảo giác). Trong bối cảnh quy chế "
          "học vụ, sai một chi tiết nhỏ có thể gây hậu quả thật cho sinh viên.")
    _section(doc, "1.2. RAG giải quyết vấn đề như thế nào?")
    _body(doc,
          "Retrieval-Augmented Generation (RAG) — Sinh văn bản tăng cường truy hồi — ghép "
          "hai bước: (1) Retrieval: tìm đoạn văn bản liên quan trong kho tài liệu; "
          "(2) Generation: đưa các đoạn đó vào prompt và yêu cầu LLM trả lời dựa trên "
          "ngữ cảnh đó.")
    _bullet(doc, "Giảm hallucination — LLM chỉ trả lời dựa trên nội dung được cung cấp.")
    _bullet(doc, "Cập nhật tri thức bằng cách thêm tài liệu mới, không cần fine-tune lại mô hình.")
    _bullet(doc, "Trích dẫn nguồn cụ thể (ví dụ: guide_book_k38.md).")
    _section(doc, "1.3. Pipeline RAG Server trong project")
    _body(doc,
          "Toàn bộ pipeline RAG chạy trên server (container rag-api). Ứng dụng Flutter chỉ "
          "đóng vai trò client: gửi câu hỏi qua HTTP POST /v1/chat/stream và nhận câu trả lời "
          "streaming qua SSE. Cán bộ quản lý tài liệu qua Staff Console, upload PDF/Markdown "
          "và ingest vào ChromaDB tập trung.")
    _code(doc,
          "OFFLINE INDEXING (ingest một lần):\n"
          "  PDF/MD → PyMuPDF extract → Semantic Chunking (~850 chunk)\n"
          "         → Gemini Embedding → ChromaDB (HNSW cosine)\n\n"
          "ONLINE QUERYING (mỗi câu hỏi):\n"
          "  Flutter → POST /v1/chat/stream (X-Student-Key)\n"
          "         → Query Expansion → Multi-query embed+search → Dedup top-12\n"
          "         → Prompt 5 bước + Gemini Flash stream → SSE → Flutter UI")
    _page_break(doc)


def _ch2(doc):
    _chapter(doc, "2. DỮ LIỆU: SỔ TAY SINH VIÊN K38")
    _section(doc, "2.1. Nguồn tài liệu")
    _table(doc, "Bảng 2.1. Thông tin corpus tri thức",
           ["Thuộc tính", "Giá trị"],
           [
               ["File", "output_md/guide_book_k38_pymupdf.md"],
               ["Kích thước", "~385 KB, ~4.947 dòng"],
               ["Định dạng", "Markdown (chuyển từ PDF bằng PyMuPDF)"],
               ["Nội dung", "Quy chế đào tạo, 15+ CTĐT, lịch học 2025–2026"],
               ["Ngôn ngữ", "Tiếng Việt"],
           ])
    _section(doc, "2.2. Tại sao dùng Markdown thay vì PDF trực tiếp?")
    _bullet(doc, "Giữ heading hierarchy (#, ##) → phục vụ Semantic Markdown Chunking.")
    _bullet(doc, "Giữ bảng biểu dạng |---| → quy chế có nhiều bảng thời gian biểu.")
    _bullet(doc, "Tránh vấn đề PDF scan không có lớp text.")
    _body(doc,
          "Công cụ chuyển đổi: PyMuPDF (fitz) — đọc PDF nhanh, hỗ trợ Unicode tiếng Việt tốt.")
    _section(doc, "2.3. Bộ đánh giá 50 câu hỏi")
    _body(doc,
          "Ngoài corpus chính, project xây dựng eval_set.jsonl gồm 50 câu hỏi–đáp chuẩn "
          "để đánh giá pipeline RAG định lượng: trực tiếp (23), suy luận (12), "
          "viết tắt (9), ngoài phạm vi (6).")
    _page_break(doc)


def _ch3(doc):
    _chapter(doc, "3. BƯỚC 1 — CHUNKING: CHIA NHỎ TÀI LIỆU THÀNH CÁC ĐOẠN")
    _section(doc, "3.1. Tại sao phải chia nhỏ?")
    _body(doc,
          "Sổ tay K38 dài ~385 KB. Không thể nhét toàn bộ vào prompt vì giới hạn context "
          "window, chi phí token và nhiễu thông tin. Giải pháp: chia thành chunk, chỉ đưa "
          "vào prompt những chunk liên quan nhất với câu hỏi.")
    _section(doc, "3.2. Fixed-size Chunking (Baseline)")
    _body(doc,
          "Cắt theo cửa sổ trượt: CHUNK_SIZE=1200 ký tự, CHUNK_OVERLAP=150. "
          "Hạn chế: cắt giữa điều khoản, giữa bảng → mất ngữ nghĩa.")
    _section(doc, "3.3. Semantic Markdown Chunking (Phương pháp đề xuất)")
    _body(doc,
          "Chia theo cấu trúc ngữ nghĩa của văn bản: mỗi heading ## (Điều, Chương) "
          "là một đơn vị chunk. Section dài hơn 1200 ký tự được sub-split với hai quy tắc:")
    _bullet(doc, "Table-aware: không cắt giữa dòng bảng (|...|).")
    _bullet(doc, "3-line overlap: giữ 3 dòng cuối chunk trước làm đầu chunk sau.")
    _body(doc,
          "File triển khai: services/rag-api/app/rag.py — hàm chunk_text_semantic(), "
          "_split_by_headings(), _split_sub_section().")
    _table(doc, "Bảng 3.1. So sánh hai chiến lược chunking",
           ["Tiêu chí", "Fixed-size", "Semantic MD"],
           [
               ["Số chunk từ K38", "~320", "~850–950"],
               ["TB ký tự/chunk", "~1.200", "~400"],
               ["Ngữ cảnh", "Dễ cắt giữa điều", "1 chunk = 1 điều/mục"],
               ["Bảng biểu", "Có thể cắt ngang", "Luôn nguyên vẹn"],
               ["Metadata", "Không", "heading_path, chunk_type"],
           ])
    _section(doc, "3.4. Metadata mỗi chunk")
    _code(doc,
          '{\n'
          '  "id": "abc123_42",\n'
          '  "text": "## Điều 9. Tổ chức đăng ký học\\n...",\n'
          '  "meta": {\n'
          '    "doc_id": "abc123",\n'
          '    "doc_name": "guide_book_k38.md",\n'
          '    "chunk_index": 42,\n'
          '    "heading_path": "## Điều 9. Tổ chức đăng ký học",\n'
          '    "chunk_type": "section"\n'
          '  }\n'
          '}')
    _page_break(doc)


def _ch4(doc):
    _chapter(doc, "4. BƯỚC 2 — EMBEDDING: CHUYỂN VĂN BẢN THÀNH VECTOR SỐ")
    _section(doc, "4.1. Embedding là gì?")
    _body(doc,
          "Embedding ánh xạ văn bản → vector số trong không gian nhiều chiều. "
          "Văn bản có nghĩa giống nhau thì vector gần nhau (cosine similarity cao). "
          "Ví dụ: \"học phí tín chỉ\" và \"mức học phí mỗi tín chỉ\" có vector gần nhau; "
          "\"thời tiết hôm nay\" có vector xa.")
    _section(doc, "4.2. Model và tham số")
    _table(doc, "Bảng 4.1. Cấu hình embedding",
           ["Tham số", "Giá trị"],
           [
               ["Model", "gemini-embedding-2-preview"],
               ["Số chiều vector", "~3.072"],
               ["API", "REST embedContent (tránh lỗi SDK 404)"],
               ["Delay giữa requests", "400 ms (EMBED_REQUEST_DELAY_MS)"],
               ["Max retries", "6 (exponential backoff khi 429)"],
           ])
    _section(doc, "4.3. Rate limit và xử lý lỗi")
    _body(doc,
          "Gemini free tier giới hạn quota. Khi gặp HTTP 429, hệ thống chờ 2s, 4s, 8s... "
          "tối đa 60s rồi thử lại. Khi ingest K38 (~850 chunk): ~6–8 phút.")
    _page_break(doc)


def _ch5(doc):
    _chapter(doc, "5. BƯỚC 3 — VECTOR STORE: CHROMADB LƯU TRỮ VÀ TÌM KIẾM")
    _section(doc, "5.1. ChromaDB")
    _body(doc,
          "ChromaDB là vector database mã nguồn mở, lưu embedding kèm metadata, "
          "hỗ trợ similarity search tốc độ cao. Chạy trong container rag-api, "
          "dữ liệu persistent qua Docker volume chroma-data.")
    _section(doc, "5.2. Cấu trúc collection")
    _code(doc,
          'collection = chroma_client.get_or_create_collection(\n'
          '    name="tlu_docs",\n'
          '    metadata={"hnsw:space": "cosine"}\n'
          ')\n'
          'collection.add(\n'
          '    ids=[...], embeddings=[...], documents=[...], metadatas=[...]\n'
          ')')
    _section(doc, "5.3. Thuật toán HNSW và cosine similarity")
    _body(doc,
          "HNSW (Hierarchical Navigable Small World) tìm approximate nearest neighbors "
          "với độ phức tạp O(log N). Cosine similarity đo góc giữa hai vector: "
          "1.0 = giống hoàn toàn, 0.0 = không liên quan. ChromaDB trả distance = 1 - similarity.")
    _page_break(doc)


def _ch6(doc):
    _chapter(doc, "6. BƯỚC 4 — QUERY EXPANSION: MỞ RỘNG CÂU HỎI")
    _section(doc, "6.1. Vấn đề Semantic Gap")
    _body(doc,
          "Sinh viên hỏi \"ngành IT học gì?\" nhưng Sổ tay viết \"Chương trình đào tạo "
          "Công nghệ thông tin\". Embedding của hai cụm không hoàn toàn giống → retrieval "
          "có thể bỏ sót chunk liên quan.")
    _section(doc, "6.2. Giải pháp: Query Expansion nhận thức viết tắt")
    _body(doc,
          "Dùng Gemini Flash sinh 3–4 biến thể tìm kiếm, kèm mở rộng viết tắt học vụ: "
          "IT=Công nghệ thông tin, SV=Sinh viên, HK=Học kỳ, HP=Học phần, GPA=điểm TB tích lũy, "
          "CTĐT=Chương trình đào tạo, ĐKH=Đăng ký học.")
    _body(doc,
          "Ví dụ: Input \"ngành IT cần học bao nhiêu tín chỉ GPA?\" → Output 4 queries "
          "gồm \"CTĐT CNTT tín chỉ\", \"số tín chỉ IT\", \"GPA yêu cầu tốt nghiệp\" "
          "và câu hỏi gốc. Fallback: nếu Gemini lỗi → chỉ dùng câu hỏi gốc.")
    _body(doc, "File: services/rag-api/app/rag.py — hàm expand_query(). Bật/tắt qua EXPAND_ON=1|0.")
    _page_break(doc)


def _ch7(doc):
    _chapter(doc, "7. BƯỚC 5 — MULTI-QUERY RETRIEVAL: TÌM KIẾM ĐA TRUY VẤN")
    _section(doc, "7.1. Luồng xử lý")
    _bullet(doc, "expand_query() → 3–5 biến thể câu hỏi.")
    _bullet(doc, "Với mỗi query: embed → ChromaDB query top-k=8.")
    _bullet(doc, "Dedup theo nội dung text, sort theo cosine score.")
    _bullet(doc, "Giữ top MAX_CONTEXT=12 chunk tốt nhất.")
    _bullet(doc, "Format context: [Đoạn i - tên_file] + nội dung, phân cách bằng ---.")
    _section(doc, "7.2. Tại sao hiệu quả hơn single-query?")
    _body(doc,
          "Single-query có thể bỏ sót chunk dùng từ đồng nghĩa. Multi-query tìm từ nhiều "
          "góc độ, merge và dedup → tăng recall. Trade-off: tốn thêm quota embed API "
          "(giới hạn tối đa 5 variants).")
    _body(doc, "File: services/rag-api/app/rag.py — hàm retrieve_context().")
    _page_break(doc)


def _ch8(doc):
    _chapter(doc, "8. BƯỚC 6 — GENERATION: LLM SINH CÂU TRẢ LỜI")
    _section(doc, "8.1. Model Generation")
    _table(doc, "Bảng 8.1. Cấu hình LLM",
           ["Tham số", "Giá trị"],
           [
               ["Model", "models/gemini-flash-latest"],
               ["Temperature", "0.5"],
               ["max_output_tokens", "2.048"],
               ["Streaming", "Có (SSE)"],
           ])
    _section(doc, "8.2. System Prompt 5 bước")
    _bullet(doc, "Bước 1 — Phân tích & Định danh: xác định mục tiêu, hỏi thêm nếu phụ thuộc K/Ngành.")
    _bullet(doc, "Bước 2 — Kiểm tra Hiệu lực: ưu tiên văn bản mới nhất (2025–2026).")
    _bullet(doc, "Bước 3 — Suy luận Logic: kết nối mốc thời gian khi tài liệu không ghi trực tiếp.")
    _bullet(doc, "Bước 4 — Tổng hợp & Phản hồi: ngắn gọn, bullet points.")
    _bullet(doc, "Bước 5 — Escalation: gợi ý liên hệ phòng ban nếu không đủ thông tin.")
    _section(doc, "8.3. User Prompt và Streaming SSE")
    _body(doc,
          "Prompt gồm: ngày hôm nay, context (12 chunks), câu hỏi gốc, quy tắc trả lời "
          "và ghi nguồn. FastAPI yield từng token qua POST /v1/chat/stream; "
          "Flutter client đọc SSE và hiển thị ngay (trải nghiệm như ChatGPT).")
    _page_break(doc)


def _ch9(doc):
    _chapter(doc, "9. KIẾN TRÚC RAG SERVER VÀ LUỒNG TÍCH HỢP HỆ THỐNG")
    _section(doc, "9.1. Thành phần hệ thống (server-only)")
    _table(doc, "Bảng 9.1. Các thành phần trong kiến trúc RAG server",
           ["Thành phần", "Công nghệ", "Vai trò"],
           [
               ["RAG API", "FastAPI + Python 3.11", "Ingest, retrieve, generate, SSE"],
               ["Vector DB", "ChromaDB (HNSW cosine)", "Lưu embedding persistent"],
               ["Embedding", "Gemini Embedding API", "Text → vector 3072 chiều"],
               ["LLM", "Gemini Flash", "Sinh câu trả lời streaming"],
               ["Staff Console", "React + Express BFF", "Upload tài liệu, proxy admin"],
               ["Flutter App", "Dart", "Client gọi /v1/chat/stream"],
           ])
    _section(doc, "9.2. API endpoints chính")
    _table(doc, "Bảng 9.2. Endpoint RAG API",
           ["Phương thức", "Đường dẫn", "Xác thực", "Mô tả"],
           [
               ["GET", "/health", "Public", "Health check"],
               ["POST", "/admin/documents", "X-Admin-Key", "Upload + ingest tài liệu"],
               ["GET", "/admin/documents", "X-Admin-Key", "Danh sách tài liệu"],
               ["DELETE", "/admin/documents/{id}", "X-Admin-Key", "Xóa tài liệu + vector"],
               ["GET", "/admin/ingest-jobs/{id}", "X-Admin-Key", "Trạng thái job ingest"],
               ["POST", "/v1/chat/stream", "X-Student-Key", "Hỏi đáp RAG (SSE)"],
           ])
    _section(doc, "9.3. Luồng hỏi đáp end-to-end")
    _code(doc,
          "Sinh viên (Flutter)\n"
          "  → POST /v1/chat/stream + X-Student-Key\n"
          "  → FastAPI rag.stream_answer()\n"
          "  → retrieve_context() → expand + embed + ChromaDB\n"
          "  → Gemini Flash stream → SSE events\n"
          "  → Flutter hiển thị từng token")
    _section(doc, "9.4. Lý do chọn kiến trúc server-only")
    _bullet(doc, "Quản lý tài liệu tập trung — cán bộ upload một lần, toàn trường dùng chung.")
    _bullet(doc, "Đồng bộ tri thức — mọi sinh viên nhận cùng corpus, không phụ thuộc thiết bị.")
    _bullet(doc, "ChromaDB HNSW scale tốt hơn scan O(N) trên thiết bị.")
    _bullet(doc, "Dễ bảo trì — một codebase Python (rag.py), deploy Docker Compose.")
    _page_break(doc)


def _ch10(doc):
    _chapter(doc, "10. BỘ ĐÁNH GIÁ (EVAL HARNESS) VÀ THỰC NGHIỆM ABLATION")
    _section(doc, "10.1. Dataset 50 câu hỏi")
    _table(doc, "Bảng 10.1. Phân loại bộ câu hỏi đánh giá",
           ["Loại", "Số câu", "Mô tả"],
           [
               ["direct", "23", "Câu trả lời nằm rõ trong 1 đoạn"],
               ["reasoning", "12", "Kết hợp nhiều điều khoản"],
               ["abbreviation", "9", "Dùng HP, HK, GPA, CTĐT..."],
               ["out_of_scope", "6", "Phải từ chối đúng"],
           ])
    _section(doc, "10.2. Các metric đánh giá")
    _subsection(doc, "Retrieval")
    _bullet(doc, "Context Precision: tỷ lệ chunk relevant trong top-k retrieved.")
    _bullet(doc, "Hit Rate@k: 1 nếu có ít nhất 1 chunk relevant trong top-k.")
    _bullet(doc, "MRR: 1/rank của chunk relevant đầu tiên.")
    _bullet(doc, "NDCG: đánh giá chất lượng ranking có tính vị trí.")
    _subsection(doc, "Generation (AI-Judge)")
    _bullet(doc, "Faithfulness (0–1): câu trả lời có bám sát context không.")
    _bullet(doc, "Answer Relevance (0–1): câu trả lời có đúng với câu hỏi và ground truth.")
    _bullet(doc, "Refusal Accuracy: từ chối đúng câu hỏi ngoài phạm vi.")
    _subsection(doc, "Vận hành")
    _bullet(doc, "TTFT: thời gian đến token đầu tiên (~1.820 ms).")
    _bullet(doc, "Total latency, retrieval latency, output tokens.")
    _section(doc, "10.3. Ablation Study — 12 cấu hình")
    _body(doc,
          "Thử nghiệm 3 trục: CHUNK_MODE (semantic/fixed) × EXPAND_ON (bật/tắt) × "
          "TOP_K (5/8/12) = 12 cấu hình. File: services/rag-api/eval/run_eval.py.")
    _table(doc, "Bảng 10.2. Kết quả ablation (trích yếu)",
           ["Cấu hình", "Chunking", "Expansion", "top-k", "Ctx Prec.", "Hit@k", "MRR", "Faith.", "Ans.Rel."],
           [
               ["C1 (đề xuất)", "Semantic", "Bật", "8", "0,71", "0,88", "0,72", "0,83", "0,81"],
               ["C4", "Semantic", "Tắt", "8", "0,61", "0,78", "0,63", "0,78", "0,74"],
               ["C7", "Fixed", "Bật", "8", "0,52", "0,74", "0,58", "0,69", "0,67"],
               ["C10", "Fixed", "Tắt", "8", "0,44", "0,62", "0,49", "0,63", "0,61"],
           ])
    _body(doc,
          "Phân tích: Semantic Chunking +61% Context Precision so với Fixed. "
          "Query Expansion +13% Hit@8. Refusal Accuracy 6/6 = 100% cho mọi cấu hình.")
    _page_break(doc)


def _ch11(doc):
    _chapter(doc, "11. PIPELINE TỔNG HỢP: TỪ CÂU HỎI ĐẾN CÂU TRẢ LỜI")
    _body(doc, "Ví dụ: \"ngành IT học tối thiểu bao nhiêu tín chỉ GPA?\"")
    _code(doc,
          "[1] QUERY EXPANSION (Gemini Flash)\n"
          "    → 4 biến thể tìm kiếm (CTĐT CNTT, số tín chỉ IT, GPA...)\n"
          "[2] EMBEDDING (Gemini API × 4 queries)\n"
          "[3] CHROMADB QUERY (HNSW, top-8 mỗi query)\n"
          "[4] DEDUP + SORT → 12 unique chunks tốt nhất\n"
          "[5] BUILD PROMPT (system 5 bước + context + câu hỏi)\n"
          "[6] GEMINI FLASH stream → SSE\n"
          "[7] FLUTTER UI hiển thị từng token + nguồn tài liệu")
    _page_break(doc)


def _ch12(doc):
    _chapter(doc, "12. TRIỂN KHAI SERVER VỚI DOCKER COMPOSE")
    _section(doc, "12.1. Cấu trúc dịch vụ")
    _table(doc, "Bảng 12.1. Docker Compose services",
           ["Service", "Cổng", "Mô tả"],
           [
               ["rag-api", "8080", "FastAPI + ChromaDB + Gemini"],
               ["staff-console", "3000", "React UI + Express BFF"],
           ])
    _section(doc, "12.2. Biến môi trường quan trọng")
    _table(doc, "Bảng 12.2. Biến môi trường RAG",
           ["Biến", "Mô tả"],
           [
               ["GEMINI_API_KEY", "Khóa Gemini (embed + generate)"],
               ["STUDENT_API_KEY", "Xác thực sinh viên gọi chat"],
               ["ADMIN_API_KEY", "Xác thực ingest tài liệu"],
               ["CHUNK_MODE", "semantic (mặc định) hoặc fixed"],
               ["EXPAND_ON", "1=bật Query Expansion, 0=tắt"],
               ["TOP_K", "8 (số chunk retrieve mỗi query)"],
               ["CHROMA_DATA_DIR", "Thư mục persistent ChromaDB"],
           ])
    _section(doc, "12.3. Flow ingest tài liệu")
    _code(doc,
          "Cán bộ upload PDF trên Staff Console /vectors\n"
          "  → Express BFF proxy multipart\n"
          "  → POST /admin/documents (X-Admin-Key)\n"
          "  → ingest_bytes(): extract → chunk → embed → ChromaDB\n"
          "  → GET /admin/ingest-jobs/{id} → status completed")
    _section(doc, "12.4. Lệnh triển khai")
    _code(doc,
          "cp .env.example .env   # điền GEMINI_API_KEY, API keys\n"
          "docker compose up --build -d\n"
          "curl http://127.0.0.1:8080/health\n"
          "# Staff Console: http://127.0.0.1:3000")
    _page_break(doc)


def _ch13(doc):
    _chapter(doc, "13. TÓM TẮT ĐÓNG GÓP KỸ THUẬT VÀ KẾT QUẢ")
    _section(doc, "13.1. Danh sách kỹ thuật đã implement")
    _table(doc, "Bảng 13.1. Đóng góp kỹ thuật RAG server",
           ["#", "Kỹ thuật", "File", "Đóng góp"],
           [
               ["1", "Semantic Markdown Chunking", "rag.py", "+61% Context Precision"],
               ["2", "Table-aware splitting", "rag.py", "Không cắt bảng quy chế"],
               ["3", "3-line overlap", "rag.py", "Context liên tục"],
               ["4", "Query Expansion + viết tắt", "rag.py", "+13% Hit@8"],
               ["5", "Multi-query retrieval", "rag.py", "Tăng recall"],
               ["6", "Dedup + score-sort", "rag.py", "Loại trùng chunk"],
               ["7", "System prompt 5 bước", "rag.py", "Cấu trúc hóa LLM"],
               ["8", "RAG API + SSE streaming", "main.py", "Client realtime"],
               ["9", "Eval harness 50 câu", "run_eval.py", "Ablation 12 cấu hình"],
               ["10", "AI-judge metrics", "run_eval.py", "Faithfulness/Relevance"],
               ["11", "Exponential backoff", "rag.py", "Xử lý rate limit 429"],
               ["12", "Docker Compose deploy", "docker-compose.yml", "Tái lập môi trường"],
           ])
    _section(doc, "13.2. Kết quả cấu hình đề xuất C1")
    _table(doc, "Bảng 13.2. Kết quả thực nghiệm (Semantic + Expansion + top-k=8)",
           ["Metric", "Giá trị", "Ý nghĩa"],
           [
               ["Context Precision", "0,71", "71% chunk retrieve là relevant"],
               ["Hit Rate@8", "0,88", "88% câu tìm được chunk đúng"],
               ["MRR", "0,72", "Chunk đúng ở rank ~1.4"],
               ["Faithfulness", "0,83", "83% câu trả lời có căn cứ"],
               ["Answer Relevance", "0,81", "81% câu trả lời đúng"],
               ["Refusal Accuracy", "100%", "Từ chối đúng 6/6 câu OOS"],
               ["TTFT", "~1.820 ms", "Token đầu sau ~1.8 giây"],
           ])
    _section(doc, "13.3. Hạn chế")
    _bullet(doc, "Eval set 50 câu — quy mô nhỏ cho kết luận thống kê mạnh.")
    _bullet(doc, "AI-judge không chuẩn hóa giữa các framework.")
    _bullet(doc, "Chưa hỗ trợ PDF scan (chưa tích hợp OCR).")
    _bullet(doc, "Job ingest in-memory — mất khi restart container.")
    _bullet(doc, "Phụ thuộc quota Gemini free tier (~5% lỗi 429 khi tải cao).")
    _page_break(doc)


def _ch14(doc):
    _chapter(doc, "14. BẢNG TỪ KHÓA KỸ THUẬT (GLOSSARY)")
    _table(doc, "",
           ["Thuật ngữ", "Giải thích"],
           [
               ["RAG", "Retrieval-Augmented Generation — tìm kiếm + sinh văn bản"],
               ["Embedding", "Biểu diễn văn bản bằng vector số"],
               ["Chunk / Chunking", "Đoạn văn bản nhỏ / quá trình chia tài liệu"],
               ["ChromaDB", "Vector database lưu embedding"],
               ["HNSW", "Thuật toán tìm hàng xóm gần nhất"],
               ["Cosine Similarity", "Đo góc giữa 2 vector (0–1)"],
               ["Query Expansion", "Mở rộng câu hỏi thành nhiều biến thể"],
               ["SSE", "Server-Sent Events — streaming text từ server"],
               ["TTFT", "Time To First Token — độ trễ token đầu"],
               ["Faithfulness", "Câu trả lời có căn cứ trong context"],
               ["Hallucination", "LLM bịa thông tin không có nguồn"],
               ["Ablation", "Thử nghiệm tắt từng component để đo ảnh hưởng"],
               ["Ingest", "Đưa tài liệu vào hệ thống: extract→chunk→embed→store"],
               ["OOS", "Out-Of-Scope — câu hỏi ngoài phạm vi tài liệu"],
           ])


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    _setup_margins(doc)

    print("[1/15] Trang bìa…")
    _cover(doc)
    print("[2/15] Mục lục…")
    _muc_luc(doc)
    for i, fn in enumerate([
        _ch1, _ch2, _ch3, _ch4, _ch5, _ch6, _ch7, _ch8,
        _ch9, _ch10, _ch11, _ch12, _ch13, _ch14,
    ], start=1):
        print(f"[{i+2}/15] Chương {i}…")
        fn(doc)

    _footer(doc)
    doc.save(str(OUT))
    v = Document(str(OUT))
    print(f"\n✓ Hoàn tất: {OUT}")
    print(f"  Đoạn văn: {len(v.paragraphs)} | Bảng: {len(v.tables)}")


if __name__ == "__main__":
    main()
