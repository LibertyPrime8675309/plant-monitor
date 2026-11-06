# The mirror (plant record 1.37.0)

A read-only copy of the plant record on a second machine (the spare hardware, or your girlfriend's PC), so the plants, the
Today page, the cold-night checklist and everything else can still be looked at when the main PC is asleep, off or broken.
It keeps itself up to date from the backups: the backup receiver (1.33.0) runs on the same machine, and every 5 minutes the
mirror takes the newest backup it has received and shows that. Changes are turned off on the mirror; every page says so and
links to the main app.

What the mirror shows is as fresh as the last backup that reached it. Automatic backups are of the database only, so photos
on the mirror come from the last backup made **with photos** (Backups page, or set the schedule to include photos once a week).

## What you need on the second machine

- Docker (Docker Desktop on Windows or a Mac; Docker Engine on Linux) and Tailscale, signed in to the same tailnet as the main PC.
- This `mirror` folder from the release zip, with the folders next to it (`app`, `receiver`, `tools`): unzip the whole release zip on the second machine too, for example to `C:\Plants\plant-database`, and work in its `mirror` subfolder. Update it the same way as the main PC (the updater keeps `mirror/data`, `mirror/backups`, `mirror/received` and `mirror/tailscale`).

## Setting it up

1. In the `mirror` folder make a file named `.env` with three lines:
   - `BACKUP_TOKEN=` followed by a long random text (30 letters and digits or more). The same text goes into the main app's Backups page.
   - `PLANTDB_MIRROR_MAIN=` followed by the main app's address (`https://plants.<your tailnet>.ts.net`), so the note on every page links to it.
   - `TS_AUTHKEY=` followed by a Tailscale auth key (optional; without one the Tailscale container prints a sign-in link in its log).
2. Start it:

Windows (cmd.exe):
```
cd /d C:\Plants\plant-database\mirror
docker compose up -d --build
```

Windows (PowerShell):
```
cd C:\Plants\plant-database\mirror
docker compose up -d --build
```

bash:
```
cd ~/plant-database/mirror
docker compose up -d --build
```

3. On the main PC, open **Backups → Second copy** and enter the second machine's Tailscale address with port 8089 (`http://100.x.y.z:8089`) and the token, then press **Copy the newest backup now**. Within 5 minutes the mirror shows it.
4. Open the mirror at `https://plants-mirror.<your tailnet>.ts.net` (the Tailscale container serves it with HTTPS, like the main app). On the second machine itself it is also at `http://localhost:8080`.

## How it behaves

- Everyone who opens it can only look: the Add, Edit and care buttons are hidden, and any change is refused with "This is the read-only mirror".
- A note at the top of every page says which backup it shows and links to the main app.
- The Sensors page and the weather history are whatever the backup carried; the mirror fetches no weather and sends no notifications.
- Settings → Health of the app on the mirror shows the mirror's own state; Jobs lists each "Mirror update".
- To stop it: `docker compose down` in the `mirror` folder (cmd.exe, PowerShell and bash alike).

## If something is wrong

- The note says "waiting for its first backup": nothing has reached the receiver yet. Check the token and the address on the main PC's Backups page, and that `http://100.x.y.z:8089/health` answers from the main PC.
- The note shows an error in brackets: the newest backup could not be restored (a damaged zip, or one from a newer version than the mirror runs). Update the mirror's folder to the same version as the main PC.
