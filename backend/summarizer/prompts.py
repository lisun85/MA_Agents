"""
Prompts for the Summarizer agent.

This file contains all prompt templates used by the summarizer
to extract information from documents.
"""

def get_company_extraction_prompt(source_file: str, content: str) -> str:
    """
    Generate the prompt for extracting portfolio companies from text.
    
    Args:
        source_file: Name of the source file
        content: Text content to analyze
        
    Returns:
        Formatted prompt string
    """
    # Special handling for portfolio.txt with stronger instructions
    if "portfolio" in source_file.lower():
        return f"""
        Please extract ALL portfolio companies owned by Branford Castle from the following file: {source_file}.
        
        CRITICAL INSTRUCTIONS:
        1. This file is the PRIMARY AUTHORITATIVE SOURCE of portfolio companies
        2. Identify actual companies, not just URLs
        3. When you see a domain/URL like "example.com", extract the company it represents, not just the URL
        4. URLs should be included in the details field for the corresponding company, not as separate entries
        5. If a URL appears directly below a company description, it belongs to that company
        6. If only a URL is provided without a clear company name, extract the company name from the URL (e.g., "acme" from "acme.com")
        7. Mark ALL companies as currently owned (is_owned: true)
        8. For companies under "BRANFORD AFFILIATE TRANSACTIONS" section, add "affiliate: true" to mark them as affiliates
        
        For each company, provide these details as a JSON array:
        - "name": The company name (NOT just the URL). Extract properly from context.
        - "description": Brief description of what the company does
        - "details": Include "Website: [URL]" when a URL is provided
        - "is_owned": true for ALL companies (both direct investments and affiliates)
        - "affiliate": true for companies under "BRANFORD AFFILIATE TRANSACTIONS", false or omitted otherwise
        
        The format should be:
        [
          {{"name": "Company Name", "description": "Brief description", "details": "Website: example.com, Additional details", "is_owned": true}},
          {{"name": "Affiliate Company", "description": "Brief description", "details": "Website: affiliate.com, Additional details", "is_owned": true, "affiliate": true}}
        ]
        
        ONLY return the JSON array.
        
        Here's the text to analyze:
        
        {content}
        """
    else:
        # Regular prompt for non-portfolio files
        return f"""
        Please extract any portfolio companies owned by Branford Castle from the following text from file: {source_file}.
        
        IMPORTANT:
        1. Identify actual company names, not just URLs
        2. Include URLs as part of the details field, not as the company name
        3. If only a URL is provided, extract the actual company name from the URL or context
        
        For each company, provide these details as a JSON array:
        - "name": The company name (not just a URL)
        - "description": Brief description of what the company does
        - "details": Include "Website: [URL]" when a URL is provided, plus any other details
        - "is_owned": true for all companies (both direct investments and affiliates)
        - "affiliate": true if it's described as an affiliate transaction, false or omitted otherwise
        
        The format should be:
        [
          {{"name": "Company Name", "description": "Brief description", "details": "Website: example.com, Additional details", "is_owned": true}},
          {{"name": "Affiliate Company", "description": "Brief description", "details": "Website: affiliate.com, Additional details", "is_owned": true, "affiliate": true}}
        ]
        
        If there are no portfolio companies in this file, return an empty array: []
        
        ONLY return the JSON array.
        
        Here's the text to analyze:
        
        {content}
        """

def get_connection_test_prompt() -> str:
    """
    Generate the prompt for testing LLM connection.
    
    Returns:
        Test prompt string
    """
    return "This is a connection test. Respond with 'Connection successful' only."