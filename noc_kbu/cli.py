"""CLI interface for NOC Knowledge Base Update project."""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from datetime import datetime

from noc_kbu.config.settings import get_settings
from noc_kbu.agents.intercom_extractor import IntercomExtractor
from noc_kbu.agents.content_analyzer import ContentAnalyzer
from noc_kbu.agents.review_manager import ReviewManager
from noc_kbu.agents.zendesk_uploader import ZendeskUploader

console = Console()


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.pass_context
def cli(ctx, debug):
    """NOC Knowledge Base Update - Migrate articles from Intercom to Zendesk."""
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    
    if debug:
        console.print("🐛 Debug mode enabled", style="yellow")


@cli.command()
@click.option('--limit', type=int, help='Maximum number of articles to extract')
@click.option('--no-details', is_flag=True, help='Skip detailed content enrichment')
@click.option('--output', help='Output filename')
@click.pass_context
def extract(ctx, limit, no_details, output):
    """Extract articles from Intercom API."""
    console.print("🔍 Starting Intercom extraction...", style="blue")
    
    try:
        settings = get_settings()
        extractor = IntercomExtractor(
            output_dir=settings.paths.raw_data_path
        )
        
        file_path = extractor.extract_and_save(
            limit=limit,
            enrich_details=not no_details,
            filename=output
        )
        
        console.print(f"✅ Extraction completed: [green]{file_path}[/green]")
        
    except Exception as e:
        console.print(f"❌ Extraction failed: [red]{e}[/red]")
        if ctx.obj.get('debug'):
            raise


@cli.command()
@click.option('--input', help='Input JSON file (default: most recent)')
@click.option('--output', help='Output filename')
@click.option('--similarity-threshold', type=float, default=0.85, help='Similarity threshold')
@click.option('--quality-threshold', type=float, default=0.7, help='Quality threshold')
@click.pass_context
def analyze(ctx, input, output, similarity_threshold, quality_threshold):
    """Analyze articles for duplicates and quality issues."""
    console.print("🔎 Starting content analysis...", style="blue")
    
    try:
        settings = get_settings()
        analyzer = ContentAnalyzer(
            input_dir=settings.paths.raw_data_path,
            output_dir=settings.paths.processed_data_path,
            similarity_threshold=similarity_threshold,
            quality_threshold=quality_threshold
        )
        
        articles = analyzer.load_articles(input)
        analysis_result = analyzer.analyze_articles(articles)
        output_path = analyzer.save_analysis(analysis_result, output)
        
        # Display summary
        summary = analysis_result["summary"]
        
        table = Table(title="📊 Analysis Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Total Articles", str(analysis_result['total_articles']))
        table.add_row("Duplicate Pairs", str(summary['total_duplicates']))
        table.add_row("Duplicate Clusters", str(summary['duplicate_clusters']))
        table.add_row("Average Quality", f"{summary['avg_quality_score']:.2f}")
        table.add_row("Quality Threshold", f"{summary['articles_passing_quality']}/{analysis_result['total_articles']}")
        table.add_row("Articles with Issues", str(summary['articles_with_issues']))
        
        console.print(table)
        console.print(f"✅ Analysis completed: [green]{output_path}[/green]")
        
    except Exception as e:
        console.print(f"❌ Analysis failed: [red]{e}[/red]")
        if ctx.obj.get('debug'):
            raise


