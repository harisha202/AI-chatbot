const BACKEND_URL = "http://localhost:5000";

class VoiceAssistant {
  constructor() {
    this.isListening = false;
    this.isProcessing = false;
    this.recognition = null;
    this.conversationHistory = [];
    this.currentSession = this.generateSessionId();
    this.retryCount = 0;
    this.maxRetries = 3;
    this.abortController = null;
    this.requestStartTime = null;

    this.chatContainer = document.getElementById("chat-container");
    this.messageInput = document.getElementById("message-input");
    this.sendButton = document.getElementById("send-btn");
    this.voiceButton = document.getElementById("voice-btn");
    this.cancelMicButton = document.getElementById("cancel-mic-btn");
    this.typingIndicator = document.getElementById("typing-indicator");
    this.welcomeMessage = document.getElementById("welcome-message");
    this.soundWaves = document.getElementById("sound-waves");
    this.pulseRing = document.getElementById("pulse-ring");
    this.listeningOverlay = document.getElementById("listening-overlay");
    this.transcriptText = document.getElementById("transcript-text");

    this.isHistoryPage = window.location.pathname.includes('history');

    if (this.isHistoryPage) {
      this.loadHistory();
    } else {
      this.init();
    }
    
    this.applyMediumFontSizes();
  }

  applyMediumFontSizes() {
    console.log('📝 Applying medium font sizes...');
    
    document.documentElement.style.setProperty('--font-size-base', '18px');
    document.documentElement.style.setProperty('--font-size-large', '22px');
    document.documentElement.style.setProperty('--font-size-xlarge', '32px');
    
    if (this.chatContainer) {
      this.chatContainer.style.fontSize = '18px';
      this.chatContainer.style.lineHeight = '1.7';
    }
    
    if (this.messageInput) {
      this.messageInput.style.fontSize = '22px';
      this.messageInput.style.padding = '16px 20px';
    }
    
    if (this.sendButton) {
      this.sendButton.style.fontSize = '32px';
      this.sendButton.style.padding = '12px 20px';
    }
    
    if (this.voiceButton) {
      this.voiceButton.style.fontSize = '32px';
      this.voiceButton.style.padding = '12px 20px';
    }
    
    if (this.welcomeMessage) {
      const h2 = this.welcomeMessage.querySelector('h2');
      const p = this.welcomeMessage.querySelector('p');
      if (h2) h2.style.fontSize = '3rem';
      if (p) p.style.fontSize = '1.5rem';
    }
    
    document.body.style.fontSize = '18px';
    document.body.style.lineHeight = '1.7';
    
    console.log('✅ Medium font sizes applied');
  }

  generateSessionId() {
    return '_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
  }

  init() {
    if (!this.chatContainer) {
      console.error("❌ Chat container not found!");
      return;
    }
    
    console.log('🚀 Initializing Voice Assistant...');
    this.setupSpeechRecognition();
    this.setupEventListeners();
    this.checkServerConnection();
  }

  setupSpeechRecognition() {
    console.log('🎤 Setting up speech recognition...');
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      console.error("❌ Speech recognition not supported");
      if (this.voiceButton) {
        this.voiceButton.disabled = true;
        this.voiceButton.title = "Speech recognition not supported in this browser";
        this.voiceButton.style.opacity = "0.5";
      }
      return;
    }

    try {
      this.recognition = new SpeechRecognition();
      this.recognition.lang = "en-US";
      this.recognition.interimResults = true;
      this.recognition.continuous = false;
      this.recognition.maxAlternatives = 1;

      console.log('✅ Speech recognition configured');

      this.recognition.onstart = () => {
        console.log('✅ Listening STARTED');
        this.isListening = true;
        this.updateUI('listening');
        this.showListeningAnimation();
      };

      this.recognition.onresult = (event) => {
        let finalTranscript = "";
        let interimTranscript = "";
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          if (result.isFinal) {
            finalTranscript += result[0].transcript;
          } else {
            interimTranscript += result[0].transcript;
          }
        }

        if (interimTranscript) {
          console.log(`🎤 Interim: "${interimTranscript}"`);
          this.updateTranscript(interimTranscript);
        }

        if (finalTranscript.trim()) {
          const confidence = event.results[event.results.length - 1][0].confidence || 0;
          console.log(`✅ Final: "${finalTranscript.trim()}" (confidence: ${confidence.toFixed(2)})`);
          this.hideListeningAnimation();
          this.processUserInput(finalTranscript.trim(), confidence, 'voice');
        }
      };

