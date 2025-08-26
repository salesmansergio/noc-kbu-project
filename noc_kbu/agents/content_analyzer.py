"""Content Analysis Agent for NOC KBU - Duplicate detection and quality assessment."""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer
from bs4 import BeautifulSoup
import html2text
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class QualityMetrics:
    """Content quality assessment metrics."""
    readability_score: float
    completeness_score: float
    freshness_score: float
    technical_accuracy_score: float
    overall_quality_score: float
    issues: List[str]


@dataclass
class SimilarityResult:
    """Similarity comparison result between two articles."""
    article_id_1: str
    article_id_2: str
    title_similarity: float
    content_similarity: float
    overall_similarity: float
    is_duplicate: bool


@dataclass
class DuplicateCluster:
    """Group of similar/duplicate articles."""
    cluster_id: str
    primary_article_id: str
    duplicate_article_ids: List[str]
    similarity_scores: List[float]
    recommended_action: str  # "merge", "keep_primary", "manual_review"


class ContentAnalyzer:
    """Analyzes article content for duplicates, quality, and other issues."""
    
    def __init__(
        self,
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        similarity_threshold: float = 0.85,
        quality_threshold: float = 0.7
    ):
        self.input_dir = input_dir or Path("data/raw")
        self.output_dir = output_dir or Path("data/processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", str(similarity_threshold)))
        self.quality_threshold = float(os.getenv("QUALITY_SCORE_THRESHOLD", str(quality_threshold)))
        
        # Initialize models
        print("Loading sentence transformer model...")
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # HTML to text converter
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = True
        self.html_converter.ignore_images = True
        
        # Content analysis parameters
        self.min_content_length = int(os.getenv("MIN_CONTENT_LENGTH", "50"))
        self.max_content_age_days = int(os.getenv("MAX_CONTENT_AGE_DAYS", "365"))
        
    def load_articles(self, filename: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load articles from JSON file."""
        if filename:
            file_path = self.input_dir / filename
        else:
            # Find most recent extraction file
            json_files = list(self.input_dir.glob("intercom_articles_*.json"))
            if not json_files:
                raise FileNotFoundError("No article files found in input directory")
            file_path = max(json_files, key=lambda p: p.stat().st_mtime)
        
        print(f"Loading articles from {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        articles = data.get('articles', [])
        print(f"Loaded {len(articles)} articles")
        return articles
    
    def extract_clean_text(self, html_content: str) -> str:
        """Convert HTML content to clean text."""
        if not html_content:
            return ""
        
        # Use BeautifulSoup for better HTML parsing
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Convert to text using html2text
        text = self.html_converter.handle(str(soup))
        
        # Clean up extra whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def calculate_content_similarity(
        self,
        articles: List[Dict[str, Any]]
    ) -> List[SimilarityResult]:
        """Calculate similarity scores between all article pairs."""
        print("Calculating content similarity...")
        
        # Extract and clean content
        article_texts = []
        article_titles = []
        article_ids = []
        
        for article in articles:
            article_id = article.get('id', '')
            title = article.get('title', '')
            body = article.get('body', '')
            
            clean_text = self.extract_clean_text(body)
            
            article_ids.append(article_id)
            article_titles.append(title)
            article_texts.append(clean_text)
        
        # Calculate title similarities using TF-IDF
        if article_titles:
            title_vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
            title_vectors = title_vectorizer.fit_transform(article_titles)
            title_similarities = cosine_similarity(title_vectors)
        else:
            title_similarities = np.zeros((len(articles), len(articles)))
        
        # Calculate content similarities using sentence transformers
        if article_texts and any(text.strip() for text in article_texts):
            content_embeddings = self.sentence_model.encode(article_texts)
            content_similarities = cosine_similarity(content_embeddings)
        else:
            content_similarities = np.zeros((len(articles), len(articles)))
        
        # Generate similarity results
        similarity_results = []
        
        for i in range(len(articles)):
            for j in range(i + 1, len(articles)):
                title_sim = title_similarities[i][j]
                content_sim = content_similarities[i][j]
                overall_sim = (title_sim * 0.3) + (content_sim * 0.7)  # Weight content more
                
                is_duplicate = overall_sim >= self.similarity_threshold
                
                result = SimilarityResult(
                    article_id_1=article_ids[i],
                    article_id_2=article_ids[j],
                    title_similarity=float(title_sim),
                    content_similarity=float(content_sim),
                    overall_similarity=float(overall_sim),
                    is_duplicate=is_duplicate
                )
                
                similarity_results.append(result)
        
        print(f"Calculated {len(similarity_results)} similarity pairs")
        return similarity_results
    
    def identify_duplicate_clusters(
        self,
        similarity_results: List[SimilarityResult]
    ) -> List[DuplicateCluster]:
        """Group articles into duplicate clusters."""
        print("Identifying duplicate clusters...")
        
        # Find all duplicates
        duplicates = [r for r in similarity_results if r.is_duplicate]
        
        if not duplicates:
            print("No duplicates found")
            return []
        
        # Build adjacency graph
        article_connections = {}
        for dup in duplicates:
            if dup.article_id_1 not in article_connections:
                article_connections[dup.article_id_1] = []
            if dup.article_id_2 not in article_connections:
                article_connections[dup.article_id_2] = []
            
            article_connections[dup.article_id_1].append((dup.article_id_2, dup.overall_similarity))
            article_connections[dup.article_id_2].append((dup.article_id_1, dup.overall_similarity))
        
        # Find connected components (clusters)
        visited = set()
        clusters = []
        
        for article_id in article_connections:
            if article_id in visited:
                continue
            
            # BFS to find all connected articles
            cluster_articles = []
            queue = [article_id]
            visited.add(article_id)
            
            while queue:
                current = queue.pop(0)
                cluster_articles.append(current)
                
                for connected_id, _ in article_connections.get(current, []):
                    if connected_id not in visited:
                        visited.add(connected_id)
                        queue.append(connected_id)
            
            if len(cluster_articles) > 1:
                # Choose primary article (could be based on creation date, views, etc.)
                primary_id = cluster_articles[0]  # Simple: first one
                duplicate_ids = cluster_articles[1:]
                
                # Get similarity scores for this cluster
                cluster_scores = []
                for dup in duplicates:
                    if (dup.article_id_1 in cluster_articles and 
                        dup.article_id_2 in cluster_articles):
                        cluster_scores.append(dup.overall_similarity)
                
                # Determine recommended action
                avg_similarity = np.mean(cluster_scores) if cluster_scores else 0.0
                if avg_similarity >= 0.95:
                    action = "keep_primary"
                elif avg_similarity >= 0.85:
                    action = "merge"
                else:
                    action = "manual_review"
                
                cluster = DuplicateCluster(
                    cluster_id=f"cluster_{len(clusters) + 1}",
                    primary_article_id=primary_id,
                    duplicate_article_ids=duplicate_ids,
                    similarity_scores=cluster_scores,
                    recommended_action=action
                )
                clusters.append(cluster)
        
        print(f"Found {len(clusters)} duplicate clusters")
        return clusters
    
    def assess_content_quality(self, article: Dict[str, Any]) -> QualityMetrics:
        """Assess the quality of an individual article."""
        title = article.get('title', '')
        body = article.get('body', '')
        created_at = article.get('created_at')
        updated_at = article.get('updated_at')
        
        clean_text = self.extract_clean_text(body)
        issues = []
        
        # Readability score (simplified)
        word_count = len(clean_text.split())
        sentence_count = len([s for s in clean_text.split('.') if s.strip()])
        
        if sentence_count > 0:
            avg_words_per_sentence = word_count / sentence_count
            readability = max(0, min(1, 1 - (avg_words_per_sentence - 15) / 30))
        else:
            readability = 0.0
            issues.append("No readable sentences found")
        
        # Completeness score
        if len(clean_text) < self.min_content_length:
            completeness = 0.0
            issues.append("Content too short")
        elif len(clean_text) < 200:
            completeness = 0.5
            issues.append("Content may be too brief")
        else:
            completeness = 1.0
        
        # Freshness score (based on last update)
        if updated_at:
            try:
                last_update = datetime.fromtimestamp(updated_at)
                days_old = (datetime.now() - last_update).days
                freshness = max(0, 1 - (days_old / self.max_content_age_days))
                
                if days_old > self.max_content_age_days:
                    issues.append("Content may be outdated")
            except (ValueError, TypeError):
                freshness = 0.5
                issues.append("Invalid update timestamp")
        else:
            freshness = 0.5
            issues.append("No update timestamp")
        
        # Technical accuracy (basic checks)
        technical_accuracy = 1.0
        
        # Check for broken patterns
        if re.search(r'<[^>]+>', clean_text):
            technical_accuracy -= 0.2
            issues.append("Contains unprocessed HTML")
        
        if 'TODO' in clean_text.upper() or 'FIXME' in clean_text.upper():
            technical_accuracy -= 0.3
            issues.append("Contains TODO/FIXME markers")
        
        if not title.strip():
            technical_accuracy -= 0.5
            issues.append("Missing or empty title")
        
        technical_accuracy = max(0, technical_accuracy)
        
        # Overall quality score (weighted average)
        overall = (
            readability * 0.2 +
            completeness * 0.3 +
            freshness * 0.2 +
            technical_accuracy * 0.3
        )
        
        return QualityMetrics(
            readability_score=readability,
            completeness_score=completeness,
            freshness_score=freshness,
            technical_accuracy_score=technical_accuracy,
            overall_quality_score=overall,
            issues=issues
        )
    
    def analyze_articles(
        self,
        articles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Complete analysis workflow for all articles."""
        print(f"Starting analysis of {len(articles)} articles...")
        
        # Calculate similarities
        similarity_results = self.calculate_content_similarity(articles)
        
        # Identify duplicate clusters
        clusters = self.identify_duplicate_clusters(similarity_results)
        
        # Assess quality for each article
        print("Assessing content quality...")
        quality_assessments = {}
        
        for article in articles:
            article_id = article.get('id', '')
            if article_id:
                quality_assessments[article_id] = self.assess_content_quality(article)
        
        # Compile analysis results
        analysis_result = {
            "analysis_date": datetime.now().isoformat(),
            "total_articles": len(articles),
            "similarity_threshold": self.similarity_threshold,
            "quality_threshold": self.quality_threshold,
            "similarity_results": [
                {
                    "article_id_1": r.article_id_1,
                    "article_id_2": r.article_id_2,
                    "title_similarity": r.title_similarity,
                    "content_similarity": r.content_similarity,
                    "overall_similarity": r.overall_similarity,
                    "is_duplicate": r.is_duplicate
                }
                for r in similarity_results
            ],
            "duplicate_clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "primary_article_id": c.primary_article_id,
                    "duplicate_article_ids": c.duplicate_article_ids,
                    "avg_similarity": np.mean(c.similarity_scores) if c.similarity_scores else 0.0,
                    "recommended_action": c.recommended_action
                }
                for c in clusters
            ],
            "quality_assessments": {
                article_id: {
                    "readability_score": qa.readability_score,
                    "completeness_score": qa.completeness_score,
                    "freshness_score": qa.freshness_score,
                    "technical_accuracy_score": qa.technical_accuracy_score,
                    "overall_quality_score": qa.overall_quality_score,
                    "issues": qa.issues,
                    "passes_threshold": qa.overall_quality_score >= self.quality_threshold
                }
                for article_id, qa in quality_assessments.items()
            }
        }
        
        # Summary statistics
        quality_scores = [qa.overall_quality_score for qa in quality_assessments.values()]
        analysis_result["summary"] = {
            "total_duplicates": len([r for r in similarity_results if r.is_duplicate]),
            "duplicate_clusters": len(clusters),
            "avg_quality_score": np.mean(quality_scores) if quality_scores else 0.0,
            "articles_passing_quality": len([s for s in quality_scores if s >= self.quality_threshold]),
            "articles_with_issues": len([qa for qa in quality_assessments.values() if qa.issues])
        }
        
        print(f"Analysis complete: {analysis_result['summary']}")
        return analysis_result
    
    def save_analysis(self, analysis_result: Dict[str, Any], filename: Optional[str] = None) -> Path:
        """Save analysis results to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"content_analysis_{timestamp}.json"
        
        file_path = self.output_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, indent=2, ensure_ascii=False)
        
        print(f"Saved analysis results to {file_path}")
        return file_path


def main():
    """CLI entry point for content analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze articles for duplicates and quality")
    parser.add_argument("--input", help="Input JSON file (default: most recent)")
    parser.add_argument("--output", help="Output filename")
    parser.add_argument("--similarity-threshold", type=float, default=0.85,
                       help="Similarity threshold for duplicates")
    parser.add_argument("--quality-threshold", type=float, default=0.7,
                       help="Quality threshold for acceptance")
    
    args = parser.parse_args()
    
    try:
        analyzer = ContentAnalyzer(
            similarity_threshold=args.similarity_threshold,
            quality_threshold=args.quality_threshold
        )
        
        articles = analyzer.load_articles(args.input)
        analysis_result = analyzer.analyze_articles(articles)
        output_path = analyzer.save_analysis(analysis_result, args.output)
        
        print(f"✅ Content analysis completed successfully: {output_path}")
        
        # Print summary
        summary = analysis_result["summary"]
        print(f"\n📊 Summary:")
        print(f"  • Total articles: {analysis_result['total_articles']}")
        print(f"  • Duplicate pairs: {summary['total_duplicates']}")
        print(f"  • Duplicate clusters: {summary['duplicate_clusters']}")
        print(f"  • Average quality: {summary['avg_quality_score']:.2f}")
        print(f"  • Quality threshold: {summary['articles_passing_quality']}/{analysis_result['total_articles']}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        raise


if __name__ == "__main__":
    main()