from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


# We'll use a small, fast model
MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_PATH = Path(__file__).resolve().parent / "data" / "fraud_knowledge_base.index"
METADATA_PATH = Path(__file__).resolve().parent / "data" / "fraud_knowledge_base_meta.json"

_model = None
_index = None
_metadata = []


def init_rag_engine() -> None:
    """Initialize the sentence transformer model and FAISS index."""
    global _model, _index, _metadata
    
    if not RAG_AVAILABLE:
        print("[RAG] Sentence-transformers or faiss not available. RAG disabled.")
        return

    print("[RAG] Initializing RAG Engine...")
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    if _model is None:
        # Load the model (downloads on first run if not cached)
        # Using CPU device explicitly for safety
        _model = SentenceTransformer(MODEL_NAME, device='cpu')
    
    if _index is None:
        if INDEX_PATH.exists() and METADATA_PATH.exists():
            print("[RAG] Loading existing FAISS index...")
            _index = faiss.read_index(str(INDEX_PATH))
            with open(METADATA_PATH, 'r') as f:
                _metadata = json.load(f)
        else:
            print("[RAG] Creating new FAISS index...")
            # 384 is the hidden dimension of all-MiniLM-L6-v2
            _index = faiss.IndexFlatL2(384)
            _metadata = []


def add_document_to_knowledge_base(text: str, doc_id: str, label: str = "approved") -> None:
    """
    Chunk the document text and add to the FAISS index.
    label can be 'approved' (legit pattern) or 'fraud' (known fraud pattern).
    """
    global _model, _index, _metadata
    
    if not RAG_AVAILABLE or _model is None or _index is None:
        init_rag_engine()
        if not RAG_AVAILABLE:
            return

    # Simple chunking by paragraph or double newline
    chunks = [c.strip() for c in text.split('\n\n') if len(c.strip()) > 20]
    
    if not chunks:
        return
        
    embeddings = _model.encode(chunks, convert_to_numpy=True)
    
    _index.add(embeddings)
    
    for i, chunk in enumerate(chunks):
        _metadata.append({
            "doc_id": doc_id,
            "label": label,
            "chunk_id": i,
            "text": chunk
        })
        
    # Save index and metadata
    faiss.write_index(_index, str(INDEX_PATH))
    with open(METADATA_PATH, 'w') as f:
        json.dump(_metadata, f)


def analyze_with_rag(text: str) -> list[dict[str, Any]]:
    """
    Compare current document text against the knowledge base.
    Returns a list of fraud signals if anomalies are detected compared to known good patterns.
    """
    global _model, _index, _metadata
    
    if not RAG_AVAILABLE:
        return []
        
    if _model is None or _index is None:
        init_rag_engine()
        
    if _index is None or _index.ntotal == 0:
        # No history yet
        return []

    signals = []
    
    # Query with the whole text (or top chunks)
    query_embedding = _model.encode([text[:1000]], convert_to_numpy=True)
    
    # Search for top 5 nearest neighbors
    D, I = _index.search(query_embedding, 5)
    
    # If the distances are very large, it means this document is highly anomalous 
    # compared to anything we've ever seen (especially approved docs)
    # The L2 distance threshold depends on the model. For MiniLM, > 1.5 is quite far.
    
    avg_distance = np.mean(D[0])
    
    if avg_distance > 1.2:
        signals.append({
            "id": "rag-structural-anomaly",
            "name": "Unprecedented Document Structure",
            "severity": "medium",
            "summary": "Document structure deviates significantly from known valid templates",
            "description": "RAG vector analysis indicates this document does not match the structural embeddings of any previously approved financial documents in the knowledge base.",
            "evidence": [f"High vector distance from known templates (score: {avg_distance:.2f})"],
            "confidence": 0.85,
            "weight": 20,
        })
        
    return signals
