"""
Parallel extraction architecture for the Summarizer.

This module implements a set of extraction agents that can process
different sections of content in parallel, along with a compilation
agent that merges the results.
"""

import os
import logging
from typing import Dict, Any, List, Optional
import asyncio
from pathlib import Path
from langchain.agents import AgentExecutor
from langchain.agents.agent_types import AgentType
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

# Initialize logger
logger = logging.getLogger(__name__)

class BaseExtractionAgent:
    """Base class for all extraction agents."""
    
    def __init__(self, parent_summarizer, name="BaseExtractionAgent"):
        """
        Initialize with a reference to the parent summarizer.
        
        Args:
            parent_summarizer: The Summarizer instance that created this agent
            name: Name of this agent for logging
        """
        self.summarizer = parent_summarizer
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
        # Use the same LLM as the parent
        self.llm = parent_summarizer.llm
        self.extraction_results = {}
    
    async def extract(self, file_contents: Dict[str, str], firm_name: str) -> Dict[str, Any]:
        """
        Extract information from file contents.
        Must be implemented by subclasses.
        
        Args:
            file_contents: Dictionary mapping file paths to their contents
            firm_name: Name of the private equity firm
            
        Returns:
            Dictionary of extracted information
        """
        raise NotImplementedError("Subclasses must implement extract()")


class ExtractionAgent1(BaseExtractionAgent):
    """Agent responsible for investment_strategy and geographic_focus."""
    
    def __init__(self, parent_summarizer):
        super().__init__(parent_summarizer, "ExtractionAgent1")
        self.sections = ["investment_strategy", "geographic_focus"]
    
    async def extract(self, file_contents: Dict[str, str], firm_name: str) -> Dict[str, Any]:
        """Extract investment strategy and geographic focus information."""
        self.logger.info(f"Starting extraction of {', '.join(self.sections)}")
        
        try:
            # Create async tasks for each extraction
            tasks = [
                self._extract_investment_strategy(file_contents),
                self._extract_geographic_focus(file_contents)
            ]
            
            # Run tasks concurrently
            results = await asyncio.gather(*tasks)
            
            # Combine results
            extraction_results = {
                "investment_strategy": results[0],
                "geographic_focus": results[1]
            }
            
            self.logger.info(f"Completed extraction of {', '.join(self.sections)}")
            return extraction_results
            
        except Exception as e:
            self.logger.error(f"Error in ExtractionAgent1: {str(e)}")
            # Fallback to sequential extraction
            self.logger.info("Falling back to sequential extraction")
            return {
                "investment_strategy": await self._extract_investment_strategy_fallback(file_contents),
                "geographic_focus": await self._extract_geographic_focus_fallback(file_contents)
            }
    
    async def _extract_investment_strategy(self, file_contents: Dict[str, str]) -> Dict[str, Any]:
        """Async wrapper around parent's _extract_investment_strategy."""
        firm_name = self.summarizer.current_firm_name
        return await asyncio.to_thread(self.summarizer._extract_investment_strategy, file_contents)
    
    async def _extract_investment_strategy_fallback(self, file_contents: Dict[str, str]) -> Dict[str, Any]:
        """Fallback extraction for investment strategy."""
        try:
            return await self._extract_investment_strategy(file_contents)
        except Exception as e:
            self.logger.error(f"Fallback extraction failed for investment_strategy: {str(e)}")
            return {"extracts": [], "source_files": []}
    
    async def _extract_geographic_focus(self, file_contents: Dict[str, str]) -> Dict[str, Any]:
        """Async wrapper around parent's _extract_geographic_focus."""
        return await asyncio.to_thread(self.summarizer._extract_geographic_focus, file_contents)
    
    async def _extract_geographic_focus_fallback(self, file_contents: Dict[str, str]) -> Dict[str, Any]:
        """Fallback extraction for geographic focus."""
        try:
            return await self._extract_geographic_focus(file_contents)
        except Exception as e:
            self.logger.error(f"Fallback extraction failed for geographic_focus: {str(e)}")
            return {"extracts": [], "summary": ""}


