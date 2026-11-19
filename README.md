# Reelhouse

Reelhouse is a responsive movie-ticket booking website with a Python backend and a SQLite SQL database. The backend uses Python's standard library; it does not need application packages.

## Run locally

Install Python 3.9 or newer, then open PowerShell in this folder and run:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\start.ps1
```

Open [http://localhost:5055](http://localhost:5055). Keep the PowerShell window open while using the site. Press **Ctrl+C** there to stop it. To use another port, run:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\start.ps1 -Port 5056
```

The local database is `data/reelhouse.sqlite3`. The backend imports existing `bookings.json` and `newsletter.json` records on startup.

## Private bookings table

Set `REELHOUSE_ADMIN_PASSWORD` in the service environment to a strong, private password. Then open `/admin` on the deployed site and sign in with username `admin` and that password. The private table reads from SQLite and shows booking references, movie/show details, seats, amount, and status. It does not display customer email or phone. Without the environment variable, the admin page stays disabled.

## Deploy on Railway

1. Push this project to a GitHub repository and create a Railway service from that repository. Railway will detect the root `Dockerfile` and build the app.
2. Attach a Railway volume to the app service with mount path `/data` so SQLite records survive redeployments.
3. Set the service healthcheck path to `/api/health`, then generate a public domain for the service.

Railway supplies the app's `PORT` automatically. Its Dockerfile detection and persistent volume behavior are documented [here](https://docs.railway.com/builds/dockerfiles) and [here](https://docs.railway.com/volumes).

## Features

- Search and filter the movie catalogue, save favourites, and switch between six Indian cities.
- Pick a date, cinema, and showtime, then choose seats from a live availability map.
- Reserve up to eight seats. A SQLite transaction prevents concurrent bookings from claiming the same seat.
- Look up tickets by booking reference and email, print them, or cancel reservations.
- Join the email list; subscriptions are stored in SQLite.
- Responsive layouts for desktop, tablet, and mobile screens.

UPI is a demo selection; no real payment is taken. Movies, cinemas, and showtimes are sample data. Posters and web fonts load from Unsplash and Google Fonts when internet access is available.

## Files

- `server.py` — static-file server and movie, showtime, seat, booking, and newsletter API backed by SQLite.
- `public/` — website markup, styling, and browser interactions.
- `data/` — local SQLite database created when the server starts.
