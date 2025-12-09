from transformers import AutoTokenizer
from unstructured.partition.auto import partition
from unstructured.documents.elements import NarrativeText, Title

# Initialize tokenizer once
tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

MAX_TOKENS = 300
OVERLAP_TOKENS = 32  # New: overlap between chunks

def get_avg_tokens_per_chunk(texts):
    """
    Efficiently calculate average token count for a list of texts.
    """
    if not texts:
        return 0

    try:
        encodings = tokenizer.batch_encode_plus(
            texts, add_special_tokens=False, return_attention_mask=False
        )
        token_counts = [len(ids) for ids in encodings['input_ids']]
        avg_tokens = sum(token_counts) // len(token_counts)
        return avg_tokens
    except Exception as e:
        print(f"[Token Counting Error] {e}")
        return 0

def chunk_text_token_aware(text, max_tokens=MAX_TOKENS, overlap=OVERLAP_TOKENS):
    """
    Splits text into chunks using sentence boundaries while respecting token limits.
    Adds overlap between chunks for better context.
    """
    if not text:
        return []

    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    current_tokens = []

    for sentence in sentences:
        tentative_chunk = f"{current_chunk} {sentence}".strip() if current_chunk else sentence
        tokenized = tokenizer.encode(tentative_chunk, add_special_tokens=False)
        token_count = len(tokenized)

        if token_count <= max_tokens:
            current_chunk = tentative_chunk
            current_tokens = tokenized
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # Start new chunk with overlap
            if overlap > 0 and current_tokens:
                overlap_tokens = current_tokens[-overlap:]
                overlap_text = tokenizer.decode(overlap_tokens)
                current_chunk = overlap_text + " " + sentence
                current_tokens = tokenizer.encode(current_chunk, add_special_tokens=False)
            else:
                current_chunk = sentence
                current_tokens = tokenizer.encode(current_chunk, add_special_tokens=False)

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def hybrid_chunk_document(file_path, max_tokens=MAX_TOKENS, overlap=OVERLAP_TOKENS):
    """
    Hybrid chunking approach:
    - Uses 'unstructured' to extract semantically meaningful blocks (NarrativeText and Title)
    - Falls back to token-aware chunking for blocks exceeding token limit
    - Adds overlap between chunks
    """
    try:
        elements = partition(file_path)
        chunked_texts = []

        for el in elements:
            if isinstance(el, (NarrativeText, Title)):
                text = el.text.strip()
                if not text:
                    continue

                token_count = len(tokenizer.encode(text, add_special_tokens=False))

                if token_count > max_tokens:
                    chunked_texts.extend(chunk_text_token_aware(text, max_tokens, overlap))
                else:
                    chunked_texts.append(text)

        print(f" [Chunking] Document split into {len(chunked_texts)} chunks.")
        return chunked_texts

    except Exception as e:
        print(f" [Hybrid Chunking Error] {e}")
        return []
