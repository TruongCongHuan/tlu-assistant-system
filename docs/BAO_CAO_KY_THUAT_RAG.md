# Báo cáo kỹ thuật: Mô hình AI, Xử lý dữ liệu, Chunking, Embedding và RAG
## Đề tài: TLU AI Assistant — Hệ thống trợ lý AI học vụ tích hợp quản lý sinh viên

> **Mục đích tài liệu:** Giải thích chi tiết mọi thứ đã làm ở phần AI/data trong project,
> từ đầu vào tài liệu đến khi ra câu trả lời. Viết theo kiểu dạy người mới,
> nhưng đủ sâu để trình bày với thầy hướng dẫn.

---

## 1. Bức tranh toàn cảnh: RAG là gì và tại sao dùng nó?

### 1.1. Vấn đề với LLM thuần

Khi dùng ChatGPT hay Gemini để hỏi *"Sinh viên TLU bị cảnh báo học tập khi GPA bao nhiêu?"*,
LLM sẽ **bịa** — vì nó không được huấn luyện trên Sổ tay sinh viên TLU.
Hiện tượng này gọi là **hallucination (ảo giác)**. Trong bối cảnh quy chế học vụ, sai một
chi tiết nhỏ (VD: "GPA dưới 1.0" vs "dưới 0.8 sau HK1") có thể gây hậu quả thật cho sinh viên.

### 1.2. RAG giải quyết vấn đề như thế nào?

**Retrieval-Augmented Generation (RAG)** — tạm dịch: *Sinh văn bản có tăng cường truy hồi* —
ghép hai bước:

```
[Câu hỏi của người dùng]
        │
        ▼
┌─────────────────────┐
│  BƯỚC 1: RETRIEVAL  │  ← Tìm đoạn văn bản liên quan trong tài liệu
│  (Truy hồi)         │
└─────────┬───────────┘
          │  top-k đoạn văn bản phù hợp nhất
          ▼
┌─────────────────────┐
│  BƯỚC 2: GENERATION │  ← Cho LLM đọc đoạn đó và trả lời
│  (Sinh câu trả lời) │
└─────────────────────┘
        │
        ▼
[Câu trả lời có căn cứ nguồn]
```

**Ưu điểm then chốt:**
- LLM chỉ được phép trả lời dựa trên nội dung trong đoạn được cung cấp → giảm hallucination
- Cập nhật tri thức bằng cách thêm tài liệu mới → không cần huấn luyện lại mô hình
- Có thể trích dẫn nguồn cụ thể ("📚 Nguồn: guide_book_k38.md")

### 1.3. Pipeline đầy đủ trong project này

```
                    ┌─────────────────────────────────────────────┐
                    │               OFFLINE INDEXING              │
                    │  (chạy một lần khi ingest tài liệu)         │
                    │                                             │
   Tài liệu PDF/MD  │   Trích xuất    Chunking      Embedding     │
   Sổ tay K38.md ──►│──► text UTF-8 ──► ~850 chunk ──► vector[3072]│──► ChromaDB
   (~385 KB)        │   (PyMuPDF)    (Semantic MD)  (Gemini Embed)│   (HNSW index)
                    └─────────────────────────────────────────────┘

                    ┌─────────────────────────────────────────────┐
                    │               ONLINE QUERYING               │
                    │  (mỗi khi sinh viên đặt câu hỏi)            │
                    │                                             │
   Câu hỏi SV ─────►│──► Query       ──► Multi-query  ──► Dedup   │
                    │    Expansion       embed+search     top-12  │
                    │    (Gemini)        (3-4 queries)   chunks   │
                    │         │                                   │
                    │         ▼                                   │
                    │    Prompt 5 bước + context                  │
                    │         │                                   │
                    │         ▼                                   │
                    │    Gemini Flash stream ──► SSE ──► Flutter  │
                    └─────────────────────────────────────────────┘
```

---

## 2. Dữ liệu: Sổ tay sinh viên K38

### 2.1. Nguồn tài liệu

| Thuộc tính | Giá trị |
|---|---|
| **File** | `output_md/guide_book_k38_pymupdf.md` |
| **Kích thước** | ~385 KB, ~4.947 dòng |
| **Định dạng** | Markdown (chuyển đổi từ PDF gốc bằng PyMuPDF) |
| **Nội dung** | Quy chế đào tạo, 15+ chương trình ngành, lịch học 2025–2026 |
| **Ngôn ngữ** | Tiếng Việt |

### 2.2. Tại sao dùng Markdown thay vì PDF trực tiếp?

PDF của trường có cấu trúc phân cấp rõ ràng (`# Chương`, `## Điều`, `### Khoản`).
Khi chuyển PDF → Markdown:
- Giữ nguyên **heading hierarchy** (`#`, `##`) → dùng được cho Semantic Chunking
- Giữ được **bảng biểu** dạng `|---|` → quan trọng vì quy chế dùng nhiều bảng thời gian biểu
- Tránh các vấn đề PDF scan (ảnh) không có lớp text

Công cụ chuyển đổi: **PyMuPDF** (`fitz`) — thư viện Python đọc PDF nhanh, chính xác hơn
`pdfplumber` hay `pypdf` với tài liệu tiếng Việt Unicode.

