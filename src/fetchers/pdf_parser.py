"""PDF parser module for government documents"""

import pdfplumber
from typing import Optional, Dict, List
import logging
import os

logger = logging.getLogger(__name__)


class PDFParser:
    """Extracts text content from PDF documents"""

    def __init__(self):
        """Initialize PDF parser"""
        pass

    def parse_pdf(self, pdf_path: str, source: str = "PDF") -> Optional[Dict]:
        """
        Parse PDF file and extract text content
        
        Args:
            pdf_path: Path to PDF file
            source: Source name (e.g., "Economic Survey", "Union Budget")
            
        Returns:
            Dictionary with title, content, and metadata, or None on failure
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return None
        
        try:
            logger.info(f"Parsing PDF: {pdf_path}")
            content_parts = []
            
            with pdfplumber.open(pdf_path) as pdf:
                # Extract title from first page if possible
                title = self._extract_title(pdf)
                
                # Extract text from all pages
                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        text = page.extract_text()
                        if text:
                            content_parts.append(text)
                    except Exception as e:
                        logger.warning(f"Error extracting text from page {page_num}: {str(e)}")
                        continue
                
                # Combine all text
                full_content = '\n\n'.join(content_parts)
                
                if not full_content.strip():
                    logger.warning(f"No text content extracted from PDF: {pdf_path}")
                    return None
                
                return {
                    'url': pdf_path,
                    'title': title or os.path.basename(pdf_path),
                    'content': full_content,
                    'source': source,
                    'total_pages': len(pdf.pages)
                }
                
        except Exception as e:
            logger.error(f"Error parsing PDF {pdf_path}: {str(e)}")
            return None

    def _extract_title(self, pdf) -> Optional[str]:
        """
        Extract title from first page of PDF
        
        Args:
            pdf: pdfplumber PDF object
            
        Returns:
            Title string or None
        """
        try:
            if len(pdf.pages) > 0:
                first_page = pdf.pages[0]
                text = first_page.extract_text()
                
                if text:
                    # Take first few lines as potential title
                    lines = text.split('\n')[:5]
                    # Filter out very short lines and common headers/footers
                    title_candidates = [
                        line.strip() for line in lines
                        if len(line.strip()) > 10 and len(line.strip()) < 200
                    ]
                    if title_candidates:
                        return title_candidates[0]
        except Exception as e:
            logger.debug(f"Could not extract title: {str(e)}")
        
        return None

    def parse_pdf_section(self, pdf_path: str, start_page: int, end_page: int, 
                         source: str = "PDF") -> Optional[Dict]:
        """
        Parse specific section of PDF (pages range)
        
        Args:
            pdf_path: Path to PDF file
            start_page: Starting page number (1-indexed)
            end_page: Ending page number (1-indexed)
            source: Source name
            
        Returns:
            Dictionary with content from specified pages
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return None
        
        try:
            logger.info(f"Parsing PDF section: {pdf_path} (pages {start_page}-{end_page})")
            content_parts = []
            
            with pdfplumber.open(pdf_path) as pdf:
                if start_page > len(pdf.pages) or end_page > len(pdf.pages):
                    logger.error(f"Page range out of bounds. PDF has {len(pdf.pages)} pages")
                    return None
                
                for page_num in range(start_page - 1, min(end_page, len(pdf.pages))):
                    try:
                        page = pdf.pages[page_num]
                        text = page.extract_text()
                        if text:
                            content_parts.append(text)
                    except Exception as e:
                        logger.warning(f"Error extracting text from page {page_num + 1}: {str(e)}")
                        continue
                
                full_content = '\n\n'.join(content_parts)
                
                if not full_content.strip():
                    logger.warning(f"No text content extracted from PDF section")
                    return None
                
                return {
                    'url': pdf_path,
                    'title': f"{os.path.basename(pdf_path)} (Pages {start_page}-{end_page})",
                    'content': full_content,
                    'source': source,
                    'pages': f"{start_page}-{end_page}"
                }
                
        except Exception as e:
            logger.error(f"Error parsing PDF section {pdf_path}: {str(e)}")
            return None

    def extract_tables(self, pdf_path: str, pages: Optional[List[int]] = None) -> List[Dict]:
        """
        Extract tables from PDF
        
        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers to extract tables from (None for all pages)
            
        Returns:
            List of extracted tables as dictionaries
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return []
        
        tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                target_pages = pages if pages else range(len(pdf.pages))
                
                for page_num in target_pages:
                    if page_num < 0 or page_num >= len(pdf.pages):
                        continue
                    
                    try:
                        page = pdf.pages[page_num]
                        page_tables = page.extract_tables()
                        
                        for table in page_tables:
                            if table:
                                tables.append({
                                    'page': page_num + 1,
                                    'data': table
                                })
                    except Exception as e:
                        logger.warning(f"Error extracting tables from page {page_num + 1}: {str(e)}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error extracting tables from PDF {pdf_path}: {str(e)}")
        
        return tables