class ExtractionAgent2(BaseExtractionAgent):
    """Agent responsible for industry_focus and portfolio_companies."""
    
    def __init__(self, parent_summarizer):
        super().__init__(parent_summarizer, "ExtractionAgent2")
        self.sections = ["industry_focus", "portfolio_companies"]
    
    async def extract(self, file_contents: Dict[str, str], firm_name: str) -> Dict[str, Any]:
        """Extract industry focus and portfolio companies information."""
        self.logger.info(f"Starting extraction of {', '.join(self.sections)}")
        
        try:
            # Create async tasks for each extraction
            tasks = [
                self._extract_industry_focus(file_contents),
                self._extract_portfolio_companies(file_contents)
            ]
            
            # Run tasks concurrently
            results = await asyncio.gather(*tasks)
            
            # Combine results
            extraction_results = {
                "industry_focus": results[0],
                "portfolio_companies": results[1]
            }
            
            self.logger.info(f"Completed extraction of {', '.join(self.sections)}")
            return extraction_results
            
        except Exception as e:
            self.logger.error(f"Error in ExtractionAgent2: {str(e)}")
            # Fallback to sequential extraction
            self.logger.info("Falling back to sequential extraction")
            return {
                "industry_focus": await self._extract_industry_focus_fallback(file_contents),
                "portfolio_companies": await self._extract_portfolio_companies_fallback(file_contents)
            }
    
    async def _extract_industry_focus(self, file_contents: Dict[str, str]) -> Dict[str, Any]:
        """Async wrapper around parent's _extract_industry_focus."""
        return await asyncio.to_thread(self.summarizer._extract_industry_focus, file_contents)
    
    async def _extract_industry_focus_fallback(self, file_contents: Dict[str, str]) -> Dict[str, Any]:
        """Fallback extraction for industry focus."""
        try:
            return await self._extract_industry_focus(file_contents)
        except Exception as e:
            self.logger.error(f"Fallback extraction failed for industry_focus: {str(e)}")
            return {"extracts": [], "summary": ""}
    
    async def _extract_portfolio_companies(self, file_contents: Dict[str, str]) -> List[Dict[str, Any]]:
        """Async wrapper around parent's _extract_portfolio_companies."""
        return await asyncio.to_thread(self.summarizer._extract_portfolio_companies, file_contents)
    
    async def _extract_portfolio_companies_fallback(self, file_contents: Dict[str, str]) -> List[Dict[str, Any]]:
        """Fallback extraction for portfolio companies."""
        try:
            return await self._extract_portfolio_companies(file_contents)
        except Exception as e:
            self.logger.error(f"Fallback extraction failed for portfolio_companies: {str(e)}")
            return []


class ExtractionAgent3(BaseExtractionAgent):
    """Agent responsible for team_and_contacts and media_and_news."""
    
    def __init__(self, parent_summarizer):
        super().__init__(parent_summarizer, "ExtractionAgent3")
        self.sections = ["team_and_contacts", "media_and_news"]
    
    async def extract(self, file_contents: Dict[str, str], firm_name: str) -> Dict[str, Any]:
        """Extract team and contacts and media and news information."""
        self.logger.info(f"Starting extraction of {', '.join(self.sections)}")
        
        # Create async tasks for each extraction
        team_task = self._extract_team_and_contacts(file_contents)
        media_task = self._extract_media_and_news(file_contents)
        
        # Results container
        extraction_results = {}
        
        # Handle team extraction
        try:
            team_results = await team_task
            extraction_results["team_and_contacts"] = team_results
            self.logger.info(f"Successfully extracted team_and_contacts")
        except Exception as e:
            self.logger.error(f"Error extracting team_and_contacts: {str(e)}")
            extraction_results["team_and_contacts"] = []
        
        # Handle media extraction - no fallback needed
        try:
            media_results = await media_task
            extraction_results["media_and_news"] = media_results
            self.logger.info(f"Successfully extracted media_and_news")
        except Exception as e:
            self.logger.error(f"Error extracting media_and_news: {str(e)}")
            extraction_results["media_and_news"] = []
        
        self.logger.info(f"Completed extraction of {', '.join(self.sections)}")
        return extraction_results
    
    async def _extract_team_and_contacts(self, file_contents: Dict[str, str]) -> List[Dict[str, Any]]:
        """Async wrapper around parent's _extract_team_and_contacts."""
        return await asyncio.to_thread(self.summarizer._extract_team_and_contacts, file_contents)
    
    async def _extract_media_and_news(self, file_contents: Dict[str, str]) -> List[Dict[str, Any]]:
        """Async wrapper around parent's _extract_media_and_news."""
        return await asyncio.to_thread(self.summarizer._extract_media_and_news, file_contents)


