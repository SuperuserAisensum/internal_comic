import os
import logging
import email
import extract_msg
from pathlib import Path

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG for more detailed logging

def extract_email_content(file_path):
    """Extract content from email files (.msg or .eml)"""
    logger.debug(f"Starting to process email file: {file_path}")
    file_path = Path(file_path)
    
    try:
        if file_path.suffix.lower() == '.msg':
            content = _process_msg_file(file_path)
            logger.debug(f"MSG file processing result: {'Success' if content else 'Failed'}")
            return content
        elif file_path.suffix.lower() == '.eml':
            content = _process_eml_file(file_path)
            logger.debug(f"EML file processing result: {'Success' if content else 'Failed'}")
            return content
        else:
            logger.error(f"Unsupported email file type: {file_path}")
            return None
    except Exception as e:
        logger.error(f"Error processing email file {file_path}: {str(e)}")
        return None

def _process_msg_file(file_path):
    """Process .msg files using extract_msg library"""
    try:
        logger.debug(f"Opening MSG file: {file_path}")
        msg = extract_msg.Message(str(file_path))
        subject = msg.subject or "No Subject"
        body = msg.body or ""
        
        content = f"Subject: {subject}\n\n{body}"
        if content.strip():
            logger.info(f"Successfully extracted content from MSG file: {file_path}")
            logger.debug(f"Content length: {len(content)} characters")
            return content
        else:
            logger.error(f"Empty content extracted from MSG file: {file_path}")
            return None
    except Exception as e:
        logger.error(f"Error processing MSG file {file_path}: {str(e)}")
        return None

def _process_eml_file(file_path):
    """Process .eml files using email library"""
    try:
        logger.debug(f"Opening EML file: {file_path}")
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            msg = email.message_from_file(f)
            content_parts = []
            
            # Add subject
            subject = msg.get('subject', 'No Subject')
            content_parts.append(f"Subject: {subject}\n")
            logger.debug(f"Added subject: {subject}")
            
            # Process body
            if msg.is_multipart():
                logger.debug("Processing multipart email")
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                text = payload.decode('utf-8', errors='ignore')
                                content_parts.append(text)
                                logger.debug(f"Added text part: {len(text)} characters")
                        except Exception as e:
                            logger.error(f"Error decoding email part: {str(e)}")
            else:
                logger.debug("Processing single-part email")
                try:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        text = payload.decode('utf-8', errors='ignore')
                        content_parts.append(text)
                        logger.debug(f"Added main content: {len(text)} characters")
                except Exception as e:
                    logger.error(f"Error decoding email content: {str(e)}")
            
            content = "\n".join(content_parts).strip()
            if content:
                logger.info(f"Successfully extracted content from EML file: {file_path}")
                logger.debug(f"Total content length: {len(content)} characters")
                return content
            else:
                logger.error(f"Empty content extracted from EML file: {file_path}")
                return None
    except Exception as e:
        logger.error(f"Error processing EML file {file_path}: {str(e)}")
        return None

def process_email_directory(directory):
    """Process all email files in a directory"""
    directory = Path(directory)
    logger.info(f"Starting to process email directory: {directory}")
    
    if not directory.exists():
        logger.error(f"Email directory does not exist: {directory}")
        return [], [], []
    
    email_contents = []
    processed_files = []
    failed_files = []
    
    # Get all .msg and .eml files
    msg_files = list(directory.glob("*.msg"))
    eml_files = list(directory.glob("*.eml"))
    email_files = msg_files + eml_files
    
    logger.info(f"Found {len(msg_files)} MSG files and {len(eml_files)} EML files")
    
    if not email_files:
        logger.warning(f"No email files found in directory: {directory}")
        return [], [], []
    
    for file_path in email_files:
        try:
            logger.debug(f"Processing file: {file_path.name}")
            content = extract_email_content(file_path)
            
            if content and content.strip():
                logger.info(f"Successfully extracted content from: {file_path.name}")
                email_contents.append(f"Email {file_path.name}:\n{content}")
                processed_files.append(file_path.name)
                logger.debug(f"Content length for {file_path.name}: {len(content)} characters")
            else:
                logger.error(f"No content extracted from: {file_path.name}")
                failed_files.append(file_path.name)
        except Exception as e:
            logger.error(f"Error processing email {file_path.name}: {str(e)}")
            failed_files.append(file_path.name)
    
    logger.info(f"Processed {len(processed_files)} files successfully, {len(failed_files)} files failed")
    logger.debug(f"Total content entries: {len(email_contents)}")
    
    return email_contents, processed_files, failed_files 