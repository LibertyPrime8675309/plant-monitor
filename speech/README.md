# Speech service (search by voice)

The container `plant-speech` turns a few seconds of what you say into words for **Search by voice**. It runs
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) (OpenAI's Whisper, converted for CTranslate2, MIT licence) on the
processor, on this computer. Nothing you say goes to Google, Microsoft or anyone else, and recordings are never saved.

## How it fits together

1. A **Search by voice** button records from the microphone in the browser (MediaRecorder: WebM/Opus in Chrome, Edge, Brave and
   Firefox; MP4/AAC in Safari). It stops by itself after about 1.5 seconds of quiet, after 15 seconds, or when pressed again.
2. The recording goes to the app: `POST /api/voice` (field `audio`, at most about 2 MB). The app adds a short prompt with the page
   names, your plant names and how codes look (P-036, F-002), so Whisper spells them the way the record does.
3. The app passes both to this service on Docker's private network: `POST /transcribe`. The service reads the recording in memory
   with PyAV, transcribes it (English, beam 2, silence trimmed) and answers `{"text": ...}`. The recording is then dropped.
4. `GET /status` says `ready`, `setting up` (with how many MB of the model have downloaded) or `error`; `off` when turned off.
   The app shows it on the Identify page and in Display settings, and says it in plain words when a button is pressed too early.

The service has no ports on this computer, the home network or Tailscale. It cannot see the plant records.

## First start

The first start downloads the model into `data/speech`:

| `SPEECH_MODEL` | Download | On an 8-core processor | Notes |
|---|---|---|---|
| `tiny.en` | about 75 MB | well under a second | quickest, most mistakes |
| `base.en` | about 145 MB | under a second | |
| `small.en` (the usual) | about 465 MB | about a second for a short phrase | a good balance |
| `medium.en` | about 1.5 GB | a few seconds | fewest mistakes |

To choose another, put `PLANTDB_SPEECH_MODEL=base.en` (for example) in the `.env` file next to `docker-compose.yml` and run the
updater. `PLANTDB_SPEECH_THREADS` limits the processor cores it uses (empty: all of them). `PLANTDB_SPEECH=0` turns it off.

Deleting `data/speech` is safe: the model downloads again on the next start.

## Building

`docker compose up -d --build` (the updater runs it) builds `plant-database-speech:<version>` from `speech/Dockerfile`: Python 3.12
slim with the packages in `speech/requirements.txt` (about 200 MB). PyAV is held at 18.1: faster-whisper 1.2.1 passes an option
PyAV 19 removed, and decoding fails with it.

## Tests

`dev/test/mock_speech.py` is a stand-in the mock server starts on port 8093: a test tells it what the next recording "says".
`dev/test/voice_check.py` drives real recordings from a stand-in microphone; `dev/test/unit/test_voice.py` covers `/api/voice`.
