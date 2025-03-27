import os
import logging
import PyPDF2
from pathlib import Path

logger = logging.getLogger(__name__)

def extract_pdf_content(file_path):
    """Extract text content from a PDF file."""
    logger.info(f"Processing PDF file: {file_path}")
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text_parts = []
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(f"Page {page_num}:\n{text}")
                except Exception as e:
                    logger.error(f"Error extracting text from page {page_num}: {str(e)}")
            
            content = "\n\n".join(text_parts)
            if content.strip():
                logger.info(f"Successfully extracted content from PDF: {file_path}")
                return content
            else:
                logger.error(f"Empty content extracted from PDF: {file_path}")
                return None
    except Exception as e:
        logger.error(f"Error processing PDF file {file_path}: {str(e)}")
        return None

def process_pdf_directory(directory):
    """Process all PDF files in a directory"""
    directory = Path(directory)
    if not directory.exists():
        logger.error(f"PDF directory does not exist: {directory}")
        return [], [], []
    
    pdf_contents = []
    processed_files = []
    failed_files = []
    
    # Get all PDF files
    pdf_files = list(directory.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in directory: {directory}")
        return [], [], []
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    for file_path in pdf_files:
        try:
            content = extract_pdf_content(file_path)
            if content and content.strip():
                pdf_contents.append(f"PDF {file_path.name}:\n{content}")
                processed_files.append(file_path.name)
                logger.info(f"Successfully processed PDF: {file_path.name}")
            else:
                failed_files.append(file_path.name)
                logger.error(f"Failed to extract content from: {file_path.name}")
        except Exception as e:
            failed_files.append(file_path.name)
            logger.error(f"Error processing PDF {file_path.name}: {str(e)}")
    
    return pdf_contents, processed_files, failed_files 