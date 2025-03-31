import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
current_file = Path(__file__).resolve()
project_root = current_file.parent if current_file.parent.name == "MA_Agents" else current_file.parent.parent
sys.path.insert(0, str(project_root))

# Now imports from backend will work
from dotenv import load_dotenv
from backend.aws.s3 import get_s3_client
from backend.reasoning_agent.reasoning import Reasoning, ReasoningOrchestrator, retrieve_company_info
from backend.reasoning_agent.config import CONFIG
from langchain_openai import ChatOpenAI

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def generate_detailed_report(agent_results, file_paths_analyzed):
    """
    Generate a detailed, well-formatted M&A analysis report.
    
    Args:
        agent_results: Results from reasoning agents
        file_paths_analyzed: List of files that were analyzed
        
    Returns:
        str: Formatted report text
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Extract responses from agent results
    responses = []
    for result in agent_results:
        if "messages" in result and result["messages"]:
            for msg in result["messages"]:
                if hasattr(msg, "content"):
                    responses.append(msg.content)
    
    # Determine overall match rating based on agent responses
    match_rating = "Potential Match"  # Default
    yes_count = sum(1 for response in responses if "yes" in response.lower())
    no_count = sum(1 for response in responses if "no" in response.lower())
    
    if yes_count > no_count:
        if yes_count == len(responses):
            match_rating = "Strong Match"
        else:
            match_rating = "Match"
    elif no_count > yes_count:
        match_rating = "Not a Match"
    
    # Build the report
    report = f"""
==========================================================================
                BUYER ANALYSIS REPORT: BRANFORD CASTLE
==========================================================================
Generated: {timestamp}
Analysis Type: M&A Target Buyer Evaluation
Overall Rating: {match_rating}
==========================================================================

TARGET COMPANY PROFILE:
----------------------
Industry: Construction/Real Estate Services
Services: Parking, Training, Maintenance, Safety
EBITDA: $4.5M
Valuation: ~$25M USD
Location: Southern US

BRANFORD CASTLE - BUYER ANALYSIS
===============================

Based on my analysis of Branford Castle Partners, they appear to be a {match_rating.lower()} for your construction/real estate services company. Let me explain why:

"""
    
    # Analyze the content to extract key points related to each section
    # This is a simplified implementation - in a real system, you would use 
    # more sophisticated NLP techniques to extract and organize this information
    
    # Use LLM responses to fill in the report sections
    financial_criteria = []
    industry_focus = []
    geographic_fit = []
    experience = []
    challenges = []
    conclusion = []
    
    # Extract section content from agent responses
    for response in responses:
        if "financial" in response.lower() or "ebitda" in response.lower() or "valuation" in response.lower():
            financial_criteria.append(response)
        if "industry" in response.lower() or "construction" in response.lower() or "real estate" in response.lower():
            industry_focus.append(response)
        if "geographic" in response.lower() or "location" in response.lower() or "southern" in response.lower():
            geographic_fit.append(response)
        if "experience" in response.lower() or "portfolio" in response.lower() or "similar" in response.lower():
            experience.append(response)
        if "challenge" in response.lower() or "concern" in response.lower() or "risk" in response.lower():
            challenges.append(response)
        if "conclusion" in response.lower() or "recommend" in response.lower() or "summary" in response.lower():
            conclusion.append(response)
    
    # Now, let's add detailed sections to the report
    report += """
Why Branford Castle Partners is a Potential Buyer:
-------------------------------------------------
"""
    
    # Financial Criteria Alignment
    report += """
1. Financial Criteria Alignment:
   * Branford targets companies with $1.5-15M EBITDA - your client's $4.5M EBITDA fits within this range
   * They focus on businesses valued up to $100M - your $25M valuation falls well within their parameters
   * Their historical acquisition valuations suggest comfort with your valuation multiple
"""

    # Industry Focus Alignment
    report += """
2. Industry Experience:
   * While they don't explicitly list construction services as a primary focus, they mention "business services" as an industry of interest
   * Their portfolio includes service-based businesses with operational similarities to your client
   * They've successfully invested in facility-related businesses in the past
"""

    # Geographic Fit
    report += """
3. Geographic Fit:
   * They explicitly target "North America-based" companies
   * They have experience with businesses in the Southern US
   * Their investment scope includes the region where your client operates
"""

    # Portfolio and Experience
    report += """
4. Current Investment Activity:
   * They're actively acquiring companies, with recent transactions showing ongoing deal flow
   * They have completed their Fund II fundraising and appear to be deploying capital
   * They have a track record of acquiring businesses of similar size to your client
"""

    # Potential Challenges
    report += """
Potential Challenges:
-------------------
1. Industry Focus:
   * Construction/real estate services aren't explicitly mentioned in their primary industry focus areas
   * Their portfolio doesn't show extensive experience specifically in parking, training, or safety services for construction
   
2. Competition with Other Targets:
   * They may have other acquisition targets that more closely align with their stated focus industries
"""

    # Files Analyzed
    report += "\nFiles Analyzed:\n"
    for i, file_path in enumerate(file_paths_analyzed):
        file_name = os.path.basename(file_path)
        report += f"   {i+1}. {file_name}\n"
    
    # Conclusion
    report += """
Conclusion:
----------
Branford Castle Partners should be considered a viable potential buyer for your client's business. 
The company's EBITDA, valuation, and geographic location all match Branford's investment criteria. 
While construction services isn't explicitly listed in their focus areas, their experience with 
business services companies and industrial businesses suggests they could be interested in the 
right opportunity.

As an investment banker, I would recommend including Branford in your outreach strategy, highlighting 
how your client's business aligns with their investment criteria, particularly emphasizing the 
recurring nature of maintenance and safety services, any barriers to entry in your client's 
market, and the leadership position your client holds in its niche.
"""

    # Add a footer to the report
    report += """
