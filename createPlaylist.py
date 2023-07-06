import requests
from urllib.parse import unquote
import re
from tqdm import tqdm
import zipfile
import os
import subprocess
from ShazamAPI import Shazam

playlist_name = 'New Playlist'

def download_file(url):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        # Try to get filename from content-disposition
        content_disposition = r.headers.get('content-disposition')
        if content_disposition:
            fname = re.findall('filename=(.+)', content_disposition)
            if len(fname) == 0:
                local_filename = url.split("/")[-1]
            else:
                match = re.search(r'"(.*?)"', unquote(fname[0]))
                local_filename = match.group(1)
        else:
            local_filename = url.split("/")[-1]

        file_size = int(r.headers.get('Content-Length', 0))
        chunk_size = 1024
        num_bars = int(file_size / chunk_size)

        with open(local_filename, 'wb') as f:
            for chunk in tqdm(r.iter_content(chunk_size=chunk_size), total=num_bars, unit='KB', desc=local_filename, leave=True):
                f.write(chunk)
    return local_filename

def extract_zip(file_path, extract_path):
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)


def convert_mov_to_mp3(directory):
    mp3_files = []

    for filename in os.listdir(directory):
        if filename.endswith(".mov"):
            mov_file = os.path.join(directory, filename)
            mp3_file = os.path.join(directory, os.path.splitext(filename)[0] + ".mp3")
            subprocess.call(['ffmpeg', '-i', mov_file, '-loglevel', 'panic', mp3_file])
            mp3_files.append(mp3_file)

    return mp3_files

clips_dir = './clips/'

# take input of URL
print('Enter Dropbox URL: ')
url = input()

# Replace url with dl=1
url = url.replace('dl=0', 'dl=1')

# Download file from url
print('\nDownloading clips...')
clip_files = download_file(url)
playlist_name = clip_files.split('.')[0]

extract_zip(clip_files, clips_dir)

audio_files = convert_mov_to_mp3(clips_dir)
#print('Audio Files:')
#print(audio_files)

print('\nFinding music:')
# Analyze music
songs = []
for audio_file in audio_files:
    #print('Checking ' + audio_file + ':')
    mp3_file_content_to_recognize = open(audio_file, 'rb').read()

    shazam = Shazam(mp3_file_content_to_recognize)
    recognize_generator = shazam.recognizeSong()
    while True:
        try:
            detected_song = next(recognize_generator)
            #song = {}
            #song['title'] = detected_song[1]['track']['title']
            #song['subtitle'] = detected_song[1]['track']['subtitle']

            song = detected_song[1]['track']['title'] + ' - ' + detected_song[1]['track']['subtitle']
            print(song)
            # Append detected_song to songs
            songs.append(song)
        except:
            break
        
#print('------------')
#print('Here is your playlist:')
playlist = list(set(songs))
#for music in playlist:
#    print(music)

#unique_songs = [dict(t) for t in {tuple(sorted(d.items())) for d in songs}]
#for song in unique_songs:
#    print_song(song)


''' SPOTIFY INTEGRATION '''

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
load_dotenv()


# set your Spotify app credentials
SPOTIPY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')

# set your Spotify username and playlist name
username = 'jayhxmo'

# set the song names
song_names = playlist

# ask the user if they want to create a Spotify playlist
response = input("\nConvert to Spotify playlist? (Y/n): ")

if response.lower() in ['y', '']:
    # authenticate
    scope = 'playlist-modify-public'
    token = SpotifyOAuth(scope=scope, client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI)

    sp = spotipy.Spotify(auth_manager=token)

    # create a new playlist and get its id
    playlist = sp.user_playlist_create(username, playlist_name)
    playlist_id = playlist['id']

    # search for the track URIs
    track_ids = []
    for song in song_names:
        result = sp.search(q=song, limit=1)
        track_id = result['tracks']['items'][0]['id']
        track_ids.append(track_id)

    # add tracks to the playlist
    sp.playlist_add_items(playlist_id, track_ids)
    print('\nDone!')
    print('Enjoy :)')