@cli.command()
@click.option('--analysis-file', help='Analysis results file')
@click.option('--output', help='Output filename')
@click.option('--auto-approve', is_flag=True, help='Auto-approve qualifying articles')
@click.pass_context
def review(ctx, analysis_file, output, auto_approve):
    """Generate review report and manage approvals."""
    console.print("📋 Starting review process...", style="blue")
    
    try:
        settings = get_settings()
        manager = ReviewManager(
            input_dir=settings.paths.processed_data_path,
            output_dir=settings.paths.approved_data_path,
            reports_dir=settings.paths.reports_path
        )
        
        # Generate review report
        report_path = manager.generate_review_report(
            analysis_filename=analysis_file,
            output_filename=output
        )
        
        console.print(f"✅ Review report generated: [green]{report_path}[/green]")
        console.print(f"📂 Open in browser: [link]file://{report_path.absolute()}[/link]")
        
        # Auto-approve if requested
        if auto_approve:
            analysis_results = manager.load_analysis_results(analysis_file)
            approved_articles = manager.auto_approve_articles(analysis_results)
            
            if approved_articles:
                approved_path = manager.save_approved_articles(approved_articles)
                console.print(f"✅ Auto-approved {len(approved_articles)} articles: [green]{approved_path}[/green]")
            else:
                console.print("ℹ️ No articles qualified for auto-approval")
        
    except Exception as e:
        console.print(f"❌ Review process failed: [red]{e}[/red]")
        if ctx.obj.get('debug'):
            raise


@cli.command()
@click.option('--input', help='Approved articles file')
@click.option('--section-id', type=int, help='Default Zendesk section ID')
@click.option('--dry-run', is_flag=True, help='Test run without uploading')
@click.option('--test-connection', is_flag=True, help='Test Zendesk connection only')
@click.option('--output', help='Upload report filename')
@click.pass_context
def upload(ctx, input, section_id, dry_run, test_connection, output):
    """Upload approved articles to Zendesk."""
    if dry_run:
        console.print("🔍 Starting dry run upload...", style="yellow")
    else:
        console.print("🚀 Starting Zendesk upload...", style="blue")
    
    try:
        settings = get_settings()
        uploader = ZendeskUploader(
            input_dir=settings.paths.approved_data_path,
            output_dir=settings.paths.reports_path
        )
        
        if test_connection:
            uploader.validate_zendesk_connection()
            return
        
        articles = uploader.load_approved_articles(input)
        upload_results = uploader.upload_articles(
            articles,
            default_section_id=section_id,
            dry_run=dry_run
        )
        
        report_path = uploader.save_upload_report(upload_results, output)
        
        # Display summary
        successful = len([r for r in upload_results if r.status == "success"])
        failed = len([r for r in upload_results if r.status == "failed"])
        
        table = Table(title="📤 Upload Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Total Articles", str(len(upload_results)))
        table.add_row("Successful", str(successful))
        table.add_row("Failed", str(failed))
        
        if dry_run:
            table.add_row("Mode", "DRY RUN")
        
        console.print(table)
        
        if successful == len(upload_results):
            console.print(f"✅ Upload completed successfully: [green]{report_path}[/green]")
        else:
            console.print(f"⚠️  Upload completed with issues: [yellow]{report_path}[/yellow]")
            
    except Exception as e:
        console.print(f"❌ Upload failed: [red]{e}[/red]")
        if ctx.obj.get('debug'):
            raise


