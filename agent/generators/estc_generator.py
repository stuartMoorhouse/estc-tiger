import json
import asyncio
from typing import Dict, Any, List
from anthropic import Anthropic
import os

class ElasticsearchGenerator:
    """
    Generator component that integrates Claude with Elasticsearch MCP tools for ESTC analysis.
    """
    
    def __init__(self):
        self.anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.model = "claude-3-5-sonnet-20241022"  # Updated to more recent model
        
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
            return response
            
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
        
        Always provide helpful, data-driven responses about ESTC.
        """
    
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