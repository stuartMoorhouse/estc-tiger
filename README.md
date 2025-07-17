# ESTC Tiger 🐅

ESTC Tiger is an intelligent chatbot designed to help Elastic (ESTC) RSU holders make informed investment decisions. The app combines AI-powered analysis with comprehensive financial data to provide actionable insights about ESTC stock performance, market trends, and RSU timing strategies.

## Features

- **Conversation Memory**: Maintains context across multiple exchanges for natural dialogue
- **Source Citations**: All data-driven insights include citations to specific documents
- **Comprehensive Data**: Combines AI training knowledge with real-time Elasticsearch data
- **Security-First**: Built with robust security evaluators to prevent malicious prompts
- **RSU-Focused**: Specifically designed for RSU holders with relevant metrics and advice

## Architecture

The app uses the "Evaluator Optimizer" pattern with MCP (Model Context Protocol) integration:

```
User Query → Security Evaluator → Generator (Claude + Elasticsearch MCP) → Output Evaluator → Response
     ↓              ↓                        ↓                           ↓
  Block/Allow    Jailbreak       Elasticsearch Query          Quality Check
  Decision      Detection        & Tool Use                   & Refinement
```

## Prerequisites

- Python 3.12 or higher
- UV package manager
- Elasticsearch cluster (optional - app works with fallback data)
- Anthropic API key

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

# Optional: Elasticsearch configuration
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=your_password
# OR use API key authentication:
# ELASTICSEARCH_API_KEY=your_api_key_here
```

### 4. Elasticsearch Setup (Optional)

If you want to use live Elasticsearch data instead of the fallback dataset:

#### Option A: Local Elasticsearch
```bash
# Start Elasticsearch with Docker
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.11.0
```

#### Option B: Elastic Cloud
1. Sign up for [Elastic Cloud](https://cloud.elastic.co)
2. Create a deployment
3. Get your cluster endpoint and API key
4. Update the `.env` file with your credentials

### 5. Load Financial Data

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
- Check that your `.env` file has the correct `ANTHROPIC_API_KEY`
- Ensure Python 3.12+ is installed
- Try `uv sync` to reinstall dependencies

### No Elasticsearch data
- The app works with fallback data if Elasticsearch is unavailable
- Check your Elasticsearch URL and credentials
- Verify the bulk data was loaded successfully

### API errors
- Verify your Anthropic API key is valid and has credits
- Check network connectivity
- Review the console logs for specific error messages

## Development

### Project Structure
```
estc-tiger/
├── agent/                  # Core AI components
│   ├── evaluators/        # Security and output evaluators
│   └── generators/        # Claude + Elasticsearch integration
├── shared/                # Shared utilities
│   ├── conversation_memory.py
│   ├── ecs_logger.py
│   └── elasticsearch_client.py
├── web/                   # Flask web application
│   ├── app.py
│   ├── static/           # CSS, images
│   └── templates/        # HTML templates
├── estc_es9_bulk.json    # Financial dataset
└── pyproject.toml        # Dependencies
```

### Running Tests
```bash
# Add test dependencies
uv add --dev pytest pytest-asyncio

# Run tests
uv run pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for informational purposes only and does not constitute financial advice. Always consult with qualified financial professionals before making investment decisions.