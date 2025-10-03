import libtorrent as lt
import threading
import time
import os
import tempfile
from typing import Optional, Callable, Dict, Any
import logging

class TorrentManager:
    def __init__(self):
        self.session = lt.session()
        self.session.listen_on(6881, 6891)
        self.active_torrents = {}
        self.download_dir = tempfile.mkdtemp(prefix="torrent_player_")
        self.logger = logging.getLogger(__name__)
        
        # Configure session settings
        settings = self.session.get_settings()
        settings['user_agent'] = 'TorrentPlayer/1.0'
        settings['download_rate_limit'] = 0  # No limit
        settings['upload_rate_limit'] = 0    # No limit
        settings['active_downloads'] = 1
        settings['active_seeds'] = 1
        settings['active_limit'] = 1
        self.session.set_settings(settings)
    
    def add_torrent(self, torrent_url: str, callback: Optional[Callable] = None) -> Optional[str]:
        """
        Add a torrent for downloading/streaming
        Returns torrent handle ID if successful
        """
        try:
            # Create torrent parameters
            params = {
                'url': torrent_url,
                'save_path': self.download_dir,
                'storage_mode': lt.storage_mode_t.storage_mode_sparse
            }
            
            # Add torrent to session
            handle = self.session.add_torrent(params)
            torrent_id = str(handle.info_hash())
            
            # Store torrent info
            self.active_torrents[torrent_id] = {
                'handle': handle,
                'url': torrent_url,
                'callback': callback,
                'status': 'downloading',
                'progress': 0.0,
                'download_rate': 0,
                'upload_rate': 0,
                'peers': 0,
                'files': []
            }
            
            # Start monitoring thread
            monitor_thread = threading.Thread(
                target=self._monitor_torrent, 
                args=(torrent_id,),
                daemon=True
            )
            monitor_thread.start()
            
            self.logger.info(f"Added torrent: {torrent_id}")
            return torrent_id
            
        except Exception as e:
            self.logger.error(f"Failed to add torrent: {e}")
            return None
    
    def _monitor_torrent(self, torrent_id: str):
        """
        Monitor torrent progress and update status
        """
        torrent_info = self.active_torrents.get(torrent_id)
        if not torrent_info:
            return
        
        handle = torrent_info['handle']
        
        while torrent_id in self.active_torrents:
            try:
                status = handle.status()
                
                # Update torrent info
                torrent_info['progress'] = status.progress * 100
                torrent_info['download_rate'] = status.download_rate
                torrent_info['upload_rate'] = status.upload_rate
                torrent_info['peers'] = status.num_peers
                torrent_info['status'] = str(status.state)
                
                # Get file list if not already done
                if not torrent_info['files'] and handle.torrent_file():
                    torrent_file = handle.torrent_file()
                    files = []
                    for i in range(torrent_file.num_files()):
                        file_info = torrent_file.file_at(i)
                        files.append({
                            'path': file_info.path,
                            'size': file_info.size,
                            'priority': handle.file_priority(i)
                        })
                    torrent_info['files'] = files
                
                # Call callback if provided
                if torrent_info['callback']:
                    torrent_info['callback'](torrent_id, torrent_info)
                
                # Check if torrent is complete
                if status.is_finished:
                    torrent_info['status'] = 'completed'
                    self.logger.info(f"Torrent completed: {torrent_id}")
                    break
                
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error monitoring torrent {torrent_id}: {e}")
                break
    
    def get_torrent_status(self, torrent_id: str) -> Optional[Dict]:
        """
        Get current status of a torrent
        """
        return self.active_torrents.get(torrent_id)
    
    def get_torrent_files(self, torrent_id: str) -> list:
        """
        Get list of files in a torrent
        """
        torrent_info = self.active_torrents.get(torrent_id)
        if not torrent_info:
            return []
        
        return torrent_info.get('files', [])
    
    def get_file_path(self, torrent_id: str, file_index: int) -> Optional[str]:
        """
        Get local path of a specific file in the torrent
        """
        torrent_info = self.active_torrents.get(torrent_id)
        if not torrent_info:
            return None
        
        handle = torrent_info['handle']
        files = torrent_info.get('files', [])
        
        if file_index >= len(files):
            return None
        
        file_path = os.path.join(self.download_dir, files[file_index]['path'])
        return file_path if os.path.exists(file_path) else None
    
    def prioritize_file(self, torrent_id: str, file_index: int, priority: int = 7):
        """
        Set priority for a specific file in the torrent
        Priority: 0 = don't download, 1-7 = download priority
        """
        torrent_info = self.active_torrents.get(torrent_id)
        if not torrent_info:
            return False
        
        try:
            handle = torrent_info['handle']
            handle.file_priority(file_index, priority)
            return True
        except Exception as e:
            self.logger.error(f"Failed to set file priority: {e}")
            return False
    
    def pause_torrent(self, torrent_id: str):
        """
        Pause a torrent
        """
        torrent_info = self.active_torrents.get(torrent_id)
        if not torrent_info:
            return False
        
        try:
            torrent_info['handle'].pause()
            torrent_info['status'] = 'paused'
            return True
        except Exception as e:
            self.logger.error(f"Failed to pause torrent: {e}")
            return False
    
    def resume_torrent(self, torrent_id: str):
        """
        Resume a torrent
        """
        torrent_info = self.active_torrents.get(torrent_id)
        if not torrent_info:
            return False
        
        try:
            torrent_info['handle'].resume()
            torrent_info['status'] = 'downloading'
            return True
        except Exception as e:
            self.logger.error(f"Failed to resume torrent: {e}")
            return False
    
    def remove_torrent(self, torrent_id: str, delete_files: bool = False):
        """
        Remove a torrent from the session
        """
        torrent_info = self.active_torrents.get(torrent_id)
        if not torrent_info:
            return False
        
        try:
            self.session.remove_torrent(torrent_info['handle'])
            del self.active_torrents[torrent_id]
            
            if delete_files:
                # Clean up downloaded files
                for file_info in torrent_info.get('files', []):
                    file_path = os.path.join(self.download_dir, file_info['path'])
                    if os.path.exists(file_path):
                        os.remove(file_path)
            
            self.logger.info(f"Removed torrent: {torrent_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to remove torrent: {e}")
            return False
    
    def get_video_files(self, torrent_id: str) -> list:
        """
        Get list of video files in a torrent
        """
        files = self.get_torrent_files(torrent_id)
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
        
        video_files = []
        for i, file_info in enumerate(files):
            file_path = file_info['path'].lower()
            if any(file_path.endswith(ext) for ext in video_extensions):
                video_files.append({
                    'index': i,
                    'path': file_info['path'],
                    'size': file_info['size'],
                    'local_path': self.get_file_path(torrent_id, i)
                })
        
        return video_files
    
    def cleanup(self):
        """
        Clean up all torrents and temporary files
        """
        for torrent_id in list(self.active_torrents.keys()):
            self.remove_torrent(torrent_id, delete_files=True)
        
        # Clean up download directory
        try:
            import shutil
            shutil.rmtree(self.download_dir, ignore_errors=True)
        except Exception as e:
            self.logger.error(f"Failed to cleanup download directory: {e}")

if __name__ == "__main__":
    # Test the torrent manager
    manager = TorrentManager()
    
    def progress_callback(torrent_id, torrent_info):
        print(f"Torrent {torrent_id}: {torrent_info['progress']:.1f}% - "
              f"{torrent_info['download_rate']} bytes/s")
    
    # Example usage
    torrent_url = "magnet:?xt=urn:btih:..."  # Replace with actual magnet link
    torrent_id = manager.add_torrent(torrent_url, progress_callback)
    
    if torrent_id:
        print(f"Added torrent: {torrent_id}")
        time.sleep(10)  # Monitor for 10 seconds
        manager.cleanup()
