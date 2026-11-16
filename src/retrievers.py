"""Retrieval methods for Day 7: Dense, Lexical (BM25/TF-IDF), and Hybrid RRF."""
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


def tokenize(text: str) -> list[str]:
    """Normalize and tokenize text into words."""
    return re.findall(r'\w+', unicodedata.normalize('NFC', text).casefold())


class DenseRetriever:
    """Dense vector retriever using cosine similarity over normalized embeddings."""

    def __init__(self, chunks: list[dict[str, Any]], embeddings_path: Path, embedder=None, query_cache_path: Path | None = None):
        self.chunks = chunks
        self.chunk_by_id = {c['id']: c for c in chunks}
        self.embedder = embedder
        
        # Load chunk embeddings
        raw_embs = json.loads(embeddings_path.read_text(encoding='utf-8'))
        self.chunk_ids = [c['id'] for c in chunks if c['id'] in raw_embs]
        self.vectors = [raw_embs[cid] for cid in self.chunk_ids]

        # Load query cache
        self.query_cache: dict[str, list[float]] = {}
        if query_cache_path and query_cache_path.exists():
            data = json.loads(query_cache_path.read_text(encoding='utf-8'))
            for qid, val in data.items():
                self.query_cache[val['question']] = val['embedding']
                self.query_cache[qid] = val['embedding']

    def encode_query(self, query: str) -> list[float]:
        if query in self.query_cache:
            return self.query_cache[query]
        if self.embedder is not None:
            emb = self.embedder.encode(query, normalize_embeddings=True).tolist()
            self.query_cache[query] = emb
            return emb
        raise ValueError(f"No embedding found for query: '{query}' and no dynamic embedder provided.")

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        q_vec = self.encode_query(query)
        scored = []
        for cid, vec in zip(self.chunk_ids, self.vectors):
            chunk = self.chunk_by_id[cid]
            if filters:
                # Apply metadata filter
                meta = chunk.get('metadata', {})
                match = True
                for k, v in filters.items():
                    if meta.get(k) != v and chunk.get(k) != v:
                        match = False
                        break
                if not match:
                    continue
            
            # Dot product for normalized vectors = cosine similarity
            sim = sum(a * b for a, b in zip(q_vec, vec))
            scored.append({**chunk, 'score': sim, 'strategy': 'dense'})

        scored.sort(key=lambda x: (-x['score'], x['id']))
        return scored[:top_k]


class LexicalRetriever:
    """BM25 Lexical retriever for keyword relevance."""

    def __init__(self, chunks: list[dict[str, Any]], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.corpus = [tokenize(c['text']) for c in chunks]
        self.doc_lens = [len(doc) for doc in self.corpus]
        self.avg_len = sum(self.doc_lens) / (len(self.doc_lens) or 1)
        
        # Document frequencies
        df = Counter()
        for doc in self.corpus:
            df.update(set(doc))
        self.N = len(chunks)
        # BM25 standard idf
        self.idf = {term: math.log((self.N - freq + 0.5) / (freq + 0.5) + 1.0) for term, freq in df.items()}

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        q_tokens = tokenize(query)
        q_counts = Counter(q_tokens)
        scored = []
        for i, (chunk, doc, doc_len) in enumerate(zip(self.chunks, self.corpus, self.doc_lens)):
            if filters:
                meta = chunk.get('metadata', {})
                match = True
                for k, v in filters.items():
                    if meta.get(k) != v and chunk.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            doc_counts = Counter(doc)
            score = 0.0
            for term, q_cnt in q_counts.items():
                if term not in doc_counts:
                    continue
                tf = doc_counts[term]
                idf = self.idf.get(term, 0.0)
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_len))
                term_score = idf * (tf * (self.k1 + 1.0)) / denom
                score += term_score

            if score > 0:
                scored.append({**chunk, 'score': score, 'strategy': 'bm25'})

        scored.sort(key=lambda x: (-x['score'], x['id']))
        return scored[:top_k]


