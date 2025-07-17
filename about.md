# ESTC Tiger - Architecture & Logic

## Overview

ESTC Tiger is a secure chatbot application designed to help users analyze Elastic (ESTC) stock and financial data. The application implements the **Evaluator-Optimizer pattern** with multi-layered security to protect against malicious prompts while providing intelligent responses using Claude AI and Elasticsearch.

## Architecture

The application follows a **3-stage pipeline** architecture:

```
User Query ’ Security Evaluator ’ Generator ’ Output Evaluator ’ Response
     “              “                “            “
  Validation    Jailbreak         Claude +     Quality Check
                Detection      Elasticsearch   & Refinement
```

## Core Components

### 1. **Security Evaluator** (`agent/evaluators/security_evaluator.py`)
- **Purpose**: First line of defense against malicious input
- **Logic**: 
  - Scans for jailbreak patterns (e.g., "ignore previous instructions")
  - Detects dangerous Elasticsearch operations (e.g., "delete index")
  - Validates query length and special character usage
  - Blocks suspicious requests before they reach the AI
- **Returns**: `{"safe": True/False, "reason": "explanation"}`

### 2. **Generator** (`agent/generators/elasticsearch_generator.py`)
- **Purpose**: Core AI processing with access to specialized data
- **Logic**:
  - Uses Claude AI (Sonnet model) to process validated queries
  - Integrates with Elasticsearch via MCP (Model Context Protocol)
  - Has access to comprehensive ESTC financial data (2018-2025)
  - Generates contextually relevant responses about stock analysis
- **Returns**: Generated response string

### 3. **Output Evaluator** (`agent/evaluators/output_evaluator.py`)
- **Purpose**: Quality control and safety check for AI responses
- **Logic**:
  - Scans for sensitive data leakage (passwords, API keys, etc.)
  - Validates response quality and helpfulness
  - Ensures completeness relative to user query
  - Verifies Elasticsearch-specific accuracy
- **Returns**: `{"approved": True/False, "feedback": "explanation"}`

## Web Interface

### **Flask Application** (`web/app.py`)
- **Routes**:
  - `/` - Main chat interface
  - `/api/estc-stock` - Real-time stock data from Finnhub API
  - `/chat` - POST endpoint for processing user messages
- **Features**:
  - Real-time stock chart visualization
  - Interactive chat interface with security indicators
  - Error handling and user feedback

### **Frontend** (`web/templates/index.html`)
- **Technologies**: HTML, CSS, JavaScript
- **Features**:
  - Real-time stock price chart
  - Chat interface with message history
  - Visual indicators for blocked/approved responses
  - Responsive design

## Data Layer

### **Elasticsearch Integration**
- **Purpose**: Stores and searches comprehensive ESTC financial data
- **Data Sources**: 
  - SEC filings and earnings reports
  - Stock performance data (2018-2025)
  - Competitive analysis vs Datadog, Splunk
  - RSU-specific information and scenarios
- **Access**: Via MCP (Model Context Protocol) for secure tool use

### **External APIs**
- **Finnhub**: Real-time stock price data
- **Anthropic**: Claude AI processing
- **Elasticsearch**: Financial data search and retrieval

## Security Features

### **Multi-Layer Protection**
1. **Input Validation**: Regex patterns for jailbreak detection
2. **Query Sanitization**: Length limits and special character filtering
3. **Output Scanning**: Sensitive data detection in responses
4. **Rate Limiting**: Prevents abuse and DoS attacks

### **Pattern Detection**
- **Jailbreak Attempts**: "ignore previous instructions", "pretend you are"
- **SQL Injection**: "drop table", "delete from", "'; --"
- **XSS Attempts**: "script alert", "javascript:", "eval("
- **Elasticsearch Abuse**: "_cluster settings", "delete index"

## Development Setup

### **Requirements**
- Python 3.13+
- Flask web framework
- Anthropic Claude API access
- Elasticsearch instance
- Finnhub API key (for stock data)

### **Environment Variables**
```bash
ANTHROPIC_API_KEY=your_claude_api_key
ELASTICSEARCH_URL=http://localhost:9200
FINNHUB_API_KEY=your_finnhub_api_key
```

### **Installation**
```bash
# Install dependencies
pip install -r requirements.txt

# Load sample data
curl -X POST "${ELASTICSEARCH_URL}/_bulk" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @estc_es9_bulk.json

# Start application
python web/app.py
```

## Use Cases

### **Target Users**
- ESTC RSU holders making vesting decisions
- Financial analysts researching Elastic stock
- Investors seeking comprehensive ESTC analysis

### **Typical Queries**
- "What's ESTC's revenue growth trend?"
- "How does Elastic compare to Datadog?"
- "Should I hold or sell my RSUs?"
- "What are the latest analyst ratings?"

## Technical Benefits

### **Security First**
- Prevents prompt injection attacks
- Validates all inputs and outputs
- Protects against data exfiltration

### **AI-Powered**
- Leverages Claude's advanced reasoning
- Contextual understanding of financial data
- Natural language query processing

### **Scalable Architecture**
- Modular component design
- Async processing pipeline
- Extensible evaluation framework

---

*This application demonstrates how to build secure AI chatbots with specialized knowledge while maintaining robust protection against malicious use.*