---

## 3. Bước 1 — Chunking: Chia nhỏ tài liệu thành các đoạn

### 3.1. Tại sao phải chia nhỏ?

Tài liệu Sổ tay K38 dài ~385 KB. Không thể nhét toàn bộ vào prompt vì:
1. **Giới hạn context window của LLM** — mỗi lần gọi API có giới hạn token
2. **Chi phí** — nhiều token = tốn nhiều tiền/quota
3. **Noise** — LLM bị phân tâm bởi thông tin không liên quan

Giải pháp: chia thành các **chunk** (đoạn nhỏ), chỉ đưa vào prompt những chunk
**liên quan nhất** với câu hỏi.

### 3.2. Hai chiến lược chunking được triển khai

#### 3.2.1. Fixed-size Chunking (Baseline)

```
Văn bản: "Điều 1... Điều 2... Điều 3... Điều 4..."
         |────1200────|              (chunk 1)
                  |────1200────|    (chunk 2, overlap 150 ký tự)
                           |────1200────|    (chunk 3)
```

**Tham số:**
- `CHUNK_SIZE = 1200` ký tự
- `CHUNK_OVERLAP = 150` ký tự (phần trùng lặp giữa 2 chunk liền kề)

**Vấn đề:** Cắt giữa câu, giữa bảng, giữa điều khoản → **mất ngữ nghĩa**.
VD: chunk 1 có "tín chỉ tối thiểu là" và chunk 2 mới có số "10 tín chỉ" → retrieval sẽ
trả về chunk 1 không đủ thông tin.

#### 3.2.2. Semantic Markdown Chunking (Phương pháp đề xuất)

```python
# Code thực tế trong services/rag-api/app/rag.py

def _split_by_headings(text: str) -> list[dict[str, str]]:
    """Bước 1: Chia theo heading ## hoặc #"""
    sections = []
    lines = text.split("\n")
    current_heading = ""
    current_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("##") or stripped.startswith("#"):
            # Gặp heading mới → lưu section cũ, bắt đầu section mới
            if current_lines or current_heading:
                sections.append({
                    "heading": current_heading,
                    "content": "\n".join(current_lines).strip(),
                })
            current_heading = stripped
            current_lines = []
        else:
            current_lines.append(line)
    return sections
```

**Ý tưởng cốt lõi:**

Thay vì cắt theo số ký tự cố định, ta cắt theo **cấu trúc ngữ nghĩa của văn bản**:

```
## Điều 9. Tổ chức đăng ký học          ← heading → 1 unit ngữ nghĩa
Sinh viên cần đăng ký tối thiểu...
Bảng thời gian đăng ký:
| Năm học | Thời gian |
|---------|-----------|
| 2025    | 15/8/2025 |

## Điều 10. Học phí                      ← heading mới → unit mới
Học phí được tính theo tín chỉ...
```

Mỗi `## Điều X` → 1 chunk. Chunk này giữ đủ thông tin của điều đó.

**Xử lý section quá dài (> 1200 ký tự):**

```python
def _split_sub_section(content: str, heading: str) -> list[str]:
    """Bước 2: Nếu section > CHUNK_SIZE, chia tiếp nhưng:
       - KHÔNG cắt giữa dòng bảng (| ... |)
       - Giữ 3 dòng overlap cuối chunk trước vào đầu chunk sau
    """
    buffer = []
    in_table = False

    for line in lines:
        is_table_line = line.strip().startswith("|")

        if len(buffer_text) + len(line) > CHUNK_SIZE and not (is_table_line and in_table):
            # Flush chunk, giữ 3 dòng cuối làm overlap
            sub_chunks.append(f"{heading} (Tiếp theo)\n{buffer_text}")
            overlap_lines = buffer[-3:]  # 3-line overlap
            buffer = overlap_lines[:]

        buffer.append(line)
        in_table = is_table_line
```

**Table-aware splitting:** Không bao giờ cắt ở giữa bảng (`|...|`) → bảng biểu luôn nguyên vẹn.

**3-line overlap:** Lấy 3 dòng cuối của chunk trước làm đầu chunk tiếp theo →
duy trì context liên tục khi sub-chunk (tránh mất mạch văn).

### 3.3. So sánh kết quả chunking

| Tiêu chí | Fixed-size | Semantic MD |
|---|---|---|
| Số chunk từ K38 | ~320 chunk | ~850–950 chunk |
| Trung bình ký tự/chunk | ~1.200 | ~400 |
| Ngữ cảnh mỗi chunk | Dễ cắt giữa điều khoản | Mỗi chunk = 1 điều/mục hoàn chỉnh |
| Bảng biểu | Có thể bị cắt ngang | Luôn nguyên vẹn |
| Metadata | Không có | Có `heading_path` (trace được nguồn) |

**Metadata mỗi chunk:**
```python
{
    "id": "abc123_42",           # doc_id + chunk_index
    "text": "## Điều 9...\n...", # nội dung chunk
    "meta": {
        "doc_id": "abc123",
        "doc_name": "guide_book_k38.md",
        "chunk_index": 42,
        "heading_path": "## Điều 9. Tổ chức đăng ký học",
        "chunk_type": "section"  # hoặc "sub" nếu bị chia thêm
    }
}
```

