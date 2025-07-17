import json
import asyncio
from typing import Dict, Any, List
from anthropic import Anthropic
import os
import time

class ElasticsearchGenerator:
    """
    Generator component that integrates Claude with Elasticsearch MCP tools for ESTC analysis.
    """
    
    def __init__(self):
        self.anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.model = "claude-3-5-sonnet-20241022"  # Updated to more recent model
        self.mcp_calls = []  # Track MCP calls for logging
        
        # ESTC-specific MCP tools
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
    
    async def generate(self, user_query: str) -> str:
        """
        Generate response using Claude with ESTC data from Elasticsearch.
        
        Args:
            user_query: User's validated query about ESTC
            
        Returns:
            Generated response string about ESTC
        """
        
        try:
            # Reset MCP calls tracking for this query
            self.mcp_calls = []
            
            # Simulate MCP calls to Elasticsearch (since we don't have actual MCP server)
            await self._simulate_mcp_calls(user_query)
            
            # Build system message
            system_message = self._build_system_message()
            
            # Create user message for Claude
            user_message = f"""
            User is asking about ESTC (Elastic stock): {user_query}
            
            You have access to comprehensive ESTC data including:
            - Financial performance (revenue, growth, margins)
            - Stock data (prices, analyst targets, ratings)
            - Competitive analysis vs Datadog, Splunk
            - RSU and equity compensation info
            - Market events and product milestones
            
            Please provide a helpful, direct response about ESTC based on this query.
            """
            
            # Call Claude to generate response
            response = await self._call_claude_api(system_message, user_message)
            
            # Post-process for better readability
            formatted_response = self._format_response(response)
            return formatted_response
            
        except Exception as e:
            return f"I encountered an error analyzing ESTC data: {str(e)}"
    
    def _build_system_message(self) -> str:
        """Build the system message for Claude focused on ESTC"""
        return """
        You are an ESTC (Elastic stock) financial analyst helping RSU holders make informed decisions.
        
        Your role:
        - Analyze ESTC's financial performance and market position
        - Help with RSU investment decisions and timing
        - Provide clear, actionable insights about ESTC stock
        - Explain market trends and competitive landscape
        
        Key ESTC data you have access to:
        - Current revenue: $1.48B (+17% YoY)
        - Current stock price: $85.71
        - Analyst target: $115.74 (35% upside)
        - Cloud revenue growth: 30% YoY
        - GenAI customers: 1,750+
        - Operating margin: 12% (non-GAAP)
        
        Guidelines:
        - Be direct and concise
        - Focus on actionable investment insights
        - Use specific financial metrics
        - Help with RSU timing and tax considerations
        - Compare to competitors when relevant
        
        Formatting requirements:
        - Use clear paragraph breaks between different topics
        - Break up long text into digestible sections
        - Use line breaks after bullet points and before new topics
        - Structure responses with clear sections (e.g., "Key Metrics:", "Investment Perspective:", etc.)
        
        Always provide helpful, data-driven responses about ESTC with proper formatting.
        """
    
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
    
    async def _simulate_mcp_calls(self, user_query: str):
        """Simulate MCP calls to Elasticsearch based on user query"""
        query_lower = user_query.lower()
        
        # Simulate different index searches based on query content
        if "financial" in query_lower or "revenue" in query_lower or "earnings" in query_lower:
            self.mcp_calls.append({
                "index": "estc-financial-data",
                "operation": "search",
                "document_count": 15,
                "documents": [
                    {"id": "estc-q4-2024", "type": "earnings_report"},
                    {"id": "estc-revenue-2024", "type": "financial_metrics"},
                    {"id": "estc-growth-trends", "type": "financial_analysis"}
                ]
            })
        
        if "stock" in query_lower or "price" in query_lower or "analyst" in query_lower:
            self.mcp_calls.append({
                "index": "estc-stock-data", 
                "operation": "search",
                "document_count": 8,
                "documents": [
                    {"id": "estc-price-history", "type": "stock_prices"},
                    {"id": "estc-analyst-ratings", "type": "analyst_data"},
                    {"id": "estc-target-prices", "type": "price_targets"}
                ]
            })
        
        if "competitive" in query_lower or "datadog" in query_lower or "splunk" in query_lower:
            self.mcp_calls.append({
                "index": "estc-competitive-analysis",
                "operation": "search", 
                "document_count": 12,
                "documents": [
                    {"id": "estc-vs-datadog-2024", "type": "competitive_analysis"},
                    {"id": "estc-vs-splunk-metrics", "type": "competitive_metrics"},
                    {"id": "estc-market-position", "type": "market_analysis"}
                ]
            })
        
        if "rsu" in query_lower or "equity" in query_lower or "compensation" in query_lower:
            self.mcp_calls.append({
                "index": "estc-rsu-data",
                "operation": "search",
                "document_count": 6,
                "documents": [
                    {"id": "estc-rsu-vesting-schedule", "type": "compensation_data"},
                    {"id": "estc-equity-tax-guide", "type": "tax_information"},
                    {"id": "estc-rsu-scenarios", "type": "decision_scenarios"}
                ]
            })
        
        # Default search if no specific category matched
        if not self.mcp_calls:
            self.mcp_calls.append({
                "index": "estc-general-data",
                "operation": "search",
                "document_count": 10,
                "documents": [
                    {"id": "estc-company-overview", "type": "company_info"},
                    {"id": "estc-recent-news", "type": "news_data"},
                    {"id": "estc-market-trends", "type": "market_data"}
                ]
            })
    
    def get_mcp_calls(self) -> List[Dict[str, Any]]:
        """Get the MCP calls made during the last generation"""
        return self.mcp_calls.copy()
    
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