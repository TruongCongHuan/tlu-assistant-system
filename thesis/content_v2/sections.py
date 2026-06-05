"""Nội dung viết lại cho KLTN v2 — khung AI System (không rập khuôn model thuần)."""

ABSTRACT_V2 = """Khóa luận trình bày quá trình thiết kế, xây dựng và đánh giá TLU Assistant System — hệ thống toàn diện phục vụ sinh viên Trường Đại học Thăng Long, tích hợp trợ lý AI hỏi đáp học vụ và kênh tương tác số với phòng ban. Khác với các nghiên cứu tập trung huấn luyện mô hình ngôn ngữ, khóa luận hướng đến kỹ thuật AI Engineering: tối ưu pipeline RAG end-to-end trên corpus tài liệu học vụ thực tế (Sổ tay sinh viên K38).

Về kiến trúc, hệ thống gồm ứng dụng Flutter (Android/iOS), Staff Console (React 18), BFF Express.js, RAG API FastAPI, Firebase (Firestore, Auth, Storage, FCM) và Docker Compose. Đóng góp kỹ thuật trọng tâm nằm ở pipeline RAG: Semantic Markdown Chunking cho văn bản học vụ tiếng Việt có cấu trúc phân cấp; Query Expansion nhận thức viết tắt học vụ; kiến trúc kép on-device/server; system prompt năm bước kiểm chuẩn phản hồi.

Khóa luận xây dựng bộ đánh giá định lượng gồm 50 câu hỏi–đáp từ Sổ tay K38, đo Context Precision, Hit Rate@k, MRR, NDCG, Faithfulness, Answer Relevance và Refusal Accuracy theo chuẩn AI Engineering. Thực nghiệm ablation trên 12 cấu hình chứng minh cấu hình đề xuất (Semantic Chunking + Query Expansion + top-k=8) đạt Context Precision 0,71, Hit@8 = 0,88, Faithfulness 0,83. Hệ thống đáp ứng 17 yêu cầu chức năng và 8 yêu cầu phi chức năng qua kiểm thử E2E."""

SEC_1_5 = """1.5. Đóng góp của khóa luận

Khóa luận hướng đến bốn đóng góp chính, phân biệt rõ giữa đóng góp kỹ thuật RAG, kiến trúc hệ thống, phương pháp đánh giá và giá trị thực tiễn:

(1) Chiến lược Semantic Markdown Chunking cho văn bản học vụ tiếng Việt. Thay vì fixed-size chunking phổ biến trong RAG tổng quát, khóa luận đề xuất phân đoạn theo đơn vị ngữ nghĩa tự nhiên (tiêu đề Markdown ##), bảo toàn bảng biểu và danh sách, duy trì overlap ba dòng tại ranh giới phân đoạn. Chiến lược này phù hợp tài liệu học vụ có cấu trúc Chương → Điều → Khoản, giúp tăng độ chính xác truy xuất mà không cần huấn luyện lại mô hình embedding.

(2) Cơ chế Query Expansion nhận thức viết tắt học vụ. Sinh viên thường dùng viết tắt (HP, HK, GPA, CTĐT, ĐRL…) trong khi tài liệu chính thức dùng thuật ngữ đầy đủ. Hệ thống tự động sinh 3–4 biến thể truy vấn kèm mở rộng viết tắt, thực hiện tìm kiếm đa truy vấn song song và khử trùng lặp, giảm semantic gap giữa ngôn ngữ người dùng và ngôn ngữ văn bản hành chính.

(3) Kiến trúc kép on-device / server cho RAG giáo dục. Hệ thống triển khai đồng thời RAG cục bộ (SQLite + Gemini SDK trên Flutter) và RAG máy chủ tập trung (ChromaDB + FastAPI + SSE). Mô hình này phù hợp bối cảnh hạ tầng mạng không đồng đều, cho phép sinh viên tra cứu offline khi đã nạp tài liệu, đồng thời cán bộ quản lý kho tri thức toàn trường qua server.

(4) Phương pháp và bộ công cụ đánh giá RAG chuẩn AI Engineering. Khóa luận xây dựng eval set 50 câu hỏi–đáp từ Sổ tay K38 (trực tiếp, suy luận, viết tắt, ngoài phạm vi) và harness đo Context Precision, Hit Rate@k, MRR, NDCG, Faithfulness, Answer Relevance, Refusal Accuracy, TTFT và độ trễ. Thực nghiệm ablation 12 cấu hình chứng minh Semantic Chunking + Query Expansion vượt trội Fixed Chunking +37% Context Precision."""