class HybridRetriever:
    """Hybrid Retriever combining Dense and Lexical using Reciprocal Rank Fusion (RRF)."""

    def __init__(self, dense_retriever: DenseRetriever, lexical_retriever: LexicalRetriever, rrf_k: int = 60):
        self.dense = dense_retriever
        self.lexical = lexical_retriever
        self.rrf_k = rrf_k

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3, candidate_k: int = 20) -> list[dict[str, Any]]:
        dense_results = self.dense.search(query, filters=filters, top_k=candidate_k)
        lexical_results = self.lexical.search(query, filters=filters, top_k=candidate_k)

        rrf_scores: dict[str, float] = {}
        chunk_map: dict[str, dict[str, Any]] = {}

        for rank, item in enumerate(dense_results, start=1):
            cid = item['id']
            chunk_map[cid] = item
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank))

        for rank, item in enumerate(lexical_results, start=1):
            cid = item['id']
            if cid not in chunk_map:
                chunk_map[cid] = item
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank))

        merged = []
        for cid, score in rrf_scores.items():
            merged.append({**chunk_map[cid], 'score': score, 'strategy': 'hybrid_rrf'})

        merged.sort(key=lambda x: (-x['score'], x['id']))
        return merged[:top_k]


class RerankRetriever:
    """Two-Stage Retrieval + Reranking: Retrieves candidate chunks and rescores using lexical-semantic cross-scoring."""

    def __init__(self, base_retriever, lexical_retriever: LexicalRetriever | None = None, candidate_k: int = 15):
        self.base = base_retriever
        self.lexical = lexical_retriever
        self.candidate_k = candidate_k

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        # Stage 1: Candidate Generation
        candidates = self.base.search(query, filters=filters, top_k=self.candidate_k)
        if not candidates:
            return []

        # Stage 2: Cross-Scoring & Reranking
        q_tokens = tokenize(query)
        stopwords = {'what', 'is', 'the', 'and', 'to', 'in', 'of', 'for', 'are', 'a', 'an', 'how', 'does', 'according', 'chapter', 'which'}
        meaningful = {t for t in q_tokens if t not in stopwords and len(t) > 2} or set(q_tokens)
        
        base_scores = [c['score'] for c in candidates]
        max_b, min_b = max(base_scores), min(base_scores)
        range_b = max_b - min_b if max_b != min_b else 1.0

        reranked = []
        for c in candidates:
            doc_text = c['text'].lower()
            doc_tokens = set(tokenize(c['text']))
            
            # (a) Normalized base retrieval score [0, 1]
            norm_base = (c['score'] - min_b) / range_b
            
            # (b) Keyword coverage ratio
            coverage = sum(1 for t in meaningful if t in doc_tokens) / len(meaningful)
            
            # (c) Bigram phrase proximity
            bigram_matches = sum(1 for i in range(len(q_tokens) - 1) if f"{q_tokens[i]} {q_tokens[i+1]}" in doc_text)
            proximity = min(bigram_matches / 2.0, 1.0)
            
            # (d) Lexical BM25 component
            bm25_norm = 0.0
            if self.lexical is not None:
                q_counts = Counter(q_tokens)
                doc_tok_list = tokenize(c['text'])
                doc_len = len(doc_tok_list)
                doc_cnts = Counter(doc_tok_list)
                bm25_part = 0.0
                for t in q_counts:
                    if t in doc_cnts:
                        tf = doc_cnts[t]
                        idf = self.lexical.idf.get(t, 0.0)
                        denom = tf + self.lexical.k1 * (1.0 - self.lexical.b + self.lexical.b * (doc_len / self.lexical.avg_len))
                        bm25_part += idf * (tf * (self.lexical.k1 + 1.0)) / denom
                bm25_norm = min(bm25_part / 15.0, 1.0)

            # Composite rerank score
            final_score = 0.50 * norm_base + 0.25 * coverage + 0.15 * proximity + 0.10 * bm25_norm
            reranked.append({**c, 'score': final_score, 'strategy': 'retrieval_rerank'})

        reranked.sort(key=lambda x: (-x['score'], x['id']))
        return reranked[:top_k]

