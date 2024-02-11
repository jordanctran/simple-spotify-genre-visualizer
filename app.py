from flask import Flask, request, redirect, url_for, session, render_template, send_from_directory
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import matplotlib.pyplot as plt
import uuid
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['IMAGE_FOLDER'] = 'static/images'

# Spotify OAuth setup
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')
SCOPE = 'playlist-read-private'

sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                        client_secret=SPOTIPY_CLIENT_SECRET,
                        redirect_uri=SPOTIPY_REDIRECT_URI,
                        scope=SCOPE)

# Authentication route
@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

# Callback route
@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('analyze'))

# Route for analyzing playlist genres
@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    if request.method == 'POST':
        playlist_name = request.form['playlist_name']
        token_info = session.get('token_info', None)
        if not token_info:
            return redirect(url_for('login'))

        sp = spotipy.Spotify(auth=token_info['access_token'])
        playlist_tracks = fetch_playlist_data(sp, playlist_name)
        if playlist_tracks:
            genre_count = get_top_genres_from_playlist(sp, playlist_tracks)
            image_name = f"{uuid.uuid4()}.png"
            image_path = os.path.join(app.config['IMAGE_FOLDER'], image_name)
            plot_top_genres(genre_count, image_path, playlist_name)  # Pass playlist_name here
            return render_template('show_genres.html', image_file=image_name, playlist_name=playlist_name)  # Pass playlist_name to the template
        else:
            error_message = f"{playlist_name} does not exist. Please try again."
            return render_template('analyze.html', error_message=error_message)

    # GET request or initial page load
    return render_template('analyze.html')

# Helper function to fetch playlist data
def fetch_playlist_data(sp, playlist_name):
    results = sp.current_user_playlists()
    for playlist in results['items']:
        if playlist['name'].lower() == playlist_name.lower():
            return sp.playlist_tracks(playlist['id'])
    return None

# Helper function to get top genres from playlist
def get_top_genres_from_playlist(sp, tracks):
    genre_count = {}
    for item in tracks['items']:
        track = item['track']
        if track is not None:  # Check if track details are available
            artist_id = track['artists'][0]['id']
            artist_genres = sp.artist(artist_id)['genres']
            for genre in artist_genres:
                genre_count[genre] = genre_count.get(genre, 0) + 1

    # Sort genres by count in descending order and keep the top 10
    top_genres = dict(sorted(genre_count.items(), key=lambda item: item[1], reverse=True)[:10])
    return top_genres

# Helper function to plot top genres and save as an image
def plot_top_genres(genre_count, image_path, playlist_name):
    # Extract genres and counts
    genres = list(genre_count.keys())
    counts = list(genre_count.values())

    # Define Spotify brand colors
    spotify_green = '#1DB954'
    spotify_black = '#191414'  # Darker shade of black

    # Create a figure and axes
    fig, ax = plt.subplots(figsize=(8, 8))

    # Plotting the data as a pie chart
    ax.pie(counts, labels=genres, autopct='%1.1f%%', startangle=140, colors=[spotify_green, spotify_black])

    # Equal aspect ratio ensures that pie is drawn as a circle
    ax.axis('equal')

    # Add a title with playlist name
    ax.set_title(f'Top Genres in {playlist_name}', fontsize=16, color='white')

    # Save the plot with a transparent background
    plt.savefig(image_path, bbox_inches='tight', facecolor=fig.get_facecolor(), transparent=True)
    plt.close()

# Route for serving plot images
@app.route('/images/<filename>')
def image(filename):
    return send_from_directory(app.config['IMAGE_FOLDER'], filename)

# Homepage route
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
