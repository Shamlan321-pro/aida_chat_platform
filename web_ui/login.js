class LoginManager {
    constructor() {
        this.apiBaseUrl = window.AIDA_CONFIG?.apiBaseUrl || 'http://localhost:5000';
        this.initializeEventListeners();
    }
    
    init() {
        this.setupEventListeners();
        this.checkExistingSession();
    }
    
    setupEventListeners() {
        const loginForm = document.getElementById('loginForm');
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });
    }
    
    async checkExistingSession() {
        // Check if user is already logged in
        const sessionId = localStorage.getItem('aida-user-session');
        if (sessionId) {
            try {
                const response = await fetch(`${this.apiBaseUrl}/auth/check_session`, {
                    headers: {
                        'Authorization': `Bearer ${sessionId}`
                    }
                });
                
                if (response.ok) {
                    // User is already logged in, redirect to main platform
                    window.location.href = '/';
                    return;
                } else {
                    // Session is invalid, remove it
                    localStorage.removeItem('aida-user-session');
                }
            } catch (error) {
                console.error('Error checking session:', error);
                localStorage.removeItem('aida-user-session');
            }
        }
    }
    
    async handleLogin() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        if (!username || !password) {
            this.showError('Please enter both username and password');
            return;
        }
        
        this.setLoading(true);
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                
                // Store session token
                localStorage.setItem('aida-user-session', data.session_id);
                localStorage.setItem('aida-user-info', JSON.stringify({
                    user_id: data.user_id,
                    username: data.username,
                    role: data.role
                }));
                
                this.showSuccess('Login successful! Redirecting...');
                
                // Redirect to main platform after a short delay
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            } else {
                const errorData = await response.json();
                this.showError(errorData.error || 'Login failed');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showError('Connection error. Please try again.');
        } finally {
            this.setLoading(false);
        }
    }
    
    setLoading(loading) {
        const loginBtn = document.getElementById('loginBtn');
        const loginText = document.getElementById('loginText');
        const loginSpinner = document.getElementById('loginSpinner');
        
        if (loading) {
            loginBtn.disabled = true;
            loginText.style.display = 'none';
            loginSpinner.style.display = 'inline-block';
        } else {
            loginBtn.disabled = false;
            loginText.style.display = 'inline';
            loginSpinner.style.display = 'none';
        }
    }
    
    showError(message) {
        const errorDiv = document.getElementById('errorMessage');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        
        // Hide success message if shown
        document.getElementById('successMessage').style.display = 'none';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
    
    showSuccess(message) {
        const successDiv = document.getElementById('successMessage');
        successDiv.textContent = message;
        successDiv.style.display = 'block';
        
        // Hide error message if shown
        document.getElementById('errorMessage').style.display = 'none';
    }
}

// Initialize login manager
const loginManager = new LoginManager(); 