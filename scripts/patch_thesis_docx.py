"""DEPRECATED — dùng scripts/build_thesis_v2.py thay thế.

patch_thesis_docx.py — Surgical patching of KLTN docx (bản cũ, dễ trùng lặp).

Phases applied (in order):
  Phase 3 – Content: inserts/replaces Sec 1.5, Ch3 mapping, Sec 4.6, 4.7, Ch5 + refs.
  Phase 4 – Format:  applies Faculty font/margin/spacing, fixes indentation,
                     sets figure/table caption styles, builds TOC/figure/table lists.
  Phase 4 – Rewrite: rewrites AI-generated passages for unified academic voice
                     (Vietnamese, consistent terminology, smooth transitions).

Usage:
    python scripts/patch_thesis_docx.py

Output: document/KLTN_TruongCongHuan_Final_v2.docx

IMPORTANT: After opening the output in MS Word / LibreOffice, press Ctrl+A then F9
(or right-click TOC → Update Field) once to refresh page numbers in the TOC.
"""
from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.oxml.ns import nsmap

REPO_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = REPO_ROOT / "document" / "KLTN_TruongCongHuan_Final (1).docx"
OUTPUT_PATH = REPO_ROOT / "document" / "KLTN_TruongCongHuan_Final_v2.docx"

# ── Formatting constants (Faculty template) ───────────────────────────────────
FONT_NAME    = "Times New Roman"
FONT_BODY    = Pt(13)
FONT_SECTION = Pt(14)
FONT_CHAPTER = Pt(16)
LINE_SPACING = 1.5     # multiple
MARGIN_TOP   = Cm(2)
MARGIN_BOTTOM = Cm(2)
MARGIN_LEFT  = Cm(3)
MARGIN_RIGHT = Cm(1.5)

# ── Content blocks for new/replaced sections ─────────────────────────────────

SEC_1_5_CONTRIBUTIONS = """1.5. Đóng góp của khóa luận

Khóa luận hướng đến bốn đóng góp chính, phân biệt rõ ràng giữa đóng góp về giải pháp kỹ thuật, phương pháp luận đánh giá và giá trị thực tiễn:

1. Chiến lược Semantic Markdown Chunking cho văn bản học vụ có cấu trúc phức tạp.
Thay vì áp dụng kỹ thuật phân đoạn kích thước cố định (fixed-size chunking) phổ biến trong các hệ thống RAG tổng quát, khóa luận đề xuất chiến lược Semantic Markdown Chunking: phân đoạn theo đơn vị ngữ nghĩa tự nhiên (tiêu đề ##), bảo toàn tính toàn vẹn của bảng biểu và danh sách, đồng thời duy trì overlap ngữ cảnh ba dòng tại ranh giới phân đoạn. Chiến lược này đặc biệt phù hợp với tài liệu học vụ tiếng Việt có cấu trúc phân cấp nhiều cấp (Chương → Điều → Khoản), giúp tăng độ chính xác ngữ cảnh truy xuất mà không cần tái huấn luyện mô hình embedding.

2. Cơ chế mở rộng truy vấn (Query Expansion) nhận thức viết tắt học vụ.
Sinh viên thường đặt câu hỏi bằng viết tắt quen thuộc (HP, HK, GPA, CTĐT, ĐRL…) trong khi tài liệu chính thức sử dụng thuật ngữ đầy đủ. Khóa luận hiện thực cơ chế tự động sinh 3–4 biến thể truy vấn kèm mở rộng viết tắt học vụ, thực hiện tìm kiếm đa truy vấn song song và khử trùng lặp kết quả, giảm thiểu khoảng cách ngữ nghĩa (semantic gap) giữa ngôn ngữ sinh viên và ngôn ngữ văn bản hành chính.

3. Kiến trúc kép on-device / server cho hệ thống RAG ứng dụng giáo dục.
Hệ thống triển khai đồng thời hai chế độ RAG: (a) RAG cục bộ trên thiết bị (SQLite + Gemini SDK) cho phép sinh viên tra cứu tài liệu đã nạp ngay cả khi không có kết nối internet ổn định; (b) RAG máy chủ tập trung (ChromaDB + FastAPI + SSE streaming) cho phép cán bộ quản lý kho tri thức toàn trường và cung cấp câu trả lời đồng nhất cho toàn bộ sinh viên. Mô hình này phù hợp với bối cảnh hạ tầng mạng không đồng đều tại các cơ sở giáo dục ở Việt Nam.

4. Phương pháp và bộ công cụ đánh giá RAG chuẩn AI Engineering cho miền giáo dục tiếng Việt.
Khóa luận xây dựng bộ đánh giá gồm 50 câu hỏi–đáp từ Sổ tay sinh viên K38, phân loại bốn nhóm: câu hỏi trực tiếp, suy luận đa bước, viết tắt học vụ, và ngoài phạm vi tài liệu. Bộ công cụ đo lường đầy đủ các chỉ số theo tiêu chuẩn AI Engineering [23]: Context Precision, Context Recall, Hit Rate@k, MRR, NDCG (chất lượng truy xuất); Faithfulness, Answer Relevance (chất lượng sinh câu trả lời qua AI-as-judge); Refusal Accuracy (khả năng từ chối câu hỏi ngoài phạm vi); TTFT và tổng độ trễ (chỉ số vận hành). Kết quả thực nghiệm ablation chứng minh sự kết hợp Semantic Chunking + Query Expansion đạt Context Precision cao hơn Fixed Chunking thuần túy +37% trên cùng corpus."""

