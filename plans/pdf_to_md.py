import os
import re
from pathlib import Path
import pymupdf4llm

def fill_forward_markdown_tables(md_text):
    """
    Hàm hậu xử lý (Post-processing) đặc biệt cho bảng biểu Markdown:
    Tự động điền khuyết (Fill-forward) cho các ô gộp (Merged cells) bị trống.
    Áp dụng riêng cho các cột thường xuyên bị gộp như "Lịch" để giúp RAG hiểu đúng ngữ cảnh.
    """
    lines = md_text.split('\n')
    in_table = False
    header_indices_to_fill = []
    prev_values = {}
    
    new_lines = []
    
    for line in lines:
        stripped_line = line.strip()
        # Kiểm tra xem dòng có phải là một phần của bảng không (bắt đầu và kết thúc bằng |)
        if stripped_line.startswith('|') and stripped_line.endswith('|'):
            # Tách các cột, giữ nguyên khoảng trắng bên trong nhưng bỏ khoảng trắng thừa 2 bên
            cols = line.split('|')
            # Cột đầu và cuối sẽ là rỗng do split('|') với chuỗi bắt đầu/kết thúc bằng '|'
            
            if not in_table:
                # Bắt đầu bảng mới (dòng Header)
                in_table = True
                header_indices_to_fill = []
                prev_values = {}
                
                # Tìm index của các cột cần fill-forward
                for i, col in enumerate(cols):
                    clean_col = col.replace('*', '').replace('_', '').strip().lower()
                    # Điền danh sách các cột cần điền khuyết tự động tại đây:
                    if clean_col in ['lịch']: 
                        header_indices_to_fill.append(i)
                new_lines.append(line)
            else:
                # Kiểm tra dòng phân cách bảng (VD: |---|---|)
                is_separator = True
                for c in cols[1:-1]:
                    c_strip = c.strip()
                    if not (c_strip == '' or set(c_strip).issubset({'-', ':'})):
                        is_separator = False
                        break
                
                if is_separator:
                    new_lines.append(line)
                    continue
                
                # Kiểm tra dòng Section Header (VD: |**Học kỳ I...**|||||)
                # Dòng này thường có nội dung ở cột đầu tiên, và rỗng ở tất cả các cột tiếp theo
                cols_content = [c.strip() for c in cols[1:-1]]
                if len(cols_content) > 1:
                    is_section_header = (len(cols_content[0]) > 0) and all(len(c) == 0 for c in cols_content[1:])
                    if is_section_header:
                        # Gặp Header phụ (Học kỳ mới), reset lại bộ nhớ điền khuyết
                        prev_values = {}
                        new_lines.append(line)
                        continue
                
                # Dòng dữ liệu bình thường -> Thực hiện Fill-forward
                for i in header_indices_to_fill:
                    if i < len(cols):
                        c_strip = cols[i].strip()
                        if c_strip == '':
                            # Nếu ô hiện tại trống và có dữ liệu từ dòng trên -> Lấy xuống
                            if i in prev_values:
                                # Thêm khoảng trắng cho đẹp nếu cần, hoặc để nguyên format cũ
                                cols[i] = prev_values[i]
                        else:
                            # Cập nhật giá trị mới để fill cho các dòng sau
                            prev_values[i] = cols[i]
                            
                new_line = '|'.join(cols)
                new_lines.append(new_line)
        else:
            in_table = False
            new_lines.append(line)
            
    return '\n'.join(new_lines)


def convert_pdf_to_markdown(input_pdf, output_dir):
    """
    Chuyển đổi PDF sang Markdown bằng pymupdf4llm, tối ưu và siêu nhẹ cho Mac Intel.
    Kèm theo bộ lọc làm sạch và điền khuyết dữ liệu bảng.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"[*] Đang xử lý: {input_pdf} (Sử dụng pymupdf4llm + Fill-forward algorithm)")
    
    try:
        # Chuyển đổi PDF thành Markdown
        raw_md = pymupdf4llm.to_markdown(input_pdf)
        
        # Gọi hàm hậu xử lý bảng biểu để tối ưu cho RAG
        cleansed_md = fill_forward_markdown_tables(raw_md)
        
        file_name = Path(input_pdf).stem
        out_path = os.path.join(output_dir, f"{file_name}_pymupdf.md")
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(cleansed_md)
            
        print(f"[V] Xong! Kết quả tại: {out_path}")
        print("-> Đã áp dụng thuật toán Fill-forward (Điền khuyết ô gộp) cho các cột quan trọng (VD: Lịch).")
        
    except Exception as e:
        print(f"[X] Lỗi trong quá trình chuyển đổi: {e}")

if __name__ == "__main__":
    FILE_NAME = "guide_book_k38.pdf" 
    
    if not os.path.exists(FILE_NAME):
        print(f"[!] Không tìm thấy file {FILE_NAME} trong thư mục hiện tại.")
    else:
        convert_pdf_to_markdown(FILE_NAME, "output_md")