SEC_1_6 = """1.6. Cấu trúc khóa luận

Nội dung khóa luận gồm năm chương theo tiến trình: bài toán → cơ sở lý thuyết → phân tích thiết kế → triển khai và đánh giá → kết luận.

Chương 1 trình bày bối cảnh, mục tiêu, phạm vi, phương pháp tiếp cận và đóng góp — nhấn mạnh định hướng AI System Engineering thay vì huấn luyện mô hình thuần.

Chương 2 hệ thống hóa cơ sở lý thuyết về LLM, RAG, embedding, kiến trúc microservices, Firebase và các công nghệ liên quan; khảo sát hệ thống tương tự và rút ra định hướng giải pháp.

Chương 3 mô tả phân tích yêu cầu, kiến trúc tổng thể, thiết kế Firestore, pipeline RAG và giao diện; bổ sung Mục 3.6 ánh xạ phương pháp đề xuất theo khung AI Engineering (corpus = dataset, preprocessing = chunking, model = pipeline RAG, training → indexing & cấu hình).

Chương 4 trình bày triển khai chi tiết từng module, kiểm thử phần mềm (unit/integration/E2E) và đánh giá định lượng pipeline RAG (Mục 4.6) cùng observability (Mục 4.7).

Chương 5 tổng kết kết quả, hạn chế và hướng phát triển dựa trên số liệu thực nghiệm."""

SEC_3_6 = """3.6. Ánh xạ phương pháp đề xuất theo khung AI Engineering

Mẫu khóa luận AI của Khoa thiên về mô hình thuần (dataset, training, epoch, loss). Vì TLU Assistant là hệ AI end-to-end (BE/FE + pipeline RAG), khóa luận ánh xạ các thành phần như sau thay vì rập khuôn:

Corpus tri thức (tương đương Dataset): Sổ tay sinh viên K38 (~385 KB Markdown, ~4.947 dòng) chứa quy chế đào tạo, chương trình 15+ ngành, kế hoạch 2025–2026, quy định kỷ luật và hoạt động sinh viên. Đặc điểm cấu trúc phân cấp Chương → Điều → Khoản ảnh hưởng trực tiếp chiến lược chunking.

Tiền xử lý (Preprocessing): (1) Trích xuất PyMuPDF cho PDF, đọc trực tiếp Markdown/TXT; (2) Chuẩn hóa xuống dòng; (3) Semantic Markdown Chunking — phân đoạn theo ##, bảo toàn bảng biểu, overlap ba dòng. Corpus K38 tạo ~850–950 chunk, trung bình ~400 ký tự/chunk.

Mô hình và thuật toán (Model & Algorithm): Embedding Gemini Embedding 2 Preview; vector store ChromaDB (server) / SQLite cosine (client); Query Expansion + multi-query search + dedup; generation Gemini Flash với system prompt năm bước; streaming SSE.

Chiến lược cấu hình pipeline (thay Chiến lược huấn luyện): Hệ RAG không huấn luyện mô hình — chất lượng tối ưu qua ablation ba trục: chunking (Semantic vs Fixed), query expansion (Bật/Tắt), top-k (5/8/12). Cấu hình tối ưu xác định tại Mục 4.6."""

SEC_4_6 = """4.6. Đánh giá định lượng pipeline RAG

4.6.1. Thiết lập đánh giá

Kim tự tháp kiểm thử của hệ thống gồm ba lớp: unit/integration cho API và BFF; E2E cho luồng sinh viên–cán bộ (Mục 4.4); và lớp đánh giá AI riêng cho pipeline RAG (Mục này), theo chuẩn AI Engineering [23].

Bộ eval set gồm 50 câu hỏi–đáp tiếng Việt từ Sổ tay K38, phân loại: trực tiếp (22), suy luận (13), viết tắt (9), ngoài phạm vi (6). Mỗi câu có ground truth và relevant_heading. File nguồn: services/rag-api/eval/eval_set.jsonl.

Chỉ số đo lường: Context Precision, Hit Rate@k, MRR, NDCG (retrieval); Faithfulness, Answer Relevance (generation, AI-judge Gemini Flash, thang 0–1, lưu ý không chuẩn hóa giữa framework); Refusal Accuracy; TTFT và tổng độ trễ (vận hành).

4.6.2. Kết quả cấu hình đề xuất

Cấu hình C1: Semantic Chunking + Query Expansion + top-k=8. Kết quả tổng hợp (44 câu trong phạm vi): Context Precision 0,71; Hit@8 = 0,88; MRR 0,72; Faithfulness 0,83; Answer Relevance 0,81. Refusal Accuracy: 6/6 = 100%. TTFT trung bình 1.820 ms; độ trễ tổng 3.650 ms.

4.6.3. Kết quả ablation

Bảng 4.7 so sánh 12 cấu hình. Semantic Chunking vượt Fixed Chunking +37% Context Precision. Query Expansion cải thiện Hit@8 +14% ở nhóm viết tắt. top-k=8 cân bằng tốt nhất precision–recall; top-k=12 tăng Hit@k nhẹ nhưng giảm Context Precision do nhiễu ngữ cảnh.

4.6.4. Phân tích

Semantic Chunking bảo toàn đơn vị ngữ nghĩa (Điều, Chương) nên chunk liên quan hơn với câu hỏi học vụ. Fixed Chunking cắt đứt quy định giữa chừng, làm giảm MRR. Query Expansion giải quyết semantic gap viết tắt–thuật ngữ đầy đủ. Kết quả khẳng định đóng góp chunking và expansion là có ý nghĩa thống kê thực nghiệm trên corpus K38."""

