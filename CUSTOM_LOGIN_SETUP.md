# Custom Login Page Setup - Pluviago

## Overview

A custom branded login page has been created for Pluviago Biotech. The login page features:
- Modern, responsive design with Pluviago branding
- Two-panel layout (form + welcome panel)
- Password visibility toggle
- Integrated with Frappe's authentication API
- Error handling and loading states

## Files Created

1. **`pluviago/www/login.html`** - The custom login page HTML/CSS/JS
2. **`pluviago/www/login.py`** - Python context handler for the page
3. **`pluviago/www/__init__.py`** - Python package marker

## Installation

### Step 1: Upload Logo

1. Login to ERPNext Desk
2. Go to **Files** → Upload
3. Upload your Pluviago logo as `pluviago-logo.jpeg`
4. The logo will be accessible at `/files/pluviago-logo.jpeg`

**Alternative:** If you have a different logo filename or path, update line 155 in `login.html`:
```html
<img src="/files/pluviago-logo.jpeg" alt="Pluviago" class="left-logo-img" onerror="this.style.display='none'">
```

### Step 2: Build Assets

After adding the files, rebuild the app:

```bash
cd <bench_directory>
bench build --app pluviago
bench --site <site_name> clear-cache
```

### Step 3: Access Custom Login

The custom login page will be available at:
- **URL:** `http://your-site.com/login`
- **Route:** `/login`

## How It Works

1. **Automatic Route:** Files in the `www` directory are automatically served by Frappe
2. **Login API Integration:** The page uses Frappe's `/api/method/login` endpoint
3. **CSRF Protection:** Automatically fetches and includes CSRF token
4. **Redirect:** On successful login, redirects to `/app` (ERPNext Desk)

## Customization

### Change Logo Path

Edit `login.html` line 155:
```html
<img src="/files/your-logo.png" alt="Pluviago" class="left-logo-img">
```

### Change Colors

Edit the CSS variables at the top of `login.html`:
```css
:root {
    --coral: #E8533F;           /* Primary brand color */
    --coral-light: #F17A6A;     /* Light variant */
    --coral-dark: #C9402E;      /* Dark variant */
    --charcoal: #1A1A1A;        /* Text color */
    /* ... */
}
```

### Change Welcome Text

Edit `login.html` around line 240:
```html
<div class="right-brand-name">PLUVIAGO</div>
<h2>Welcome to login</h2>
<p>Don't have an account?</p>
```

### Modify Form Fields

The form fields are in the left panel section (around line 160-190). You can:
- Add additional fields
- Change labels
- Modify validation

## Testing

1. **Clear browser cache** to see the new login page
2. Navigate to `/login` on your site
3. Test login with valid credentials
4. Verify redirect to `/app` after successful login
5. Test error messages with invalid credentials

## Troubleshooting

### Login page not showing

```bash
# Rebuild assets
bench build --app pluviago
bench --site <site_name> clear-cache

# Restart bench
bench restart
```

### Logo not displaying

1. Check if logo file exists in Files
2. Verify file path in `login.html`
3. Check browser console for 404 errors
4. Ensure file permissions are correct

### Login not working

1. Check browser console for JavaScript errors
2. Verify CSRF token is being fetched correctly
3. Check network tab for API call status
4. Verify Frappe login API endpoint is accessible

### Styling issues

1. Clear browser cache
2. Check if Bootstrap/Font Awesome CDN is accessible
3. Verify custom CSS is not being overridden
4. Check for conflicting styles in other apps

## Overriding Default Login

If you want to completely replace ERPNext's default login:

1. **Option 1:** Set as home page (not recommended - affects all routes)
   ```python
   # In hooks.py
   home_page = "login"
   ```

2. **Option 2:** Use website route rules (recommended)
   - The custom login at `/login` will be used automatically
   - Default ERPNext login remains at `/login?cmd=web_form` if needed

## Security Notes

- ✅ CSRF protection is implemented
- ✅ Password field uses proper input type
- ✅ Form validation on client side
- ✅ Server-side authentication via Frappe API
- ✅ No credentials stored in client-side code

## Browser Compatibility

- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Mobile browsers (responsive design)

## Support

For issues:
1. Check Frappe logs: `tail -f logs/web.log`
2. Check browser console for errors
3. Verify all files are in correct locations
4. Ensure app is properly installed: `bench --site <site> list-apps | grep pluviago`

---

**Last Updated:** February 2026
