"""私钥/公钥格式整理：支持 PKCS#8 PEM、PKCS#1 PEM 或支付宝工具导出的无头尾单行 Base64。"""

from __future__ import annotations

import re
import textwrap

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _wrap_b64_64_cols(b64: str) -> str:
    b64 = re.sub(r"\s+", "", b64)
    return "\n".join(textwrap.wrap(b64, 64)) if b64 else b64


def ensure_pkcs1_pem_private_key(material: str) -> str:
    text = material.strip()
    if "BEGIN RSA PRIVATE KEY" in text:
        return text
    if "BEGIN PRIVATE KEY" in text:
        key = serialization.load_pem_private_key(
            text.encode("utf-8"), password=None, backend=default_backend()
        )
        pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return pem.decode("utf-8")
    # 无头尾的 Base64：先按 PKCS#8 再按 PKCS#1 包装尝试加载
    body = _wrap_b64_64_cols(text)
    pkcs8_pem = f"-----BEGIN PRIVATE KEY-----\n{body}\n-----END PRIVATE KEY-----\n"
    key = None
    try:
        key = serialization.load_pem_private_key(
            pkcs8_pem.encode("utf-8"), password=None, backend=default_backend()
        )
    except Exception:
        pkcs1_pem = f"-----BEGIN RSA PRIVATE KEY-----\n{body}\n-----END RSA PRIVATE KEY-----\n"
        key = serialization.load_pem_private_key(
            pkcs1_pem.encode("utf-8"), password=None, backend=default_backend()
        )
    assert key is not None
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode("utf-8")


def normalize_for_alipay_sdk_private_key(material: str) -> str:
    """返回 PKCS#1 PEM；SDK 内部会再去头尾参与签名。"""
    pem = ensure_pkcs1_pem_private_key(material)
    return pem.replace("\n", "").replace("-----BEGIN RSA PRIVATE KEY-----", "").replace(
        "-----END RSA PRIVATE KEY-----", ""
    )


def load_rsa_public_key_from_material(material: str) -> rsa.RSAPublicKey:
    """解析「应用公钥」或「支付宝公钥」常见格式（PEM 或无头尾 Base64）。"""
    text = material.strip().lstrip("\ufeff")
    if "BEGIN" in text:
        key = serialization.load_pem_public_key(text.encode("utf-8"), backend=default_backend())
        if not isinstance(key, rsa.RSAPublicKey):
            raise TypeError("期望 RSA 公钥")
        return key
    body = _wrap_b64_64_cols(text)
    pem = f"-----BEGIN PUBLIC KEY-----\n{body}\n-----END PUBLIC KEY-----\n"
    key = serialization.load_pem_public_key(pem.encode("utf-8"), backend=default_backend())
    if not isinstance(key, rsa.RSAPublicKey):
        raise TypeError("期望 RSA 公钥")
    return key


def verify_application_key_pair(private_key_material: str, application_public_key_material: str) -> None:
    """
    校验「应用私钥」与「应用公钥」为同一 RSA 对。
    invalid-signature 多为：开放平台上传的应用公钥与当前私钥不是一对，或 AppID 与密钥分属不同应用。
    """
    pem_priv = ensure_pkcs1_pem_private_key(private_key_material)
    private_key = serialization.load_pem_private_key(
        pem_priv.encode("utf-8"), password=None, backend=default_backend()
    )
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise TypeError("期望 RSA 应用私钥")
    pub_from_priv = private_key.public_key()
    pub_user = load_rsa_public_key_from_material(application_public_key_material)
    if pub_from_priv.public_numbers() != pub_user.public_numbers():
        raise ValueError(
            "应用私钥与 ALIPAY_APP_PUBLIC_KEY（应用公钥）不是一对，无法通过本地校验。"
            "请到开放平台该 AppID 下核对「接口加签方式」里上传的「应用公钥」是否与当前私钥匹配；"
            "ALIPAY_PUBLIC_KEY 应填「支付宝公钥」，不能与应用公钥填反。"
        )


def normalize_for_alipay_sdk_public_key(material: str) -> str:
    text = material.strip()
    if "BEGIN PUBLIC KEY" in text:
        return text.replace("\n", "").replace("-----BEGIN PUBLIC KEY-----", "").replace(
            "-----END PUBLIC KEY-----", ""
        )
    body = _wrap_b64_64_cols(text)
    pem = f"-----BEGIN PUBLIC KEY-----\n{body}\n-----END PUBLIC KEY-----\n"
    return pem.replace("\n", "").replace("-----BEGIN PUBLIC KEY-----", "").replace(
        "-----END PUBLIC KEY-----", ""
    )