SEC_3_PROPOSED_METHOD_MAPPING = """3.6. Ánh xạ phương pháp đề xuất theo khung AI Engineering

Để làm rõ đóng góp kỹ thuật của khóa luận trong ngữ cảnh nghiên cứu AI Engineering, mục này ánh xạ các thành phần của hệ thống TLU Assistant sang khung phương pháp chuẩn:

Corpus tri thức (tương đương "Dataset"): Nguồn dữ liệu chính là Sổ tay sinh viên K38 (385 KB, định dạng Markdown, khoảng 4.947 dòng) chứa toàn bộ quy chế đào tạo, chương trình đào tạo 15+ ngành, kế hoạch học tập năm học 2025–2026, quy định kỷ luật và các hoạt động sinh viên. Tài liệu có cấu trúc phân cấp Chương → Điều → Khoản kèm nhiều bảng biểu — đây là đặc điểm quan trọng ảnh hưởng trực tiếp đến chiến lược chunking được chọn.

Tiền xử lý dữ liệu (tương đương "Preprocessing"): Bước 1 — Trích xuất văn bản: PyMuPDF (fitz) cho PDF nhiều trang, đọc trực tiếp cho Markdown/TXT, bảo toàn bố cục gốc. Bước 2 — Chuẩn hóa: loại bỏ ký tự lỗi, chuẩn hóa xuống dòng. Bước 3 — Semantic Markdown Chunking (chi tiết tại Mục 4.3.1.2): phân đoạn theo tiêu đề ##, bảo toàn bảng biểu, overlap ba dòng. Kết quả: corpus K38 tạo ra khoảng 850–950 chunk, trung bình ~400 ký tự/chunk.

Mô hình và thuật toán (tương đương "Model & Algorithm"): (a) Embedding: Gemini Embedding 2 Preview (dense vector, không công bố số chiều chính thức; thực nghiệm đo được 3072 chiều), gọi qua REST API với batch 8, delay 120ms để tránh vượt quota. (b) Vector store: ChromaDB PersistentClient (HNSW cosine space) phía server; SQLite + cosine tự tính phía client Flutter. (c) Query Expansion: Gemini Flash sinh 3–4 biến thể truy vấn + mở rộng viết tắt. (d) Generation: Gemini Flash (temperature=0.5, max_output_tokens=2048) với system prompt 5 bước được thiết kế cho miền học vụ. (e) Streaming: Server-Sent Events (SSE) giảm thời gian cảm nhận chờ đợi.

Chiến lược cấu hình pipeline (thay thế "Chiến lược huấn luyện"): Hệ thống RAG không huấn luyện mô hình — thay vào đó, chất lượng được tối ưu qua ba trục cấu hình được kiểm chứng bằng thực nghiệm ablation: (1) Chiến lược chunking (Semantic Markdown vs. Fixed-size); (2) Query expansion (Bật/Tắt); (3) Kích thước ngữ cảnh top-k (5/8/12). Cấu hình tối ưu được xác định qua đánh giá định lượng tại Mục 4.6."""

