import json
import asyncio
from typing import Dict, Any, List, Optional
from anthropic import Anthropic
import os
import time
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from shared.elasticsearch_client import elasticsearch_service
from shared.conversation_memory import conversation_manager
from shared.finnhub_client import finnhub_client

class ElasticsearchGenerator:
    """
    Generator component that integrates Claude with Elasticsearch for ESTC analysis.
    """
    
    def __init__(self):
        self.anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.model = "claude-3-5-sonnet-20241022"  # Updated to more recent model
        self.api_calls = []  # Track API calls for logging
        
        # ESTC-specific data tools
        self.available_tools = [
            {
                "name": "search",
                "description": "Search ESTC financial and market data",
                "parameters": {
                    "index": {"type": "string", "description": "ESTC data index to search"},
                    "query": {"type": "object", "description": "Elasticsearch Query DSL"}
                }
            }
        ]
    
    async def generate(self, user_query: str, session_id: Optional[str] = None) -> str:
        """
        Generate response using Claude with ESTC data from Elasticsearch.
        
        Args:
            user_query: User's validated query about ESTC
            session_id: Optional session ID for conversation memory
            
        Returns:
            Generated response string about ESTC
        """
        
        try:
            # Reset API calls tracking for this query
            self.api_calls = []
            
            # Get or create session for conversation memory
            session_id = conversation_manager.get_or_create_session(session_id)
            
            # Analyze query intent and retrieve relevant data
            retrieved_data = await self._retrieve_all_data(user_query)
            
            # Check if Elasticsearch is connected, return error if not
            if not retrieved_data.get('connection_status', False):
                logger.error("Elasticsearch connection failed - cannot provide ESTC analysis")
                return "ERROR: Unable to connect to Elasticsearch data source. Please check the connection and try again. I cannot provide ESTC analysis without access to the financial data."
            
            # Build system message with retrieved data and conversation context
            system_message = self._build_system_message(retrieved_data, session_id)
            
            # Create user message for Claude with context
            user_message = self._build_user_message(user_query, retrieved_data, session_id)
            
            # Check if we should include current price phrase
            should_include_price_phrase = (
                retrieved_data.get('finnhub_data') and 
                session_id and 
                not conversation_manager.has_current_price_been_mentioned(session_id)
            )
            
            # Add current price phrase instruction if needed
            if should_include_price_phrase:
                finnhub_data = retrieved_data.get('finnhub_data', {})
                current_price = finnhub_data.get('current_price', 0)
                price_phrase_instruction = f"""
                
                IMPORTANT: Start your response with: "Based on the current stock price of ${current_price:.2f} [data from finnhub.io API], " and then continue with your analysis.
                """
                system_message += price_phrase_instruction
                
                # Mark current price as mentioned immediately to prevent duplicate usage
                conversation_manager.mark_current_price_mentioned(session_id)
            
            # Call Claude to generate response
            response = await self._call_claude_api(system_message, user_message)
            
            # Post-process for better readability
            formatted_response = self._format_response(response)
            
            # Add this exchange to conversation memory
            conversation_manager.add_exchange(
                session_id=session_id,
                user_query=user_query,
                assistant_response=formatted_response,
                api_calls=self.api_calls
            )
            
            return formatted_response
            
        except Exception as e:
            return f"I encountered an error analyzing ESTC data: {str(e)}"
    
    def _build_system_message(self, retrieved_data: Dict[str, Any], session_id: str = None) -> str:
        """Build the system message for Claude focused on ESTC with retrieved data and conversation context"""
        
        # Check if we have Elasticsearch connection
        connection_status = retrieved_data.get('connection_status', False)
        search_results = retrieved_data.get('search_results', {})
        
        base_message = """
        You are an ESTC (Elastic stock) financial analyst helping RSU holders make informed decisions.
        
        Your role:
        - Analyze ESTC's financial performance and market position
        - Help with RSU investment decisions and timing
        - Provide clear, actionable insights about ESTC stock
        - Explain market trends and competitive landscape
        """
        
        if search_results.get('results'):
            # Add information about retrieved data (either from Elasticsearch or fallback)
            data_mode = "Elasticsearch" if connection_status else "comprehensive ESTC dataset"
            data_context = f"""
        
        COMPREHENSIVE DATA CONTEXT:
        You have access to {len(search_results['results'])} relevant documents from the {data_mode} containing:
        - Query type: {search_results.get('query_type', 'general')}
        - Total documents found: {search_results.get('total', 0)}
        - Search terms used: {', '.join(search_results.get('search_terms', []))}
        
        This dataset contains complete and current ESTC financial, market, and operational data.
        Use this retrieved data to provide confident, definitive answers based on the actual ESTC information available.
        """
        else:
            # No data retrieved - this should not happen if Elasticsearch is connected
            # Log the issue and use minimal context to explain the problem
            data_context = """
        
        DATA ACCESS ISSUE:
        No relevant documents were found in Elasticsearch for this query.
        This may indicate a search configuration issue or missing data in the indices.
        """
        
        guidelines = """
        
        Guidelines:
        - Be direct, confident, and responsive - avoid hedging language
        - Focus on actionable investment insights
        - Use BOTH your training data AND the retrieved data to provide comprehensive analysis
        - Help with RSU timing and tax considerations
        - Compare to competitors when relevant
        - Reference previous conversation context when relevant for continuity
        - Always provide confident, definitive responses using all available information
        - NEVER mention incomplete datasets, missing data, or need for more information
        - NEVER use phrases like "I should maintain accuracy" or "I'll refrain from specifying"
        - Be helpful and responsive rather than overly cautious about precision
        - Make reasonable inferences from the data provided
        - Combine training knowledge with retrieved data for complete, actionable analysis
        
        Citation Requirements:
        - MANDATORY: After every fact or data point retrieved from the data source, add a citation in square brackets
        - For Elasticsearch data, use format: [index_name, document_id]
        - For Finnhub data, use format: [data from finnhub.io API]
        - Examples: "ESTC revenue is $1.48B [estc-financial-data, doc-revenue-2024]", "Current stock price is $85.71 [data from finnhub.io API]"
        - Only add citations for facts that came from the retrieved data, not general knowledge
        - Citations should be placed immediately after the specific fact or statistic
        - Do not cite general market knowledge or training data
        
        Formatting requirements:
        - Use clear paragraph breaks between different topics
        - Break up long text into digestible sections
        - Use line breaks after bullet points and before new topics
        - Structure responses with clear sections (e.g., "Key Metrics:", "Investment Perspective:", etc.)
        
        Always provide confident, comprehensive responses about ESTC combining training knowledge with retrieved data.
        """
        
        # Add conversation context if available
        conversation_context = ""
        if session_id:
            conversation_context = conversation_manager.get_context_for_llm(session_id)
        
        return base_message + data_context + guidelines + conversation_context
    
    def _build_user_message(self, user_query: str, retrieved_data: Dict[str, Any], session_id: str = None) -> str:
        """Build user message with retrieved data context and conversation continuity"""
        
        search_results = retrieved_data.get('search_results', {})
        finnhub_data = retrieved_data.get('finnhub_data')
        
        base_message = f"""
        User is asking about ESTC (Elastic stock): {user_query}
        """
        
        if search_results.get('results'):
            # Include retrieved data in the message
            data_section = "\n\nRETRIEVED DATA FROM ELASTICSEARCH:\n"
            
            for i, result in enumerate(search_results['results'][:5]):  # Limit to top 5 results
                source = result.get('source', {})
                data_section += f"\n{i+1}. Document ID: {result['document_id']}\n"
                data_section += f"   Index: {result['index']}\n"
                data_section += f"   Type: {result['type']}\n"
                data_section += f"   Score: {result['score']:.2f}\n"
                
                # Add relevant fields from the source
                if source.get('title'):
                    data_section += f"   Title: {source['title']}\n"
                if source.get('summary'):
                    data_section += f"   Summary: {source['summary']}\n"
                if source.get('content'):
                    # Limit content to avoid token overflow
                    content = source['content'][:500] + "..." if len(source['content']) > 500 else source['content']
                    data_section += f"   Content: {content}\n"
                if source.get('date'):
                    data_section += f"   Date: {source['date']}\n"
                if source.get('value'):
                    data_section += f"   Value: {source['value']}\n"
                
                # Add financial data fields
                financial_fields = ['revenue', 'revenue_growth_yoy', 'subscription_revenue', 'subscription_percentage', 
                                  'gaap_operating_margin', 'non_gaap_operating_margin', 'free_cash_flow_margin', 
                                  'implied_arr', 'arr_growth_yoy', 'net_expansion_rate', 'customers', 'fiscal_year', 
                                  'period_end', 'status', 'notes', 'milestone', 'description', 'impact', 
                                  'revenue_impact', 'financial_impact', 'partner', 'deal_type']
                
                for field in financial_fields:
                    if source.get(field):
                        data_section += f"   {field.replace('_', ' ').title()}: {source[field]}\n"
                
                data_section += "\n"
            
            # Add Finnhub data if available
            if finnhub_data:
                if finnhub_data.get('price_data'):
                    # Historical data
                    data_section += "\n\nHISTORICAL STOCK DATA (Finnhub):\n"
                    data_section += f"Symbol: {finnhub_data['symbol']}\n"
                    data_section += f"Date Range: {finnhub_data['date_range']}\n"
                    data_section += f"Total Data Points: {len(finnhub_data['price_data'])}\n"
                    
                    # Add sample of recent data points
                    price_data = finnhub_data['price_data']
                    recent_dates = sorted(price_data.keys())[-10:]  # Last 10 trading days
                    data_section += "\nRecent Price Data:\n"
                    for date in recent_dates:
                        price_info = price_data[date]
                        data_section += f"  {date}: Close ${price_info['close']:.2f}, High ${price_info['high']:.2f}, Low ${price_info['low']:.2f}\n"
                    
                    data_section += f"\nFull dataset contains daily prices from {finnhub_data['date_range']}.\n"
                    data_section += f"Data source: {finnhub_data['source']}\n"
                    data_section += f"Use this data to find correlations with product events and provide specific stock prices for historical events.\n"
                    
                else:
                    # Current real-time data
                    data_section += "\n\nREAL-TIME STOCK DATA (Finnhub):\n"
                    data_section += f"Symbol: {finnhub_data['symbol']}\n"
                    data_section += f"Current Price: ${finnhub_data['current_price']:.2f}\n"
                    data_section += f"Previous Close: ${finnhub_data['previous_close']:.2f}\n"
                    data_section += f"Change: ${finnhub_data['change']:.2f} ({finnhub_data['change_percent']:.2f}%)\n"
                    data_section += f"Day High: ${finnhub_data['day_high']:.2f}\n"
                    data_section += f"Day Low: ${finnhub_data['day_low']:.2f}\n"
                    data_section += f"Day Open: ${finnhub_data['day_open']:.2f}\n"
                    data_section += f"Timestamp: {finnhub_data['timestamp']}\n"
                    
                    # Add weekly/monthly data if available
                    if finnhub_data.get('week_high'):
                        data_section += f"Week High: ${finnhub_data['week_high']:.2f}\n"
                        data_section += f"Week Low: ${finnhub_data['week_low']:.2f}\n"
                    if finnhub_data.get('month_high'):
                        data_section += f"Month High: ${finnhub_data['month_high']:.2f}\n"
                        data_section += f"Month Low: ${finnhub_data['month_low']:.2f}\n"
                        data_section += f"Month Average: ${finnhub_data['month_avg']:.2f}\n"
                
                data_section += "\n"
            
            # Add conversation context reminder
            context_reminder = ""
            if session_id:
                context_reminder = "\n\nIMPORTANT: Review the previous conversation context in the system message to maintain continuity and reference previous topics when relevant."
            
            instruction = f"""
            
            Based on the retrieved data above AND your training knowledge, provide a comprehensive response about ESTC that directly addresses the user's question. 
            Use specific information from the documents to support your analysis, supplemented with your general market knowledge.
            Consider the conversation context if this is a follow-up question.{context_reminder}
            
            CRITICAL CITATION REQUIREMENTS: 
            - MANDATORY: Add citations in square brackets [index_name, document_id] IMMEDIATELY after ANY fact that comes from the retrieved data above
            - MANDATORY: For ALL stock data from Finnhub (current prices, historical data, etc.), add citation [data from finnhub.io API] immediately after the relevant facts
            - MANDATORY: For ALL fallback stock data when Finnhub fails, add citation [historical estimates (Finnhub subscription limitation)] immediately after the relevant facts
            - MANDATORY: For ALL Elasticsearch data (revenue, growth, margins, etc.), add citation [index_name, document_id] immediately after the relevant facts
            - MANDATORY: ALL current stock prices must use Finnhub data and be cited as [data from finnhub.io API] - NEVER use baseline or Elasticsearch data for current prices
            - When referencing historical stock data, ALWAYS include specific stock prices and dates WITH citations
            - When correlating product events with stock performance, MUST include the stock price at that time WITH citations
            - If Finnhub historical data is not available, use the fallback historical data provided (from historical estimates) WITH citations
            - Do not cite general market knowledge or training data that you already knew
            - Use both retrieved data and training knowledge to provide confident, complete analysis
            - Never mention incomplete datasets or missing data
            - Be responsive and helpful - avoid overly cautious language about accuracy
            - For each product event mentioned, provide an estimated stock price for that timeframe WITH appropriate citations
            - Combine all available information to provide actionable investment insights
            - Fill gaps in retrieved data with relevant training knowledge (without citations for general knowledge)
            - Reference previous exchanges when answering follow-up questions
            - CRITICAL: Every product event must be accompanied by a stock price estimate [data from finnhub.io API] or reasonable estimate based on historical data
            - When Finnhub API fails, use the historical estimates to provide reasonable stock price estimates for historical periods
            - Always include specific stock prices and dates for product events, even if from historical estimates
            
            EXAMPLES OF PROPER CITATIONS:
            - "Current stock price is $85.71 [data from finnhub.io API]"
            - "ESTC is trading at $85.71 [data from finnhub.io API]"
            - "Revenue reached $1.48B [estc-financial-data, doc-revenue-2024]"
            - "17% year-over-year growth [estc-financial-data, doc-growth-2024]"
            - "Operating margin of 12% [estc-financial-data, doc-margins-2024]"
            - "Analyst consensus target of $115.74 [estc-analyst-ratings, doc-consensus-2024]"
            """
            
        else:
            # No elasticsearch data retrieved
            connection_status = retrieved_data.get('connection_status', False)
            if not connection_status:
                data_section = "\n\nERROR: Elasticsearch connection not available. Cannot provide ESTC data analysis."
            else:
                data_section = "\n\nWARNING: No relevant documents found in Elasticsearch for this query. This may indicate a search configuration issue."
            
            # Add Finnhub data if available even without elasticsearch data
            if finnhub_data:
                if finnhub_data.get('price_data'):
                    # Historical data
                    data_section += " and historical stock data.\n"
                    data_section += "\n\nHISTORICAL STOCK DATA (Finnhub):\n"
                    data_section += f"Symbol: {finnhub_data['symbol']}\n"
                    data_section += f"Date Range: {finnhub_data['date_range']}\n"
                    data_section += f"Total Data Points: {len(finnhub_data['price_data'])}\n"
                    
                    # Add sample of recent data points
                    price_data = finnhub_data['price_data']
                    recent_dates = sorted(price_data.keys())[-10:]  # Last 10 trading days
                    data_section += "\nRecent Price Data:\n"
                    for date in recent_dates:
                        price_info = price_data[date]
                        data_section += f"  {date}: Close ${price_info['close']:.2f}, High ${price_info['high']:.2f}, Low ${price_info['low']:.2f}\n"
                    
                    data_section += f"\nFull dataset contains daily prices from {finnhub_data['date_range']}.\n"
                    data_section += f"Data source: {finnhub_data['source']}\n"
                    data_section += f"Use this data to find correlations with product events and provide specific stock prices for historical events.\n"
                    
                else:
                    # Current real-time data
                    data_section += " and real-time stock data.\n"
                    data_section += "\n\nREAL-TIME STOCK DATA (Finnhub):\n"
                    data_section += f"Symbol: {finnhub_data['symbol']}\n"
                    data_section += f"Current Price: ${finnhub_data['current_price']:.2f}\n"
                    data_section += f"Previous Close: ${finnhub_data['previous_close']:.2f}\n"
                    data_section += f"Change: ${finnhub_data['change']:.2f} ({finnhub_data['change_percent']:.2f}%)\n"
                    data_section += f"Day High: ${finnhub_data['day_high']:.2f}\n"
                    data_section += f"Day Low: ${finnhub_data['day_low']:.2f}\n"
                    data_section += f"Day Open: ${finnhub_data['day_open']:.2f}\n"
                    data_section += f"Timestamp: {finnhub_data['timestamp']}\n"
                    
                    # Add weekly/monthly data if available
                    if finnhub_data.get('week_high'):
                        data_section += f"Week High: ${finnhub_data['week_high']:.2f}\n"
                        data_section += f"Week Low: ${finnhub_data['week_low']:.2f}\n"
                    if finnhub_data.get('month_high'):
                        data_section += f"Month High: ${finnhub_data['month_high']:.2f}\n"
                        data_section += f"Month Low: ${finnhub_data['month_low']:.2f}\n"
                        data_section += f"Month Average: ${finnhub_data['month_avg']:.2f}\n"
                
                data_section += "\n"
            else:
                data_section += ".\n"
            
            # Add conversation context reminder
            context_reminder = ""
            if session_id:
                context_reminder = "\n\nIMPORTANT: Review the previous conversation context in the system message to maintain continuity and reference previous topics when relevant."
            
            instruction = f"""
            
            IMPORTANT: You cannot provide ESTC analysis because no relevant data was found in Elasticsearch.
            Explain that you cannot answer the question without access to the ESTC financial and market data.
            Consider the conversation context if this is a follow-up question.{context_reminder}
            
            If Finnhub stock data is available, you may mention current stock prices but clearly state that detailed analysis requires Elasticsearch data.
            
            CRITICAL CITATION REQUIREMENTS: 
            - MANDATORY: For ALL stock data from Finnhub (current prices, historical data, etc.), add citation [data from finnhub.io API] immediately after the relevant facts
            - Do not make up financial metrics or data - only use what's available from Finnhub
            - Be transparent about the data limitations
            """
        
        return base_message + data_section + instruction
    
    def _format_response(self, response: str) -> str:
        """Format response for better readability"""
        # Add paragraph breaks after bullet points and before new sections
        formatted = response.replace(' - ', '\n- ')
        
        # Add breaks before common section headers
        section_headers = ['Key Metrics:', 'Investment Perspective:', 'For RSU holders:', 
                          'Key ESTC Metrics:', 'Current Performance:', 'Outlook:', 
                          'Recommendation:', 'Summary:', 'Analysis:']
        
        for header in section_headers:
            formatted = formatted.replace(header, f'\n\n{header}')
        
        # Add breaks before questions
        formatted = formatted.replace('Would you like', '\n\nWould you like')
        formatted = formatted.replace('Do you need', '\n\nDo you need')
        
        # Clean up multiple line breaks
        import re
        formatted = re.sub(r'\n{3,}', '\n\n', formatted)
        
        # Remove leading/trailing whitespace
        formatted = formatted.strip()
        
        return formatted
    
    async def _retrieve_all_data(self, user_query: str) -> Dict[str, Any]:
        """Retrieve relevant ESTC data from Elasticsearch and Finnhub"""
        
        # Analyze query intent to determine what data to search for
        query_analysis = elasticsearch_service.analyze_query_intent(user_query)
        
        # Perform search based on analyzed intent
        search_results = elasticsearch_service.search_estc_data(
            query_type=query_analysis['primary_type'],
            search_terms=query_analysis['search_terms'],
            limit=10
        )
        
        # Track API calls for logging
        if search_results.get('results'):
            self.api_calls.append({
                "index": search_results.get('indices_searched', []),
                "operation": "search",
                "document_count": len(search_results['results']),
                "documents": [
                    {
                        "id": result['document_id'],
                        "type": result['type'],
                        "score": result['score']
                    } for result in search_results['results'][:5]  # Limit for logging
                ],
                "query_type": query_analysis['primary_type'],
                "search_terms": query_analysis['search_terms']
            })
        
        # Check if we should fetch Finnhub data based on query
        finnhub_data = None
        data_type_needed = self._should_fetch_finnhub_data(user_query, query_analysis)
        
        if data_type_needed != 'none' and finnhub_client.is_available():
            if data_type_needed == 'historical':
                finnhub_data = finnhub_client.get_extended_historical_data(5)  # 5 years
                if finnhub_data:
                    # Track Finnhub API call
                    self.api_calls.append({
                        "service": "finnhub",
                        "operation": "get_extended_historical_data",
                        "symbol": "ESTC",
                        "data_type": "historical_stock_data",
                        "years": 5
                    })
            elif data_type_needed == 'current':
                finnhub_data = finnhub_client.get_stock_summary()
                if finnhub_data:
                    # Track Finnhub API call
                    self.api_calls.append({
                        "service": "finnhub",
                        "operation": "get_stock_summary",
                        "symbol": "ESTC",
                        "data_type": "real_time_stock_data"
                    })
        
        return {
            "query_analysis": query_analysis,
            "search_results": search_results,
            "connection_status": elasticsearch_service.is_connected(),
            "cluster_info": elasticsearch_service.get_cluster_info(),
            "finnhub_data": finnhub_data,
            "finnhub_available": finnhub_client.is_available()
        }
    
    def _should_fetch_finnhub_data(self, user_query: str, query_analysis: Dict[str, Any]) -> str:
        """Determine what type of Finnhub data to fetch based on the query"""
        query_lower = user_query.lower()
        
        # Keywords that indicate need for historical data
        historical_keywords = [
            'last 5 years', 'last five years', 'historical', 'over time',
            'years', 'correlation', 'trend', 'pattern', 'since',
            'past', 'history', 'over the', 'timeline', 'evolution'
        ]
        
        # Keywords that indicate need for current stock data
        current_price_keywords = [
            'current price', 'latest price', 'price now', 'stock price',
            'current value', 'trading at', 'price today', 'today',
            'now', 'current', 'latest', 'real time', 'live',
            'market price', 'share price'
        ]
        
        # Check for historical data needs first
        for keyword in historical_keywords:
            if keyword in query_lower:
                return 'historical'
        
        # Check if query contains current price keywords
        for keyword in current_price_keywords:
            if keyword in query_lower:
                return 'current'
        
        # Check if query type is stock-related
        if query_analysis.get('primary_type') == 'stock':
            return 'current'
        
        # Check for general stock performance questions
        performance_keywords = ['performance', 'how is', 'doing', 'trend']
        for keyword in performance_keywords:
            if keyword in query_lower and 'stock' in query_lower:
                return 'current'
        
        # For any stock-related query (like selling decisions), always include current data
        stock_decision_keywords = ['sell', 'buy', 'hold', 'invest', 'position', 'shares', 'rsu', 'decision']
        for keyword in stock_decision_keywords:
            if keyword in query_lower:
                return 'current'
        
        # Since this is an ESTC stock analysis system, always include current stock data by default
        return 'current'
    
    def get_api_calls(self) -> List[Dict[str, Any]]:
        """Get the API calls made during the last generation"""
        return self.api_calls.copy()
    
    async def _call_claude_api(self, system_message: str, user_message: str) -> str:
        """Make actual call to Claude API"""
        try:
            # Make actual Claude API call (synchronous - Anthropic client is not async)
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=system_message,
                messages=[{"role": "user", "content": user_message}]
            )
            return response.content[0].text
            
        except Exception as e:
            print(f"Claude API Error: {str(e)}")  # Debug logging
            return f"Error calling Claude API: {str(e)}"
    
    def get_tool_descriptions(self) -> List[Dict[str, Any]]:
        """Get descriptions of available ESTC tools for the UI"""
        return [
            {
                "name": "ESTC Analysis",
                "description": "Analyzes ESTC financial data and market position",
                "icon": "🐅"
            }
        ]