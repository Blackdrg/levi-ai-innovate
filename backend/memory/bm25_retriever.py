import math
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class BM25Retriever:
    """
    Sovereign v11.0: Lite BM25 Keyword Retriever.
    Provides high-precision keyword matching to complement semantic vector search.
    Used in Phase 4 Hybrid Retrieval.
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def compute_bm25_scores(self, query: str, documents: List[Dict[str, Any]], text_field: str = "fact") -> List[Dict[str, Any]]:
        """
        Calculates BM25 scores for a list of documents relative to a query.
        Documents should be a list of dicts with at least the text_field.
        """
        if not documents: return []
        
        # 1. Preprocessing
        query_words = query.lower().split()
        corpus = [doc.get(text_field, "").lower().split() for doc in documents]
        corpus_size = len(corpus)
        avg_doc_len = sum(len(d) for d in corpus) / corpus_size
        
        # 2. IDF Calculation
        def get_idf(word: str):
            n_q = sum(1 for d in corpus if word in d)
            return math.log((corpus_size - n_q + 0.5) / (n_q + 0.5) + 1.0)

        # 3. Scoring
        scored_docs = []
        idfs = {word: get_idf(word) for word in query_words}
        
        for i, doc_words in enumerate(corpus):
            score = 0.0
            doc_len = len(doc_words)
            for word in query_words:
                tf = doc_words.count(word)
                idf = idfs[word]
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / avg_doc_len)
                score += idf * (numerator / denominator)
            
            # Update original document ref
            doc = documents[i].copy()
            doc["bm25_score"] = score
            scored_docs.append(doc)
            
        return sorted(scored_docs, key=lambda x: x["bm25_score"], reverse=True)

    @classmethod
    async def hybrid_merge(cls, vector_results: List[Dict[str, Any]], keyword_results: List[Dict[str, Any]], alpha: float = 0.7) -> List[Dict[str, Any]]:
        """
        Merges Vector and BM25 results using Reciprocal Rank Fusion (RRF) or Weighted Sum.
        Default: Weighted Sum of normalized scores.
        """
        # Normalize scores
        def normalize(results, score_field):
            if not results: return results
            max_s = max(r.get(score_field, 0) for r in results) or 1
            for r in results: r["norm_score"] = r.get(score_field, 0) / max_s
            return results

        vector_results = normalize(vector_results, "final_score")
        keyword_results = normalize(keyword_results, "bm25_score")
        
        # Merge by 'fact' or 'fact_id'
        merged = {}
        for r in vector_results:
            fid = r.get("fact_id", r.get("fact"))
            merged[fid] = r.copy()
            merged[fid]["hybrid_score"] = r["norm_score"] * alpha
            
        for r in keyword_results:
            fid = r.get("fact_id", r.get("fact"))
            if fid in merged:
                merged[fid]["hybrid_score"] += r["norm_score"] * (1 - alpha)
            else:
                merged[fid] = r.copy()
                merged[fid]["hybrid_score"] = r["norm_score"] * (1 - alpha)
                
        return sorted(merged.values(), key=lambda x: x["hybrid_score"], reverse=True)