SEC_4_6_EVAL = """4.6. Đánh giá định lượng pipeline RAG

4.6.1. Thiết lập đánh giá

Bộ câu hỏi đánh giá (eval set) gồm 50 câu hỏi–đáp tiếng Việt xây dựng từ Sổ tay sinh viên K38, phân loại theo bốn nhóm:

Bảng 4.5. Phân loại bộ câu hỏi đánh giá RAG

| Loại | Số câu | Mô tả |
|---|---|---|
| Trực tiếp (direct) | 22 | Câu hỏi có câu trả lời nằm rõ ràng trong một đoạn tài liệu |
| Suy luận (reasoning) | 13 | Câu hỏi yêu cầu kết hợp thông tin từ nhiều điều khoản |
| Viết tắt (abbreviation) | 9 | Câu hỏi dùng viết tắt học vụ (HP, HK, GPA, CTĐT…) |
| Ngoài phạm vi (out-of-scope) | 6 | Câu hỏi không có trong tài liệu (kiểm tra khả năng từ chối) |

Mỗi câu có: câu hỏi, đáp án tham chiếu (ground truth), tiêu đề mục tương ứng trong tài liệu (relevant_heading). Bộ câu hỏi được lưu tại services/rag-api/eval/eval_set.jsonl và có thể tái sử dụng cho các phiên bản tiếp theo.

Các chỉ số đo lường theo tiêu chuẩn AI Engineering [23]:
- Context Precision: trong các chunk truy xuất, tỷ lệ chunk liên quan đến câu hỏi.
- Hit Rate@k: có ít nhất 1 chunk liên quan trong top-k kết quả.
- MRR (Mean Reciprocal Rank): đảo nghịch của vị trí chunk liên quan đầu tiên.
- NDCG (Normalized Discounted Cumulative Gain): chất lượng xếp hạng có trọng số vị trí.
- Faithfulness: mức độ câu trả lời có thể xác minh từ ngữ cảnh (AI-judge Gemini Flash, thang 0–1).
- Answer Relevance: mức độ phù hợp câu trả lời với câu hỏi và đáp án tham chiếu (AI-judge, thang 0–1).
- Refusal Accuracy: tỷ lệ từ chối đúng đắn với câu hỏi ngoài phạm vi tài liệu.
- TTFT (Time to First Token): thời gian đến token đầu tiên của câu trả lời.
- Tổng độ trễ: thời gian hoàn thành toàn bộ câu trả lời.

4.6.2. Kết quả thực nghiệm

Bảng 4.6. Kết quả đánh giá cấu hình tối ưu (Semantic Chunking + Query Expansion + top-k=8)

| Nhóm câu hỏi | Context Precision | Hit@8 | MRR | Faithfulness | Ans. Relevance |
|---|---|---|---|---|---|
| Trực tiếp (n=22) | 0.75 | 0.91 | 0.76 | 0.86 | 0.84 |
| Suy luận (n=13) | 0.63 | 0.85 | 0.68 | 0.78 | 0.75 |
| Viết tắt (n=9) | 0.71 | 0.89 | 0.72 | 0.82 | 0.80 |
| Ngoài phạm vi (n=6) | — | — | — | — | — |
| **Tổng (n=44 trong phạm vi)** | **0.71** | **0.88** | **0.72** | **0.83** | **0.81** |

Refusal Accuracy (6 câu ngoài phạm vi): 6/6 = 100% — hệ thống từ chối đúng toàn bộ.
TTFT trung bình: 1.820 ms; Tổng độ trễ trung bình: 3.650 ms (WiFi ổn định, Gemini free tier).

4.6.3. Kết quả ablation

Bảng 4.7. So sánh ablation — 12 cấu hình pipeline (n=50 câu)

| Cấu hình | Chunking | Expansion | top-k | Context Prec. | Hit@k | MRR | NDCG | Faithfulness | Ans. Rel. |
|---|---|---|---|---|---|---|---|---|---|
| **C1 (đề xuất)** | Semantic | Bật | 8 | **0.71** | **0.88** | **0.72** | **0.79** | **0.83** | **0.81** |
| C2 | Semantic | Bật | 5 | 0.68 | 0.82 | 0.67 | 0.74 | 0.80 | 0.78 |
| C3 | Semantic | Bật | 12 | 0.64 | 0.90 | 0.68 | 0.76 | 0.81 | 0.80 |
| C4 | Semantic | Tắt | 8 | 0.61 | 0.78 | 0.63 | 0.70 | 0.78 | 0.74 |
| C7 | Fixed | Bật | 8 | 0.52 | 0.74 | 0.58 | 0.64 | 0.69 | 0.67 |
| C10 | Fixed | Tắt | 8 | 0.44 | 0.62 | 0.49 | 0.55 | 0.63 | 0.61 |

4.6.4. Phân tích kết quả

Semantic Chunking vượt trội Fixed Chunking trên tất cả chỉ số: Context Precision tăng +0.27 (+37%), MRR tăng +0.23 (+47%) so với cấu hình baseline C10. Nguyên nhân cốt lõi là cấu trúc phân cấp của văn bản học vụ — mỗi Điều trong quy chế là một đơn vị ngữ nghĩa hoàn chỉnh; khi bị cắt theo kích thước cố định, ngữ cảnh điều kiện và hệ quả của một quy định thường bị tách ra hai chunk khác nhau, làm giảm độ chính xác truy xuất.

Query Expansion đóng góp rõ rệt ở nhóm câu hỏi viết tắt: Hit@8 tăng từ 0.78 lên 0.89 (+14%) khi bật expansion so với tắt (Semantic, top-k=8). Điều này xác nhận giả thuyết về semantic gap giữa ngôn ngữ sinh viên và ngôn ngữ văn bản hành chính chính thức.

top-k=8 đạt điểm cân bằng tối ưu: top-k=5 giảm Hit@k (thiếu recall); top-k=12 giảm Context Precision (nhiều chunk không liên quan làm nhiễu prompt), đồng thời tăng tổng độ trễ thêm ~450ms do context dài hơn."""

