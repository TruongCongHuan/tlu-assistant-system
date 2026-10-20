# Mẫu báo cáo cải thiện retrieval và reranking TLU

**Đây là mẫu cấu trúc, không phải bảng kết quả.** Dấu `—` nghĩa là chưa điền, không phải số 0. Kết quả chạy thật nằm trong [báo cáo 20/10/2026](benchmarks/BAO_CAO_RETRIEVAL_2026-10-20.md). Người dùng đã chốt chỉ benchmark retrieval/reranking, nên mục generation bên dưới chỉ giữ để tham khảo.

Kế hoạch và định nghĩa cấu hình: [KE_HOACH_RERANKING_BENCHMARK.md](../plans/KE_HOACH_RERANKING_BENCHMARK.md).

## 1. Câu hỏi thực nghiệm

Cross-Encoder có cải thiện thứ hạng evidence học vụ so với dense và hybrid không? Lợi ích trên test độc lập là bao nhiêu, với chi phí độ trễ và bộ nhớ nào?

## 2. Thông tin tái lập

| Thuộc tính | Giá trị từ manifest |
|---|---|
| Run IDs, code commit, lệnh chạy | — |
| Corpus version/hash, số tài liệu/chunk | — |
| Qrels version/hash, cách gán nhãn và review | — |
| Số câu dev/test; answerable/OOS; phân bố nhóm | — |
| Kiểm tra trùng ý định giữa dev/test | — |
| Chunking, embedding model/revision, vector dimension | — |
| Reranker model/revision, precision, max length, batch | — |
| Candidate K, final K, BM25 weight, RRF constant | — |
| CPU/GPU, RAM/VRAM, Python và dependency lock | — |
| Ngày chạy, seed, warmup, repetitions, concurrency/cache | — |
| Ngân sách latency và quy tắc chọn cấu hình đã khóa trên dev | — |

Ghi rõ kết quả nào là cached replay, kết quả nào đo live; cold start không gộp vào warm latency. Nếu chạy khác thiết bị, tách bảng.

## 3. Kết quả retrieval trên test

Metrics chất lượng dưới đây chỉ tính trên các câu có đáp án. Phải bổ sung số câu dự kiến, thành công, lỗi, fallback và tỷ lệ candidate chưa được chấm nhãn.

| Cấu hình | n | Candidate Hit@K | Recall@K | Hit@5 | MRR@5 | nDCG@5 | Precision@5 | Recall@5 | Đủ mọi evidence group |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A: Dense | — | — | — | — | — | — | — | — | — |
| B: BM25 | — | — | — | — | — | — | — | — | — |
| C: Hybrid RRF | — | — | — | — | — | — | — | — | — |
| D: Dense + Cross-Encoder | — | — | — | — | — | — | — | — | — |
| E: Hybrid + Cross-Encoder | — | — | — | — | — | — | — | — | — |

Candidate metrics của A/D và C/E phải giống nhau khi dùng cùng pool. Công bố thêm phân tích theo evidence group tương đương và loại câu hỏi. L0/F, nếu chạy, thêm bảng riêng với ngân sách/expansion ghi rõ.

| So sánh theo cặp | Số cặp | Δ nDCG@5 [95% CI] | Δ MRR@5 [95% CI] | Δ Hit@5 | Câu được cứu/bị giảm | Diễn giải |
|---|---:|---|---|---:|---|---|
| D − A: rerank trên dense | — | — | — | — | — | — |
| E − C: rerank trên hybrid | — | — | — | — | — | — |
| C − A: hybrid so với dense | — | — | — | — | — | — |

Chênh lệch tỷ lệ phải ghi đơn vị: điểm phần trăm hoặc phần trăm tương đối. Công bố CI, số câu và phụ thuộc giữa các paraphrase; không chỉ công bố p-value hay cấu hình tốt nhất.

## 4. Tài nguyên và độ trễ

| Cấu hình | Thiết bị/cache | Retrieval p50/p95 ms | Rerank p50/p95 ms | Tổng retrieval p50/p95 ms | Peak RAM/VRAM | Throughput | Lỗi/fallback |
|---|---|---|---|---|---|---|---|
| A | — | — | Không áp dụng | — | — | — | — |
| B | — | — | Không áp dụng | — | — | — | — |
| C | — | — | Không áp dụng | — | — | — | — |
| D | — | — | — | — | — | — | — |
| E | — | — | — | — | — | — | — |

Bổ sung breakdown expansion/embedding/search/fusion, cold start, số lần lặp và tỷ lệ truncation. Đính kèm biểu đồ chất lượng–độ trễ và recall theo K từ dữ liệu dev; không chọn lại K sau khi xem test.

## 5. Đánh giá end-to-end và chi phí

So sánh A, C và cấu hình chọn trên dev bằng cùng LLM/prompt/token budget. Ghi run ID riêng và xác nhận generation đọc đúng context được chấm retrieval.

| Cấu hình | Faithfulness | Answer relevance/correctness | OOS refusal n/N | False refusal n/N | TTFT p50/p95 | Tổng answer latency p50/p95 |
|---|---:|---:|---|---|---|---|
| A | — | — | — | — | — | — |
| C | — | — | — | — | — | — |
| Cấu hình đã chọn | — | — | — | — | — | — |

Chi phí: tách indexing, embedding truy vấn, expansion, generation, judge và máy inference; ghi usage, nguồn đơn giá/ngày áp dụng, số lần gọi và retry. Các phần không đo được ghi “chưa đo”. Nêu rubric, judge model và kết quả rà soát thủ công.

## 6. Phân tích lỗi có dẫn chứng

| Query ID và loại lỗi | Gold evidence | Rank trước/sau | Nguyên nhân có bằng chứng | Hướng xử lý |
|---|---|---|---|---|
| Câu rerank cải thiện | — | — | — | — |
| Câu rerank làm giảm | — | — | — | — |
| Gold không lọt candidate pool | — | — | — | — |
| Chunk gần trùng/tương đương | — | — | — | — |
| Thiếu một trong nhiều evidence cần kết hợp | — | — | — | — |
| OOS, truncation hoặc inference lỗi | — | — | — | — |

Mỗi ví dụ liên kết tới query, đoạn nguồn và bản ghi ranking. Phân biệt lỗi corpus, lỗi nhãn, lỗi retrieval, lỗi reranker và lỗi generation. Không kết luận nguyên nhân chỉ từ việc top-1 thay đổi.

## 7. Kết luận và giới hạn

Điền sau khi có số liệu: cấu hình được khuyến nghị, mức cải thiện tuyệt đối/CI, điều kiện thiết bị, độ trễ và trường hợp nên giữ baseline. Nếu không có lợi ích rõ hoặc CI rộng, ghi đúng mức bằng chứng.

Nêu hạn chế về kích thước test, độ đầy đủ qrels, corpus K38, chủ đề/niên khóa, chất lượng judge và khác biệt giữa benchmark offline với tải thực tế.

## 8. Artifacts đi kèm

- Manifest có commit, hashes và model revisions; query/qrels versions.
- Cấu hình/lệnh tái lập, candidate pool, ranking đầy đủ, per-query metrics.
- Summary, paired comparisons/CI, latency samples, errors/fallbacks và biểu đồ.
- Đường dẫn báo cáo được xuất và vị trí lưu raw artifacts; xác nhận không dùng số trong placeholder làm kết quả chạy thật.
