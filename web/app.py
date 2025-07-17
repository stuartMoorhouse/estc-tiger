import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Add parent directory to path so we can import agent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your agent components
try:
    from agent.evaluators.security_evaluator import SecurityEvaluator
    from agent.generators.elasticsearch_generator import ElasticsearchGenerator
    from agent.evaluators.output_evaluator import OutputEvaluator
    from shared.ecs_logger import logger
    
    # Initialize components
    security_evaluator = SecurityEvaluator()
    elasticsearch_generator = ElasticsearchGenerator()
    output_evaluator = OutputEvaluator()
    
    AGENT_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import agent components: {e}")
    print("Chat functionality will be limited.")
    AGENT_COMPONENTS_AVAILABLE = False

# Create Flask app
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/estc-stock')
def get_estc_stock():
    try:
        finnhub_key = os.getenv('FINNHUB_API_KEY')
        if not finnhub_key:
            return jsonify({'error': 'Finnhub API key not found'}), 500
        
        # Get current price
        current_url = f"https://finnhub.io/api/v1/quote?symbol=ESTC&token={finnhub_key}"
        current_response = requests.get(current_url)
        current_data = current_response.json()
        
        # Get historical data (30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        
        history_url = f"https://finnhub.io/api/v1/stock/candle?symbol=ESTC&resolution=D&from={start_timestamp}&to={end_timestamp}&token={finnhub_key}"
        history_response = requests.get(history_url)
        history_data = history_response.json()
        
        # Process historical data
        if history_data.get('s') == 'ok':
            dates = []
            prices = []
            
            for i, timestamp in enumerate(history_data['t']):
                date = datetime.fromtimestamp(timestamp)
                dates.append(date.strftime('%Y-%m-%d'))
                prices.append(history_data['c'][i])  # closing price
            
            return jsonify({
                'success': True,
                'dates': dates,
                'prices': prices,
                'currentPrice': current_data.get('c', 0),  # current price
                'previousClose': current_data.get('pc', 0),  # previous close
                'change': current_data.get('d', 0),  # change
                'changePercent': current_data.get('dp', 0)  # change percent
            })
        else:
            return jsonify({'error': 'Failed to get historical data'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        if not AGENT_COMPONENTS_AVAILABLE:
            return jsonify({
                'success': True,
                'response': "I'm a simple ESTC chatbot. The full agent system isn't available right now, but you can still view the stock chart above!",
                'blocked': False
            })
        
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'success': False, 'error': 'No message provided'})
        
        # Run the evaluator-optimizer workflow
        result = asyncio.run(run_workflow(user_message))
        
        return jsonify({
            'success': True,
            'response': result['response'],
            'blocked': result['blocked']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

async def run_workflow(user_message):
    """Run the Evaluator-Optimizer workflow with comprehensive logging"""
    start_time = time.time()
    
    try:
        if not AGENT_COMPONENTS_AVAILABLE:
            return {
                'response': "Agent components not available. Please check your setup.",
                'blocked': False
            }
        
        # Log initial user query
        query_id = logger.log_user_query(user_message)
        
        # Stage 1: Security Evaluation
        security_start = time.time()
        security_result = await security_evaluator.evaluate(user_message)
        security_duration = int((time.time() - security_start) * 1000)
        
        # Log security evaluation
        patterns_matched = security_result.get('pattern_matched', [])
        if patterns_matched:
            patterns_matched = [patterns_matched]
        logger.log_security_evaluation(query_id, user_message, security_result, 
                                     security_duration, patterns_matched)
        
        if not security_result['safe']:
            total_duration = int((time.time() - start_time) * 1000)
            logger.log_final_response(query_id, security_result['reason'], True, total_duration)
            return {
                'response': security_result['reason'],
                'blocked': True
            }
        
        # Stage 2: Generation
        generation_start = time.time()
        generator_response = await elasticsearch_generator.generate(user_message)
        generation_duration = int((time.time() - generation_start) * 1000)
        
        # Log generation with MCP calls
        mcp_calls = elasticsearch_generator.get_mcp_calls()
        logger.log_elasticsearch_generation(query_id, user_message, generator_response, 
                                          generation_duration, mcp_calls)
        
        # Stage 3: Output Evaluation
        output_start = time.time()
        output_result = await output_evaluator.evaluate(generator_response, user_message)
        output_duration = int((time.time() - output_start) * 1000)
        
        # Log output evaluation
        logger.log_output_evaluation(query_id, generator_response, output_result, output_duration)
        
        if not output_result['approved']:
            total_duration = int((time.time() - start_time) * 1000)
            logger.log_final_response(query_id, output_result['feedback'], True, total_duration)
            return {
                'response': output_result['feedback'],
                'blocked': True
            }
        
        # Log successful final response
        total_duration = int((time.time() - start_time) * 1000)
        logger.log_final_response(query_id, generator_response, False, total_duration)
        
        return {
            'response': generator_response,
            'blocked': False
        }
        
    except Exception as e:
        total_duration = int((time.time() - start_time) * 1000)
        error_msg = f"I encountered an error processing your request: {str(e)}"
        
        # Log error if we have a query_id
        if 'query_id' in locals():
            logger.log_error(query_id, str(e), "workflow", total_duration)
            logger.log_final_response(query_id, error_msg, False, total_duration)
        
        return {
            'response': error_msg,
            'blocked': False
        }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)