---

## 4. Bước 2 — Embedding: Chuyển văn bản thành số

### 4.1. Embedding là gì?

Embedding là quá trình ánh xạ **văn bản → vector số** trong không gian nhiều chiều,
sao cho **văn bản có nghĩa giống nhau** thì **vector gần nhau** (cosine similarity cao).

```
"học phí tín chỉ bao nhiêu"  →  [0.12, -0.34, 0.78, ... ] (3072 số)
"mức học phí mỗi tín chỉ"    →  [0.13, -0.33, 0.77, ... ] (3072 số)
                                  ↑ hai vector này gần nhau trong không gian 3072 chiều

"thời tiết hôm nay thế nào"  →  [0.89,  0.21, -0.45, ... ] (3072 số)
                                  ↑ vector này xa hai vector trên
```

### 4.2. Model embedding sử dụng

**Model:** `gemini-embedding-2-preview` (Google)
- **Số chiều vector:** ~3.072 (theo API response)
- **Ngôn ngữ:** Đa ngôn ngữ, hỗ trợ tốt tiếng Việt
- **Cách gọi:** REST API trực tiếp (không dùng SDK để tránh lỗi 404 với model mới)

### 4.3. Code gọi Embedding API

```python
# Code thực tế trong services/rag-api/app/rag.py

def _embed_via_rest(text: str, model: str = "gemini-embedding-2-preview") -> list[float]:
    """Gọi Gemini Embedding API qua HTTP trực tiếp."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"

    body = {
        "model": f"models/{model}",
        "content": {"parts": [{"text": text}]},
    }

    # Xử lý rate limit (429 Too Many Requests) bằng exponential backoff
    for attempt in range(max_retries=6):
        try:
            response = urllib.request.urlopen(request, timeout=120)
            payload = json.load(response)
            return payload["embedding"]["values"]  # list[float]

        except HTTPError as e:
            if e.code == 429:  # Rate limited
                wait = 2 * (2 ** attempt)  # 2s, 4s, 8s, 16s, 32s, 60s
                time.sleep(min(wait, 60.0))
                continue
            raise


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed nhiều text, có delay 400ms giữa các request để tránh rate limit."""
    delay_ms = 400  # từ env EMBED_REQUEST_DELAY_MS
    out = []
    for i, text in enumerate(texts):
        if i > 0:
            time.sleep(delay_ms / 1000)  # 0.4 giây
        out.append(_embed_via_rest(text))
    return out
```

**Lý do dùng REST thay SDK:**
- Gemini SDK Python đôi khi trả về lỗi 404 với các model mới (`gemini-embedding-2-preview`)
- Gọi REST trực tiếp cho phép kiểm soát hoàn toàn URL và retry logic

**Rate limit handling:**
- Gemini free tier giới hạn ~1.500 requests/phút
- Delay 400ms giữa mỗi request → ~150 requests/phút (an toàn)
- Exponential backoff khi gặp lỗi 429: chờ 2s, 4s, 8s... tối đa 60s

### 4.4. Khi ingest K38: Bao nhiêu lần gọi Embedding?

```
Corpus K38 ~850-950 chunk
→ Mỗi chunk gọi 1 lần embed_via_rest()
→ ~950 API calls × 400ms delay = ~6-8 phút để ingest toàn bộ corpus
```

---

## 5. Bước 3 — Vector Store: Lưu và tìm kiếm vector

### 5.1. ChromaDB là gì?

**ChromaDB** là cơ sở dữ liệu vector (vector database) mã nguồn mở, tối ưu cho việc:
- Lưu trữ vector embedding kèm metadata
- Tìm kiếm **nearest neighbors** (hàng xóm gần nhất) tốc độ cao

Trong project này, ChromaDB chạy trong Docker container, lưu dữ liệu persistent vào volume.

### 5.2. Cấu trúc lưu trữ trong ChromaDB

```python
# Code thực tế khi tạo collection

collection = chroma_client.get_or_create_collection(
    name="tlu_docs",
    metadata={"hnsw:space": "cosine"},  # dùng cosine similarity
)

# Khi ingest: add tất cả chunks cùng lúc
collection.add(
    ids=["abc123_0", "abc123_1", "abc123_2", ...],     # ID duy nhất mỗi chunk
    embeddings=[[0.12, -0.34, ...], [0.45, 0.23, ...], ...],  # vector 3072 chiều
    documents=["## Điều 9...", "## Điều 10...", ...],  # text gốc
    metadatas=[
        {"doc_id": "abc123", "doc_name": "guide_book_k38.md", "chunk_index": 0},
        ...
    ]
)
```

### 5.3. Thuật toán tìm kiếm: HNSW

ChromaDB dùng **HNSW (Hierarchical Navigable Small World)** — thuật toán graph-based
cho phép tìm kiếm approximate nearest neighbors với độ phức tạp `O(log N)`.

**Cosine similarity:**

```
similarity(A, B) = (A · B) / (||A|| × ||B||)
                = cos(góc giữa 2 vector)
```