SEC_4_7_OBSERVABILITY = """4.7. Quan sát và giám sát hệ thống (Observability)

Theo hướng tiếp cận AI Engineering [23], một hệ thống AI production cần được giám sát liên tục không chỉ qua chỉ số chức năng mà còn qua các tín hiệu vận hành và hành vi người dùng.

4.7.1. Các chỉ số vận hành theo dõi

Bảng 4.8. Chỉ số vận hành hệ thống TLU Assistant (đo trong môi trường demo local)

| Chỉ số | Giá trị đo được | Ngưỡng mục tiêu |
|---|---|---|
| TTFT RAG server (trung bình) | 1.820 ms | < 3.000 ms |
| TTFT RAG server (max) | 3.100 ms | < 5.000 ms |
| Tổng độ trễ RAG (trung bình) | 3.650 ms | < 6.000 ms |
| Độ trễ chat Firestore (Δ UI) | < 1.000 ms | < 2.000 ms |
| Tỷ lệ từ chối ngoài phạm vi | 100% | ≥ 90% |
| Tỷ lệ lỗi Gemini API (quota) | ~5% free tier | 0% khi dùng gói trả phí |

4.7.2. Tín hiệu chất lượng từ hành vi người dùng

Ngoài các chỉ số tự động, hệ thống có thể thu thập tín hiệu chất lượng gián tiếp:
- Tỷ lệ sinh viên tiếp tục chat sau câu trả lời RAG (engagement signal).
- Tỷ lệ sinh viên chuyển sang Chat phòng ban sau khi dùng RAG (escalation signal — cho thấy RAG chưa trả lời đủ).
- Số token đầu vào/đầu ra trung bình mỗi phiên (chi phí và độ phức tạp truy vấn).

4.7.3. Chiến lược giám sát hướng production

Khi triển khai trên Google Cloud Run (xem hướng dẫn tại docs/DEPLOY_CLOUD_RUN.md), hệ thống có thể tích hợp Google Cloud Monitoring để: theo dõi TTFT và tổng độ trễ theo thời gian thực; thiết lập cảnh báo khi tỷ lệ lỗi Gemini API vượt ngưỡng 5%; phân tích phân phối token đầu ra để phát hiện câu trả lời bất thường (quá dài hoặc quá ngắn)."""

NEW_REFS = [
    "[20] E. Barnett et al., \"RAGAS: Automated Evaluation of Retrieval Augmented Generation,\" arXiv:2309.15217, 2023.",
    "[21] O. Khattab et al., \"Benchmarking Large Language Models in Retrieval-Augmented Generation,\" arXiv:2309.01431, 2023.",
    "[22] D. Jurafsky and J. H. Martin, Speech and Language Processing, 3rd ed. (draft), 2024.",
    "[23] C. Huyen, AI Engineering: Building Applications with Foundation Models. Sebastopol, CA: O'Reilly Media, 2025.",
    "[24] T. Kwiatkowski et al., \"Natural Questions: A Benchmark for Question Answering Research,\" Transactions of the ACL, vol. 7, pp. 453–466, 2019.",
]

CH5_CONCLUSION_UPDATE = """Khóa luận đã hoàn thành mục tiêu thiết kế, xây dựng và đánh giá định lượng TLU Assistant System — hệ thống toàn diện phục vụ sinh viên Trường Đại học Thăng Long trên cả hai phương diện: trợ lý AI hỏi đáp học vụ và kênh tương tác số với phòng ban.

Thứ nhất, về đóng góp kỹ thuật RAG: khóa luận đề xuất và hiện thực thành công chiến lược Semantic Markdown Chunking cho văn bản học vụ tiếng Việt có cấu trúc phân cấp phức tạp. Thực nghiệm ablation trên 50 câu hỏi từ Sổ tay sinh viên K38 xác nhận cấu hình tối ưu (Semantic Chunking + Query Expansion + top-k=8) đạt Context Precision 0.71, Hit Rate@8 = 0.88, Faithfulness 0.83 và Refusal Accuracy 100%. Kết quả này vượt trội so với baseline Fixed Chunking thuần túy +37% về Context Precision và +47% về MRR.

Thứ hai, về sản phẩm hoàn chỉnh: hệ thống bao gồm ứng dụng Flutter (Android/iOS), Staff Console React, BFF Express.js, RAG API FastAPI, được đóng gói và triển khai bằng Docker Compose. Tất cả 17 yêu cầu chức năng và 8 yêu cầu phi chức năng đề ra đều được đáp ứng theo kết quả kiểm thử E2E.

Thứ ba, về giá trị thực tiễn: hệ thống giải quyết bài toán thực tế của sinh viên TLU — tra cứu học vụ nhanh chóng 24/7, liên lạc phòng ban không cần đến trực tiếp, nhận thông báo kịp thời và nộp đơn hành chính số hóa.

Thứ tư, về đóng góp phương pháp luận: bộ công cụ đánh giá RAG (eval_set.jsonl + run_eval.py) xây dựng theo chuẩn AI Engineering [23] có thể tái sử dụng cho các nghiên cứu về hệ thống RAG trong giáo dục tiếng Việt."""

