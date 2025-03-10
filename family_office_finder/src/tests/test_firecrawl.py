import unittest
import os
from unittest.mock import patch, MagicMock
from firecrawl import FirecrawlApp
from family_office_finder.schema import FamilyOfficeSchema, SimplifiedFamilyOfficeSchema, family_office_schema
from dotenv import load_dotenv

load_dotenv()

'''
Test these websites:
https://cressetcapital.com/contact
https://axial.net/forum/companies/construction-engineering-private-equity-firms/2
https://branfordcastle.com/media-coverage
'''


class TestFirecrawl(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.api_key = os.environ.get("FIRECRAWL_API_KEY", "test_api_key")
        self.app = FirecrawlApp(api_key=self.api_key)
        self.test_url = "https://branfordcastle.com/*"
        # FamilyOfficeSchema.get_clean_schema())
        print('schema****=', family_office_schema)
        self.schema = FamilyOfficeSchema.get_clean_schema()

    def test_scrape_url_real_api(self):
        """Test scraping a single URL with the real API."""
        # Call the method with actual API

        params = {
            "formats": ["extract"],
            "extract": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "media_news_coverage": {
                            "type": "array",
                            "description": "Unique and complete list of every media or news coverage of this family office. Extract the COMPLETE text of each article word-for-word, not summaries. Include the exact publication date for each article.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "date": {"type": "string", "description": "The date publication of the media coverage"},
                                    "text": {"type": "string", "description": "The complete text word for word of the media item"}
                                }
                            }
                        }
                    }
                }
            }
        }
        result = self.app.scrape_url(
            "https://branfordcastle.com/media-coverage/", params)
        print('result media coverage****=', result)
        print('MEDIA LENGTH****=',
              len(result['extract']['media_news_coverage']))

        # Assertions
        self.assertIsNotNone(result)
        self.assertIn("markdown", result)
        self.assertIn("metadata", result)
        self.assertIn("title", result["metadata"])
        self.assertEqual(result["metadata"]["sourceURL"], self.test_url)

    def test_scrape_url_with_options_real_api(self):
        """Test scraping a URL with custom options using the real API."""
        # Define scrape options
        params = {
            "formats": ["extract"],
            "extract": {
                "schema": self.schema
            }
        }

        # Call with params
        result = self.app.scrape_url(self.test_url, params)

        # Assertions
        self.assertIsNotNone(result)
        self.assertIn("markdown", result)
        self.assertIn("html", result)

    def test_crawl_url_real_api(self):
        params = {
            "scrapeOptions": {
                "formats": ["extract"],
                "extract": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "media_news_coverage": {
                                "type": "array",
                                "description": "Unique and complete list of every media or news coverage of this family office. Extract the COMPLETE text of each article word-for-word, not summaries. Include the exact publication date for each article.",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "date": {"type": "string", "description": "The date publication of the media coverage"},
                                        "text": {"type": "string", "description": "The complete text word for word of the media item"}
                                    }
                                }
                            }
                        }
                    },
                    "prompt": "Extract EVERY SINGLE media or news coverage item. There should be at least 5-10 items on this page."
                }
            }
        }
        result = self.app.crawl_url(
            "https://branfordcastle.com/media-coverage/", params)
        print('result****=', result)

    def test_extract_url_real_api(self):
        """Test crawling a website with the real API."""
        # Call the method

        params__ = {
            # FamilyOfficeSchema.get_clean_schema()#simple_schema
            "schema": family_office_schema,
            "prompt": "If there a list of media items extract the complete text of each article word-for-word, not summaries. Include the exact publication date for each article.",
            'scrapeOptions': {
                'timeout': 1200000  # 30 seconds
            }
        }

        # result = self.app.crawl_url(self.test_url, params)
        result = self.app.extract(
            ["https://branfordcastle.com/*"], params__)
        print('result****=', result)
        #print('MEDIA LENGTH****=', len(result['data']['media_news_coverage']))
        # Assertions
        self.assertIsNotNone(result)
        self.assertTrue(result["success"])
        self.assertIn("id", result)
        self.assertIn("url", result)

    def test_extract_url_real_api_single_page(self):
        params = {
            # FamilyOfficeSchema.get_clean_schema()#simple_schema
            "schema": {
                "type": "object",
                "properties": {
                        "media_news_coverage": {
                            "type": "array",
                            "description": "Unique and complete list of every media or news coverage of this family office. Extract the COMPLETE text of each article word-for-word, not summaries. Include the exact publication date for each article.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "date": {"type": "string", "description": "The date publication of the media coverage"},
                                    "text": {"type": "string", "description": "The complete text word for word of the media item"}
                                }
                            }
                        }
                }
            },
            "prompt": "If there a list of media items extract the complete text of each article word-for-word, not summaries. Include the exact publication date for each article.",
            'scrapeOptions': {
                'timeout': 120000,
                'waitFor': 5000
            }
        }

        # result = self.app.crawl_url(self.test_url, params)
        result = self.app.extract([self.test_url], params)
        print('result****=', result)
        print('MEDIA LENGTH****=', len(result['data']['media_news_coverage']))

    def test_crawl_url_with_options_real_api(self):
        """Test crawling a website with custom options using the real API."""
        # Define crawl options
        params = {}

        # Call with params
        result = self.app.crawl_url(self.test_url, params)

        # Assertions
        self.assertIsNotNone(result)
        self.assertTrue(result["success"])
        self.assertIn("id", result)

    def test_check_crawl_status_real_api(self):
        """Test checking the status of a crawl job with the real API."""
        # First create a crawl job
        crawl_result = self.app.crawl_url(self.test_url, {"limit": 2})
        crawl_id = crawl_result["id"]

        # Call the method
        result = self.app.check_crawl_status(crawl_id)

        # Assertions
        self.assertIsNotNone(result)
        self.assertIn("status", result)
        # Status could be "pending", "scraping", or "completed"
        self.assertIn(result["status"], ["pending", "scraping", "completed"])
        self.assertIn("total", result)

    def test_map_url_real_api(self):
        """Test mapping a website to get all URLs using the real API."""
        # Call the method
        result = self.app.map_url(self.test_url)

        # Assertions
        self.assertIsNotNone(result)
        self.assertTrue(result["success"])
        self.assertIn("links", result)
        # Example.com should have at least one link (itself)
        self.assertGreaterEqual(len(result["links"]), 1)
        self.assertIn(self.test_url, result["links"])


if __name__ == '__main__':
    unittest.main()
