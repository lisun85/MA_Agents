"""
Email Agent Implementation.

This module implements the core functionality for generating personalized
emails based on reasoning agent outputs.
"""

import os
import re
import sys
import logging
import json
import google.generativeai as genai
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import docx
from docx import Document
from docx.shared import Pt, Inches
import base64
from io import BytesIO

from backend.email_agent.config import (
    MODEL_ID, TEMPERATURE, MAX_OUTPUT_TOKENS, API_KEY,
    REASONING_DIR, OUTPUT_DIR, BUYER_PREFIX, EMAIL_TEMPLATE_PATH,
    MAX_EMAILS_TO_GENERATE
)
from backend.email_agent.prompts import EMAIL_PROMPT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('email_agent.log')
    ]
)
logger = logging.getLogger(__name__)

class EmailAgent:
    """
    Agent for generating personalized emails based on reasoning outputs.
    """
    
    def __init__(self, template_path=None, output_dir=None):
        """Initialize the email agent."""
        if not API_KEY:
            raise ValueError("Google API key not found. Please set the GOOGLE_API_KEY environment variable.")
        
        # Configure Gemini API
        genai.configure(api_key=API_KEY)
        
        self.model = genai.GenerativeModel(
            model_name=MODEL_ID,
            generation_config={
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
            }
        )
        
        # Use custom template path if provided
        self.template_path = template_path if template_path else EMAIL_TEMPLATE_PATH
        logger.info(f"Using template path: {self.template_path}")
        
        # Use custom output directory if provided
        self.output_dir = output_dir if output_dir else OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized EmailAgent with model: {MODEL_ID}")
    
    def list_strong_buyer_files(self) -> List[Dict[str, Any]]:
        """
        List all strong buyer files in the reasoning output directory.
        
        Returns:
            List of dictionaries with file information
        """
        files = []
        
        try:
            logger.info(f"Looking for files in: {REASONING_DIR}")
            logger.info(f"Directory exists: {REASONING_DIR.exists()}")
            logger.info(f"Directory is a directory: {REASONING_DIR.is_dir()}")
            
            # List all files in the directory for debugging
            all_files = list(REASONING_DIR.glob("*"))
            logger.info(f"All files in directory ({len(all_files)}): {[f.name for f in all_files]}")
            
            # Get all files in the reasoning output directory
            pattern = f"{BUYER_PREFIX}*.txt"
            logger.info(f"Looking for pattern: {pattern}")
            matching_files = list(REASONING_DIR.glob(pattern))
            logger.info(f"Found {len(matching_files)} matching files")
            
            # Process all found files
            for file_path in matching_files:
                # Extract company name from filename
                filename = file_path.name
                company_name_match = re.search(r'(?:STRONG|Strong|strong)_(?:buyer_)?(.+?)_reasoning_', filename, re.IGNORECASE)
                
                if company_name_match:
                    company_name = company_name_match.group(1)
                    
                    files.append({
                        "path": str(file_path),  # Convert Path to string
                        "company_name": company_name,
                        "filename": filename,
                        "processed": False,
                        "success": None,
                        "output_file": None,
                        "error": None
                    })
            
            logger.info(f"Found {len(files)} strong buyer files to process")
            
            # Limit the number of files if needed
            if len(files) > MAX_EMAILS_TO_GENERATE:
                logger.warning(f"Limiting to {MAX_EMAILS_TO_GENERATE} files")
                files = files[:MAX_EMAILS_TO_GENERATE]
                
            return files
            
        except Exception as e:
            logger.error(f"Error listing strong buyer files: {str(e)}")
            return []
    
    def extract_buyer_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract relevant buyer information from a reasoning file.
        
        Args:
            file_path: Path to the reasoning file
            
        Returns:
            Dictionary with extracted information
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract company name
            company_name_match = re.search(r'Company:\s*(.+?)\n', content)
            company_name = company_name_match.group(1) if company_name_match else "Unknown Company"
            
            # Extract URL - updated to be more reliable
            url_match = re.search(r'URL:\s*([^\s]+)', content)
            url = url_match.group(1).strip() if url_match else f"{company_name}.com"
            
            # If URL is somehow wrong, try to fix it
            if not url or url == "4.5M" or not re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}$', url):
                url = f"{company_name}.com"
            
            # Extract contact information using multiple patterns
            contacts = []
            
            # Try to find contacts in the CONTACT INFORMATION section
            contact_section = re.search(r'CONTACT INFORMATION\n=+\n(.*?)\n=+', content, re.DOTALL)
            if contact_section and "No contact information found" not in contact_section.group(1):
                contact_text = contact_section.group(1)
                contact_lines = [line.strip() for line in contact_text.split('\n') if line.strip()]
                contacts.extend(contact_lines)
            
            # Also look for Key Team Members section with emails
            team_section = re.search(r'Key Team Members[:\s]*\n(.*?)(?:\n\n|\n=+)', content, re.DOTALL)
            if team_section:
                team_text = team_section.group(1).strip()
                team_lines = [line.strip() for line in team_text.split('\n') if line.strip() and '|' in line]
                contacts.extend(team_lines)
            
            # Look for emails in the entire document if we still don't have any
            if not contacts:
                email_matches = re.findall(r'([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)', content)
                if email_matches:
                    unique_emails = list(set(email_matches))
                    name_email_pattern = r'([A-Za-z\s.]+)(?:\([^)]+\))?\s*\|?\s*Email:\s*([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)'
                    name_email_matches = re.findall(name_email_pattern, content)
                    
                    if name_email_matches:
                        contacts = [f"{name.strip()} | Email: {email.strip()}" for name, email in name_email_matches]
                    else:
                        # Just list the emails if we can't associate names
                        contacts = [f"Contact: {email}" for email in unique_emails]
            
            # Extract reasoning from final assessment
            final_assessment = ""
            final_section = re.search(r'FINAL ASSESSMENT\n-+\n(.*?)\n(?:=+|CONTACT)', content, re.DOTALL)
            if final_section:
                final_assessment = final_section.group(1).strip()
            
            # Extract any other relevant sections for the email
            analysis_process = ""
            analysis_section = re.search(r'ANALYSIS PROCESS\n-+\n(.*?)\nFINAL ASSESSMENT', content, re.DOTALL)
            if analysis_section:
                analysis_process = analysis_section.group(1).strip()
            
            return {
                "company_name": company_name,
                "url": url,
                "contacts": contacts,
                "final_assessment": final_assessment,
                "analysis_process": analysis_process,
                "full_content": content
            }
            
        except Exception as e:
            logger.error(f"Error extracting buyer info from {file_path}: {str(e)}")
            return {
                "company_name": "Error",
                "url": "Error",
                "contacts": [],
                "final_assessment": "",
                "analysis_process": "",
                "full_content": f"Error: {str(e)}"
            }
    
    def encode_image(self, image_path: Path) -> str:
        """
        Encode an image to base64 for the Gemini API.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded image data
        """
        if not image_path.exists():
            logger.error(f"Image file not found: {image_path}")
            return ""
        
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image: {str(e)}")
            return ""
    
    def generate_email(self, buyer_info: Dict[str, Any]) -> str:
        """
        Generate a personalized email using the Gemini model.
        
        Args:
            buyer_info: Dictionary with buyer information
            
        Returns:
            Generated email content
        """
        try:
            # Prepare prompt with buyer information
            prompt = EMAIL_PROMPT
            
            # Create message parts
            parts = [{"text": prompt}]
            
            # Check if the template is an image or text file
            if self.template_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                # Handle image template
                template_image_b64 = self.encode_image(self.template_path)
                if not template_image_b64:
                    raise ValueError(f"Failed to encode template image at {self.template_path}")
                
                parts.append({
                    "inline_data": {
                        "mime_type": f"image/{self.template_path.suffix.lower().lstrip('.')}",
                        "data": template_image_b64
                    }
                })
            else:
                # Handle text template (assume it's a text file)
                try:
                    with open(self.template_path, 'r') as f:
                        template_text = f.read()
                    parts.append({"text": f"Email Template:\n\n{template_text}"})
                except Exception as e:
                    logger.error(f"Error reading template file: {e}")
                    raise ValueError(f"Failed to read template file at {self.template_path}")
            
            # Add buyer information
            parts.append({"text": "Buyer profile information:\n" + buyer_info['full_content']})
            
            # Create the template content
            template_content = {
                "role": "user",
                "parts": parts
            }
            
            # Generate response
            logger.info(f"Generating email for {buyer_info['company_name']}")
            response = self.model.generate_content([template_content])
            
            if not response or not response.text:
                raise ValueError("Empty response from Gemini API")
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating email: {str(e)}")
            return f"Error generating email: {str(e)}"
    
    def save_email_as_docx(self, email_content: str, buyer_info: Dict[str, Any]) -> Optional[Path]:
        """
        Save generated email as a Word document with proper formatting.
        
        Args:
            email_content: The generated email content
            buyer_info: Buyer information dictionary
            
        Returns:
            Path to the saved document or None if failed
        """
        try:
            # Create a new document
            doc = Document()
            
            # Add metadata section at top
            doc.add_heading("META INFORMATION", level=1)
            
            # Add URL with proper formatting
            url_para = doc.add_paragraph()
            url_para.add_run("URL: ").bold = True
            
            # Ensure URL is not "4.5M" and is a valid domain
            url = buyer_info['url']
            if not url or url == "4.5M" or not re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}$', url):
                url = f"{buyer_info['company_name']}.com"
            
            url_para.add_run(url)
            
            # Add team members with proper formatting and bullet points
            team_para = doc.add_paragraph()
            team_para.add_run("Team Members:").bold = True
            
            # Process contact information
            if buyer_info['contacts']:
                for contact in buyer_info['contacts']:
                    contact_para = doc.add_paragraph(style='ListBullet')
                    contact_para.add_run(contact)
            else:
                # Extract team information from the generated email
                team_section = re.search(r'\*\*Team Members:\*\*(.*?)(?:\*\*Subject:|$)', email_content, re.DOTALL)
                if team_section:
                    team_text = team_section.group(1).strip()
                    
                    # Process each team member line
                    for line in team_text.split('\n'):
                        if line.strip() and (line.strip().startswith('*') or line.strip().startswith('•')):
                            contact_para = doc.add_paragraph(style='ListBullet')
                            contact_para.add_run(line.strip().replace('* ', '').replace('• ', ''))
            
            # Add horizontal line
            doc.add_paragraph("─" * 50)
            
            # Extract and format the actual email content
            email_body = email_content
            
            # Remove the metadata section if it exists in the email content
            url_pattern = r'\*\*URL:\*\*.*?\n'
            team_pattern = r'\*\*Team Members:\*\*.*?(?=\*\*Subject:|$)'
            
            email_body = re.sub(url_pattern, '', email_body, flags=re.DOTALL)
            email_body = re.sub(team_pattern, '', email_body, flags=re.DOTALL)
            
            # Extract subject line
            subject_match = re.search(r'\*\*Subject:(.*?)\*\*', email_body)
            if subject_match:
                subject = subject_match.group(1).strip()
                email_body = re.sub(r'\*\*Subject:.*?\*\*', '', email_body, flags=re.DOTALL)
            else:
                subject = "Project Elevate: Premier Parking Lift Distributor Buyout Opportunity"
            
            # Add the subject as a heading
            doc.add_heading(subject, level=1)
            
            # Split into paragraphs
            paragraphs = re.split(r'\n\s*\n', email_body.strip())
            
            for paragraph in paragraphs:
                # Handle bullet point sections differently
                if '•' in paragraph or '*' in paragraph:
                    # Split by newlines to process each bullet point 
                    lines = paragraph.split('\n')
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                            
                        if line.startswith('•') or line.startswith('*'):
                            # This is a bullet point
                            bullet_para = doc.add_paragraph(style='ListBullet')
                            
                            # Extract the bullet text without the bullet symbol
                            bullet_text = re.sub(r'^[•*]\s*', '', line)
                            
                            # Look for bold text patterns and apply formatting
                            if '**' in bullet_text:
                                # Process bold text within the bullet point
                                parts = re.split(r'(\*\*.*?\*\*)', bullet_text)
                                for part in parts:
                                    if part.startswith('**') and part.endswith('**'):
                                        # This is bold text
                                        bold_text = part.strip('*')
                                        run = bullet_para.add_run(bold_text)
                                        run.bold = True
                                    else:
                                        bullet_para.add_run(part)
                            else:
                                # No formatting needed
                                bullet_para.add_run(bullet_text)
                        else:
                            # Regular text within a bullet point section
                            doc.add_paragraph(line)
                else:
                    # Regular paragraph
                    p = doc.add_paragraph()
                    
                    # Look for bold text with ** markers
                    if '**' in paragraph:
                        parts = re.split(r'(\*\*.*?\*\*)', paragraph)
                        for part in parts:
                            if part.startswith('**') and part.endswith('**'):
                                # This is bold text
                                bold_text = part.strip('*')
                                run = p.add_run(bold_text)
                                run.bold = True
                            else:
                                p.add_run(part)
                    else:
                        # No formatting needed
                        p.add_run(paragraph)
            
            # Save document
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            company_name = buyer_info['company_name'].replace('/', '_').replace('\\', '_')
            output_file = self.output_dir / f"Email_{company_name}_{timestamp}.docx"
            
            doc.save(output_file)
            logger.info(f"Saved email to {output_file}")
            
            return output_file
            
        except Exception as e:
            logger.error(f"Error saving email as Word document: {str(e)}")
            return None
    
    def process_file(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single strong buyer file.
        
        Args:
            file_info: Dictionary with file information
            
        Returns:
            Updated file information dictionary
        """
        try:
            logger.info(f"Processing file: {file_info['filename']}")
            
            # If path is a string, convert to Path
            file_path = file_info['path']
            if isinstance(file_path, str):
                file_path = Path(file_path)
            
            # Extract buyer information
            buyer_info = self.extract_buyer_info(file_path)
            
            # Generate email
            email_content = self.generate_email(buyer_info)
            
            # Save as Word document
            output_file = self.save_email_as_docx(email_content, buyer_info)
            
            # Update file information
            file_info.update({
                "processed": True,
                "success": output_file is not None,
                "output_file": str(output_file) if output_file else None,  # Convert Path to string
                "error": None
            })
            
            return file_info
            
        except Exception as e:
            logger.error(f"Error processing file {file_info['filename']}: {str(e)}")
            
            file_info.update({
                "processed": True,
                "success": False,
                "output_file": None,
                "error": str(e)
            })
            
            return file_info
    
    def run(self, single_file=None) -> Dict[str, Any]:
        """
        Run the email generation process for all strong buyer files or a single file.
        
        Args:
            single_file: Optional path to a single file to process
            
        Returns:
            Dictionary with results and statistics
        """
        logger.info("Starting email generation process")
        
        # Check if we're processing just a single file
        if single_file:
            single_file_path = Path(single_file)
            if not single_file_path.exists():
                logger.error(f"Single file not found: {single_file}")
                return {
                    "status": "error",
                    "message": f"File not found: {single_file}",
                    "stats": {"total": 0, "processed": 0, "successful": 0, "failed": 0}
                }
            
            # Create file info for the single file
            company_name = single_file_path.stem.split('_')[1]  # Assuming format STRONG_companyname_...
            file_info = {
                "path": str(single_file_path),  # Convert Path to string
                "company_name": company_name,
                "filename": single_file_path.name,
                "processed": False,
                "success": None,
                "output_file": None,
                "error": None
            }
            
            # Process the single file
            logger.info(f"Processing single file: {single_file_path.name}")
            result = self.process_file(file_info)
            
            # Update statistics
            stats = {"total": 1, "processed": 1, "successful": 1 if result["success"] else 0, "failed": 0 if result["success"] else 1}
            
            logger.info(f"Single file processing complete. Success: {result['success']}")
            
            return {
                "status": "complete",
                "results": [result],
                "stats": stats
            }
        
        # Default behavior - process all strong buyer files
        # List strong buyer files
        files = self.list_strong_buyer_files()
        
        if not files:
            logger.warning("No strong buyer files found to process")
            return {
                "status": "complete",
                "message": "No strong buyer files found to process",
                "stats": {"total": 0, "processed": 0, "successful": 0, "failed": 0}
            }
        
        # Process each file
        results = []
        stats = {"total": len(files), "processed": 0, "successful": 0, "failed": 0}
        
        for file_info in files:
            # Convert Path to string to ensure JSON serialization works
            if isinstance(file_info["path"], Path):
                file_info["path"] = str(file_info["path"])
            
            # Process the file
            result = self.process_file(file_info)
            
            # Ensure output_file is a string for JSON serialization
            if result["output_file"] and isinstance(result["output_file"], Path):
                result["output_file"] = str(result["output_file"])
            
            # Update statistics
            stats["processed"] += 1
            if result["success"]:
                stats["successful"] += 1
            else:
                stats["failed"] += 1
            
            # Add to results
            results.append(result)
        
        # Save summary
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.output_dir / f"email_generation_summary_{timestamp}.json"
        
        with open(summary_file, "w") as f:
            json.dump({
                "stats": stats,
                "results": results
            }, f, indent=2, default=str)  # Use default=str to handle any other non-serializable objects
        
        logger.info(f"Email generation complete. Stats: {stats}")
        
        return {
            "status": "complete",
            "results": results,
            "stats": stats,
            "summary_file": str(summary_file)  # Convert Path to string
        } 