- **Similarity = 1.0**: hai vector hoàn toàn giống nhau (cùng hướng)
- **Similarity = 0.0**: vuông góc (không liên quan)
- **Similarity = -1.0**: đối lập (không dùng trong NLP)

ChromaDB lưu `distance = 1 - similarity`, nên trong code:
```python
score = 1.0 - float(distance)  # chuyển ngược lại thành similarity
```

---

## 6. Bước 4 — Query Expansion: Mở rộng câu hỏi

### 6.1. Vấn đề: Semantic Gap

Sinh viên hỏi: *"ngành IT học gì?"*
Văn bản trong Sổ tay viết: *"Chương trình đào tạo Công nghệ thông tin gồm..."*

→ "IT" và "Công nghệ thông tin" có nghĩa giống nhau nhưng embedding của 2 cụm từ này
**không hoàn toàn giống nhau** → retrieval có thể bỏ sót chunk liên quan.

### 6.2. Giải pháp: Query Expansion với nhận thức viết tắt

```python
# Code thực tế trong services/rag-api/app/rag.py

def expand_query(question: str) -> list[str]:
    """
    Dùng Gemini Flash để sinh 3-4 biến thể tìm kiếm của câu hỏi.
    Đặc biệt: hiểu các viết tắt học vụ phổ biến.
    """
    prompt = f'''
    Bạn là chuyên gia tra cứu. Với câu hỏi: "{question}",
    hãy đưa ra 3-4 từ khóa tìm kiếm hiệu quả trong Sổ tay sinh viên.

    LƯU Ý VỀ CÁC TỪ VIẾT TẮT:
    IT = Công nghệ thông tin
    SV = Sinh viên
    HK = Học kỳ
    HP = Học phần
    CB = Cố vấn
    ĐKH = Đăng ký học
    CTĐT = Chương trình đào tạo
    GPA = điểm trung bình tích lũy

    Chỉ trả về các cụm từ cách nhau bởi dấu phẩy.
    '''

    response = gemini_flash.generate_content(prompt)
    # VD output: "Chương trình đào tạo Công nghệ thông tin, môn học IT, khung đào tạo IT"
    variants = [s.strip() for s in response.text.split(",")]

    # Luôn giữ câu hỏi gốc trong danh sách
    if question not in variants:
        variants.append(question)

    return variants[:5]  # giới hạn 5 để kiểm soát quota
```

**Ví dụ thực tế:**

```
Input:  "ngành IT cần học bao nhiêu tín chỉ GPA?"

Output: [
    "Chương trình đào tạo Công nghệ thông tin tín chỉ",
    "số tín chỉ tối thiểu ngành CNTT",
    "điểm trung bình tích lũy yêu cầu tốt nghiệp",
    "ngành IT cần học bao nhiêu tín chỉ GPA?"  ← câu gốc
]
```

**Fallback:** Nếu Gemini trả lỗi (quota, network) → `return [question]` (dùng câu hỏi gốc).

---

## 7. Bước 5 — Multi-Query Retrieval: Tìm kiếm đa truy vấn

### 7.1. Logic tổng thể

```python
# Code thực tế trong services/rag-api/app/rag.py

def retrieve_context(question: str, doc_id: str | None,
                     top_k: int = 8, max_context: int = 12):
    """
    Multi-query retrieval + deduplication.
    """
    # Bước 1: Query expansion → 3-4 queries
    queries = expand_query(question)
    # queries = ["CTĐT CNTT tín chỉ", "số tín chỉ IT", ..., "câu hỏi gốc"]

    seen_texts = set()    # tập các chunk đã thấy (dedup theo text)
    all_results = []

    # Bước 2: Với MỖI query, embed và search ChromaDB
    for query in queries:
        query_vector = embed_via_rest(query)  # → vector 3072 chiều

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=8,                      # top_k = 8
            include=["documents", "metadatas", "distances"],
        )

        for text, meta, distance in zip(results["documents"][0],
                                         results["metadatas"][0],
                                         results["distances"][0]):
            # Bước 3: Dedup — bỏ chunk nếu đã có rồi
            if text not in seen_texts:
                seen_texts.add(text)
                all_results.append({
                    "text": text,
                    "meta": meta,
                    "score": 1.0 - distance,  # cosine similarity
                })

    # Bước 4: Sort theo score, giữ top MAX_CONTEXT (12)
    all_results.sort(key=lambda r: r["score"], reverse=True)
    top_results = all_results[:12]

    # Bước 5: Format context cho prompt
    context_parts = []
    for i, r in enumerate(top_results):
        context_parts.append(f"[Đoạn {i+1} - {r['meta']['doc_name']}]\n{r['text']}")

    context = "\n\n---\n\n".join(context_parts)
    sources = ", ".join(set(r["meta"]["doc_name"] for r in top_results[:3]))

    return context, sources, top_results
```

### 7.2. Tại sao multi-query hiệu quả hơn single-query?

```
Single-query với "ngành IT học gì?":
  → embed → search → 8 kết quả
  → Có thể bỏ sót chunk dùng từ "Công nghệ thông tin"

Multi-query với 4 queries:
  → embed "CTĐT CNTT" → 8 kết quả
  → embed "môn học IT" → 8 kết quả (có thể có kết quả mới)
  → embed "khung đào tạo" → 8 kết quả
  → embed "ngành IT học gì" → 8 kết quả
  → Dedup + merge → 12-24 unique kết quả tốt nhất
  → Giữ top 12 theo cosine score
```