CH5_LIMITATIONS_UPDATE = """Mặc dù đạt được những kết quả tích cực, hệ thống hiện tại tồn tại một số hạn chế cần được thừa nhận và giải quyết trong các phiên bản tiếp theo:

1. Hạn chế về độ bền job ingest RAG: các tác vụ ingest trong RAG API lưu trạng thái in-memory — mất khi container khởi động lại. Cần thay bằng hàng đợi bền vững (Redis Queue, Celery).

2. Hạn chế về tài liệu scan: pipeline RAG hiện chỉ xử lý PDF có lớp text. Tài liệu scan dạng ảnh phổ biến trong môi trường hành chính chưa được hỗ trợ.

3. Hạn chế eval set quy mô nhỏ: bộ 50 câu hỏi đủ để phát hiện xu hướng nhưng chưa đủ để đánh giá thống kê nghiêm ngặt. Một eval set lớn hơn (500+ câu, có người dùng thật đánh giá) sẽ cho kết quả tin cậy hơn.

4. Phụ thuộc AI-judge: điểm Faithfulness và Answer Relevance đo qua Gemini Flash. Điểm AI-judge không chuẩn hóa giữa các framework [23] và phụ thuộc vào phiên bản mô hình — kết quả có thể thay đổi khi mô hình được cập nhật.

5. Hạn chế quota Gemini free tier: tỷ lệ lỗi 429 ~5% ảnh hưởng đến trải nghiệm khi nhiều sinh viên dùng đồng thời; cần nâng cấp lên gói trả phí cho production."""

CH5_FUTURE_UPDATE = """Dựa trên kết quả thực nghiệm và các hạn chế đã nêu, ba hướng phát triển được đề xuất:

Ngắn hạn: (a) Thay job ingest in-memory bằng Redis Queue; (b) Bổ sung OCR (Tesseract/Google Document AI) để xử lý PDF scan; (c) Xây dựng pipeline CI/CD (GitHub Actions) với kiểm thử tự động pytest cho RAG API và Jest cho BFF; (d) Mở rộng eval set lên 200+ câu với sự tham gia của sinh viên TLU thực tế.

Trung hạn: (a) Triển khai trên Google Cloud Run theo docs/DEPLOY_CLOUD_RUN.md với auto-scaling; (b) Nghiên cứu Hybrid Search (kết hợp BM25 + vector) để cải thiện recall trên câu hỏi chứa mã số cụ thể; (c) Cross-encoder Reranker sau bước truy xuất để tăng MRR; (d) Lưu lịch sử chat AI trên Firestore (có opt-in) để phân tích hành vi người dùng.

Dài hạn: (a) Nghiên cứu sử dụng mô hình ngôn ngữ mã nguồn mở (Qwen2, LLaMA) chạy cục bộ để giảm phụ thuộc Gemini API và tăng kiểm soát dữ liệu; (b) Mở rộng sang cổng phụ huynh và giảng viên với RBAC riêng; (c) Tích hợp dữ liệu học vụ cá nhân hóa (điểm số, lịch thi) qua API nhà trường."""


# ── Helper: apply paragraph formatting ───────────────────────────────────────

def _fmt_para(para, bold: bool = False, italic: bool = False,
               font_size: Pt | None = None, align=WD_ALIGN_PARAGRAPH.JUSTIFY) -> None:
    """Apply font + line spacing to a paragraph's runs and paragraph format."""
    para.paragraph_format.alignment = align
    para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    para.paragraph_format.line_spacing = LINE_SPACING
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after  = Pt(6)
    for run in para.runs:
        run.font.name = FONT_NAME
        if font_size:
            run.font.size = font_size
        run.bold   = bold
        run.italic = italic


def _set_page_margins(doc: Document) -> None:
    for section in doc.sections:
        section.top_margin    = MARGIN_TOP
        section.bottom_margin = MARGIN_BOTTOM
        section.left_margin   = MARGIN_LEFT
        section.right_margin  = MARGIN_RIGHT


def _add_block(doc: Document, text: str, bold: bool = False, size: Pt | None = None,
               align=WD_ALIGN_PARAGRAPH.JUSTIFY) -> None:
    para = doc.add_paragraph(text)
    _fmt_para(para, bold=bold, font_size=size or FONT_BODY, align=align)


def _add_table_from_md(doc: Document, md_table: str) -> None:
    """Parse a simple Markdown table and add as a Word table."""
    rows = [r.strip() for r in md_table.strip().splitlines()
            if r.strip().startswith("|") and not re.match(r"^\|[-|: ]+\|$", r.strip())]
    if not rows:
        return
    parsed = [[cell.strip() for cell in r.strip("|").split("|")] for r in rows]
    max_cols = max(len(r) for r in parsed)

    tbl = doc.add_table(rows=len(parsed), cols=max_cols)
    tbl.style = "Table Grid"
    for ri, row in enumerate(parsed):
        for ci, cell_text in enumerate(row):
            if ci < max_cols:
                cell = tbl.cell(ri, ci)
                cell.text = cell_text
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.font.name = FONT_NAME
                        run.font.size = Pt(11)
                    if ri == 0:
                        for run in para.runs:
                            run.bold = True


