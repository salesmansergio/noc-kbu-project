# NOC Knowledge Base Update (NOC KBU)

A Python-based migration tool to transfer articles from Intercom to Zendesk with content evaluation, duplicate detection, and quality assessment.

## Project Overview

NOC KBU facilitates the migration of knowledge base articles from Intercom to Zendesk by:
- **Collection Discovery** - Exploring and listing available Intercom collections
- **Smart Extraction** - Filtering articles by collection or extracting all articles
- **Content Analysis** - Evaluating content for duplicates and quality issues  
- **Review Workflow** - Local human review with interactive reports
- **Controlled Upload** - Transferring only approved articles to Zendesk

### ✨ New Features

- **🎯 Collection Filtering**: Target specific collections instead of processing all articles
- **📚 Collection Discovery**: List and explore available collections before extraction
- **🔍 Smart Matching**: Exact and partial collection name matching with helpful error handling
- **⚡ Smart Processing**: Client-side filtering by collection reduces irrelevant content processing

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

### Phase 1: Small Scale Testing with Collection Filtering (10-20 articles)

#### Step 1: Discover Available Collections
Before extracting articles, you can explore available collections:

```bash
# List all available collections (CLI interface)
noc-kbu collections

# Or using the agent directly
python -m noc_kbu.agents.intercom_extractor --list-collections
```

#### Step 2: Extract Articles from Specific Collection
```bash
# Extract from a specific collection (recommended approach)
python -m noc_kbu.agents.intercom_extractor --collection "API Documentation" --limit 20

# Or using CLI interface
noc-kbu extract --collection "Getting Started" --limit 10

# Still works: Extract from all collections (original behavior)
python -m noc_kbu.agents.intercom_extractor --limit 20
```

#### Step 3: Process and Analyze
```bash
# Analyze content for duplicates and quality
python -m noc_kbu.agents.content_analyzer

# Generate review report
python -m noc_kbu.agents.review_manager --generate-report

# After manual review, upload approved articles
python -m noc_kbu.agents.zendesk_uploader --approved-only
```

### Phase 2: Full Scale Migration (1000+ articles)
```bash
# Process all articles from specific collection
noc-kbu extract --collection "Product Documentation" --limit 1000

# Or process all articles (original behavior)
python -m noc_kbu.cli migrate --batch-size 100
```

### Collection Filtering Features

**Smart Collection Matching:**
- **Exact Match**: `--collection "API Documentation"`
- **Partial Match**: `--collection "API"` (matches "API Documentation")
- **Case Insensitive**: `--collection "api"` (matches "API Documentation")

**How Collection Filtering Works:**
- Fetches all articles from Intercom API (standard `/articles` endpoint)
- Filters articles client-side based on `parent_id` and `parent_ids` fields
- Only processes articles that belong to the specified collection
- Stops fetching when the desired number of filtered articles is reached

**Error Handling:**
- Shows available collections if collection not found
- Handles ambiguous matches with helpful suggestions
- Lists all available collections for easy discovery

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

### Enhanced Workflow with Collection Filtering

1. **Discover** - List and explore available Intercom collections
2. **Extract** - Pull articles from Intercom API (all or filtered by collection)
3. **Analyze** - Detect duplicates, assess content quality
4. **Review** - Human evaluation of flagged content
5. **Approve** - Mark articles ready for migration
6. **Upload** - Transfer approved articles to Zendesk

### Workflow Commands

```bash
# 1. Discover collections
noc-kbu collections

# 2. Extract from specific collection (recommended)
noc-kbu extract --collection "API Docs" --limit 20

# 3. Analyze extracted content
noc-kbu analyze

# 4. Generate review reports
noc-kbu review --generate-report

# 5. Upload approved articles
noc-kbu upload --approved-only
```

## Data Processing Pipeline

```
Collection Discovery → Intercom API (Filtered) → Raw JSON → Content Processing → 
Duplicate Detection → Quality Evaluation → Human Review → Approved Collection → Zendesk Upload
```