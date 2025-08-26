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


class IntercomCollection(BaseModel):
    """Structured representation of an Intercom collection."""
    id: str
    workspace_id: str
    name: str
    description: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    url: Optional[str] = None
    icon: Optional[str] = None
    order: Optional[int] = None
    help_center_id: Optional[str] = None
    parent_id: Optional[str] = None
    parent_type: Optional[str] = None
    type: str = "collection"  # Always "collection" according to API


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
    
    def list_collections(self, page_size: int = 50) -> List[Dict[str, Any]]:
        """Fetch all collections from Intercom with pagination."""
        collections = []
        url = f"{self.base_url}/help_center/collections"
        params = {"per_page": page_size}
        
        print(f"Starting collection extraction from Intercom...")
        
        while url:
            print(f"Fetching collections page... (current count: {len(collections)})")
            
            response_data = self._make_request(url, params)
            page_collections = response_data.get("data", [])
            
            if not page_collections:
                break
                
            collections.extend(page_collections)
            
            # Get next page URL
            pages = response_data.get("pages", {})
            url = pages.get("next")
            params = None  # Next URL includes all parameters
        
        print(f"Extracted {len(collections)} collections from Intercom")
        return collections
    
    def find_collection_by_name(self, collection_name: str) -> Optional[str]:
        """Find collection ID by name (case-insensitive partial match)."""
        collections = self.list_collections()
        
        # Try exact match first
        for collection in collections:
            if collection.get("name", "").lower() == collection_name.lower():
                print(f"Found exact collection match: '{collection['name']}' (ID: {collection['id']})")
                return collection["id"]
        
        # Try partial match
        matches = []
        for collection in collections:
            if collection_name.lower() in collection.get("name", "").lower():
                matches.append(collection)
        
        if len(matches) == 1:
            collection = matches[0]
            print(f"Found collection match: '{collection['name']}' (ID: {collection['id']})")
            return collection["id"]
        elif len(matches) > 1:
            print(f"Multiple collections found matching '{collection_name}':")
            for collection in matches:
                print(f"  - {collection['name']} (ID: {collection['id']})")
            raise Exception(f"Ambiguous collection name '{collection_name}'. Please be more specific.")
        
        print(f"No collection found matching '{collection_name}'")
        print("Available collections:")
        for collection in collections:
            print(f"  - {collection.get('name', 'Unnamed')} (ID: {collection['id']})")
        return None
    
    def list_articles_by_collection(self, collection_id: str, page_size: int = 50, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch articles from a specific collection using optimized search approach."""
        print(f"Starting article extraction from collection {collection_id}...")
        
        # Convert collection_id to int for comparison
        try:
            collection_id_int = int(collection_id)
        except ValueError:
            print(f"Invalid collection ID format: {collection_id}")
            return []
        
        # Try to get collection name for potential search optimization
        collection_name = None
        try:
            collections = self.list_collections()
            for collection in collections:
                if collection.get("id") == collection_id:
                    collection_name = collection.get("name")
                    break
        except Exception:
            pass  # Fallback to original method if collections fetch fails
        
        # Method 1: Try search API with collection name (if available)
        if collection_name and len(collection_name.split()) <= 3:  # Simple collection names work better with search
            print(f"Attempting optimized search for collection name: '{collection_name}'")
            search_results = self._search_articles_by_phrase(collection_name, limit=limit*3)  # Get more results to filter
            
            # Filter search results by actual parent_id
            filtered_from_search = []
            for article in search_results:
                parent_id = article.get("parent_id")
                parent_ids = article.get("parent_ids", [])
                
                # Convert to int for comparison
                if parent_id is not None:
                    try:
                        parent_id = int(parent_id)
                    except (ValueError, TypeError):
                        parent_id = None
                
                if parent_ids:
                    try:
                        parent_ids = [int(pid) for pid in parent_ids if pid is not None]
                    except (ValueError, TypeError):
                        parent_ids = []
                
                # Check if matches our target collection
                if (parent_id == collection_id_int or collection_id_int in parent_ids):
                    filtered_from_search.append(article)
                    if limit and len(filtered_from_search) >= limit:
                        break
            
            if filtered_from_search:
                print(f"Search method found {len(filtered_from_search)} articles efficiently")
                return filtered_from_search[:limit] if limit else filtered_from_search
            else:
                print("Search method didn't find articles, falling back to full scan...")
        
        # Method 2: Fallback to original filtering method with early stopping
        print("Using full scan with early stopping optimization...")
        filtered_articles = []
        url = f"{self.base_url}/articles"
        params = {"per_page": page_size}
        total_fetched = 0
        pages_scanned = 0
        max_pages_without_results = 5  # Stop if no results found in 5 consecutive pages
        pages_without_results = 0
        
        while url and (limit is None or len(filtered_articles) < limit):
            print(f"Fetching page {pages_scanned + 1}... (total fetched: {total_fetched}, filtered: {len(filtered_articles)})")
            
            response_data = self._make_request(url, params)
            page_articles = response_data.get("data", [])
            
            if not page_articles:
                break
            
            total_fetched += len(page_articles)
            pages_scanned += 1
            found_in_page = 0
            
            # Filter articles that belong to this collection
            for article in page_articles:
                parent_id = article.get("parent_id")
                parent_ids = article.get("parent_ids", [])
                
                # Convert parent_id to int if it exists
                if parent_id is not None:
                    try:
                        parent_id = int(parent_id)
                    except (ValueError, TypeError):
                        parent_id = None
                
                # Convert parent_ids to integers
                if parent_ids:
                    try:
                        parent_ids = [int(pid) for pid in parent_ids if pid is not None]
                    except (ValueError, TypeError):
                        parent_ids = []
                
                # Check if collection_id matches parent_id or is in parent_ids
                if (parent_id == collection_id_int or collection_id_int in parent_ids):
                    filtered_articles.append(article)
                    found_in_page += 1
                    
                    # Stop if we've reached the limit
                    if limit and len(filtered_articles) >= limit:
                        break
            
            # Early stopping logic for sparse collections
            if found_in_page == 0:
                pages_without_results += 1
                if pages_without_results >= max_pages_without_results:
                    print(f"Early stopping: No results found in {max_pages_without_results} consecutive pages")
                    break
            else:
                pages_without_results = 0  # Reset counter if we found results
            
            # Break if we've reached the limit
            if limit and len(filtered_articles) >= limit:
                filtered_articles = filtered_articles[:limit]
                break
            
            # Get next page URL
            pages = response_data.get("pages", {})
            url = pages.get("next")
            params = None  # Next URL includes all parameters
        
        print(f"Filtered {len(filtered_articles)} articles from collection {collection_id} (scanned {total_fetched} total articles)")
        return filtered_articles
    
    def _search_articles_by_phrase(self, phrase: str, limit: Optional[int] = None, state: str = "published") -> List[Dict[str, Any]]:
        """Search articles using Intercom search API."""
        articles = []
        url = f"{self.base_url}/articles/search"
        params = {
            "phrase": phrase,
            "state": state,
            "per_page": min(50, limit) if limit else 50
        }
        
        try:
            response_data = self._make_request(url, params)
            search_data = response_data.get("data", {})
            articles = search_data.get("articles", [])
            
            print(f"Search API found {len(articles)} articles for phrase '{phrase}'")
            return articles[:limit] if limit else articles
            
        except Exception as e:
            print(f"Search API failed: {e}")
            return []
    
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
        collection_name: Optional[str] = None,
        enrich_details: bool = True,
        filename: Optional[str] = None
    ) -> Path:
        """Complete extraction workflow: fetch, enrich, validate, and save."""
        # Fetch article list - either from specific collection or all articles
        if collection_name:
            collection_id = self.find_collection_by_name(collection_name)
            if not collection_id:
                raise Exception(f"Collection '{collection_name}' not found")
            articles = self.list_articles_by_collection(collection_id, limit=limit)
        else:
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
    parser.add_argument("--collection", type=str, help="Filter articles by collection name (exact or partial match)")
    parser.add_argument("--list-collections", action="store_true", help="List all available collections and exit")
    parser.add_argument("--no-details", action="store_true", help="Skip detailed content enrichment")
    parser.add_argument("--output", help="Output filename")
    
    args = parser.parse_args()
    
    try:
        extractor = IntercomExtractor()
        
        # Handle list collections command
        if args.list_collections:
            print("📚 Available Collections:")
            print("=" * 50)
            collections = extractor.list_collections()
            if not collections:
                print("No collections found.")
                return
            
            for collection in collections:
                print(f"• {collection.get('name', 'Unnamed')} (ID: {collection['id']})")
                if collection.get('description'):
                    print(f"  Description: {collection['description']}")
                print()
            
            print(f"Total: {len(collections)} collections found.")
            print("\nTo extract from a specific collection, use:")
            print("python -m noc_kbu.agents.intercom_extractor --collection \"<collection_name>\" --limit <number>")
            return
        
        # Handle article extraction
        file_path = extractor.extract_and_save(
            limit=args.limit,
            collection_name=args.collection,
            enrich_details=not args.no_details,
            filename=args.output
        )
        print(f"✅ Extraction completed successfully: {file_path}")
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        raise


if __name__ == "__main__":
    main()