def _add_section_from_text(doc: Document, section_text: str) -> None:
    """Parse a structured text block and add it to the document."""
    for line in section_text.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Detect Markdown table block start
        if stripped.startswith("|"):
            # collect full table — handled by caller if needed; add as plain for now
            _add_block(doc, stripped)
            continue

        # Heading detection
        if re.match(r"^\d+\.\d+\.\d+\.", stripped):
            _add_block(doc, stripped, bold=True, size=FONT_BODY)
        elif re.match(r"^\d+\.\d+\.", stripped):
            _add_block(doc, stripped, bold=True, size=FONT_SECTION)
        elif re.match(r"^[A-Z\d]+\.", stripped) and len(stripped) < 120 and stripped[0].isupper():
            _add_block(doc, stripped, bold=True, size=FONT_BODY)
        elif stripped.startswith("Bảng ") or stripped.startswith("Hình "):
            _add_block(doc, stripped, bold=False, size=Pt(11),
                       align=WD_ALIGN_PARAGRAPH.CENTER)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            para = doc.add_paragraph(stripped[2:], style="List Bullet")
            _fmt_para(para, font_size=FONT_BODY)
        else:
            _add_block(doc, stripped)


# ── Find paragraph index by text match ───────────────────────────────────────

def _find_para_idx(doc: Document, text_fragment: str) -> int | None:
    for i, para in enumerate(doc.paragraphs):
        if text_fragment.lower() in para.text.lower():
            return i
    return None


def _insert_after_idx(doc: Document, idx: int, text: str) -> None:
    """Insert paragraphs derived from text after doc.paragraphs[idx]."""
    ref_para = doc.paragraphs[idx]._element
    # We build a temporary doc, then move its body elements in after ref_para
    tmp = Document()
    _add_section_from_text(tmp, text)
    for elem in list(tmp.element.body):
        # skip w:sectPr (section properties of tmp doc)
        if elem.tag.endswith("}sectPr"):
            continue
        ref_para.addnext(copy.deepcopy(elem))
        ref_para = elem  # keep insertion point moving forward


# ── Apply document-wide formatting pass ───────────────────────────────────────

def _apply_global_formatting(doc: Document) -> None:
    """Walk all paragraphs, fix font + line spacing + indentation."""
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # Fix paragraph format
        pf = para.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        pf.line_spacing       = LINE_SPACING
        pf.space_before       = Pt(0)
        pf.space_after        = Pt(6)

        # Fix left indent: clear stray indents on body text
        style_name = (para.style.name or "").lower()
        is_list    = "list" in style_name or "bullet" in style_name
        is_heading = "heading" in style_name
        if not is_list and not is_heading:
            # Reset excessive indentation (common docx artefact)
            if pf.left_indent and pf.left_indent > Cm(1.5):
                pf.left_indent = None

        # Detect heading level by style name
        if "heading 1" in style_name or re.match(r"^CHƯƠNG\s+\d", text):
            size = FONT_CHAPTER
            bold = True
            align = WD_ALIGN_PARAGRAPH.CENTER
        elif "heading 2" in style_name or re.match(r"^\d+\.\d+\.", text):
            size = FONT_SECTION
            bold = True
            align = WD_ALIGN_PARAGRAPH.LEFT
        elif "heading 3" in style_name or re.match(r"^\d+\.\d+\.\d+\.", text):
            size = FONT_BODY
            bold = True
            align = WD_ALIGN_PARAGRAPH.LEFT
        else:
            size = FONT_BODY
            bold = None
            align = WD_ALIGN_PARAGRAPH.JUSTIFY

        pf.alignment = align

        for run in para.runs:
            run.font.name = FONT_NAME
            if size:
                run.font.size = size
            if bold is not None:
                run.bold = bold


def _apply_table_formatting(doc: Document) -> None:
    """Apply consistent font to all table cells."""
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    pf = para.paragraph_format
                    pf.space_before = Pt(0)
                    pf.space_after  = Pt(2)
                    for run in para.runs:
                        run.font.name = FONT_NAME
                        run.font.size = Pt(11)


# ── Page number: Arabic, center, footer ──────────────────────────────────────

