"""Intercom Data Extraction Agent for NOC KBU."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()


class IntercomArticle(BaseModel):
    """Structured representation of an Intercom article."""
    id: str
    title: str
    body: Optional[str] = None  # Can be null according to API docs
    workspace_id: str
    description: Optional[str] = None
    url: Optional[str] = None
    author_id: Optional[int] = None  # Integer, not string
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    state: Optional[str] = None
    parent_id: Optional[int] = None  # Integer, not string  
    parent_ids: Optional[List[int]] = None  # Array of parent IDs
    parent_type: Optional[str] = None
    default_locale: Optional[str] = None
    type: str = "article"  # Always "article" according to API


class IntercomExtractor:
    """Handles extraction of articles from Intercom API."""
    
    def __init__(
        self,
        access_token: Optional[str] = None,
        base_url: Optional[str] = None,
        output_dir: Optional[Path] = None
    ):
        self.access_token = access_token or os.getenv("INTERCOM_ACCESS_TOKEN")
        self.base_url = base_url or os.getenv("INTERCOM_API_BASE_URL", "https://api.intercom.io")
        self.output_dir = output_dir or Path("data/raw")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.access_token:
            raise ValueError("Intercom access token is required")
        
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Rate limiting configuration
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.request_delay = float(os.getenv("REQUEST_DELAY", "1.0"))
        
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request with retry logic and rate limiting."""
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.request_delay)
                response = self.session.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise Exception(f"Failed to fetch from {url} after {self.max_retries} attempts: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
        
    def list_articles(self, page_size: int = 50, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch all articles from Intercom with pagination."""
        articles = []
        url = f"{self.base_url}/articles"
        params = {"per_page": page_size}
        
        print(f"Starting article extraction from Intercom...")
        
        while url and (limit is None or len(articles) < limit):
            print(f"Fetching page... (current count: {len(articles)})")
            
            response_data = self._make_request(url, params)
            page_articles = response_data.get("data", [])
            
            if not page_articles:
                break
                
            articles.extend(page_articles)
            
            if limit and len(articles) >= limit:
                articles = articles[:limit]
                break
            
            # Get next page URL
            pages = response_data.get("pages", {})
            url = pages.get("next")
            params = None  # Next URL includes all parameters
        
        print(f"Extracted {len(articles)} articles from Intercom")
        return articles
    
    def get_article_details(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a specific article."""
        url = f"{self.base_url}/articles/{article_id}"
        try:
            return self._make_request(url)
        except Exception as e:
            print(f"Failed to fetch article {article_id}: {e}")
            return None
    
    def enrich_articles_with_details(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich article list with detailed content from individual API calls."""
        enriched_articles = []
        total = len(articles)
        
        print(f"Enriching {total} articles with detailed content...")
        
        for i, article in enumerate(articles, 1):
            article_id = article.get("id")
            if not article_id:
                print(f"Skipping article without ID: {article}")
                continue
            
            print(f"Fetching details for article {i}/{total}: {article_id}")
            detailed_article = self.get_article_details(article_id)
            
            if detailed_article:
                enriched_articles.append(detailed_article)
            else:
                enriched_articles.append(article)
        
        return enriched_articles
    
    def validate_article(self, article: Dict[str, Any]) -> Optional[IntercomArticle]:
        """Validate and parse article data."""
        try:
            return IntercomArticle(**article)
        except Exception as e:
            print(f"Invalid article data: {e}")
            return None
    
    def save_articles(self, articles: List[Dict[str, Any]], filename: Optional[str] = None) -> Path:
        """Save articles to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"intercom_articles_{timestamp}.json"
        
        file_path = self.output_dir / filename
        
        # Add extraction metadata
        data = {
            "extraction_date": datetime.now().isoformat(),
            "total_articles": len(articles),
            "source": "intercom",
            "articles": articles
        }
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(articles)} articles to {file_path}")
        return file_path
    
    def extract_and_save(
        self,
        limit: Optional[int] = None,
        enrich_details: bool = True,
        filename: Optional[str] = None
    ) -> Path:
        """Complete extraction workflow: fetch, enrich, validate, and save."""
        # Fetch article list
        articles = self.list_articles(limit=limit)
        
        if not articles:
            raise Exception("No articles found")
        
        # Enrich with detailed content if requested
        if enrich_details:
            articles = self.enrich_articles_with_details(articles)
        
        # Validate articles
        valid_articles = []
        for article in articles:
            validated = self.validate_article(article)
            if validated:
                valid_articles.append(article)
        
        print(f"Validated {len(valid_articles)} out of {len(articles)} articles")
        
        # Save to file
        return self.save_articles(valid_articles, filename)


def main():
    """CLI entry point for Intercom extraction."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract articles from Intercom")
    parser.add_argument("--limit", type=int, help="Maximum number of articles to extract")
    parser.add_argument("--no-details", action="store_true", help="Skip detailed content enrichment")
    parser.add_argument("--output", help="Output filename")
    
    args = parser.parse_args()
    
    try:
        extractor = IntercomExtractor()
        file_path = extractor.extract_and_save(
            limit=args.limit,
            enrich_details=not args.no_details,
            filename=args.output
        )
        print(f"✅ Extraction completed successfully: {file_path}")
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        raise


if __name__ == "__main__":
    main()