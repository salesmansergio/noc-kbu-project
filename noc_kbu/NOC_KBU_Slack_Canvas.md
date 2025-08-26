# NOC Knowledge Base Update (NOC KBU) - Project Canvas

## 📋 Project Overview

**Mission:** Migrate articles from Intercom to Zendesk with intelligent content evaluation, duplicate detection, and quality assessment.

**Status:** ✅ Ready for Development  
**Team:** NOC Engineering  
**Timeline:** Phase 1 (10-20 articles) → Phase 2 (1000+ articles)  

---

## 🎯 Key Objectives

- [x] **Extract** articles from Intercom API with rate limiting
- [x] **Analyze** content for duplicates using AI similarity detection
- [x] **Evaluate** article quality (readability, freshness, completeness)
- [x] **Review** flagged content through human workflow
- [x] **Upload** approved articles to Zendesk with error handling

---

## 🏗️ System Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Intercom   │ → │  Content    │ → │   Review    │ → │   Zendesk   │
│ Extractor   │   │  Analyzer   │   │  Manager    │   │  Uploader   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                   │                   │                   │
      ▼                   ▼                   ▼                   ▼
  Raw JSON         Similarity &         HTML Reports      Upload Reports
  Articles         Quality Scores      & Approvals        & Status Logs
```

---

## 🤖 Agent Responsibilities

### 🔍 **Intercom Extractor**
- Fetch articles via API with pagination
- Handle rate limiting & retries
- Enrich with detailed content
- Save raw JSON files

### 🧠 **Content Analyzer** 
- Parse HTML to clean text
- Generate embeddings for similarity
- Score quality metrics
- Cluster duplicate groups

### 📋 **Review Manager**
- Generate interactive HTML reports
- Auto-approve qualifying articles
- Track approval status
- Export approved collections

### 🚀 **Zendesk Uploader**
- Transform content format
- Handle API authentication
- Upload with error recovery
- Generate status reports

---

## 📊 Data Flow & States

| Stage | Location | Format | Description |
|-------|----------|--------|-------------|
| **Raw** | `data/raw/` | JSON | Fresh from Intercom API |
| **Analyzed** | `data/processed/` | JSON | With similarity & quality scores |
| **Review** | `reports/` | HTML | Interactive review interface |
| **Approved** | `data/approved/` | JSON | Ready for Zendesk upload |
| **Uploaded** | `reports/` | JSON | Upload status & logs |

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Language** | Python 3.9+ | Core implementation |
| **CLI** | Click + Rich | Beautiful terminal interface |
| **AI/ML** | sentence-transformers, scikit-learn | Content similarity detection |
| **Web** | requests, BeautifulSoup | API integration & HTML parsing |
| **Config** | Pydantic, python-dotenv | Settings management |
| **Testing** | pytest, pytest-cov | Unit tests & coverage |

---

## 🚀 Getting Started

### Quick Setup
```bash
cd noc_kbu
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Add your API keys
```

### Environment Variables
```bash
# Required API credentials
INTERCOM_ACCESS_TOKEN=your_intercom_token
ZENDESK_SUBDOMAIN=your_subdomain
ZENDESK_EMAIL=admin@company.com
ZENDESK_API_TOKEN=your_zendesk_token

# Processing settings (optional)
SIMILARITY_THRESHOLD=0.85
QUALITY_SCORE_THRESHOLD=0.7
BATCH_SIZE=10
```

---

## ⚡ Usage Examples

### 🧪 **Phase 1: Small Scale Testing**
```bash
# Complete workflow (recommended)
noc-kbu migrate --limit 20 --dry-run

# Individual steps for debugging
noc-kbu extract --limit 20
noc-kbu analyze
noc-kbu review --generate-report --auto-approve
noc-kbu upload --dry-run
```

### 🏭 **Phase 2: Full Production**
```bash
# Production migration
noc-kbu migrate --batch-size 100

# Test connection first
noc-kbu upload --test-connection
```

### 📊 **Monitoring & Status**
```bash
# Check project status
noc-kbu status

