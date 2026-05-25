# TheLineup API

Django REST Framework backend for TheLineup — a gig booking and musician management app. Bookers can create gigs, post open slots by instrument, and invite musicians. Musicians can accept or decline invites. Setlists are built from Spotify search and can be attached to gigs.

---

## Tech Stack

- Python / Django 5
- Django REST Framework
- Token authentication
- SQLite (local dev)
- Spotify Web API (Client Credentials flow)

---

## Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/docs/#installation)
- A [Spotify Developer](https://developer.spotify.com/dashboard) app (free) for the client ID and secret

---

## Local Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd server-capstone-api
```

### 2. Install dependencies

```bash
poetry install
```

### 3. Create your `.env` file

Create a `.env` file in the project root (same folder as `manage.py`):

```
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
```

To get these: go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard), create an app, and copy the Client ID and Client Secret.

### 4. Run migrations

```bash
poetry run python manage.py migrate
```

### 5. Load seed data

```bash
poetry run python manage.py loaddata instruments
poetry run python manage.py loaddata users
poetry run python manage.py loaddata user_profiles
poetry run python manage.py loaddata gigs
poetry run python manage.py loaddata gig_slots
poetry run python manage.py loaddata invites
poetry run python manage.py loaddata songs
poetry run python manage.py loaddata setlists
poetry run python manage.py loaddata setlist_songs
```

### 6. Start the server

```bash
poetry run python manage.py runserver
```

The API will be running at `http://localhost:8000`.

---

## Authentication

All endpoints require a token. To get one, register or log in:

```
POST /register
POST /login
```

Include the token in every request header:

```
Authorization: Token <your-token-here>
```

---

## API Endpoints

All routes use trailing slashes.

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/profiles/` | Get all user profiles |
| `GET` | `/profiles/{id}/` | Get a single profile |
| `PATCH` | `/profiles/{id}/` | Update your profile |
| `GET` | `/instruments/` | List all instruments |
| `GET` | `/gigs/` | Get gigs related to the logged-in user |
| `GET` | `/gigs/{id}/` | Get a single gig with its slots |
| `POST` | `/gigs/` | Create a gig |
| `PATCH` | `/gigs/{id}/` | Update a gig |
| `DELETE` | `/gigs/{id}/` | Delete a gig |
| `GET` | `/gigslots/` | Get slots for a gig (`?gig_id=1`) |
| `POST` | `/gigslots/` | Create a slot on a gig |
| `PATCH` | `/gigslots/{id}/` | Update a slot |
| `DELETE` | `/gigslots/{id}/` | Delete a slot |
| `GET` | `/invites/` | Get your received invites, or a gig's invites (`?gig_id=1`) |
| `POST` | `/invites/` | Send an invite to a musician |
| `PATCH` | `/invites/{id}/` | Accept, decline, or withdraw an invite |
| `DELETE` | `/invites/{id}/` | Delete an invite |
| `GET` | `/spotify-search/?q=` | Search Spotify for tracks |
| `POST` | `/songs/` | Save a song from Spotify to the database |
| `GET` | `/setlists/` | Get your setlists |
| `GET` | `/setlists/{id}/` | Get a single setlist with its songs |
| `POST` | `/setlists/` | Create a setlist |
| `PATCH` | `/setlists/{id}/` | Rename a setlist |
| `DELETE` | `/setlists/{id}/` | Delete a setlist |
| `POST` | `/setlist-songs/` | Add a song to a setlist |
| `DELETE` | `/setlist-songs/{id}/` | Remove a song from a setlist |

---

## Frontend

The React frontend lives in a separate repo. It expects the API at `http://localhost:8000` and requires CORS to allow `http://localhost:3000` or `http://localhost:5173` (both are already configured in settings).
