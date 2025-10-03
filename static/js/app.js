class TorrentPlayerApp {
    constructor() {
        this.socket = null;
        this.sessionId = this.generateSessionId();
        this.currentMovies = [];
        this.currentPage = 1;
        this.currentMovie = null;
        this.isPlaying = false;
        
        this.init();
    }
    
    init() {
        this.setupSocket();
        this.setupEventListeners();
        this.loadMovies();
        this.setupServiceWorker();
    }
    
    generateSessionId() {
        return 'session_' + Math.random().toString(36).substr(2, 9);
    }
    
    setupSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.showToast('Connected to server', 'success');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.showToast('Disconnected from server', 'warning');
        });
        
        this.socket.on('torrent_progress', (data) => {
            if (data.session_id === this.sessionId) {
                this.updateTorrentStatus(data);
            }
        });
        
        this.socket.on('video_ready', (data) => {
            if (data.session_id === this.sessionId) {
                this.playVideo(data.video_path);
            }
        });
        
        this.socket.emit('join_session', { session_id: this.sessionId });
    }
    
    setupEventListeners() {
        // Search functionality
        document.getElementById('searchBtn').addEventListener('click', () => {
            this.searchMovies();
        });
        
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.searchMovies();
            }
        });
        
        // Load more movies
        document.getElementById('loadMoreBtn').addEventListener('click', () => {
            this.loadMoreMovies();
        });
        
        // Control buttons
        document.getElementById('pauseBtn').addEventListener('click', () => {
            this.controlTorrent('pause');
        });
        
        document.getElementById('resumeBtn').addEventListener('click', () => {
            this.controlTorrent('resume');
        });
        
        document.getElementById('stopBtn').addEventListener('click', () => {
            this.controlTorrent('stop');
        });
        
        // Mobile navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const panel = e.currentTarget.dataset.panel;
                this.switchPanel(panel);
            });
        });
        
        // Video player events
        const videoPlayer = document.getElementById('videoPlayer');
        videoPlayer.addEventListener('loadstart', () => {
            this.showToast('Loading video...', 'info');
        });
        
        videoPlayer.addEventListener('canplay', () => {
            this.showToast('Video ready to play', 'success');
        });
        
        videoPlayer.addEventListener('error', (e) => {
            this.showToast('Video playback error', 'error');
            console.error('Video error:', e);
        });
    }
    
    async loadMovies(query = '') {
        this.showLoading(true);
        
        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                limit: 20,
                quality: document.getElementById('qualitySelect').value
            });
            
            if (query) {
                params.append('query', query);
            }
            
            const response = await fetch(`/api/movies?${params}`);
            const data = await response.json();
            
            if (data.success) {
                if (query) {
                    this.currentMovies = data.movies;
                    this.currentPage = 1;
                } else {
                    this.currentMovies = [...this.currentMovies, ...data.movies];
                }
                this.renderMovies();
                this.showToast(`Loaded ${data.movies.length} movies`, 'success');
            } else {
                this.showToast(data.error || 'Failed to load movies', 'error');
            }
        } catch (error) {
            console.error('Error loading movies:', error);
            this.showToast('Failed to load movies', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    async searchMovies() {
        const query = document.getElementById('searchInput').value.trim();
        if (!query) {
            this.showToast('Please enter a search term', 'warning');
            return;
        }
        
        await this.loadMovies(query);
    }
    
    async loadMoreMovies() {
        this.currentPage++;
        await this.loadMovies();
    }
    
    renderMovies() {
        const grid = document.getElementById('moviesGrid');
        grid.innerHTML = '';
        
        this.currentMovies.forEach(movie => {
            const card = this.createMovieCard(movie);
            grid.appendChild(card);
        });
    }
    
    createMovieCard(movie) {
        const card = document.createElement('div');
        card.className = 'movie-card';
        card.addEventListener('click', () => this.playMovie(movie));
        
        const poster = movie.medium_cover_image || movie.large_cover_image || '/static/images/no-poster.png';
        
        card.innerHTML = `
            <img src="${poster}" alt="${movie.title}" class="movie-poster" 
                 onerror="this.src='/static/images/no-poster.png'">
            <div class="movie-info">
                <h3 class="movie-title">${movie.title}</h3>
                <p class="movie-year">${movie.year}</p>
                <div class="movie-rating">
                    <span class="rating-stars">⭐</span>
                    <span>${movie.rating}/10</span>
                </div>
                <div class="movie-genres">
                    ${movie.genres.slice(0, 3).map(genre => 
                        `<span class="genre-tag">${genre}</span>`
                    ).join('')}
                </div>
            </div>
        `;
        
        return card;
    }
    
    async playMovie(movie) {
        this.currentMovie = movie;
        this.showToast(`Starting ${movie.title}...`, 'info');
        
        try {
            const response = await fetch('/api/play', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    movie_id: movie.id,
                    quality: document.getElementById('qualitySelect').value,
                    session_id: this.sessionId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.switchToVideoPanel();
                this.updateMovieDetails(movie);
                this.enableControlButtons();
                this.showToast('Torrent started successfully', 'success');
            } else {
                this.showToast(data.error || 'Failed to start movie', 'error');
            }
        } catch (error) {
            console.error('Error playing movie:', error);
            this.showToast('Failed to start movie', 'error');
        }
    }
    
    playVideo(videoPath) {
        const videoPlayer = document.getElementById('videoPlayer');
        videoPlayer.src = videoPath;
        videoPlayer.load();
        
        // Auto-play on mobile might be restricted, so we'll let user tap to play
        if (this.isMobile()) {
            this.showToast('Tap video to start playing', 'info');
        } else {
            videoPlayer.play().catch(e => {
                console.log('Autoplay prevented:', e);
                this.showToast('Click play button to start video', 'info');
            });
        }
        
        this.isPlaying = true;
    }
    
    async controlTorrent(action) {
        try {
            const response = await fetch(`/api/control/${this.sessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ action })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast(data.message, 'success');
                
                if (action === 'stop') {
                    this.stopVideo();
                }
            } else {
                this.showToast(data.error || 'Control failed', 'error');
            }
        } catch (error) {
            console.error('Error controlling torrent:', error);
            this.showToast('Control failed', 'error');
        }
    }
    
    stopVideo() {
        const videoPlayer = document.getElementById('videoPlayer');
        videoPlayer.pause();
        videoPlayer.src = '';
        this.isPlaying = false;
        this.disableControlButtons();
        this.switchToMoviesPanel();
    }
    
    updateTorrentStatus(data) {
        document.getElementById('statusValue').textContent = data.status;
        document.getElementById('progressFill').style.width = `${data.progress}%`;
        document.getElementById('progressText').textContent = `${data.progress.toFixed(1)}%`;
        document.getElementById('speedValue').textContent = this.formatBytes(data.download_rate) + '/s';
        document.getElementById('peersValue').textContent = data.peers;
        
        // Update control buttons based on status
        if (data.status === 'downloading') {
            document.getElementById('pauseBtn').disabled = false;
            document.getElementById('resumeBtn').disabled = true;
        } else if (data.status === 'paused') {
            document.getElementById('pauseBtn').disabled = true;
            document.getElementById('resumeBtn').disabled = false;
        }
    }
    
    updateMovieDetails(movie) {
        const details = document.getElementById('movieDetails');
        details.innerHTML = `
            <h3>${movie.title} (${movie.year})</h3>
            <p><strong>Rating:</strong> ${movie.rating}/10 ⭐</p>
            <p><strong>Runtime:</strong> ${movie.runtime} minutes</p>
            <p><strong>Genres:</strong> ${movie.genres.join(', ')}</p>
            <p><strong>Language:</strong> ${movie.language}</p>
            <p><strong>MPA Rating:</strong> ${movie.mpa_rating}</p>
            <div style="margin-top: 1rem;">
                <h4>Summary:</h4>
                <p style="color: rgba(255, 255, 255, 0.8); line-height: 1.5;">
                    ${movie.summary || 'No summary available'}
                </p>
            </div>
        `;
    }
    
    switchToVideoPanel() {
        document.getElementById('moviesPanel').style.display = 'none';
        document.getElementById('videoPanel').style.display = 'block';
        
        // Update mobile nav
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector('[data-panel="video"]').classList.add('active');
        
        // Update video title
        if (this.currentMovie) {
            document.getElementById('videoTitle').textContent = this.currentMovie.title;
            document.getElementById('videoDetails').textContent = 
                `${this.currentMovie.year} • ${this.currentMovie.rating}/10 ⭐`;
        }
    }
    
    switchToMoviesPanel() {
        document.getElementById('moviesPanel').style.display = 'block';
        document.getElementById('videoPanel').style.display = 'none';
        
        // Update mobile nav
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector('[data-panel="movies"]').classList.add('active');
    }
    
    switchPanel(panelName) {
        if (panelName === 'movies') {
            this.switchToMoviesPanel();
        } else if (panelName === 'video') {
            this.switchToVideoPanel();
        }
    }
    
    enableControlButtons() {
        document.getElementById('pauseBtn').disabled = false;
        document.getElementById('stopBtn').disabled = false;
    }
    
    disableControlButtons() {
        document.getElementById('pauseBtn').disabled = true;
        document.getElementById('resumeBtn').disabled = true;
        document.getElementById('stopBtn').disabled = true;
    }
    
    showLoading(show) {
        const indicator = document.getElementById('loadingIndicator');
        indicator.style.display = show ? 'block' : 'none';
    }
    
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }
    
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
    
    isMobile() {
        return window.innerWidth <= 768;
    }
    
    setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then(registration => {
                    console.log('Service Worker registered:', registration);
                })
                .catch(error => {
                    console.log('Service Worker registration failed:', error);
                });
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new TorrentPlayerApp();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Page is hidden, pause video if playing
        const videoPlayer = document.getElementById('videoPlayer');
        if (videoPlayer && !videoPlayer.paused) {
            videoPlayer.pause();
        }
    }
});

// Handle online/offline status
window.addEventListener('online', () => {
    window.app.showToast('Connection restored', 'success');
});

window.addEventListener('offline', () => {
    window.app.showToast('Connection lost', 'warning');
});