# Generate review reports
noc-kbu review --generate-report
```

---

## 📈 Quality Metrics

### **Similarity Detection**
- **Algorithm:** Sentence transformers + TF-IDF cosine similarity
- **Threshold:** 0.85 (configurable)
- **Clustering:** Connected components for duplicate groups

### **Quality Scoring** (0.0 - 1.0)
- **Readability:** 20% weight - sentence length analysis
- **Completeness:** 30% weight - content length validation
- **Freshness:** 20% weight - last update recency
- **Technical:** 30% weight - HTML cleanup, TODO markers

### **Auto-Approval Criteria**
✅ Quality score ≥ 0.7  
✅ No quality issues flagged  
✅ Not in duplicate cluster  
✅ Valid content structure  

---

## 🎨 Review Workflow

### **Interactive HTML Reports**
- 📊 **Summary Dashboard** - Key metrics & statistics
- 🔄 **Duplicates Tab** - Clustered similar articles with recommendations
- 📋 **Quality Issues** - Articles needing attention
- 📑 **All Articles** - Complete overview with scores

### **Approval Actions**
- **Auto-Approve:** Articles meeting all criteria
- **Manual Review:** Flagged content requiring human decision
- **Batch Actions:** Process multiple articles simultaneously

---

## 🔧 Configuration

### **Processing Settings**
| Setting | Default | Description |
|---------|---------|-------------|
| `SIMILARITY_THRESHOLD` | 0.85 | Duplicate detection sensitivity |
| `QUALITY_SCORE_THRESHOLD` | 0.7 | Auto-approval minimum |
| `BATCH_SIZE` | 10 | Articles per processing batch |
| `MAX_RETRIES` | 3 | API request retry attempts |
| `REQUEST_DELAY` | 1.0 | Seconds between API calls |

### **Content Analysis**
| Setting | Default | Description |
|---------|---------|-------------|
| `MIN_CONTENT_LENGTH` | 50 | Minimum article length |
| `MAX_CONTENT_AGE_DAYS` | 365 | Freshness threshold |

---

## 🚨 Error Handling

### **API Resilience**
- ⏱️ **Rate Limiting** - Automatic delay between requests
- 🔄 **Retry Logic** - Exponential backoff for failed requests
- 🛡️ **Connection Handling** - Persistent sessions with timeouts

### **Data Validation**
- ✅ **Pydantic Models** - Strict data structure validation
- 🔍 **Content Verification** - HTML parsing safety checks
- 💾 **Backup Strategy** - Original data preserved at each stage

---

## 📁 Project Structure

```
noc_kbu/
├── 🤖 agents/              # Core processing components
│   ├── intercom_extractor.py
│   ├── content_analyzer.py
│   ├── review_manager.py
│   └── zendesk_uploader.py
├── ⚙️ config/              # Settings management
├── 📊 data/                # Processing pipeline data
│   ├── raw/               # Intercom JSON files
│   ├── processed/         # Analysis results
│   └── approved/          # Upload-ready articles
├── 📋 reports/            # HTML review interfaces
├── 🧪 tests/              # Unit test suite
├── 🖥️ cli.py              # Command-line interface
└── 📖 docs/               # Documentation
```

---

## 🔮 Future Enhancements

### **Phase 3 Roadmap**
- [ ] **Real-time Sync** - Continuous monitoring of Intercom changes
- [ ] **Advanced ML** - Custom models for domain-specific content scoring
- [ ] **Multi-tenancy** - Support multiple Intercom → Zendesk migrations
- [ ] **Web Dashboard** - Browser-based review interface
- [ ] **Webhook Integration** - Event-driven processing

### **Analytics & Reporting**
- [ ] **Migration Metrics** - Success rates, processing times
- [ ] **Content Analytics** - Usage patterns, popular topics
- [ ] **Quality Trends** - Score improvements over time

---

## 🤝 Team Collaboration

### **Development Workflow**
1. **Local Development** - VS Code with Python extensions
2. **Testing** - Run `pytest` before commits
3. **Code Quality** - Use `black`, `isort`, `flake8` for formatting
4. **Documentation** - Update CLAUDE.md for any architecture changes

### **Review Process**
- 🔍 **Code Review** - All agents require peer review
- 📋 **Manual Testing** - Test with 10-20 articles before scaling
- ✅ **Quality Gates** - Ensure metrics thresholds are appropriate

---

## 📞 Support & Maintenance

### **Monitoring**
- Check `noc-kbu status` for project health
- Monitor `reports/` directory for review activities
- Review API rate limits and usage patterns

### **Troubleshooting**
- **Connection Issues:** Use `--test-connection` flag
- **Quality Problems:** Adjust thresholds in `.env`
- **Duplicate Detection:** Fine-tune similarity threshold
- **Debug Mode:** Use `--debug` flag for detailed logging

### **Contacts**
- **Tech Lead:** NOC Engineering Team
- **Stakeholders:** Knowledge Base Managers
- **Support:** Create issues in project repository

---

**Last Updated:** 2024-08-26  
**Version:** 1.0.0  
**Status:** ✅ Production Ready