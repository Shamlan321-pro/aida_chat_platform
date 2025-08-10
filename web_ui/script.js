// AIDA Web UI JavaScript
class AidaWebUI {
    constructor() {
        this.sessionId = null;
        this.isConnected = false;
        this.apiBaseUrl = window.AIDA_CONFIG?.apiBaseUrl || 'http://localhost:5000';
        this.currentTheme = localStorage.getItem('aida-theme') || 'light';
        this.currentChatId = null;
        this.recentChats = [];
        this.userInfo = null;
        
        this.init();
    }
    
    async init() {
        // Show loading screen first
        this.showLoadingScreen('Checking your saved credentials...');
        
        this.setupEventListeners();
        this.setupTheme();
        this.setupAutoResize();
        this.loadSavedConfig();
        
        try {
            // Check authentication and load user info
            const isAuthenticated = await this.checkAuthentication();
            
            if (isAuthenticated) {
                // Check for saved Mocxha credentials and auto-connect
                const hasCredentials = await this.checkSavedMocxhaCredentials();
                
                if (hasCredentials) {
                    // User has saved credentials, try to auto-connect
                    this.updateLoadingMessage('Connecting to Mocxha...');
                    const connected = await this.autoConnectToMocxha();
                    if (!connected) {
                        // Auto-connection failed, show welcome screen
                        this.updateLoadingMessage('Loading platform...');
                        await this.showWelcomeScreen();
                    }
                } else {
                    // No saved credentials, show welcome screen
                    this.updateLoadingMessage('Loading platform...');
                    await this.showWelcomeScreen();
                }
            } else {
                // Authentication failed, redirect to login (handled in checkAuthentication)
                return;
            }
        } catch (error) {
            console.error('Initialization error:', error);
            this.updateLoadingMessage('Error loading platform...');
            await this.showWelcomeScreen();
        } finally {
            // Hide loading screen and show app
            this.hideLoadingScreen();
        }
    }
    
