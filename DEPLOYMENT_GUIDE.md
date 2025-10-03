# GitHub Deployment Guide for Torrent Player

## 🚀 Quick Deployment Options

### Option 1: Heroku (Recommended)
1. **Create Heroku Account**: Sign up at [heroku.com](https://heroku.com)
2. **Install Heroku CLI**: Download from [devcenter.heroku.com](https://devcenter.heroku.com/articles/heroku-cli)
3. **Deploy**:
   ```bash
   git clone https://github.com/yourusername/torrent-player.git
   cd torrent-player
   heroku create your-app-name
   git push heroku main
   ```
4. **Access**: Your app will be at `https://your-app-name.herokuapp.com`

### Option 2: Railway
1. **Connect GitHub**: Go to [railway.app](https://railway.app)
2. **Deploy from GitHub**: Connect your repository
3. **Auto-deploy**: Railway will automatically deploy your app

### Option 3: Render
1. **Sign up**: Go to [render.com](https://render.com)
2. **New Web Service**: Connect your GitHub repository
3. **Build Command**: `pip install -r requirements_heroku.txt`
4. **Start Command**: `python web_app_heroku.py`

### Option 4: PythonAnywhere
1. **Sign up**: Go to [pythonanywhere.com](https://pythonanywhere.com)
2. **Upload files**: Upload your project files
3. **Configure**: Set up web app with Flask
4. **Run**: Your app will be accessible via PythonAnywhere URL

## 📁 Files Needed for GitHub

### Required Files:
- `web_app_heroku.py` - Main application (Heroku-ready)
- `yts_scraper.py` - YTS.mx integration
- `templates/index.html` - Frontend template
- `static/css/style.css` - Styles
- `static/js/app.js` - JavaScript
- `requirements_heroku.txt` - Dependencies
- `Procfile` - Heroku process file
- `runtime.txt` - Python version
- `README_GITHUB.md` - Documentation

### Optional Files:
- `static/manifest.json` - PWA manifest
- `static/sw.js` - Service worker
- `create_placeholder.py` - Image generator

## 🔧 Configuration

### Environment Variables (Optional):
- `SECRET_KEY` - Flask secret key
- `PORT` - Server port (auto-set by hosting platform)

### Heroku Specific:
- Uses `web_app_heroku.py` instead of `web_app_robust.py`
- Includes `gunicorn` for production
- Handles port from environment variable
- Optimized for cloud deployment

## 🌐 Access Your Deployed App

Once deployed, your app will be accessible at:
- **Heroku**: `https://your-app-name.herokuapp.com`
- **Railway**: `https://your-app-name.railway.app`
- **Render**: `https://your-app-name.onrender.com`
- **PythonAnywhere**: `https://yourusername.pythonanywhere.com`

## 📱 Mobile Access

Your deployed app will work perfectly on mobile devices:
- **Responsive design** adapts to any screen size
- **PWA features** allow installation on mobile
- **Touch-friendly** interface optimized for mobile

## 🔄 Updates

To update your deployed app:
1. Make changes to your code
2. Commit and push to GitHub
3. Most platforms auto-deploy on push
4. Your changes will be live within minutes

## 💡 Tips

- **Free tiers** are available on most platforms
- **Custom domains** can be added for professional use
- **HTTPS** is automatically provided
- **Auto-scaling** handles traffic spikes

## ⚠️ Important Notes

- **libtorrent** may not work on free hosting tiers
- **Browser-only mode** will be active on most cloud platforms
- **File storage** is temporary on free tiers
- **Bandwidth limits** apply on free tiers

Your app will work great as a movie browser even without streaming functionality!