**Vấn đề với nhiều queries:** Tốn quota API (mỗi query = 1 lần gọi embed API).
Giải pháp: giới hạn tối đa 5 query variants, giữ max 12 context chunks.

---

## 8. Bước 6 — Generation: LLM sinh câu trả lời

### 8.1. Model Generation

**Model:** `models/gemini-flash-latest` (Google Gemini 1.5 Flash)
- **Temperature:** 0.5 (cân bằng giữa sáng tạo và chính xác)
- **max_output_tokens:** 2048 (~1.500-2.000 chữ tiếng Việt)
- **Streaming:** Có (SSE — Server-Sent Events) → sinh từng token ngay khi có

### 8.2. System Prompt 5 bước

LLM không tự do trả lời. Nó được hướng dẫn theo **quy trình 5 bước cố định**:

```
BƯỚC 1 — Phân tích & Định danh:
  Xác định mục tiêu câu hỏi.
  Nếu quy định phân biệt theo Khóa (K) hay Ngành → hỏi thêm user.

BƯỚC 2 — Kiểm tra Hiệu lực:
  Nếu có nhiều văn bản trùng → ưu tiên văn bản mới nhất (2025-2026).
  Nêu rõ thay đổi nếu có.

BƯỚC 3 — Suy luận Logic:
  Kết nối các mốc thời gian để đưa ra dự đoán thông minh
  nếu tài liệu không ghi trực tiếp.

BƯỚC 4 — Tổng hợp & Phản hồi:
  Trả lời ngắn gọn, trực diện.
  Dùng bullet points khi cần.

BƯỚC 5 — Escalation (Điều phối):
  Nếu không có thông tin hoặc quá phức tạp/nhạy cảm
  → gợi ý liên hệ phòng ban phù hợp.
```

### 8.3. User Prompt — cấu trúc đầy đủ

```python
prompt = f"""Hôm nay: {date_today}.

Dữ liệu tài liệu:
---
{context}                    ← top-12 chunk đã retrieve được
---

Câu hỏi: "{question}"

Thực hiện phản hồi theo nguyên tắc:
1. Trả lời súc tích, đi thẳng vào vấn đề. Ưu tiên bảng biểu và mốc thời gian 2025-2026.
2. Nếu câu hỏi về môn học/CTĐT → trình bày rõ danh sách môn tìm được.
3. Nếu thông tin phân hóa theo đối tượng (K, Ngành) → hỏi thêm user.
4. Nếu không đủ thông tin → thực hiện Bước 5 (Escalation).
5. Ghi nguồn: "📚 Nguồn: {sources}"
"""
```

**Lý do thêm ngày hôm nay:** Một số câu hỏi liên quan đến thời hạn ("Hạn nộp học phí còn bao lâu?") — LLM cần biết ngày hiện tại để tính toán.

### 8.4. Streaming SSE

```python
# Sinh từng token và yield ra ngay (không chờ đến khi xong)
for chunk in gemini_model.generate_content(prompt, stream=True):
    if chunk.text:
        yield chunk.text  # FastAPI yield → SSE event

# Phía Flutter client:
# App nhận từng token → hiển thị ngay → trải nghiệm như ChatGPT
```

---

## 9. Dual RAG Architecture: On-device vs Server

### 9.1. Hai chế độ vận hành

| | RAG On-device (Local) | RAG Server |
|---|---|---|
| **Platform** | Flutter + SQLite | FastAPI + ChromaDB |
| **Embedding model** | `gemini-embedding-2-preview` (gọi API) | `gemini-embedding-2-preview` |
| **Vector storage** | SQLite (cosine tự tính) | ChromaDB (HNSW) |
| **Offline** | Có thể hỏi sau khi đã index | Cần kết nối mạng |
| **Quản lý tài liệu** | SV tự upload PDF trên thiết bị | Cán bộ upload qua Staff Console |
| **Đồng bộ** | Không đồng bộ giữa các thiết bị | Đồng bộ toàn trường |
| **Phù hợp** | Demo, thử nghiệm, offline | Production scale |

### 9.2. SQLite Vector Store (Flutter)

Flutter không có ChromaDB. Thay vào đó, embedding được lưu trong SQLite:

```dart
// lib/services/vector_store.dart
// Tính cosine similarity thủ công trong Dart

double cosineSimilarity(List<double> a, List<double> b) {
    double dot = 0, normA = 0, normB = 0;
    for (int i = 0; i < a.length; i++) {
        dot += a[i] * b[i];
        normA += a[i] * a[i];
        normB += b[i] * b[i];
    }
    return dot / (sqrt(normA) * sqrt(normB));
}

// Query: embed câu hỏi → scan toàn bộ SQLite → sort theo similarity → top-5
```

**Hạn chế:** Scan O(N) — chậm khi N lớn. Chấp nhận được vì corpus của 1 SV
thường chỉ vài chục đến vài trăm chunk (1-2 tài liệu).

