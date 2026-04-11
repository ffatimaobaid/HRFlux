import os
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from transformers import AutoTokenizer

# ChromaDB setup - lazy initialization
chroma_path = "chroma_storage"
embedding_func = None
client = None
tokenizer = None
_token_cache = {}

def _init_chromadb():
    """Lazy initialization of ChromaDB to avoid issues during import."""
    global client, embedding_func, tokenizer
    if client is None:
        try:
            embedding_func = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            client = chromadb.PersistentClient(path=chroma_path)
            tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
        except Exception as e:
            print(f"Warning: ChromaDB initialization failed: {e}")
            # Create a mock client for testing
            pass

def get_or_create_collection(name="hr_docs"):
    """Fetch or create a ChromaDB collection for HR documents."""
    _init_chromadb()
    if client is None:
        raise RuntimeError("ChromaDB client not initialized")
    return client.get_or_create_collection(name=name, embedding_function=embedding_func)

def add_document_chunks(doc_id, chunks, embeddings=None):
    """
    Add document chunks into ChromaDB.
    
    Args:
        doc_id (str): Unique document ID.
        chunks (List[str]): Text chunks to index.
        embeddings (List[List[float]], optional): Precomputed embeddings.
    """
    collection = get_or_create_collection()
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [{"doc_id": doc_id} for _ in chunks]

    try:
        if embeddings:
            collection.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
        else:
            collection.add(documents=chunks, ids=ids, metadatas=metadatas)
    except Exception as e:
        print(f"[❌] Error adding chunks for {doc_id}: {e}")

def delete_document_embeddings(doc_id):
    """
    Remove all chunks for a specific document ID from ChromaDB.
    
    Args:
        doc_id (str): Unique document identifier used when indexing.
    """
    collection = get_or_create_collection()
    try:
        all_data = collection.get()
        all_ids = all_data.get("ids", [])
        ids_to_delete = [doc for doc in all_ids if doc.startswith(f"{doc_id}_")]
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            print(f"[✅] Deleted {len(ids_to_delete)} chunks for {doc_id}")
        else:
            print(f"[ℹ️] No chunks found for document {doc_id}")
    except Exception as e:
        print(f"[❌] Error deleting document {doc_id}: {e}")

def search_context(query, top_k=8, doc_id=None):
    """
    Perform semantic search to retrieve top matching chunks for a query,
    optionally filtered by doc_id.
    
    Args:
        query (str): Natural language query.
        top_k (int): Number of results to return.
        doc_id (str, optional): If provided, filters results to this document ID.
    
    Returns:
        List[str]: Top matching document chunks.
    """
    collection = get_or_create_collection()
    try:
        if doc_id:
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
                where={"doc_id": doc_id}
            )
        else:
            results = collection.query(
                query_texts=[query],
                n_results=top_k
            )
        documents = results.get("documents", [])
        return documents[0] if documents and len(documents[0]) > 0 else []
    except Exception as e:
        print(f"[❌] Error during search for query '{query}': {e}")
        return []


def search_sources(query, top_k=3, doc_id=None):
    """Return top document IDs (sources) for a query for debugging/traceability."""
    collection = get_or_create_collection()
    try:
        filters = {"doc_id": doc_id} if doc_id else None
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where=filters,
            include=["metadatas"],
        )
        metadatas = results.get("metadatas", [])
        if not metadatas or not metadatas[0]:
            return []

        doc_ids = []
        for meta in metadatas[0]:
            d = meta.get("doc_id")
            if d and d not in doc_ids:
                doc_ids.append(d)
        return doc_ids
    except Exception as e:
        print(f"[❌] Error during source search for query '{query}': {e}")
        return []


def list_documents():
    """
    List all unique document IDs stored in ChromaDB.
    
    Returns:
        List[str]: Sorted list of document IDs.
    """
    collection = get_or_create_collection()
    try:
        all_data = collection.get(include=["metadatas"])
        doc_ids = set(meta.get("doc_id", "") for meta in all_data.get("metadatas", []) if "doc_id" in meta)
        return sorted(list(doc_ids))
    except Exception as e:
        print(f"[❌] Error listing documents: {e}")
        return []

def get_avg_tokens_per_chunk(chunks):
    """
    Compute the average number of tokens per chunk using a cached tokenizer.

    Args:
        chunks (List[str]): List of text chunks.

    Returns:
        float: Average number of tokens per chunk.
    """
    if not chunks:
        return 0

    _init_chromadb()
    if tokenizer is None:
        # Fallback: estimate tokens as ~4 characters per token
        return sum(len(chunk) / 4 for chunk in chunks) / len(chunks)

    total_tokens = 0
    for chunk in chunks:
        if chunk in _token_cache:
            total_tokens += _token_cache[chunk]
        else:
            tokens = tokenizer.encode(chunk, add_special_tokens=False)
            token_count = len(tokens)
            _token_cache[chunk] = token_count
            total_tokens += token_count

    return total_tokens / len(chunks)
