import os
from typing import Dict, Any, Optional
import PyPDF2
import re
import email
from email import policy
from email.parser import BytesParser
from .text_processor import process_text_content

def process_file(file_path: str) -> Dict[str, Any]:
    """
    Process different file types (PDF, MSG, EML, TXT) to extract text content
    and generate insights.
    
    Args:
        file_path: Path to the file to process
        
    Returns:
        Dictionary containing processed content from text_processor
    """
    # Determine file type from extension
    _, ext = os.path.splitext(file_path)
    ext = ext.lower().lstrip('.')
    
    # Extract text content based on file type
    if ext == 'pdf':
        text_content = extract_text_from_pdf(file_path)
    elif ext == 'msg':
        text_content = extract_text_from_msg(file_path)
    elif ext == 'eml':
        text_content = extract_text_from_eml(file_path)
    elif ext == 'txt':
        text_content = extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    
    # Process the extracted text content
    if text_content:
        return process_text_content(text_content)
    else:
        # Return empty default results if no text was extracted
        return {
            'topics': ["Content Analysis", "Document Processing"],
            'linkedin_posts': [],
            'instagram_posts': []
        }

def extract_text_from_pdf(file_path: str) -> Optional[str]:
    """Extract text content from PDF file."""
    try:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return None

def extract_text_from_msg(file_path: str) -> Optional[str]:
    """Extract text content from MSG file."""
    # Note: This is a placeholder. Actual MSG parsing requires additional libraries
    # like extract_msg or win32com (Windows only)
    try:
        # Simulated implementation - in a real app, use a proper MSG parser
        with open(file_path, 'rb') as file:
            content = file.read()
            # Very basic extraction of text parts - not reliable for production
            text_parts = re.findall(rb'[\x20-\x7E\r\n]{20,}', content)
            text = b'\n'.join(text_parts).decode('utf-8', errors='ignore')
        return text
    except Exception as e:
        print(f"Error extracting text from MSG: {str(e)}")
        return None

def extract_text_from_eml(file_path: str) -> Optional[str]:
    """Extract text content from EML file."""
    try:
        with open(file_path, 'rb') as file:
            msg = BytesParser(policy=policy.default).parse(file)
            
            # Get subject and body
            subject = msg.get('subject', '')
            
            # Extract body text from different parts
            body = ""
            
            # Function to extract text from parts
            def extract_text_from_part(part):
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    return part.get_content()
                elif content_type == 'multipart/alternative' or content_type.startswith('multipart/'):
                    text = ""
                    for subpart in part.iter_parts():
                        text += extract_text_from_part(subpart)
                    return text
                return ""
            
            # Extract text from the message
            body = extract_text_from_part(msg)
            
            # Combine subject and body
            full_text = f"Subject: {subject}\n\n{body}"
            return full_text
            
    except Exception as e:
        print(f"Error extracting text from EML: {str(e)}")
        return None

def extract_text_from_txt(file_path: str) -> Optional[str]:
    """Extract text content from TXT file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        # Try with different encodings if UTF-8 fails
        try:
            with open(file_path, 'r', encoding='latin-1') as file:
                return file.read()
        except Exception as e:
            print(f"Error reading text file with latin-1 encoding: {str(e)}")
            return None
    except Exception as e:
        print(f"Error extracting text from TXT: {str(e)}")
        return None 