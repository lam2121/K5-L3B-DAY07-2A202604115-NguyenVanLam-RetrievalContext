"""Runner for Agentic RAG Evaluation on Dev/Test splits according to Day 7 rubrics."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

# Add project root and starter directory to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "starter"))
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

# Load environment variables from .env (override=True ensures any changes in .env are immediately applied)
load_dotenv(ROOT / ".env", override=True)

from agentic import run_agent
from agent_controller import OpenRouterController
from retrievers import DenseRetriever, LexicalRetriever, HybridRetriever, RerankRetriever


def get_embedder():
    """Load SentenceTransformer for dynamic query embeddings, leveraging Day 6 environment."""
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    day6_site_packages = Path("E:/Projects/Lab6Vinuni/K5-L3B-DAY06-NguyenVanLam-2A202604115-DataIngestion/starter/.venv/Lib/site-packages")
    if day6_site_packages.exists() and str(day6_site_packages) not in sys.path:
        sys.path.insert(0, str(day6_site_packages))
    try:
        from sentence_transformers import SentenceTransformer
        print("[INFO] Loading SentenceTransformer ('all-MiniLM-L6-v2') for dynamic query embedding...")
        return SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
    except Exception as e:
        print(f"[WARN] Could not load SentenceTransformer ({e}). Falling back to cached embeddings.")
        return None


def main():
    parser = argparse.ArgumentParser(description="Run AI Agent evaluation on Dev/Test benchmark questions.")
    parser.add_argument("--split", choices=("dev", "test"), default="dev", help="Benchmark split to evaluate (dev or test)")
    parser.add_argument("--budget", type=int, default=3200, help="Context character budget (default: 3200)")
    parser.add_argument("--top-k", type=int, default=3, help="Top-K chunks per retrieval (default: 3)")
    parser.add_argument("--max-searches", type=int, default=2, help="Maximum search tool calls per question (default: 2)")
    parser.add_argument("--retriever", choices=("dense", "hybrid", "bm25", "rerank"), default="dense", help="Retrieval strategy (default: dense)")
    parser.add_argument("--fallback-model", default=os.getenv("FALLBACK_LLM_MODEL", "meta-llama/llama-3.3-70b-instruct"), help="Fallback LLM model if primary is rate limited")
    parser.add_argument("--output", type=Path, default=ROOT / "starter" / "results" / "dev-agent", help="Output directory for traces")
    args = parser.parse_args()

    # 1. Load data
    data_dir = ROOT / "data" / "converted"
    chunks_path = data_dir / "chunks.json"
    cases_path = data_dir / "agent_cases.json"
    chunk_embs_path = data_dir / "chunk_embeddings.json"
    query_embs_path = data_dir / "query_embeddings.json"

    if not chunks_path.exists() or not cases_path.exists():
        raise FileNotFoundError("Missing chunks.json or agent_cases.json. Run conversion first.")

    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    all_cases = json.loads(cases_path.read_text(encoding="utf-8"))
    selected_cases = [c for c in all_cases if c.get("split") == args.split]

    print(f"============================================================")
    print(f"  Day 7 Agentic RAG Evaluation — Split: {args.split.upper()} ({len(selected_cases)} cases)")
    print(f"  Retriever: {args.retriever.upper()} | Top-K: {args.top_k} | Budget: {args.budget} chars")
    print(f"============================================================")

    # 2. Initialize Retriever
    embedder = get_embedder()
    dense_retriever = DenseRetriever(chunks, chunk_embs_path, embedder=embedder, query_cache_path=query_embs_path)

    if args.retriever == "dense":
        retriever = dense_retriever
    elif args.retriever == "bm25":
        retriever = LexicalRetriever(chunks)
    elif args.retriever == "hybrid":
        lexical = LexicalRetriever(chunks)
        retriever = HybridRetriever(dense_retriever, lexical)
    elif args.retriever == "rerank":
        lexical = LexicalRetriever(chunks)
        retriever = RerankRetriever(dense_retriever, lexical_retriever=lexical, candidate_k=15)
    else:
        raise ValueError(f"Unknown retriever: {args.retriever}")

    # 3. Initialize Controller (reads OPENROUTER_API_KEY and LLM_MODEL from .env)
    llm_model = os.getenv("LLM_MODEL", "nvidia/nemotron-3.5-super-vl:free")
    controller = OpenRouterController(model=llm_model, fallback_model=args.fallback_model)

    # 4. Run Evaluation Loop
    traces = []
    answered_count = 0
    abstain_count = 0
    error_count = 0

    total = len(selected_cases)
    for idx, case in enumerate(selected_cases, start=1):
        qid = case["id"]
        q_text = case["question"]
        is_answerable = case.get("answerable", True)

        start_time = time.perf_counter()
        try:
            res = run_agent(
                q_text,
                controller,
                retriever,
                budget=args.budget,
                top_k=args.top_k,
                max_searches=args.max_searches
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            status = res["status"]

            if status == "answered":
                answered_count += 1
            elif status == "abstain":
                abstain_count += 1

            trace_item = {
                "query_id": qid,
                "split": args.split,
                "question": q_text,
                "answerable": is_answerable,
                "status": status,
                "answer": res.get("answer", ""),
                "citations": res.get("citations", []),
                "events": res.get("events", []),
                "elapsed_ms": round(elapsed_ms, 2)
            }
            traces.append(trace_item)

            c_info = f"{len(res.get('citations', []))} citations" if status == "answered" else "abstain"
            print(f"[{idx:02d}/{total:02d}] {qid} | Status: {status:8s} | {c_info:15s} | {elapsed_ms/1000:4.1f}s | {q_text[:45]}...")

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            error_count += 1
            print(f"[{idx:02d}/{total:02d}] {qid} | ERROR: {e}")
            traces.append({
                "query_id": qid,
                "split": args.split,
                "question": q_text,
                "answerable": is_answerable,
                "status": "error",
                "error": str(e),
                "citations": [],
                "events": [],
                "elapsed_ms": round(elapsed_ms, 2)
            })

    # 5. Save results
    args.output.mkdir(parents=True, exist_ok=True)
    traces_file = args.output / "traces.json"
    traces_file.write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n============================================================")
    print(f"  Hoàn thành đánh giá!")
    print(f"  - Tổng số câu: {total}")
    print(f"  - Answered:    {answered_count}")
    print(f"  - Abstain:     {abstain_count}")
    print(f"  - Errors:      {error_count}")
    print(f"  - File kết quả đã lưu: {traces_file}")
    print(f"============================================================")


if __name__ == "__main__":
    main()
