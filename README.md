# ESTC Tiger 🐅

ESTC Tiger is an intelligent chatbot designed to help Elastic (ESTC) RSU holders make informed investment decisions. The app combines AI-powered analysis with comprehensive financial data to provide actionable insights about ESTC stock performance, market trends, and RSU timing strategies.

## Features

- **Conversation Memory**: Maintains context across multiple exchanges for natural dialogue
- **Source Citations**: All data-driven insights include citations to specific documents
- **Real-Time Stock Data**: Integrates with Finnhub API for current stock prices and market data
- **Comprehensive Data**: Combines AI training knowledge with real-time Elasticsearch data
- **Security-First**: Built with robust security evaluators to prevent malicious prompts
- **RSU-Focused**: Specifically designed for RSU holders with relevant metrics and advice

## Architecture

The app implements a multi-source RAG pipeline with security validation:

```
User Query → Security Evaluator → Generator (Claude + ES + Finnhub) → Output Evaluator → Response
     ↓              ↓                        ↓                                ↓
  Jailbreak      Block/Allow       Elasticsearch Query + Finnhub API        Quality Check
  Detection      Decision          Financial Data + Stock Prices            & Refinement
```

## Prerequisites

- Python 3.12 or higher
- UV package manager
- Anthropic API key (required)
- Elasticsearch cluster (required - app will not function without it)
- Finnhub API key (optional - for real-time stock data, falls back to historical estimates)

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/stuartMoorhouse/estc-tiger.git
cd estc-tiger
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```bash
# Required: Anthropic API key
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Finnhub API key for real-time stock data
FINNHUB_API_KEY=your_finnhub_api_key_here

# Optional: Elasticsearch configuration
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=your_password
# OR use API key authentication:
# ELASTICSEARCH_API_KEY=your_api_key_here
```

#### Getting API Keys:

- **Anthropic API Key**: Sign up at [console.anthropic.com](https://console.anthropic.com)
- **Finnhub API Key**: Get a free API key at [finnhub.io](https://finnhub.io/register) (free tier includes 60 calls/minute)

### 4. Elasticsearch Setup (Required)

**⚠️ Critical**: The app requires Elasticsearch to function. Choose one option:

#### Option A: Local Elasticsearch with Docker
```bash
# Start Elasticsearch with Docker
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.11.0

# Verify it's running (should return cluster info)
curl http://localhost:9200
```

#### Option B: Elastic Cloud
1. Sign up for [Elastic Cloud](https://cloud.elastic.co)
2. Create a deployment
3. Get your cluster endpoint and API key
4. Update the `.env` file with your credentials

### 5. Load Financial Data (Required)

Load the ESTC financial dataset into Elasticsearch:

```bash
# Using curl with API key authentication
curl -X POST "${ELASTICSEARCH_URL}/_bulk" \
  -H "Content-Type: application/x-ndjson" \
  -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
  --data-binary @estc_es9_bulk.json

# OR using basic authentication
curl -X POST "${ELASTICSEARCH_URL}/_bulk" \
  -H "Content-Type: application/x-ndjson" \
  -u "${ELASTICSEARCH_USERNAME}:${ELASTICSEARCH_PASSWORD}" \
  --data-binary @estc_es9_bulk.json

# Verify data was loaded (should show multiple indices)
curl "${ELASTICSEARCH_URL}/_cat/indices/estc-*?v"
```

### 6. Run the Application

```bash
uv run python web/app.py
```

The app will start on `http://localhost:5000`

## Usage

1. **Open your browser** and navigate to `http://localhost:5000`
2. **Start chatting** with ESTC Tiger about:
   - ESTC financial performance and metrics
   - Stock price analysis and trends
   - RSU timing and tax strategies
   - Competitive landscape analysis
   - Market conditions and outlook

3. **Example questions**:
   - "What's ESTC's current revenue growth rate?"
   - "How does ESTC compare to Datadog?"
   - "Should I sell my RSUs now or wait?"
   - "What are the analyst price targets for ESTC?"

## Data Sources

The app includes comprehensive ESTC financial data from:
- SEC filings and earnings reports
- Analyst ratings and price targets
- Historical stock performance (2018-2025)
- Competitive analysis vs. Datadog, Splunk
- RSU vesting schedules and tax implications
- Product milestones and market positioning

**Data Coverage**: 150+ documents across 25+ indices spanning 7 years since IPO

## Troubleshooting

### App won't start
- **Check environment variables**: Ensure `.env` file has valid `ANTHROPIC_API_KEY`
- **Python version**: Verify Python 3.12+ with `python --version`
- **Dependencies**: Try `uv sync` to reinstall dependencies
- **Port conflict**: Default port 5000 might be in use

### "Agent components not available" error
- **Import errors**: Check that all shared modules are properly installed
- **Dependencies**: Ensure all packages from pyproject.toml are installed with `uv sync`

### Elasticsearch connection issues
- **Service not running**: Verify Elasticsearch is running on configured URL
- **Wrong credentials**: Check `ELASTICSEARCH_URL`, username/password, or API key
- **Data not loaded**: Run the bulk data loading command and verify with `curl "${ELASTICSEARCH_URL}/_cat/indices/estc-*?v"`
- **Network issues**: Test connection with `curl ${ELASTICSEARCH_URL}`

### API errors
- **Invalid Anthropic key**: Verify key is valid and has credits at [console.anthropic.com](https://console.anthropic.com)
- **Finnhub issues**: App will work without Finnhub (uses fallback data)
- **Network connectivity**: Test with `curl https://api.anthropic.com`

### Common Development Issues
- **Empty responses**: Usually indicates missing Elasticsearch data
- **Slow responses**: Check Elasticsearch query performance
- **Memory issues**: Large conversation histories may cause memory usage spikes

## Development

### Project Structure
```
estc-tiger/
├── agent/                     # Core AI components
│   ├── evaluators/           # Security and output validation
│   │   ├── security_evaluator.py    # Input validation & jailbreak detection
│   │   └── output_evaluator.py      # Response security scanning
│   └── generators/           # AI response generation
│       └── data_processor.py  # Multi-source data processing (Elasticsearch + Finnhub + Claude)
├── shared/                   # Shared utilities
│   ├── conversation_memory.py    # Session & conversation management
│   ├── ecs_logger.py            # Structured logging (ECS format)
│   ├── elasticsearch_client.py   # Elasticsearch service wrapper
│   └── finnhub_client.py        # Stock data API client
├── web/                     # Flask web application
│   ├── app.py              # Main web server & API endpoints
│   ├── static/            # CSS, images, client assets
│   └── templates/         # HTML templates
├── estc_es9_bulk.json     # Financial dataset for Elasticsearch
└── pyproject.toml         # UV dependencies & project config
```

## Technical Architecture

### Core Components

**SecurityEvaluator** (`agent/evaluators/security_evaluator.py`)
- Regex-based jailbreak detection, query length limits, special character filtering
- Returns: `{"safe": True/False, "reason": "explanation"}`

**DataProcessor** (`agent/generators/data_processor.py`) 
- Multi-source data processing: Elasticsearch (financial docs) + Finnhub (stock data) + Claude (Sonnet)
- Query analysis, data retrieval, response generation with citations
- Returns: Generated response string

**OutputEvaluator** (`agent/evaluators/output_evaluator.py`)**
- Security-only scanning for sensitive data (passwords, API keys, IPs)
- **Note**: Does NOT validate response quality or accuracy
- Returns: `{"approved": True/False, "feedback": "explanation"}`

## Disclaimer

This tool is for informational purposes only and does not constitute financial advice. Always consult with qualified financial professionals before making investment decisions.

---
