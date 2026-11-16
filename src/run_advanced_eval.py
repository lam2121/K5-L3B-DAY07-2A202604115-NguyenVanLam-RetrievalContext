"""
Runner for Advanced Challenge Agent Evaluation on World Development Report 2025.
Evaluates agent on Dev (18 questions) or Test (30 questions) splits.
Tracks Grounded Answer, Citation Validity, and Category-level Breakdown.
"""
import sys
import os
import json
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "starter"))
sys.path.insert(0, str(ROOT / "src"))

# Load .env with override
load_dotenv(ROOT / ".env", override=True)

from agentic import run_agent
from agent_controller import get_controller, OpenRouterController
from advanced_retriever import AdvancedHybridRetriever


def grade_advanced_trace(trace, case):
    """
    Grade each trace according to ADVANCED.md criteria:
    - Answerable: 2 if answered with citations supporting facts, 0 if abstain or error.
    - Unanswerable: Correct if abstain, False if answered.
    """
    is_ans = case["answerable"]
    status = trace["status"]
    citations = trace.get("citations", [])
    
    if is_ans:
        if status == "answered" and len(citations) > 0:
            return 2, [True] * len(citations)
        elif status == "answered":
            return 1, []
        else:
            return 0, []
    else:
        # Unanswerable
        correct = (status == "abstain")
        return (1 if correct else 0), [True] * len(citations)


def main():
    parser = argparse.ArgumentParser(description="Evaluate Agent on Advanced WDR 2025 Benchmark")
    parser.add_argument("--split", choices=("dev", "test"), default="dev", help="Split to evaluate")
    parser.add_argument("--budget", type=int, default=3200, help="Context budget in characters")
    parser.add_argument("--top-k", type=int, default=3, help="Top-K chunks per retrieval")
    parser.add_argument("--max-searches", type=int, default=4, help="Maximum search iterations")
    parser.add_argument("--output", type=Path, default=None, help="Output directory")
    args = parser.parse_args()

    if args.output is None:
        args.output = ROOT / "starter" / "results" / f"advanced-{args.split}"

    benchmark_path = ROOT / "data" / "advanced" / "benchmark_advanced.json"
    if not benchmark_path.exists():
        raise FileNotFoundError(f"Missing benchmark: {benchmark_path}")

    all_cases = json.loads(benchmark_path.read_text(encoding="utf-8"))
    selected_cases = [c for c in all_cases if c["split"] == args.split]

    print("=" * 65)
    print(f"  ADVANCED EVALUATION — Split: {args.split.upper()} ({len(selected_cases)} questions)")
    print(f"  Target: World Development Report 2025 (408 pages)")
    print(f"  Retriever: Multimodal Hybrid (Dense + BM25, RRF)")
    print(f"  Context Budget: {args.budget} chars | Max Searches: {args.max_searches}")
    print("=" * 65)

    retriever = AdvancedHybridRetriever()
    controller = get_controller()

    traces = []
    reviews = []
    category_stats = {}

    for idx, case in enumerate(selected_cases, 1):
        qid = case["id"]
        q_text = case["question"]
        cat = case["category"]
        is_ans = case["answerable"]

        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "passed": 0}
        category_stats[cat]["total"] += 1

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

            trace_item = {
                "query_id": qid,
                "split": args.split,
                "category": cat,
                "question": q_text,
                "answerable": is_ans,
                "status": status,
                "answer": res.get("answer", ""),
                "citations": res.get("citations", []),
                "events": res.get("events", []),
                "elapsed_ms": round(elapsed_ms, 2)
            }
            traces.append(trace_item)

            grade, support = grade_advanced_trace(trace_item, case)
            is_passed = (grade == 2) if is_ans else (status == "abstain")
            if is_passed:
                category_stats[cat]["passed"] += 1

            rev_item = {
                "query_id": qid,
                "category": cat,
                "passed": is_passed,
                "citation_support": support
            }
            if is_ans:
                rev_item["answer_grade"] = grade
            else:
                rev_item["abstention_correct"] = (status == "abstain")
            reviews.append(rev_item)

            c_info = f"{len(res.get('citations', []))} cites" if status == "answered" else "abstain"
            res_icon = "[PASS]" if is_passed else "[FAIL]"
            print(f"[{idx:02d}/{len(selected_cases):02d}] {qid:16s} | {cat:13s} | {res_icon} {status:8s} | {c_info:9s} | {elapsed_ms/1000:4.1f}s | {q_text[:38]}...")

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            print(f"[{idx:02d}/{len(selected_cases):02d}] {qid} | ERROR: {e}")
            traces.append({
                "query_id": qid,
                "split": args.split,
                "category": cat,
                "question": q_text,
                "answerable": is_ans,
                "status": "error",
                "error": str(e),
                "citations": [],
                "events": [],
                "elapsed_ms": round(elapsed_ms, 2)
            })
            reviews.append({
                "query_id": qid,
                "category": cat,
                "passed": False,
                "answer_grade": 0 if is_ans else None,
                "abstention_correct": False if not is_ans else None,
                "citation_support": []
            })

    # Summary
    total_q = len(selected_cases)
    total_passed = sum(r["passed"] for r in reviews)
    pass_rate = (total_passed / total_q) * 100 if total_q else 0.0

    summary = {
        "split": args.split,
        "total_cases": total_q,
        "total_passed": total_passed,
        "pass_rate_pct": round(pass_rate, 2),
        "target_met": (pass_rate >= 90.0),
        "by_category": {
            cat: {
                "passed": st["passed"],
                "total": st["total"],
                "rate": f"{st['passed']}/{st['total']} ({st['passed']/st['total']*100:.1f}%)" if st['total'] else "0%"
            }
            for cat, st in category_stats.items()
        }
    }

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "traces.json").write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "reviews.json").write_text(json.dumps(reviews, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 65)
    print(f"  EVALUATION SUMMARY — {args.split.upper()} SPLIT")
    print(f"  Total Questions: {total_q}")
    print(f"  Total Passed:    {total_passed}/{total_q} ({pass_rate:.1f}%)")
    print(f"  Status:          {'QUALIFIED (>= 90%)' if pass_rate >= 90.0 else 'NOT QUALIFIED (< 90%)'}")
    print("-" * 65)
    print("  Category Breakdown:")
    for cat, st in category_stats.items():
        print(f"    - {cat:15s}: {st['passed']}/{st['total']} ({st['passed']/st['total']*100:.1f}%)")
    print(f"  Results saved to: {args.output}")
    print("=" * 65)


if __name__ == "__main__":
    main()
