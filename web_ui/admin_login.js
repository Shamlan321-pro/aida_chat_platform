class AdminLogin {
    constructor() {
        this.apiBaseUrl = 'http://localhost:5000';
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.checkExistingSession();
    }
    
    setupEventListeners() {
        const form = document.getElementById('adminLoginForm');
        const usernameInput = document.getElementById('username');
        const passwordInput = document.getElementById('password');
        
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });
        
        // Auto-focus username field
        usernameInput.focus();
    }
    
    async checkExistingSession() {
        const adminSessionId = localStorage.getItem('aida-admin-session');
        if (adminSessionId) {
            try {
                const response = await fetch(`${this.apiBaseUrl}/admin/check_session`, {
                    headers: {
                        'Authorization': `Bearer ${adminSessionId}`
                    }
                });
                
                if (response.ok) {
                    // Session is valid, redirect to admin panel
                    window.location.href = '/admin';
                } else {
                    // Session is invalid, remove it
                    localStorage.removeItem('aida-admin-session');
                }
            } catch (error) {
                console.error('Session check failed:', error);
                localStorage.removeItem('aida-admin-session');
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
            const response = await fetch(`${this.apiBaseUrl}/admin/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                // Store admin session
                localStorage.setItem('aida-admin-session', data.session_id);
                this.showSuccess('Login successful! Redirecting...');
                
                // Redirect to admin panel
                setTimeout(() => {
                    window.location.href = '/admin';
                }, 1000);
            } else {
                this.showError(data.error || 'Login failed');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showError('Connection error. Please try again.');
        } finally {
            this.setLoading(false);
        }
    }
    
    setLoading(loading) {
        const button = document.getElementById('adminLoginBtn');
        const buttonText = document.getElementById('loginText');
        const spinner = document.getElementById('loginSpinner');
        
        if (loading) {
            button.disabled = true;
            buttonText.textContent = 'Logging in...';
            spinner.style.display = 'inline-block';
        } else {
            button.disabled = false;
            buttonText.textContent = 'Login as Admin';
            spinner.style.display = 'none';
        }
    }
    
    showError(message) {
        const errorDiv = document.getElementById('errorMessage');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        
        // Hide success message if visible
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
        
        // Hide error message if visible
        document.getElementById('errorMessage').style.display = 'none';
    }
}

// Initialize admin login when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AdminLogin();
}); 