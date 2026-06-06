"""Nội dung KLTN v3 — khung Khoa Trí tuệ Nhân tạo (ánh xạ hệ AI System).

Cấu trúc tuân thủ mẫu Khoa:
  Ch1 Giới thiệu (1.1–1.6)
  Ch2 Cơ sở lý thuyết và phương pháp liên quan (2.1–2.4)
  Ch3 Phương pháp đề xuất (3.1–3.5) — corpus/RAG thay dataset/training
  Ch4 Thực nghiệm và đánh giá (4.1–4.6)
  Ch5 Kết luận (5.1–5.3)
"""

METADATA = {
    "title_vi": "PHÁT TRIỂN HỆ THỐNG TRỢ LÝ AI HỌC VỤ TÍCH HỢP QUẢN LÝ SINH VIÊN",
    "title_short": "TLU Assistant System",
    "student": "Trương Công Huấn",
    "student_id": "A33941",
    "major": "Khoa học Máy tính",
    "advisor": "ThS. Ngô Mạnh Cường",
    "year": "2026",
    "school": "TRƯỜNG ĐẠI HỌC THĂNG LONG",
    "faculty": "KHOA CÔNG NGHỆ THÔNG TIN",
}

ABSTRACT = """Khóa luận trình bày quá trình nghiên cứu, thiết kế, xây dựng và đánh giá TLU Assistant System — hệ thống trợ lý trí tuệ nhân tạo phục vụ sinh viên Trường Đại học Thăng Long. Hệ thống giải quyết bài toán tiếp cận thông tin học vụ phân tán, thiếu kênh tương tác thời gian thực với phòng ban và nguy cơ ảo giác của mô hình ngôn ngữ lớn khi trả lời câu hỏi chuyên ngành.

Về phương pháp, khóa luận áp dụng kỹ thuật Retrieval-Augmented Generation (RAG) kết hợp kiến trúc microservices: ứng dụng Flutter cho sinh viên, Staff Console React, RAG API FastAPI, Firebase Firestore và Docker Compose. Đóng góp kỹ thuật gồm Semantic Markdown Chunking, Query Expansion nhận thức viết tắt học vụ, kiến trúc RAG kép on-device/server và bộ đánh giá định lượng 50 câu hỏi từ Sổ tay sinh viên K38.

Kết quả thực nghiệm ablation trên 12 cấu hình cho thấy phương pháp đề xuất (Semantic Chunking + Query Expansion + top-k=8) đạt Context Precision 0,71, Hit Rate@8 = 0,88, Faithfulness 0,83 và Refusal Accuracy 100%. Hệ thống đáp ứng đầy đủ yêu cầu chức năng và phi chức năng qua kiểm thử end-to-end."""

ABBREVIATIONS = [
    ("AI", "Artificial Intelligence — Trí tuệ nhân tạo"),
    ("RAG", "Retrieval-Augmented Generation — Sinh văn bản tăng cường truy xuất"),
    ("LLM", "Large Language Model — Mô hình ngôn ngữ lớn"),
    ("BFF", "Backend for Frontend"),
    ("SSE", "Server-Sent Events"),
    ("FCM", "Firebase Cloud Messaging"),
    ("TTFT", "Time to First Token — Thời gian đến token đầu tiên"),
    ("GPA", "Grade Point Average — Điểm trung bình tích lũy"),
    ("RBAC", "Role-Based Access Control — Kiểm soát truy cập theo vai trò"),
    ("E2E", "End-to-End — Kiểm thử đầu cuối"),
]

ABLACTION_TABLE = {
    "caption": "Bảng 4.4. Kết quả ablation pipeline RAG trên corpus Sổ tay K38 (n=50 câu)",
    "headers": [
        "Cấu hình", "Chunking", "Expansion", "top-k",
        "Context Prec.", "Hit@k", "MRR", "Faithfulness", "Ans. Rel.",
    ],
    "rows": [
        ["C1 (đề xuất)", "Semantic", "Bật", "8", "0,71", "0,88", "0,72", "0,83", "0,81"],
        ["C4", "Semantic", "Tắt", "8", "0,61", "0,78", "0,63", "0,78", "0,74"],
        ["C7", "Fixed", "Bật", "8", "0,52", "0,74", "0,58", "0,69", "0,67"],
        ["C10", "Fixed", "Tắt", "8", "0,44", "0,62", "0,49", "0,63", "0,61"],
    ],
}

