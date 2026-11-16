# Source Code — Day 7 Retrieval & Context Engineering

Thư mục này chứa mã nguồn cài đặt và đánh giá toàn diện cho hệ thống Agentic RAG Day 7:

- **`agent_controller.py`**:
  - Tích hợp LLM Controller thực tế qua OpenRouter API (mặc định model `meta-llama/llama-3.3-70b-instruct`, fallback: `nvidia/nemotron-3.5-super-vl:free`).
  - Ép chuẩn cấu trúc đầu ra JSON (`response_format={"type": "json_object"}`), parse action `search` hoặc `answer`.
  - Cơ chế xử lý Rate Limit (HTTP 429) và lỗi mạng với exponential backoff 3 lần (2s, 4s, 8s).

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
