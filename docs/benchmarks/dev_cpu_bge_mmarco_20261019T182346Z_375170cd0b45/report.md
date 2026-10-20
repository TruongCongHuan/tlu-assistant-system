# Báo cáo benchmark retrieval/reranking TLU

Run: `dev_cpu_bge_mmarco_20261019T182346Z_375170cd0b45`; split `dev`; smoke=False.

**Kết quả đo thật trên bộ nhãn thử nghiệm do agent biên soạn và kiểm tra nguồn; chưa được người độc lập thẩm định.**
Không sinh câu trả lời hoặc gọi judge LLM, theo phạm vi người dùng đã chốt.

Corpus có 321 chunk; candidate K=20, final K=5.
Embedding: `BAAI/bge-m3`; reranker: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`.
Chế độ int8: False; peak process RSS=1026 MiB.
Các revision, cấu hình, source hashes và môi trường nằm trong [manifest](manifest.json).

| Config | n answerable | Candidate Hit@K | Known-gold Recall@K | Hit@5 | MRR@5 | nDCG@5 | Ranking p50/p95 ms |
|---|---:|---:|---:|---:|---:|---:|---|
| A | 43 | 0.9767 | 0.9612 | 0.9535 | 0.8062 | 0.8159 | 5.4 / 7.7 |
| B | 43 | 0.9302 | 0.9109 | 0.8605 | 0.6810 | 0.6879 | 3.6 / 5.7 |
| C | 43 | 0.9767 | 0.9612 | 0.9302 | 0.7946 | 0.8020 | 9.2 / 13.2 |
| D | 43 | 0.9767 | 0.9612 | 0.8837 | 0.6888 | 0.7116 | 5657.7 / 8170.3 |
| E | 43 | 0.9767 | 0.9612 | 0.8837 | 0.6888 | 0.7116 | 5702.4 / 8014.0 |

A = Dense; B = BM25; C = Hybrid RRF; D = Dense + Cross-Encoder; E = Hybrid + Cross-Encoder.

## So sánh theo cặp

- D-A: Δ nDCG@5=-0.1044, bootstrap CI 95% [-0.1928, -0.0292], 43 câu/36 nhóm; Hit tăng 1, giảm 4 câu.
- E-C: Δ nDCG@5=-0.0904, bootstrap CI 95% [-0.1761, -0.0199], 43 câu/36 nhóm; Hit tăng 1, giảm 3 câu.
- C-A: Δ nDCG@5=-0.0140, bootstrap CI 95% [-0.0761, +0.0374], 43 câu/36 nhóm; Hit tăng 0, giảm 1 câu.

## Giới hạn và cách đọc

- Đây là known-gold metrics trên evidence đã chỉ định, chưa phải qrels đầy đủ toàn corpus. Candidate ngoài tập positive chưa được gán nhãn âm; không kết luận mọi kết quả khác là sai.
- OOS bị loại khỏi mẫu số retrieval; không thể suy ra tỷ lệ từ chối vì không chạy generation hoặc bộ phân loại answerability.
- Độ trễ đo Chroma/BM25/rerank với vector query đã cache, chưa gồm embedding query, cold model load hoặc network. Các trường thời gian thành phần không đồng nghĩa latency API live.
- Lượt lặp cấu hình: 1; nếu chỉ 1 lượt thì p95 chỉ mô tả các câu trong lượt đó, chưa đáp ứng đánh giá độ ổn định vận hành 3 lượt.
- Hai cấu hình có/không rerank dùng cùng hash candidate pool. Các intent cùng nguồn được giữ cùng split và dùng cluster bootstrap.
- Bảng chi tiết gồm coverage và lỗi trong [summary](summary.json); không dùng số mẫu cũ làm baseline.

![Chất lượng và độ trễ](quality_latency.png)

## Artifacts

[Per query](per_query.csv), [rankings](rankings.jsonl), [candidate pools](candidates.jsonl), [paired comparisons](comparison.json), [latency](latency.csv), [errors](errors.jsonl).

## Ví dụ kiểm tra được

| Query | Config | Top-5 chunk IDs | Loại |
|---|---|---|---|
| Q01 | D | k38-v1:4:10bf9b2ebc7df41a, k38-v1:236:03baf4dcae1f9dc3, k38-v1:67:df287f2b0f7cc4ad, k38-v1:232:517be18c962e8ea8, k38-v1:226:16ab63db44b1c2a5 | hit |
| Q01 | B | k38-v1:4:10bf9b2ebc7df41a, k38-v1:78:b61697aa7070d838, k38-v1:67:df287f2b0f7cc4ad, k38-v1:232:517be18c962e8ea8, k38-v1:58:b50412aa076f330a | hit |
| Q01 | C | k38-v1:4:10bf9b2ebc7df41a, k38-v1:67:df287f2b0f7cc4ad, k38-v1:237:e733b077d8b8a298, k38-v1:232:517be18c962e8ea8, k38-v1:228:b1c434d4d005776b | hit |
| Q09 | B | k38-v1:256:db9d4d137a8a1ef2, k38-v1:260:7546dca23d073d12, k38-v1:232:517be18c962e8ea8, k38-v1:234:c75680dc8935264f, k38-v1:206:6abef9b69f08a43f | top5_miss |
| Q19 | B | k38-v1:111:996ad9ca2c625691, k38-v1:43:668cddbadf2d4a86, k38-v1:44:625bec22a87530a0, k38-v1:127:e75c4f1ab3cf7a9d, k38-v1:41:abde056d9e80c8a7 | candidate_miss |
| Q19 | D | k38-v1:158:1dfa066f467384cb, k38-v1:40:5920b9fc6786175a, k38-v1:62:6d0490d75f02cf53, k38-v1:43:668cddbadf2d4a86, k38-v1:39:1addba2fbe980ec7 | top5_miss |
| Q19 | E | k38-v1:158:1dfa066f467384cb, k38-v1:40:5920b9fc6786175a, k38-v1:62:6d0490d75f02cf53, k38-v1:43:668cddbadf2d4a86, k38-v1:39:1addba2fbe980ec7 | top5_miss |
| Q39 | B | k38-v1:39:1addba2fbe980ec7, k38-v1:294:661f2b98ff646c1d, k38-v1:297:fc41f974ac27e395, k38-v1:293:015bc56695b9e2ef, k38-v1:43:668cddbadf2d4a86 | candidate_miss |
| Q50 | D | k38-v1:35:34ba3eb139ebd267, k38-v1:190:bb90e08597e926f1, k38-v1:43:668cddbadf2d4a86, k38-v1:149:d9907e18287659f5, k38-v1:7:71d8345c3d328321 | candidate_miss |