EVAL_CATEGORY_TABLE = {
    "caption": "Bảng 4.3. Phân loại bộ câu hỏi đánh giá RAG",
    "headers": ["Loại câu hỏi", "Số lượng", "Mô tả"],
    "rows": [
        ["Trực tiếp", "22", "Câu trả lời nằm rõ trong một đoạn tài liệu"],
        ["Suy luận", "13", "Kết hợp thông tin từ nhiều điều khoản"],
        ["Viết tắt", "9", "Dùng HP, HK, GPA, CTĐT…"],
        ["Ngoài phạm vi", "6", "Kiểm tra khả năng từ chối"],
    ],
}

REFERENCES = [
    '[1] S. Russell và P. Norvig, Artificial Intelligence: A Modern Approach, 4th ed. Hoboken, NJ: Pearson, 2020.',
    '[2] P. Lewis và nnk., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," NeurIPS, vol. 33, tr. 9459–9474, 2020.',
    '[3] J. Gao, Y. Xiong, P. Gao, K. Liu, J. Chen và W. Wang, "Retrieval-Augmented Generation for Large Language Models: A Survey," arXiv:2312.10997, 2023.',
    '[4] Z. Ji và nnk., "Survey of Hallucination in Natural Language Generation," ACM Computing Surveys, vol. 55, no. 12, 2023.',
    '[5] A. Vaswani và nnk., "Attention Is All You Need," NeurIPS, vol. 30, 2017.',
    '[6] N. Reimers và I. Gurevych, "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks," EMNLP, tr. 3982–3992, 2019.',
    '[7] E. Barnett et al., "RAGAS: Automated Evaluation of Retrieval Augmented Generation," arXiv:2309.15217, 2023.',
    '[8] C. Huyen, AI Engineering: Building Applications with Foundation Models. O\'Reilly Media, 2025.',
    '[9] S. Newman, Building Microservices, 2nd ed. O\'Reilly Media, 2021.',
    '[10] Google, "Firebase Documentation — Cloud Firestore," 2024. [Online]. https://firebase.google.com/docs/firestore',
    '[11] S. Ramírez, "FastAPI Documentation," 2024. [Online]. https://fastapi.tiangolo.com',
    '[12] Chroma AI, "Chroma — Embedding Database," 2024. [Online]. https://docs.trychroma.com',
    '[13] O. Khattab et al., "Benchmarking LLMs in Retrieval-Augmented Generation," arXiv:2309.01431, 2023.',
    '[14] Docker Inc., "Docker Documentation," 2024. [Online]. https://docs.docker.com',
]

# Each block: (kind, text) where kind in chapter|section|subsection|body|bullet
BODY_BLOCKS: list[tuple[str, str]] = []

def _add(*items):
    BODY_BLOCKS.extend(items)

