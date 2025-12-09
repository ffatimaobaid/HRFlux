import streamlit as st
from rag import ingest_document
from db import get_all_documents, delete_document_metadata, init_db
from vector_store import delete_document_embeddings  

import os
import shutil
import json

# Initialize the database
init_db()

st.set_page_config(page_title="Admin Portal", layout="wide")
st.title("📂 Admin Document Manager")

# --- Model Selection Section ---
st.subheader("Select Gemini Model for Chatbot")

model_options = ["models/gemini-1.5-flash","models/gemini-2.5-flash", "models/gemini-1.5-pro"]
default_model = "models/gemini-1.5-flash"

# Load existing model choice
config_path = "config.json"
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        try:
            config = json.load(f)
            default_model = config.get("model", default_model)
        except json.JSONDecodeError:
            pass

selected_model = st.selectbox("Choose a Gemini model", model_options, index=model_options.index(default_model))

if st.button("Save Model Selection"):
    with open(config_path, "w") as f:
        json.dump({"model": selected_model}, f)
    st.success(f"Model set to: {selected_model}")

# --- Upload Section ---
st.subheader("Upload New HR Document")

file = st.file_uploader(
    "Choose a document (PDF, Word, PPT, HTML, EPUB)",
    type=["pdf", "docx", "pptx", "html", "epub"]
)

if file:
    os.makedirs("policy_docs", exist_ok=True)
    file_path = os.path.join("policy_docs", file.name)

    with st.spinner("Uploading and indexing document..."):
        try:
            # Save the file locally
            with open(file_path, "wb") as f:
                f.write(file.read())

            # Ingest the document
            chunks, avg_tokens, doc_id = ingest_document(file_path)
            st.success(f"Uploaded and indexed {chunks} chunks. Avg tokens/chunk: {avg_tokens:.2f}")
        except Exception as e:
            st.error(f"Failed to process document: {e}")

# --- Existing Document List ---
st.subheader("Existing Documents")
docs = get_all_documents()

if not docs:
    st.info("No documents found.")
else:
    for doc in docs:
        col1, col2, col3 = st.columns([4, 2, 1])
        with col1:
            st.markdown(f"**{doc[1]}** uploaded on `{doc[2][:10]}`")
        with col2:
            st.markdown(f"Avg tokens/chunk: `{doc[3]:.2f}`")
        with col3:
            if st.button("Delete", key=f"del_{doc[0]}"):
                filename = doc[1]
                doc_id = doc[0]

                # Delete metadata from DB
                delete_document_metadata(doc_id)

                # Delete local files
                try:
                    os.remove(os.path.join("policy_docs", filename))
                    shutil.rmtree(f"chroma/{doc_id}", ignore_errors=True)
                except Exception:
                    pass

                # ✅ Delete vector embeddings from ChromaDB
                try:
                    delete_document_embeddings(str(doc_id))
                except Exception as e:
                    st.warning(f"Failed to delete embeddings: {e}")

                st.rerun()
