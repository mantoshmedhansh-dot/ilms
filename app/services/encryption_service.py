"""
Encryption Service for Secure Credential Storage

Provides secure encryption/decryption for sensitive data like:
- GST E-Invoice portal credentials
- E-Way Bill portal passwords
- API keys and secrets
- Bank account credentials

Uses Fernet symmetric encryption (AES-128-CBC) with key derivation.
For production, use a Key Management Service (AWS KMS, HashiCorp Vault, etc.)
"""

import base64
import os
import hashlib
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


class EncryptionError(Exception):
    """Custom exception for encryption errors."""
    pass


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data.

    Uses Fernet (AES-128-CBC) with PBKDF2 key derivation.
    The encryption key is derived from a master secret and salt.

    For production use:
    - Store ENCRYPTION_SECRET in environment variable
    - Use AWS KMS or HashiCorp Vault for key management
    - Rotate keys periodically
    """

    # Prefix for encrypted values to identify them
    ENCRYPTED_PREFIX = "ENC:"

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize encryption service.

        Args:
            secret_key: Master secret for key derivation.
                       If not provided, uses ENCRYPTION_SECRET env var.
        """
        self._secret = secret_key or os.getenv("ENCRYPTION_SECRET")

        if not self._secret:
            # Generate a random secret for development only
            # In production, this should always be set via environment
            import warnings
            warnings.warn(
                "ENCRYPTION_SECRET not set. Using random key - data will not persist across restarts!",
                RuntimeWarning
            )
            self._secret = Fernet.generate_key().decode()

        # Default salt (should be unique per installation)
        self._salt = os.getenv("ENCRYPTION_SALT", "ilms_erp_salt_2024").encode()

        # Initialize cipher
        self._fernet = self._create_cipher()

    def _create_cipher(self) -> Fernet:
        """Create Fernet cipher from derived key."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=100000,
            backend=default_backend()
        )

        key = base64.urlsafe_b64encode(
            kdf.derive(self._secret.encode())
        )

        return Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Encrypted string with prefix (ENC:base64_data)
        """
        if not plaintext:
            return plaintext

        # Already encrypted?
        if plaintext.startswith(self.ENCRYPTED_PREFIX):
            return plaintext

        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            return f"{self.ENCRYPTED_PREFIX}{encrypted.decode()}"
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {str(e)}")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            ciphertext: The encrypted string (with or without ENC: prefix)

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ciphertext

        # Remove prefix if present
        if ciphertext.startswith(self.ENCRYPTED_PREFIX):
            ciphertext = ciphertext[len(self.ENCRYPTED_PREFIX):]
        else:
            # Not encrypted, return as-is
            return ciphertext

        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken:
            raise EncryptionError("Decryption failed: Invalid token or key")
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {str(e)}")

    def is_encrypted(self, value: str) -> bool:
        """Check if a value is encrypted."""
        return value and value.startswith(self.ENCRYPTED_PREFIX)

    def rotate_encryption(self, old_value: str, new_secret: str) -> str:
        """
        Re-encrypt a value with a new secret key.

        Used during key rotation.

        Args:
            old_value: The currently encrypted value
            new_secret: The new secret key to encrypt with

        Returns:
            Value encrypted with new key
        """
        # Decrypt with current key
        plaintext = self.decrypt(old_value)

        # Create new cipher with new secret
        new_service = EncryptionService(secret_key=new_secret)

        # Encrypt with new key
        return new_service.encrypt(plaintext)

    @staticmethod
    def hash_for_comparison(value: str) -> str:
        """
        Create a hash of a value for comparison without storing plaintext.

        Useful for checking if passwords match without decrypting.
        """
        return hashlib.sha256(value.encode()).hexdigest()


class CredentialManager:
    """
    High-level manager for storing and retrieving encrypted credentials.

    Provides type-specific methods for common credential types.
    """

    def __init__(self, encryption_service: Optional[EncryptionService] = None):
        self.encryption = encryption_service or EncryptionService()

    def encrypt_password(self, password: str) -> str:
        """Encrypt a password for storage."""
        return self.encryption.encrypt(password)

    def decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt a stored password."""
        return self.encryption.decrypt(encrypted_password)

    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt an API key for storage."""
        return self.encryption.encrypt(api_key)

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt a stored API key."""
        return self.encryption.decrypt(encrypted_key)

    def encrypt_credentials(self, username: str, password: str) -> dict:
        """
        Encrypt a username/password pair.

        Returns dict with encrypted values.
        """
        return {
            "username": username,  # Usually username doesn't need encryption
            "password": self.encryption.encrypt(password)
        }

    def decrypt_credentials(self, credentials: dict) -> dict:
        """
        Decrypt a credentials dict.

        Returns dict with decrypted values.
        """
        return {
            "username": credentials.get("username", ""),
            "password": self.encryption.decrypt(credentials.get("password", ""))
        }


# Singleton instance for global use
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get or create the global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_value(plaintext: str) -> str:
    """Convenience function to encrypt a value."""
    return get_encryption_service().encrypt(plaintext)


def decrypt_value(ciphertext: str) -> str:
    """Convenience function to decrypt a value."""
    return get_encryption_service().decrypt(ciphertext)