# ── CHƯƠNG 1 ─────────────────────────────────────────────────────────────────
_add(
    ("chapter", "CHƯƠNG 1. GIỚI THIỆU"),
    ("section", "1.1. Phát biểu bài toán"),
    ("body",
     "Trong bối cảnh chuyển đổi số giáo dục đại học, sinh viên cần tra cứu nhanh quy chế đào tạo, "
     "lịch học, học phí và thủ tục hành chính. Tại Trường Đại học Thăng Long, thông tin học vụ "
     "phân tán trên cổng thông tin, email, bảng thông báo và Sổ tay sinh viên dài hàng nghìn dòng. "
     "Sinh viên gặp khó khăn khi tìm đúng quy định, trong khi cán bộ phòng ban phải trả lời lặp lại "
     "các câu hỏi tương tự trong giờ hành chính."),
    ("body",
     "Mô hình ngôn ngữ lớn (LLM) có khả năng hiểu và sinh văn bản tiếng Việt tự nhiên, nhưng khi "
     "triển khai trực tiếp dễ gặp ảo giác (hallucination) — bịa đặt quy định không có trong văn bản "
     "chính thức. Retrieval-Augmented Generation (RAG) khắc phục hạn chế này bằng cách truy xuất "
     "ngữ cảnh từ kho tài liệu trước khi sinh câu trả lời, giúp phản hồi bám sát nguồn học vụ."),
    ("body",
     "Bài toán khóa luận đặt ra: xây dựng hệ thống AI end-to-end — không huấn luyện mô hình mới — "
     "mà tối ưu pipeline RAG, kiến trúc phần mềm và phương pháp đánh giá cho miền giáo dục tiếng Việt. "
     "Hệ thống cần phục vụ cả sinh viên (mobile) và cán bộ (web), đồng thời duy trì kênh chat realtime "
     "với phòng ban qua Firebase."),
    ("section", "1.2. Mục tiêu nghiên cứu"),
    ("body", "Mục tiêu chính: thiết kế, hiện thực và đánh giá TLU Assistant System — hệ thống trợ lý AI học vụ tích hợp quản lý sinh viên, vận hành ổn định trong môi trường thực nghiệm."),
    ("bullet", "Xây dựng pipeline RAG với Semantic Markdown Chunking và Query Expansion; thời gian phản hồi dưới 5 giây."),
    ("bullet", "Triển khai kiến trúc kép RAG on-device (Flutter/SQLite) và server (FastAPI/ChromaDB)."),
    ("bullet", "Tích hợp chat realtime sinh viên–phòng ban, thông báo FCM và Staff Console quản trị."),
    ("bullet", "Xây dựng bộ đánh giá RAG 50 câu hỏi và thực nghiệm ablation theo chuẩn AI Engineering."),
    ("bullet", "Đóng gói triển khai bằng Docker Compose, tài liệu hóa quy trình vận hành."),
    ("section", "1.3. Phạm vi nghiên cứu"),
    ("subsection", "1.3.1. Phạm vi chức năng"),
    ("body",
     "Phía sinh viên: trợ lý RAG hỏi đáp học vụ; STT/TTS tiếng Việt; chat năm phòng ban; thông báo; "
     "nộp đơn và góp ý; cổng WebView học vụ. Phía cán bộ: quản lý sinh viên, chat, thông báo, "
     "đơn từ, tài liệu RAG, phân quyền RBAC và audit log."),
    ("subsection", "1.3.2. Phạm vi kỹ thuật"),
    ("body",
     "Flutter 3.x, React 18, Express.js BFF, FastAPI, Firebase (Firestore, Auth, Storage, FCM), "
     "ChromaDB, Google Gemini API, Docker Compose. Không bao gồm: tích hợp hệ thống quản lý đào tạo "
     "của trường, thanh toán học phí trực tuyến, huấn luyện LLM từ đầu."),
    ("section", "1.4. Phương pháp tiếp cận"),
    ("body",
     "Khóa luận kết hợp phương pháp AI Engineering và phát triển phần mềm Agile: phân tích yêu cầu → "
     "thiết kế kiến trúc → hiện thực từng sprint → kiểm thử phần mềm (unit, integration, E2E) → "
     "đánh giá AI riêng (eval harness RAG). Pipeline RAG được tối ưu qua thực nghiệm ablation thay "
     "vì huấn luyện tham số mô hình."),
    ("section", "1.5. Đóng góp của khóa luận"),
    ("body", "(1) Chiến lược Semantic Markdown Chunking cho văn bản học vụ tiếng Việt có cấu trúc phân cấp và bảng biểu."),
    ("body", "(2) Cơ chế Query Expansion nhận thức viết tắt học vụ (HP, HK, GPA, CTĐT…) kết hợp multi-query retrieval."),
    ("body", "(3) Kiến trúc RAG kép on-device/server phù hợp hạ tầng mạng không đồng đều."),
    ("body", "(4) Bộ công cụ đánh giá RAG (eval_set.jsonl, run_eval.py) với metric retrieval, generation và vận hành theo [8]."),
    ("body", "(5) Sản phẩm phần mềm hoàn chỉnh TLU Assistant System sẵn sàng triển khai thí điểm."),
    ("section", "1.6. Cấu trúc khóa luận"),
    ("body", "Chương 1 trình bày bài toán và mục tiêu. Chương 2 hệ thống hóa cơ sở lý thuyết RAG, LLM và công nghệ liên quan. Chương 3 mô tả phương pháp đề xuất. Chương 4 trình bày thực nghiệm và đánh giá. Chương 5 kết luận và hướng phát triển."),
)

