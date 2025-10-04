from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_socketio import SocketIO, emit
import threading
import time
import os
import json
import logging
from typing import Dict, List, Optional
import tempfile
import mimetypes

from yts_scraper import YTSScraper

# Try to import libtorrent, but handle gracefully if it fails
try:
    import libtorrent as lt
    LIBTORRENT_AVAILABLE = True
    print("✓ libtorrent loaded successfully")
except ImportError as e:
    LIBTORRENT_AVAILABLE = False
    print(f"⚠ libtorrent not available: {e}")
    print("Running in browser-only mode (no video streaming)")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'torrent_player_secret_key')
socketio = SocketIO(app, cors_allowed_origins="*")

# Global instances
scraper = YTSScraper()
torrent_manager = None
active_sessions = {}  # Store user sessions

# Initialize torrent manager only if libtorrent is available
if LIBTORRENT_AVAILABLE:
    try:
        from torrent_manager import TorrentManager
        torrent_manager = TorrentManager()
        print("✓ Torrent manager initialized")
    except Exception as e:
        print(f"⚠ Failed to initialize torrent manager: {e}")
        LIBTORRENT_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_movies = []
        self.current_torrent_id = None
        self.current_movie = None
        self.download_progress = 0.0
        self.status = "ready"

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/movies')
def get_movies():
    """Get movies from YTS"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        quality = request.args.get('quality', '720p')
        query = request.args.get('query', '')
        
        if query:
            movies = scraper.search_movies(query, limit)
        else:
            movies = scraper.get_movies(page=page, limit=limit, quality=quality)
        
        return jsonify({
            'success': True,
            'movies': movies,
            'total': len(movies)
        })
    except Exception as e:
        logger.error(f"Error fetching movies: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/movie/<int:movie_id>')
def get_movie_details(movie_id):
    """Get detailed movie information"""
    try:
        movie = scraper.get_movie_details(movie_id)
        if movie:
            return jsonify({
                'success': True,
                'movie': movie
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Movie not found'
            }), 404
    except Exception as e:
        logger.error(f"Error fetching movie details: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/torrent/<int:movie_id>')
def get_torrent_info(movie_id):
    """Get torrent information for a movie"""
    try:
        movie = scraper.get_movie_details(movie_id)
        if not movie:
            return jsonify({
                'success': False,
                'error': 'Movie not found'
            }), 404
        
        quality = request.args.get('quality', '720p')
        torrent = scraper.get_best_torrent(movie, quality)
        
        if torrent:
            return jsonify({
                'success': True,
                'torrent': {
                    'url': torrent.get('url'),
                    'quality': torrent.get('quality'),
                    'size': torrent.get('size'),
                    'seeds': torrent.get('seeds', 0),
                    'peers': torrent.get('peers', 0)
                },
                'movie': movie,
                'streaming_available': LIBTORRENT_AVAILABLE
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No torrent available for this quality'
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting torrent info: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/play', methods=['POST'])
def play_movie():
    """Start playing a movie"""
    if not LIBTORRENT_AVAILABLE or not torrent_manager:
        return jsonify({
            'success': False,
            'error': 'Torrent functionality not available. Please install libtorrent.',
            'torrent_info': 'Browser-only mode active'
        }), 503
    
    try:
        data = request.get_json()
        movie_id = data.get('movie_id')
        quality = data.get('quality', '720p')
        session_id = data.get('session_id', 'default')
        
        # Get or create session
        if session_id not in active_sessions:
            active_sessions[session_id] = WebSession(session_id)
        
        session = active_sessions[session_id]
        
        # Get movie details
        movie = scraper.get_movie_details(movie_id)
        if not movie:
            return jsonify({
                'success': False,
                'error': 'Movie not found'
            }), 404
        
        # Get best torrent
        torrent = scraper.get_best_torrent(movie, quality)
        if not torrent:
            return jsonify({
                'success': False,
                'error': 'No torrent available for this quality'
            }), 400
        
        # Start torrent download
        torrent_url = torrent.get('url')
        torrent_id = torrent_manager.add_torrent(
            torrent_url, 
            lambda tid, info: _on_torrent_progress(session_id, tid, info)
        )
        
        if torrent_id:
            session.current_torrent_id = torrent_id
            session.current_movie = movie
            session.status = "downloading"
            
            # Start monitoring for video files
            threading.Thread(
                target=_monitor_for_video_files,
                args=(session_id, torrent_id),
                daemon=True
            ).start()
            
            return jsonify({
                'success': True,
                'torrent_id': torrent_id,
                'message': 'Torrent started successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start torrent'
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting movie: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/status/<session_id>')
def get_status(session_id):
    """Get current session status"""
    session = active_sessions.get(session_id)
    if not session:
        return jsonify({
            'success': False,
            'error': 'Session not found'
        }), 404
    
    torrent_status = None
    if session.current_torrent_id and torrent_manager:
        torrent_status = torrent_manager.get_torrent_status(session.current_torrent_id)
    
    return jsonify({
        'success': True,
        'status': session.status,
        'progress': session.download_progress,
        'torrent_status': torrent_status,
        'current_movie': session.current_movie,
        'streaming_available': LIBTORRENT_AVAILABLE
    })

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('status', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('join_session')
def handle_join_session(data):
    """Handle client joining a session"""
    session_id = data.get('session_id', 'default')
    logger.info(f"Client {request.sid} joined session {session_id}")
    emit('session_joined', {'session_id': session_id})

def _on_torrent_progress(session_id: str, torrent_id: str, torrent_info: Dict):
    """Handle torrent progress updates"""
    session = active_sessions.get(session_id)
    if session:
        session.download_progress = torrent_info.get('progress', 0)
        session.status = torrent_info.get('status', 'downloading')
        
        # Emit progress update to all clients in this session
        socketio.emit('torrent_progress', {
            'session_id': session_id,
            'progress': session.download_progress,
            'status': session.status,
            'download_rate': torrent_info.get('download_rate', 0),
            'peers': torrent_info.get('peers', 0)
        })

def _monitor_for_video_files(session_id: str, torrent_id: str):
    """Monitor torrent for video files"""
    if not torrent_manager:
        return
        
    session = active_sessions.get(session_id)
    if not session:
        return
    
    while session.current_torrent_id == torrent_id:
        try:
            # Get video files
            video_files = torrent_manager.get_video_files(torrent_id)
            
            if video_files:
                # Find the largest video file
                main_video = max(video_files, key=lambda x: x['size'])
                
                # Check if file is available locally
                if main_video['local_path'] and os.path.exists(main_video['local_path']):
                    session.status = "ready_to_play"
                    
                    # Notify clients that video is ready
                    socketio.emit('video_ready', {
                        'session_id': session_id,
                        'video_path': f'/api/video/{session_id}',
                        'movie': session.current_movie
                    })
                    break
            
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error monitoring torrent: {e}")
            break

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    logger.info("Starting Torrent Player Web Server...")
    if LIBTORRENT_AVAILABLE:
        logger.info("✓ Full functionality available (streaming enabled)")
    else:
        logger.info("⚠ Running in browser-only mode (no video streaming)")
        logger.info("To enable streaming, install libtorrent properly")
    
    # Get port from environment variable (for Heroku) or use default
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