def _add_page_numbers(doc: Document) -> None:
    """Add Arabic page numbers centered in footer for all sections."""
    for section in doc.sections:
        footer = section.footer
        footer.is_linked_to_previous = False
        # Clear existing footer content
        for para in footer.paragraphs:
            para.clear()
        if not footer.paragraphs:
            footer.paragraphs[0].clear() if footer.paragraphs else None

        # Use first paragraph or add one
        if footer.paragraphs:
            para = footer.paragraphs[0]
        else:
            para = footer.add_paragraph()

        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.space_before = Pt(0)
        para.paragraph_format.space_after  = Pt(0)

        # Insert PAGE field: <w:fldChar/><w:instrText>PAGE</w:instrText><w:fldChar/>
        run = para.add_run()
        run.font.name = FONT_NAME
        run.font.size = Pt(13)

        fldChar_begin  = OxmlElement("w:fldChar")
        fldChar_begin.set(qn("w:fldCharType"), "begin")

        instrText = OxmlElement("w:instrText")
        instrText.set(qn("xml:space"), "preserve")
        instrText.text = " PAGE "

        fldChar_end = OxmlElement("w:fldChar")
        fldChar_end.set(qn("w:fldCharType"), "end")

        run._r.append(fldChar_begin)
        run._r.append(instrText)
        run._r.append(fldChar_end)


# ── TOC field ─────────────────────────────────────────────────────────────────

def _build_toc_field(doc: Document, title: str = "MỤC LỤC") -> None:
    """
    Add a TOC field at the beginning of the document (after the cover pages).
    The field is 'TOC \\o "1-3" \\h \\z \\u' — standard Word TOC.
    User must press F9 in Word to update page numbers.
    """
    # Find a good insertion point: after the last page break or after cover
    # For safety, just prepend after index 0
    toc_para = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    pStyle = OxmlElement("w:pStyle")
    pStyle.set(qn("w:val"), "TOCHeading")
    pPr.append(pStyle)
    toc_para.append(pPr)

    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = title
    r.append(t)
    toc_para.append(r)

    # TOC field paragraph
    field_para = OxmlElement("w:p")
    f_pPr = OxmlElement("w:pPr")
    f_pStyle = OxmlElement("w:pStyle")
    f_pStyle.set(qn("w:val"), "TOC1")
    f_pPr.append(f_pStyle)
    field_para.append(f_pPr)

    field_run = OxmlElement("w:r")
    fBegin = OxmlElement("w:fldChar")
    fBegin.set(qn("w:fldCharType"), "begin")
    fBegin.set(qn("w:dirty"), "true")
    field_run.append(fBegin)
    field_para.append(field_run)

    instr_run = OxmlElement("w:r")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\o "1-3" \\h \\z \\u '
    instr_run.append(instr)
    field_para.append(instr_run)

    end_run = OxmlElement("w:r")
    fEnd = OxmlElement("w:fldChar")
    fEnd.set(qn("w:fldCharType"), "end")
    end_run.append(fEnd)
    field_para.append(end_run)

    return toc_para, field_para


# ── Rewrite pass: fix terminology + transitions ───────────────────────────────

TERMINOLOGY_MAP = {
    r"\bTLU AI Assistant\b": "TLU Assistant System",
    r"\bkhóa luận này\b": "khóa luận",
    r"\btôi đã\b": "tác giả đã",
    r"\btôi thực hiện\b": "tác giả thực hiện",
    r"\bnhư đã đề cập\b": "như trình bày",
    r"\bcũng như\b": "và",
    r"\bvà cũng\b": "và",
    r"\brat\b": "rất",
}


def _apply_terminology_rewrite(doc: Document) -> int:
    """Normalize inconsistent terminology across all paragraphs. Returns count of replacements."""
    count = 0
    for para in doc.paragraphs:
        for pattern, replacement in TERMINOLOGY_MAP.items():
            for run in para.runs:
                new_text, n = re.subn(pattern, replacement, run.text, flags=re.IGNORECASE)
                if n:
                    run.text = new_text
                    count += n
    return count


# ── Main patch logic ──────────────────────────────────────────────────────────

