# Benchmark retrieval/reranking không dùng generation LLM

Phạm vi người dùng chốt ngày 20/10/2026: chỉ đo truy xuất bằng chứng, xếp hạng, thời gian và tài nguyên. Không cần Gemini key, generation hay judge. Không dùng số trong `results/ablation_placeholder.md` làm kết quả thật.

## Kiến trúc và dữ liệu

- Corpus K38 dùng semantic chunking chung trong `app/chunking.py`, 321 chunk ở snapshot v1. Các bảng lớn vẫn được giữ nguyên theo chiến lược hiện có; phải xem tỷ lệ truncation khi dùng model 512 token.
- `datasets/retrieval_v1/evidence_queries.jsonl`: 50 dev đã kiểm tra lại từ câu cũ, 100 test mới (80 answerable/20 OOS). Dev còn 43 answerable/7 OOS sau khi chuyển câu TCN/TCNT không có bằng chứng sang OOS.
- `audit_log.json` giữ bản gốc, bản sửa và dòng nguồn của cả 50 câu. Có sửa cả giả định câu hỏi khi không có căn cứ trong corpus.
- `qrels.jsonl` ánh xạ đoạn evidence được chỉ định rõ sang các chunk chứa đúng span, chấp nhận overlap tương đương. Không dùng trùng từ heading để tự suy ra relevance.
- Nhãn do agent biên soạn và đối chiếu nguồn, **chưa được người độc lập thẩm định**, chưa bao phủ hết mọi chunk đúng có thể có. Các metric được gọi là known-gold; không hiểu chunk chưa chấm là nhãn âm đã xác nhận.
- Dev/test không chung intent group hoặc chunk evidence dương. Test đã được tạo trước chạy benchmark, nhưng vẫn là bộ thử nghiệm tổng hợp chứ chưa phải câu hỏi người dùng thật chưa từng thấy.

Năm cấu hình kiểm soát: A Dense; B BM25; C Dense + BM25 weighted RRF; D A + Cross-Encoder; E C + Cross-Encoder. Tất cả giữ cùng candidate K=20 và final K=5. A/D và C/E được kiểm tra cùng candidate hash. Tắt expansion để tránh cần API và giữ phép so sánh rõ ràng.

## Cài môi trường

Chạy từ repository root. Dùng Python 3.12 và venv riêng; không đổi Python hệ thống:

```bash
python3 -m venv services/rag-api/.venv
services/rag-api/.venv/bin/pip install 'torch==2.6.0+cpu' --index-url https://download.pytorch.org/whl/cpu
services/rag-api/.venv/bin/pip install -r services/rag-api/requirements-rerank.txt
services/rag-api/.venv/bin/pip install 'chromadb==0.5.23'
services/rag-api/.venv/bin/pip check
```

`transformers==4.46.3` và `tokenizers==0.20.3` được chọn để tương thích giới hạn tokenizer của Chroma 0.5.23. Để chạy service/tests integration, cài thêm dependency backend trong `requirements.txt`; Cursor SDK là tùy chọn cho harness cũ, không dùng trong retrieval runner.

Mô hình tải từ model repository chính thức và khóa revision trong config. Lần đầu cần mạng và dung lượng cache; sau khi tải đủ có thể đặt `HF_HUB_OFFLINE=1`. Không đặt `RERANK_MODEL` tùy chỉnh mà vẫn giữ revision của model cũ.

Ba profile:

- `benchmark_configs.json`: BGE-M3 + BGE reranker v2 M3 theo PDF; thiết bị mặc định CPU, có thể tạo config GPU riêng. Không coi kết quả của profile khác là kết quả của profile này.
- `benchmark_configs_bge_int8.json`: giữ hai model BGE trong PDF, quantize động Linear sang int8 trên CPU và giới hạn rerank 256 token. Đây là profile tối ưu tài nguyên riêng, không đồng nhất với FP32/512 token.
- `benchmark_configs_cpu.json`: cùng BGE-M3 nhưng Cross-Encoder mMARCO MiniLM nhỏ hơn cho thí nghiệm CPU. Đây là ablation thay mô hình, phải báo riêng model, revision, max length và batch.

