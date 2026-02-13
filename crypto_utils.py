"""加密工具模块 - 提供密码加密和解密功能"""

import base64
import hashlib
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class PasswordCrypto:
    """密码加密工具类"""

    _instance = None
    _key = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_or_create_key(self) -> bytes:
        """获取或创建加密密钥"""
        if self._key is not None:
            return self._key

        # 使用机器特定信息生成密钥
        import platform
        import os

        # 组合机器特定信息
        machine_info = f"{platform.node()}-{platform.machine()}-{platform.processor()}"

        # 生成盐值（固定盐值，确保同一台机器上能解密）
        salt = hashlib.sha256(machine_info.encode()).digest()[:16]

        # 使用 PBKDF2 派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )

        key = base64.urlsafe_b64encode(kdf.derive(machine_info.encode()))
        self._key = key
        return key

    def encrypt(self, plaintext: str) -> str:
        """加密明文密码

        Args:
            plaintext: 明文密码

        Returns:
            str: 加密后的密码（base64编码）
        """
        if not plaintext:
            return ""

        try:
            key = self._get_or_create_key()
            f = Fernet(key)
            encrypted = f.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception:
            # 加密失败返回空字符串
            return ""

    def decrypt(self, ciphertext: str) -> str:
        """解密密码

        Args:
            ciphertext: 加密后的密码（base64编码）

        Returns:
            str: 明文密码
        """
        if not ciphertext:
            return ""

        try:
            key = self._get_or_create_key()
            f = Fernet(key)
            # 先解码 base64
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = f.decrypt(encrypted)
            return decrypted.decode()
        except Exception:
            # 解密失败，可能是明文存储的旧密码
            return ciphertext

    def is_encrypted(self, text: str) -> bool:
        """检查文本是否已加密

        Args:
            text: 待检查的文本

        Returns:
            bool: 是否已加密
        """
        if not text:
            return False

        try:
            # 尝试解码 base64
            decoded = base64.urlsafe_b64decode(text.encode())
            # 检查是否包含 Fernet 的标识
            return decoded.startswith(b'gAAAAA')
        except Exception:
            return False


# 全局加密实例
_crypto = PasswordCrypto()


def encrypt_password(plaintext: str) -> str:
    """加密密码（便捷函数）"""
    return _crypto.encrypt(plaintext)


def decrypt_password(ciphertext: str) -> str:
    """解密密码（便捷函数）"""
    return _crypto.decrypt(ciphertext)


def is_password_encrypted(text: str) -> bool:
    """检查密码是否已加密（便捷函数）"""
    return _crypto.is_encrypted(text)
