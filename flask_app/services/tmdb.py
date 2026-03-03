import os
import requests
from flask import current_app

BASE_URL = 'https://api.themoviedb.org/3'
API_KEY = os.getenv('TMDB_API_KEY')

def get_genres():
    """Fetch list of movie genres from TMDB."""
    url = f'{BASE_URL}/genre/movie/list'
    params = {'api_key': API_KEY}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json().get('genres', [])

def get_movies_by_genre(genre_id, page=1):
    """Fetch movies for a specific genre, sorted by popularity."""
    url = f'{BASE_URL}/discover/movie'
    params = {
        'api_key': API_KEY,
        'with_genres': genre_id,
        'sort_by': 'popularity.desc',
        'page': page
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json().get('results', [])

def get_movie_details(movie_id):
    """Fetch detailed info for a single movie."""
    url = f'{BASE_URL}/movie/{movie_id}'
    params = {'api_key': API_KEY}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()

def get_movie_trailer(movie_id):
    """Fetch videos for a movie and return the first YouTube trailer."""
    url = f'{BASE_URL}/movie/{movie_id}/videos'
    params = {'api_key': API_KEY}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    videos = resp.json().get('results', [])
    for video in videos:
        if video['type'] == 'Trailer' and video['site'] == 'YouTube':
            return video
    return None

def get_popular_movies():
    """Fetch popular movies from TMDB."""
    url = f'{BASE_URL}/movie/popular'
    params = {'api_key': API_KEY, 'language': 'en-US', 'page': 1}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json().get('results', [])

def search_movies(query):
    """Search for movies by title using a search string."""
    url = f'{BASE_URL}/search/movie'
    params = {
        'api_key': current_app.config['TMDB_API_KEY'],
        'query': query
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json().get('results', [])