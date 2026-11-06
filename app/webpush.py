"""1.33.0: Web Push with the cryptography library only (no pywebpush, which needs a package that does not build everywhere).
VAPID (RFC 8292): a key pair the app makes once; each request carries a short signed token so the push service knows it is us.
Payload encryption (RFC 8291, aes128gcm): the browser gave us its public key and a secret when it subscribed; we agree a key with
ECDH, derive the content key and nonce with HKDF, and send the encrypted message. No Flask here, so it is easy to test."""
import base64, json, os, struct, time, urllib.error, urllib.request
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

def b64u(b): return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
def b64d(s): return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))

def make_vapid():
    """A new key pair: (private key as base64url DER PKCS8, public key as the 65-byte uncompressed point, base64url)."""
    k = ec.generate_private_key(ec.SECP256R1())
    priv = k.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    pub = k.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return b64u(priv), b64u(pub)

def vapid_header(priv_b64, pub_b64, endpoint, subject, hours=12):
    """The Authorization header for one push service (its origin), signed with our private key."""
    from urllib.parse import urlsplit
    k = serialization.load_der_private_key(b64d(priv_b64), None)
    u = urlsplit(endpoint); aud = f'{u.scheme}://{u.netloc}'
    head = b64u(json.dumps({'typ': 'JWT', 'alg': 'ES256'}, separators=(',', ':')).encode())
    body = b64u(json.dumps({'aud': aud, 'exp': int(time.time()) + hours * 3600, 'sub': subject}, separators=(',', ':')).encode())
    sig = k.sign(f'{head}.{body}'.encode(), ec.ECDSA(hashes.SHA256()))
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    r, s = decode_dss_signature(sig)
    return f'vapid t={head}.{body}.{b64u(r.to_bytes(32, "big") + s.to_bytes(32, "big"))}, k={pub_b64}'

def encrypt(p256dh_b64, auth_b64, payload):
    """RFC 8291: the message, encrypted for one subscription, as the aes128gcm body (header + ciphertext)."""
    ua_pub = b64d(p256dh_b64); auth = b64d(auth_b64)
    ua_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_pub)
    ours = ec.generate_private_key(ec.SECP256R1())
    as_pub = ours.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    shared = ours.exchange(ec.ECDH(), ua_key)
    ikm = HKDF(hashes.SHA256(), 32, auth, b'WebPush: info\x00' + ua_pub + as_pub).derive(shared)
    salt = os.urandom(16)
    cek = HKDF(hashes.SHA256(), 16, salt, b'Content-Encoding: aes128gcm\x00').derive(ikm)
    nonce = HKDF(hashes.SHA256(), 12, salt, b'Content-Encoding: nonce\x00').derive(ikm)
    data = payload if isinstance(payload, bytes) else payload.encode()
    body = AESGCM(cek).encrypt(nonce, data + b'\x02', None)        # one record; 0x02 marks the last record
    header = salt + struct.pack('>I', 4096) + bytes([len(as_pub)]) + as_pub
    return header + body

def send(sub, payload, priv_b64, pub_b64, subject='mailto:plants@example.invalid', ttl=86400, urgency='normal', opener=None):
    """Sends one message to one subscription {endpoint, p256dh, auth}. Returns (status, text). 404 and 410 mean the subscription
    is gone and should be dropped; 201 means it was accepted."""
    body = encrypt(sub['p256dh'], sub['auth'], json.dumps(payload) if not isinstance(payload, (str, bytes)) else payload)
    req = urllib.request.Request(sub['endpoint'], data=body, method='POST', headers={
        'Content-Encoding': 'aes128gcm', 'Content-Type': 'application/octet-stream', 'TTL': str(ttl), 'Urgency': urgency,
        'Authorization': vapid_header(priv_b64, pub_b64, sub['endpoint'], subject)})
    try:
        with (opener or urllib.request.urlopen)(req, timeout=20) as r: return r.status, ''
    except urllib.error.HTTPError as e: return e.code, (e.read(500).decode('utf-8', 'replace') if e.fp else '')