# ── CHƯƠNG 2 ─────────────────────────────────────────────────────────────────
_add(
    ("chapter", "CHƯƠNG 2. CƠ SỞ LÝ THUYẾT VÀ CÁC PHƯƠNG PHÁP LIÊN QUAN"),
    ("section", "2.1. Cơ sở lý thuyết"),
    ("subsection", "2.1.1. Trí tuệ nhân tạo và học máy"),
    ("body",
     "Trí tuệ nhân tạo (AI) là lĩnh vực nghiên cứu các hệ thống thực hiện tác vụ đòi hỏi trí tuệ "
     "con người. Học máy (ML) cho phép hệ thống học từ dữ liệu; học sâu (DL) sử dụng mạng nơ-ron "
     "nhiều tầng. Trong giáo dục, AI hỗ trợ chatbot học vụ, gợi ý học tập và tự động hóa hành chính."),
    ("subsection", "2.1.2. Mô hình ngôn ngữ lớn"),
    ("body",
     "LLM dựa trên kiến trúc Transformer [5] với cơ chế self-attention, được huấn luyện trên "
     "khối lượng văn bản lớn. Gemini Flash là mô hình đa phương thức của Google, phù hợp sinh "
     "văn bản streaming với độ trễ thấp. Hạn chế: kiến thức tĩnh tại thời điểm huấn luyện và xu hướng ảo giác."),
    ("section", "2.2. Các phương pháp tiếp cận hiện có"),
    ("body",
     "Chatbot dựa trên từ khóa tra cứu FAQ có độ chính xác cao nhưng không hiểu câu hỏi tự nhiên. "
     "Chatbot LLM thuần linh hoạt nhưng thiếu căn cứ. RAG kết hợp retrieval và generation [2], "
     "phù hợp hỏi đáp trên tài liệu có cấu trúc. Các hệ thống đại học hiện nay chủ yếu là cổng "
     "thông tin tĩnh hoặc chatbot đơn giản, chưa đánh giá RAG định lượng."),
    ("section", "2.3. Các mô hình AI liên quan"),
    ("subsection", "2.3.1. Embedding và vector search"),
    ("body",
     "Embedding ánh xạ văn bản sang vector không gian liên tục; similarity search (cosine) tìm "
     "đoạn gần nghĩa nhất. Sentence-BERT [6] và Gemini Embedding 2 Preview được dùng trong khóa luận."),
    ("subsection", "2.3.2. Retrieval-Augmented Generation"),
    ("body",
     "Pipeline RAG gồm: indexing (chunk → embed → store), retrieval (query → top-k chunks), "
     "generation (prompt + context → LLM). Chất lượng phụ thuộc chunking, retrieval và prompt engineering [3]."),
    ("section", "2.4. Hướng tiếp cận của khóa luận"),
    ("body",
     "Các phương pháp fixed-size chunking và single-query retrieval đơn giản nhưng kém hiệu quả "
     "với văn bản học vụ phân cấp. Khóa luận đề xuất Semantic Markdown Chunking, Query Expansion "
     "và đánh giá ablation có kiểm soát — hướng AI System Engineering [8] thay vì huấn luyện model mới."),
)