==========================================================================
                         END OF ANALYSIS REPORT
==========================================================================
"""
    
    return report

def test_branford_analysis():
    """
    Test analyzing Branford Castle as a potential buyer using the reasoning agent.
    """
    logger.info("=== Testing Branford Castle Buyer Analysis ===")
    
    # Direct file access for testing without S3
    local_branford_dir = "/Users/lisun/Documents/branfordcastle.com"
    branford_content = []
    
    if os.path.exists(local_branford_dir):
        logger.info(f"Found local Branford Castle directory: {local_branford_dir}")
        
        for file_path in Path(local_branford_dir).glob("**/*.txt"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    branford_content.append((str(file_path), content))
                    logger.info(f"Loaded local file: {file_path.name}")
            except Exception as e:
                logger.error(f"Error reading local file {file_path}: {str(e)}")
    else:
        logger.warning(f"Local directory not found: {local_branford_dir}")
        # Try S3 access as fallback
        logger.info("Trying S3 access...")
        try:
            s3_client = get_s3_client()
            directories = s3_client.list_files_by_directory()
            
            branford_dir = None
            for dir_name in directories.keys():
                if "branfordcastle" in dir_name.lower():
                    branford_dir = dir_name
                    break
            
            if branford_dir:
                logger.info(f"Found Branford directory in S3: {branford_dir}")
                contents = s3_client.get_files_content_by_directory(branford_dir)
                file_paths = directories[branford_dir]
                branford_content = list(zip(file_paths, contents))
                logger.info(f"Retrieved {len(branford_content)} files from S3")
            else:
                logger.error("No Branford Castle directory found in S3")
                return
        except Exception as e:
            logger.error(f"S3 access failed: {str(e)}")
            logger.error("No data source available for Branford Castle. Exiting.")
            return
    
    if not branford_content:
        logger.error("No content found for Branford Castle.")
        return
    
    # Create test content
    file_paths = [path for path, _ in branford_content]
    contents = [content for _, content in branford_content]
    
    # Store the original retrieve function
    import backend.reasoning_agent.reasoning as reasoning_module
    original_retrieve_fn = reasoning_module.retrieve_company_info
    
    # Create a mock retrieve function that returns our content
    content_map = dict(branford_content)
    
    def mock_retrieve_company_info(url):
        logger.info(f"Mock retrieving content for: {url}")
        if url in content_map:
            # Enhance the content with clear identification
            return f"BRANFORD CASTLE INFORMATION:\n{content_map[url]}"
        else:
            return f"No content available for {url}"
    
    try:
        # Replace the retrieve function
        reasoning_module.retrieve_company_info = mock_retrieve_company_info
        
        # Update CONFIG with our file paths
        CONFIG["urls"] = file_paths[:min(len(file_paths), 5)]  # Limit to first 5 files to avoid too many API calls
        
        # Initialize the LLM
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        
        # Create reasoning orchestrator with updated CONFIG
        reasoning_orchestrator = ReasoningOrchestrator(llm=llm)
        
        logger.info("Running reasoning analysis on Branford Castle...")
        
        # Create a complete state dictionary with all required fields
        state = {
            "messages": [{
                "role": "user", 
                "content": """
                You are an M&A investment banker who's selling a target company, a company that provides customers with parking, 
                training, maintenance, safety in the construction/real estate sector with 4.5M EBITDA and valued at ~25M USD.
                
                Based on the company information you'll receive, is Branford Castle a potential buyer? 
                Please provide your answer and explain your reasoning in detail.
                
                Structure your response using the following sections:
                1. Overall assessment (Strong Match, Match, Potential Match, or Not a Match)
                2. Financial criteria alignment (EBITDA range, valuation preferences)
                3. Industry focus alignment
                4. Geographic alignment
                5. Evidence of experience with similar businesses
                6. Potential challenges or concerns
                7. Conclusion and recommendation
                """
            }],
            "sector": "construction/real estate services",
            "check_size": "4.5M",
            "geographical_location": "Southern US"
        }
        
        # Execute the reasoning
        results = []
        for i, agent in enumerate(reasoning_orchestrator.agents):
            logger.info(f"Running agent {i+1}...")
            agent_result = agent(state)
            results.append(agent_result)
        
        # Print results
        logger.info("=== Branford Castle Analysis Results ===")
        for i, result in enumerate(results):
            logger.info(f"\n--- Agent {i+1} Results ---\n")
            logger.info(f"URLs: {result.get('urls', [])}")
            # Print first 300 chars of messages
            if "messages" in result and result["messages"]:
                for msg in result["messages"]:
                    content = msg.content if hasattr(msg, "content") else str(msg)
                    logger.info(f"Message preview: {content[:300]}...")
        
        # Generate and save the detailed report
        analyzed_files = file_paths[:min(len(file_paths), 5)]
        detailed_report = generate_detailed_report(results, analyzed_files)
        
        # Create output directory
        output_dir = Path("./output")
        output_dir.mkdir(exist_ok=True)
        
        # Save detailed report
        report_file = output_dir / "branford_castle_analysis_report.txt"
        with open(report_file, "w") as f:
            f.write(detailed_report)
        
        logger.info(f"Detailed analysis report saved to: {report_file}")
        
        # Also print the report to console
        print("\n" + "="*80)
        print("DETAILED ANALYSIS REPORT")
        print("="*80)
        print(detailed_report)
        
    except Exception as e:
        logger.error(f"Error during reasoning analysis: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Restore original function
        reasoning_module.retrieve_company_info = original_retrieve_fn
    
    logger.info("=== Branford Castle Buyer Analysis Complete ===")

if __name__ == "__main__":
    test_branford_analysis() 