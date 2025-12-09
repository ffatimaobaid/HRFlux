# Detailed Data Flow Process Analysis - HR Chatbot Project

## Table of Contents
1. [Overview](#overview)
2. [Document Ingestion Flow](#document-ingestion-flow)
3. [Query Processing Flow](#query-processing-flow)
4. [File-by-File Breakdown](#file-by-file-breakdown)
5. [Data Storage Architecture](#data-storage-architecture)
6. [Complete End-to-End Example](#complete-end-to-end-example)

---

## Overview

The HR Chatbot system uses a **Retrieval-Augmented Generation (RAG)** architecture with the following key components:

- **Frontend**: Streamlit web interface
- **LLM**: Google Gemini API
- **Vector Storage**: ChromaDB
- **Database**: SQLite (structured data)
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)

---

## Document Ingestion Flow

When an admin uploads a document, here's the complete flow:

### Step 1: Admin Upload (`admin_app.py`)

**File**: `admin_app.py` (Lines 42-61)
- Admin selects a file (PDF, DOCX, PPTX, HTML, EPUB)
- File is saved to `policy_docs/` directory
- Calls `ingest_document(file_path)` from `rag.py`

**Code Flow**:
```python
# admin_app.py line 58
chunks, avg_tokens, doc_id = ingest_document(file_path)
```

---

### Step 2: Document Text Extraction (`rag.py` → `embedder.py`)

**File**: `rag.py` (Lines 109-155)
- Detects file extension (`.pdf`, `.docx`, etc.)
- Routes to appropriate extractor in `embedder.py`

**For PDFs** (`rag.py` lines 114-118):
```python
from embedder import extract_text as extract_text_pdf
combined_text += extract_text_pdf(file_path)  # Uses unstructured library
combined_text += "\n\n" + extract_image_text(file_path)  # OCR + BLIP captions
```

**For other formats** (`rag.py` lines 120-134):
- DOCX → `extract_text_from_docx()` using `docx` library
- PPTX → `extract_text_from_pptx()` using `pptx` library
- HTML → `extract_text_from_html()` using `BeautifulSoup`
- EPUB → `extract_text_from_epub()` using `ebooklib`

**File**: `embedder.py` (Lines 15-39)
- Main extraction logic using `unstructured.partition.auto` library
- Normalizes text (removes extra whitespace)
- Handles multiple file formats

**Image Processing** (`rag.py` lines 42-80):
- Extracts images from PDFs using PyMuPDF
- Runs OCR using Tesseract
- Generates captions using BLIP model
- Combines OCR text + captions into searchable format

---

### Step 3: Document Chunking (`chunking.py`)

**File**: `chunking.py` (Lines 69-98)
- Uses `hybrid_chunk_document()` function
- Calls `partition()` from unstructured library
- Extracts `NarrativeText` and `Title` elements
- Checks token count for each element

**Token-Aware Chunking** (`chunking.py` lines 29-67):
- Maximum 300 tokens per chunk
- 32-token overlap between chunks for context continuity
- Splits on sentence boundaries
- Preserves semantic units

**Example**:
```python
# If block is too large (>300 tokens):
if token_count > max_tokens:
    chunked_texts.extend(chunk_text_token_aware(text, max_tokens, overlap))
else:
    chunked_texts.append(text)  # Keep as single chunk
```

---

### Step 4: Embedding Generation (`rag.py` → `embedder.py`)

**File**: `rag.py` (Lines 30-38)
- Creates parallel processing pool
- Calls `embed_chunks_parallel(chunks)` which uses multiprocessing
- Each worker re-imports the embedding model (multiprocessing safety)

**File**: `embedder.py` (Line 13)
- Loads `SentenceTransformer("all-MiniLM-L6-v2")` globally
- Converts each chunk to 384-dimensional vector

**Parallel Processing**:
```python
def embedding_worker(chunk):
    from embedder import model
    return model.encode([chunk])[0]  # Returns vector

with multiprocessing.Pool(processes=4) as pool:
    embeddings = pool.map(embedding_worker, chunks)
```

---

### Step 5: Vector Storage (`vector_store.py`)

**File**: `vector_store.py` (Lines 19-38)
- Generates unique IDs: `doc_id_0`, `doc_id_1`, etc.
- Stores in ChromaDB collection named "hr_docs"
- Metadata includes `doc_id` for filtering

**Code**:
```python
collection = get_or_create_collection()  # ChromaDB collection
ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
metadatas = [{"doc_id": doc_id} for _ in chunks]
collection.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
```

**Storage Locations**:
- **ChromaDB**: `chroma_storage/` directory (persistent)
- **SQLite**: `queries.db` (metadata only)

---

### Step 6: Metadata Storage (`db.py`)

**File**: `db.py` (Lines 77-83)
- Stores document metadata in SQLite `documents` table
- Records: `doc_id`, `filename`, `uploaded_at`, `avg_tokens`

**Also stores chunks** (`db.py` lines 103-113):
- Each chunk stored in `document_chunks` table
- Includes text and optional embedding blob
- Linked to doc_id

---

## Query Processing Flow

When a user asks a question, here's the complete flow:

### Step 1: User Input (`chat_app.py`)

**File**: `chat_app.py` (Lines 90-115)
- User types question in chat interface
- Gets recent context from last 24 hours

**Code**:
```python
# Line 97-100
context = get_recent_context(user)  # From context_cache.py
answer, suggestions = run_agent(user, question, model)
```

**Session Management**:
- Loads chat history from database (line 86)
- Maintains conversation in `st.session_state.chat_history`
- Cleans up old sessions >24 hours (line 33)

---

### Step 2: Agent Orchestration (`agent.py`)

**File**: `agent.py` (Lines 5-73)
- Main orchestrator for query processing
- Gets chat history for context

**Intent Classification** (Lines 9-29):
```python
intent_result = classify_and_extract_leave(question, model_name)
```

**Two Paths**:

#### Path A: Leave Request Detection
- If `is_leave_request == True`:
  - Extracts: `start_date`, `end_date`, `reason`, `leave_type`
  - Saves to `leave_requests` table (lines 18-21)
  - Returns confirmation message
  - **NO document retrieval needed**

#### Path B: Policy Question
- Calls `retrieve_context(question)` from `rag.py` (line 33)
- Gets document chunks related to query

**Context Retrieval** (Lines 32-34):
```python
if context_chunks is None:
    context_chunks = retrieve_context(question)
```

---

### Step 3: Hybrid Retrieval (`rag.py`)

**File**: `rag.py` (Lines 159-191)
- Implements **hybrid search** combining semantic + keyword

**A. Semantic Search** (Lines 165-169):
```python
dense_results = search_context(query, top_k=top_k)
```
- Calls `vector_store.py` → ChromaDB
- Finds semantically similar chunks using embeddings

**File**: `vector_store.py` (Lines 60-85):
- Converts query to embedding
- Searches ChromaDB collection using cosine similarity
- Returns top K results (default: 5)

**B. Keyword Search** (Lines 171-175):
```python
keyword_results = keyword_search(query, top_k=top_k)
```

**File**: `keyword_search.py` (Lines 4-18):
- Gets all chunks from SQLite `document_chunks` table
- Splits query into words
- Checks if any word appears in chunk text
- Returns matching chunks

**C. Merge & Deduplicate** (Lines 177-184):
```python
# Combine results
for r in dense_results + keyword_results:
    text = r[0] if isinstance(r, tuple) else r
    if text not in seen:
        combined.append(text)
        seen.add(text)
```

**Returns**: Top 5 unique chunks (removes duplicates)

---

### Step 4: LLM Response Generation (`gemini_llm.py`)

**File**: `gemini_llm.py` (Lines 52-130)
- Takes retrieved context chunks
- Builds conversation history string
- Creates prompt with:
  - System role (HR assistant)
  - Conversation history (last 5 exchanges)
  - Retrieved document context
  - User question

**Prompt Structure**:
```
You are a professional, helpful HR assistant.

Conversation History:
User: What is the leave policy?
Assistant: The leave policy allows...

HR Policy Document:
[Retrieved chunk 1]
[Retrieved chunk 2]

User Question: How do I apply for leave?

Answer:
```

**API Call** (`gemini_llm.py` lines 113-120):
```python
model = genai.GenerativeModel(model_name=model_name)
response = model.generate_content(
    prompt,
    generation_config={
        "temperature": 0.3,
        "max_output_tokens": 400
    }
)
return response.text.strip()
```

**Error Handling** (Lines 123-130):
- Handles API quota limits (429 errors)
- Falls back gracefully

---

### Step 5: Fallback & Suggestions

**File**: `agent.py` (Lines 35-70)

**If no context found** (Lines 35-42):
```python
if not context_chunks:
    answer = "Sorry, I couldn't find information..."
    similar = get_similar_questions(question, FAQ_QUESTIONS, top_n=3)
    return answer, similar
```

**If answer is too short or contains fallback phrases** (Lines 48-70):
```python
fallback_phrases = ["couldn't find", "no information", ...]
if any(phrase in answer_lower for phrase in fallback_phrases):
    similar = get_similar_questions(question, FAQ_QUESTIONS, top_n=3)
    return answer, similar
```

**Similarity Calculation** (`gemini_llm.py` lines 24-49):
- Uses embeddings to find similar FAQ questions
- Cosine similarity between query embedding and FAQ embeddings
- Returns top 3 most similar questions

---

### Step 6: Storage & UI Update

**File**: `chat_app.py` (Lines 107-114)
- Saves question/answer to database
- Updates context cache
- Displays response and suggestions

**Database Operations**:

1. **Logs Table** (`db.py` lines 125-130):
```python
save_log(user, question, answer)  # Saves to logs table
```

2. **Context Cache** (`context_cache.py` lines 22-27):
```python
add_to_cache(user, question, answer)  # For 24h context
```

3. **Chat History** (`chat_app.py` line 114):
```python
st.session_state.chat_history.append((question, answer, suggestions))
```

**UI Rendering** (`chat_app.py` lines 123-171):
- Displays chat messages
- Shows suggestion buttons if applicable
- Handles click events to set `pending_question`

---

## File-by-File Breakdown

### Core Application Files

#### 1. `chat_app.py` - Main User Interface
**Purpose**: Streamlit web interface for end users

**Key Functions**:
- `expand_query_with_synonyms()` - Query expansion
- Login/signup handling
- Chat history management
- Suggestion button handling

**Data Flow**:
1. Receives user input
2. Calls `run_agent()`
3. Saves to database + cache
4. Displays response with suggestions

**Dependencies**: `agent.py`, `db.py`, `context_cache.py`

---

#### 2. `agent.py` - Query Orchestrator
**Purpose**: Central coordinator for query processing

**Key Functions**:
- `run_agent()` - Main orchestration function
- Intent classification (leave vs policy)
- Context retrieval coordination
- Fallback handling

**Data Flow**:
1. Gets chat history from `db.py`
2. Classifies intent via Gemini
3. Retrieves context from `rag.py`
4. Generates answer via `gemini_llm.py`
5. Provides fallback suggestions

**Dependencies**: `rag.py`, `gemini_llm.py`, `db.py`

---

#### 3. `rag.py` - Retrieval System
**Purpose**: Document ingestion and retrieval

**Key Functions**:
- `ingest_document()` - Full ingestion pipeline
- `retrieve_context()` - Hybrid retrieval (semantic + keyword)
- `embed_chunks_parallel()` - Parallel embedding
- `extract_image_text()` - Image processing

**Data Flow**:
1. Extracts text from documents
2. Chunks document intelligently
3. Generates embeddings
4. Stores in ChromaDB + SQLite
5. Retrieves context for queries

**Dependencies**: `embedder.py`, `chunking.py`, `vector_store.py`, `keyword_search.py`

---

#### 4. `gemini_llm.py` - LLM Interface
**Purpose**: Google Gemini API integration

**Key Functions**:
- `query_gemini()` - Main LLM query function
- `classify_and_extract_leave()` - Intent classification
- `get_similar_questions()` - FAQ similarity search

**Data Flow**:
1. Builds prompt with context + history
2. Calls Gemini API
3. Returns generated text
4. Handles errors gracefully

**Dependencies**: `embedder.py` (for similarity search)

---

### Supporting Files

#### 5. `vector_store.py` - ChromaDB Interface
**Purpose**: Vector database operations

**Key Functions**:
- `get_or_create_collection()` - Collection management
- `add_document_chunks()` - Add embeddings
- `search_context()` - Semantic search
- `delete_document_embeddings()` - Delete docs

**Storage**: `chroma_storage/` directory

---

#### 6. `db.py` - SQLite Database
**Purpose**: Structured data storage

**Tables**:
1. `logs` - Chat messages
2. `documents` - Document metadata
3. `document_chunks` - Chunk texts
4. `leave_requests` - Leave submissions
5. `users` - User accounts
6. `user_sessions` - Session tracking

**Key Functions**:
- `init_db()` - Create tables
- `save_log()` - Save chat message
- `get_recent_history()` - Get chat history
- `save_leave_request()` - Submit leave request

---

#### 7. `embedder.py` - Text Extraction
**Purpose**: Document text extraction

**Key Functions**:
- `extract_text()` - Main extraction logic
- `extract_with_unstructured()` - Use unstructured library
- `extract_text_from_epub()` - EPUB handling
- `extract_text_from_image()` - OCR

**Dependencies**: `unstructured`, `pytesseract`, various format libraries

---

#### 8. `chunking.py` - Document Chunking
**Purpose**: Intelligent text splitting

**Key Functions**:
- `hybrid_chunk_document()` - Semantic chunking
- `chunk_text_token_aware()` - Token-aware splitting
- `get_avg_tokens_per_chunk()` - Statistics

**Strategy**:
- Max 300 tokens per chunk
- 32-token overlap
- Preserves sentence boundaries
- Maintains semantic units

---

#### 9. `keyword_search.py` - Keyword Search
**Purpose**: Traditional text search fallback

**Key Functions**:
- `keyword_search()` - Simple word matching

**Process**:
1. Gets all chunks from `db.py`
2. Splits query into words
3. Checks if words appear in chunks
4. Returns matching chunks

---

#### 10. `context_cache.py` - Context Management
**Purpose**: 24-hour conversation cache

**Key Functions**:
- `add_to_cache()` - Store conversation
- `get_recent_context()` - Retrieve recent context

**Storage**: `query_cache.db` SQLite file

---

#### 11. `admin_app.py` - Admin Interface
**Purpose**: Document management UI

**Key Functions**:
- Document upload interface
- Model selection (Gemini Flash/Pro)
- Document deletion
- Metadata viewing

**Process**:
1. Upload file to `policy_docs/`
2. Call `ingest_document()`
3. Display results
4. Manage existing documents

---

## Data Storage Architecture

### Three Storage Systems

#### 1. ChromaDB (`chroma_storage/`)
**Purpose**: Vector embeddings for semantic search

**Structure**:
- Collection: "hr_docs"
- Documents: Chunk texts
- Embeddings: 384-dimensional vectors
- IDs: `{doc_id}_{index}`
- Metadata: `{"doc_id": "..."}`

**Operations**:
- Add: `collection.add(documents, embeddings, ids, metadatas)`
- Query: `collection.query(query_texts, n_results)`
- Delete: `collection.delete(ids)`

---

#### 2. SQLite (`queries.db`)
**Purpose**: Structured relational data

**Tables**:
```sql
-- Chat logs
logs (id, user, question, answer, timestamp)

-- Document metadata
documents (id, filename, uploaded_at, avg_tokens)

-- Chunk storage
document_chunks (id, doc_id, text, embedding)

-- Leave requests
leave_requests (id, user, type, start_date, end_date, reason, status, timestamp)

-- Users
users (username, password)

-- Sessions
user_sessions (id, user, started_at)
```

**Operations**: Standard SQL (INSERT, SELECT, DELETE)

---

#### 3. Context Cache (`query_cache.db`)
**Purpose**: Temporary conversation context

**Structure**:
```sql
query_cache (id, user_id, question, answer, timestamp)
```

**Used for**: 24-hour conversation continuity

---

## Complete End-to-End Example

### Scenario: User asks "What is the leave policy?"

#### Step 1: User Input (chat_app.py)
```
User types: "What is the leave policy?"
File: chat_app.py lines 93-100
```

#### Step 2: Authentication Check
```python
# chat_app.py line 46
if login_user(login_user_input, login_pass_input):
    # User authenticated
```

#### Step 3: Get Context
```python
# chat_app.py line 97
context = get_recent_context(user)  # Last 24 hours
# Returns: [(question, answer), ...]
```

#### Step 4: Call Agent
```python
# chat_app.py line 100
answer, suggestions = run_agent(user, question, model)
```

#### Step 5: Intent Classification (agent.py)
```python
# agent.py line 10
intent_result = classify_and_extract_leave(question, model_name)
# Returns: {"is_leave_request": False}
```

#### Step 6: Retrieve Context (rag.py)
```python
# agent.py line 33
context_chunks = retrieve_context(question)
# Calls hybrid retrieval
```

#### Step 7A: Semantic Search (vector_store.py)
```python
# rag.py line 166
dense_results = search_context(query, top_k=5)
# Searches ChromaDB with embeddings
# Returns: ["Leave policy allows...", "You can apply...", ...]
```

#### Step 7B: Keyword Search (keyword_search.py)
```python
# rag.py line 172
keyword_results = keyword_search(query, top_k=5)
# Searches for "leave" and "policy" keywords
# Returns: Matching chunks
```

#### Step 8: Merge Results (rag.py)
```python
# rag.py lines 178-184
combined = []
for r in dense_results + keyword_results:
    if text not in seen:
        combined.append(text)
return combined[:5]  # Top 5 chunks
```

#### Step 9: Generate Answer (gemini_llm.py)
```python
# agent.py line 46
answer = query_gemini(context_texts, question, model_name, chat_history)

# Prompt:
"""
HR Policy Document:
The leave policy allows employees to take...

User Question: What is the leave policy?
"""
# Gemini generates answer from context
```

#### Step 10: Save Response (chat_app.py)
```python
# chat_app.py line 110
save_chat_message(user, question, answer, important=False)
add_to_cache(user, question, answer)
st.session_state.chat_history.append((question, answer, []))
```

#### Step 11: Display Result (chat_app.py)
```python
# chat_app.py lines 123-128
with st.chat_message("user"):
    st.markdown(q)
with st.chat_message("assistant"):
    st.markdown(a)  # Displays "The leave policy includes..."
```

---

## Key Design Patterns

### 1. Hybrid Retrieval
- **Semantic Search**: ChromaDB embeddings (meaning-based)
- **Keyword Search**: SQLite text matching (exact match)
- **Benefit**: Better recall, handles synonyms

### 2. Token-Aware Chunking
- **Max 300 tokens** per chunk
- **32-token overlap** between chunks
- **Benefit**: Preserves context, fits LLM context window

### 3. Conversational Context
- **24-hour cache** for continuity
- **Last 10 exchanges** in chat history
- **Benefit**: Follow-up questions work naturally

### 4. Fallback Strategy
- **No context found** → Show suggestions
- **Short answer** → Assume unsure, show FAQs
- **Benefit**: Never leaves user stuck

### 5. Parallel Processing
- **Multiprocessing** for embeddings
- **4 workers** maximum
- **Benefit**: Faster document ingestion

---

## Summary

The HR Chatbot follows a **layered RAG architecture**:

1. **Document Ingestion**: Extract → Chunk → Embed → Store
2. **Query Processing**: Classify → Retrieve → Generate → Display
3. **Storage**: ChromaDB (vectors) + SQLite (structured) + Cache (context)

Each file has a specific role in the pipeline, creating a robust and scalable HR assistant system.

