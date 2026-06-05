# Chiến lược RAG Tối ưu cho Tài liệu Markdown (TLU AI Assistant)

## 1. Mục tiêu và Thách thức
**Mục tiêu:**
- Đảm bảo trích xuất dữ liệu chính xác từ file Markdown (`.md`) - đặc biệt là sổ tay sinh viên chứa nhiều bảng biểu, danh sách, và quy định.
- Không làm "cắt vụn" (fragment) ngữ cảnh của các câu văn, điều luật hay bảng biểu.
- Tiết kiệm dung lượng lưu trữ vector (Vector DB) và token khi gửi lên LLM (Gemini), giúp giải bài toán chi phí (nhẹ và tiết kiệm cho trường).

**Thách thức với phương pháp cắt độ dài cố định (Sliding Window / Fixed-size Chunking):**
Nếu chỉ cắt mỗi 1000 ký tự (như cách truyền thống), hệ thống sẽ gặp lỗi:
- **Cắt ngang bảng biểu:** Một bảng lịch học hoặc học phí bị cắt đôi khiến LLM không hiểu được cấu trúc cột/hàng.
- **Mất ngữ cảnh:** Đoạn text ở chunk 2 bị mất tiêu đề của chunk 1, LLM không biết đoạn text đó thuộc "Phòng Đào tạo" hay "Phòng Tài chính".

---

## 2. Giải pháp: Semantic Markdown Chunking (Phân mảnh theo Ngữ nghĩa)

Để giải quyết, chúng ta sử dụng chiến lược **Nhận thức cấu trúc Markdown (Markdown-Aware Chunking)**:

### 2.1. Phân tách theo Tiêu đề (Heading-Based Chunking)
Thay vì đếm số ký tự, hệ thống sẽ dò các thẻ Heading của Markdown (`#`, `##`, `###`) làm mốc để chia nhỏ (chunk).
- Mỗi mục (Section) sẽ là một Chunk độc lập. 
- *Ví dụ:* Toàn bộ nội dung dưới `## 3. PHÒNG ĐÀO TẠO` cho đến `## 4. PHÒNG TÀI CHÍNH – KẾ TOÁN` sẽ được đóng gói thành 1 chunk duy nhất. Điều này giữ trọn vẹn 100% ngữ cảnh của một phòng ban.

### 2.2. Kế thừa Ngữ cảnh Cha - Con (Context Enrichment)
Khi một mục con được tách ra, nó phải mang theo Tiêu đề của mục cha để không bị lạc lỏng.
- *Ví dụ:* Chuỗi nội dung sẽ được gộp thành: `[CÁC ĐỊA CHỈ SINH VIÊN CẦN LIÊN HỆ > PHÒNG ĐÀO TẠO]: Giải quyết các vấn đề có liên quan...`
- *Lợi ích:* Khi sinh viên hỏi "Đăng ký học ở đâu?", LLM tìm thấy chunk này và biết chắc chắn nó thuộc "Phòng Đào tạo".

### 2.3. Bảo toàn Bảng biểu và Danh sách (Table & List Preservation)
Trong sổ tay sinh viên có các bảng "Kế hoạch đào tạo năm học". 
- Thuật toán Chunking phải ưu tiên **KHÔNG BAO GIỜ** cắt ngang một block `|---|---|` (Table) hoặc các gạch đầu dòng `-` liên tiếp nhau. 
- Toàn bộ 1 bảng (dù có thể lên tới 1500 ký tự) vẫn sẽ được ép vào cùng 1 chunk để đảm bảo LLM hiểu được logic hàng/cột.

### 2.4. Chia nhỏ dự phòng (Fallback Sliding Window)
Chỉ áp dụng với các khối văn bản (Section) quá dài (ví dụ vượt quá 2000 ký tự). Khi đó, ta mới dùng phương pháp cắt ký tự + Overlap (chồng chéo 200 ký tự) ở giữa các đoạn văn (Paragraph), tuyệt đối không cắt giữa một câu.

---

## 3. Cấu trúc Metadata lưu trữ trong Vector Database (SQLite/Chroma)

Mỗi Chunk khi lưu vào CSDL Vector sẽ không chỉ có `text` và `embedding`, mà kèm theo:
- `doc_id`: ID của tài liệu.
- `heading_path`: Đường dẫn ngữ cảnh (VD: `Chương 1 > Điều 2 > Khoản 3`).
- `chunk_type`: Loại dữ liệu (`text`, `table`, `list`).

---

## 4. Tóm tắt lợi ích (Báo cáo Nhà trường)
1. **Tiết kiệm tài nguyên:** Thay vì tạo ra hàng ngàn vector rác bị cắt vụn, hệ thống tạo ra ít vector hơn nhưng "chất" hơn. Tiết kiệm dung lượng bộ nhớ trên thiết bị di động của sinh viên (Local SQLite).
2. **Tiết kiệm chi phí API:** Việc giữ nguyên ngữ cảnh giúp truy xuất đúng và trúng ngay lần đầu. Tránh việc phải nhồi nhét quá nhiều chunk dư thừa vào Prompt của LLM, giúp giảm thiểu số lượng Input Tokens.
3. **Độ chính xác cao:** Giải quyết triệt để lỗi AI trả lời sai lịch học, sai quy định do đọc bảng biểu bị thiếu dòng/thiếu cột. Sinh viên sẽ nhận được câu trả lời chính xác, kèm nguồn (Source) trỏ đúng đến chương/mục nào trong cẩm nang.
