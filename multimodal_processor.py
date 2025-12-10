"""
Multimodal RAG Processor
Handles images, videos, audio, and other media formats for HR chatbot
"""

import os
import base64
import tempfile
from typing import List, Dict, Any, Optional
import json
from pathlib import Path
import pytesseract

# Point pytesseract to the installed Tesseract binary (adjust path if needed)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class MultimodalProcessor:
    """Handles processing of various media formats for RAG"""
    
    def __init__(self):
        self.supported_image_formats = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        self.supported_video_formats = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
        self.supported_audio_formats = ['.mp3', '.wav', '.m4a', '.flac', 'aac', '.ogg']
        self.supported_documentdisplay_formats = ['.pdf', '.docx', '.pptx', '.xlsx']
    
    def process_media_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process a media file and extract searchable content
        
        Args:
            file_path: Path to the media file
            
        Returns:
            Dict with extracted content and metadata
        """
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext in self.supported_image_formats:
            return self._process_image(file_path)
        elif file_ext in self.supported_video_formats:
            return self._process_video(file_path)
        elif file_ext in self.supported_audio_formats:
            return self._process_audio(file_path)
        else:
            return {"error": f"Unsupported format: {file_ext}"}
    
    def _process_image(self, image_path: str) -> Dict[str, Any]:
        """Process image file using vision models"""
        try:
            # Import vision libraries
            from PIL import Image
            import pytesseract
            from transformers import pipeline
            
            # Open image
            image = Image.open(image_path)
            
            # Extract text using OCR
            text_content = pytesseract.image_to_string(image)
            
            # Generate image description using vision model
            try:
                # Use BLIP or similar vision model for description
                image_description = self._generate_image_description(image)
            except Exception as e:
                print(f"Vision model error: {e}")
                image_description = "Image content could not be analyzed"
            
            # Get image metadata
            metadata = {
                "format": image.format,
                "size": image.size,
                "mode": image.mode,
                "filename": os.path.basename(image_path)
            }
            
            return {
                "type": "image",
                "text_content": text_content.strip(),
                "description": image_description,
                "metadata": metadata,
                "searchable_content": f"{text_content.strip()} {image_description}"
            }
            
        except Exception as e:
            return {"error": f"Image processing failed: {str(e)}"}
    
    def _process_video(self, video_path: str) -> Dict[str, Any]:
        """Process video file - extract frames and audio"""
        try:
            import cv2
            from moviepy.editor import VideoFileClip
            
            # Extract video metadata
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            cap.release()
            
            # Extract audio from video
            video_clip = VideoFileClip(video_path)
            
            # Extract key frames (every 30 seconds)
            frames_content = []
            frame_descriptions = []
            
            for i, time in enumerate(range(0, int(duration), 30)):
                if time >= duration:
                    break
                    
                try:
                    frame = video_clip.get_frame(time)
                    frame_image = Image.fromarray(frame)
                    
                    # OCR on frame
                    frame_text = pytesseract.image_to_string(frame_image)
                    if frame_text.strip():
                        frames_content.append(f"Frame at {time}s: {frame_text.strip()}")
                    
                    # Frame description
                    frame_desc = self._generate_image_description(frame_image)
                    frame_descriptions.append(f"Frame at {time}s: {frame_desc}")
                    
                except Exception as e:
                    print(f"Frame processing error at {time}s: {e}")
                    continue
            
            # Extract audio transcript if available
            audio_transcript = ""
            try:
                if video_clip.audio is not None:
                    audio_transcript = self._transcribe_audio_from_video(video_clip)
            except Exception as e:
                print(f"Audio extraction error: {e}")
            
            video_clip.close()
            
            return {
                "type": "video",
                "duration": duration,
                "fps": fps,
                "frame_count": frame_count,
                "frames_content": frames_content,
                "frame_descriptions": frame_descriptions,
                "audio_transcript": audio_transcript,
                "searchable_content": " ".join(frames_content + frame_descriptions + [audio_transcript]),
                "metadata": {
                    "filename": os.path.basename(video_path),
                    "duration": duration,
                    "fps": fps
                }
            }
            
        except Exception as e:
            return {"error": f"Video processing failed: {str(e)}"}
    
    def _process_audio(self, audio_path: str) -> Dict[str, Any]:
        """Process audio file - transcribe to text"""
        try:
            import speech_recognition as sr
            from pydub import AudioSegment
            
            # Load audio file
            audio = AudioSegment.from_file(audio_path)
            
            # Convert to WAV for processing
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                audio.export(temp_file.name, format="wav")
                
                # Transcribe audio
                recognizer = sr.Recognizer()
                with sr.AudioFile(temp_file.name) as source:
                    audio_data = recognizer.record(source)
                    
                try:
                    # Try Google Speech Recognition
                    transcript = recognizer.recognize_google(audio_data)
                except:
                    try:
                        # Fallback to Sphinx
                        transcript = recognizer.recognize_sphinx(audio_data)
                    except:
                        transcript = "Audio transcription failed"
                
                os.unlink(temp_file.name)
            
            return {
                "type": "audio",
                "transcript": transcript,
                "duration": len(audio) / 1000.0,  # Convert to seconds
                "searchable_content": transcript,
                "metadata": {
                    "filename": os.path.basename(audio_path),
                    "duration": len(audio) / 1000.0
                }
            }
            
        except Exception as e:
            return {"error": f"Audio processing failed: {str(e)}"}
    
    def _generate_image_description(self, image) -> str:
        """Generate description using vision model"""
        try:
            from transformers import BlipProcessor, BlipForConditionalGeneration
            
            # Load BLIP model
            processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
            
            # Generate caption
            inputs = processor(image, return_tensors="pt")
            out = model.generate(**inputs, max_length=50)
            caption = processor.decode(out[0], skip_special_tokens=True)
            
            return caption
            
        except Exception as e:
            # Fallback to basic description
            return f"Image with dimensions {image.size} in {image.mode} mode"
    
    def _transcribe_audio_from_video(self, video_clip) -> str:
        """Transcribe audio from video clip"""
        try:
            # Extract audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                video_clip.audio.write_audiofile(temp_file.name, verbose=False, logger=None)
                
                # Transcribe
                import speech_recognition as sr
                recognizer = sr.Recognizer()
                with sr.AudioFile(temp_file.name) as source:
                    audio_data = recognizer.record(source)
                    transcript = recognizer.recognize_google(audio_data)
                
                os.unlink(temp_file.name)
                return transcript
                
        except Exception as e:
            return f"Audio transcription failed: {str(e)}"
    
    def extract_media_content_for_chunking(self, file_path: str) -> str:
        """
        Extract searchable content from media file for chunking
        
        Args:
            file_path: Path to media file
            
        Returns:
            Searchable text content
        """
        result = self.process_media_file(file_path)
        
        if "error" in result:
            return f"[{result['error']}]"
        
        if result["type"] == "image":
            return f"[IMAGE: {result['metadata']['filename']}] {result['searchable_content']}"
        elif result["type"] == "video":
            content = f"[VIDEO: {result['metadata']['filename']} - {result['duration']:.1f}s]\n"
            if result['audio_transcript']:
                content += f"Audio: {result['audio_transcript']}\n"
            if result['frame_descriptions']:
                content += "Visual content: " + " ".join(result['frame_descriptions'][:5])  # Limit descriptions
            return content
        elif result["type"] == "audio":
            return f"[AUDIO: {result['metadata']['filename']} - {result['duration']:.1f}s] {result['transcript']}"
        
        return result.get("searchable_content", "")

# Global instance
multimodal_processor = MultimodalProcessor()
