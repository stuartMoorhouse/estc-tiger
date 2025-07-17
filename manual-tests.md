# Manual Tests for API Response Verification

This document provides step-by-step instructions for manually testing that the chatbot's responses are genuinely coming from Finnhub and Elasticsearch APIs, not being hallucinated.

## Prerequisites

Before running these tests, ensure you have:
1. `curl` installed on your system
2. The application's API endpoints and ports
3. Finnhub API key (if testing direct Finnhub access)
4. Elasticsearch instance URL and credentials (if applicable)

## Test 1: Verify Finnhub Stock Quote Data

### Step 1.1: Test the App's Stock Quote Endpoint

Run this curl command to get a stock quote through your app:

```bash
curl -X GET "http://localhost:3000/api/stock/quote?symbol=AAPL" \
     -H "Content-Type: application/json"
```

Record the response, particularly:
- Current price
- Previous close
- Percentage change
- Timestamp

### Step 1.2: Verify Directly with Finnhub API

Now verify the same data directly from Finnhub:

```bash
curl -X GET "https://finnhub.io/api/v1/quote?symbol=AAPL&token=YOUR_FINNHUB_API_KEY" \
     -H "Content-Type: application/json"
```

### Step 1.3: Compare Results

The values should match exactly:
- `c` (current price) should be identical
- `pc` (previous close) should be identical
- `dp` (percent change) should be identical

## Test 2: Verify Company Profile Data

### Step 2.1: Test App's Company Profile Endpoint

```bash
curl -X GET "http://localhost:3000/api/company/profile?symbol=AAPL" \
     -H "Content-Type: application/json"
```

### Step 2.2: Verify with Finnhub

```bash
curl -X GET "https://finnhub.io/api/v1/stock/profile2?symbol=AAPL&token=YOUR_FINNHUB_API_KEY" \
     -H "Content-Type: application/json"
```

### Step 2.3: Validation Checklist

Compare these fields:
- [ ] Company name matches
- [ ] Industry matches
- [ ] Market capitalization matches
- [ ] Logo URL is identical
- [ ] Exchange information matches

## Test 3: Verify Elasticsearch Search Results

### Step 3.1: Test App's Search Endpoint

```bash
curl -X POST "http://localhost:3000/api/search" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "technology stocks",
       "size": 5
     }'
```

### Step 3.2: Query Elasticsearch Directly

```bash
curl -X GET "http://localhost:9200/your_index_name/_search" \
     -H "Content-Type: application/json" \
     -u "username:password" \
     -d '{
       "query": {
         "match": {
           "content": "technology stocks"
         }
       },
       "size": 5
     }'
```

### Step 3.3: Verify Results Match

Check that:
- [ ] Number of results matches
- [ ] Document IDs are the same
- [ ] Relevance scores are similar
- [ ] Content snippets match

## Test 4: Real-Time Market Data Verification

### Step 4.1: Get Real-Time Price Through App

```bash
curl -X GET "http://localhost:3000/api/realtime/TSLA" \
     -H "Content-Type: application/json"
```

### Step 4.2