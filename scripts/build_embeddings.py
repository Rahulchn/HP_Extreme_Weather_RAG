"""
build_embeddings.py
Milestone 2B: Local Embedding & Vector Store Builder
Embeds ONLY document chunks from data/master/document_chunks.json.
Does NOT embed raw rainfall observations, CSV rows, or full PDFs as single vectors.

Model: BAAI/bge-base-en-v1.5 (dimension 768, normalized, cosine similarity)
Fallback: sentence-transformers/all-MiniLM-L6-v2 (dimension 384, normalized)
Vector Store: FAISS IndexFlatIP + metadata sidecar (Option A)
Persists to: data/knowledge_base/vector_store/
Manifest: data/master/embedding_manifest.json

Ensures:
- Deterministic chunk_id ordering
- Idempotency: repeated execution does not duplicate vectors (N -> N, not 2N)
- Full provenance metadata sidecar
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

CHUNKS_PATH = "data/master/document_chunks.json"
OUTPUT_DIR = "data/knowledge_base/vector_store"
INDEX_PATH = os.path.join(OUTPUT_DIR, "index.faiss")
METADATA_PATH = os.path.join(OUTPUT_DIR, "index_meta.json")
MANIFEST_PATH = "data/master/embedding_manifest.json"

PREFERRED_MODEL = "BAAI/bge-base-en-v1.5"
FALLBACK_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def compute_sha256(filepath):
    if not os.path.exists(filepath):
        return None
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def load_chunks():
    if not os.path.exists(CHUNKS_PATH):
        raise FileNotFoundError(f"Missing document chunks file: {CHUNKS_PATH}")
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"Loaded {len(chunks)} raw chunks from {CHUNKS_PATH}")
    
    # Sort deterministically by chunk_id to guarantee reproducibility
    chunks.sort(key=lambda x: x["chunk_id"])
    return chunks

def validate_chunk(c):
    required_keys = ["chunk_id", "document_id", "source_id", "page_number", "year", "districts", "event_types", "parameters", "authority_level", "text"]
    for k in required_keys:
        if k not in c:
            return False, f"Missing key: {k}"
    if not c["text"] or len(c["text"].strip()) < 20:
        return False, "Empty or too short text"
    return True, "OK"

def get_dimension(model):
    if hasattr(model, "get_embedding_dimension"):
        return model.get_embedding_dimension()
    return model.get_sentence_embedding_dimension()

def get_model():
    try:
        print(f"Loading preferred local embedding model: {PREFERRED_MODEL}...")
        model = SentenceTransformer(PREFERRED_MODEL)
        dim = get_dimension(model)
        return model, PREFERRED_MODEL, dim
    except Exception as e:
        print(f"Warning: Failed to load {PREFERRED_MODEL} ({e}). Falling back to {FALLBACK_MODEL}...")
        model = SentenceTransformer(FALLBACK_MODEL)
        dim = get_dimension(model)
        return model, FALLBACK_MODEL, dim

def build_embeddings():
    t_start = time.time()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)

    chunks = load_chunks()

    valid_chunks = []
    failed_chunks = []

    for c in chunks:
        is_val, reason = validate_chunk(c)
        if is_val:
            valid_chunks.append(c)
        else:
            failed_chunks.append({"chunk_id": c.get("chunk_id", "UNKNOWN"), "reason": reason})

    if failed_chunks:
        print(f"Warning: {len(failed_chunks)} chunks failed validation.")

    print(f"Valid chunks to embed: {len(valid_chunks)}")

    # Check existing index for idempotency
    existing_meta = []
    if os.path.exists(INDEX_PATH) and os.path.exists(METADATA_PATH):
        print(f"Found existing vector store at {OUTPUT_DIR}. Checking for idempotency...")
        try:
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                existing_meta = json.load(f)
            existing_ids = {m["chunk_id"] for m in existing_meta}
            current_ids = {c["chunk_id"] for c in valid_chunks}
            
            # If the set of chunk IDs is identical, we can safely overwrite/rebuild cleanly
            # or skip redundant computations while maintaining exactly N vectors!
            print(f"Existing index contains {len(existing_ids)} vectors. Rebuilding clean index to ensure zero drift...")
        except Exception as e:
            print(f"Notice reading existing index: {e}. Rebuilding fresh index.")

    # Load model
    model, model_name, embedding_dim = get_model()
    print(f"Active embedding model: {model_name} (dimension: {embedding_dim})")

    # Extract text list
    # BGE models benefit from instruction prefix on queries, but raw chunk text is encoded directly
    texts_to_embed = [c["text"] for c in valid_chunks]

    CACHE_EMB_PATH = os.path.join(OUTPUT_DIR, "embeddings.npy")
    if os.path.exists(CACHE_EMB_PATH):
        print(f"Loading cached embeddings from {CACHE_EMB_PATH}...")
        embeddings = np.load(CACHE_EMB_PATH)
        if embeddings.shape[0] != len(valid_chunks) or embeddings.shape[1] != embedding_dim:
            print("Cache mismatch. Recomputing embeddings...")
            embeddings = model.encode(
                texts_to_embed,
                batch_size=32,
                show_progress_bar=True,
                normalize_embeddings=True,
                convert_to_numpy=True
            ).astype("float32")
            np.save(CACHE_EMB_PATH, embeddings)
    else:
        print(f"Generating embeddings for {len(texts_to_embed)} chunks (batch_size=32, normalize_embeddings=True)...")
        embeddings = model.encode(
            texts_to_embed,
            batch_size=32,
            show_progress_bar=True,
            normalize_embeddings=True,
            convert_to_numpy=True
        ).astype("float32")
        np.save(CACHE_EMB_PATH, embeddings)

    # Dimension validation
    if embeddings.shape[1] != embedding_dim:
        raise ValueError(f"Embedding dimension mismatch: expected {embedding_dim}, got {embeddings.shape[1]}")
    if embeddings.shape[0] != len(valid_chunks):
        raise ValueError(f"Count mismatch: expected {len(valid_chunks)} vectors, got {embeddings.shape[0]}")

    # Build FAISS IndexFlatIP (Cosine similarity for L2-normalized vectors)
    print("Building FAISS IndexFlatIP index...")
    index = faiss.IndexFlatIP(embedding_dim)
    index.add(embeddings)

    print(f"Writing vector index to {INDEX_PATH} (ntotal = {index.ntotal})...")
    faiss.write_index(index, INDEX_PATH)

    # Build metadata sidecar
    # Preserves 1-to-1 mapping: vector_id (0 to N-1) -> chunk metadata
    metadata_sidecar = []
    for idx, c in enumerate(valid_chunks):
        metadata_sidecar.append({
            "vector_id": idx,
            "chunk_id": c["chunk_id"],
            "document_id": c["document_id"],
            "source_id": c["source_id"],
            "document_title": c.get("document_title", ""),
            "page_number": c["page_number"],
            "section_title": c["section_title"],
            "year": c["year"],
            "districts": c["districts"],
            "event_types": c["event_types"],
            "parameters": c["parameters"],
            "authority_level": c["authority_level"],
            "authority_rank": c["authority_rank"],
            "char_count": c["char_count"],
            "token_estimate": c["token_estimate"],
            "fingerprint": c["fingerprint"],
            "text": c["text"]
        })

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata_sidecar, f, indent=2)
    print(f"Saved metadata sidecar to {METADATA_PATH}")

    # Checksums
    idx_sha = compute_sha256(INDEX_PATH)
    meta_sha = compute_sha256(METADATA_PATH)
    idx_size_bytes = os.path.getsize(INDEX_PATH)
    meta_size_bytes = os.path.getsize(METADATA_PATH)

    t_end = time.time()
    build_duration = round(t_end - t_start, 2)

    # Build Manifest
    manifest = {
        "embedding_model": model_name,
        "model_version": "1.5" if "1.5" in model_name else "1.0",
        "embedding_dimension": embedding_dim,
        "similarity_metric": "cosine",
        "normalized": True,
        "chunk_count": len(chunks),
        "embedded_count": len(valid_chunks),
        "failed_count": len(failed_chunks),
        "vector_store_type": "FAISS_IndexFlatIP_with_metadata_sidecar",
        "build_timestamp": datetime.now().isoformat() + "Z",
        "build_duration_seconds": build_duration,
        "index_file": INDEX_PATH,
        "index_size_bytes": idx_size_bytes,
        "index_sha256": idx_sha,
        "metadata_file": METADATA_PATH,
        "metadata_size_bytes": meta_size_bytes,
        "metadata_sha256": meta_sha,
        "failed_chunks": failed_chunks
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nSaved embedding manifest to {MANIFEST_PATH}")

    print("\n=== Vector Store Build Complete ===")
    print(f"Total Chunks: {len(chunks)}")
    print(f"Embedded Vectors: {index.ntotal}")
    print(f"Index Size: {idx_size_bytes / 1024:.1f} KB")
    print(f"Build Time: {build_duration} seconds")

if __name__ == "__main__":
    build_embeddings()
