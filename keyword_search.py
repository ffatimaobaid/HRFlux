# keyword_search.py
from db import get_all_chunks

def keyword_search(query, top_k=5):
    query_words = query.lower().split()
    results = []

    chunks = get_all_chunks()
    print(f"[keyword_search] Retrieved {len(chunks)} chunks from DB")
    print(f"[keyword_search] Query words: {query_words}")

    for chunk in chunks:  # should return [(text,), ...]
        text = chunk[0].lower()
        if any(word in text for word in query_words):
            results.append(chunk)

    print(f"[keyword_search] Found {len(results)} matching chunks")
    return results[:top_k]