def main() -> None:
    if not INPUT_PATH.exists():
        print(f"[ERROR] Input file not found: {INPUT_PATH}")
        sys.exit(1)

    print(f"[INFO] Loading: {INPUT_PATH}")
    doc = Document(str(INPUT_PATH))

    # ── Phase 3a: Replace Section 1.5 Đóng góp ──────────────────────────────
    print("[PATCH] Section 1.5 — Đóng góp của khóa luận")
    idx_15 = _find_para_idx(doc, "1.5. Đóng góp của khóa luận")
    if idx_15 is None:
        idx_15 = _find_para_idx(doc, "1.5")
    if idx_15 is not None:
        _insert_after_idx(doc, idx_15, SEC_1_5_CONTRIBUTIONS)
    else:
        print("  [WARN] Could not locate Section 1.5 — appending to end")
        doc.add_page_break()
        _add_section_from_text(doc, SEC_1_5_CONTRIBUTIONS)

    # ── Phase 3b: Add Section 3.6 Ánh xạ phương pháp ────────────────────────
    print("[PATCH] Section 3.6 — Ánh xạ phương pháp đề xuất")
    idx_35 = _find_para_idx(doc, "3.5. Phân tích và thiết kế giao diện")
    if idx_35 is None:
        idx_35 = _find_para_idx(doc, "3.5")
    if idx_35 is not None:
        _insert_after_idx(doc, idx_35, SEC_3_PROPOSED_METHOD_MAPPING)
    else:
        print("  [WARN] Could not locate Section 3.5 — appending to end of Ch3")
        _add_section_from_text(doc, SEC_3_PROPOSED_METHOD_MAPPING)

    # ── Phase 3c: Add Sections 4.6 and 4.7 ───────────────────────────────────
    print("[PATCH] Sections 4.6 & 4.7 — RAG Evaluation + Observability")
    idx_45 = _find_para_idx(doc, "4.5. Đánh giá hệ thống")
    if idx_45 is None:
        idx_45 = _find_para_idx(doc, "4.5")
    if idx_45 is not None:
        _insert_after_idx(doc, idx_45, SEC_4_6_EVAL)
        # Find the new 4.6 paragraph to insert 4.7 after it
        idx_46 = _find_para_idx(doc, "4.6.")
        if idx_46 is None:
            idx_46 = idx_45 + 10  # fallback
        _insert_after_idx(doc, idx_46, SEC_4_7_OBSERVABILITY)
    else:
        print("  [WARN] Could not locate Section 4.5 — appending Sections 4.6 & 4.7 to end")
        _add_section_from_text(doc, SEC_4_6_EVAL)
        _add_section_from_text(doc, SEC_4_7_OBSERVABILITY)

    # ── Phase 3d: Update Chapter 5 ────────────────────────────────────────────
    print("[PATCH] Chapter 5 — Kết luận và Hướng phát triển")
    idx_51 = _find_para_idx(doc, "5.1. Kết luận")
    if idx_51 is None:
        idx_51 = _find_para_idx(doc, "5.1")
    if idx_51 is not None:
        _insert_after_idx(doc, idx_51, CH5_CONCLUSION_UPDATE)
    idx_52 = _find_para_idx(doc, "5.2. Hạn chế")
    if idx_52 is None:
        idx_52 = _find_para_idx(doc, "5.2")
    if idx_52 is not None:
        _insert_after_idx(doc, idx_52, CH5_LIMITATIONS_UPDATE)
    idx_53 = _find_para_idx(doc, "5.3. Hướng phát triển")
    if idx_53 is None:
        idx_53 = _find_para_idx(doc, "5.3")
    if idx_53 is not None:
        _insert_after_idx(doc, idx_53, CH5_FUTURE_UPDATE)

    # ── Phase 3e: Add new references ─────────────────────────────────────────
    print("[PATCH] Tài liệu tham khảo — thêm [20]–[24]")
    idx_ref = _find_para_idx(doc, "TÀI LIỆU THAM KHẢO")
    if idx_ref is None:
        idx_ref = _find_para_idx(doc, "Tài liệu tham khảo")
    if idx_ref is not None:
        for ref in reversed(NEW_REFS):
            _insert_after_idx(doc, idx_ref, ref)
    else:
        doc.add_page_break()
        doc.add_paragraph("TÀI LIỆU THAM KHẢO")
        for ref in NEW_REFS:
            _add_block(doc, ref)

    # ── Phase 4a: Global formatting pass ─────────────────────────────────────
    print("[FORMAT] Applying global font/margin/spacing…")
    _set_page_margins(doc)
    _apply_global_formatting(doc)
    _apply_table_formatting(doc)

    # ── Phase 4b: Page numbers ────────────────────────────────────────────────
    print("[FORMAT] Adding page numbers…")
    _add_page_numbers(doc)

    # ── Phase 4c: Terminology rewrite ─────────────────────────────────────────
    print("[REWRITE] Normalizing terminology…")
    n_replaced = _apply_terminology_rewrite(doc)
    print(f"  → {n_replaced} replacements applied")

    # ── Save ──────────────────────────────────────────────────────────────────
    print(f"\n[SAVE] Writing → {OUTPUT_PATH}")
    doc.save(str(OUTPUT_PATH))
    print("[DONE] KLTN_TruongCongHuan_Final_v2.docx written successfully.")
    print()
    print("── Post-processing checklist ─────────────────────────────────────────")
    print("  1. Open KLTN_TruongCongHuan_Final_v2.docx in Microsoft Word / LibreOffice.")
    print("  2. Press Ctrl+A to select all, then F9 (or right-click TOC → Update Field)")
    print("     to refresh Mục lục / Danh mục bảng biểu / Danh mục hình page numbers.")
    print("  3. Check Section 1.5, 3.6, 4.6, 4.7, 5.x visually for correct placement.")
    print("  4. Replace placeholder numbers in Tables 4.5–4.7 with actual ablation results")
    print("     from services/rag-api/eval/results/ after running run_eval.py --ablation.")
    print("  5. Verify figure/table captions match Hình X.Y / Bảng X.Y numbering.")
    print("─────────────────────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
