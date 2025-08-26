# CLAUDE.md - NOC Knowledge Base Update Project

This file provides guidance to Claude Code when working with the NOC KBU project.

## Project Overview

NOC KBU is a Python-based migration tool for transferring articles from Intercom to Zendesk with intelligent content evaluation, duplicate detection, and quality assessment.

## Development Commands

```bash
# Setup development environment
cd /home/localadmin/noc_kbu_project/v_1_0_0/noc_kbu
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Run tests
pytest
pytest --cov=noc_kbu --cov-report=html

# Code quality checks
black .
isort .
flake8 .
mypy .

# Run individual agents for testing
python -m noc_kbu.agents.intercom_extractor --limit 10
python -m noc_kbu.agents.content_analyzer
python -m noc_kbu.agents.review_manager --generate-report
python -m noc_kbu.agents.zendesk_uploader --dry-run
```

## Architecture

### Core Components
- **agents/** - Four specialized agents for different phases
- **config/** - Configuration management and settings
- **data/** - Local storage for raw, processed, and approved content
- **tests/** - Unit and integration test suite
- **reports/** - Generated analysis and review reports

### Agent Responsibilities
1. **intercom_extractor.py** - Intercom API integration and data extraction
2. **content_analyzer.py** - Duplicate detection and content quality scoring
3. **review_manager.py** - Human review workflow and report generation
4. **zendesk_uploader.py** - Zendesk API integration and upload management

## Key Configuration Files

- **pyproject.toml** - Project metadata, dependencies, and tool configuration
- **requirements.txt** - Python package dependencies
- **.env** - API credentials and runtime configuration
- **.gitignore** - Version control exclusions

## Environment Variables

Create a `.env` file based on `.env.example`:
```bash
# API Credentials
INTERCOM_ACCESS_TOKEN=your_token_here
ZENDESK_SUBDOMAIN=your_subdomain
ZENDESK_API_TOKEN=your_token_here

# Processing Settings
SIMILARITY_THRESHOLD=0.85
BATCH_SIZE=10
QUALITY_SCORE_THRESHOLD=0.7
```

## Development Workflow

1. **Phase 1**: Small scale testing with 10-20 articles
2. **Phase 2**: Scale up to 1000+ articles after validation
3. **Local iteration**: Refine content evaluation before Zendesk upload
4. **One-time upload**: Only upload to Zendesk when collection is 100% ready

## VS Code Integration

The project is designed for VS Code development with:
- Python virtual environment support
- Integrated testing with pytest
- Code formatting with black and isort
- Type checking with mypy
- Debugging configuration for individual agents