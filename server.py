#!/usr/bin/env python3
"""Reelhouse web server and SQLite-backed booking API."""

from __future__ import annotations

import json
import base64
import binascii
import hmac
import mimetypes
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
PUBLIC_ROOT = (ROOT / "public").resolve()
DATA_ROOT = Path(
    os.environ.get("REELHOUSE_DATA_DIR")
    or os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
    or ROOT / "data"
).resolve()
DATABASE_PATH = Path(os.environ.get("REELHOUSE_DATABASE_PATH") or DATA_ROOT / "reelhouse.sqlite3").resolve()
ADMIN_PASSWORD = os.environ.get("REELHOUSE_ADMIN_PASSWORD", "")
PORT = int(os.environ.get("PORT", "5055"))
INDIA_TZ = ZoneInfo("Asia/Kolkata")
MAX_BODY = 1024 * 1024

MOVIES = [
    {"id": "after-the-light", "title": "After the Light", "language": "Hindi", "genre": "Drama", "genres": ["Drama", "Romance"], "duration": 128, "rating": "UA 13+", "score": "8.7", "reviews": "2.4k", "basePrice": 220, "badge": "CRITIC'S PICK", "featured": True, "poster": "https://images.unsplash.com/photo-1478720568477-152d9b164e26?auto=format&fit=crop&w=900&q=82", "cover": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=2000&q=88", "description": "A restless photographer returns to the town she left behind and finds an old friendship waiting in the last place she expects.", "cast": ["Aarav Mehta", "Mira Sethi", "Kabir Rao"]},
    {"id": "neon-run", "title": "Neon Run", "language": "English", "genre": "Action", "genres": ["Action", "Thriller"], "duration": 116, "rating": "A", "score": "8.3", "reviews": "1.8k", "basePrice": 260, "badge": "FAN FAVOURITE", "featured": False, "poster": "https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=900&q=82", "cover": "https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=2000&q=88", "description": "One night, one impossible delivery and an entire city on her tail. The streets have never looked this electric.", "cast": ["Riya Khanna", "Dev Malhotra", "Ishan Bose"]},
    {"id": "last-orbit", "title": "The Last Orbit", "language": "English", "genre": "Sci-Fi", "genres": ["Sci-Fi", "Adventure"], "duration": 142, "rating": "UA 13+", "score": "9.1", "reviews": "4.1k", "basePrice": 280, "badge": "IMAX", "featured": False, "poster": "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?auto=format&fit=crop&w=900&q=82", "cover": "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?auto=format&fit=crop&w=2000&q=88", "description": "With Earth fading below, a rookie pilot discovers that the most important mission is the one nobody planned for.", "cast": ["Noah James", "Priya Nair", "Levi Hart"]},
    {"id": "raat-baarish-ki", "title": "Raat Baarish Ki", "language": "Hindi", "genre": "Romance", "genres": ["Romance", "Drama"], "duration": 132, "rating": "UA 13+", "score": "7.9", "reviews": "980", "basePrice": 210, "badge": "NEW", "featured": False, "poster": "https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=900&q=82", "cover": "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=2000&q=88", "description": "Two strangers miss the last train on a rainy evening. The long walk home becomes a story neither saw coming.", "cast": ["Anaya Roy", "Rehaan Kapoor", "Sana Ali"]},
    {"id": "wild-signal", "title": "The Wild Signal", "language": "English", "genre": "Adventure", "genres": ["Adventure", "Drama"], "duration": 121, "rating": "UA 7+", "score": "8.5", "reviews": "1.2k", "basePrice": 240, "badge": "IN 4K", "featured": False, "poster": "https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=900&q=82", "cover": "https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=2000&q=88", "description": "A father and daughter follow a mysterious radio signal across the Himalayas, finding more than either set out to look for.", "cast": ["Vikram Arora", "Leela Sen", "Arjun Gill"]},
    {"id": "good-news-maybe", "title": "Good News, Maybe", "language": "Hindi", "genre": "Comedy", "genres": ["Comedy", "Family"], "duration": 108, "rating": "U", "score": "8.1", "reviews": "2.0k", "basePrice": 190, "badge": "LAUGH OUT LOUD", "featured": False, "poster": "https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&w=900&q=82", "cover": "https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&w=2000&q=88", "description": "A family WhatsApp group, a very confused wedding planner and one announcement that changes absolutely everything.", "cast": ["Naina Das", "Amit Verma", "Rohit Dey"]},
    {"id": "elara", "title": "Elara", "language": "Tamil", "genre": "Fantasy", "genres": ["Fantasy", "Adventure"], "duration": 137, "rating": "UA 13+", "score": "8.8", "reviews": "1.5k", "basePrice": 250, "badge": "IN 3D", "featured": False, "poster": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=900&q=82", "cover": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=2000&q=88", "description": "In a kingdom where memories can be traded, a mapmaker risks everything to remember the sister she lost.", "cast": ["Anika Raman", "Karthik Dev", "Meera Krish"]},
    {"id": "quiet-house", "title": "The Quiet House", "language": "English", "genre": "Thriller", "genres": ["Thriller", "Horror"], "duration": 104, "rating": "A", "score": "7.8", "reviews": "760", "basePrice": 230, "badge": "SUSPENSE", "featured": False, "poster": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=900&q=82", "cover": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=2000&q=88", "description": "The old house at the end of the lane has been empty for forty years. Tonight, someone left the porch light on.", "cast": ["Maya Collins", "Ethan Park", "Zara Khan"]},
    {"id": "monsoon-postcard", "title": "Monsoon Postcard", "language": "Malayalam", "genre": "Drama", "genres": ["Drama", "Family"], "duration": 119, "rating": "U", "score": "8.6", "reviews": "1.1k", "basePrice": 200, "badge": "HEARTWARMING", "featured": False, "poster": "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=900&q=82", "cover": "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=2000&q=88", "description": "A faded postcard sends a young chef back to a coastal village, where an unfinished family recipe waits to be found.", "cast": ["Nila Thomas", "Rahul Menon", "Anu Varghese"]},
]

CITIES = ["Delhi NCR", "Mumbai", "Bengaluru", "Hyderabad", "Chennai", "Pune"]
CINEMAS = [
    {"id": "pvr-cp", "name": "PVR Director's Cut", "area": "Connaught Place", "city": "Delhi NCR", "premium": 80, "formats": ["IMAX", "4DX", "Dolby Atmos"]},
    {"id": "inox-aerocity", "name": "INOX Luxe", "area": "Aerocity", "city": "Delhi NCR", "premium": 55, "formats": ["Dolby Atmos", "Laser"]},
    {"id": "cinepolis-noida", "name": "Cinépolis", "area": "Sector 18, Noida", "city": "Delhi NCR", "premium": 30, "formats": ["4DX", "Dolby Atmos"]},
    {"id": "pvr-andheri", "name": "PVR Icon", "area": "Andheri West", "city": "Mumbai", "premium": 75, "formats": ["IMAX", "Dolby Atmos"]},
    {"id": "inox-bandra", "name": "INOX", "area": "Bandra Kurla Complex", "city": "Mumbai", "premium": 45, "formats": ["Dolby Atmos", "Laser"]},
    {"id": "cinepolis-ghatkopar", "name": "Cinépolis", "area": "Ghatkopar", "city": "Mumbai", "premium": 25, "formats": ["4DX"]},
    {"id": "pvr-forum", "name": "PVR Forum", "area": "Koramangala", "city": "Bengaluru", "premium": 65, "formats": ["IMAX", "Dolby Atmos"]},
    {"id": "inox-orion", "name": "INOX", "area": "Rajajinagar", "city": "Bengaluru", "premium": 35, "formats": ["Laser", "Dolby Atmos"]},
    {"id": "cinepolis-whitefield", "name": "Cinépolis", "area": "Whitefield", "city": "Bengaluru", "premium": 25, "formats": ["4DX"]},
    {"id": "pvr-hitech", "name": "PVR Next Galleria", "area": "HITEC City", "city": "Hyderabad", "premium": 55, "formats": ["IMAX", "4DX"]},
    {"id": "inox-gvk", "name": "INOX", "area": "Banjara Hills", "city": "Hyderabad", "premium": 35, "formats": ["Dolby Atmos"]},
    {"id": "cinepolis-kukatpally", "name": "Cinépolis", "area": "Kukatpally", "city": "Hyderabad", "premium": 25, "formats": ["4DX"]},
    {"id": "pvr-express", "name": "PVR Aerohub", "area": "Meenambakkam", "city": "Chennai", "premium": 50, "formats": ["IMAX", "Dolby Atmos"]},
    {"id": "inox-chennai", "name": "INOX Luxe", "area": "Nungambakkam", "city": "Chennai", "premium": 35, "formats": ["Dolby Atmos", "Laser"]},
    {"id": "cinepolis-omr", "name": "Cinépolis", "area": "OMR", "city": "Chennai", "premium": 20, "formats": ["4DX"]},
    {"id": "pvr-pavilion", "name": "PVR Phoenix", "area": "Viman Nagar", "city": "Pune", "premium": 50, "formats": ["IMAX", "Dolby Atmos"]},
    {"id": "inox-westend", "name": "INOX", "area": "Aundh", "city": "Pune", "premium": 30, "formats": ["Laser"]},
    {"id": "cinepolis-seasons", "name": "Cinépolis", "area": "Hadapsar", "city": "Pune", "premium": 20, "formats": ["4DX"]},
]
SLOTS = [
    {"code": "1030", "time": "10:30 AM", "extra": 0},
    {"code": "1345", "time": "1:45 PM", "extra": 10},
    {"code": "1815", "time": "6:15 PM", "extra": 25},
    {"code": "2130", "time": "9:30 PM", "extra": 15},
]
MOVIE_BY_ID = {movie["id"]: movie for movie in MOVIES}
CINEMA_BY_ID = {cinema["id"]: cinema for cinema in CINEMAS}
SLOT_BY_CODE = {slot["code"]: slot for slot in SLOTS}
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SEAT_RE = re.compile(r"^[A-H](?:[1-9]|1[0-2])$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp() -> str:
    return utc_now().isoformat(timespec="milliseconds").replace("+00:00", "Z")


def db_connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 15000")
    return connection


@contextmanager
def database():
    connection = db_connect()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    connection = db_connect()
    try:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id TEXT PRIMARY KEY,
                show_id TEXT NOT NULL,
                email TEXT NOT NULL,
                status TEXT NOT NULL,
                booked_at TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS bookings_show_status ON bookings(show_id, status);
            CREATE TABLE IF NOT EXISTS booking_seats (
                show_id TEXT NOT NULL,
                seat_id TEXT NOT NULL,
                booking_id TEXT NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
                PRIMARY KEY(show_id, seat_id)
            );
            CREATE INDEX IF NOT EXISTS booking_seats_booking ON booking_seats(booking_id);
            CREATE TABLE IF NOT EXISTS newsletter_subscribers (
                email TEXT PRIMARY KEY,
                subscribed_at TEXT NOT NULL
            );
            """
        )
        import_legacy_json(connection)
        connection.commit()
    finally:
        connection.close()


def import_legacy_json(connection: sqlite3.Connection) -> None:
    legacy_bookings = DATA_ROOT / "bookings.json"
    if legacy_bookings.is_file():
        try:
            rows = json.loads(legacy_bookings.read_text(encoding="utf-8-sig") or "[]")
        except (OSError, json.JSONDecodeError):
            rows = []
        for booking in rows if isinstance(rows, list) else []:
            if not isinstance(booking, dict) or not booking.get("id") or not booking.get("showId"):
                continue
            booked_at = str(booking.get("bookedAt") or timestamp())
            inserted = connection.execute(
                "INSERT OR IGNORE INTO bookings(id, show_id, email, status, booked_at, payload) VALUES(?, ?, ?, ?, ?, ?)",
                (str(booking["id"]), str(booking["showId"]), str(booking.get("email", "")).lower(), str(booking.get("status", "Confirmed")), booked_at, json.dumps(booking, ensure_ascii=False)),
            ).rowcount
            if inserted and booking.get("status") == "Confirmed":
                connection.executemany(
                    "INSERT OR IGNORE INTO booking_seats(show_id, seat_id, booking_id) VALUES(?, ?, ?)",
                    [(str(booking["showId"]), str(seat).upper(), str(booking["id"])) for seat in booking.get("seats", [])],
                )

    legacy_newsletter = DATA_ROOT / "newsletter.json"
    if legacy_newsletter.is_file():
        try:
            rows = json.loads(legacy_newsletter.read_text(encoding="utf-8-sig") or "[]")
        except (OSError, json.JSONDecodeError):
            rows = []
        for subscriber in rows if isinstance(rows, list) else []:
            if isinstance(subscriber, dict) and subscriber.get("email"):
                connection.execute(
                    "INSERT OR IGNORE INTO newsletter_subscribers(email, subscribed_at) VALUES(?, ?)",
                    (str(subscriber["email"]).strip().lower(), str(subscriber.get("subscribedAt") or timestamp())),
                )


def valid_date(date_text: str | None) -> date | None:
    try:
        parsed = date.fromisoformat(date_text or "")
    except ValueError:
        return None
    today = datetime.now(INDIA_TZ).date()
    return parsed if today <= parsed <= today + timedelta(days=7) else None


def shows_for(movie_id: str | None, date_text: str | None, city: str | None) -> list[dict]:
    movie = MOVIE_BY_ID.get(movie_id or "")
    show_date = valid_date(date_text)
    if movie is None or show_date is None or city not in CITIES:
        return []
    date_value = show_date.isoformat()
    result = []
    for cinema in CINEMAS:
        if cinema["city"] != city:
            continue
        for slot in SLOTS:
            show_id = f"{movie_id}~{date_value}~{cinema['id']}~{slot['code']}"
            result.append({
                "id": show_id, "movieId": movie_id, "date": date_value, "time": slot["time"],
                "city": city, "cinema": cinema["name"], "area": cinema["area"],
                "price": int(movie["basePrice"]) + int(cinema["premium"]) + int(slot["extra"]),
                "formats": cinema["formats"], "screen": "Screen 1",
            })
    return result


def find_show(show_id: str | None) -> dict | None:
    parts = (show_id or "").split("~")
    if len(parts) != 4 or parts[2] not in CINEMA_BY_ID or parts[3] not in SLOT_BY_CODE:
        return None
    cinema = CINEMA_BY_ID[parts[2]]
    return next((show for show in shows_for(parts[0], parts[1], cinema["city"]) if show["id"] == show_id), None)


def seeded_sold_seats(show_id: str) -> set[str]:
    seed = sum(ord(char) for char in show_id) % 19
    sold = set()
    for index in range(96):
        if (index + seed) % 23 == 0 or index in (2, 9, 86, 93):
            sold.add(f"{chr(ord('A') + index // 12)}{index % 12 + 1}")
    return sold


def sold_seats(connection: sqlite3.Connection, show_id: str) -> set[str]:
    booked = connection.execute(
        "SELECT seat_id FROM booking_seats WHERE show_id = ?", (show_id,)
    ).fetchall()
    return seeded_sold_seats(show_id) | {row["seat_id"] for row in booked}


class ReelhouseHandler(BaseHTTPRequestHandler):
    server_version = "Reelhouse/2.0"

    def admin_authorized(self) -> bool:
        if not ADMIN_PASSWORD:
            self.send_error_json(503, "The private bookings page is not configured yet.")
            return False

        header = self.headers.get("Authorization", "")
        try:
            scheme, encoded = header.split(" ", 1)
            if scheme.lower() != "basic":
                raise ValueError("Unsupported authorization scheme")
            credentials = base64.b64decode(encoded, validate=True).decode("utf-8")
            username, password = credentials.split(":", 1)
        except (ValueError, UnicodeDecodeError, binascii.Error):
            username, password = "", ""

        valid = hmac.compare_digest(username.encode("utf-8"), b"admin") and hmac.compare_digest(
            password.encode("utf-8"), ADMIN_PASSWORD.encode("utf-8")
        )
        if valid:
            return True

        body = b"Authentication required. Sign in with the private admin password."
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Reelhouse Admin", charset="UTF-8"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
        return False

    def send_admin_page(self) -> None:
        page = ROOT / "admin.html"
        if not page.is_file():
            self.send_error_json(404, "The private bookings page is unavailable.")
            return
        body = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def send_admin_bookings(self) -> None:
        with database() as connection:
            rows = connection.execute(
                "SELECT id, status, booked_at, payload FROM bookings ORDER BY booked_at DESC"
            ).fetchall()

        bookings = []
        for row in rows:
            try:
                payload = json.loads(row["payload"])
            except (TypeError, json.JSONDecodeError):
                payload = {}
            show = payload.get("show") if isinstance(payload.get("show"), dict) else {}
            seats = payload.get("seats") if isinstance(payload.get("seats"), list) else []
            bookings.append({
                "id": row["id"],
                "status": row["status"],
                "bookedAt": row["booked_at"],
                "movie": payload.get("movieTitle") or payload.get("movieId") or "—",
                "cinema": show.get("cinema") or "—",
                "city": show.get("city") or "—",
                "showDate": show.get("date") or "—",
                "showTime": show.get("time") or "—",
                "seats": seats,
                "total": payload.get("total", 0),
            })
        self.send_json(200, {"bookings": bookings})

    def send_json(self, status: int, value) -> None:
        body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: int, message: str) -> None:
        self.send_json(status, {"error": message})

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid request body.")
        if length < 0 or length > MAX_BODY:
            raise ValueError("Request body is too large.")
        raw = self.rfile.read(length)
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def do_GET(self) -> None:
        self.handle_request("GET")

    def do_POST(self) -> None:
        self.handle_request("POST")

    def handle_request(self, method: str) -> None:
        parsed = urlsplit(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query, keep_blank_values=True)
        value = lambda key, default="": query.get(key, [default])[0]

        try:
            if path == "/admin" or path == "/admin/":
                if method == "GET" and self.admin_authorized():
                    self.send_admin_page()
                elif method != "GET":
                    self.send_error_json(405, "Method not allowed.")
                return
            if path == "/api/admin/bookings":
                if method == "GET" and self.admin_authorized():
                    self.send_admin_bookings()
                elif method != "GET":
                    self.send_error_json(405, "Method not allowed.")
                return
            if path == "/api/health" and method == "GET":
                with database() as connection:
                    count = connection.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
                self.send_json(200, {"status": "ok", "service": "Reelhouse", "bookings": count, "database": "sqlite"})
                return
            if path == "/api/cities" and method == "GET":
                self.send_json(200, CITIES)
                return
            if path == "/api/movies" and method == "GET":
                self.send_json(200, MOVIES)
                return
            if path == "/api/shows" and method == "GET":
                self.send_json(200, shows_for(value("movieId"), value("date"), value("city")))
                return
            if path == "/api/seats" and method == "GET":
                show_id = value("showId")
                show = find_show(show_id)
                if show is None:
                    self.send_error_json(404, "Showtime not found.")
                    return
                with database() as connection:
                    sold = sold_seats(connection, show_id)
                seats = []
                for row_index in range(8):
                    row = chr(ord("A") + row_index)
                    for number in range(1, 13):
                        seat_id = f"{row}{number}"
                        seats.append({"id": seat_id, "row": row, "number": number, "status": "sold" if seat_id in sold else "available"})
                self.send_json(200, {"show": show, "seats": seats, "maxSelection": 8})
                return
            if path == "/api/bookings" and method == "POST":
                self.create_booking()
                return
            match = re.fullmatch(r"/api/bookings/([^/]+)(?:/(cancel))?", path)
            if match:
                code = match.group(1)
                if match.group(2) == "cancel" and method == "POST":
                    self.cancel_booking(code)
                    return
                if match.group(2) is None and method == "GET":
                    self.lookup_booking(code, value("email"))
                    return
            if path == "/api/newsletter" and method == "POST":
                self.subscribe()
                return
            if method == "GET" and not path.startswith("/api/"):
                self.send_static(path)
                return
            self.send_error_json(404, "That page or API route was not found.")
        except ValueError as error:
            self.send_error_json(400, str(error))
        except sqlite3.Error:
            self.log_error("Database request failed")
            self.send_error_json(500, "Something went wrong. Please try again.")
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            self.log_error("Request failed")
            self.send_error_json(500, "Something went wrong. Please try again.")

    def create_booking(self) -> None:
        body = self.read_json()
        if not isinstance(body, dict):
            self.send_error_json(400, "Booking details are missing.")
            return
        movie = MOVIE_BY_ID.get(str(body.get("movieId", "")))
        show_id = str(body.get("showId", ""))
        show = find_show(show_id)
        name = str(body.get("name", "")).strip()
        email = str(body.get("email", "")).strip().lower()
        phone = str(body.get("phone", "")).strip()
        raw_seats = body.get("seats", [])
        if not isinstance(raw_seats, list):
            raw_seats = []
        seats = list(dict.fromkeys(str(seat).strip().upper() for seat in raw_seats))

        if movie is None or show is None or show["movieId"] != movie["id"]:
            self.send_error_json(400, "That movie or showtime is no longer available.")
        elif len(name) < 2 or len(name) > 80:
            self.send_error_json(400, "Enter a name between 2 and 80 characters.")
        elif not EMAIL_RE.fullmatch(email):
            self.send_error_json(400, "Enter a valid email address.")
        elif not re.fullmatch(r"[0-9+() .-]{7,20}", phone):
            self.send_error_json(400, "Enter a valid phone number.")
        elif not 1 <= len(seats) <= 8:
            self.send_error_json(400, "Choose between 1 and 8 seats.")
        elif any(not SEAT_RE.fullmatch(seat) for seat in seats):
            self.send_error_json(400, "One of the selected seats is invalid.")
        else:
            base_total = int(show["price"]) * len(seats)
            booking = {
                "id": "RH" + datetime.now(INDIA_TZ).strftime("%y%m%d") + uuid.uuid4().hex[:8].upper(),
                "movieId": movie["id"], "movieTitle": movie["title"], "showId": show_id, "show": show,
                "seats": seats, "name": name, "email": email, "phone": phone,
                "ticketTotal": base_total, "convenienceFee": 39, "total": base_total + 39,
                "paymentMethod": "UPI (demo)" if body.get("paymentMethod") == "upi-demo" else "Pay at cinema",
                "status": "Confirmed", "bookedAt": timestamp(),
            }
            connection = db_connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                sold = sold_seats(connection, show_id)
                conflict = next((seat for seat in seats if seat in sold), None)
                if conflict:
                    connection.rollback()
                    self.send_error_json(409, f"Seat {conflict} was just taken. Please choose another seat.")
                    return
                connection.execute(
                    "INSERT INTO bookings(id, show_id, email, status, booked_at, payload) VALUES(?, ?, ?, ?, ?, ?)",
                    (booking["id"], show_id, email, "Confirmed", booking["bookedAt"], json.dumps(booking, ensure_ascii=False)),
                )
                connection.executemany(
                    "INSERT INTO booking_seats(show_id, seat_id, booking_id) VALUES(?, ?, ?)",
                    [(show_id, seat, booking["id"]) for seat in seats],
                )
                connection.commit()
            except sqlite3.IntegrityError:
                connection.rollback()
                conflict = seats[0]
                self.send_error_json(409, f"Seat {conflict} was just taken. Please choose another seat.")
                return
            finally:
                connection.close()
            self.send_json(201, booking)

    def lookup_booking(self, code: str, email: str) -> None:
        with database() as connection:
            row = connection.execute("SELECT email, payload FROM bookings WHERE id = ?", (code,)).fetchone()
        if row is None:
            self.send_error_json(404, "We could not find that booking reference.")
        elif not email.strip() or email.strip().lower() != row["email"]:
            self.send_error_json(403, "Enter the email address used for this booking.")
        else:
            self.send_json(200, json.loads(row["payload"]))

    def cancel_booking(self, code: str) -> None:
        body = self.read_json()
        email = str(body.get("email", "")).strip().lower() if isinstance(body, dict) else ""
        connection = db_connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT email, status, payload FROM bookings WHERE id = ?", (code,)).fetchone()
            if row is None:
                connection.rollback()
                self.send_error_json(404, "We could not find that booking reference.")
                return
            if email != row["email"]:
                connection.rollback()
                self.send_error_json(403, "Enter the email address used for this booking.")
                return
            if row["status"] == "Cancelled":
                connection.rollback()
                self.send_error_json(409, "This booking has already been cancelled.")
                return
            booking = json.loads(row["payload"])
            booking["status"] = "Cancelled"
            booking["cancelledAt"] = timestamp()
            connection.execute("UPDATE bookings SET status = 'Cancelled', payload = ? WHERE id = ?", (json.dumps(booking, ensure_ascii=False), code))
            connection.execute("DELETE FROM booking_seats WHERE booking_id = ?", (code,))
            connection.commit()
        finally:
            connection.close()
        self.send_json(200, booking)

    def subscribe(self) -> None:
        body = self.read_json()
        email = str(body.get("email", "")).strip().lower() if isinstance(body, dict) else ""
        if not EMAIL_RE.fullmatch(email):
            self.send_error_json(400, "Enter a valid email address.")
            return
        subscribed_at = timestamp()
        with database() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO newsletter_subscribers(email, subscribed_at) VALUES(?, ?)",
                (email, subscribed_at),
            )
            already = cursor.rowcount == 0
        self.send_json(200 if already else 201, {"subscribed": True, "alreadySubscribed": already})

    def send_static(self, request_path: str) -> None:
        relative = request_path.lstrip("/") or "index.html"
        try:
            target = (PUBLIC_ROOT / relative).resolve()
            target.relative_to(PUBLIC_ROOT)
        except (OSError, ValueError):
            self.send_error_json(404, "That page or API route was not found.")
            return
        if not target.is_file():
            self.send_error_json(404, "That page or API route was not found.")
            return
        body = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in ("application/javascript", "application/json"):
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string: str, *args) -> None:
        message = format_string % args
        print(f"{self.log_date_time_string()} {self.address_string()} {message}", flush=True)


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> None:
    initialize_database()
    server = ReusableThreadingHTTPServer(("0.0.0.0", PORT), ReelhouseHandler)
    print(f"Reelhouse is ready on port {PORT}; SQLite database: {DATABASE_PATH}", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
