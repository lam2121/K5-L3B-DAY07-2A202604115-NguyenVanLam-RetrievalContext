"""
Multimodal Advanced Retriever for World Development Report 2025.
Combines Dense Semantic Search (all-MiniLM-L6-v2) and Lexical Search (BM25)
with Reciprocal Rank Fusion (RRF, k=60).
"""
import sys
import json
import math
import re
from pathlib import Path

# Add Day 6 site-packages for sentence-transformers
day6_site_packages = Path(r"E:\Projects\Lab6Vinuni\K5-L3B-DAY06-NguyenVanLam-2A202604115-DataIngestion\starter\.venv\Lib\site-packages")
if day6_site_packages.exists() and str(day6_site_packages) not in sys.path:
    sys.path.insert(0, str(day6_site_packages))

import numpy as np
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = ROOT / "data" / "advanced" / "processed" / "chunks_advanced.json"
EMBS_PATH = ROOT / "data" / "advanced" / "processed" / "chunk_embeddings_advanced.json"


def tokenize(text):
    return re.findall(r"\w+", text.lower())


class AdvancedHybridRetriever:
    def __init__(self, chunks_path=CHUNKS_PATH, embs_path=EMBS_PATH):
        print("[AdvancedRetriever] Loading chunks and embeddings...")
        self.chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        self.chunk_by_id = {c["id"]: c for c in self.chunks}
        
        # Load Dense embeddings matrix
        embs_dict = json.loads(embs_path.read_text(encoding="utf-8"))
        self.ordered_ids = [c["id"] for c in self.chunks]
        self.matrix = np.array([embs_dict[cid] for cid in self.ordered_ids], dtype=np.float32)
        # Normalize
        norms = np.linalg.norm(self.matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.matrix = self.matrix / norms
        
        # Initialize BM25
        print("[AdvancedRetriever] Building BM25 index...")
        corpus = [tokenize(c["text"]) for c in self.chunks]
        self.bm25 = BM25Okapi(corpus)
        
        # Load SentenceTransformer for queries
        print("[AdvancedRetriever] Loading SentenceTransformer for dynamic query encoding...")
        from sentence_transformers import SentenceTransformer
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
        print(f"[AdvancedRetriever] Ready! Indexed {len(self.chunks)} chunks.")

    def search_dense(self, query, top_k=20):
        q_emb = self.embedder.encode(query, normalize_embeddings=True)
        scores = np.dot(self.matrix, q_emb)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(self.ordered_ids[idx], float(scores[idx])) for idx in top_indices]

    def search_bm25(self, query, top_k=20):
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(self.ordered_ids[idx], float(scores[idx])) for idx in top_indices if scores[idx] > 0]

    def search(self, query, filters=None, top_k=5, k_rrf=60):
        # 1. Dense candidates
        dense_res = self.search_dense(query, top_k=25)
        # 2. BM25 candidates
        bm25_res = self.search_bm25(query, top_k=25)
        
        # RRF Scoring
        rrf_scores = {}
        for rank, (cid, _) in enumerate(dense_res):
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k_rrf + rank + 1))
            
        for rank, (cid, _) in enumerate(bm25_res):
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k_rrf + rank + 1))
            
        # Boost exact Figure/Table/Box/Map entity mentions in query
        explicit_matches = re.findall(r"(figure|table|box|map)\s+([a-z0-9\._]+)", query, re.IGNORECASE)
        for mtype, mnum in explicit_matches:
            target_sub = f"{mtype.lower()}-{mnum.replace('.', '_')}"
            for cid in self.ordered_ids:
                if target_sub in cid.lower():
                    rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 0.1
                    
        sorted_cids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        results = []
        for cid in sorted_cids:
            chunk = self.chunk_by_id[cid]
            if filters and filters.get("chunk_type"):
                if chunk["chunk_type"] != filters["chunk_type"]:
                    continue
            results.append({
                **chunk,
                "source": chunk.get("source", chunk.get("source_id", "World_Development_Report_2025.pdf")),
                "score": round(rrf_scores[cid], 5)
            })
            if len(results) >= top_k:
                break
                
        return results


if __name__ == "__main__":
    retriever = AdvancedHybridRetriever()
    test_q = "How many boiler explosions in Germany Table 1.1?"
    print(f"\nTest Query: {test_q}")
    res = retriever.search(test_q, top_k=3)
    for idx, r in enumerate(res, 1):
        print(f"[{idx}] {r['id']} (Page {r['page']}, Type: {r['chunk_type']}, Score: {r['score']})")
        print("   ", r["text"][:120].replace("\n", " "))
