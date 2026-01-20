import os
import re
import time
import uuid
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from functools import wraps

# Third-party imports
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import wikipedia

# Optional imports with graceful fallback
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

# Configure logging - FIXED: Changed back to INFO
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv("api.env")

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configure CORS - ONLY LOCALHOST
# Configure CORS - Allow both localhost and 127.0.0.1
CORS(app, 
     origins=["http://localhost:5000", "http://127.0.0.1:5000"], 
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'OPTIONS']
)

# Database setup
db_path = os.path.join(app.root_path, 'instance', 'users.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

@dataclass
class Config:
    """Configuration class for application settings"""
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    MAX_HISTORY_ENTRIES: int = 1000
    API_TIMEOUT: int = 10
    SESSION_TIMEOUT_HOURS: int = 24
    RATE_LIMIT_PER_MINUTE: int = 60
    MAX_MESSAGE_LENGTH: int = 2000

config = Config()

# Configure Google Generative AI if available - FIXED: Correct import usage
if GENAI_AVAILABLE and config.GOOGLE_API_KEY:
    try:
        genai.configure(api_key=config.GOOGLE_API_KEY)
        logger.info("✅ Gemini AI Ready")
    except Exception as e:
        logger.error(f"⚠️ Gemini setup failed: {e}")
        GENAI_AVAILABLE = False
else:
    logger.warning("⚠️ Running without AI - Wikipedia only")

# Global data structures
conversation_history: List[Dict] = []
active_sessions: Dict[str, Dict] = {}
rate_limit_tracker: Dict[str, List[datetime]] = {}
user_contexts: Dict[str, Dict] = {}
history_lock = threading.Lock()
sessions_lock = threading.Lock()

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password = password

    def check_password(self, password):
        return self.password == password

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            if request.is_json:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

class RateLimiter:
    @staticmethod
    def is_rate_limited(client_ip: str) -> bool:
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(minutes=1)
            
            if client_ip not in rate_limit_tracker:
                rate_limit_tracker[client_ip] = []
            
            rate_limit_tracker[client_ip] = [
                timestamp for timestamp in rate_limit_tracker[client_ip] 
                if timestamp > cutoff_time
            ]
            
            if len(rate_limit_tracker[client_ip]) >= config.RATE_LIMIT_PER_MINUTE:
                return True
            
            rate_limit_tracker[client_ip].append(current_time)
            return False
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return False

class SessionManager:
    @staticmethod
    def create_session(user_ip: str) -> str:
        try:
            session_id = str(uuid.uuid4())
            current_time = datetime.now()
            
            with sessions_lock:
                active_sessions[session_id] = {
                    'created': current_time.isoformat(),
                    'last_activity': current_time.isoformat(),
                    'user_ip': user_ip,
                    'message_count': 0
                }
                # FIXED: Added missing interaction_count field
                user_contexts[session_id] = {
                    'conversation_history': [],
                    'user_name': None,
                    'topics_discussed': [],
                    'mood': 'neutral',
                    'preferences': {},
                    'last_topic': None,
                    'interaction_count': 0
                }
            
            return session_id
            
        except Exception as e:
            logger.error(f"Session creation error: {e}")
            return f"session_{int(time.time())}"
    
    @staticmethod
    def update_session(session_id: str) -> bool:
        try:
            with sessions_lock:
                if session_id in active_sessions:
                    active_sessions[session_id]['last_activity'] = datetime.now().isoformat()
                    active_sessions[session_id]['message_count'] += 1
                    return True
            return False
        except Exception as e:
            logger.error(f"Session update error: {e}")
            return False
    
    @staticmethod
    def is_valid_session(session_id: str) -> bool:
        try:
            if not session_id or session_id not in active_sessions:
                return False
            
            session_data = active_sessions[session_id]
            last_activity = datetime.fromisoformat(session_data['last_activity'])
            cutoff_time = datetime.now() - timedelta(hours=config.SESSION_TIMEOUT_HOURS)
            
            return last_activity > cutoff_time
            
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return False

class HistoryManager:
    """History manager with timestamps"""
    
    @staticmethod
    def add_conversation(user_msg: str, bot_reply: str, session_id: str, 
                        input_method: str = 'unknown', user_ip: str = 'unknown', 
                        response_time: float = 0.0) -> Dict:
        try:
            timestamp = datetime.now()
            entry = {
                'id': str(uuid.uuid4()),
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'date': timestamp.strftime('%Y-%m-%d'),
                'time': timestamp.strftime('%H:%M:%S'),
                'user': str(user_msg).strip(),
                'bot': str(bot_reply).strip(),
                'session_id': str(session_id),
                'input_method': str(input_method),
                'response_time': f"{response_time:.2f}s"
            }
            
            with history_lock:
                conversation_history.append(entry)
                if len(conversation_history) > config.MAX_HISTORY_ENTRIES:
                    conversation_history.pop(0)
            
            return entry
            
        except Exception as e:
            logger.error(f"Error adding conversation: {e}")
            return {}
    
    @staticmethod
    def get_recent_conversations(limit: int = 50) -> List[Dict]:
        try:
            with history_lock:
                recent_conversations = conversation_history[-limit:] if conversation_history else []
                return list(reversed(recent_conversations))
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []
    
    @staticmethod
    def clear_history() -> bool:
        try:
            with history_lock:
                conversation_history.clear()
            return True
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            return False

class ConversationEnhancer:
    """Enhance conversations with context and personality"""
    
    @staticmethod
    def update_context(session_id: str, user_msg: str, bot_reply: str):
        """Update conversation context for better continuity"""
        try:
            if session_id not in user_contexts:
                # FIXED: Ensure all fields are initialized
                user_contexts[session_id] = {
                    'conversation_history': [],
                    'user_name': None,
                    'topics_discussed': [],
                    'mood': 'neutral',
                    'preferences': {},
                    'last_topic': None,
                    'interaction_count': 0,
                }
            
            context = user_contexts[session_id]
            context['interaction_count'] += 1
            
            # Analyze mood
            mood_keywords = {
                'positive': ['great', 'awesome', 'love', 'excited', 'happy'],
                'negative': ['sad', 'angry', 'frustrated', 'disappointed'],
                'neutral': ['okay', 'fine', 'alright']
            }
            
            user_lower = user_msg.lower()
            detected_mood = 'neutral'
            for mood, keywords in mood_keywords.items():
                if any(kw in user_lower for kw in keywords):
                    detected_mood = mood
                    break
            context['mood'] = detected_mood
            
            # Update history
            context['conversation_history'].append({
                'user': user_msg,
                'bot': bot_reply,
                'timestamp': datetime.now().isoformat(),
                'mood': detected_mood
            })
            
            # Keep only last 10 exchanges
            if len(context['conversation_history']) > 10:
                context['conversation_history'] = context['conversation_history'][-10:]
            
            # Extract user name
            name_match = re.search(r'(?:my name is|call me|i am|i\'m)\s+(\w+)', user_msg.lower())
            if name_match:
                context['user_name'] = name_match.group(1).capitalize()
                
        except Exception as e:
            logger.error(f"Context update error: {e}")
    
    @staticmethod
    def get_enhanced_prompt(session_id: str, user_msg: str) -> str:
        """Create enhanced prompt with context"""
        try:
            if session_id not in user_contexts:
                return user_msg
            
            context = user_contexts[session_id]
            enhanced_parts = []
            
            enhanced_parts.append("You are a helpful and friendly AI assistant. Be conversational and engaging.")
            
            if context.get('user_name'):
                enhanced_parts.append(f"The user's name is {context['user_name']}.")
            
            if context['conversation_history']:
                recent = context['conversation_history'][-3:]
                history_text = "Recent conversation:\n"
                for exchange in recent:
                    history_text += f"User: {exchange['user'][:100]}\nAssistant: {exchange['bot'][:100]}\n"
                enhanced_parts.append(history_text)
            
            enhanced_parts.append(f"\nCurrent message: {user_msg}")
            enhanced_parts.append("\nRespond naturally and helpfully.")
            
            return "\n".join(enhanced_parts)
            
        except Exception as e:
            logger.error(f"Enhanced prompt error: {e}")
            return user_msg

class WikipediaService:
    def __init__(self):
        try:
            wikipedia.set_lang("en")
            wikipedia.set_rate_limiting(True)
            self.use_api_package = True
        except Exception as e:
            logger.error(f"Wikipedia init error: {e}")
            self.use_api_package = False
    
    def search_wikipedia(self, query: str) -> str:
        """Search Wikipedia and return content"""
        try:
            clean_query = self._clean_query(query)
            result = self._get_comprehensive_content(clean_query)
            return result if result else self._get_search_suggestions(clean_query)
        except Exception as e:
            logger.error(f"Wikipedia search error: {e}")
            return f"I couldn't find information about '{query}' on Wikipedia."
    
    def _clean_query(self, query: str) -> str:
        clean_query = query.strip()
        question_words = ['what is', 'who is', 'tell me about', 'explain', 'describe', 'define']
        for word in question_words:
            if clean_query.lower().startswith(word):
                clean_query = clean_query[len(word):].strip()
                break
        return clean_query
    
    def _get_comprehensive_content(self, query: str) -> Optional[str]:
        try:
            page = wikipedia.page(query, auto_suggest=True)
            return self._format_comprehensive_response(page)
        except wikipedia.DisambiguationError as e:
            if e.options:
                try:
                    page = wikipedia.page(e.options[0])
                    return self._format_comprehensive_response(page)
                except:
                    pass
            return self._handle_disambiguation(query, e.options[:5])
        except Exception as e:
            logger.error(f"Wikipedia content error: {e}")
            return None
    
    def _format_comprehensive_response(self, page) -> str:
        """Format Wikipedia response"""
        try:
            content = page.content
            
            paragraphs = []
            for p in content.split('\n\n'):
                p = p.strip()
                if (p and len(p) > 100 and not p.startswith('==')):
                    paragraphs.append(p)
            
            if not paragraphs:
                return None
            
            response_parts = [f"📚 **{page.title}**\n\n"]
            
            current_length = len(response_parts[0])
            target_length = 3500
            
            for para in paragraphs:
                if current_length + len(para) > 4000:
                    if current_length < 3000:
                        remaining = 4000 - current_length - 50
                        truncated = para[:remaining].rsplit('.', 1)[0] + '.'
                        response_parts.append(f"{truncated}\n\n")
                    break
                
                response_parts.append(f"{para}\n\n")
                current_length += len(para) + 2
                
                if current_length >= target_length:
                    break
            
            response_parts.append(f"🔗 *Source: Wikipedia*")
            
            return "".join(response_parts)
            
        except Exception as e:
            logger.error(f"Wikipedia format error: {e}")
            return None
    
    def _handle_disambiguation(self, query: str, options: List[str]) -> str:
        response_parts = [f"🔍 I found multiple topics for '{query}'. Here are the main ones:\n\n"]
        
        for i, option in enumerate(options[:5], 1):
            try:
                summary = wikipedia.summary(option, sentences=2, auto_suggest=False)
                response_parts.append(f"**{i}. {option}**\n{summary}\n\n")
            except:
                response_parts.append(f"**{i}. {option}**\n\n")
        
        response_parts.append("💡 Please be more specific!")
        return "".join(response_parts)
    
    def _get_search_suggestions(self, query: str) -> str:
        try:
            search_results = wikipedia.search(query, results=5)
            if not search_results:
                return f"I couldn't find any Wikipedia articles about '{query}'."
            
            response_parts = [f"🔎 I found these Wikipedia articles related to '{query}':\n\n"]
            
            for i, result in enumerate(search_results, 1):
                try:
                    summary = wikipedia.summary(result, sentences=2, auto_suggest=False)
                    response_parts.append(f"**{i}. {result}**\n{summary}\n\n")
                except:
                    response_parts.append(f"**{i}. {result}**\n\n")
            
            return "".join(response_parts)
            
        except Exception as e:
            logger.error(f"Wikipedia suggestions error: {e}")
            return f"I encountered an issue searching for '{query}'."
    
    @staticmethod
    def is_wikipedia_query(message: str) -> bool:
        """Detect if this is a Wikipedia query"""
        wiki_patterns = [
            r'\b(what is|who is|tell me about|explain|describe|define)\b',
            r'\b(wikipedia|facts about|information about)\b',
        ]
        return any(re.search(pattern, message.lower()) for pattern in wiki_patterns)

wikipedia_service = WikipediaService()

class AIService:
    """Enhanced AI service with error handling"""
    
    @staticmethod
    def get_response(message: str, session_id: str) -> dict:
        try:
            # Check Wikipedia first
            if WikipediaService.is_wikipedia_query(message):
                wiki_response = wikipedia_service.search_wikipedia(message)
                return {
                    'text': wiki_response,
                    'source': 'wikipedia',
                    'emoji': '🔍'
                }
            
            # Check for code generation
            if any(keyword in message.lower() for keyword in ['write code', 'generate code', 'python code', 'javascript code']):
                return AIService._get_gemini_code_response(message, session_id)
            
            # Regular conversation
            return AIService._get_gemini_response(message, session_id)
            
        except Exception as e:
            logger.error(f"AI Service error: {e}")
            return {
                'text': "I'm having trouble processing your request. Could you try rephrasing that?",
                'source': 'error',
                'emoji': '⚠️'
            }
    
    @staticmethod
    def _get_gemini_response(message: str, session_id: str) -> dict:
        """Get response from Gemini or fallback"""
        try:
            # Check if Gemini is available
            if not GENAI_AVAILABLE or not config.GOOGLE_API_KEY:
                return AIService._get_fallback_response(message, session_id)
            
            # Try Gemini - FIXED: Correct model initialization
            enhanced_message = ConversationEnhancer.get_enhanced_prompt(session_id, message)
            
            try:
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(enhanced_message)
                
                if response and hasattr(response, 'text') and response.text:
                    return {
                        'text': response.text,
                        'source': 'gemini',
                        'emoji': '🤖'
                    }
                else:
                    return AIService._get_fallback_response(message, session_id)
                    
            except Exception as e:
                logger.error(f"Gemini API error: {e}")
                return AIService._get_fallback_response(message, session_id)
            
        except Exception as e:
            logger.error(f"Gemini response error: {e}")
            return AIService._get_fallback_response(message, session_id)
    
    @staticmethod
    def _get_gemini_code_response(message: str, session_id: str) -> dict:
        """Get code generation response"""
        try:
            if not GENAI_AVAILABLE or not config.GOOGLE_API_KEY:
                return {
                    'text': "Code generation requires AI setup.",
                    'source': 'error',
                    'emoji': '💻'
                }
            
            enhanced_prompt = f"""Generate clean, well-commented code for: {message}

Please provide:
1. Complete, functional code
2. Clear comments
3. Example usage

Format with markdown code blocks."""
            
            try:
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(enhanced_prompt)
                response_text = response.text if (response and hasattr(response, 'text')) else "Couldn't generate code."
            except Exception as e:
                logger.error(f"Code generation error: {e}")
                response_text = "I couldn't generate code at this time."
            
            return {
                'text': f"**Code Generated**\n\n{response_text}",
                'source': 'gemini-code',
                'emoji': '💻'
            }
            
        except Exception as e:
            logger.error(f"Code generation error: {e}")
            return {
                'text': "I couldn't generate that code right now.",
                'source': 'error',
                'emoji': '⚠️'
            }
    
    @staticmethod
    def _get_fallback_response(message: str, session_id: str) -> dict:
        """Fallback responses when AI is unavailable"""
        message_lower = message.lower()
        context = user_contexts.get(session_id, {})
        user_name = context.get('user_name', '')
        name_greeting = f" {user_name}" if user_name else ""
        
        # Greeting
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good evening']):
            return {
                'text': f"👋 Hello{name_greeting}! I'm your AI assistant. How can I help you today?",
                'source': 'fallback',
                'emoji': '👋'
            }
        
        # How are you
        elif any(word in message_lower for word in ['how are you', 'how r u']):
            return {
                'text': f"I'm doing great{name_greeting}! Ready to help. What would you like to know?",
                'source': 'fallback',
                'emoji': '😊'
            }
        
        # Help/capabilities
        elif any(word in message_lower for word in ['help', 'what can you do']):
            return {
                'text': "I can help you with:\n\n📚 Search Wikipedia for information\n💬 Answer questions\n🤔 General conversation\n\nWhat would you like to explore?",
                'source': 'fallback',
                'emoji': '💡'
            }
        
        # Thanks
        elif any(word in message_lower for word in ['thank', 'thanks']):
            return {
                'text': f"You're welcome{name_greeting}! Happy to help anytime! 😊",
                'source': 'fallback',
                'emoji': '😊'
            }
        
        # Questions
        elif '?' in message:
            return {
                'text': "That's an interesting question! Try asking about specific topics and I'll search Wikipedia for accurate information.",
                'source': 'fallback',
                'emoji': '🤔'
            }
        
        # Default
        else:
            return {
                'text': f"I understand{name_greeting}! Feel free to ask me anything, especially factual topics I can research for you.",
                'source': 'fallback',
                'emoji': '💬'
            }

# Routes
# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not username or len(username) < 3:
            return jsonify({'success': False, 'message': 'Username must be at least 3 characters'}), 400
        
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Username already exists'}), 409
        
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already exists'}), 409
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({'success': True, 'redirect_url': url_for('login')}), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Signup error: {e}")
        return jsonify({'success': False, 'message': 'An error occurred during signup'}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = username
            session['logged_in'] = True
            # ✅ CHANGED: Redirect to welcome screen instead of intex
            return jsonify({'success': True, 'redirect_url': url_for('welcome')}), 200
        
        return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'message': 'Login failed. Please try again.'}), 500

