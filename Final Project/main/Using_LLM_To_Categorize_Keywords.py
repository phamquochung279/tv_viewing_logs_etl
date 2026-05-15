import pandas as pd
import threading
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from openai import OpenAI

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

def load_keywords(input_file):
    """Load keywords từ file CSV vào DataFrame 1 cột"""
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    # Phân tách header & data
    header = lines[0]
    data = lines[1:]

    # Tạo DataFrame 1 cột
    keywords = pd.DataFrame(data, columns=[header])
    return keywords

# Setup LLM model

client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
# print("=== Models available in LM Studio ===")
models = client.models.list()
# for idx, m in enumerate(models.data, 1):
#     print(f"{idx}. {m.id}")

# print(f"\nTổng số models: {len(models.data)}")

def classify_keywords_parallel(df, batch_size, file_name, max_workers=2):
    """Song song, lưu raw response vào file TXT, append nếu file đã tồn tại"""

    keywords_list = df['keyword'].tolist()
    batches = [keywords_list[i:i+batch_size] for i in range(0, len(keywords_list), batch_size)]
    
    print(f"Tổng số keywords: {len(keywords_list)}")
    print(f"Số batch: {len(batches)}")
    
    MODEL_ID = "qwen2.5-7b-instruct.gguf"
    file_path = PROJECT_DIR / f'{file_name}.txt'
    file_lock = threading.Lock()

    # Chế độ 'a' sẽ tự động append nếu file đã tồn tại, tạo mới nếu chưa có
    file_mode = 'a' if os.path.exists(file_path) else 'w'

    def process_one_batch(batch_data):
        batch_idx, batch_keywords = batch_data
        print(f"Processing batch {batch_idx + 1}/{len(batches)}")
        
        prompt = f"""
    Bạn là một chuyên gia phân loại nội dung phim, chương trình truyền hình và các loại nội dung giải trí.  
    Bạn sẽ nhận một danh sách tên có thể viết sai, viết liền không dấu, viết tắt, hoặc chỉ là cụm từ liên quan đến nội dung.

    Nhiệm vụ của bạn:
    1. **Chuẩn hoá tên**: thêm dấu tiếng Việt nếu cần, tách từ, chỉnh chính tả (vd: "thuyếtminh" → "Thuyết minh", "tramnamu" → "Trăm năm hữu duyên", "capdoi" → "Cặp đôi").
    2. **Nhận diện tên hoặc ý nghĩa gốc gần đúng nhất**. Bao gồm:
    - Tên phim, series, show, chương trình
    - Quốc gia / đội tuyển (→ "Sports" hoặc "News")
    - Từ khoá mô tả nội dung (→ phân loại theo ý nghĩa, ví dụ "thuyếtminh" → "Other" hoặc "Drama", "bigfoot" → "Horror")
    3. **Gán thể loại phù hợp nhất** trong các thể loại sau:  
    - Action  
    - Romance  
    - Comedy  
    - Horror  
    - Animation  
    - Drama  
    - C Drama  
    - K Drama  
    - Sports  
    - Music  
    - Reality Show  
    - TV Channel  
    - News

    ⚠️ Nguyên tắc quan trọng:
    - Luôn cố gắng sửa lỗi, nhận diện tên gần đúng hoặc đoán thể loại gần đúng.  
    - Nếu không chắc → chọn thể loại gần nhất (VD: từ mô tả tình cảm → Romance, tên địa danh thể thao → Sports, chương trình giải trí → Reality Show, v.v.)
    - KHÔNG tạo thêm thể loại ngoài danh sách cho phép.

    Một số quy tắc gợi ý nhanh:
    - Có từ “VTV”, “HTV”, “Channel” → TV Channel  
    - Có “running”, “master key”, “reality” → Reality Show  
    - Quốc gia, CLB bóng đá, sự kiện thể thao → Sports hoặc News  
    - “sex”, “romantic”, “love” → Romance  
    - “potter”, “hogwarts” → Drama / Fantasy  
    - Tên phim Việt/Trung/Hàn → ưu tiên Drama / C Drama / K Drama

    Chỉ trả về các dòng đúng format: Keyword ### Category.
    Keyword = tên gốc trong danh sách.  
    Category = thể loại đã phân loại.

    Ví dụ:  

    bigfoot ### Horror
    capdoi ### Romance
    ARGEN ### Sports
    nhật ký ### Drama
    PENT ### C Drama
    running ### Reality Show
    VTV3 ### TV Channel

    Danh sách:
    {batch_keywords}

    """
        try:
            resp = client.chat.completions.create(
                model=MODEL_ID,
                messages=[{"role":"user","content":prompt}],
                temperature=0.0,
                top_p=0.9,
                max_tokens=8192,
            )
            content = resp.choices[0].message.content.strip()
            print(f"Debug: Full raw response: {content}")
            # Lưu raw response vào file TXT
            with file_lock:
                with open(file_path, file_mode, encoding='utf-8') as f:
                    f.write(f"# Batch {batch_idx + 1}\n")
                    f.write(content + "\n\n")
            print(f"✅ Đã lưu batch {batch_idx + 1} vào TXT")
            return content
        except Exception as e:
            print(f"Error batch {batch_idx + 1}: {e}")
            return ""

    all_results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(process_one_batch, enumerate(batches))
        for batch_result in results:
            all_results.append(batch_result)
    
    print(f"\n✅ Hoàn thành! Đã lưu tất cả vào '{file_path}'")
    print(f"Tổng số batch đã lưu: {len(all_results)}")
    return all_results

if __name__ == "__main__":
    input_file = PROJECT_DIR / "distinct_most_searched_keywords" / "distinct_most_searched_keywords.csv"
    keywords = load_keywords(input_file)
    
    # Test với 10,000 dòng random
    # keywords_sample = keywords.sample(n=10000, random_state=1)
    # results_sample = classify_keywords_parallel(keywords_sample, batch_size=100, file_name='keywords_sample', max_workers=8)

    # Chạy full dataset
    results = classify_keywords_parallel(keywords, batch_size=100, file_name='distinct_most_searched_keywords_categorized', max_workers=4)

