"""Zendesk Upload Agent for NOC KBU - Handles article upload to Zendesk."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import requests
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import base64
from urllib.parse import urljoin

load_dotenv()


class ZendeskArticle(BaseModel):
    """Zendesk article structure."""
    title: str
    body: str
    locale: str = "en-us"
    section_id: Optional[int] = None
    category_id: Optional[int] = None
    position: Optional[int] = None
    promoted: bool = False
    draft: bool = False
    user_segment_id: Optional[int] = None
    permission_group_id: Optional[int] = None
    label_names: Optional[List[str]] = None


class UploadResult(BaseModel):
    """Result of an individual article upload."""
    intercom_id: str
    zendesk_id: Optional[int] = None
    title: str
    status: str  # "success", "failed", "skipped"
    error_message: Optional[str] = None
    uploaded_at: Optional[str] = None


class ZendeskUploader:
    """Handles uploading approved articles to Zendesk."""
    
    def __init__(
        self,
        subdomain: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None
    ):
        self.subdomain = subdomain or os.getenv("ZENDESK_SUBDOMAIN")
        self.email = email or os.getenv("ZENDESK_EMAIL")
        self.api_token = api_token or os.getenv("ZENDESK_API_TOKEN")
        
        if not all([self.subdomain, self.email, self.api_token]):
            raise ValueError("Zendesk credentials (subdomain, email, api_token) are required")
        
        self.base_url = f"https://{self.subdomain}.zendesk.com/api/v2"
        self.input_dir = input_dir or Path("data/approved")
        self.output_dir = output_dir or Path("reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup authentication
        auth_string = f"{self.email}/token:{self.api_token}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        self.headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Rate limiting configuration
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.request_delay = float(os.getenv("REQUEST_DELAY", "1.0"))
        
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Tuple[bool, Any]:
        """Make API request with retry logic and rate limiting."""
        url = urljoin(self.base_url + "/", endpoint)
        
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.request_delay)
                
                if method.upper() == "GET":
                    response = self.session.get(url, params=params)
                elif method.upper() == "POST":
                    response = self.session.post(url, json=data, params=params)
                elif method.upper() == "PUT":
                    response = self.session.put(url, json=data, params=params)
                elif method.upper() == "DELETE":
                    response = self.session.delete(url, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                
                if response.content:
                    return True, response.json()
                else:
                    return True, None
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    return False, f"Failed after {self.max_retries} attempts: {e}"
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return False, "Request failed"
    
    def get_sections(self) -> List[Dict[str, Any]]:
        """Fetch all sections from Zendesk."""
        success, result = self._make_request("GET", "help_center/sections")
        if success and result:
            return result.get("sections", [])
        return []
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """Fetch all categories from Zendesk."""
        success, result = self._make_request("GET", "help_center/categories")
        if success and result:
            return result.get("categories", [])
        return []
    
    def create_article(self, article_data: ZendeskArticle) -> Tuple[bool, Any]:
        """Create a new article in Zendesk."""
        payload = {
            "article": {
                "title": article_data.title,
                "body": article_data.body,
                "locale": article_data.locale,
                "draft": article_data.draft,
                "promoted": article_data.promoted
            }
        }
        
        # Add optional fields if provided
        if article_data.section_id:
            payload["article"]["section_id"] = article_data.section_id
        if article_data.position:
            payload["article"]["position"] = article_data.position
        if article_data.user_segment_id:
            payload["article"]["user_segment_id"] = article_data.user_segment_id
        if article_data.permission_group_id:
            payload["article"]["permission_group_id"] = article_data.permission_group_id
        if article_data.label_names:
            payload["article"]["label_names"] = article_data.label_names
        
        endpoint = "help_center/articles"
        if article_data.section_id:
            endpoint = f"help_center/sections/{article_data.section_id}/articles"
        
        return self._make_request("POST", endpoint, payload)
    
    def transform_intercom_to_zendesk(
        self,
        intercom_article: Dict[str, Any],
        default_section_id: Optional[int] = None
    ) -> ZendeskArticle:
        """Transform Intercom article format to Zendesk format."""
        title = intercom_article.get("title", "Untitled")
        body = intercom_article.get("body", "")
        
        # Basic transformation - can be enhanced based on specific needs
        zendesk_article = ZendeskArticle(
            title=title,
            body=body,
            locale="en-us",
            section_id=default_section_id,
            draft=True,  # Start as draft for safety
            promoted=False
        )
        
        # Add labels based on Intercom metadata
        labels = []
        
        # Add migration label
        labels.append("migrated-from-intercom")
        
        # Add ID reference
        intercom_id = intercom_article.get("id")
        if intercom_id:
            labels.append(f"intercom-id-{intercom_id}")
        
        # Add author info if available
        author_id = intercom_article.get("author_id")
        if author_id:
            labels.append(f"intercom-author-{author_id}")
        
        zendesk_article.label_names = labels
        
        return zendesk_article
    
    def load_approved_articles(self, filename: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load approved articles from JSON file."""
        if filename:
            file_path = self.input_dir / filename
        else:
            # Find most recent approved file
            json_files = list(self.input_dir.glob("approved_articles_*.json"))
            if not json_files:
                raise FileNotFoundError("No approved articles found")
            file_path = max(json_files, key=lambda p: p.stat().st_mtime)
        
        print(f"Loading approved articles from {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        articles = data.get('articles', [])
        print(f"Loaded {len(articles)} approved articles")
        return articles
    
    def upload_articles(
        self,
        articles: List[Dict[str, Any]],
        default_section_id: Optional[int] = None,
        dry_run: bool = False
    ) -> List[UploadResult]:
        """Upload approved articles to Zendesk."""
        print(f"Starting upload of {len(articles)} articles (dry_run={dry_run})...")
        
        if dry_run:
            print("🔍 DRY RUN MODE - No articles will be uploaded")
        
        upload_results = []
        
        for i, article in enumerate(articles, 1):
            intercom_id = article.get("id", f"unknown_{i}")
            title = article.get("title", "Untitled")
            
            print(f"Processing article {i}/{len(articles)}: {title[:50]}...")
            
            try:
                # Transform to Zendesk format
                zendesk_article = self.transform_intercom_to_zendesk(
                    article, 
                    default_section_id
                )
                
                if dry_run:
                    # Simulate success for dry run
                    result = UploadResult(
                        intercom_id=intercom_id,
                        zendesk_id=None,
                        title=title,
                        status="success",
                        uploaded_at=datetime.now().isoformat()
                    )
                    print(f"  ✅ (DRY RUN) Would upload: {title}")
                else:
                    # Actually upload to Zendesk
                    success, response = self.create_article(zendesk_article)
                    
                    if success and response:
                        zendesk_id = response.get("article", {}).get("id")
                        result = UploadResult(
                            intercom_id=intercom_id,
                            zendesk_id=zendesk_id,
                            title=title,
                            status="success",
                            uploaded_at=datetime.now().isoformat()
                        )
                        print(f"  ✅ Uploaded successfully (Zendesk ID: {zendesk_id})")
                    else:
                        result = UploadResult(
                            intercom_id=intercom_id,
                            title=title,
                            status="failed",
                            error_message=str(response)
                        )
                        print(f"  ❌ Upload failed: {response}")
                
                upload_results.append(result)
                
            except Exception as e:
                result = UploadResult(
                    intercom_id=intercom_id,
                    title=title,
                    status="failed",
                    error_message=str(e)
                )
                upload_results.append(result)
                print(f"  ❌ Error processing article: {e}")
        
        # Summary
        successful = len([r for r in upload_results if r.status == "success"])
        failed = len([r for r in upload_results if r.status == "failed"])
        
        print(f"\n📊 Upload Summary:")
        print(f"  • Total articles: {len(upload_results)}")
        print(f"  • Successful: {successful}")
        print(f"  • Failed: {failed}")
        
        return upload_results
    
    def save_upload_report(
        self,
        upload_results: List[UploadResult],
        filename: Optional[str] = None
    ) -> Path:
        """Save upload results to JSON report."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"upload_report_{timestamp}.json"
        
        file_path = self.output_dir / filename
        
        # Compile report data
        report_data = {
            "upload_date": datetime.now().isoformat(),
            "total_articles": len(upload_results),
            "successful_uploads": len([r for r in upload_results if r.status == "success"]),
            "failed_uploads": len([r for r in upload_results if r.status == "failed"]),
            "results": [
                {
                    "intercom_id": r.intercom_id,
                    "zendesk_id": r.zendesk_id,
                    "title": r.title,
                    "status": r.status,
                    "error_message": r.error_message,
                    "uploaded_at": r.uploaded_at
                }
                for r in upload_results
            ]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved upload report to {file_path}")
        return file_path
    
    def validate_zendesk_connection(self) -> bool:
        """Test connection to Zendesk API."""
        print("Testing Zendesk API connection...")
        
        success, result = self._make_request("GET", "help_center/categories", params={"per_page": 1})
        
        if success:
            print("✅ Zendesk connection successful")
            return True
        else:
            print(f"❌ Zendesk connection failed: {result}")
            return False


def main():
    """CLI entry point for Zendesk upload."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload approved articles to Zendesk")
    parser.add_argument("--input", help="Input approved articles JSON file")
    parser.add_argument("--section-id", type=int, help="Default Zendesk section ID")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Test run without actually uploading")
    parser.add_argument("--test-connection", action="store_true",
                       help="Test Zendesk API connection only")
    parser.add_argument("--output", help="Output report filename")
    
    args = parser.parse_args()
    
    try:
        uploader = ZendeskUploader()
        
        if args.test_connection:
            uploader.validate_zendesk_connection()
            return
        
        articles = uploader.load_approved_articles(args.input)
        upload_results = uploader.upload_articles(
            articles,
            default_section_id=args.section_id,
            dry_run=args.dry_run
        )
        
        report_path = uploader.save_upload_report(upload_results, args.output)
        
        if args.dry_run:
            print(f"✅ Dry run completed successfully: {report_path}")
        else:
            successful = len([r for r in upload_results if r.status == "success"])
            total = len(upload_results)
            
            if successful == total:
                print(f"✅ Upload completed successfully: {successful}/{total} articles")
            else:
                print(f"⚠️  Upload completed with issues: {successful}/{total} successful")
            
            print(f"📄 Report saved: {report_path}")
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        raise


if __name__ == "__main__":
    main()