// AIDA Platform Configuration
// This file can be modified to override default settings for production deployments

window.AIDA_CONFIG = {
    // API Base URL - automatically detected from current domain
    // Can be overridden here for specific deployments
    apiBaseUrl: window.location.protocol + '//' + window.location.host,
    
    // Alternative: Hardcode for specific deployments
    // apiBaseUrl: 'https://aida.mocxha.com',
    
    // Other configuration options
    debug: false,
    version: '1.0.0',
    
    // Feature flags
    features: {
        recentChats: true,
        userSettings: true,
        adminPanel: true,
        mocxhaIntegration: true
    }
};

// Log configuration in development mode
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    console.log('AIDA Platform Configuration:', window.AIDA_CONFIG);
} 