      this.recognition.onerror = (event) => {
        console.error("❌ Speech error:", event.error);
        this.handleRecognitionError(event.error);
      };

      this.recognition.onend = () => {
        console.log('🔴 Listening ended');
        this.isListening = false;
        this.retryCount = 0;
        this.hideListeningAnimation();
        this.updateUI('idle');
      };

      console.log('✅ Speech recognition setup complete');

    } catch (err) {
      console.error("❌ Error creating speech recognition:", err);
    }
  }

  showListeningAnimation() {
    // Show sound waves
    if (this.soundWaves) {
      this.soundWaves.classList.add('active');
    }
    
    // Show pulse ring
    if (this.pulseRing) {
      this.pulseRing.classList.add('active');
    }
    
    // Show listening overlay
    if (this.listeningOverlay) {
      this.listeningOverlay.classList.add('active');
    }
    
    // Show cancel button
    if (this.cancelMicButton) {
      this.cancelMicButton.classList.add('active');
    }
  }

  hideListeningAnimation() {
    // Hide sound waves
    if (this.soundWaves) {
      this.soundWaves.classList.remove('active');
    }
    
    // Hide pulse ring
    if (this.pulseRing) {
      this.pulseRing.classList.remove('active');
    }
    
    // Hide listening overlay
    if (this.listeningOverlay) {
      this.listeningOverlay.classList.remove('active');
    }
    
    // Hide cancel button
    if (this.cancelMicButton) {
      this.cancelMicButton.classList.remove('active');
    }
  }

  updateTranscript(text) {
    if (this.transcriptText) {
      this.transcriptText.textContent = text || 'Speak now...';
    }
  }

  handleRecognitionError(error) {
    console.error(`❌ Recognition error: ${error}`);
    this.hideListeningAnimation();
    
    switch (error) {
      case 'no-speech':
        if (this.retryCount < this.maxRetries) {
          this.retryCount++;
          console.log(`⚠️ Retry ${this.retryCount}/${this.maxRetries}`);
          this.showNotification(`No speech detected. Retrying... (${this.retryCount}/${this.maxRetries})`, 'warning');
          setTimeout(() => this.startListening(), 1000);
          return;
        }
        this.showNotification("❌ No speech detected. Please speak clearly and try again.", 'error');
        break;
        
      case 'audio-capture':
        this.showNotification("❌ No microphone detected! Please connect a microphone.", 'error');
        break;
        
      case 'not-allowed':
        this.showNotification("❌ Microphone access blocked! Please allow microphone access in your browser settings.", 'error');
        break;
        
      case 'network':
        this.showNotification("❌ Network error. Please check your internet connection.", 'error');
        break;
        
      case 'aborted':
        console.log('ℹ️ Recognition aborted by user');
        break;
        
      default:
        this.showNotification(`❌ Speech recognition error: ${error}`, 'error');
    }

    this.isListening = false;
    this.updateUI('idle');
  }

  setupEventListeners() {
    console.log('🔧 Setting up event listeners...');
    
    if (this.voiceButton) {
      this.voiceButton.addEventListener("click", () => {
        console.log('🖱️ Voice button clicked');
        this.toggleListening();
      });
      console.log('✅ Voice button ready');
    }

    if (this.cancelMicButton) {
      this.cancelMicButton.addEventListener("click", () => {
        console.log('🖱️ Cancel button clicked');
        this.stopListening();
      });
      console.log('✅ Cancel button ready');
    }

    if (this.sendButton) {
      this.sendButton.addEventListener("click", () => this.sendTypedMessage());
      console.log('✅ Send button ready');
    }
    
    if (this.messageInput) {
      this.messageInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          this.sendTypedMessage();
        }
      });
      console.log('✅ Message input ready');
    }

    document.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && e.ctrlKey) {
        e.preventDefault();
        this.toggleListening();
      }
      if (e.code === 'Escape' && this.isListening) {
        e.preventDefault();
        this.stopListening();
      }
    });
    console.log('✅ Keyboard shortcuts ready (Ctrl+Space to toggle voice, Escape to stop)');
  }

  sendTypedMessage() {
    if (!this.messageInput) return;
    
    const message = this.messageInput.value.trim();
    if (!message) {
      this.showNotification("⚠️ Please enter a message", 'warning');
      return;
    }
    
    if (this.isProcessing) {
      this.showNotification("⚠️ Please wait for the current message to finish processing", 'warning');
      return;
    }

    console.log(`📤 Sending typed message: "${message}"`);
    this.messageInput.value = "";
    this.processUserInput(message, 1.0, 'text');
  }

  toggleListening() {
    console.log('🔄 Toggling listening state');
    if (this.isListening || this.isProcessing) {
      this.stopListening();
    } else {
      this.startListening();
    }
  }

  async startListening() {
    console.log('▶️ Attempting to start listening...');
    
    if (this.isListening) {
      console.log('⚠️ Already listening');
      return;
    }
    
    if (this.isProcessing) {
      console.log('⚠️ Currently processing a message');
      this.showNotification("⚠️ Please wait for the current response to finish", 'warning');
      return;
    }
    
    if (!this.recognition) {
      console.error('❌ Speech recognition not available');
      this.showNotification("❌ Speech recognition is not available in this browser. Please use Chrome, Edge, or Safari.", 'error');
      return;
    }
    
    try {
      console.log('🎤 Requesting microphone permission...');
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('✅ Microphone permission granted!');
      
      stream.getTracks().forEach(track => track.stop());
      
      console.log('🎤 Starting speech recognition...');
      this.recognition.start();
      this.retryCount = 0;
      
    } catch (err) {
      console.error('❌ Microphone access error:', err);
      
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        this.showNotification("❌ Microphone permission denied! Please allow microphone access in your browser settings.", 'error');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        this.showNotification("❌ No microphone found! Please connect a microphone and try again.", 'error');
      } else {
        this.showNotification("❌ Microphone error: " + err.message, 'error');
      }
      
      this.updateUI('idle');
    }
  }

  stopListening() {
    console.log('⏹️ Stopping speech recognition...');
    
    this.isListening = false;
    this.isProcessing = false;
    
    if (this.recognition) {
      try {
        this.recognition.stop();
        console.log('✅ Recognition stopped');
      } catch (err) {
        console.error("⚠️ Error stopping recognition:", err);
      }
    }
    
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    
    this.retryCount = 0;
    this.hideListeningAnimation();
    this.updateUI('idle');
  }

  async processUserInput(userInput, confidence = 0, inputType = 'voice') {
    console.log(`🔄 Processing input: "${userInput}" (${inputType}, confidence: ${confidence.toFixed(2)})`);
    
    if (!userInput || !userInput.trim()) return;
    
    this.isProcessing = true;
    this.updateUI('processing');
    
    if (this.welcomeMessage) {
      this.welcomeMessage.style.display = 'none';
    }
    
    this.addUserMessage(userInput, inputType);
    this.showTyping();
    
    this.requestStartTime = Date.now();
    this.abortController = new AbortController();

    try {
      const requestData = {
        message: userInput,
        confidence: confidence,
        input_method: inputType,
        session_id: this.currentSession,
        timestamp: new Date().toISOString()
      };

      console.log('📡 Sending request to backend:', requestData);

      const response = await fetch(`${BACKEND_URL}/api/chat`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify(requestData),
        signal: this.abortController.signal
      });

      console.log('📥 Response status:', response.status);

      if (!response.ok) {
        let errorDetails;
        try {
          errorDetails = await response.json();
          console.error('❌ Server error response (JSON):', errorDetails);
        } catch (e) {
          errorDetails = await response.text();
          console.error('❌ Server error response (Text):', errorDetails);
        }
        
        const errorMessage = errorDetails.error || errorDetails.message || errorDetails || 'Unknown server error';
        throw new Error(`Server error ${response.status}: ${errorMessage}`);
      }

      const data = await response.json();
      console.log('✅ Response data received:', data);
      
      this.hideTyping();
      
      if (data.success && data.response) {
        this.addBotMessage(data.response, data.gif_url);
        
        this.conversationHistory.push({
          user: userInput,
          bot: data.response,
          confidence: confidence,
          input_type: inputType,
          timestamp: data.timestamp || new Date().toISOString(),
          response_time: data.response_time || this.calculateResponseTime(),
          gif_url: data.gif_url || ''
        });
        
        console.log(`✅ Response received in ${data.response_time || '0s'}`);
      } else {
        console.error('❌ Invalid response data:', data);
        this.showError(data.error || "Invalid response from server");
      }
    } catch (err) {
      this.hideTyping();
      if (err.name === 'AbortError') {
        console.log('ℹ️ Request cancelled by user');
        this.showNotification("Request cancelled", 'info');
      } else {
        console.error('❌ Error processing request:', err);
        console.error('❌ Error stack:', err.stack);
        
        const errorMsg = err.message || 'Unknown error occurred';
        this.showError(`${errorMsg}\n\nPlease check:\n1. Flask server is running on http://localhost:5000\n2. No Python errors in terminal\n3. API key configured in api.env file`);
      }
    } finally {
      this.isProcessing = false;
      this.updateUI('idle');
      this.abortController = null;
    }
  }

  calculateResponseTime() {
    if (this.requestStartTime) {
      return `${((Date.now() - this.requestStartTime) / 1000).toFixed(2)}s`;
    }
    return '0.5s';
  }

  addUserMessage(text, inputType = 'text') {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message user-message';
    
    msgDiv.style.fontSize = '22px';
    msgDiv.style.lineHeight = '1.7';
    msgDiv.style.padding = '24px 28px';
    
    const badge = inputType === 'voice' ? '🎤 ' : '';
    msgDiv.textContent = badge + text;
    
    this.chatContainer.appendChild(msgDiv);
    this.scrollToBottom();
  }

  addBotMessage(text, gifUrl = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot-message';
    
    msgDiv.style.fontSize = '22px';
    msgDiv.style.lineHeight = '1.7';
    msgDiv.style.padding = '24px 28px';
    
    msgDiv.innerHTML = this.formatText(text);
    
    if (gifUrl) {
      const gifImg = document.createElement('img');
      gifImg.src = gifUrl;
      gifImg.alt = 'Response GIF';
      gifImg.className = 'response-gif';
      gifImg.style.maxWidth = '350px';
      gifImg.style.marginTop = '18px';
      gifImg.style.borderRadius = '10px';
      gifImg.style.border = '3px solid #00ff88';
      msgDiv.appendChild(gifImg);
    }
    
    this.chatContainer.appendChild(msgDiv);
    this.scrollToBottom();
  }

  formatText(text) {
    text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<div class="code-block" style="font-size: 18px; line-height: 1.6; padding: 20px; background: rgba(0,0,0,0.4); border-radius: 10px; overflow-x: auto;">${this.escapeHtml(code.trim())}</div>`;
    });
    
    text = text.replace(/`([^`]+)`/g, (match, code) => {
      return `<span class="inline-code" style="font-size: 19px; padding: 4px 8px; background: rgba(0,0,0,0.2); border-radius: 5px;">${this.escapeHtml(code)}</span>`;
    });
    
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong style="color: #00ff88; font-size: 22px;">$1</strong>');
    
    text = text.replace(/\n/g, '<br>');
    
    return text;
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  updateUI(state) {
    if (!this.voiceButton) return;

    this.voiceButton.classList.remove("listening", "processing");
    this.voiceButton.disabled = false;
    
    if (this.sendButton) {
      this.sendButton.disabled = (state === 'processing');
    }
    
    if (this.messageInput) {
      this.messageInput.disabled = (state === 'processing');
    }
    
    switch (state) {
      case 'listening':
        this.voiceButton.classList.add("listening");
        this.voiceButton.title = "Stop listening (Click or press Escape)";
        break;
      case 'processing':
        this.voiceButton.classList.add("processing");
        this.voiceButton.textContent = "⏳";
        this.voiceButton.disabled = true;
        this.voiceButton.title = "Processing your message...";
        break;
      default:
        this.voiceButton.textContent = "🎙️";
        this.voiceButton.title = "Start voice input (Click or press Ctrl+Space)";
    }
  }

  showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    const colors = {
      'info': 'rgba(0, 255, 255, 0.2)',
      'warning': 'rgba(255, 200, 0, 0.2)',
      'error': 'rgba(255, 70, 70, 0.2)',
      'success': 'rgba(0, 255, 136, 0.2)'
    };
    
    const borderColors = {
      'info': 'rgba(0, 255, 255, 0.6)',
      'warning': 'rgba(255, 200, 0, 0.6)',
      'error': 'rgba(255, 70, 70, 0.6)',
      'success': 'rgba(0, 255, 136, 0.6)'
    };
    
    notification.style.cssText = `
      position: fixed;
      top: 100px;
      right: 30px;
      background: ${colors[type] || colors.info};
      border: 2px solid ${borderColors[type] || borderColors.info};
      border-radius: 10px;
      padding: 18px 26px;
      color: #fff;
      font-size: 18px;
      line-height: 1.7;
      z-index: 10000;
      max-width: 450px;
      animation: slideIn 0.3s ease;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => notification.remove(), 300);
    }, 4000);
  }

  showError(message) {
    console.error("❌ Error:", message);
    const errorDiv = document.createElement('div');
    errorDiv.className = 'message bot-message';
    errorDiv.style.fontSize = '20px';
    errorDiv.style.lineHeight = '1.7';
    errorDiv.style.padding = '24px 28px';
    errorDiv.style.backgroundColor = 'rgba(255, 70, 70, 0.1)';
    errorDiv.style.borderLeft = '4px solid rgba(255, 70, 70, 0.8)';
    errorDiv.innerHTML = `<strong style="color: #ff4646; font-size: 22px;">❌ Error:</strong><br>${this.escapeHtml(message)}`;
    this.chatContainer.appendChild(errorDiv);
    this.scrollToBottom();
    this.showNotification(message, 'error');
  }

  showTyping() {
    if (this.typingIndicator) {
      this.typingIndicator.classList.add('active');
      this.typingIndicator.style.fontSize = '18px';
      this.scrollToBottom();
    }
  }

  hideTyping() {
    if (this.typingIndicator) {
      this.typingIndicator.classList.remove('active');
    }
  }

  scrollToBottom() {
    if (this.chatContainer) {
      this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }
  }

  async loadHistory() {
    try {
      console.log('📜 Loading conversation history...');
      const response = await fetch(`${BACKEND_URL}/api/history?limit=50`);
      const data = await response.json();
      
      if (data.success && data.history.length > 0) {
        this.displayHistory(data.history);
      } else {
        this.chatContainer.innerHTML = `
          <div class="welcome-message" style="font-size: 18px; line-height: 1.7;">
            <h2 style="font-size: 3rem;">📜 No conversation history</h2>
            <p style="font-size: 1.5rem;">Start chatting to build your history!</p>
          </div>
        `;
      }
    } catch (error) {
      console.error('❌ Error loading history:', error);
      this.chatContainer.innerHTML = `
        <div class="welcome-message" style="font-size: 18px; line-height: 1.7;">
          <h2 style="font-size: 3rem;">❌ Error loading history</h2>
          <p style="font-size: 1.5rem;">Please try again later.</p>
        </div>
      `;
    }
  }

  displayHistory(history) {
    this.chatContainer.innerHTML = '';
    history.forEach(conv => {
      this.addUserMessage(conv.user, conv.input_method || 'text');
      this.addBotMessage(conv.bot, conv.gif_url);
    });
  }

  async checkServerConnection() {
    try {
      console.log('🔌 Checking server connection...');
      const controller = new AbortController();
      setTimeout(() => controller.abort(), 5000);

      const response = await fetch(`${BACKEND_URL}/health`, {
        signal: controller.signal
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('✅ Server connected:', data);
        this.showNotification('✅ Connected to server successfully!', 'success');
        return true;
      } else {
        console.error('❌ Server returned error status:', response.status);
        throw new Error('Server unavailable');
      }
    } catch (err) {
      console.error('❌ Server connection failed:', err);
      this.showNotification("❌ Cannot connect to server! Please make sure the Flask server is running on http://localhost:5000", 'error');
      return false;
    }
  }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn {
    from {
      transform: translateX(400px);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  
  @keyframes slideOut {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(400px);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);

// Initialize Voice Assistant when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  console.log('═══════════════════════════════════════');
  console.log('🚀 INITIALIZING VOICE ASSISTANT');
  console.log('📏 MEDIUM FONT SIZES ENABLED');
  console.log('🎙️ ANIMATED MICROPHONE WITH WAVES');
  console.log('🌐 Backend: http://localhost:5000');
  console.log('═══════════════════════════════════════');
  
  const requiredElements = ['chat-container'];
  const missingElements = requiredElements.filter(id => !document.getElementById(id));
  
  if (missingElements.length > 0) {
    console.error('❌ Missing required HTML elements:', missingElements);
    alert('❌ Page initialization error!\n\nMissing elements: ' + missingElements.join(', '));
    return;
  }
  
  window.voiceAssistant = new VoiceAssistant();
  console.log('✅ Voice Assistant initialized successfully!');
  console.log('💡 Tips:');
  console.log('   • Click 🎙️ button to start voice input with animated waves');
  console.log('   • Click ✕ Cancel button to stop listening');
  console.log('   • Press Escape to cancel voice input');
  console.log('   • Live transcript appears at bottom during listening');
  console.log('═══════════════════════════════════════\n');
});