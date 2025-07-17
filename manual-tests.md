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

### Step 4.2: Verify with Finnhub WebSocket (Alternative Method)

Since WebSockets are harder to test with curl, use this REST endpoint:

```bash
curl -X GET "https://finnhub.io/api/v1/quote?symbol=TSLA&token=YOUR_FINNHUB_API_KEY" \
     -H "Content-Type: application/json"
```

### Step 4.3: Timestamp Verification

Ensure that:
- [ ] Timestamps are recent (within last few seconds/minutes)
- [ ] Price data is current market data
- [ ] Volume information matches

## Test 5: News Data Verification

### Step 5.1: Get News Through App

```bash
curl -X GET "http://localhost:3000/api/news?symbol=GOOGL&from=2024-01-01&to=2024-01-31" \
     -H "Content-Type: application/json"
```

### Step 5.2: Verify with Finnhub

```bash
curl -X GET "https://finnhub.io/api/v1/company-news?symbol=GOOGL&from=2024-01-01&to=2024-01-31&token=YOUR_FINNHUB_API_KEY" \
     -H "Content-Type: application/json"
```

### Step 5.3: Validate News Items

For each news item, verify:
- [ ] Headlines match exactly
- [ ] URLs are identical
- [ ] Publication dates match
- [ ] Source names are the same

## Test 6: Chatbot Response Verification

### Step 6.1: Ask Chatbot for Stock Information

```bash
curl -X POST "http://localhost:3000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "What is the current price of Apple stock?"
     }'
```

### Step 6.2: Extract Data Points from Response

From the chatbot's response, identify:
- Stock price mentioned
- Any percentage changes
- Market cap or other metrics

### Step 6.3: Cross-Reference Each Data Point

For each piece of data the chatbot provides, verify using the direct API calls above.

## Test 7: Error Handling Verification

### Step 7.1: Test Invalid Symbol

```bash
curl -X GET "http://localhost:3000/api/stock/quote?symbol=INVALID123" \
     -H "Content-Type: application/json"
```

### Step 7.2: Verify Error Matches Finnhub

```bash
curl -X GET "https://finnhub.io/api/v1/quote?symbol=INVALID123&token=YOUR_FINNHUB_API_KEY" \
     -H "Content-Type: application/json"
```

Both should return similar error responses.

## Troubleshooting Common Issues

### Issue 1: Timestamps Don't Match
- **Solution**: Check timezone settings in both systems
- **Verify**: Use UTC timestamps for comparison

### Issue 2: Prices Slightly Different
- **Solution**: Market data may update between calls
- **Verify**: Check if difference is within reasonable market movement (< 0.1%)

### Issue 3: Elasticsearch Results Differ
- **Solution**: Check index refresh interval
- **Verify**: Force refresh: `curl -X POST "http://localhost:9200/your_index/_refresh"`

## Validation Checklist Summary

- [ ] All Finnhub stock quotes match direct API calls
- [ ] Company profile data is identical
- [ ] News items correspond to Finnhub's news API
- [ ] Elasticsearch search results match direct queries
- [ ] Error responses are consistent
- [ ] Timestamps are current and accurate
- [ ] No data appears to be cached or stale

## Red Flags Indicating Hallucination

Watch for these signs that data might be hallucinated:
1. Prices that never change over multiple requests
2. Round numbers that seem too convenient (e.g., exactly $100.00)
3. News articles with generic titles
4. Timestamps that don't update
5. Data that doesn't match market hours
6. Company information that seems outdated

## Conclusion

By following these tests systematically, you can verify that your chatbot is retrieving real data from Finnhub and Elasticsearch rather than generating hallucinated responses. Run these tests periodically, especially after any code changes to the chatbot or API integration layers.