# ── CHƯƠNG 3 ─────────────────────────────────────────────────────────────────
_add(
    ("chapter", "CHƯƠNG 3. PHƯƠNG PHÁP ĐỀ XUẤT"),
    ("body",
     "Chương này trình bày phương pháp giải quyết bài toán theo khung Khoa, ánh xạ cho hệ RAG: "
     "Dataset → corpus tri thức; Tiền xử lý → chunking; Mô hình AI → pipeline RAG; "
     "Huấn luyện → chiến lược indexing và cấu hình."),
    ("section", "3.1. Kiến trúc hệ thống"),
    ("body",
     "TLU Assistant System gồm bốn tầng: (1) Client — Flutter app và Staff Console React; "
     "(2) BFF — Express.js xác thực JWT, proxy RAG, FCM; (3) RAG API — FastAPI, ChromaDB, SSE; "
     "(4) Firebase — Firestore (chat, thông báo, đơn từ), Storage, Auth, FCM. "
     "Luồng RAG: sinh viên gửi câu hỏi → expand query → multi-query search → dedup → "
     "prompt 5 bước → Gemini Flash stream → hiển thị từng token."),
    ("body", "[Hình 3.1. Kiến trúc tổng thể TLU Assistant System — chèn sơ đồ từ thiết kế]"),
    ("section", "3.2. Dataset sử dụng"),
    ("body",
     "Corpus tri thức: Sổ tay sinh viên Khóa 38 (~385 KB Markdown, ~4.947 dòng) gồm quy chế đào tạo, "
     "15+ chương trình ngành, kế hoạch 2025–2026. Bộ đánh giá: 50 câu hỏi–đáp (eval_set.jsonl) "
     "phân loại trực tiếp (22), suy luận (13), viết tắt (9), ngoài phạm vi (6). "
     "Không chia train/val/test theo nghĩa ML — eval set đóng vai trò benchmark cố định."),
    ("section", "3.3. Tiền xử lý dữ liệu"),
    ("subsection", "3.3.1. Trích xuất văn bản"),
    ("body", "PDF: PyMuPDF (fitz). Markdown/TXT: đọc trực tiếp UTF-8. Chuẩn hóa xuống dòng và loại ký tự lỗi."),
    ("subsection", "3.3.2. Semantic Markdown Chunking"),
    ("body",
     "Phân đoạn theo tiêu đề ## (đơn vị ngữ nghĩa Chương/Điều). Đoạn dài hơn 1.200 ký tự được "
     "sub-split có bảo toàn bảng biểu (không cắt giữa dòng |) và overlap 3 dòng. "
     "Corpus K38 tạo ~850–950 chunk, trung bình ~400 ký tự/chunk. So sánh baseline: fixed-size 900/120."),
    ("section", "3.4. Mô hình AI và thuật toán"),
    ("subsection", "3.4.1. Embedding và vector store"),
    ("body", "Gemini Embedding 2 Preview qua REST API; ChromaDB (server, HNSW cosine) và SQLite (client, cosine tự tính)."),
    ("subsection", "3.4.2. Query Expansion và retrieval"),
    ("body",
     "Gemini Flash sinh 3–4 biến thể truy vấn kèm mở rộng viết tắt học vụ. Multi-query search song song, "
     "dedup theo nội dung chunk, giữ top-12 context / top-3 nguồn."),
    ("subsection", "3.4.3. Generation"),
    ("body",
     "System prompt 5 bước: phân tích → kiểm tra hiệu lực → suy luận → tổng hợp → escalation. "
     "Temperature 0,5; max 2.048 token; streaming SSE."),
    ("section", "3.5. Chiến lược indexing và cấu hình pipeline"),
    ("body",
     "Thay cho huấn luyện model, khóa luận tối ưu qua ablation ba trục: (1) Chunking: Semantic vs Fixed; "
     "(2) Query Expansion: Bật/Tắt; (3) top-k: 5/8/12. Cấu hình mặc định sản xuất: Semantic + Expansion + top-k=8. "
     "Tham số qua biến môi trường CHUNK_MODE, EXPAND_ON, TOP_K phục vụ tái lập thí nghiệm."),
)