[Model card BGE-M3](https://huggingface.co/BAAI/bge-m3), [BGE reranker](https://huggingface.co/BAAI/bge-reranker-v2-m3), [mMARCO MiniLM](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1).

## Chạy theo thứ tự

Có thể chạy toàn bộ dev → lock → test → report bằng một lệnh (mặc định profile BGE int8; kiểm tra tài nguyên trước):

```bash
services/rag-api/.venv/bin/python services/rag-api/eval/run_retrieval_pipeline.py --config services/rag-api/eval/benchmark_configs_bge_int8.json
```

Lệnh chi tiết cho từng giai đoạn:

```bash
# Chỉ rebuild khi thực sự sửa/version dữ liệu; không sửa test theo kết quả đã thấy.
services/rag-api/.venv/bin/python services/rag-api/eval/build_retrieval_dataset.py
services/rag-api/.venv/bin/python services/rag-api/eval/run_retrieval_benchmark.py --validate-data

# Encoder chạy ở process riêng, không giữ cùng lúc encoder và reranker lớn trong RAM.
services/rag-api/.venv/bin/python services/rag-api/eval/run_retrieval_benchmark.py --stage embed --split dev

# Chọn đúng một profile, giữ nguyên từ dev đến test.
services/rag-api/.venv/bin/python services/rag-api/eval/run_retrieval_benchmark.py --config services/rag-api/eval/benchmark_configs_cpu.json --split dev --smoke
services/rag-api/.venv/bin/python services/rag-api/eval/run_retrieval_benchmark.py --config services/rag-api/eval/benchmark_configs_cpu.json --split dev

# Thay DEV_RUN bằng đường dẫn [RESULT] của full dev, không dùng smoke.
services/rag-api/.venv/bin/python services/rag-api/eval/run_retrieval_benchmark.py --lock-from data/benchmarks/reranking/DEV_RUN

services/rag-api/.venv/bin/python services/rag-api/eval/run_retrieval_benchmark.py --stage embed --split test --locked-config data/benchmarks/reranking/locked_config.json
services/rag-api/.venv/bin/python services/rag-api/eval/run_retrieval_benchmark.py --split test --locked-config data/benchmarks/reranking/locked_config.json

# Thay TEST_RUN bằng đường dẫn run thật, không lấy tên mẫu làm đường dẫn tồn tại.
services/rag-api/.venv/bin/python services/rag-api/eval/report_retrieval_benchmark.py --run-dir data/benchmarks/reranking/TEST_RUN
```

Có thể chạy riêng baseline B trước khi có weights/cache bằng `--configs B`. Một run B riêng không thay thế ma trận A–E. Test bắt buộc locked config từ dev hoàn chỉnh; runner kiểm tra hashes dữ liệu và source files, kể cả file chưa commit. Đổi mã benchmark, cấu hình hoặc nhãn sau lock phải chạy lại dev trước khi mở test.

Chạy regression suite:

```bash
services/rag-api/.venv/bin/python -m unittest discover -s services/rag-api/eval -p 'test_retrieval.py' -v
```

## Artifacts và độ trễ

Raw runs: `data/benchmarks/reranking/<run_id>/` (gitignored). Export có thể review: `docs/benchmarks/<run_id>/`, gồm manifest, summary, paired comparisons, per-query CSV, full ranking/candidates, errors và biểu đồ. Embeddings và index Chroma riêng nằm trong `data/benchmarks/reranking/embedding_cache/`, không ghi đè runtime production.

Độ trễ ranking dùng **vector query đã cache**, gồm Chroma/BM25/fusion/reranker, không bao gồm encode query, download hoặc model load. Thời gian encode lưu riêng trong metadata cache. Không cộng p95 hai giai đoạn rồi gọi đó là p95 toàn pipeline. Peak RSS là đỉnh của process ranking; không phải RAM hệ thống hoặc VRAM, và không đo đồng thời encoder + reranker.

Chất lượng đo một lần trên mỗi query. `--repetitions` thêm lần inference reranker trên cùng pool; các lần đó không tạo query chất lượng mới, không phải lượt API end-to-end độc lập. Khi cần đo ổn định toàn pipeline, chạy nhiều run cùng profile trên thiết bị rảnh và công bố rõ mẫu/lượt đo. OOM/lỗi không được fallback âm thầm trong benchmark.

Hit/MRR/Precision/Recall dùng grade 2; nDCG dùng gain `2^grade-1` và IDCG từ gold list. OOS nhận N/A và bị loại khỏi trung bình retrieval. Exact McNemar được báo như tham khảo; cluster bootstrap theo intent group là thống kê chính khi có nhiều câu cùng chủ đề.

## Bật trong backend

Sau khi đã chọn mô hình phù hợp và cài dependency rerank:

```bash
CANDIDATE_K=20 FINAL_K=5 RERANK_MODE=cross_encoder \
services/rag-api/.venv/bin/uvicorn app.main:app --app-dir services/rag-api
```

Backend vẫn dùng embedding/runtime corpus riêng của ứng dụng. Mặc định `CANDIDATE_K=0`, `RERANK_MODE=none`; không tự đổi model embedding của production. Có thể đặt `RETRIEVAL_MODE=bm25` để bỏ hoàn toàn embedding/expansion khi truy xuất sparse. Telemetry bổ sung có score type, rank trước/sau, trạng thái rerank và stage timings; `RERANK_FAIL_OPEN=1` chỉ dùng khi muốn fallback có đánh dấu trong vận hành.

Các phép preflight CPU được lưu riêng trong `docs/benchmarks/preflight*_cpu.json`; chúng chỉ chứng minh mô hình chạy được và cung cấp ước lượng tài nguyên, không thay thế benchmark chất lượng theo split.

## Lượt đo độ trễ lặp lại

Sau khi hoàn tất benchmark chất lượng, chạy trên cùng profile đã đóng băng:

```bash
services/rag-api/.venv/bin/python scripts/benchmark_retrieval_latency.py --reference-run data/benchmarks/reranking/DEV_RUN --repetitions 3
```

Lượt này dùng 12 câu dev smoke, 3 lần lặp đầy đủ cho cả 5 cấu hình, xáo trộn thứ tự mỗi lần, xuất 180 mẫu timing. Không cộng các lượt lặp vào số câu độc lập của thống kê chất lượng. Chroma ANN có thể trả thứ tự hoặc tập ứng viên hơi khác khi mở lại index; script ghi số candidate hash/set khác reference để công bố, không sửa nhãn hoặc coi đó là quan sát chất lượng mới. Phép so sánh có/không rerank trong mỗi run chất lượng vẫn dùng cùng pool đã lưu.

## Replay fusion với hai pool cố định

Để đổi RRF weight mà không nhầm biến động ANN với tác động thuật toán:

```bash
services/rag-api/.venv/bin/python scripts/replay_retrieval_fusion.py --reference-run data/benchmarks/reranking/TEST_RUN --weight 0.5
```

Script trước hết xác minh fusion weight gốc tái tạo đúng candidate hash của mọi query, rồi chỉ thay weight trên các danh sách Dense/BM25 đã lưu. Đây là phép đo chất lượng replay, không có latency search live; kết quả sensitivity không được dùng như test độc lập mới. `scripts/analyze_retrieval_cases.py --run-dir ...` kiểm tra thêm gold ranks và offset evidence so với token budget.

Để khôi phục môi trường chính xác: cài CPU torch như trên, sau đó `pip install -r services/rag-api/requirements-benchmark.lock` bằng pip trong venv. Báo cáo tổng hợp và chỉ mục artifacts nằm tại [docs/benchmarks](../../../docs/benchmarks/README.md).