    setupEventListeners() {
        // Mobile menu toggle
        document.getElementById('mobileMenuBtn').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('open');
        });
        
        // Sidebar toggle
        document.getElementById('sidebarToggle').addEventListener('click', () => {
            document.getElementById('sidebar').classList.remove('open');
        });
        
        // Theme toggle
        document.getElementById('themeToggle').addEventListener('click', () => {
            this.toggleTheme();
        });
        
        // Connect button
        document.getElementById('connectBtn').addEventListener('click', () => {
            this.showConfigModal();
        });
        
        // Configuration modal
        document.getElementById('configBtn').addEventListener('click', () => {
            this.showConfigModal();
        });
        
        document.getElementById('configModalClose').addEventListener('click', () => {
            this.hideConfigModal();
        });
        
        document.getElementById('configCancel').addEventListener('click', () => {
            this.hideConfigModal();
        });
        
        // Settings modal
        document.getElementById('settingsBtn').addEventListener('click', () => {
            this.showSettingsModal();
        });
        
        document.getElementById('settingsModalClose').addEventListener('click', () => {
            this.hideSettingsModal();
        });
        
        document.getElementById('settingsCancel').addEventListener('click', () => {
            this.hideSettingsModal();
        });
        
        document.getElementById('settingsForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.changePassword();
        });
        
        document.getElementById('configForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleConnect();
        });
        

        
        // Chat functionality
        document.getElementById('sendBtn').addEventListener('click', () => {
            this.sendMessage();
        });
        
        document.getElementById('messageInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        document.getElementById('messageInput').addEventListener('input', () => {
            this.updateSendButton();
        });
        
        // Suggestion buttons
        document.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.getElementById('messageInput').value = btn.textContent;
                this.updateSendButton();
                this.sendMessage();
            });
        });
        
        // Session management
        document.getElementById('clearChatBtn').addEventListener('click', () => {
            this.clearChat();
        });
        
        document.getElementById('disconnectBtn').addEventListener('click', () => {
            this.disconnect();
        });
        
        // Recent chats functionality
        document.getElementById('newChatBtn').addEventListener('click', () => {
            this.startNewChat();
        });
        
        // Logout functionality
        document.getElementById('logoutBtn').addEventListener('click', () => {
            this.logout();
        });
        
        // Close modals on outside click
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.classList.remove('show');
            }
        });
    }
    
    setupTheme() {
        document.documentElement.setAttribute('data-theme', this.currentTheme);
        const themeIcon = document.querySelector('#themeToggle i');
        themeIcon.className = this.currentTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
    
    toggleTheme() {
        this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        localStorage.setItem('aida-theme', this.currentTheme);
        this.setupTheme();
    }
    
    setupAutoResize() {
        const textarea = document.getElementById('messageInput');
        textarea.addEventListener('input', () => {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        });
    }
    
    loadSavedConfig() {
        const savedConfig = localStorage.getItem('aida-config');
        if (savedConfig) {
            const config = JSON.parse(savedConfig);
            document.getElementById('mocxhaUrl').value = config.mocxhaUrl || '';
            document.getElementById('username').value = config.username || '';
        }
    }
    
    saveConfig() {
        const config = {
            mocxhaUrl: document.getElementById('mocxhaUrl').value,
            username: document.getElementById('username').value
        };
        localStorage.setItem('aida-config', JSON.stringify(config));
    }
    
    showConfigModal() {
        document.getElementById('configModal').classList.add('show');
    }
    
    hideConfigModal() {
        document.getElementById('configModal').classList.remove('show');
    }
    
    showSettingsModal() {
        document.getElementById('settingsModal').classList.add('show');
        // Clear form
        document.getElementById('settingsForm').reset();
    }
    
    hideSettingsModal() {
        document.getElementById('settingsModal').classList.remove('show');
    }
    

    
    showLoading(text = 'Loading...') {
        document.getElementById('loadingText').textContent = text;
        document.getElementById('loadingOverlay').classList.add('show');
    }
    
    hideLoading() {
        document.getElementById('loadingOverlay').classList.remove('show');
    }
    
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <i class="fas ${
                    type === 'success' ? 'fa-check-circle' :
                    type === 'error' ? 'fa-exclamation-circle' :
                    type === 'warning' ? 'fa-exclamation-triangle' :
                    'fa-info-circle'
                }"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.getElementById('toastContainer').appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideInRight 0.3s ease-out reverse';
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 4000);
    }
    
    updateConnectionStatus(connected) {
        this.isConnected = connected;
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        
        if (connected) {
            statusIndicator.className = 'status-indicator online';
            statusText.textContent = 'Connected';
        } else {
            statusIndicator.className = 'status-indicator offline';
            statusText.textContent = 'Disconnected';
        }
    }
    
    updateSendButton() {
        const input = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        sendBtn.disabled = !input.value.trim() || !this.isConnected;
    }
    
    async handleConnect() {
        const formData = {
            mocxha_url: document.getElementById('mocxhaUrl').value,
            username: document.getElementById('username').value,
            password: document.getElementById('password').value,
            site_base_url: document.getElementById('mocxhaUrl').value
        };
        
        // Validate required fields
        if (!formData.mocxha_url || !formData.username || !formData.password) {
            this.showToast('Please fill in all required fields', 'error');
            return;
        }
        
        this.showLoading('Connecting to AIDA...');
        
        try {
            const sessionId = localStorage.getItem('aida-user-session');
            const response = await fetch(`${this.apiBaseUrl}/user/connect_mocxha`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${sessionId}`
                },
                body: JSON.stringify(formData)
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.sessionId = data.session_id;
                this.updateConnectionStatus(true);
                this.hideConfigModal();
                this.showChatInterface();
                this.saveConfig();
                
                // Store session ID for persistence
                localStorage.setItem('aida-session-id', this.sessionId);
                
                this.showToast('Successfully connected to AIDA!', 'success');
                this.addMessage('assistant', 'Hello! I\'m AIDA, your Mocxha AI assistant. How can I help you today?');
                
                // Load recent chats after connecting
                await this.loadRecentChats();
            } else {
                this.showToast(data.error || 'Connection failed', 'error');
            }
        } catch (error) {
            console.error('Connection error:', error);
            this.showToast('Failed to connect to API server', 'error');
        } finally {
            this.hideLoading();
        }
    }
    

    
    showChatInterface() {
        document.getElementById('welcomeScreen').style.display = 'none';
        document.getElementById('chatMessages').style.display = 'block';
        document.getElementById('chatInputContainer').style.display = 'block';
        this.updateSendButton();
    }
    
    hideChatInterface() {
        document.getElementById('welcomeScreen').style.display = 'flex';
        document.getElementById('chatMessages').style.display = 'none';
        document.getElementById('chatInputContainer').style.display = 'none';
    }
    
    async sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (!message || !this.isConnected) return;
        
        // Add user message to chat
        this.addMessage('user', message);
        input.value = '';
        input.style.height = 'auto';
        this.updateSendButton();
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    user_input: message
                })
            });
            
            const data = await response.json();
            
            this.hideTypingIndicator();
            
            if (response.ok) {
                this.addMessage('assistant', data.response);
                
                // Save chat after successful response
                await this.saveChat();
            } else {
                // Handle session invalidation or server restart
                if (response.status === 404 || response.status === 400) {
                    this.handleSessionInvalidation();
                } else {
                    this.addMessage('assistant', `Error: ${data.error || 'Something went wrong'}`);
                }
            }
        } catch (error) {
            console.error('Chat error:', error);
            this.hideTypingIndicator();
            
            // Check if it's a connection error (server might be restarted)
            if (error.name === 'TypeError' || error.message.includes('fetch')) {
                this.handleSessionInvalidation();
            } else {
                this.addMessage('assistant', 'Sorry, I\'m having trouble connecting. Please try again.');
            }
        }
    }
    
    addMessage(sender, content) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        // Create message structure
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = `<i class="fas ${sender === 'user' ? 'fa-user' : 'fa-robot'}"></i>`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        
        // For assistant messages, allow HTML content (for buttons)
        // For user messages, escape HTML for security
        if (sender === 'assistant') {
            textDiv.innerHTML = this.formatMessage(content);
        } else {
            textDiv.textContent = content;
        }
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = time;
        
        contentDiv.appendChild(textDiv);
        contentDiv.appendChild(timeDiv);
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    formatMessage(content) {
        // Enhanced formatting that preserves HTML buttons while adding markdown support
        let formatted = content;
        
        // Check if content already contains HTML (like buttons, headings, etc.)
        const hasHtml = /<[^>]*>/.test(formatted);
        
        if (hasHtml) {
            // If content already has HTML, preserve it and only apply minimal formatting
            // First, convert markdown tables to HTML tables
            formatted = this.convertMarkdownTables(formatted);
            
            // Preserve existing HTML elements (buttons, headings, links, etc.)
            const htmlElements = [];
            let elementIndex = 0;
            
            // Store HTML elements temporarily
            formatted = formatted.replace(/(<[^>]+>[^<]*<\/[^>]+>|<[^>]+\/>)/g, (match) => {
                htmlElements.push(match);
                return `__HTML_ELEMENT_${elementIndex++}__`;
            });
            
            // Apply markdown formatting to the remaining text
            formatted = formatted
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`(.*?)`/g, '<code>$1</code>')
                // Convert markdown links to HTML (but skip if already HTML)
                .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
                // Convert line breaks (but not inside tables)
                .replace(/\n(?![\s]*\|)/g, '<br>');
            
            // Restore HTML elements
            htmlElements.forEach((element, index) => {
                formatted = formatted.replace(`__HTML_ELEMENT_${index}__`, element);
            });
            
            return formatted;
        } else {
            // If no HTML, apply full markdown formatting
            // Convert markdown tables to HTML tables
            formatted = this.convertMarkdownTables(formatted);
            
            // Apply other markdown formatting
            formatted = formatted
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`(.*?)`/g, '<code>$1</code>')
                // Convert markdown links to HTML
                .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
                // Convert line breaks (but not inside tables)
                .replace(/\n(?![\s]*\|)/g, '<br>');
                
            return formatted;
        }
    }
    
    convertMarkdownTables(content) {
        // Split content by double line breaks to handle tables separately
        const sections = content.split(/\n\s*\n/);
        
        return sections.map(section => {
            // Check if this section contains a markdown table
            const lines = section.split('\n');
            const tableLines = lines.filter(line => line.trim().includes('|'));
            
            if (tableLines.length >= 2) {
                // This looks like a table
                let tableHtml = '<table class="markdown-table">';
                let isHeader = true;
                
                for (let line of lines) {
                    line = line.trim();
                    if (!line) continue;
                    
                    if (line.includes('|')) {
                        // Skip separator lines (lines with only |, -, and spaces)
                        if (/^[\s\|\-]+$/.test(line)) {
                            isHeader = false;
                            continue;
                        }
                        
                        const cells = line.split('|').map(cell => cell.trim()).filter(cell => cell);
                        const tag = isHeader ? 'th' : 'td';
                        
                        tableHtml += '<tr>';
                        cells.forEach(cell => {
                            tableHtml += `<${tag}>${cell}</${tag}>`;
                        });
                        tableHtml += '</tr>';
                        
                        if (isHeader) isHeader = false;
                    }
                }
                
                tableHtml += '</table>';
                return tableHtml;
            }
            
            return section;
        }).join('<br><br>');
    }
    
    showTypingIndicator() {
        const messagesContainer = document.getElementById('chatMessages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant';
        typingDiv.id = 'typing-indicator';
        
        typingDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="typing-indicator">
                <span>AIDA is typing</span>
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    async loadChatHistory() {
        if (!this.sessionId) return;
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/get_chat_history/${this.sessionId}`);
            const data = await response.json();
            
            if (response.ok && data.history && data.history.length > 0) {
                const messagesContainer = document.getElementById('chatMessages');
                messagesContainer.innerHTML = ''; // Clear existing messages
                
                // Load chat history
                data.history.forEach(message => {
                    // Add user message
                    if (message.user_message) {
                        this.addMessage('user', message.user_message);
                    }
                    // Add AI response
                    if (message.ai_response) {
                        this.addMessage('assistant', message.ai_response);
                    }
                });
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
        }
    }
    
    async checkAuthentication() {
        const sessionId = localStorage.getItem('aida-user-session');
        if (!sessionId) {
            window.location.href = '/login';
            return false;
        }
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/check_session`, {
                headers: {
                    'Authorization': `Bearer ${sessionId}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.userInfo = JSON.parse(localStorage.getItem('aida-user-info') || '{}');
                this.updateUserInfo();
                return true;
            } else {
                // Session is invalid, redirect to login
                localStorage.removeItem('aida-user-session');
                localStorage.removeItem('aida-user-info');
                window.location.href = '/login';
                return false;
            }
        } catch (error) {
            console.error('Authentication check error:', error);
            localStorage.removeItem('aida-user-session');
            localStorage.removeItem('aida-user-info');
            window.location.href = '/login';
            return false;
        }
    }
    
    async checkSavedMocxhaCredentials() {
        try {
            const sessionId = localStorage.getItem('aida-user-session');
            const response = await fetch(`${this.apiBaseUrl}/user/mocxha_credentials`, {
                headers: {
                    'Authorization': `Bearer ${sessionId}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                return data.has_credentials;
            }
            return false;
        } catch (error) {
            console.error('Error checking saved Mocxha credentials:', error);
            return false;
        }
    }
    
    async autoConnectToMocxha(credentials = null) {
        try {
            const sessionId = localStorage.getItem('aida-user-session');
            
            // Use the auto-connect endpoint that uses saved credentials
            const response = await fetch(`${this.apiBaseUrl}/user/auto_connect_mocxha`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${sessionId}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.sessionId = data.session_id;
                this.isConnected = true;
                this.updateConnectionStatus(true);
                this.showChatInterface();
                this.showToast('Mocxha connection restored automatically!', 'success');
                
                // Load recent chats
                await this.loadRecentChats();
                return true;
            } else {
                console.log('Auto-connection failed, user will need to connect manually');
                return false;
            }
        } catch (error) {
            console.error('Auto-connection error:', error);
            return false;
        }
    }
    
    showLoadingScreen(message = 'Loading...') {
        const loadingScreen = document.getElementById('loadingScreen');
        const loadingMessage = document.getElementById('loadingMessage');
        const appContainer = document.getElementById('appContainer');
        
        if (loadingMessage) {
            loadingMessage.textContent = message;
        }
        
        loadingScreen.style.display = 'flex';
        appContainer.style.display = 'none';
    }
    
    hideLoadingScreen() {
        const loadingScreen = document.getElementById('loadingScreen');
        const appContainer = document.getElementById('appContainer');
        
        loadingScreen.style.display = 'none';
        appContainer.style.display = 'flex';
    }
    
    updateLoadingMessage(message) {
        const loadingMessage = document.getElementById('loadingMessage');
        if (loadingMessage) {
            loadingMessage.textContent = message;
        }
    }
    
    async showWelcomeScreen() {
        // Show the welcome screen with features and connect button
        const welcomeScreen = document.getElementById('welcomeScreen');
        const chatMessages = document.getElementById('chatMessages');
        const chatInputContainer = document.getElementById('chatInputContainer');
        
        if (welcomeScreen) {
            welcomeScreen.style.display = 'block';
        }
        if (chatMessages) {
            chatMessages.style.display = 'none';
        }
        if (chatInputContainer) {
            chatInputContainer.style.display = 'none';
        }
        
        // Update connection status to disconnected
        this.updateConnectionStatus(false);
    }
    
    updateUserInfo() {
        if (this.userInfo) {
            // Update header with user info
            const headerTitle = document.querySelector('.header h1');
            if (headerTitle) {
                headerTitle.textContent = `AIDA - Welcome, ${this.userInfo.username}`;
            }
        }
    }
    
    async checkExistingSession() {
        // For the new recent chats approach, we don't restore sessions automatically
        // Each visit should be treated as a new interaction
        // Only load recent chats, don't restore session
        const savedSessionId = localStorage.getItem('aida-session-id');
        if (savedSessionId) {
            // Clear the old session ID to force new session creation
            localStorage.removeItem('aida-session-id');
        }
        
        // Don't automatically restore session - let user connect manually
        // This ensures each visit creates new chats instead of restoring old sessions
    }
    
    clearChat() {
        const messagesContainer = document.getElementById('chatMessages');
        messagesContainer.innerHTML = '';
        this.showToast('Chat cleared', 'info');
    }
    
    async disconnect() {
        // Save current chat before disconnecting
        if (this.isConnected && this.sessionId) {
            await this.saveChat();
        }
        
        if (this.sessionId) {
            try {
                await fetch(`${this.apiBaseUrl}/clear_session`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        session_id: this.sessionId
                    })
                });
            } catch (error) {
                console.error('Disconnect error:', error);
            }
        }
        
        this.sessionId = null;
        this.currentChatId = null;
        this.updateConnectionStatus(false);
        this.hideChatInterface();
        this.clearChat();
        
        // Clear stored session ID
        localStorage.removeItem('aida-session-id');
        
        this.showToast('Disconnected from AIDA', 'info');
    }
    
    async logout() {
        try {
            const sessionId = localStorage.getItem('aida-user-session');
            if (sessionId) {
                await fetch(`${this.apiBaseUrl}/auth/logout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${sessionId}`
                    }
                });
            }
        } catch (error) {
            console.error('Logout error:', error);
        }
        
        // Clear all local storage
        localStorage.removeItem('aida-user-session');
        localStorage.removeItem('aida-user-info');
        localStorage.removeItem('aida-session-id');
        
        // Redirect to login
        window.location.href = '/login';
    }
    
    async changePassword() {
        const currentPassword = document.getElementById('currentPassword').value;
        const newPassword = document.getElementById('newPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        if (!currentPassword || !newPassword || !confirmPassword) {
            this.showToast('Please fill in all fields', 'error');
            return;
        }
        
        if (newPassword !== confirmPassword) {
            this.showToast('New passwords do not match', 'error');
            return;
        }
        
        if (newPassword.length < 6) {
            this.showToast('New password must be at least 6 characters long', 'error');
            return;
        }
        
        try {
            const sessionId = localStorage.getItem('aida-user-session');
            const response = await fetch(`${this.apiBaseUrl}/auth/change_password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${sessionId}`
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });
            
            if (response.ok) {
                this.showToast('Password changed successfully!', 'success');
                this.hideSettingsModal();
            } else {
                const errorData = await response.json();
                this.showToast(errorData.error || 'Failed to change password', 'error');
            }
        } catch (error) {
            console.error('Change password error:', error);
            this.showToast('Error changing password', 'error');
        }
    }
    
    async handleSessionInvalidation() {
        // Clear the current session
        this.sessionId = null;
        this.isConnected = false;
        localStorage.removeItem('aida-session-id');
        
        // Update UI
        this.updateConnectionStatus(false);
        this.hideChatInterface();
        
        // Show informative message
        this.showToast('Server was restarted. Please reconnect to continue.', 'warning');
        
        // Try to preserve chat history by checking if there's any stored session data
        // The chat messages will remain visible until user reconnects
        // This way, users can see their previous conversation even after server restart
        
        // Add a message to the chat explaining what happened
        this.addMessage('assistant', '🔄 The server was restarted and your session has been cleared. Your chat history is preserved and will be restored when you reconnect. Please click "Connect" to establish a new session.');
    }
    
    // Health check to monitor connection
    async checkHealth() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/health`);
            return response.ok;
        } catch (error) {
            return false;
        }
    }
    
    // Start periodic health checks
    startHealthCheck() {
        setInterval(async () => {
            if (this.isConnected) {
                const healthy = await this.checkHealth();
                if (!healthy) {
                    this.showToast('Connection to server lost', 'warning');
                }
            }
        }, 30000); // Check every 30 seconds
    }
    
    // Recent Chats Methods
    async loadRecentChats() {
        // Load recent chats using authentication
        try {
            const sessionId = localStorage.getItem('aida-user-session');
            if (!sessionId) {
                return;
            }
            
            const response = await fetch(`${this.apiBaseUrl}/get_recent_chats`, {
                headers: {
                    'Authorization': `Bearer ${sessionId}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.recentChats = data.chats || [];
                this.renderRecentChats();
            }
        } catch (error) {
            console.error('Error loading recent chats:', error);
        }
    }
    
    renderRecentChats() {
        const recentChatsContainer = document.getElementById('recentChats');
        recentChatsContainer.innerHTML = '';
        
        if (this.recentChats.length === 0) {
            recentChatsContainer.innerHTML = '<div class="no-chats">No recent chats</div>';
            return;
        }
        
        this.recentChats.forEach(chat => {
            const chatElement = this.createChatElement(chat);
            recentChatsContainer.appendChild(chatElement);
        });
    }
    
    createChatElement(chat) {
        const chatDiv = document.createElement('div');
        chatDiv.className = 'recent-chat-item';
        chatDiv.dataset.chatId = chat.chat_id;
        
        const date = new Date(chat.created_at);
        const formattedDate = date.toLocaleDateString();
        const formattedTime = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        chatDiv.innerHTML = `
            <div class="chat-icon">
                <i class="fas fa-comments"></i>
            </div>
            <div class="chat-info">
                <div class="chat-title">${this.truncateText(chat.title || 'Chat', 20)}</div>
                <div class="chat-preview">${this.truncateText(chat.preview || 'No messages', 30)}</div>
                <div class="chat-date">${formattedDate} ${formattedTime}</div>
            </div>
            <div class="chat-actions">
                <button class="chat-action-btn delete" title="Delete chat" onclick="event.stopPropagation(); app.deleteChat('${chat.chat_id}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        chatDiv.addEventListener('click', () => {
            this.loadChat(chat.chat_id);
        });
        
        return chatDiv;
    }
    
    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
    
    async loadChat(chatId) {
        try {
            this.showLoading('Loading chat...');
            
            const sessionId = localStorage.getItem('aida-user-session');
            const response = await fetch(`${this.apiBaseUrl}/get_chat/${chatId}`, {
                headers: {
                    'Authorization': `Bearer ${sessionId}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                const chat = data.chat;
                
                // Clear current chat
                this.clearChat();
                
                // Load chat messages
                chat.messages.forEach(message => {
                    this.addMessage(message.role, message.content);
                });
                
                this.currentChatId = chatId;
                this.updateChatUI();
                this.showToast('Chat loaded successfully', 'success');
            } else {
                this.showToast('Failed to load chat', 'error');
            }
        } catch (error) {
            console.error('Error loading chat:', error);
            this.showToast('Error loading chat', 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    async deleteChat(chatId) {
        if (!confirm('Are you sure you want to delete this chat?')) {
            return;
        }
        
        try {
            const sessionId = localStorage.getItem('aida-user-session');
            const response = await fetch(`${this.apiBaseUrl}/delete_chat/${chatId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${sessionId}`
                }
            });
            
            if (response.ok) {
                this.recentChats = this.recentChats.filter(chat => chat.chat_id !== chatId);
                this.renderRecentChats();
                
                if (this.currentChatId === chatId) {
                    this.startNewChat();
                }
                
                this.showToast('Chat deleted successfully', 'success');
            } else {
                this.showToast('Failed to delete chat', 'error');
            }
        } catch (error) {
            console.error('Error deleting chat:', error);
            this.showToast('Error deleting chat', 'error');
        }
    }
    
    startNewChat() {
        this.currentChatId = null;
        this.clearChat();
        this.updateChatUI();
        this.showToast('New chat started', 'info');
        
        // Update header title
        const headerTitle = document.querySelector('.header h1');
        headerTitle.textContent = 'AIDA - AI Mocxha Assistant';
    }
    
    updateChatUI() {
        // Update active state in recent chats
        document.querySelectorAll('.recent-chat-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.chatId === this.currentChatId) {
                item.classList.add('active');
            }
        });
        
        // Update header title
        const headerTitle = document.querySelector('.header h1');
        if (this.currentChatId) {
            const chat = this.recentChats.find(c => c.chat_id === this.currentChatId);
            headerTitle.textContent = chat ? chat.title : 'AIDA - AI Mocxha Assistant';
        } else {
            headerTitle.textContent = 'AIDA - AI Mocxha Assistant';
        }
    }
    
    async saveChat() {
        if (!this.isConnected || !this.sessionId) {
            return;
        }
        
        const messages = document.querySelectorAll('#chatMessages .message');
        if (messages.length === 0) {
            return;
        }
        
        // Only save if we have at least one user message and one assistant response
        const userMessages = document.querySelectorAll('#chatMessages .message.user');
        const assistantMessages = document.querySelectorAll('#chatMessages .message.assistant');
        
        if (userMessages.length === 0 || assistantMessages.length === 0) {
            return;
        }
        
        const chatData = {
            session_id: this.sessionId,
            title: this.generateChatTitle(),
            preview: this.generateChatPreview(),
            messages: []
        };
        
        messages.forEach(message => {
            const role = message.classList.contains('user') ? 'user' : 'assistant';
            const messageTextElement = message.querySelector('.message-text');
            
            // For assistant messages, preserve HTML content (for buttons and formatting)
            // For user messages, use textContent for security
            let content;
            if (role === 'assistant') {
                content = messageTextElement.innerHTML;
            } else {
                content = messageTextElement.textContent;
            }
            
            chatData.messages.push({ role, content });
        });
        
        try {
            const sessionId = localStorage.getItem('aida-user-session');
            const response = await fetch(`${this.apiBaseUrl}/save_chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${sessionId}`
                },
                body: JSON.stringify(chatData)
            });
            
            if (response.ok) {
                const data = await response.json();
                this.currentChatId = data.chat_id;
                await this.loadRecentChats();
                this.updateChatUI();
                console.log('✅ Chat saved successfully:', data.chat_id);
            }
        } catch (error) {
            console.error('Error saving chat:', error);
        }
    }
    
    generateChatTitle() {
        const firstUserMessage = document.querySelector('#chatMessages .message.user .message-text');
        if (firstUserMessage) {
            const text = firstUserMessage.textContent.trim();
            return this.truncateText(text, 30);
        }
        return 'New Chat';
    }
    
    generateChatPreview() {
        const lastMessage = document.querySelector('#chatMessages .message:last-child .message-text');
        if (lastMessage) {
            return this.truncateText(lastMessage.textContent.trim(), 50);
        }
        return 'No messages';
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const app = new AidaWebUI();
    app.startHealthCheck();
    
    // Add some keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K to focus on message input
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            document.getElementById('messageInput').focus();
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal.show').forEach(modal => {
                modal.classList.remove('show');
            });
        }
    });
    
    // Add some helpful console messages
    console.log('%cAIDA Web UI Loaded Successfully! 🤖', 'color: #6366f1; font-size: 16px; font-weight: bold;');
    console.log('Keyboard shortcuts:');
    console.log('- Ctrl/Cmd + K: Focus message input');
    console.log('- Escape: Close modals');
    console.log('- Enter: Send message (Shift+Enter for new line)');
});

// Add some utility functions to window for debugging
window.aidaDebug = {
    clearStorage: () => {
        localStorage.removeItem('aida-config');
        localStorage.removeItem('aida-theme');
        console.log('AIDA storage cleared');
    },
    getConfig: () => {
        return JSON.parse(localStorage.getItem('aida-config') || '{}');
    },
    setTheme: (theme) => {
        localStorage.setItem('aida-theme', theme);
        document.documentElement.setAttribute('data-theme', theme);
        console.log(`Theme set to: ${theme}`);
    }
};

// Service Worker registration for PWA capabilities (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Uncomment if you want to add PWA capabilities
        // navigator.serviceWorker.register('/sw.js')
        //     .then(registration => console.log('SW registered'))
        //     .catch(registrationError => console.log('SW registration failed'));
    });
}