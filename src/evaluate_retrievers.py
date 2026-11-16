"""Benchmark retrieval methods on Dev/Test splits according to Day 7 rubrics."""
import argparse
import json
import statistics
import time
from pathlib import Path
import sys

# Add starter and src to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'starter'))
sys.path.insert(0, str(ROOT / 'src'))

from baseline import hit, pack_context
from retrievers import DenseRetriever, LexicalRetriever, HybridRetriever, RerankRetriever


def evaluate_method(retriever, questions, budget=800, top_k=3, strategy_name="unknown"):
    traces = []
    for q in questions:
        start = time.perf_counter()
        filters = q.get('filter')
        results = retriever.search(q['question'], filters=filters, top_k=top_k)
        context, ids = pack_context(results, budget=budget)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        marked = [{**c, 'hit': hit(c, q['gold'])} for c in results]
        h1 = bool(marked and marked[0]['hit'])
        h3 = any(c['hit'] for c in marked[:3])
        c_hit = any(c['hit'] and c['id'] in ids for c in marked)

        traces.append({
            'query_id': q['id'],
            'split': q['split'],
            'question': q['question'],
            'strategy': strategy_name,
            'top_k': top_k,
            'budget_chars': budget,
            'gold': q['gold'],
            'results': marked,
            'context': context,
            'context_ids': ids,
            'context_chars': len(context),
            'elapsed_ms': elapsed_ms,
            'hit1': h1,
            'hit3': h3,
            'context_hit': c_hit
        })
    return traces


def summarize_traces(traces, strategy_name, split):
    n = len(traces)
    h1 = sum(t['hit1'] for t in traces)
    h3 = sum(t['hit3'] for t in traces)
    c_hit = sum(t['context_hit'] for t in traces)
    avg_chars = statistics.mean(t['context_chars'] for t in traces) if traces else 0
    med_ms = statistics.median(t['elapsed_ms'] for t in traces) if traces else 0

    return {
        'strategy': strategy_name,
        'split': split,
        'n': n,
        'hit1': h1,
        'hit1_rate': f"{h1}/{n} ({h1/n*100:.1f}%)" if n else "0%",
        'hit3': h3,
        'hit3_rate': f"{h3}/{n} ({h3/n*100:.1f}%)" if n else "0%",
        'context_hit': c_hit,
        'context_hit_rate': f"{c_hit}/{n} ({c_hit/n*100:.1f}%)" if n else "0%",
        'avg_context_chars': round(avg_chars, 1),
        'median_ms': round(med_ms, 2),
        'service_cost_usd': 0.0
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', choices=('dev', 'test', 'all'), default='dev')
    parser.add_argument('--budget', type=int, default=800)
    args = parser.parse_args()

    data_dir = ROOT / 'data' / 'converted'
    chunks = json.loads((data_dir / 'chunks.json').read_text(encoding='utf-8'))
    all_questions = json.loads((data_dir / 'questions.json').read_text(encoding='utf-8'))
    emb_path = data_dir / 'chunk_embeddings.json'
    q_emb_path = data_dir / 'query_embeddings.json'

    splits_to_run = ['dev', 'test'] if args.split == 'all' else [args.split]

    print(f"Initializing retrievers for {len(chunks)} chunks...")
    lexical = LexicalRetriever(chunks)
    dense = DenseRetriever(chunks, emb_path, query_cache_path=q_emb_path)
    hybrid = HybridRetriever(dense, lexical)
    rerank = RerankRetriever(dense, lexical_retriever=lexical, candidate_k=15)

    methods = [
        ("TF-IDF/BM25 (Lexical)", lexical),
        ("Dense (all-MiniLM-L6-v2)", dense),
        ("Hybrid RRF (Dense + BM25)", hybrid),
        ("Retrieval + Rerank (Dense + Cross-Score)", rerank),
    ]

    all_summaries = []

    for split in splits_to_run:
        questions = [q for q in all_questions if q['split'] == split]
        print(f"\n================ Running on {split.upper()} ({len(questions)} questions) ================")
        
        for name, retriever in methods:
            traces = evaluate_method(retriever, questions, budget=args.budget, top_k=3, strategy_name=name)
            summary = summarize_traces(traces, name, split)
            all_summaries.append(summary)

            out_dir = ROOT / 'starter' / 'results' / f"{split}-{name.lower().replace(' ', '_').replace('/', '_').replace('+', '_')}"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / 'traces.json').write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding='utf-8')
            (out_dir / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

            print(f"[{name}] Hit@1: {summary['hit1_rate']} | Hit@3: {summary['hit3_rate']} | ContextHit: {summary['context_hit_rate']} | Latency: {summary['median_ms']}ms")

    print("\n\n### BẢNG TỔNG HỢP HIỆU NĂNG RETRIEVAL (Báo cáo Day 7)")
    print("| Cấu hình | Phương pháp | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian | Chi phí |")
    print("|---|---|---|---|---|---|---|---|")
    for s in all_summaries:
        print(f"| {s['strategy']} | top_k=3, budget={args.budget} | {s['split']} | {s['hit1_rate']} | {s['hit3_rate']} | {s['context_hit_rate']} | {s['median_ms']}ms | ${s['service_cost_usd']} |")


if __name__ == '__main__':
    main()
