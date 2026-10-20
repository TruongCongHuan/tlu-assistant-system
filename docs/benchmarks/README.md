# Kết quả benchmark retrieval

Đọc [báo cáo tổng hợp ngày 20/10/2026](BAO_CAO_RETRIEVAL_2026-10-20.md) trước. Benchmark chỉ đánh giá retrieval/reranking, không sinh câu trả lời hoặc dùng LLM judge.

| Nhóm kết quả | Artifacts |
|---|---|
| Dev chính: 50 câu, 5 cấu hình | [Báo cáo dev](dev_cpu_bge_mmarco_20261019T182346Z_375170cd0b45/report.md) |
| Test chính: 100 câu, 5 cấu hình | [Báo cáo test](test_cpu_bge_mmarco_20261019T183514Z_06530e6b720a/report.md), [phân tích evidence](test_cpu_bge_mmarco_20261019T183514Z_06530e6b720a/case_review.json) |
| BGE reranker int8/256: 12 câu dev | [Báo cáo smoke](dev_cpu_bge_int8_20261019T185448Z_975b8d49d5fa/report.md) |
| RRF weight 0,5, giữ nguyên pool test chính | [Metrics](fusion_replay_test_cpu_bge_mmarco_20261019T183514Z_06530e6b720a_w0.5/summary.json), [manifest](fusion_replay_test_cpu_bge_mmarco_20261019T183514Z_06530e6b720a_w0.5/manifest.json) |
| Độ trễ: 12 câu dev × 3 lần × 5 cấu hình | [180 mẫu CSV](latency_cpu_bge_mmarco_20261019T191359Z/samples.csv), [thống kê](latency_cpu_bge_mmarco_20261019T191359Z/summary.json) |
| Kiểm tra tái lập và môi trường | [Validation](validation.json), [phần cứng](hardware_cpu.json), [biến động ANN](ann_replay_check.json) |

Các thư mục run còn lại chứa smoke test và các lượt khảo sát K/weight; báo cáo tổng hợp phân biệt chúng với phép so sánh chính. Mỗi run xuất manifest, metrics, ranking và candidate IDs để đối chiếu. Raw run và model cache ở `data/benchmarks/reranking/` là dữ liệu local bị gitignore; bản kết quả cần xem lại nằm tại đây.

Bộ nhãn là pilot được tạo và đối chiếu nguồn, chưa được người thẩm định độc lập duyệt. Trong 100 câu test có 80 câu có evidence; 20 câu ngoài phạm vi không được đưa vào trung bình chất lượng. Kết quả RRF weight 0,5 là khảo sát bổ sung, cần holdout mới trước khi chọn làm cấu hình triển khai.

[Hướng dẫn cài đặt và chạy lại](../../services/rag-api/eval/README_RETRIEVAL.md).
