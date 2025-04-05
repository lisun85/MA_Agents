"""
Prompts for the Summarizer agent.

This file contains all prompt templates used by the summarizer
to extract information from documents.
"""

def get_company_extraction_prompt(source_file: str, content: str, firm_name: str = None) -> str:
    """
    Generate the prompt for extracting portfolio companies from text.
    
    Args:
        source_file: Name of the source file
        content: Text content to analyze
        firm_name: Name of the private equity firm (dynamically determined)
        
    Returns:
        Formatted prompt string
    """
    # If firm name not provided, use a generic reference
    if not firm_name:
        firm_name = "the private equity firm"
    
    # Special handling for portfolio.txt with stronger instructions
    if "portfolio" in source_file.lower():
        return f"""
        Please extract ALL portfolio companies owned by {firm_name} from the following file: {source_file}.
        
        CRITICAL INSTRUCTIONS:
        1. This file is the PRIMARY AUTHORITATIVE SOURCE of portfolio companies
        2. Identify actual companies, not just URLs
        3. When you see a domain/URL like "example.com", extract the company it represents, not just the URL
        4. URLs should be included in the details field for the corresponding company, not as separate entries
        5. If a URL appears directly below a company description, it belongs to that company
        6. If only a URL is provided without a clear company name, extract the company name from the URL (e.g., "acme" from "acme.com")
        7. Mark ALL companies as currently owned (is_owned: true)
        8. For companies under "AFFILIATE TRANSACTIONS" section, add "affiliate: true" to mark them as affiliates
        
        For each company, provide these details as a JSON array:
        - "name": The company name (NOT just the URL). Extract properly from context.
        - "description": Brief description of what the company does
        - "details": Include "Website: [URL]" when a URL is provided
        - "is_owned": true for ALL companies (both direct investments and affiliates)
        - "affiliate": true for companies under "AFFILIATE TRANSACTIONS", false or omitted otherwise
        
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
        Please extract any portfolio companies owned by {firm_name} from the following text from file: {source_file}.
        
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

def get_investment_strategy_prompt(source_file: str, content: str, firm_name: str = None) -> str:
    """
    Generate the prompt for extracting investment strategy, approach, and criteria information.
    This combines the former separate investment approach and criteria prompts.
    
    Args:
        source_file: Name of the source file
        content: Text content to analyze
        firm_name: Name of the private equity firm
        
    Returns:
        Formatted prompt string
    """
    if not firm_name:
        firm_name = "the private equity firm"
    
    return f"""
    Please extract verbatim text describing the investment strategy, approach, and criteria of {firm_name} from the following file: {source_file}.
    
    IMPORTANT INSTRUCTIONS:
    1. Extract direct quotes that describe ANY of the following:
       a) Investment philosophy or approach - how the firm approaches investments
       b) Investment strategy - what strategies they use to create value
       c) Investment criteria - specific requirements for target companies (size, revenue, EBITDA)
       d) Deal structures, transaction types, or ownership preferences
    2. Look for relevant phrases about investment decision-making process, preferences, and requirements
    3. Preserve the exact wording from the text
    4. Do NOT summarize or paraphrase - only provide direct quotes
    5. If no relevant content is found, return an empty JSON array
    
    For each extract, provide:
    - "text": The exact verbatim text from the document
    - "location": A brief description of where in the document this appears (e.g., "About Us section")
    - "type": Classify each extract as either "approach" (investment philosophy, approach), or "criteria" (specific requirements, target metrics)
    
    The format should be:
    [
      {{"text": "Verbatim text about investment approach...", "location": "About section", "type": "approach"}},
      {{"text": "Verbatim text about investment criteria...", "location": "Criteria section", "type": "criteria"}}
    ]
    
    ONLY return the JSON array.
    
    Here's the text to analyze:
    
    {content}
    """

def get_industry_focus_prompt(source_file: str, content: str, firm_name: str = None) -> str:
    """
    Generate the prompt for extracting industry focus information.
    
    Args:
        source_file: Name of the source file
        content: Text content to analyze
        firm_name: Name of the private equity firm
        
    Returns:
        Formatted prompt string
    """
    if not firm_name:
        firm_name = "the private equity firm"
    
    return f"""
    Please extract verbatim text describing the industry focus areas of {firm_name} from the following file: {source_file}.
    
    IMPORTANT INSTRUCTIONS:
    1. Only extract direct quotes that explicitly describe target industries or sectors
    2. Look for mentions of specific industries, sectors, verticals, or markets the firm targets
    3. Preserve the exact wording from the text
    4. Do NOT summarize or paraphrase - only provide direct quotes
    5. Each extract should clearly indicate industry preferences or sector expertise
    6. If no relevant content is found, return an empty JSON array
    
    For each extract, provide:
    - "text": The exact verbatim text from the document
    - "location": A brief description of where in the document this appears (e.g., "Industry Focus section")
    
    The format should be:
    [
      {{"text": "Verbatim text about industry focus...", "location": "Sectors section"}},
      {{"text": "Another verbatim extract about target industries...", "location": "Strategy page"}}
    ]
    
    ONLY return the JSON array.
    
    Here's the text to analyze:
    
    {content}
    """

def get_industry_focus_summary_prompt(extracts: list) -> str:
    """
    Generate the prompt for summarizing industry focus information.
    
    Args:
        extracts: List of extracted text about industry focus
        
    Returns:
        Formatted prompt string
    """
    extracts_text = "\n\n".join([f"Extract {i+1}: {extract['text']}" for i, extract in enumerate(extracts)])
    
    return f"""
    Based on the following extracts about industry focus areas, please provide a concise summary of the key industries that the private equity firm focuses on.
    
    IMPORTANT INSTRUCTIONS:
    1. Identify the specific industries or sectors mentioned across the extracts
    2. Organize them by priority if that information is available
    3. Mention any industry specialization, expertise, or preference indicated
    4. Be factual and precise - only include industries explicitly mentioned
    5. Make the summary concise but comprehensive, covering all mentioned industries
    6. Use bullet points if there are multiple distinct industry focuses
    
    Here are the extracts to summarize:
    
    {extracts_text}
    
    Please provide only the summary with no additional commentary.
    """

def get_geographic_focus_prompt(source_file: str, content: str, firm_name: str = None) -> str:
    """
    Generate the prompt for extracting geographic focus information.
    
    Args:
        source_file: Name of the source file
        content: Text content to analyze
        firm_name: Name of the private equity firm
        
    Returns:
        Formatted prompt string
    """
    if not firm_name:
        firm_name = "the private equity firm"
    
    return f"""
    Please extract verbatim text describing the geographic focus or target regions of {firm_name} from the following file: {source_file}.
    
    IMPORTANT INSTRUCTIONS:
    1. Only extract direct quotes that explicitly describe target geographic regions
    2. Look for mentions of specific countries, regions, cities, or geographic preferences
    3. Preserve the exact wording from the text
    4. Do NOT summarize or paraphrase - only provide direct quotes
    5. Each extract should clearly indicate geographic preferences or regional focus
    6. If no relevant content is found, return an empty JSON array
    
    For each extract, provide:
    - "text": The exact verbatim text from the document
    - "location": A brief description of where in the document this appears (e.g., "Geographic Focus section")
    
    The format should be:
    [
      {{"text": "Verbatim text about geographic focus...", "location": "Regions section"}},
      {{"text": "Another verbatim extract about target regions...", "location": "Strategy page"}}
    ]
    
    ONLY return the JSON array.
    
    Here's the text to analyze:
    
    {content}
    """

def get_geographic_focus_summary_prompt(extracts: list) -> str:
    """
    Generate the prompt for summarizing geographic focus information.
    
    Args:
        extracts: List of extracted text about geographic focus
        
    Returns:
        Formatted prompt string
    """
    extracts_text = "\n\n".join([f"Extract {i+1}: {extract['text']}" for i, extract in enumerate(extracts)])
    
    return f"""
    Based on the following extracts about geographic focus areas, please provide a concise summary of the key regions that the private equity firm targets.
    
    IMPORTANT INSTRUCTIONS:
    1. Identify the specific regions, countries, or geographic areas mentioned across the extracts
    2. Organize them by priority if that information is available
    3. Mention any regional specialization or preference indicated
    4. Be factual and precise - only include regions explicitly mentioned
    5. Make the summary concise but comprehensive, covering all mentioned regions
    6. Use bullet points if there are multiple distinct geographic focuses
    
    Here are the extracts to summarize:
    
    {extracts_text}
    
    Please provide only the summary with no additional commentary.
    """

def get_team_and_contacts_prompt(source_file: str, content: str, firm_name: str = None) -> str:
    """
    Generate the prompt for extracting team members and contact information.
    
    Args:
        source_file: Name of the source file
        content: Text content to analyze
        firm_name: Name of the private equity firm
        
    Returns:
        Formatted prompt string
    """
    if not firm_name:
        firm_name = "the private equity firm"
    
    return f"""
    Please extract verbatim text describing team members and contact information of {firm_name} from the following file: {source_file}.
    
    IMPORTANT INSTRUCTIONS:
    1. Only extract direct quotes that describe team members, executives, partners, or contact details
    2. Look for names, titles, biographies, phone numbers, email addresses, and office locations
    3. Preserve the exact wording from the text
    4. Do NOT summarize or paraphrase - only provide direct quotes
    5. Each extract should be clearly about specific team members or contact information
    6. If no relevant content is found, return an empty JSON array
    
    For each extract, provide:
    - "text": The exact verbatim text from the document
    - "location": A brief description of where in the document this appears (e.g., "Team section")
    
    The format should be:
    [
      {{"text": "Verbatim text about team member...", "location": "Team page"}},
      {{"text": "Another verbatim extract about contact information...", "location": "Contact page"}}
    ]
    
    ONLY return the JSON array.
    
    Here's the text to analyze:
    
    {content}
    """

def get_media_and_news_prompt(source_file: str, content: str, firm_name: str = None, is_priority: bool = False) -> str:
    """
    Generate the prompt for extracting media mentions and news articles.
    
    Args:
        source_file: Name of the source file
        content: Text content to analyze
        firm_name: Name of the private equity firm
        is_priority: Whether this is a priority file that likely contains media content
        
    Returns:
        Formatted prompt string
    """
    if not firm_name:
        firm_name = "the private equity firm"
    
    # More specific instructions for priority files
    priority_instructions = """
    This file is likely to contain media content. Look carefully for:
    - Press releases or announcements (with dates and/or locations)
    - Deal announcements
    - Awards or recognition
    - Media mentions or quotes from news sources
    - Annual reports or investor communications
    """ if is_priority else ""
    
    return f"""
    Please extract verbatim text describing media mentions, news articles, or press releases about {firm_name} from the following file: {source_file}.
    
    {priority_instructions}
    
    IMPORTANT INSTRUCTIONS:
    1. Only extract DIRECT QUOTES from the text about:
       - Media coverage and press mentions
       - News articles and press releases
       - Deal announcements (acquisitions, investments)
       - Company awards and recognition
       - Major events and milestones
       - Executive appointments and leadership changes
    
    2. Look specifically for these key indicators of news content:
       - Date patterns (e.g., "September 10, 2024", "04.25.24", "June 2023")
       - Location formats (e.g., "NEW YORK, NY", "CHANTILLY, Va.", "Boston and San Francisco")
       - News announcement phrases (e.g., "announced today", "has acquired", "completed the sale")
       - Title-like text (often capitalized words at the beginning of paragraphs)
       - Quotes from executives or organizations
    
    3. Extract COMPLETE paragraphs containing these patterns, including:
       - The full title when present
       - The complete date and location information
       - The entire news content
       - Any quoted material
    
    4. Preserve the exact wording and formatting from the text
    5. DO NOT use general labels like "MEDIA" - extract the actual text content
    6. DO NOT summarize or paraphrase - only provide direct quotes
    7. Each extract should be substantive content about specific media mentions or news items
    8. If no relevant content is found, return an empty JSON array
    
    For each extract, provide:
    - "text": The exact verbatim text from the document (NOT placeholder text like "MEDIA")
    - "location": A brief description of where in the document this appears (e.g., "News section")
    
    The format should be:
    [
      {{"text": "Verbatim text about media mention...", "location": "News page"}},
      {{"text": "Another verbatim extract about press release...", "location": "Media section"}}
    ]
    
    ONLY return the JSON array.
    
    Here's the text to analyze:
    
    {content}
    """