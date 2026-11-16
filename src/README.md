# Source Code — Day 7 Retrieval & Context Engineering

Thư mục này chứa mã nguồn cài đặt và đánh giá toàn diện cho hệ thống Agentic RAG Day 7:

- **`agent_controller.py`**:
  - Tích hợp LLM Controller thực tế hỗ trợ đa nhà cung cấp: **Anthropic Direct API (mặc định model `claude-haiku-5-5`)**, Google Gemini API (`gemini-2.5-flash`), OpenRouter, Groq, và Ollama.
  - Hỗ trợ bóc tách khối suy luận mở rộng (`ThinkingBlock`) và trích xuất khối văn bản (`TextBlock`) từ Claude 5.5.
  - Chuẩn hóa đầu ra JSON và hàm `normalize_action()` đảm bảo 100% trích dẫn `[chunk-id]` khớp chính xác với ngữ cảnh tích lũy.
  - Cơ chế xử lý Rate Limit (HTTP 429) và lỗi mạng với exponential backoff.

- **`advanced_index.py`**:
  - Trích xuất cấu trúc và index đa phương thức toàn diện cho tài liệu *World Development Report 2025* (408 trang, 3.473 chunks).
  - Tự động bóc tách 49 bảng biểu Markdown, cắt ảnh 170 hình ảnh/biểu đồ kèm bounding box tọa độ pixel thực tế, vector hóa embedding 384 chiều (`all-MiniLM-L6-v2`).

- **`advanced_retriever.py`**:
  - Bộ truy xuất nâng cao kết hợp Reciprocal Rank Fusion (RRF, $k=60$) giữa Dense Cosine Similarity và BM25 Okapi.
  - Tích hợp cơ chế **Entity Mention Boosting** tự động tăng hạng cho các chunk có mã định danh thực thể (như `Figure 7.7`, `Table 4.2`, `Map 6.1`).

- **`run_advanced_eval.py`**:
  - CLI đánh giá toàn diện Agent trên bộ benchmark WDR 2025 (Dev 18 câu, Test 30 câu gồm Table, Diagram, Chart, Multi-hop, Text, Unanswerable).
  - Tự động chấm điểm, tính toán tỷ lệ đạt theo từng nhóm câu hỏi và xuất kết quả `summary.json`, `traces.json`, `reviews.json`.

- **`retrievers.py`**:
  - Cài đặt 4 phương pháp retrieval:
    1. `LexicalRetriever`: BM25 sử dụng thư viện `rank-bm25`.
    2. `DenseRetriever`: Tính cosine similarity từ embedding vector 384 chiều (`all-MiniLM-L6-v2`) kế thừa từ pgvector Day 6.
    3. `HybridRetriever`: Reciprocal Rank Fusion (RRF với $k=60$) kết hợp Rank của Dense và BM25.
    4. `RerankRetriever`: Pipeline 2 giai đoạn (Lấy top-15 ứng viên từ Dense, sau đó tính điểm hỗn hợp tổng hòa Cross-scoring giữa Dense + N-gram coverage + Proximity + BM25 để tái xếp hạng).

- **`evaluate_retrievers.py`**:
  - CLI đánh giá độc lập 4 phương pháp retrieval trên các tập Dev / Test với chỉ số: `Hit@1`, `Evidence Hit@3`, `Context Evidence Rate`, `MRR`, `Latency`.

- **`run_agent_eval.py`**:
  - CLI đánh giá toàn diện Agent trong vòng lặp tương tác (Multi-turn Agent Loop).
  - Hỗ trợ lựa chọn `--retriever dense|bm25|hybrid|rerank`, điều chỉnh `--budget` và `--max-searches`.
  - Tự động xuất kết quả `summary.json`, `traces.json`, và sinh sẵn `reviews.json` cho việc chấm điểm.

Xem hướng dẫn chạy chi tiết tại [README.md chính](../README.md).
