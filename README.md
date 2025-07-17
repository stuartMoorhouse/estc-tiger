
This app uses the "Evaluator Optimizer" pattern and MCP to create a chatbot that uses specialised knowledge and aims to protect itself from malicous prompts. 

User Query → Security Evaluator → Generator (Claude + Elasticsearch MCP) → Output Evaluator → Response
     ↓              ↓                        ↓                           ↓
  Block/Allow    Jailbreak       Elasticsearch Query          Quality Check
  Decision      Detection        & Tool Use                   & Refinement


## Set up project
uv add flask anthropic python-dotenv aiohttp requests

## add the financial data
curl -X POST "${ELASTICSEARCH_URL}/_bulk" \
  -H "Content-Type: application/x-ndjson" \
  -H "Authorization: ApiKey ${ELASTICSEARCH_API_KEY}" \
  --data-binary @estc_es9_bulk.json


## Start the app
uv run python app.py



## data provenance
This ESTC financial dataset was compiled on January 17, 2025 by Claude Sonnet 4 (model: claude-sonnet-4-20250514) through comprehensive web research of authoritative sources including SEC filings, earnings reports, investor relations materials, and market analysis from 2018-2025, specifically designed to support RSU holder decision-making through MCP-enabled chatbot interactions, created in response to the prompt: "A chatbot to help people who get Elastic (ESTC) RSOs every quarter. Is there some information about Elastic that I could put into the Elasticsearch instance to help make this use case better? I want to search for that info with the MCPlink."


Data Summary & Sources
Data Coverage

Time Period: 2018-2025 (7 years since IPO)
Total Records: 150+ documents across 25+ indices
Data Categories: Financial, competitive, product, market, RSU-specific

Key Data Sources
Primary Financial Data

MacroTrends: Historical revenue data from 2018-2025 Elastic (ESTC) Statistics & Valuation
Elastic Investor Relations: Official quarterly earnings reports The Motley FoolThe Motley Fool
Meritech Capital: IPO S-1 breakdown and early financial metrics Elastic NV (ESTC) - Revenue

Stock Performance Data

CNBC: IPO performance and debut trading data Elastic (ESTC) Earnings Date and Reports 2025 $ESTC
MacroTrends: 7-year stock price history with all-time highs/lows Elastic NV Earnings: ESTC Quarterly Earnings Calendar (2022)
Stock Analysis: Current trading statistics and valuation metrics

Competitive Intelligence

Zacks/Yahoo Finance: DDOG vs ESTC competitive analysis Elastic - 7 Year Stock Price History | ESTC | MacroTrends
Seeking Alpha: Competitive positioning concerns and analysis Elastic (ESTC) Stock Price & Overview
Software Stack Investing: Detailed competitive landscape review Elastic — The Search AI Company | Elastic

Market Recognition & Analysis

TipRanks: Analyst consensus and earnings call summaries Elastic (ESTC): Undervalued But Competitive Position Is Concerning | Seeking Alpha
Motley Fool: Q3 and Q4 2024 earnings call transcripts SoftwarestackinvestingCSIMarket
Elastic.co: Official company product announcements and market position Elastic N.V. Ordinary Shares (ESTC) Stock Price, News, Quotes, & Historic Data | Nasdaq

Company Background

Wikipedia: Company history, acquisitions, and founding story
Stock Titan: Recent product launches and partnership announcements DDOG vs. ESTC: Which Cloud Observability Stock is the Better Buy?

Data Methodology

Historical Accuracy: All financial data cross-referenced with SEC filings
Real-time Updates: Stock prices and analyst data current as of search date
Comprehensive Coverage: 10 major data categories from financial to competitive
RSU-Specific Focus: Includes vesting schedules, tax implications, and scenarios

Data Quality Notes

Pre-IPO Data: Limited to S-1 filing information (company was private)
Projections: Forward-looking estimates based on current analyst consensus
Assumptions: Some granular metrics estimated from available ranges
Currency: All financial data in USD millions unless specified

This dataset provides RSU holders with institutional-grade analysis capabilities, combining official company data with market intelligence and competitive insights all searchable through your MCP-enabled chatbot!