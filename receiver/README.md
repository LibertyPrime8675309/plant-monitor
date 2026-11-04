# Backup receiver (plant record 1.33.0)

A tiny server for a second computer, so each backup of the plant record also lands there. It keeps the newest twenty.

## On the second computer

1. Install Docker Desktop and Tailscale (signed in to the same tailnet as the plant record's PC).
2. Copy this `receiver` folder somewhere, for example `C:\PlantBackups\receiver`.
3. In that folder make a file named `.env` with one line: `BACKUP_TOKEN=` followed by a long random text (30 letters and digits or more). Keep it; the same text goes into the plant record.
4. Start it:

Windows (cmd.exe):
```
cd /d C:\PlantBackups\receiver
docker compose up -d
```

Windows (PowerShell):
```
cd C:\PlantBackups\receiver
docker compose up -d
```

bash:
```
cd ~/PlantBackups/receiver
docker compose up -d
```

5. Find the computer's Tailscale address (the Tailscale app shows it, something like `100.101.102.103`). Open `http://that-address:8089/health` from the plant record's PC: it should say `{"ok": true, ...}`.

Backups arrive in `received\` next to the compose file.

## On the plant record

Settings, Backups, **Second copy**: type the address (`http://100.101.102.103:8089`) and the token, press **Save**, then **Copy the newest backup now** to try it.

## Without Docker

`python3 receiver.py` with `BACKUP_TOKEN` set in the environment does the same thing (Python 3.8 or newer, nothing to install).