# ✅ NEW ROUTE: Welcome splash screen (shows before chat)
@app.route('/welcome')
@login_required
def welcome():
    """Welcome splash screen with 3D animation before main chat"""
    return render_template('welcome.html')

@app.route('/intex')
@login_required
def intex():
    return render_template('intex.html')

@app.route('/history')
@login_required
def history():
    return render_template('history.html')

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})
    
    try:
        start_time = time.time()
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        # Rate limiting
        if RateLimiter.is_rate_limited(client_ip):
            return jsonify({'success': False, 'error': 'Too many requests. Please wait a minute.'}), 429
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
        
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', '')
        input_method = data.get('input_method', 'text')
        
        # Validate message
        if not user_message:
            return jsonify({'success': False, 'error': 'Message cannot be empty'}), 400
        
        if len(user_message) > config.MAX_MESSAGE_LENGTH:
            return jsonify({'success': False, 'error': f'Message too long. Maximum {config.MAX_MESSAGE_LENGTH} characters'}), 400
        
        # Session management
        if not session_id or not SessionManager.is_valid_session(session_id):
            session_id = SessionManager.create_session(client_ip)
        else:
            SessionManager.update_session(session_id)
        
        # Get AI response
        response_data = AIService.get_response(user_message, session_id)
        bot_response = response_data['text']
        source = response_data.get('source', 'unknown')
        emoji = response_data.get('emoji', '💬')
        
        # Update conversation context
        ConversationEnhancer.update_context(session_id, user_message, bot_response)
        
        response_time = time.time() - start_time
        
        # Save to history
        HistoryManager.add_conversation(
            user_message, bot_response, session_id, input_method, 
            client_ip, response_time
        )
        
        # Build response
        response_json = {
            'success': True,
            'response': bot_response,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'response_time': f"{response_time:.2f}s",
            'source': source,
            'emoji': emoji
        }
        
        return jsonify(response_json)
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({
            'success': False, 
            'error': 'Something went wrong. Please try again.'
        }), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Public API endpoint for history"""
    try:
        limit = request.args.get('limit', default=100, type=int)
        limit = min(limit, 500)
        conversations = HistoryManager.get_recent_conversations(limit)
        
        return jsonify({
            'success': True,
            'history': conversations,
            'count': len(conversations)
        })
    except Exception as e:
        logger.error(f"History fetch error: {e}")
        return jsonify({'success': False, 'error': 'Failed to load history'}), 500

@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """Public API endpoint for clearing history"""
    try:
        HistoryManager.clear_history()
        return jsonify({'success': True, 'message': 'History cleared successfully'})
    except Exception as e:
        logger.error(f"History clear error: {e}")
        return jsonify({'success': False, 'error': 'Failed to clear history'}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'api_configured': bool(config.GOOGLE_API_KEY),
        'gemini_available': GENAI_AVAILABLE,
        'backend_url': 'http://localhost:5000'
    })

# Error handlers
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Endpoint not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}", exc_info=True)
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    return render_template('500.html'), 500

# MAIN EXECUTION - THIS WAS MISSING!
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        logger.info("=" * 60)
        logger.info("🚀 Flask Server Starting")
        logger.info("=" * 60)
        logger.info(f"🌐 Backend URL: http://localhost:5000")
        logger.info(f"🔑 Google API configured: {bool(config.GOOGLE_API_KEY)}")
        logger.info(f"🤖 Gemini available: {GENAI_AVAILABLE}")
        logger.info(f"📚 Wikipedia service: Active")
        if not config.GOOGLE_API_KEY:
            logger.warning("⚠️  No API key found - Running in FALLBACK MODE")
            logger.warning("⚠️  Create api.env with GOOGLE_API_KEY=your_key")
        logger.info("=" * 60)
    
    # THIS LINE ACTUALLY STARTS THE SERVER - YOU WERE MISSING THIS!
    # Using 0.0.0.0 to make it accessible on both localhost and 127.0.0.1
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)