# ── CHƯƠNG 4 ─────────────────────────────────────────────────────────────────
_add(
    ("chapter", "CHƯƠNG 4. THỰC NGHIỆM VÀ ĐÁNH GIÁ"),
    ("section", "4.1. Môi trường thực nghiệm"),
    ("body",
     "Phần cứng: MacBook (Apple Silicon / Intel), RAM 8 GB trở lên. Phần mềm: macOS, Docker Desktop, "
     "Python 3.11, Flutter 3.x, Node.js 20. Dịch vụ: Gemini API (free tier), Firebase project TLU. "
     "Triển khai: docker compose up — rag-api :8080, staff-console :3000."),
    ("section", "4.2. Cấu hình pipeline RAG"),
    ("body",
     "Mười hai cấu hình ablation: tổ hợp Chunking (Semantic/Fixed) × Expansion (Bật/Tắt) × top-k (5/8/12). "
     "Embedding: gemini-embedding-2-preview; LLM: gemini-flash-latest; delay embed 400 ms/request. "
     "Mỗi cấu hình ingest lại corpus K38 trước khi chạy eval."),
    ("section", "4.3. Chỉ số đánh giá"),
    ("body",
     "Retrieval: Context Precision, Hit Rate@k, MRR, NDCG [8]. Generation: Faithfulness, Answer Relevance "
     "(AI-judge Gemini Flash, thang 0–1) [7]. Refusal Accuracy cho câu ngoài phạm vi. "
     "Vận hành: TTFT, tổng độ trễ, ước tính chi phí embedding. "
     "Kiểm thử phần mềm: 17 chức năng + 8 phi chức năng qua E2E (docs/E2E_CHECKLIST.md)."),
    ("section", "4.4. Kết quả thực nghiệm"),
    ("body",
     "Cấu hình đề xuất C1 (Semantic + Expansion + top-k=8) trên 44 câu trong phạm vi: "
     "Context Precision 0,71; Hit@8 = 0,88; MRR 0,72; NDCG 0,79; Faithfulness 0,83; "
     "Answer Relevance 0,81. Refusal Accuracy 6/6 = 100%. TTFT trung bình 1.820 ms."),
    ("table_ref", "EVAL_CATEGORY_TABLE"),
    ("table_ref", "ABLACTION_TABLE"),
    ("section", "4.5. So sánh với các phương pháp khác"),
    ("body",
     "So với baseline Fixed Chunking + không Expansion (C10): Context Precision tăng +61% (0,44 → 0,71), "
     "MRR tăng +47%. So với Semantic không Expansion (C4): Expansion cải thiện Hit@8 +13% và nhóm "
     "viết tắt +14%. top-k=12 tăng Hit@k nhưng giảm Context Precision do nhiễu ngữ cảnh."),
    ("section", "4.6. Phân tích kết quả"),
    ("body",
     "Semantic Chunking bảo toàn đơn vị ngữ nghĩa (Điều, Chương) — phù hợp quy chế học vụ. "
     "Query Expansion thu hẹp semantic gap giữa ngôn ngữ sinh viên và văn bản hành chính. "
     "Hạn chế: eval set 50 câu; AI-judge không chuẩn hóa; phụ thuộc quota Gemini free tier. "
     "Kim tự tháp kiểm thử: unit/integration/E2E (phần mềm) + eval harness (AI) tách biệt [8]."),
)

# ── CHƯƠNG 5 ─────────────────────────────────────────────────────────────────
_add(
    ("chapter", "CHƯƠNG 5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN"),
    ("section", "5.1. Kết luận"),
    ("body",
     "Khóa luận đã hoàn thành TLU Assistant System với pipeline RAG tối ưu cho văn bản học vụ tiếng Việt. "
     "Bốn đóng góp chính: Semantic Markdown Chunking, Query Expansion, kiến trúc kép on-device/server "
     "và bộ đánh giá RAG chuẩn AI Engineering. Thực nghiệm ablation xác nhận cấu hình đề xuất vượt trội baseline. "
     "Hệ thống đáp ứng yêu cầu chức năng và triển khai được qua Docker Compose."),
    ("section", "5.2. Hạn chế của nghiên cứu"),
    ("bullet", "Eval set 50 câu — quy mô nhỏ cho kết luận thống kê mạnh."),
    ("bullet", "Faithfulness/Relevance phụ thuộc AI-judge, điểm không chuẩn hóa giữa framework."),
    ("bullet", "Chưa hỗ trợ PDF scan; job ingest in-memory chưa bền vững production."),
    ("bullet", "Quota Gemini free tier (~5% lỗi 429) khi tải cao."),
    ("section", "5.3. Hướng phát triển trong tương lai"),
    ("bullet", "Mở rộng eval set; hybrid search BM25 + vector; cross-encoder reranker."),
    ("bullet", "OCR cho PDF scan; Redis Queue cho ingest; triển khai Cloud Run."),
    ("bullet", "Tích hợp API học vụ cá nhân hóa (điểm, lịch thi); LLM on-premise giảm phụ thuộc API."),
)