class CompilationAgent:
    """Agent responsible for compiling the outputs from the extraction agents."""
    
    def __init__(self, parent_summarizer):
        """
        Initialize with a reference to the parent summarizer.
        
        Args:
            parent_summarizer: The Summarizer instance that created this agent
        """
        self.summarizer = parent_summarizer
        self.logger = logging.getLogger(f"{__name__}.CompilationAgent")
    
    def _deduplicate_text_content(self, content):
        """
        Remove duplicate paragraphs from extracted text content.
        
        Args:
            content: String or list of strings containing potentially duplicated content
            
        Returns:
            Deduplicated content in the same format as the input
        """
        if not content:
            return content
            
        # Handle different input types
        is_string_input = isinstance(content, str)
        if is_string_input:
            # Split the content into paragraphs
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        elif isinstance(content, list) and all(isinstance(item, str) for item in content):
            # If it's a list of strings, treat each as a paragraph
            paragraphs = [p.strip() for p in content if p.strip()]
        else:
            # For other types (like structured data), return as is
            return content
            
        # Track seen paragraphs to avoid duplicates
        unique_paragraphs = []
        seen_paragraphs = set()
        
        for para in paragraphs:
            if para not in seen_paragraphs:
                unique_paragraphs.append(para)
                seen_paragraphs.add(para)
        
        # Log deduplication statistics
        original_count = len(paragraphs)
        deduped_count = len(unique_paragraphs)
        if original_count > deduped_count:
            self.logger.info(f"Removed {original_count - deduped_count} duplicate paragraphs ({(original_count - deduped_count) / original_count * 100:.1f}%)")
        
        # Return in the same format as input
        if is_string_input:
            return "\n\n".join(unique_paragraphs)
        else:
            return unique_paragraphs
    
    def _deduplicate_extracts_list(self, extracts):
        """
        Deduplicate a list of extract dictionaries.
        
        Args:
            extracts: List of dictionaries with 'text' keys
            
        Returns:
            Deduplicated list of extract dictionaries
        """
        if not extracts or not isinstance(extracts, list):
            return extracts
            
        # Extract just the text values to deduplicate
        texts = [item.get('text', '') for item in extracts if isinstance(item, dict)]
        
        # Track seen texts and corresponding extracts
        unique_extracts = []
        seen_texts = set()
        
        for extract in extracts:
            if not isinstance(extract, dict) or 'text' not in extract:
                continue
                
            text = extract['text']
            if text not in seen_texts:
                unique_extracts.append(extract)
                seen_texts.add(text)
        
        # Log deduplication statistics
        original_count = len(extracts)
        deduped_count = len(unique_extracts)
        if original_count > deduped_count:
            self.logger.info(f"Removed {original_count - deduped_count} duplicate extracts ({(original_count - deduped_count) / original_count * 100:.1f}%)")
            
        return unique_extracts
    
    def _deduplicate_structured_content(self, data):
        """
        Deduplicate structured content containing text fields.
        
        Args:
            data: Dictionary or list of dictionaries with mixed content
            
        Returns:
            Deduplicated structured content
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                # Recursively deduplicate nested structures
                if isinstance(value, (dict, list)):
                    result[key] = self._deduplicate_structured_content(value)
                # Deduplicate string content
                elif isinstance(value, str) and len(value) > 100:  # Only deduplicate longer text fields
                    result[key] = self._deduplicate_text_content(value)
                # Keep other values as is
                else:
                    result[key] = value
            return result
            
        elif isinstance(data, list):
            # If it's a list of dictionaries with 'text' fields, treat as extracts
            if all(isinstance(item, dict) and 'text' in item for item in data if isinstance(item, dict)):
                return self._deduplicate_extracts_list(data)
            # If it's a list of strings, deduplicate as text content
            elif all(isinstance(item, str) for item in data):
                return self._deduplicate_text_content(data)
            # For lists of other structures, recursively deduplicate each item
            else:
                return [self._deduplicate_structured_content(item) for item in data]
                
        # Return non-container types as is
        return data
    
    async def compile(self, extraction_results: Dict[str, Any], directory_name: str, firm_name: str, file_count: int) -> Dict[str, Any]:
        """
        Compile extraction results into the final summary, with deduplication.
        
        Args:
            extraction_results: Dictionary of extraction results from all agents
            directory_name: Name of the directory that was processed
            firm_name: Name of the private equity firm
            file_count: Number of files processed
            
        Returns:
            Dictionary containing the final summary result
        """
        self.logger.info("Compiling extraction results into final summary")
        
        try:
            # First, deduplicate the extraction results
            self.logger.info("Deduplicating extraction results")
            deduplicated_results = self._deduplicate_structured_content(extraction_results)
            
            # Merge all extraction results into a single dictionary
            summary_data = {
                "portfolio_companies": deduplicated_results.get("portfolio_companies", []),
                "investment_strategy": deduplicated_results.get("investment_strategy", {"extracts": [], "source_files": []}),
                "industry_focus": deduplicated_results.get("industry_focus", {"extracts": [], "summary": ""}),
                "geographic_focus": deduplicated_results.get("geographic_focus", {"extracts": [], "summary": ""}),
                "team_and_contacts": deduplicated_results.get("team_and_contacts", []),
                "media_and_news": deduplicated_results.get("media_and_news", [])
            }
            
            # Create the final summary result dictionary
            summary_result = {
                "success": True,
                "directory": directory_name,
                "firm_name": firm_name,
                "file_count": file_count,
                "summary": summary_data,
                "timestamp": self.summarizer.get_timestamp()
            }
            
            self.logger.info("Successfully compiled and deduplicated extraction results")
            return summary_result
            
        except Exception as e:
            self.logger.error(f"Error compiling extraction results: {str(e)}")
            # Return a minimal valid result
            return {
                "success": False,
                "error": f"Error compiling extraction results: {str(e)}",
                "directory": directory_name,
                "firm_name": firm_name,
                "summary": {},
                "timestamp": self.summarizer.get_timestamp()
            }


class ParallelExtractionManager:
    """Manager for coordinating parallel extraction agents."""
    
    def __init__(self, parent_summarizer):
        """
        Initialize with a reference to the parent summarizer.
        
        Args:
            parent_summarizer: The Summarizer instance that created this manager
        """
        self.summarizer = parent_summarizer
        self.logger = logging.getLogger(f"{__name__}.ParallelExtractionManager")
        
        # Create extraction agents
        self.agent1 = ExtractionAgent1(parent_summarizer)
        self.agent2 = ExtractionAgent2(parent_summarizer)
        self.agent3 = ExtractionAgent3(parent_summarizer)
        
        # Create compilation agent
        self.compilation_agent = CompilationAgent(parent_summarizer)
    
    async def run_parallel_extraction(self, file_contents: Dict[str, str], directory_name: str) -> Dict[str, Any]:
        """
        Run parallel extraction on file contents.
        
        Args:
            file_contents: Dictionary mapping file paths to their contents
            directory_name: Name of the directory to process
            
        Returns:
            Dictionary containing the final summary result
        """
        self.logger.info("Starting parallel extraction")
        firm_name = self.summarizer.current_firm_name
        file_count = len(file_contents)
        
        try:
            # Create tasks for each extraction agent
            tasks = [
                self.agent1.extract(file_contents, firm_name),
                self.agent2.extract(file_contents, firm_name),
                self.agent3.extract(file_contents, firm_name)
            ]
            
            # Run tasks concurrently
            agent_results = await asyncio.gather(*tasks)
            
            # Combine agent results
            extraction_results = {}
            for result in agent_results:
                extraction_results.update(result)
            
            # Compile results
            summary_result = await self.compilation_agent.compile(
                extraction_results, directory_name, firm_name, file_count
            )
            
            self.logger.info("Parallel extraction completed successfully")
            return summary_result
            
        except Exception as e:
            self.logger.error(f"Error in parallel extraction: {str(e)}")
            self.logger.info("Falling back to sequential extraction")
            # Defer to parent summarizer's sequential extraction
            return None 