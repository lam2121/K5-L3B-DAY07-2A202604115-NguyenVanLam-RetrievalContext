# Day 7 — Agentic RAG

**Bài cá nhân · Python 3.11+ · tiếp nối Day 6**

Dùng embedding và vector store từ Day 6 để xây một agent biết tìm bằng chứng, trả lời có nguồn và nhận biết khi không đủ thông tin. Bạn tự chọn kiến trúc, số tool và cách tổ chức retrieval.

> **Tùy chọn:** [Gợi ý dùng AI để lập trình](AGENT_SETUP.md) giúp bạn làm lab; phần này không bắt buộc và không tính điểm.

## Bài cần làm

![Agent tìm tài liệu trong kho Day 6 và trả lời có nguồn](assets/retrieval-pipeline.svg)

1. Kết nối dữ liệu, embedding và vector store Day 6.
2. Xây agent dùng model thật và ít nhất một khả năng truy xuất dữ liệu. Agent có thể dùng nhiều tool và nhiều lượt gọi.
3. Thử **ít nhất 3 phương pháp retrieval khác nhau**, trong đó có dense retrieval dùng vector store Day 6. Tự chọn các phương pháp còn lại; xem [gợi ý](GUIDE.md#2-thử-các-phương-pháp-retrieval).
4. Thử nhiều cấu hình, benchmark, phân tích lỗi và chọn cấu hình tốt trên **dev**; sau đó đánh giá trên **test**.

Benchmark tối thiểu có **24 câu**: dev gồm 15 câu có đáp án và 2 câu thiếu bằng chứng; test gồm 5 câu có đáp án và 2 câu thiếu bằng chứng. Xem [benchmark](BENCHMARK.md) và [rubric](RUBRIC.md).

## Thử thách nâng cao · +15 điểm

Index một tài liệu thực tế từ **100 trang** có bảng, ảnh và biểu đồ; xây agent truy xuất và trả lời các câu hỏi về nội dung đó. Hoàn thành [thử thách nâng cao](ADVANCED.md) và đạt **ít nhất 90% benchmark test** để nhận 15 điểm bonus. Phần cơ bản tối đa 85 điểm; toàn bài tối đa 100 điểm.

## Bắt đầu

1. Đọc [hướng dẫn](GUIDE.md), [rubric](RUBRIC.md) và [quy tắc](RULES.md).
2. Tạo repo cá nhân theo [cách nộp bài](SUBMISSION.md), chuẩn bị đầu ra Day 6 và model hỗ trợ tool calling.
3. Dùng hoặc thay thế [starter](starter/README.md); bạn cần kết nối model và vector store thật.
4. Chạy `python -m unittest discover -s tests -v`. Test mock chỉ kiểm tra code, không phải benchmark agent thật.

![Các bước thử nghiệm trên dev và đánh giá trên test](assets/experiment-loop.svg)

Nộp code, cách chạy, cấu hình, benchmark, trace và [báo cáo](report/individual/MSSV_HoTen.md). Thời gian ở [checkpoints](CHECKPOINTS.md) là gợi ý, có thể điều chỉnh theo lớp và phạm vi thử nghiệm.

---

## Hướng dẫn cài đặt & Chạy thực nghiệm (Reproduction Guide)

- **Sinh viên thực hiện:** Nguyễn Văn Lâm
- **MSSV:** 2A202604115
- **Lớp:** K5-L3B
- **Báo cáo cá nhân chi tiết:** [`report/individual/2A202604115_NguyenVanLam.md`](report/individual/2A202604115_NguyenVanLam.md)
- **Interactive Dashboard (Day 7):** [`benchmark_viewer.html`](benchmark_viewer.html)
- **Advanced Explorer (WDR 2025):** [`advanced_viewer.html`](advanced_viewer.html)

---

### 1. Chuẩn bị môi trường

Yêu cầu môi trường: **Python 3.11+**

```bash
# Tạo và kích hoạt môi trường ảo
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

Cấu hình API Key trong file `.env` (tạo từ `.env.example`):
```bash
cp .env.example .env
```
Điền `OPENROUTER_API_KEY=sk-or-v1-...` vào file `.env`.  
Hệ thống sử dụng LLM Controller thật kết nối OpenRouter với model chính `meta-llama/llama-3.3-70b-instruct` (kèm model dự phòng `nvidia/nemotron-3.5-super-vl:free` khi gặp sự cố mạng hoặc quota).

---

### 2. Chạy Unit Test kiểm tra toàn vẹn hệ thống

Chạy toàn bộ 15 test cases kiểm thử logic agent, trích dẫn hợp lệ, ngân sách context và rank metrics:
```bash
python -m unittest discover -s tests -v
```
*(Kết quả mong đợi: `Ran 15 tests in 0.103s ... OK`)*

---

### 3. Đánh giá Benchmark 4 phương pháp Retrieval

Đánh giá 4 phương pháp retrieval gồm **TF-IDF/BM25 (Lexical)**, **Dense (`all-MiniLM-L6-v2`)**, **Hybrid RRF ($k=60$)**, và **Two-Stage Retrieval + Cross-Scoring Rerank**:

```bash
# Đánh giá trên tập Dev (21 câu, budget=2400)
python src/evaluate_retrievers.py --split dev --budget 2400

# Đánh giá trên tập Test (8 câu, budget=2400)
python src/evaluate_retrievers.py --split test --budget 2400
```

Toàn bộ metrics (Hit@1, Hit@3, Context Evidence Rate, MRR, Latency) và file traces sẽ được tự động lưu vào:
- `starter/results/dev-tf-idf_bm25_(lexical)/` & `test-tf-idf_bm25_(lexical)/`
- `starter/results/dev-dense_(all-minilm-l6-v2)/` & `test-dense_(all-minilm-l6-v2)/`
- `starter/results/dev-hybrid_rrf_(dense___bm25)/` & `test-hybrid_rrf_(dense___bm25)/`
- `starter/results/dev-retrieval___rerank_(dense___cross-score)/` & `test-retrieval___rerank_(dense___cross-score)/`

---

### 4. Đánh giá Agent trên các cấu hình (LLM Controller)

#### A. Đánh giá trên tập Dev (21 câu):
```bash
# 1. Baseline Agent (Dense, budget=800, max_searches=2)
python src/run_agent_eval.py --split dev --config baseline --retriever dense --budget 800 --max-searches 2

# 2. Improved Dense Agent (Dense, budget=3200, max_searches=4)
python src/run_agent_eval.py --split dev --config improved --retriever dense --budget 3200 --max-searches 4

# 3. Lexical Agent (BM25, budget=3200, max_searches=4)
python src/run_agent_eval.py --split dev --config bm25 --retriever bm25 --budget 3200 --max-searches 4

# 4. Hybrid RRF Agent (Dense + BM25, budget=3200, max_searches=4)
python src/run_agent_eval.py --split dev --config hybrid --retriever hybrid --budget 3200 --max-searches 4

# 5. Rerank Agent (Dense + Cross-Score, budget=3200, max_searches=4)
python src/run_agent_eval.py --split dev --config rerank --retriever rerank --budget 3200 --max-searches 4
```

#### B. Đánh giá trên tập Test (8 câu):
```bash
# 1. Baseline Agent trên Test
python src/run_agent_eval.py --split test --config baseline --retriever dense --budget 800 --max-searches 2

# 2. Improved Dense Agent trên Test (Đạt 6/6 câu đúng tuyệt đối, 0% từ chối sai)
python src/run_agent_eval.py --split test --config improved --retriever dense --budget 3200 --max-searches 4

# 3. Lexical Agent trên Test
python src/run_agent_eval.py --split test --config bm25 --retriever bm25 --budget 3200 --max-searches 4

# 4. Hybrid RRF Agent trên Test
python src/run_agent_eval.py --split test --config hybrid --retriever hybrid --budget 3200 --max-searches 4

# 5. Rerank Agent trên Test (Đạt 6/6 câu đúng tuyệt đối, 0% từ chối sai)
python src/run_agent_eval.py --split test --config rerank --retriever rerank --budget 3200 --max-searches 4
```

---

### 5. Xem kết quả trực quan trên Interactive Dashboard

Mở trực tiếp file [`benchmark_viewer.html`](benchmark_viewer.html) bằng trình duyệt web bất kỳ:
- Bảng tổng hợp so sánh trực quan toàn diện giữa cả 4 phương pháp retrieval và 5 cấu hình Agent.
- Khả năng lọc câu hỏi theo: `All`, `Dev`, `Test`, `Answerable`, `Unanswerable`.
- Xem song song chi tiết từng câu: Query, Ground Truth Evidence và Top Chunks được truy xuất bởi từng phương pháp.
- **Trình chiếu trang PDF gốc tích hợp:** Render hình ảnh trang sách thực tế từ `results/pdf_pages/` với bounding box màu vàng phát sáng bao quanh đoạn bằng chứng chuẩn.
- Inspector xem chi tiết từng lượt tool call, reasoning thought, câu trả lời, độ trễ và chi phí của Agent.

---

### 6. Hướng dẫn chạy Thử thách Nâng cao (Advanced Challenge — WDR 2025)

Thử thách nâng cao sử dụng tài liệu thực tế **World Development Report 2025: Standards for Development** (408 trang, 3.473 chunks đa phương thức: văn bản, 49 bảng biểu, 170 hình ảnh/biểu đồ, 5 bản đồ) và hệ thống Agentic Multimodal RAG kết hợp Claude 5.5 Haiku, đạt **28/30 câu Test (93.3%)** $\ge 90\%$, đủ điều kiện đạt tối đa **15/15 điểm bonus**.

#### A. Cấu hình Model trong `.env`
Mở file `.env` tại thư mục gốc và cấu hình API key (hỗ trợ cả Anthropic Claude 5.5 Haiku trực tiếp hoặc Google Gemini):
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-haiku-5-5
```

#### B. Các lệnh thực thi Thử thách Nâng cao:
```bash
# 1. (Tùy chọn) Tái lập Index Multimodal từ file PDF gốc 408 trang
# Pipeline tự động phân tích layout, trích xuất bảng Markdown, cắt ảnh diagram/chart và sinh embedding:
python src/advanced_index.py

# 2. Chạy đánh giá trên tập Dev (18 câu — Đạt 94.4%):
python src/run_advanced_eval.py --split dev

# 3. Chạy đánh giá toàn diện trên tập Test (30 câu — Đạt 93.3% >= 90%):
python src/run_advanced_eval.py --split test

# 4. (Tùy chọn) Tái tạo lại giao diện HTML tương tác tra cứu dẫn chứng PDF:
python src/generate_advanced_viewer.py
```

#### C. Xem kết quả đánh giá và Trực quan hóa:
- **Dữ liệu Trace và Đánh giá chi tiết:**
  - Tập Dev: [`starter/results/advanced-dev/summary.json`](starter/results/advanced-dev/summary.json) & [`traces.json`](starter/results/advanced-dev/traces.json)
  - Tập Test: [`starter/results/advanced-test/summary.json`](starter/results/advanced-test/summary.json) & [`traces.json`](starter/results/advanced-test/traces.json)
- **Advanced Challenge Explorer:** Mở trực tiếp file [`advanced_viewer.html`](advanced_viewer.html) bằng trình duyệt web để:
  - Xem chi tiết 30 câu hỏi theo từng nhóm: *Table, Image/Diagram, Chart, Multi-hop, Text, Unanswerable*.
  - Kiểm tra execution trace, reasoning, prompt, thời gian và trích dẫn `[chunk-id]`.
  - **Trình chiếu trang PDF gốc đối chiếu:** Hiển thị trực quan trang PDF tương ứng với bounding box màu vàng phát sáng bao quanh đúng vùng dữ liệu trích dẫn của Agent và dữ liệu chuẩn, hỗ trợ tab chuyển đổi trang cho câu hỏi đa bước (multi-hop).
