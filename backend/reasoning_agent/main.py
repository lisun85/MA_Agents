import logging
from backend.reasoning_agent.reasoning import ReasoningOrchestrator, reasoning_completion

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Entry point for the reasoning agent."""
    logger.info("Starting reasoning agent categorization...")
    
    # Create and run the orchestrator
    orchestrator = ReasoningOrchestrator()
    result = orchestrator()
    
    # Process completion
    final_result = reasoning_completion(result)
    
    # Print category summary
    if "stats_summary" in final_result and "categories" in final_result["stats_summary"]:
        categories = final_result["stats_summary"]["categories"]
        logger.info("Buyer Categorization Results:")
        logger.info(f"  Strong Potential Buyers: {categories.get('STRONG', 0)}")
        logger.info(f"  Medium Potential Buyers: {categories.get('MEDIUM', 0)}")
        logger.info(f"  Not Potential Buyers: {categories.get('NOT', 0)}")
    
    logger.info(f"Reasoning summary saved to: {final_result.get('summary_file', 'unknown')}")
    return 0

if __name__ == "__main__":
    main()
