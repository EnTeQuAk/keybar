import base64
import ssl

from django.conf import settings
from django.utils.encoding import force_bytes, force_text
from cryptography.fernet import Fernet

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


# Verify we can use all feature we require.
assert ssl.HAS_ECDH
assert ssl.HAS_SNI


def derive_encryption_key(salt, password):
    """Get the real encryption key.

    Don't use the password directly but derive a encryption key
    dynamically based on the password and a stored key.
    """
    backend = default_backend()

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=force_bytes(salt),
        iterations=settings.KEYBAR_KDF_ITERATIONS,
        backend=backend
    )

    return kdf.derive(force_bytes(password))


def verify_encryption_key(salt, password, key):
    backend = default_backend()

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=force_bytes(salt),
        iterations=settings.KEYBAR_KDF_ITERATIONS,
        backend=backend
    )

    kdf.verify(force_bytes(password), key)

    return key


def encrypt(text, password, salt):
    fernet = Fernet(base64.urlsafe_b64encode(derive_encryption_key(salt, password)))
    return fernet.encrypt(force_bytes(text))


def decrypt(text, password, salt):
    fernet = Fernet(base64.urlsafe_b64encode(derive_encryption_key(salt, password)))
    return force_text(fernet.decrypt(force_bytes(text)))


def get_server_context(verify=True):
    """Our TLS configuration for the server"""
    server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

    server_ctx.set_ecdh_curve('prime256v1')
    server_ctx.verify_mode = ssl.CERT_OPTIONAL if not verify else ssl.CERT_REQUIRED

    # This list is based on the official supported ciphers by CloudFlare
    # (cloudflare/sslconfig on GitHub) but is again just a tiny little bit
    # more restricted as we force best security available.
    server_ctx.set_ciphers('EECDH+AES128:RSA+AES128:EECDH+AES256:RSA+AES256')

    # Mitigate CRIME
    server_ctx.options |= ssl.OP_NO_COMPRESSION

    # Prevents re-use of the same ECDH key for distinct SSL sessions.
    # This improves forward secrecy but requires more computational resources.
    server_ctx.options |= ssl.OP_SINGLE_ECDH_USE

    # Use the server’s cipher ordering preference, rather than the client’s.
    server_ctx.options |= ssl.OP_CIPHER_SERVER_PREFERENCE

    # Load the certificates
    server_ctx.load_cert_chain(
        settings.KEYBAR_SERVER_CERTIFICATE,
        settings.KEYBAR_SERVER_KEY
    )

    server_ctx.load_verify_locations(settings.KEYBAR_CA_BUNDLE)

    return server_ctx


def get_client_context(verify=True):
    """Matching TLS configuration for the client."""
    client_ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

    client_ctx.verify_mode = ssl.CERT_OPTIONAL if not verify else ssl.CERT_REQUIRED

    # Require checking the hostname
    client_ctx.check_hostname = True

    # Same as the server.
    client_ctx.set_ciphers('EECDH+AES128:RSA+AES128:EECDH+AES256:RSA+AES256')

    # Mitigate CRIME
    client_ctx.options |= ssl.OP_NO_COMPRESSION

    # Load the certificates
    client_ctx.load_cert_chain(
        settings.KEYBAR_CLIENT_CERTIFICATE,
        settings.KEYBAR_CLIENT_KEY
    )

    client_ctx.load_verify_locations(settings.KEYBAR_CA_BUNDLE)

    return client_ctx
