"""
Enhanced PDF Display Utilities for Chat App
Provides multiple methods for PDF display in Streamlit.
"""

import streamlit as st
import base64
import os
from typing import Optional

def display_pdf_embed(pdf_path: str, width: str = "100%", height: str = "600px") -> bool:
    """
    Display PDF using iframe embed method.
    
    Args:
        pdf_path: Path to PDF file
        width: Width of iframe
        height: Height of iframe
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(pdf_path, "rb") as pdf_file:
            base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
        
        pdf_display = f'''
        <iframe src="data:application/pdf;base64,{base64_pdf}" 
                width="{width}" height="{height}" type="application/pdf">
        </iframe>
        '''
        st.markdown(pdf_display, unsafe_allow_html=True)
        return True
        
    except Exception as e:
        st.error(f"Error displaying PDF with embed: {str(e)}")
        return False

def display_pdf_object(pdf_path: str, width: str = "100%", height: str = "600px") -> bool:
    """
    Display PDF using object tag method.
    
    Args:
        pdf_path: Path to PDF file
        width: Width of object
        height: Height of object
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(pdf_path, "rb") as pdf_file:
            base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
        
        pdf_display = f'''
        <object data="data:application/pdf;base64,{base64_pdf}" 
                type="application/pdf" width="{width}" height="{height}">
            <p>It appears you don't have a PDF plugin for this browser. 
               You can <a href="data:application/pdf;base64,{base64_pdf}" 
               download="document.pdf">click here to download the PDF file.</a></p>
        </object>
        '''
        st.markdown(pdf_display, unsafe_allow_html=True)
        return True
        
    except Exception as e:
        st.error(f"Error displaying PDF with object: {str(e)}")
        return False

def display_pdf_base64_link(pdf_path: str) -> bool:
    """
    Display PDF as a clickable base64 link.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(pdf_path, "rb") as pdf_file:
            base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
        
        # Create a clickable link
        pdf_link = f'''
        <a href="data:application/pdf;base64,{base64_pdf}" 
           target="_blank" style="display: inline-block; padding: 10px 20px; 
           background-color: #007bff; color: white; text-decoration: none; 
           border-radius: 5px; margin: 10px 0;">
           📄 Open PDF in New Tab
        </a>
        '''
        st.markdown(pdf_link, unsafe_allow_html=True)
        return True
        
    except Exception as e:
        st.error(f"Error creating PDF link: {str(e)}")
        return False

def display_pdf_info(pdf_path: str) -> None:
    """Display PDF file information."""
    try:
        file_size = os.path.getsize(pdf_path)
        file_name = os.path.basename(pdf_path)
        
        st.write(f"📄 **File:** {file_name}")
        st.write(f"📊 **Size:** {file_size:,} bytes")
        st.write(f"📁 **Location:** {pdf_path}")
        
    except Exception as e:
        st.error(f"Error reading file info: {str(e)}")

def enhanced_pdf_display(pdf_path: str, document_title: str = "Document") -> None:
    """
    Enhanced PDF display with multiple viewing options.
    
    Args:
        pdf_path: Path to PDF file
        document_title: Title of the document
    """
    if not os.path.exists(pdf_path):
        st.error("❌ PDF file not found.")
        return
    
    st.subheader(f"📄 {document_title}")
    
    # Display file info
    display_pdf_info(pdf_path)
    
    # Create tabs for different viewing methods
    tab1, tab2, tab3 = st.tabs(["👁️ Preview", "🔗 Open in Browser", "📥 Download"])
    
    with tab1:
        st.write("**PDF Preview:**")
        # Try iframe first
        if not display_pdf_embed(pdf_path):
            # Fallback to object tag
            if not display_pdf_object(pdf_path):
                st.warning("⚠️ Preview not available. Use other tabs to view.")
    
    with tab2:
        st.write("**Open in Browser:**")
        if display_pdf_base64_link(pdf_path):
            st.info("💡 Click the link above to open the PDF in a new browser tab.")
    
    with tab3:
        st.write("**Download Options:**")
        # This will be handled by the main chat app's download button
        st.info("📥 Use the download button in the main chat interface.")

def create_pdf_viewer(pdf_path: str, document_title: str = "Document") -> None:
    """
    Create a comprehensive PDF viewer with all options in one place.
    
    Args:
        pdf_path: Path to PDF file
        document_title: Title of the document
    """
    if not os.path.exists(pdf_path):
        st.error("❌ PDF file not found.")
        return
    
    st.markdown(f"### 📄 {document_title}")
    
    # Display file info
    display_pdf_info(pdf_path)
    
    # Create expandable preview
    with st.expander("👁️ Click to Preview PDF", expanded=False):
        st.write("**Document Preview:**")
        # Try multiple display methods
        success = display_pdf_embed(pdf_path)
        if not success:
            success = display_pdf_object(pdf_path)
        
        if not success:
            st.warning("⚠️ Preview not available in this browser.")
            st.info("💡 Try the 'Open in Browser' option below.")
    
    # Additional viewing options
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🌐 Open in Browser", key=f"browser_{os.path.basename(pdf_path)}"):
            display_pdf_base64_link(pdf_path)
    
    with col2:
        st.info("📥 Use the download button on the right to save the file.")