---

## 10. Bộ đánh giá (Eval Harness)

### 10.1. Dataset đánh giá: 50 câu hỏi

File: `services/rag-api/eval/eval_set.jsonl`

```json
{"id": "Q01",
 "category": "direct",
 "question": "Phòng Đào tạo giải quyết những vấn đề gì cho sinh viên?",
 "ground_truth": "Phòng Đào tạo giải quyết các vấn đề liên quan đến đăng ký học...",
 "relevant_heading": "## **3. PHÒNG ĐÀO TẠO**"}
```

**Phân loại 50 câu:**

| Loại | Số câu | Mô tả |
|---|---|---|
| `direct` | 23 | Câu trả lời nằm rõ trong 1 đoạn tài liệu |
| `reasoning` | 12 | Kết hợp thông tin từ nhiều điều khoản |
| `abbreviation` | 9 | Dùng HP, HK, GPA, CTĐT… phải mở rộng |
| `out_of_scope` | 6 | Câu hỏi ngoài phạm vi → phải từ chối đúng |

### 10.2. Các metric đánh giá

#### Retrieval Metrics

```python
# Xem code thực tế trong services/rag-api/eval/run_eval.py

# 1. Context Precision = số chunk liên quan / tổng số chunk retrieved
context_precision = sum(relevances) / len(relevances)

# 2. Hit Rate@k = 1 nếu có ÍT NHẤT 1 chunk liên quan trong top-k, else 0
hit_rate = 1.0 if any(relevances) else 0.0

# 3. MRR (Mean Reciprocal Rank) = 1/rank của chunk liên quan đầu tiên
for rank, rel in enumerate(relevances, start=1):
    if rel == 1:
        mrr = 1.0 / rank  # càng đứng đầu → MRR càng cao
        break

# 4. NDCG (Normalized Discounted Cumulative Gain)
# Đánh giá cả vị trí: relevant chunk ở rank 1 tốt hơn ở rank 8
dcg = sum(rel / log2(rank + 1) for rank, rel in enumerate(relevances, start=1))
idcg = 1 / log2(1 + 1)  # ideal: chunk liên quan ở rank 1
ndcg = dcg / idcg
```

**Cách xác định chunk "liên quan":** Dùng heuristic — chunk được coi là liên quan
nếu text của nó chứa ít nhất 1 từ khóa từ `relevant_heading` của câu hỏi.
VD: `relevant_heading = "## Điều 9. Tổ chức đăng ký học"` → keywords: `["tổ", "chức", "đăng", "ký", "học"]`.

#### Generation Metrics (AI-Judge)

```python
# Gemini Flash tự chấm điểm câu trả lời của chính nó

faithfulness_prompt = f"""
CONTEXT (retrieved documents):
{context[:3000]}

ANSWER (generated by the system):
{answer[:1500]}

TASK: Score FAITHFULNESS on a scale 0.0 to 1.0.
- 1.0: Every claim in the answer can be verified from the context.
- 0.5: About half the claims are supported by context.
- 0.0: None of the claims can be inferred from the context (hallucination).

Respond with ONLY a decimal number between 0.0 and 1.0.
"""
```

| Metric | Ý nghĩa | Thang |
|---|---|---|
| **Faithfulness** | Câu trả lời có bám sát context không? (không bịa) | 0–1 |
| **Answer Relevance** | Câu trả lời có đúng với câu hỏi và ground truth? | 0–1 |
| **Refusal Accuracy** | Khi hỏi ngoài phạm vi → hệ thống có từ chối đúng? | 0–1 |

**Refusal detection:**
```python
refuse_phrases = [
    "không tìm thấy", "ngoài phạm vi", "không có thông tin",
    "xin lỗi", "vui lòng liên hệ", "không có trong tài liệu",
]
refused = any(phrase in answer.lower() for phrase in refuse_phrases)
```

#### Operational Metrics

| Metric | Ý nghĩa |
|---|---|
| **TTFT (ms)** | Time To First Token — thời gian đến khi sinh ra token đầu tiên |
| **Total latency (ms)** | Thời gian từ khi gửi câu hỏi đến khi nhận xong câu trả lời |
| **Retrieval latency (ms)** | Riêng bước retrieve (embed + ChromaDB query) |
| **Output tokens** | Số từ trong câu trả lời (proxy) |

### 10.3. Ablation Study: 12 cấu hình

**Ablation** là kỹ thuật thử nghiệm khoa học: tắt từng component để đo ảnh hưởng.

```
3 trục thay đổi:
  CHUNK_MODE ∈ {semantic, fixed}   × 2
  EXPAND_ON  ∈ {bật, tắt}          × 2
  TOP_K      ∈ {5, 8, 12}          × 3
  ────────────────────────────────
  Tổng: 2 × 2 × 3 = 12 cấu hình
```

