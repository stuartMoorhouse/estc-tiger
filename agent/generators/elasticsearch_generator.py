import json
import asyncio
from typing import Dict, Any, List, Optional
from anthropic import Anthropic
import os
import time
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from shared.elasticsearch_client import elasticsearch_client
from shared.conversation_memory import conversation_memory

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
            # Reset MCP calls tracking for this query
            self.mcp_calls = []
            
            # Get or create session for conversation memory
            session_id = conversation_memory.get_or_create_session(session_id)
            
            # Analyze query intent and retrieve relevant data
            retrieved_data = await self._retrieve_elasticsearch_data(user_query)
            
            # Build system message with retrieved data and conversation context
            system_message = self._build_system_message(retrieved_data, session_id)
            
            # Create user message for Claude with context
            user_message = self._build_user_message(user_query, retrieved_data, session_id)
            
            # Call Claude to generate response
            response = await self._call_claude_api(system_message, user_message)
            
            # Post-process for better readability
            formatted_response = self._format_response(response)
            
            # Add this exchange to conversation memory
            conversation_memory.add_exchange(
                session_id=session_id,
                user_query=user_query,
                assistant_response=formatted_response,
                mcp_calls=self.mcp_calls
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
            # No data retrieved at all - use static baseline data
            data_context = """
        
        BASELINE DATA CONTEXT:
        - Current revenue: $1.48B (+17% YoY)
        - Current stock price: $85.71
        - Analyst target: $115.74 (35% upside)
        - Cloud revenue growth: 30% YoY
        - GenAI customers: 1,750+
        - Operating margin: 12% (non-GAAP)
        
        This baseline data provides sufficient context for actionable investment insights.
        """
        
        guidelines = """
        
        Guidelines:
        - Be direct and concise
        - Focus on actionable investment insights
        - Use BOTH your training data AND the retrieved MCP data to provide comprehensive analysis
        - Help with RSU timing and tax considerations
        - Compare to competitors when relevant
        - Reference previous conversation context when relevant for continuity
        - Always provide confident, definitive responses using all available information
        - NEVER mention incomplete datasets, missing data, or need for more information
        - Combine training knowledge with MCP data for complete, actionable analysis
        
        Citation Requirements:
        - After every fact or data point retrieved from the MCP server, add a citation in square brackets
        - Citation format: [index_name, document_id]
        - Example: "ESTC revenue is $1.48B [estc-financial-data, doc-revenue-2024]"
        - Only add citations for facts that came from the retrieved MCP data, not general knowledge
        - Citations should be placed immediately after the specific fact or statistic
        - Do not cite general market knowledge or training data
        
        Formatting requirements:
        - Use clear paragraph breaks between different topics
        - Break up long text into digestible sections
        - Use line breaks after bullet points and before new topics
        - Structure responses with clear sections (e.g., "Key Metrics:", "Investment Perspective:", etc.)
        
        Always provide confident, comprehensive responses about ESTC combining training knowledge with MCP data.
        """
        
        # Add conversation context if available
        conversation_context = ""
        if session_id:
            conversation_context = conversation_memory.get_context_for_llm(session_id)
        
        return base_message + data_context + guidelines + conversation_context
    
    def _build_user_message(self, user_query: str, retrieved_data: Dict[str, Any], session_id: str = None) -> str:
        """Build user message with retrieved data context and conversation continuity"""
        
        search_results = retrieved_data.get('search_results', {})
        
        base_message = f"""
        User is asking about ESTC (Elastic stock): {user_query}
        """
        
        if search_results.get('results'):
            # Include retrieved data in the message
            data_section = "\n\nRETRIEVED DATA:\n"
            
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
            
            instruction = """
            
            Based on the retrieved data above AND your training knowledge, provide a comprehensive response about ESTC that directly addresses the user's question. 
            Use specific information from the documents to support your analysis, supplemented with your general market knowledge.
            Consider the conversation context if this is a follow-up question.
            
            IMPORTANT: 
            - Add citations in square brackets [index_name, document_id] ONLY after facts that come from the retrieved data above
            - Do not cite general market knowledge or training data
            - Use both MCP data and training knowledge to provide confident, complete analysis
            - Never mention incomplete datasets or missing data
            - Combine all available information to provide actionable investment insights
            - Fill gaps in MCP data with relevant training knowledge (without citations)
            """
            
        else:
            # No data retrieved
            connection_status = retrieved_data.get('connection_status', False)
            if not connection_status:
                data_section = "\n\nNOTE: Elasticsearch connection not available. Using general ESTC knowledge.\n"
            else:
                data_section = "\n\nNOTE: No specific documents found for this query. Using general ESTC knowledge.\n"
            
            instruction = """
            
            Please provide a confident, actionable response about ESTC based on the baseline data provided in the system message.
            Consider the conversation context if this is a follow-up question.
            Do not use hedging language about limited data - the baseline data is sufficient for meaningful analysis.
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
    
    async def _retrieve_elasticsearch_data(self, user_query: str) -> Dict[str, Any]:
        """Retrieve relevant ESTC data from Elasticsearch using MCP client"""
        
        # Analyze query intent to determine what data to search for
        query_analysis = elasticsearch_client.analyze_query_intent(user_query)
        
        # Perform search based on analyzed intent
        search_results = elasticsearch_client.search_estc_data(
            query_type=query_analysis['primary_type'],
            search_terms=query_analysis['search_terms'],
            limit=10
        )
        
        # Track MCP calls for logging
        if search_results.get('results'):
            self.mcp_calls.append({
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
        
        return {
            "query_analysis": query_analysis,
            "search_results": search_results,
            "connection_status": elasticsearch_client.is_connected(),
            "cluster_info": elasticsearch_client.get_cluster_info()
        }
    
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