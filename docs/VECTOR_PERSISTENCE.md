# Lưu trữ vector trên Cloud Run — trade-off

## Vấn đề

Cloud Run scale-to-zero và filesystem container là **không bền** cho dữ liệu ghi liên tục. Chroma `PersistentClient` lưu SQLite + index trên đĩa — khi instance mới khởi động, đĩa có thể **trống** (mất index).

## Các hướng

| Hướng | Ưu | Nhược |
|--------|-----|--------|
| **Volume Docker (local dev)** | Đơn giản, ổn định | Chỉ trên máy dev / VM có volume |
| **GCS sync (MVP cloud)** | Không cần Cloud SQL; backup được | Cold start phải restore → chậm; cần logic sync |
| **pgvector + Cloud SQL** | ACID, query song song tốt | Chi phí + cấu hình mạng/IAM |
| **Chroma server riêng (VM / GKE)** | Tách lifecycle khỏi API | Vận hành thêm một tier |

## MVP khuyến nghị (demo)

1. **Local:** `docker-compose` gắn volume `chroma-data` (đã cấu hình trong repo).
2. **Cloud Run demo ngắn:** chấp nhận mất dữ liệu khi scale to zero **hoặc** đặt **min instances = 1** (có phí nhỏ) để giữ đĩa trong vòng đời instance lâu hơn (vẫn không đảm bảo vĩnh viễn).
3. **Báo cáo:** ghi rõ hạn chế và hướng **GCS tarball** (nén thư mục Chroma đẩy lên bucket sau mỗi ingest) như kiến trúc trong `plans/TLU_AI_ASSISTANT_ARCHITECTURE.md`.

## Biến môi trường (tùy chỉnh sau)

- `CHROMA_DATA_DIR`: đường dẫn lưu Chroma (trong container thường `/tmp/chroma` hoặc `/data/chroma` nếu gắn volume Cloud Run).

Script `gsutil rsync` hoặc thư viện `google-cloud-storage` có thể thêm vào worker sau; không bắt buộc cho luồng E2E đầu tiên.
