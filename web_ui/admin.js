class AdminPanel {
    constructor() {
        this.apiBaseUrl = 'http://localhost:5000';
        this.adminSessionId = localStorage.getItem('aida-admin-session');
        this.init();
    }
    
    async init() {
        await this.checkAuthentication();
        this.setupEventListeners();
        this.loadStats();
        this.loadUsers();
    }
    
    async checkAuthentication() {
        if (!this.adminSessionId) {
            window.location.href = '/admin-login';
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/admin/check_session`, {
                headers: {
                    'Authorization': `Bearer ${this.adminSessionId}`
                }
            });
            
            if (!response.ok) {
                localStorage.removeItem('aida-admin-session');
                window.location.href = '/admin-login';
                return;
            }
            
            const data = await response.json();
            if (data.valid) {
                this.displayAdminInfo(data.user);
            } else {
                localStorage.removeItem('aida-admin-session');
                window.location.href = '/admin-login';
            }
        } catch (error) {
            console.error('Authentication check failed:', error);
            localStorage.removeItem('aida-admin-session');
            window.location.href = '/admin-login';
        }
    }
    
    displayAdminInfo(user) {
        const adminInfo = document.getElementById('adminInfo');
        adminInfo.textContent = `Logged in as: ${user.username} (${user.role})`;
    }
    
    setupEventListeners() {
        // Logout button
        document.getElementById('logoutBtn').addEventListener('click', (e) => {
            e.preventDefault();
            this.handleLogout();
        });
        
        // Create user form
        document.getElementById('createUserForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleCreateUser();
        });
        
        // Password change form
        document.getElementById('passwordChangeForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handlePasswordChange();
        });
    }
    
    async handleLogout() {
        try {
            await fetch(`${this.apiBaseUrl}/admin/logout`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.adminSessionId}`
                }
            });
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            localStorage.removeItem('aida-admin-session');
            window.location.href = '/admin-login';
        }
    }
    
    async loadStats() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/admin/stats`, {
                headers: {
                    'Authorization': `Bearer ${this.adminSessionId}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                const stats = data.stats;
                
                document.getElementById('totalUsers').textContent = stats.total_users || 0;
                document.getElementById('activeUsers').textContent = stats.active_users || 0;
                document.getElementById('adminUsers').textContent = stats.admin_users || 0;
                document.getElementById('todayUsers').textContent = stats.new_today || 0;
            }
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }
    
    async loadUsers() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/admin/users`, {
                headers: {
                    'Authorization': `Bearer ${this.adminSessionId}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.renderUsers(data.users);
            } else {
                document.getElementById('usersList').innerHTML = '<div class="error">Failed to load users</div>';
            }
        } catch (error) {
            console.error('Failed to load users:', error);
            document.getElementById('usersList').innerHTML = '<div class="error">Failed to load users</div>';
        }
    }
    
    renderUsers(users) {
        const usersList = document.getElementById('usersList');
        
        if (!users || users.length === 0) {
            usersList.innerHTML = '<div class="loading">No users found</div>';
            return;
        }
        
        const table = `
            <table class="users-table">
                <thead>
                    <tr>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${users.map(user => `
                        <tr>
                            <td>${user.username}</td>
                            <td>${user.email}</td>
                            <td>
                                <span class="user-status ${user.role === 'admin' ? 'status-admin' : 'status-active'}">
                                    ${user.role}
                                </span>
                            </td>
                            <td>
                                <span class="user-status ${user.is_active ? 'status-active' : 'status-inactive'}">
                                    ${user.is_active ? 'Active' : 'Inactive'}
                                </span>
                            </td>
                            <td>${new Date(user.created_at).toLocaleDateString()}</td>
                            <td class="action-buttons">
                                ${user.is_active ? 
                                    `<button class="btn btn-danger btn-sm" onclick="adminPanel.deactivateUser('${user.user_id}')">Deactivate</button>` :
                                    `<button class="btn btn-success btn-sm" onclick="adminPanel.activateUser('${user.user_id}')">Activate</button>`
                                }
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        
        usersList.innerHTML = table;
    }
    
    async handleCreateUser() {
        const formData = new FormData(document.getElementById('createUserForm'));
        const userData = {
            username: formData.get('username'),
            email: formData.get('email'),
            role: formData.get('role')
        };
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/admin/create_user`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.adminSessionId}`
                },
                body: JSON.stringify(userData)
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showMessage('createUserMessage', data.message, 'success');
                document.getElementById('createUserForm').reset();
                this.loadUsers();
                this.loadStats();
            } else {
                this.showMessage('createUserMessage', data.error, 'error');
            }
        } catch (error) {
            console.error('Failed to create user:', error);
            this.showMessage('createUserMessage', 'Failed to create user', 'error');
        }
    }
    
    async handlePasswordChange() {
        const formData = new FormData(document.getElementById('passwordChangeForm'));
        const currentPassword = formData.get('currentPassword');
        const newPassword = formData.get('newPassword');
        const confirmPassword = formData.get('confirmPassword');
        
        if (newPassword !== confirmPassword) {
            this.showMessage('passwordChangeMessage', 'New passwords do not match', 'error');
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/admin/change_password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.adminSessionId}`
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showMessage('passwordChangeMessage', data.message, 'success');
                document.getElementById('passwordChangeForm').reset();
            } else {
                this.showMessage('passwordChangeMessage', data.error, 'error');
            }
        } catch (error) {
            console.error('Failed to change password:', error);
            this.showMessage('passwordChangeMessage', 'Failed to change password', 'error');
        }
    }
    
    async deactivateUser(userId) {
        if (!confirm('Are you sure you want to deactivate this user?')) {
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/admin/deactivate_user/${userId}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.adminSessionId}`
                }
            });
            
            if (response.ok) {
                this.loadUsers();
                this.loadStats();
            } else {
                alert('Failed to deactivate user');
            }
        } catch (error) {
            console.error('Failed to deactivate user:', error);
            alert('Failed to deactivate user');
        }
    }
    
    async activateUser(userId) {
        if (!confirm('Are you sure you want to activate this user?')) {
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/admin/activate_user/${userId}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.adminSessionId}`
                }
            });
            
            if (response.ok) {
                this.loadUsers();
                this.loadStats();
            } else {
                alert('Failed to activate user');
            }
        } catch (error) {
            console.error('Failed to activate user:', error);
            alert('Failed to activate user');
        }
    }
    
    showMessage(elementId, message, type) {
        const element = document.getElementById(elementId);
        element.textContent = message;
        element.className = type;
        element.style.display = 'block';
        
        setTimeout(() => {
            element.style.display = 'none';
        }, 5000);
    }
}

// Initialize admin panel when DOM is loaded
let adminPanel;
document.addEventListener('DOMContentLoaded', () => {
    adminPanel = new AdminPanel();
}); 