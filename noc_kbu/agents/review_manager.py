"""Review Management Agent for NOC KBU - Handles human review workflow."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
import os
from dotenv import load_dotenv
import html

load_dotenv()


@dataclass
class ArticleStatus:
    """Article review status tracking."""
    article_id: str
    title: str
    status: str  # "pending", "approved", "rejected", "needs_revision"
    reviewer: Optional[str] = None
    review_date: Optional[str] = None
    comments: Optional[str] = None
    quality_score: Optional[float] = None
    issues: Optional[List[str]] = None


class ReviewManager:
    """Manages the human review workflow for article migration."""
    
    def __init__(
        self,
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        reports_dir: Optional[Path] = None
    ):
        self.input_dir = input_dir or Path("data/processed")
        self.output_dir = output_dir or Path("data/approved")
        self.reports_dir = reports_dir or Path("reports")
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self.quality_threshold = float(os.getenv("QUALITY_SCORE_THRESHOLD", "0.7"))
        
    def load_analysis_results(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Load content analysis results."""
        if filename:
            file_path = self.input_dir / filename
        else:
            # Find most recent analysis file
            json_files = list(self.input_dir.glob("content_analysis_*.json"))
            if not json_files:
                raise FileNotFoundError("No analysis results found")
            file_path = max(json_files, key=lambda p: p.stat().st_mtime)
        
        print(f"Loading analysis results from {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_original_articles(self) -> Dict[str, Dict[str, Any]]:
        """Load original articles for reference."""
        raw_files = list(Path("data/raw").glob("intercom_articles_*.json"))
        if not raw_files:
            raise FileNotFoundError("No original articles found")
        
        file_path = max(raw_files, key=lambda p: p.stat().st_mtime)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            articles = data.get('articles', [])
        
        # Create lookup dictionary
        return {article.get('id', ''): article for article in articles}
    
    def generate_review_report_html(
        self,
        analysis_results: Dict[str, Any],
        original_articles: Dict[str, Dict[str, Any]]
    ) -> str:
        """Generate comprehensive HTML review report."""
        
        # Extract data
        quality_assessments = analysis_results.get("quality_assessments", {})
        duplicate_clusters = analysis_results.get("duplicate_clusters", [])
        summary = analysis_results.get("summary", {})
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NOC KBU Review Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 6px;
            text-align: center;
        }}
        .summary-number {{
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }}
        .article-card {{
            border: 1px solid #ddd;
            border-radius: 6px;
            margin: 15px 0;
            background: #fafafa;
        }}
        .article-header {{
            background: #34495e;
            color: white;
            padding: 15px;
            font-weight: bold;
        }}
        .article-content {{
            padding: 15px;
        }}
        .quality-score {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            color: white;
            font-weight: bold;
            margin-right: 10px;
        }}
        .quality-high {{ background-color: #27ae60; }}
        .quality-medium {{ background-color: #f39c12; }}
        .quality-low {{ background-color: #e74c3c; }}
        .issue-list {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 4px;
            padding: 10px;
            margin: 10px 0;
        }}
        .duplicate-cluster {{
            background: #fff5f5;
            border: 2px solid #fab1a0;
            border-radius: 6px;
            margin: 15px 0;
            padding: 15px;
        }}
        .cluster-header {{
            font-weight: bold;
            color: #d63031;
            font-size: 1.1em;
            margin-bottom: 10px;
        }}
        .action-required {{
            background: #fff3cd;
            border-left: 4px solid #f39c12;
            padding: 10px;
            margin: 10px 0;
        }}
        .content-preview {{
            background: #f8f9fa;
            border-left: 4px solid #6c757d;
            padding: 15px;
            margin: 10px 0;
            font-family: monospace;
            font-size: 0.9em;
            white-space: pre-wrap;
            max-height: 200px;
            overflow-y: auto;
        }}
        .tabs {{
            display: flex;
            border-bottom: 1px solid #ddd;
            margin: 20px 0 10px 0;
        }}
        .tab {{
            padding: 10px 20px;
            background: #f1f2f6;
            border: 1px solid #ddd;
            border-bottom: none;
            cursor: pointer;
            margin-right: 5px;
        }}
        .tab.active {{
            background: white;
            border-bottom: 1px solid white;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
        .recommendation {{
            background: #e8f5e8;
            border: 1px solid #4caf50;
            border-radius: 4px;
            padding: 10px;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 NOC Knowledge Base Update - Review Report</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>📊 Summary</h2>
        <div class="summary-grid">
            <div class="summary-card">
                <div class="summary-number">{analysis_results.get('total_articles', 0)}</div>
                <div>Total Articles</div>
            </div>
            <div class="summary-card">
                <div class="summary-number">{summary.get('duplicate_clusters', 0)}</div>
                <div>Duplicate Clusters</div>
            </div>
            <div class="summary-card">
                <div class="summary-number">{summary.get('articles_passing_quality', 0)}</div>
                <div>Quality Threshold</div>
            </div>
            <div class="summary-card">
                <div class="summary-number">{summary.get('avg_quality_score', 0):.2f}</div>
                <div>Avg Quality Score</div>
            </div>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('duplicates')">🔄 Duplicates</div>
            <div class="tab" onclick="showTab('quality')">📋 Quality Issues</div>
            <div class="tab" onclick="showTab('all')">📑 All Articles</div>
        </div>
        
        <div id="duplicates" class="tab-content active">
            <h2>🔄 Duplicate Clusters ({len(duplicate_clusters)})</h2>
"""
        
        # Add duplicate clusters
        if duplicate_clusters:
            for cluster in duplicate_clusters:
                cluster_id = cluster.get("cluster_id", "")
                primary_id = cluster.get("primary_article_id", "")
                duplicate_ids = cluster.get("duplicate_article_ids", [])
                recommended_action = cluster.get("recommended_action", "manual_review")
                avg_similarity = cluster.get("avg_similarity", 0.0)
                
                primary_article = original_articles.get(primary_id, {})
                primary_title = primary_article.get('title', 'Unknown Title')
                
                html_content += f"""
            <div class="duplicate-cluster">
                <div class="cluster-header">{cluster_id} - Similarity: {avg_similarity:.2f}</div>
                <div class="recommendation">
                    <strong>Recommended Action:</strong> {recommended_action.replace('_', ' ').title()}
                </div>
                
                <h4>Primary Article:</h4>
                <div class="article-card">
                    <div class="article-header">
                        {html.escape(primary_title)} (ID: {primary_id})
                    </div>
                    <div class="article-content">
                        <div class="content-preview">{html.escape(primary_article.get('body', '')[:500])}...</div>
                    </div>
                </div>
                
                <h4>Duplicate Articles ({len(duplicate_ids)}):</h4>
"""
                
                for dup_id in duplicate_ids:
                    dup_article = original_articles.get(dup_id, {})
                    dup_title = dup_article.get('title', 'Unknown Title')
                    
                    html_content += f"""
                <div class="article-card">
                    <div class="article-header">
                        {html.escape(dup_title)} (ID: {dup_id})
                    </div>
                    <div class="article-content">
                        <div class="content-preview">{html.escape(dup_article.get('body', '')[:500])}...</div>
                    </div>
                </div>
"""
                
                html_content += "</div>"
        else:
            html_content += "<p>✅ No duplicate clusters found.</p>"
        
        html_content += """
        </div>
        
        <div id="quality" class="tab-content">
            <h2>📋 Quality Issues</h2>
"""
        
        # Add quality issues
        quality_issues = [
            (article_id, qa) for article_id, qa in quality_assessments.items()
            if qa.get('issues', []) or not qa.get('passes_threshold', True)
        ]
        
        if quality_issues:
            for article_id, qa in quality_issues:
                article = original_articles.get(article_id, {})
                title = article.get('title', 'Unknown Title')
                overall_score = qa.get('overall_quality_score', 0.0)
                issues = qa.get('issues', [])
                passes_threshold = qa.get('passes_threshold', False)
                
                score_class = "quality-high" if overall_score >= 0.8 else "quality-medium" if overall_score >= 0.6 else "quality-low"
                
                html_content += f"""
            <div class="article-card">
                <div class="article-header">
                    <span class="quality-score {score_class}">{overall_score:.2f}</span>
                    {html.escape(title)} (ID: {article_id})
                    {'❌ Below Threshold' if not passes_threshold else ''}
                </div>
                <div class="article-content">
"""
                
                if issues:
                    html_content += '<div class="issue-list"><strong>Issues:</strong><ul>'
                    for issue in issues:
                        html_content += f'<li>{html.escape(issue)}</li>'
                    html_content += '</ul></div>'
                
                # Add quality breakdowns
                html_content += f"""
                    <p><strong>Quality Breakdown:</strong></p>
                    <ul>
                        <li>Readability: {qa.get('readability_score', 0.0):.2f}</li>
                        <li>Completeness: {qa.get('completeness_score', 0.0):.2f}</li>
                        <li>Freshness: {qa.get('freshness_score', 0.0):.2f}</li>
                        <li>Technical Accuracy: {qa.get('technical_accuracy_score', 0.0):.2f}</li>
                    </ul>
                    <div class="content-preview">{html.escape(article.get('body', '')[:500])}...</div>
                </div>
            </div>
"""
        else:
            html_content += "<p>✅ No quality issues found.</p>"
        
        html_content += """
        </div>
        
        <div id="all" class="tab-content">
            <h2>📑 All Articles</h2>
"""
        
        # Add all articles summary
        for article_id, qa in quality_assessments.items():
            article = original_articles.get(article_id, {})
            title = article.get('title', 'Unknown Title')
            overall_score = qa.get('overall_quality_score', 0.0)
            passes_threshold = qa.get('passes_threshold', False)
            
            score_class = "quality-high" if overall_score >= 0.8 else "quality-medium" if overall_score >= 0.6 else "quality-low"
            
            html_content += f"""
            <div class="article-card">
                <div class="article-header">
                    <span class="quality-score {score_class}">{overall_score:.2f}</span>
                    {html.escape(title)} (ID: {article_id})
                    {'✅ Approved' if passes_threshold else '⚠️ Review Required'}
                </div>
            </div>
"""
        
        html_content += """
        </div>
        
        <script>
            function showTab(tabName) {
                // Hide all tab contents
                var contents = document.querySelectorAll('.tab-content');
                contents.forEach(function(content) {
                    content.classList.remove('active');
                });
                
                // Remove active class from all tabs
                var tabs = document.querySelectorAll('.tab');
                tabs.forEach(function(tab) {
                    tab.classList.remove('active');
                });
                
                // Show selected tab content
                document.getElementById(tabName).classList.add('active');
                
                // Mark selected tab as active
                event.target.classList.add('active');
            }
        </script>
    </div>
</body>
</html>
"""
        
        return html_content
    
    def generate_review_report(
        self,
        analysis_filename: Optional[str] = None,
        output_filename: Optional[str] = None
    ) -> Path:
        """Generate HTML review report."""
        print("Generating review report...")
        
        # Load data
        analysis_results = self.load_analysis_results(analysis_filename)
        original_articles = self.load_original_articles()
        
        # Generate HTML
        html_content = self.generate_review_report_html(analysis_results, original_articles)
        
        # Save report
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"review_report_{timestamp}.html"
        
        report_path = self.reports_dir / output_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Review report saved to {report_path}")
        return report_path
    
    def auto_approve_articles(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Automatically approve articles that meet quality threshold and have no duplicates."""
        quality_assessments = analysis_results.get("quality_assessments", {})
        duplicate_clusters = analysis_results.get("duplicate_clusters", [])
        
        # Get IDs of articles in duplicate clusters
        duplicate_article_ids = set()
        for cluster in duplicate_clusters:
            duplicate_article_ids.add(cluster.get("primary_article_id", ""))
            duplicate_article_ids.update(cluster.get("duplicate_article_ids", []))
        
        # Load original articles
        original_articles = self.load_original_articles()
        
        # Auto-approve articles
        auto_approved = []
        
        for article_id, qa in quality_assessments.items():
            passes_threshold = qa.get('passes_threshold', False)
            has_issues = bool(qa.get('issues', []))
            
            if (passes_threshold and 
                not has_issues and 
                article_id not in duplicate_article_ids and
                article_id in original_articles):
                
                auto_approved.append(original_articles[article_id])
        
        print(f"Auto-approved {len(auto_approved)} articles")
        return auto_approved
    
    def save_approved_articles(
        self,
        approved_articles: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> Path:
        """Save approved articles for upload."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"approved_articles_{timestamp}.json"
        
        file_path = self.output_dir / filename
        
        # Compile approved data
        approved_data = {
            "approval_date": datetime.now().isoformat(),
            "total_approved": len(approved_articles),
            "articles": approved_articles
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(approved_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(approved_articles)} approved articles to {file_path}")
        return file_path


def main():
    """CLI entry point for review management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate review reports and manage approvals")
    parser.add_argument("--generate-report", action="store_true",
                       help="Generate HTML review report")
    parser.add_argument("--auto-approve", action="store_true",
                       help="Auto-approve qualifying articles")
    parser.add_argument("--analysis-file", help="Analysis results file to use")
    parser.add_argument("--output", help="Output filename")
    
    args = parser.parse_args()
    
    try:
        manager = ReviewManager()
        
        if args.generate_report:
            report_path = manager.generate_review_report(
                analysis_filename=args.analysis_file,
                output_filename=args.output
            )
            print(f"✅ Review report generated: {report_path}")
            print(f"📂 Open in browser: file://{report_path.absolute()}")
        
        if args.auto_approve:
            analysis_results = manager.load_analysis_results(args.analysis_file)
            approved_articles = manager.auto_approve_articles(analysis_results)
            approved_path = manager.save_approved_articles(approved_articles, args.output)
            print(f"✅ Auto-approved articles saved: {approved_path}")
        
        if not args.generate_report and not args.auto_approve:
            print("Please specify --generate-report or --auto-approve")
    
    except Exception as e:
        print(f"❌ Review management failed: {e}")
        raise


if __name__ == "__main__":
    main()