@cli.command()
@click.option('--limit', type=int, help='Maximum number of articles for initial test')
@click.option('--batch-size', type=int, default=10, help='Batch size for processing')
@click.option('--dry-run', is_flag=True, help='Dry run without uploading to Zendesk')
@click.option('--section-id', type=int, help='Default Zendesk section ID')
@click.pass_context
def migrate(ctx, limit, batch_size, dry_run, section_id):
    """Complete migration workflow: extract → analyze → review → upload."""
    console.print("🚀 Starting complete migration workflow...", style="blue bold")
    
    start_time = datetime.now()
    
    try:
        settings = get_settings()
        
        # Step 1: Extract
        console.print("\n📥 Step 1: Extracting from Intercom...")
        extractor = IntercomExtractor(output_dir=settings.paths.raw_data_path)
        extraction_file = extractor.extract_and_save(limit=limit)
        console.print(f"✅ Extracted to: {extraction_file}")
        
        # Step 2: Analyze
        console.print("\n🔍 Step 2: Analyzing content...")
        analyzer = ContentAnalyzer(
            input_dir=settings.paths.raw_data_path,
            output_dir=settings.paths.processed_data_path
        )
        articles = analyzer.load_articles()
        analysis_result = analyzer.analyze_articles(articles)
        analysis_file = analyzer.save_analysis(analysis_result)
        console.print(f"✅ Analysis saved to: {analysis_file}")
        
        # Step 3: Review (generate report + auto-approve)
        console.print("\n📋 Step 3: Review process...")
        manager = ReviewManager(
            input_dir=settings.paths.processed_data_path,
            output_dir=settings.paths.approved_data_path,
            reports_dir=settings.paths.reports_path
        )
        
        # Generate report
        report_path = manager.generate_review_report()
        console.print(f"✅ Review report: {report_path}")
        
        # Auto-approve
        approved_articles = manager.auto_approve_articles(analysis_result)
        if approved_articles:
            approved_file = manager.save_approved_articles(approved_articles)
            console.print(f"✅ Auto-approved {len(approved_articles)} articles: {approved_file}")
            
            # Step 4: Upload (if not dry run)
            console.print(f"\n🚀 Step 4: {'Dry run upload' if dry_run else 'Uploading to Zendesk'}...")
            uploader = ZendeskUploader(
                input_dir=settings.paths.approved_data_path,
                output_dir=settings.paths.reports_path
            )
            
            upload_results = uploader.upload_articles(
                approved_articles,
                default_section_id=section_id,
                dry_run=dry_run
            )
            
            upload_report = uploader.save_upload_report(upload_results)
            console.print(f"✅ Upload report: {upload_report}")
        else:
            console.print("ℹ️ No articles qualified for auto-approval")
            console.print(f"👀 Please review manually: {report_path}")
        
        # Summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        console.print(f"\n🎉 Migration workflow completed in {duration}")
        console.print(f"📂 Review report: [link]file://{report_path.absolute()}[/link]")
        
    except Exception as e:
        console.print(f"❌ Migration workflow failed: [red]{e}[/red]")
        if ctx.obj.get('debug'):
            raise


@cli.command()
def status():
    """Show current project status and configuration."""
    settings = get_settings()
    
    console.print("📊 NOC KBU Project Status", style="blue bold")
    
    # Configuration status
    config_table = Table(title="🔧 Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="white")
    
    config_table.add_row("Similarity Threshold", f"{settings.processing.similarity_threshold}")
    config_table.add_row("Quality Threshold", f"{settings.processing.quality_threshold}")
    config_table.add_row("Batch Size", f"{settings.processing.batch_size}")
    config_table.add_row("Max Retries", f"{settings.processing.max_retries}")
    
    console.print(config_table)
    
    # Directory status
    dir_table = Table(title="📁 Directories")
    dir_table.add_column("Directory", style="cyan")
    dir_table.add_column("Path", style="white")
    dir_table.add_column("Exists", style="green")
    
    directories = [
        ("Raw Data", settings.paths.raw_data_path),
        ("Processed Data", settings.paths.processed_data_path),
        ("Approved Data", settings.paths.approved_data_path),
        ("Reports", settings.paths.reports_path)
    ]
    
    for name, path in directories:
        exists = "✅" if path.exists() else "❌"
        dir_table.add_row(name, str(path), exists)
    
    console.print(dir_table)
    
    # File counts
    file_table = Table(title="📄 File Counts")
    file_table.add_column("Type", style="cyan")
    file_table.add_column("Count", style="white")
    
    raw_files = len(list(settings.paths.raw_data_path.glob("*.json")))
    processed_files = len(list(settings.paths.processed_data_path.glob("*.json")))
    approved_files = len(list(settings.paths.approved_data_path.glob("*.json")))
    reports = len(list(settings.paths.reports_path.glob("*.html")))
    
    file_table.add_row("Raw Articles", str(raw_files))
    file_table.add_row("Analysis Results", str(processed_files))
    file_table.add_row("Approved Articles", str(approved_files))
    file_table.add_row("Review Reports", str(reports))
    
    console.print(file_table)


def main():
    """Main CLI entry point."""
    cli()


if __name__ == "__main__":
    main()