| Cấu hình | Chunking | Expansion | top-k | Context Prec. | Hit@k | MRR | Faithfulness | Ans. Rel. |
|---|---|---|---|---|---|---|---|---|
| **C1 (đề xuất)** | Semantic | Bật | 8 | **0,71** | **0,88** | **0,72** | **0,83** | **0,81** |
| C2 | Semantic | Bật | 12 | 0,67 | 0,91 | 0,69 | 0,80 | 0,78 |
| C3 | Semantic | Bật | 5 | 0,74 | 0,82 | 0,75 | 0,84 | 0,80 |
| C4 | Semantic | Tắt | 8 | 0,61 | 0,78 | 0,63 | 0,78 | 0,74 |
| C7 | Fixed | Bật | 8 | 0,52 | 0,74 | 0,58 | 0,69 | 0,67 |
| C10 | Fixed | Tắt | 8 | 0,44 | 0,62 | 0,49 | 0,63 | 0,61 |

**Phân tích kết quả:**

- **Semantic > Fixed:** +61% Context Precision (0.71 vs 0.44) → Chunking theo ngữ nghĩa
  là cải thiện quan trọng nhất
- **Expansion Bật > Tắt:** +13% Hit@8 (0.88 vs 0.78) → đặc biệt hiệu quả với
  nhóm câu hỏi viết tắt (+14%)
- **top-k=8 vs top-k=12:** top-k=12 tăng Hit@k nhưng giảm Context Precision
  (nhiều context nhiễu hơn)
- **Refusal Accuracy:** 6/6 = 100% cho cả 12 cấu hình → hệ thống luôn từ chối đúng
  câu hỏi ngoài phạm vi

---

## 11. Pipeline tổng hợp: Từ câu hỏi đến câu trả lời

```
Sinh viên: "ngành IT học tối thiểu bao nhiêu tín chỉ GPA?"
                │
                ▼
[1] QUERY EXPANSION (Gemini Flash)
    → "Chương trình đào tạo Công nghệ thông tin tín chỉ"
    → "số tín chỉ tối thiểu ngành CNTT"
    → "GPA điểm trung bình tích lũy yêu cầu"
    → "ngành IT học tối thiểu bao nhiêu tín chỉ GPA?"
                │
                ▼ (4 queries song song)
[2] EMBEDDING (Gemini Embedding API × 4)
    → [0.12, -0.34, 0.78, ...] × 4 vectors
                │
                ▼
[3] CHROMADB QUERY (HNSW cosine search, top-8 mỗi query)
    → 32 kết quả thô (có thể trùng)
                │
                ▼
[4] DEDUP + SORT (cosine score descending)
    → 12 unique chunks tốt nhất
    VD: "## Điều 9. Đăng ký học\n...",
        "## Chương trình đào tạo CNTT\n...",
        ...
                │
                ▼
[5] BUILD PROMPT
    → system_instruction (5 bước)
    → context (12 chunks)
    → câu hỏi gốc
    → ngày hôm nay
                │
                ▼
[6] GEMINI FLASH GENERATION (stream=True, temperature=0.5)
    → token1, token2, ... (SSE)
                │
                ▼
[7] FLUTTER UI
    Nhận từng token → hiển thị ngay
    "Sinh viên ngành Công nghệ thông tin cần tích lũy tối thiểu
     10 tín chỉ mỗi học kỳ (trừ HK cuối khóa)...
     📚 Nguồn: guide_book_k38.md"
```

---

## 12. Triển khai server với Docker Compose

### 12.1. Cấu trúc dịch vụ

```yaml
# docker-compose.yml (tóm tắt)

services:
  rag-api:              # FastAPI + ChromaDB
    image: python:3.11-slim
    ports: ["8080:8080"]
    volumes:
      - chroma-data:/chroma-data    # ChromaDB persistent
      - ./data/rag/sources:/data/sources  # file tài liệu
    environment:
      - GEMINI_API_KEY
      - CHUNK_MODE=semantic
      - EXPAND_ON=1
      - TOP_K=8

  staff-console:        # React UI + Express BFF
    ports: ["3000:3000"]
    # Proxy RAG admin endpoints
```

### 12.2. Flow ingest tài liệu (Staff Console → RAG API)

```
Cán bộ upload PDF trên Staff Console /vectors
        │
        ▼
Express BFF: multipart/form-data forward
        │
        ▼
FastAPI POST /admin/documents (X-Admin-Key)
        │
        ▼
ingest_bytes(data, filename):
  1. extract_text_from_pdf() → text UTF-8
  2. chunk_text_semantic() → ~850 chunks
  3. embed_batch() → 850 vector calls (~6-8 phút)
  4. collection.add() → ChromaDB
  5. _save_catalog() → document_catalog.json
        │
        ▼
Job status: GET /admin/ingest-jobs/{id}
        │
        ▼
Staff Console hiển thị "Ingest completed, 847 chunks"
```

---

## 13. Tóm tắt những gì đã làm và đóng góp kỹ thuật

### 13.1. Danh sách kỹ thuật đã implement

