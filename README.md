# 🤖 AI Chatbot with Wikipedia Integration

A sophisticated conversational AI chatbot built with Flask that combines Google's Gemini AI with Wikipedia search capabilities, featuring user authentication, conversation history, and intelligent context awareness.

## ✨ Features

### 🎯 Core Capabilities
- **Dual AI Sources** - Powered by Google Gemini AI with Wikipedia fallback
- **Intelligent Query Detection** - Automatically routes Wikipedia queries for factual information
- **Code Generation** - Generate clean, well-commented code in multiple languages
- **Conversational Memory** - Maintains context across conversations
- **User Authentication** - Secure signup/login system with session management

### 💬 Conversation Features
- **Context-Aware Responses** - Remembers user names, preferences, and conversation history
- **Mood Detection** - Analyzes sentiment to provide appropriate responses
- **Multi-Source Responses** - Wikipedia for facts, Gemini for general conversation
- **Real-time Chat** - Instant responses with response time tracking
- **Message Validation** - Input sanitization and length limits

### 🛡️ Security & Performance
- **Rate Limiting** - 60 requests per minute per IP
- **Session Management** - 24-hour session timeout with activity tracking
- **Password Security** - Secure password hashing with Werkzeug
- **CORS Protection** - Configured for localhost only
- **Error Handling** - Comprehensive error catching and logging

### 📊 Data Management
- **Conversation History** - Stores up to 1,000 conversation entries
- **SQLite Database** - User data persistence
- **Search History** - Track and review past searches
- **Session Analytics** - Message counts and response time tracking

### 🎨 User Interface
- **Welcome Screen** - 3D animated splash screen on login
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Dark Mode Support** - Modern, eye-friendly interface
- **Real-time Updates** - Dynamic message display
- **Typing Indicators** - Visual feedback during processing

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Google Gemini API key (optional but recommended)

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd ai-chatbot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**

Create an `api.env` file in the project root:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
SECRET_KEY=your_secret_key_for_sessions
```

To get a Google Gemini API key:
- Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
- Sign in with your Google account
- Create a new API key
- Copy the key to your `api.env` file

4. **Initialize the database**
```bash
python app.py
```
The database will be created automatically on first run.

5. **Access the application**
Open your browser and navigate to: `http://localhost:5000`

## 📖 Usage Guide

### Getting Started
1. **Sign Up** - Create a new account with username, email, and password
2. **Login** - Use your credentials to access the chatbot
3. **Welcome Screen** - Enjoy the 3D animation before entering the chat
4. **Start Chatting** - Ask questions, request information, or generate code

### Query Types

#### Wikipedia Queries
The bot automatically detects and searches Wikipedia for factual questions:
```
"What is artificial intelligence?"
"Tell me about Albert Einstein"
"Explain quantum physics"
"Who is Elon Musk?"
```

#### Code Generation
Request code in any programming language:
```
"Write Python code to sort a list"
"Generate JavaScript code for a timer"
"Create a function to validate email"
```

#### General Conversation
Chat naturally about any topic:
```
"Hello, how are you?"
"What can you help me with?"
"Tell me a joke"
"My name is John"
```

### Features in Action

**Context Awareness**
```
You: "My name is Sarah"
Bot: "Nice to meet you, Sarah! How can I help you?"
You: "What's my name?"
Bot: "Your name is Sarah!"
```

**Conversation History**
- View all past conversations in the History page
- Search and filter by date
- Clear history when needed

## 🏗️ Project Structure

```
ai-chatbot/
│
├── app.py                      # Main Flask application
├── api.env                     # API keys and secrets (not in git)
├── requirements.txt            # Python dependencies
│
├── instance/
│   └── users.db               # SQLite database
│
├── templates/
│   ├── home.html              # Landing page
│   ├── signup.html            # User registration
│   ├── login.html             # User login
│   ├── welcome.html           # 3D splash screen
│   ├── intex.html             # Main chat interface
│   ├── history.html           # Conversation history
│   ├── 404.html               # Not found page
│   └── 500.html               # Error page
│
└── static/
    ├── css/
    │   └── styles.css         # Application styles
    └── js/
        └── chat.js            # Frontend JavaScript
```

## 🔧 Configuration

### Environment Variables
```python
GOOGLE_API_KEY       # Google Gemini API key
SECRET_KEY           # Flask session secret key
```

### Application Settings
Edit these in `app.py` under the `Config` class:
```python
MAX_HISTORY_ENTRIES = 1000          # Max conversation entries
API_TIMEOUT = 10                    # API request timeout (seconds)
SESSION_TIMEOUT_HOURS = 24          # Session expiration time
RATE_LIMIT_PER_MINUTE = 60         # Requests per minute per IP
MAX_MESSAGE_LENGTH = 2000           # Maximum message length
```

