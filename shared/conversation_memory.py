import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import threading
import logging

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Manages conversation sessions and memory for the ESTC Tiger chatbot.
    Stores conversation history in memory with automatic cleanup.
    """
    
    def __init__(self, max_sessions: int = 1000, session_timeout_hours: int = 24):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.max_sessions = max_sessions
        self.session_timeout = timedelta(hours=session_timeout_hours)
        self.lock = threading.Lock()
        
        # Token limits for memory management
        self.max_conversation_tokens = 4000  # Reserve space for current query
        self.avg_tokens_per_exchange = 200   # Estimate for Q&A pair
        
    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        """Get existing session or create new one"""
        with self.lock:
            if session_id and session_id in self.sessions:
                # Update last accessed time
                self.sessions[session_id]['last_accessed'] = datetime.now()
                return session_id
            
            # Create new session
            new_session_id = str(uuid.uuid4())
            self.sessions[new_session_id] = {
                'created_at': datetime.now(),
                'last_accessed': datetime.now(),
                'conversation_history': [],
                'current_price_mentioned': False
            }
            
            # Clean up old sessions if we're at the limit
            self._cleanup_old_sessions()
            
            return new_session_id
    
    def add_exchange(self, session_id: str, user_query: str, assistant_response: str, 
                    api_calls: List[Dict[str, Any]] = None) -> None:
        """Add a Q&A exchange to the conversation history"""
        with self.lock:
            if session_id not in self.sessions:
                session_id = self.get_or_create_session(session_id)
            
            exchange = {
                'timestamp': datetime.now().isoformat(),
                'user_query': user_query,
                'assistant_response': assistant_response,
                'api_calls': api_calls or []
            }
            
            self.sessions[session_id]['conversation_history'].append(exchange)
            self.sessions[session_id]['last_accessed'] = datetime.now()
            
            # Trim history if it's getting too long
            self._trim_conversation_history(session_id)
    
    def get_conversation_history(self, session_id: str, include_current: bool = True) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        with self.lock:
            if session_id not in self.sessions:
                return []
            
            history = self.sessions[session_id]['conversation_history'].copy()
            
            if not include_current and history:
                # Exclude the most recent exchange
                history = history[:-1]
            
            return history
    
    def get_context_for_llm(self, session_id: str) -> str:
        """Get formatted conversation context for LLM prompts"""
        history = self.get_conversation_history(session_id, include_current=False)
        
        if not history:
            return ""
        
        context = "\n\nPREVIOUS CONVERSATION CONTEXT:\n"
        context += "=" * 50 + "\n"
        context += "The following is your conversation history with this user. Use this to maintain continuity and reference previous exchanges.\n\n"
        
        # Include recent exchanges (limited by token count)
        max_exchanges = min(len(history), self.max_conversation_tokens // self.avg_tokens_per_exchange)
        recent_history = history[-max_exchanges:] if max_exchanges > 0 else []
        
        for i, exchange in enumerate(recent_history, 1):
            context += f"Exchange {i}:\n"
            context += f"USER: {exchange['user_query']}\n"
            context += f"YOUR PREVIOUS RESPONSE: {exchange['assistant_response'][:300]}{'...' if len(exchange['assistant_response']) > 300 else ''}\n\n"
        
        context += "=" * 50
        context += "\nIMPORTANT: You DO have access to this conversation history. Reference it when answering follow-up questions.\n"
        
        return context
    
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get session information"""
        with self.lock:
            if session_id not in self.sessions:
                return {}
            
            session = self.sessions[session_id]
            return {
                'session_id': session_id,
                'created_at': session['created_at'].isoformat(),
                'last_accessed': session['last_accessed'].isoformat(),
                'exchange_count': len(session['conversation_history']),
                'active': True
            }
    
    def clear_session(self, session_id: str) -> bool:
        """Clear a specific session"""
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False
    
    def _trim_conversation_history(self, session_id: str) -> None:
        """Trim conversation history to stay within token limits"""
        if session_id not in self.sessions:
            return
        
        history = self.sessions[session_id]['conversation_history']
        max_exchanges = self.max_conversation_tokens // self.avg_tokens_per_exchange
        
        if len(history) > max_exchanges:
            # Keep the most recent exchanges
            self.sessions[session_id]['conversation_history'] = history[-max_exchanges:]
            logger.info(f"Trimmed conversation history for session {session_id} to {max_exchanges} exchanges")
    
    def _cleanup_old_sessions(self) -> None:
        """Remove old or excess sessions"""
        current_time = datetime.now()
        sessions_to_remove = []
        
        # Find expired sessions
        for session_id, session_data in self.sessions.items():
            if current_time - session_data['last_accessed'] > self.session_timeout:
                sessions_to_remove.append(session_id)
        
        # Remove expired sessions
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
            logger.info(f"Removed expired session {session_id}")
        
        # If still too many sessions, remove oldest
        if len(self.sessions) > self.max_sessions:
            sorted_sessions = sorted(
                self.sessions.items(),
                key=lambda x: x[1]['last_accessed']
            )
            
            excess_count = len(self.sessions) - self.max_sessions
            for session_id, _ in sorted_sessions[:excess_count]:
                del self.sessions[session_id]
                logger.info(f"Removed excess session {session_id}")
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        with self.lock:
            return len(self.sessions)
    
    def get_total_exchanges_count(self) -> int:
        """Get total number of exchanges across all sessions"""
        with self.lock:
            return sum(len(session['conversation_history']) for session in self.sessions.values())
    
    def has_current_price_been_mentioned(self, session_id: str) -> bool:
        """Check if current stock price has been mentioned in this session"""
        with self.lock:
            if session_id not in self.sessions:
                # Create session inline to avoid lock issues
                self.sessions[session_id] = {
                    'created_at': datetime.now(),
                    'last_accessed': datetime.now(),
                    'conversation_history': [],
                    'current_price_mentioned': False
                }
            return self.sessions[session_id].get('current_price_mentioned', False)
    
    def mark_current_price_mentioned(self, session_id: str) -> None:
        """Mark that current stock price has been mentioned in this session"""
        with self.lock:
            if session_id not in self.sessions:
                # Create session inline to avoid lock issues
                self.sessions[session_id] = {
                    'created_at': datetime.now(),
                    'last_accessed': datetime.now(),
                    'conversation_history': [],
                    'current_price_mentioned': True
                }
            else:
                self.sessions[session_id]['current_price_mentioned'] = True

# Global instance
conversation_manager = ConversationManager()