"""Unit tests for the pure functions (no server, no browser): they run in seconds.  python3 -m pytest dev/test/unit -q
Importing server.py opens a database, so these use a throwaway data folder and turn the background jobs off."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp(prefix='plantdb-unit-')
os.environ.update(DATA_DIR=TMP, PLANTDB_WEATHER='0', PLANTDB_SHOPS='0', PLANTDB_OSM='0', PLANTDB_VISION_URL='http://127.0.0.1:9', PLANTDB_ASPCA_MIN='0', PLANTDB_UPDATES='0', PLANTDB_PUSH='0')
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'app'))