## 🌐 API Endpoints

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/signup` | POST | Create new user account |
| `/login` | POST | User authentication |
| `/logout` | GET | End user session |

### Chat
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message and get response |
| `/api/history` | GET | Retrieve conversation history |
| `/api/history/clear` | POST | Clear all history |

### System
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check and system status |
| `/welcome` | GET | Welcome splash screen |
| `/intex` | GET | Main chat interface |
| `/history` | GET | History page |

## 💡 Advanced Features

### Rate Limiting
The application implements IP-based rate limiting:
- 60 requests per minute per IP address
- Automatic cleanup of old tracking data
- 429 Too Many Requests response when exceeded

### Session Management
- Unique session IDs for each user
- 24-hour automatic timeout
- Activity tracking and message counting
- Session validation on each request

### Conversation Context
The bot maintains context including:
- User's name (if provided)
- Last 10 conversation exchanges
- Detected mood (positive/negative/neutral)
- Topics discussed
- User preferences

### Fallback System
When Gemini AI is unavailable, the bot uses:
1. Wikipedia search for factual queries
2. Pre-programmed responses for common queries
3. Contextual fallback messages

## 🔍 Conversation Enhancement

### Mood Detection
The system analyzes user messages for emotional content:
- **Positive**: great, awesome, love, excited, happy
- **Negative**: sad, angry, frustrated, disappointed
- **Neutral**: okay, fine, alright

### Name Recognition
Automatically extracts and remembers user names from phrases like:
- "My name is John"
- "Call me Sarah"
- "I am Michael"
- "I'm Emma"

## 🐛 Troubleshooting

### API Key Issues
**Problem**: "Running without AI - Wikipedia only"
**Solution**: 
- Ensure `GOOGLE_API_KEY` is set in `api.env`
- Verify the API key is valid and active
- Check your Google Cloud Console for API status

### Database Errors
**Problem**: "No such table: user"
**Solution**:
```bash
# Delete the database and restart
rm -rf instance/
python app.py
```

### Rate Limiting
**Problem**: "Too many requests. Please wait a minute."
**Solution**:
- Wait 60 seconds before sending more requests
- Reduce request frequency
- Contact admin to adjust rate limits

### Session Timeout
**Problem**: Logged out unexpectedly
**Solution**:
- Sessions expire after 24 hours of inactivity
- Simply log in again
- Adjust `SESSION_TIMEOUT_HOURS` if needed

## 📊 System Requirements

### Minimum Requirements
- Python 3.8+
- 100MB free disk space
- 512MB RAM
- Internet connection for API calls

### Recommended
- Python 3.10+
- 500MB free disk space
- 1GB RAM
- Stable internet connection (10+ Mbps)

## 🚀 Deployment

### Local Development
```bash
python app.py
# Access at http://localhost:5000
```

### Production Deployment

1. **Set environment variables**
```bash
export SECRET_KEY='your-production-secret-key'
export GOOGLE_API_KEY='your-api-key'
```

2. **Use production WSGI server**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

3. **Configure reverse proxy (nginx example)**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

4. **Security checklist**
- [ ] Change default SECRET_KEY
- [ ] Enable HTTPS
- [ ] Set DEBUG=False
- [ ] Configure CORS for production domain
- [ ] Set up database backups
- [ ] Implement logging
- [ ] Configure firewall rules

## 🔒 Security Best Practices

1. **Never commit `api.env` to version control**
   - Add to `.gitignore`
   - Use environment variables in production

2. **Use strong secret keys**
   ```python
   import secrets
   print(secrets.token_hex(32))
   ```

3. **Implement HTTPS in production**
   - Use Let's Encrypt for free SSL certificates
   - Redirect HTTP to HTTPS

4. **Regular security updates**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

## 📈 Monitoring & Analytics

### Health Check
```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00",
  "api_configured": true,
  "gemini_available": true,
  "backend_url": "http://localhost:5000"
}
```

### Logs
The application logs important events:
- User authentication
- API calls and responses
- Errors and exceptions
- Rate limiting events

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Google Gemini AI** - Conversational AI capabilities
- **Wikipedia API** - Comprehensive factual information
- **Flask** - Web framework
- **SQLAlchemy** - Database ORM

## 👨‍💻 Author

Created with ❤️ by Harish

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact: [your-email@example.com]
- Documentation: [your-docs-url]

## 🔄 Version History

### v1.0.0 (Current)
- Initial release
- Gemini AI integration
- Wikipedia search
- User authentication
- Conversation history
- Context awareness
- Rate limiting
- Welcome screen

### Roadmap
- [ ] Multi-language support
- [ ] Voice input/output
- [ ] Image analysis
- [ ] File upload support
- [ ] Admin dashboard
- [ ] User profiles
- [ ] Export conversations
- [ ] API rate plans

---

**Note**: This application requires active internet
