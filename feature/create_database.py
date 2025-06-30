import requests
import time
import sqlite3
import os
from dotenv import load_dotenv

def fetch_data(url):
    """Fetches the master list data from the given URL."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    cache_buster = f"?_={int(time.time())}"
    full_url = url + cache_buster
    try:
        response = requests.get(full_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None
    except ValueError:
        return None

def create_database(db_path='data/anisong.db', batch_size=1000):
    """Fetches data from the web and populates the SQLite database using batch processing to save memory."""
    load_dotenv()
    url = os.getenv('SECRECT_LINK')
    if not url:
        print("SECRECT_LINK not found in .env file.")
        return

    print("Fetching data...")
    raw_data = fetch_data(url)
    if not raw_data:
        print("Failed to fetch or parse data.")
        return
    print("Data fetched successfully.")

    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute('CREATE TABLE artists (artistId INTEGER PRIMARY KEY, name TEXT)')
    cursor.execute('CREATE TABLE groups (groupId INTEGER PRIMARY KEY, name TEXT)')
    cursor.execute('CREATE TABLE songs (songId INTEGER PRIMARY KEY, name TEXT, songArtistId INTEGER, songGroupId INTEGER, FOREIGN KEY(songArtistId) REFERENCES artists(artistId), FOREIGN KEY(songGroupId) REFERENCES groups(groupId))')
    cursor.execute('CREATE TABLE animes (animeId INTEGER PRIMARY KEY, mainNameJA TEXT, mainNameEN TEXT, year INTEGER, seasonId TEXT, category TEXT)')
    cursor.execute('CREATE TABLE animeSong (animeId INTEGER, songId INTEGER, type TEXT, number INTEGER, PRIMARY KEY (animeId, songId, type, number), FOREIGN KEY(animeId) REFERENCES animes(animeId), FOREIGN KEY(songId) REFERENCES songs(songId))')
    cursor.execute('CREATE TABLE groupMembers (groupId INTEGER, artistId INTEGER, PRIMARY KEY (groupId, artistId), FOREIGN KEY(groupId) REFERENCES groups(groupId), FOREIGN KEY(artistId) REFERENCES artists(artistId))')

    try:
        conn.execute('BEGIN TRANSACTION')

        # Process artists
        artist_data = raw_data.get('artistMap', {})
        artists_to_insert = [(int(id), data['name']) for id, data in artist_data.items()]
        cursor.executemany('INSERT INTO artists (artistId, name) VALUES (?, ?)', artists_to_insert)
        print(f"Inserted {len(artists_to_insert)} artists.")
        del artist_data, artists_to_insert

        # Process groups and group members
        group_data = raw_data.get('groupMap', {})
        groups_to_insert = [(int(id), data['name']) for id, data in group_data.items()]
        cursor.executemany('INSERT INTO groups (groupId, name) VALUES (?, ?)', groups_to_insert)
        print(f"Inserted {len(groups_to_insert)} groups.")
        
        group_members_to_insert = []
        for group_id, data in group_data.items():
            for artist_id in data.get('artistMembers', []):
                group_members_to_insert.append((int(group_id), int(artist_id)))
        cursor.executemany('INSERT INTO groupMembers (groupId, artistId) VALUES (?, ?)', group_members_to_insert)
        print(f"Inserted {len(group_members_to_insert)} group members.")
        del group_data, groups_to_insert, group_members_to_insert

        # Process songs with batching
        song_data = raw_data.get('songMap', {})
        songs_to_insert = []
        count = 0
        for id, data in song_data.items():
            songs_to_insert.append((int(id), data.get('name'), data.get('songArtistId'), data.get('songGroupId')))
            if len(songs_to_insert) >= batch_size:
                cursor.executemany('INSERT INTO songs (songId, name, songArtistId, songGroupId) VALUES (?, ?, ?, ?)', songs_to_insert)
                count += len(songs_to_insert)
                songs_to_insert = []
        if songs_to_insert:
            cursor.executemany('INSERT INTO songs (songId, name, songArtistId, songGroupId) VALUES (?, ?, ?, ?)', songs_to_insert)
            count += len(songs_to_insert)
        print(f"Inserted {count} songs.")
        del song_data, songs_to_insert

        # Process animes and anime-song links with batching
        anime_data = raw_data.get('animeMap', {})
        animes_to_insert = []
        anime_songs_to_insert = []
        anime_count = 0
        
        for anime_id, data in anime_data.items():
            animes_to_insert.append((
                int(anime_id), data['mainNames'].get('JA'), data['mainNames'].get('EN'),
                data.get('year'), data.get('seasonId'), data.get('category')
            ))
            for link_type, song_list in data.get('songLinks', {}).items():
                for song_link in song_list:
                    anime_songs_to_insert.append((
                        int(anime_id), song_link['songId'], link_type, song_link['number']
                    ))
            
            if len(animes_to_insert) >= batch_size:
                cursor.executemany('INSERT INTO animes (animeId, mainNameJA, mainNameEN, year, seasonId, category) VALUES (?, ?, ?, ?, ?, ?)', animes_to_insert)
                anime_count += len(animes_to_insert)
                animes_to_insert = []

        if animes_to_insert:
            cursor.executemany('INSERT INTO animes (animeId, mainNameJA, mainNameEN, year, seasonId, category) VALUES (?, ?, ?, ?, ?, ?)', animes_to_insert)
            anime_count += len(animes_to_insert)
        
        print(f"Inserted {anime_count} animes.")
        del anime_data, animes_to_insert
        del raw_data # Explicitly delete the largest data object

        # Insert unique anime-song links
        unique_anime_songs = set(anime_songs_to_insert)
        cursor.executemany('INSERT INTO animeSong (animeId, songId, type, number) VALUES (?, ?, ?, ?)', list(unique_anime_songs))
        print(f"Inserted {len(unique_anime_songs)} unique anime-song links.")
        del anime_songs_to_insert, unique_anime_songs

        # Create indexes
        print("Creating indexes...")
        cursor.execute('CREATE INDEX idx_songs_name ON songs (name)')
        cursor.execute('CREATE INDEX idx_artists_name ON artists (name)')
        cursor.execute('CREATE INDEX idx_animes_name_en ON animes (mainNameEN)')
        cursor.execute('CREATE INDEX idx_animeSong_songId ON animeSong (songId)')
        
        conn.commit()
        print("Database update successful.")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error: {e}. Rolling back changes.")
        raise e
    finally:
        conn.close()
        print("Database connection closed.")

if __name__ == '__main__':
    create_database()