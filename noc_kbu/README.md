# NOC Knowledge Base Update (NOC KBU)

A Python-based migration tool to transfer articles from Intercom to Zendesk with content evaluation, duplicate detection, and quality assessment.

## Project Overview

NOC KBU facilitates the migration of knowledge base articles from Intercom to Zendesk by:
- Extracting articles via Intercom API
- Evaluating content for duplicates and quality issues
- Providing a local review workflow
- Uploading approved articles to Zendesk

## Architecture

### Subagents
- **Data Extraction Agent** (`intercom_extractor.py`) - Intercom API integration
- **Content Analysis Agent** (`content_analyzer.py`) - Duplicate detection and quality scoring
- **Review Coordination Agent** (`review_manager.py`) - Human review workflow management
- **Integration Agent** (`zendesk_uploader.py`) - Zendesk API integration

### Directory Structure
```
noc_kbu/
├── agents/                 # Core agent implementations
├── data/
│   ├── raw/               # Raw Intercom JSON responses
│   ├── processed/         # Analyzed and processed content
│   └── approved/          # Human-approved articles ready for upload
├── config/                # Configuration modules
├── tests/                 # Unit and integration tests
├── reports/               # Review reports and analysis outputs
├── pyproject.toml         # Project configuration
├── requirements.txt       # Dependencies
└── .env.example          # Environment variables template
```

## Setup

1. **Clone and navigate to project:**
   ```bash
   cd noc_kbu
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API credentials
   ```

## Usage

### Phase 1: Small Scale Testing (10-20 articles)
```bash
# Extract articles from Intercom
python -m noc_kbu.agents.intercom_extractor --limit 20

# Analyze content for duplicates and quality
python -m noc_kbu.agents.content_analyzer

# Generate review report
python -m noc_kbu.agents.review_manager --generate-report

# After manual review, upload approved articles
python -m noc_kbu.agents.zendesk_uploader --approved-only
```

### Phase 2: Full Scale Migration (1000+ articles)
```bash
# Process all articles
python -m noc_kbu.cli migrate --batch-size 100
```

## Configuration

Key environment variables in `.env`:
- `INTERCOM_ACCESS_TOKEN` - Your Intercom API token
- `ZENDESK_SUBDOMAIN` - Your Zendesk subdomain
- `ZENDESK_API_TOKEN` - Your Zendesk API token
- `SIMILARITY_THRESHOLD` - Content similarity threshold for duplicate detection (default: 0.85)

## Development

### Running Tests
```bash
pytest
```

### Code Quality
```bash
black .
isort .
flake8 .
mypy .
```

## Workflow

1. **Extract** - Pull articles from Intercom API
2. **Analyze** - Detect duplicates, assess content quality
3. **Review** - Human evaluation of flagged content
4. **Approve** - Mark articles ready for migration
5. **Upload** - Transfer approved articles to Zendesk

## Data Processing Pipeline

```
Intercom API → Raw JSON → Content Processing → Duplicate Detection → 
Quality Evaluation → Human Review → Approved Collection → Zendesk Upload
```