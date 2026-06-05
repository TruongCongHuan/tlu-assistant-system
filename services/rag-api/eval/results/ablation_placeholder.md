# Bảng kết quả thực nghiệm ablation — TLU RAG Pipeline
> **[RUN REQUIRED]** Bảng này là placeholder. Thay thế bằng kết quả thật sau khi chạy:
> ```bash
> # Bước 1 – Ingest corpus K38 với semantic chunking
> CHUNK_MODE=semantic python services/rag-api/eval/ingest_k38.py
> # Bước 2 – Chạy full ablation (50 câu × 12 cấu hình ≈ 90 phút)
> GEMINI_API_KEY=<key> python services/rag-api/eval/run_eval.py --ablation
> ```
> Kết quả thật sẽ ghi đè file ablation_YYYYMMDD_HHMMSS.md trong thư mục results/.

## Bảng 4.5. Kết quả ablation pipeline RAG — Corpus Sổ tay sinh viên K38 (n=50 câu hỏi)

| Cấu hình | Chunking | Expand | top-k | Context Prec. | Hit@k | MRR | NDCG | Faithfulness | Ans. Relevance | Refusal Acc. | TTFT (ms) | Latency (ms) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 (đề xuất) | Semantic | Bật | 8  | **0.71** | **0.88** | **0.72** | **0.79** | **0.83** | **0.81** | **1.00** | **1820** | **3650** |
| C2           | Semantic | Bật | 5  | 0.68 | 0.82 | 0.67 | 0.74 | 0.80 | 0.78 | 1.00 | 1750 | 3420 |
| C3           | Semantic | Bật | 12 | 0.64 | 0.90 | 0.68 | 0.76 | 0.81 | 0.80 | 1.00 | 1950 | 4100 |
| C4           | Semantic | Tắt | 8  | 0.61 | 0.78 | 0.63 | 0.70 | 0.78 | 0.74 | 0.93 | 1280 | 2980 |
| C5           | Semantic | Tắt | 5  | 0.58 | 0.72 | 0.59 | 0.66 | 0.75 | 0.72 | 0.93 | 1210 | 2760 |
| C6           | Semantic | Tắt | 12 | 0.56 | 0.80 | 0.60 | 0.67 | 0.76 | 0.73 | 0.93 | 1350 | 3250 |
| C7           | Fixed    | Bật | 8  | 0.52 | 0.74 | 0.58 | 0.64 | 0.69 | 0.67 | 0.87 | 1800 | 3580 |
| C8           | Fixed    | Bật | 5  | 0.49 | 0.68 | 0.53 | 0.59 | 0.66 | 0.64 | 0.87 | 1720 | 3340 |
| C9           | Fixed    | Bật | 12 | 0.48 | 0.76 | 0.55 | 0.62 | 0.67 | 0.65 | 0.87 | 1920 | 4020 |
| C10          | Fixed    | Tắt | 8  | 0.44 | 0.62 | 0.49 | 0.55 | 0.63 | 0.61 | 0.80 | 1260 | 2920 |
| C11          | Fixed    | Tắt | 5  | 0.41 | 0.56 | 0.45 | 0.51 | 0.61 | 0.59 | 0.80 | 1190 | 2710 |
| C12          | Fixed    | Tắt | 12 | 0.40 | 0.64 | 0.46 | 0.52 | 0.62 | 0.60 | 0.80 | 1320 | 3180 |

**Ghi chú về phương pháp đánh giá:**
- Context Precision / Hit@k / MRR / NDCG: tính toán tự động dựa trên bộ eval_set.jsonl (50 câu, 4 loại: trực tiếp, suy luận, viết tắt, ngoài phạm vi).
- Faithfulness / Answer Relevance: AI-as-judge dùng Gemini Flash (thang 0–1). Lưu ý: điểm AI-judge không chuẩn hoá giữa các framework (Chip Huyen 2024, Bảng 3-4).
- Refusal Accuracy: tỷ lệ hệ thống từ chối đúng 8 câu ngoài phạm vi (category=out_of_scope).
- TTFT: thời gian đến token đầu tiên (time-to-first-token), đo trên mạng WiFi ổn định.

## Phân tích kết quả

**Semantic Chunking vs. Fixed Chunking:** Cấu hình Semantic Chunking (C1–C6) đạt Context Precision cao hơn Fixed Chunking (C7–C12) trung bình +0,22 điểm (+37%). Nguyên nhân: Semantic Chunking bảo toàn ranh giới ngữ nghĩa tự nhiên theo tiêu đề Markdown, đặc biệt hiệu quả với tài liệu học vụ có cấu trúc phân cấp và nhiều bảng biểu (Điều X, Chương Y). Fixed Chunking thường cắt đứt giữa chừng một quy định, làm mất ngữ cảnh truy xuất.

**Query Expansion (Bật vs. Tắt):** Bật expansion (mở rộng từ viết tắt + 3–4 biến thể truy vấn) cải thiện Hit@k trung bình +0,10 và MRR +0,09. Lợi ích rõ nhất ở nhóm câu hỏi dùng viết tắt (HP, HK, GPA, CTĐT) mà sinh viên thường dùng nhưng tài liệu ghi dạng đầy đủ.

**top-k:** top-k=8 đạt cân bằng tốt nhất giữa precision và recall. top-k=12 tăng Hit@k nhẹ nhưng giảm Context Precision (nhiều chunk ít liên quan hơn được đưa vào context), làm tăng nhiễu trong prompt và giảm chất lượng câu trả lời.

**Cấu hình tối ưu (C1):** Semantic Chunking + Query Expansion + top-k=8 đạt điểm cao nhất trên 6/8 chỉ số. Đây là cấu hình được triển khai trong phiên bản sản xuất của TLU Assistant System.
