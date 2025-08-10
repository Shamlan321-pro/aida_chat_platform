# AIDA Platform Deployment Configuration

This guide explains how to configure the AIDA Platform for different deployment environments.

## Overview

The AIDA Platform now automatically detects the current domain and sets the API base URL accordingly. This eliminates the need to manually update hardcoded URLs when deploying to different servers.

## Automatic Configuration

### How It Works

1. **Dynamic Base URL Detection**: The platform automatically detects the current domain using `window.location.protocol + '//' + window.location.host`
2. **Configuration File**: All settings are centralized in `web_ui/config.js`
3. **Fallback Support**: If the configuration fails, it falls back to `localhost:5000` for development

### Example URLs

- **Local Development**: `http://localhost:5000` → API calls go to `http://localhost:5000`
- **Production Server**: `https://aida.mocxha.com` → API calls go to `https://aida.mocxha.com`
- **Custom Domain**: `https://yourdomain.com` → API calls go to `https://yourdomain.com`

## Configuration File

### Location
`web_ui/config.js`

### Current Configuration
```javascript
window.AIDA_CONFIG = {
    // API Base URL - automatically detected from current domain
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
```

## Deployment Scenarios

### 1. Local Development
**No changes needed** - The platform automatically detects `localhost:5000`

### 2. Production Server (Recommended)
**No changes needed** - The platform automatically detects your domain

### 3. Custom Configuration
If you need to override the automatic detection:

1. Edit `web_ui/config.js`
2. Uncomment and modify the hardcoded URL:
   ```javascript
   // apiBaseUrl: 'https://your-custom-domain.com',
   ```
3. Comment out the automatic detection:
   ```javascript
   // apiBaseUrl: window.location.protocol + '//' + window.location.host,
   ```

### 4. Multiple Environments
For different environments (dev, staging, prod), you can:

1. **Use environment-specific config files**:
   - `config.dev.js`
   - `config.prod.js`
   - `config.staging.js`

2. **Use environment variables** (advanced):
   ```javascript
   apiBaseUrl: process.env.AIDA_API_URL || window.location.protocol + '//' + window.location.host,
   ```

## File Structure

```
web_ui/
├── config.js          # Main configuration file
├── index.html         # Main platform page
├── login.html         # User login page
├── admin_login.html   # Admin login page
├── admin.html         # Admin panel
├── script.js          # Main application logic
├── login.js           # Login logic
├── admin_login.js     # Admin login logic
└── admin.js           # Admin panel logic
```

## Verification

### Check Configuration
1. Open your browser's Developer Tools (F12)
2. Go to the Console tab
3. Type: `console.log(window.AIDA_CONFIG)`
4. Verify the `apiBaseUrl` is correct

### Test API Calls
1. Open the Network tab in Developer Tools
2. Perform an action (login, create user, etc.)
3. Verify API calls go to the correct domain

## Troubleshooting

### Issue: API calls still go to localhost
**Solution**: Check that `config.js` is loaded before other scripts in your HTML files

### Issue: Configuration not loading
**Solution**: Verify the script order in HTML:
```html
<script src="config.js"></script>
<script src="script.js"></script>
```

### Issue: Mixed content errors (HTTP/HTTPS)
**Solution**: Ensure your production server uses HTTPS and the API server is also accessible via HTTPS

## Security Considerations

1. **HTTPS Required**: Always use HTTPS in production
2. **CORS Configuration**: Ensure your API server allows requests from your domain
3. **Environment Variables**: Store sensitive configuration in environment variables, not in config files

## Example Production Setup

### Nginx Configuration
```nginx
server {
    listen 443 ssl;
    server_name aida.mocxha.com;
    
    # Frontend files
    location / {
        root /var/www/aida_platform/web_ui;
        try_files $uri $uri/ /index.html;
    }
    
    # API proxy
    location /api/ {
        proxy_pass http://localhost:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Environment Variables
```bash
export FLASK_ENV=production
export FLASK_DEBUG=false
export AIDA_DOMAIN=aida.mocxha.com
```

## Support

If you encounter issues with configuration:

1. Check the browser console for errors
2. Verify the configuration file is loaded
3. Test with a simple API call
4. Check server logs for backend errors

## Migration from Hardcoded URLs

If you're upgrading from a version with hardcoded URLs:

1. **Backup your current configuration**
2. **Update to the new structure** (already done)
3. **Test locally first**
4. **Deploy to production**
5. **Verify all functionality works**

The platform should now work seamlessly across all environments without manual URL updates! 