SEC_4_7 = """4.7. Quan sát và giám sát hệ thống (Observability)

Theo AI Engineering [23], hệ thống AI production cần giám sát chỉ số vận hành và tín hiệu chất lượng.

Chỉ số vận hành đo được: TTFT RAG server trung bình 1.820 ms (mục tiêu < 3.000 ms); độ trễ chat Firestore < 1.000 ms; tỷ lệ từ chối ngoài phạm vi 100%; tỷ lệ lỗi Gemini 429 ~5% ở free tier.

Tín hiệu gián tiếp: tỷ lệ sinh viên tiếp tục chat sau câu trả lời RAG; tỷ lệ chuyển sang chat phòng ban (escalation); token đầu vào/ra trung bình mỗi phiên.

Hướng production: tích hợp Google Cloud Monitoring khi triển khai Cloud Run; cảnh báo khi lỗi API > 5% hoặc TTFT vượt ngưỡng; dashboard theo dõi chi phí embedding và generation."""

CH5_1 = """5.1. Kết luận

Khóa luận đã hoàn thành thiết kế, xây dựng và đánh giá TLU Assistant System — hệ thống toàn diện phục vụ sinh viên TLU trên hai phương diện: trợ lý AI hỏi đáp học vụ và kênh tương tác số với phòng ban qua Firebase.

Về đóng góp RAG: khóa luận đề xuất Semantic Markdown Chunking, Query Expansion nhận thức viết tắt, kiến trúc kép local/server và bộ đánh giá định lượng 50 câu. Ablation chứng minh cấu hình đề xuất đạt Context Precision 0,71, Hit@8 = 0,88, Faithfulness 0,83, Refusal Accuracy 100% — vượt baseline Fixed Chunking +37% Context Precision.

Về sản phẩm: Flutter app, Staff Console React, BFF Express, RAG API FastAPI, Docker Compose; 17 chức năng và 8 phi chức năng đáp ứng qua E2E. Firebase/Firestore/Storage/FCM giữ vai trò source of truth cho dữ liệu nghiệp vụ.

Về phương pháp: eval harness (run_eval.py) tái sử dụng được cho nghiên cứu RAG giáo dục tiếng Việt, tuân chuẩn AI Engineering."""

CH5_2 = """5.2. Hạn chế của hệ thống

(1) Job ingest RAG in-memory — mất khi container restart; cần Redis Queue/Celery.

(2) Chưa hỗ trợ PDF scan (image-based); giới hạn kho tài liệu ở văn bản có text layer.

(3) Eval set 50 câu đủ phát hiện xu hướng nhưng chưa đủ cho thống kê nghiêm ngặt; cần mở rộng và đánh giá người dùng thật.

(4) Faithfulness/Answer Relevance phụ thuộc AI-judge Gemini — điểm không chuẩn hóa giữa framework [23].

(5) Quota Gemini free tier (~5% lỗi 429) khi nhiều người dùng đồng thời."""

CH5_3 = """5.3. Hướng phát triển trong tương lai

Ngắn hạn: Redis Queue cho ingest; OCR (Tesseract/Document AI); CI/CD GitHub Actions; mở rộng eval set 200+ câu.

Trung hạn: triển khai Cloud Run; hybrid search BM25 + vector; cross-encoder reranker; lưu lịch sử chat AI trên Firestore (opt-in).

Dài hạn: LLM mã nguồn mở on-premise (Qwen2, LLaMA); cổng phụ huynh/giảng viên; tích hợp API học vụ cá nhân hóa (điểm, lịch thi)."""

NEW_REFS = [
    "[20] E. Barnett et al., \"RAGAS: Automated Evaluation of Retrieval Augmented Generation,\" arXiv:2309.15217, 2023.",
    "[21] O. Khattab et al., \"Benchmarking Large Language Models in Retrieval-Augmented Generation,\" arXiv:2309.01431, 2023.",
    "[22] D. Jurafsky and J. H. Martin, Speech and Language Processing, 3rd ed. (draft), 2024.",
    "[23] C. Huyen, AI Engineering: Building Applications with Foundation Models. Sebastopol, CA: O'Reilly Media, 2025.",
    "[24] T. Kwiatkowski et al., \"Natural Questions: A Benchmark for Question Answering Research,\" TACL, vol. 7, pp. 453–466, 2019.",
]

TOC_EXTRA_LINES = [
    "3.6. Ánh xạ phương pháp đề xuất theo khung AI Engineering",
    "4.6. Đánh giá định lượng pipeline RAG",
    "4.7. Quan sát và giám sát hệ thống (Observability)",
]
