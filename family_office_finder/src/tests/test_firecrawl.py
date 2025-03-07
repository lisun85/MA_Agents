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
        print('schema****=', SimplifiedFamilyOfficeSchema.model_json_schema())
        self.schema = SimplifiedFamilyOfficeSchema.model_json_schema()

    def test_scrape_url_real_api(self):
        """Test scraping a single URL with the real API."""
        # Call the method with actual API

        params = {
            "formats": ["extract"],
            "extract": {
                "schema": self.schema
            }
        }
        result = self.app.scrape_url(self.test_url, params)

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
        """Test crawling a website with the real API."""
        # Call the method
        
        params__ = {
            "schema": FamilyOfficeSchema.get_clean_schema()#simple_schema
        }
        

        #result = self.app.crawl_url(self.test_url, params)
        result = self.app.extract([self.test_url], params__ )
        print('result****=', result)

        # Assertions
        self.assertIsNotNone(result)
        self.assertTrue(result["success"])
        self.assertIn("id", result)
        self.assertIn("url", result)

    def test_crawl_url_with_options_real_api(self):
        """Test crawling a website with custom options using the real API."""
        # Define crawl options
        params = {
            "scrapeOptions": {
                "formats": ["extract"],
                "extract": {
                    "schema": self.schema
                }
            }
        }

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
