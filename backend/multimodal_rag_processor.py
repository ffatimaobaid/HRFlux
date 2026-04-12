import logging
import sys
import os
import json
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import numpy as np
try:
    import cv2
except ImportError:
    cv2 = None
from PIL import Image
import fitz  # PyMuPDF
try:
    import speech_recognition as sr
    from pydub import AudioSegment
except ImportError:
    sr = None
    AudioSegment = None

import torch
try:
    from transformers import CLIPProcessor, CLIPModel, WhisperProcessor, WhisperForConditionalGeneration
    from sentence_transformers import SentenceTransformer
except ImportError:
    CLIPProcessor = CLIPModel = WhisperProcessor = WhisperForConditionalGeneration = SentenceTransformer = None

import chromadb
from chromadb.config import Settings
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Constants
DB_PATH = os.path.join(os.path.dirname(__file__), "queries.db")

class MultiModalRAGProcessor:
    """Multi-Modal RAG Processor for admin document upload and analysis"""
    
    def __init__(self):
        # Models will be lazily loaded in _ensure_models_loaded()
        self.text_embedder = None
        self.clip_model = None
        self.clip_processor = None
        self.whisper_processor = None
        self.whisper_model = None
        self._models_loaded = False
        
        # Initialize ChromaDB (Keep this in __init__ as it's local and fast)
        try:
            self.chroma_client = chromadb.PersistentClient(path="chroma_multimodal_storage")
            self.collection = self.chroma_client.get_or_create_collection(
                name="multimodal_documents",
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.error(f"ChromaDB initialization error: {e}")
            self.collection = None
        
        self.supported_formats = {
            'text': ['.txt', '.md', '.csv'],
            'documents': ['.pdf', '.docx', '.pptx'],
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'],
            'audio': ['.mp3', '.wav', '.m4a', '.flac', '.ogg'],
            'video': ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        }

    def _ensure_models_loaded(self):
        """Lazily load expensive AI models only when needed."""
        if self._models_loaded:
            return
            
        logger.info("⚡ Lazily loading AI models (SentenceTransformer, CLIP, Whisper)...")
        try:
            self.text_embedder = SentenceTransformer('all-MiniLM-L6-v2') if SentenceTransformer else None
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32") if CLIPModel else None
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32") if CLIPProcessor else None
            self.whisper_processor = WhisperProcessor.from_pretrained("openai/whisper-base") if WhisperProcessor else None
            self.whisper_model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-base") if WhisperForConditionalGeneration else None
            self._models_loaded = True
            logger.info("✅ AI models loaded successfully.")
        except Exception as e:
            logger.error(f"❌ Error loading AI models: {e}. System will proceed with reduced capabilities.")
            # We don't set _models_loaded to True here to allow retry later if needed, 
            # or we could set it to prevent infinite retries.
        
        self.supported_formats = {
            'text': ['.txt', '.md', '.csv'],
            'documents': ['.pdf', '.docx', '.pptx'],
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'],
            'audio': ['.mp3', '.wav', '.m4a', '.flac', '.ogg'],
            'video': ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        }
    
    def process_file_for_rag(self, file_path: str, filename: str, 
                            uploaded_by: str = "admin") -> Dict[str, Any]:
        """Main processing function for multi-modal RAG"""
        self._ensure_models_loaded()
        try:
            # Detect file type
            file_type = self._detect_file_type(file_path)
            
            # Extract content based on file type
            if file_type == 'text':
                extracted_data = self._process_text_file(file_path)
            elif file_type == 'documents':
                extracted_data = self._process_document_file(file_path)
            elif file_type == 'images':
                extracted_data = self._process_image_file(file_path)
            elif file_type == 'audio':
                extracted_data = self._process_audio_file(file_path)
            elif file_type == 'video':
                extracted_data = self._process_video_file(file_path)
            else:
                return {'success': False, 'error': f'Unsupported file type: {file_type}'}
            
            if not extracted_data.get('success', False):
                return extracted_data
            
            # Generate embeddings
            embeddings_data = self._generate_multimodal_embeddings(extracted_data)
            
            # Store in vector database
            doc_id = self._store_in_vector_db(
                filename=filename,
                file_path=file_path,
                file_type=file_type,
                extracted_data=extracted_data,
                embeddings_data=embeddings_data,
                uploaded_by=uploaded_by
            )
            
            # Save metadata to SQLite
            file_size = os.path.getsize(file_path)
            total_chunks = len(extracted_data.get('chunks', []))
            self._save_metadata_to_db(doc_id, filename, file_path, file_type, file_size, total_chunks, extracted_data, uploaded_by)
            
            return {
                'success': True,
                'doc_id': doc_id,
                'filename': filename,
                'file_type': file_type,
                'extracted_data': extracted_data,
                'embeddings_generated': bool(embeddings_data),
                'stored_in_db': True,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Multi-modal RAG processing error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type from extension"""
        ext = os.path.splitext(file_path)[1].lower()
        for file_type, extensions in self.supported_formats.items():
            if ext in extensions:
                return file_type
        return 'unknown'
    
    def _process_text_file(self, file_path: str) -> Dict[str, Any]:
        """Process text files"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text_content = f.read()
            chunks = self._chunk_text(text_content)
            return {'success': True, 'text_content': text_content, 'chunks': chunks, 'total_chars': len(text_content), 'total_chunks': len(chunks)}
        except Exception as e:
            return {'success': False, 'error': f'Text processing error: {e}'}
    
    def _process_document_file(self, file_path: str) -> Dict[str, Any]:
        """Process PDF and document files"""
        try:
            if file_path.lower().endswith('.pdf'):
                doc = fitz.open(file_path)
                text_content = "".join([page.get_text() for page in doc])
                doc.close()
                chunks = self._chunk_text(text_content)
                return {'success': True, 'text_content': text_content, 'chunks': chunks, 'total_chunks': len(chunks)}
            elif file_path.lower().endswith('.docx'):
                from docx import Document
                doc = Document(file_path)
                text_content = "\n".join([para.text for para in doc.paragraphs])
                chunks = self._chunk_text(text_content)
                return {'success': True, 'text_content': text_content, 'chunks': chunks, 'total_chunks': len(chunks)}
            else:
                return {'success': False, 'error': 'Unsupported document format'}
        except Exception as e:
            return {'success': False, 'error': f'Document processing error: {e}'}
    
    def _process_image_file(self, file_path: str) -> Dict[str, Any]:
        """Process image files with OCR and visual analysis"""
        try:
            image = Image.open(file_path).convert('RGB')
            # OCR
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                ocr_text = pytesseract.image_to_string(image)
            except:
                ocr_text = ""
            
            # CLIP analysis
            image_description = ""
            image_features = []
            if self.clip_processor and self.clip_model:
                image_inputs = self.clip_processor(images=image, return_tensors="pt")
                with torch.no_grad():
                    image_features = self.clip_model.get_image_features(**image_inputs).numpy().tolist()[0]
                image_description = "Analyzed visual content"
            
            return {
                'success': True,
                'ocr_text': ocr_text,
                'image_description': image_description,
                'image_features': image_features,
                'chunks': [ocr_text] if ocr_text else [],
                'has_text': len(ocr_text) > 0
            }
        except Exception as e:
            return {'success': False, 'error': f'Image processing error: {e}'}
    
    def _process_audio_file(self, file_path: str) -> Dict[str, Any]:
        """Process audio files with transcription"""
        try:
            if not AudioSegment or not self.whisper_model:
                return {'success': False, 'error': 'Audio processing tools not available'}
            
            audio = AudioSegment.from_file(file_path)
            wav_path = file_path + ".wav"
            audio.export(wav_path, format="wav")
            
            import soundfile as sf
            speech_array, sampling_rate = sf.read(wav_path)
            input_features = self.whisper_processor(speech_array, sampling_rate=16000, return_tensors="pt").input_features
            predicted_ids = self.whisper_model.generate(input_features)
            transcription = self.whisper_processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
            
            if os.path.exists(wav_path):
                os.remove(wav_path)
            
            chunks = self._chunk_text(transcription)
            return {'success': True, 'transcription': transcription, 'chunks': chunks, 'duration': len(audio)/1000}
        except Exception as e:
            return {'success': False, 'error': f'Audio processing error: {e}'}
    
    def _process_video_file(self, file_path: str) -> Dict[str, Any]:
        """Video processing (Simplified for MVP)"""
        try:
            return {'success': True, 'message': 'Video processing placeholder', 'chunks': []}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            if end >= len(text): break
            start = end - overlap
        return chunks

    def _generate_multimodal_embeddings(self, extracted_data: Dict) -> Dict:
        embeddings = {}
        if self.text_embedder and 'chunks' in extracted_data and extracted_data['chunks']:
            embeddings['text'] = self.text_embedder.encode(extracted_data['chunks']).tolist()
        if 'image_features' in extracted_data and extracted_data['image_features']:
            embeddings['image'] = [extracted_data['image_features']]
        return embeddings

    def _store_in_vector_db(self, filename: str, file_path: str, file_type: str, extracted_data: Dict, embeddings_data: Dict, uploaded_by: str) -> str:
        doc_id = f"{file_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        metadata = {'filename': filename, 'file_type': file_type, 'uploaded_by': uploaded_by}
        
        if self.collection and 'text' in embeddings_data:
            for i, (chunk, emb) in enumerate(zip(extracted_data['chunks'], embeddings_data['text'])):
                self.collection.add(
                    ids=[f"{doc_id}_text_{i}"],
                    embeddings=[emb],
                    metadatas=[{**metadata, 'content': chunk[:200]}],
                    documents=[chunk]
                )
        return doc_id

    def _save_metadata_to_db(self, doc_id, filename, file_path, file_type, file_size, total_chunks, extracted_data, uploaded_by):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO multimodal_files 
                (doc_id, filename, file_path, file_type, file_size, total_chunks, processing_results, uploaded_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (doc_id, filename, file_path, file_type, file_size, total_chunks, json.dumps(extracted_data), uploaded_by))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Metadata DB error: {e}")

    def multimodal_search(self, query: str, top_k: int = 5) -> List[Dict]:
        self._ensure_models_loaded()
        if not self.collection or not self.text_embedder: return []
        query_emb = self.text_embedder.encode([query])[0].tolist()
        results = self.collection.query(query_embeddings=[query_emb], n_results=top_k)
        
        formatted = []
        for i in range(len(results['ids'][0])):
            formatted.append({
                'id': results['ids'][0][i],
                'distance': results['distances'][0][i],
                'metadata': results['metadatas'][0][i],
                'document': results['documents'][0][i]
            })
        return formatted

# Initialize
multimodal_rag_processor = MultiModalRAGProcessor()
