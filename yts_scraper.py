import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Dict, Optional
import time

class YTSScraper:
    def __init__(self):
        self.base_url = "https://yts.mx"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_movies(self, page: int = 1, limit: int = 20, quality: str = "720p", 
                   minimum_rating: int = 0, query_term: str = "", 
                   genre: str = "", sort_by: str = "date_added") -> List[Dict]:
        """
        Fetch movies from YTS.mx API
        """
        try:
            url = f"{self.base_url}/api/v2/list_movies.json"
            params = {
                'page': page,
                'limit': limit,
                'quality': quality,
                'minimum_rating': minimum_rating,
                'query_term': query_term,
                'genre': genre,
                'sort_by': sort_by
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'ok':
                movies = data.get('data', {}).get('movies', [])
                return self._process_movies(movies)
            else:
                print(f"API Error: {data.get('status_message', 'Unknown error')}")
                return []
                
        except requests.RequestException as e:
            print(f"Request error: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return []
    
    def search_movies(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search for movies by title
        """
        return self.get_movies(query_term=query, limit=limit)
    
    def get_movie_details(self, movie_id: int) -> Optional[Dict]:
        """
        Get detailed information about a specific movie
        """
        try:
            url = f"{self.base_url}/api/v2/movie_details.json"
            params = {'movie_id': movie_id}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'ok':
                movie = data.get('data', {}).get('movie', {})
                return self._process_movie_details(movie)
            else:
                print(f"API Error: {data.get('status_message', 'Unknown error')}")
                return None
                
        except requests.RequestException as e:
            print(f"Request error: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return None
    
    def _process_movies(self, movies: List[Dict]) -> List[Dict]:
        """
        Process raw movie data from API
        """
        processed = []
        for movie in movies:
            processed_movie = {
                'id': movie.get('id'),
                'title': movie.get('title'),
                'year': movie.get('year'),
                'rating': movie.get('rating'),
                'runtime': movie.get('runtime'),
                'genres': movie.get('genres', []),
                'summary': movie.get('summary'),
                'language': movie.get('language'),
                'mpa_rating': movie.get('mpa_rating'),
                'background_image': movie.get('background_image'),
                'medium_cover_image': movie.get('medium_cover_image'),
                'large_cover_image': movie.get('large_cover_image'),
                'torrents': movie.get('torrents', [])
            }
            processed.append(processed_movie)
        return processed
    
    def _process_movie_details(self, movie: Dict) -> Dict:
        """
        Process detailed movie data
        """
        return {
            'id': movie.get('id'),
            'title': movie.get('title'),
            'year': movie.get('year'),
            'rating': movie.get('rating'),
            'runtime': movie.get('runtime'),
            'genres': movie.get('genres', []),
            'summary': movie.get('summary'),
            'language': movie.get('language'),
            'mpa_rating': movie.get('mpa_rating'),
            'background_image': movie.get('background_image'),
            'medium_cover_image': movie.get('medium_cover_image'),
            'large_cover_image': movie.get('large_cover_image'),
            'torrents': movie.get('torrents', []),
            'cast': movie.get('cast', []),
            'director': movie.get('director'),
            'imdb_code': movie.get('imdb_code'),
            'yt_trailer_code': movie.get('yt_trailer_code')
        }
    
    def get_best_torrent(self, movie: Dict, preferred_quality: str = "720p") -> Optional[Dict]:
        """
        Get the best available torrent for a movie based on quality preference
        """
        torrents = movie.get('torrents', [])
        if not torrents:
            return None
        
        # Sort by quality preference
        quality_order = ['2160p', '1080p', '720p', '480p']
        if preferred_quality in quality_order:
            preferred_index = quality_order.index(preferred_quality)
            quality_order = [preferred_quality] + [q for q in quality_order if q != preferred_quality]
        
        for quality in quality_order:
            for torrent in torrents:
                if torrent.get('quality') == quality:
                    return torrent
        
        # If no preferred quality found, return the first available
        return torrents[0] if torrents else None

if __name__ == "__main__":
    # Test the scraper
    scraper = YTSScraper()
    movies = scraper.get_movies(limit=5)
    print(f"Found {len(movies)} movies")
    for movie in movies:
        print(f"- {movie['title']} ({movie['year']}) - Rating: {movie['rating']}")