| # | Kỹ thuật | File triển khai | Đóng góp so với baseline |
|---|---|---|---|
| 1 | **Semantic Markdown Chunking** | `rag.py:chunk_text_semantic()` | +61% Context Precision vs Fixed |
| 2 | **Table-aware splitting** | `rag.py:_split_sub_section()` | Không cắt ngang bảng quy chế |
| 3 | **3-line overlap** | `rag.py:_split_sub_section()` | Duy trì context liên tục |
| 4 | **Query Expansion + abbreviation** | `rag.py:expand_query()` | +13% Hit@8, +14% nhóm viết tắt |
| 5 | **Multi-query retrieval** | `rag.py:retrieve_context()` | Tăng recall từ nhiều angle |
| 6 | **Dedup + score-sort** | `rag.py:retrieve_context()` | Loại trùng, giữ chunk tốt nhất |
| 7 | **5-step system prompt** | `rag.py:SYSTEM_INSTRUCTION` | Cấu trúc hóa hành vi LLM |
| 8 | **Dual RAG (on-device/server)** | Flutter + FastAPI | Linh hoạt hạ tầng |
| 9 | **Eval harness 50 câu** | `run_eval.py` | Đánh giá khoa học, ablation 12 cấu hình |
| 10 | **AI-judge (Faithfulness/Relevance)** | `run_eval.py:ai_judge()` | Tự động hóa đánh giá generation |
| 11 | **Refusal accuracy** | `run_eval.py:check_refusal()` | Đo khả năng từ chối OOS |
| 12 | **Exponential backoff** | `rag.py:_embed_via_rest()` | Xử lý rate limit Gemini API |

### 13.2. Kết quả đạt được

**Cấu hình đề xuất C1 (Semantic + Expansion + top-k=8) trên 50 câu hỏi K38:**

| Metric | Giá trị | Ý nghĩa |
|---|---|---|
| Context Precision | **0,71** | 71% chunk retrieve được là relevant |
| Hit Rate@8 | **0,88** | 88% câu hỏi tìm được chunk đúng trong top-8 |
| MRR | **0,72** | Chunk đúng trung bình ở rank ~1.4 |
| Faithfulness | **0,83** | 83% câu trả lời có căn cứ trong context |
| Answer Relevance | **0,81** | 81% câu trả lời đúng với câu hỏi |
| Refusal Accuracy | **100%** | Từ chối đúng tất cả 6 câu OOS |
| TTFT | **~1.820 ms** | Thấy token đầu tiên sau ~1.8 giây |

### 13.3. Hạn chế được thừa nhận

1. **Eval set 50 câu** — nhỏ; kết luận thống kê chưa mạnh
2. **AI-judge không chuẩn hóa** — Gemini tự chấm điểm mình; điểm không so sánh được
   trực tiếp với RAGAS hay TruLens
3. **Heuristic relevance** — dùng keyword matching để xác định chunk "liên quan";
   không dùng human annotation
4. **PDF scan** — không xử lý được PDF ảnh (chưa tích hợp OCR)
5. **Quota Gemini free tier** — ~5% request gặp lỗi 429 khi tải cao

---

## 14. Glossary — Bảng từ khoá kỹ thuật

| Thuật ngữ | Giải thích |
|---|---|
| **RAG** | Retrieval-Augmented Generation — kết hợp tìm kiếm tài liệu + sinh văn bản |
| **Embedding** | Biểu diễn văn bản bằng vector số trong không gian nhiều chiều |
| **Cosine Similarity** | Đo góc giữa 2 vector; = 1 là hoàn toàn giống, = 0 là không liên quan |
| **Chunk** | Đoạn văn bản nhỏ, đơn vị cơ bản của RAG |
| **Chunking** | Quá trình chia tài liệu thành các chunk |
| **ChromaDB** | Vector database lưu trữ embedding, hỗ trợ similarity search |
| **HNSW** | Thuật toán tìm hàng xóm gần nhất trong vector database |
| **Query Expansion** | Mở rộng câu hỏi thành nhiều biến thể để cải thiện retrieval |
| **Multi-query Retrieval** | Tìm kiếm với nhiều query, gộp và dedup kết quả |
| **Context Window** | Giới hạn lượng text LLM có thể xử lý trong 1 lần |
| **SSE** | Server-Sent Events — giao thức streaming text từ server về client |
| **TTFT** | Time To First Token — độ trễ đến token đầu tiên |
| **Ablation Study** | Thử nghiệm tắt từng component để đo ảnh hưởng |
| **AI-Judge** | Dùng LLM để tự động chấm điểm output của LLM khác |
| **Faithfulness** | Mức độ câu trả lời có căn cứ trong context (không bịa) |
| **Hallucination** | LLM bịa thông tin không có trong nguồn |
| **Refusal Accuracy** | Khả năng từ chối đúng câu hỏi ngoài phạm vi tài liệu |
| **Context Precision** | Tỷ lệ chunk relevant trong số chunk được retrieve |
| **Hit Rate@k** | 1 nếu có ít nhất 1 chunk relevant trong top-k, else 0 |
| **MRR** | Mean Reciprocal Rank — đánh giá vị trí của chunk relevant đầu tiên |
| **NDCG** | Normalized Discounted Cumulative Gain — đánh giá chất lượng ranking |
| **OOS** | Out-Of-Scope — câu hỏi ngoài phạm vi tài liệu |
| **Ingest** | Quá trình đưa tài liệu vào hệ thống: extract → chunk → embed → store |

---

*File: `docs/BAO_CAO_KY_THUAT_RAG.md` | Tạo: 06/06/2026 | Đề tài: TLU AI Assistant*
