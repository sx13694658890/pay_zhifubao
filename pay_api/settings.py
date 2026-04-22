from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pay_api.key_util import verify_application_key_pair

_pkg_dir = Path(__file__).resolve().parent
_project_root = _pkg_dir.parent
# 不依赖 cwd：用绝对路径注入 os.environ，pydantic-settings 才能稳定读到变量
load_dotenv(_project_root / ".env", override=False)
load_dotenv(_pkg_dir / ".env", override=True)

_env_candidates = [_project_root / ".env", _pkg_dir / ".env"]
_env_files = tuple(str(p) for p in _env_candidates if p.is_file())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files if _env_files else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    alipay_app_id: str = Field(validation_alias="ALIPAY_APP_ID")
    alipay_app_private_key: str | None = Field(default=None, validation_alias="ALIPAY_APP_PRIVATE_KEY")
    alipay_app_private_key_file: str | None = Field(
        default=None, validation_alias="ALIPAY_APP_PRIVATE_KEY_FILE"
    )
    #: 开放平台「查看支付宝公钥」，用于 SDK 验签支付宝响应；勿填「应用公钥」
    alipay_public_key: str = Field(validation_alias="ALIPAY_PUBLIC_KEY")
    #: 可选：开放平台「应用公钥」原文；若填写，启动时校验与 ALIPAY_APP_PRIVATE_KEY 为同一对，便于提前发现 invalid-signature
    alipay_app_public_key: str | None = Field(default=None, validation_alias="ALIPAY_APP_PUBLIC_KEY")

    alipay_sandbox: bool = Field(default=True, validation_alias="ALIPAY_SANDBOX")
    alipay_server_url: str | None = Field(default=None, validation_alias="ALIPAY_SERVER_URL")

    alipay_notify_url: str | None = Field(default=None, validation_alias="ALIPAY_NOTIFY_URL")
    alipay_return_url: str | None = Field(default=None, validation_alias="ALIPAY_RETURN_URL")
    #: 公网 API 根地址（如 ngrok https://xxx），用于自动拼接异步通知地址：{PUBLIC_API_BASE_URL}/api/pay/alipay/notify
    public_api_base_url: str | None = Field(default=None, validation_alias="PUBLIC_API_BASE_URL")

    cors_origins: str = Field(
        default="http://localhost:5173",
        validation_alias="CORS_ORIGINS",
        description="逗号分隔的前端源，开发联调用",
    )
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")

    #: 例 postgresql://user:pass@127.0.0.1:5432/pay_db
    database_url: str = Field(validation_alias="DATABASE_URL")

    @field_validator("alipay_app_private_key", "alipay_app_private_key_file", "alipay_app_public_key", mode="before")
    @classmethod
    def strip_optional(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("public_api_base_url", mode="before")
    @classmethod
    def strip_public_base(cls, v: object) -> object:
        if not isinstance(v, str):
            return v
        s = v.lstrip("\ufeff").strip()
        return None if not s else s

    @field_validator(
        "alipay_app_id",
        "alipay_public_key",
        "alipay_app_private_key",
        "alipay_app_public_key",
        "database_url",
        mode="before",
    )
    @classmethod
    def strip_bom_and_edges(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lstrip("\ufeff").strip()
        return v

    @model_validator(mode="after")
    def require_private_key_and_optional_pair_check(self) -> Settings:
        if not (self.alipay_app_private_key or self.alipay_app_private_key_file):
            raise ValueError("请在 .env 中配置 ALIPAY_APP_PRIVATE_KEY 或 ALIPAY_APP_PRIVATE_KEY_FILE")
        if self.alipay_app_public_key:
            verify_application_key_pair(
                self.resolved_app_private_key(),
                self.alipay_app_public_key,
            )
        return self

    def resolved_app_private_key(self) -> str:
        if self.alipay_app_private_key:
            return self.alipay_app_private_key.strip().lstrip("\ufeff")
        path = Path(self.alipay_app_private_key_file or "")
        if not path.is_file():
            raise FileNotFoundError(f"找不到私钥文件: {path}")
        return path.read_text(encoding="utf-8").strip().lstrip("\ufeff")

    def effective_server_url(self) -> str:
        """沙箱网关需与开放平台应用环境一致；新沙箱默认使用 dl 域名。"""
        if self.alipay_server_url:
            return self.alipay_server_url.strip().rstrip("/")
        if self.alipay_sandbox:
            # 与旧版 openapi.alipaydev.com 并存；新沙箱应用若报 invalid-app-id 可改用此默认
            return "https://openapi-sandbox.dl.alipaydev.com/gateway.do"
        return "https://openapi.alipay.com/gateway.do"

    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as e:
        tried = "\n".join(f"  - {p}" for p in _env_candidates)
        msg = (
            "未读取到 ALIPAY_APP_ID / ALIPAY_PUBLIC_KEY 等配置。\n"
            "请在以下路径之一创建 .env（推荐项目根目录），并填写支付宝参数：\n"
            f"{tried}\n"
            "若 .env 已在上述路径，请检查 ALIPAY_APP_ID、ALIPAY_PUBLIC_KEY、DATABASE_URL 等是否已填写。"
        )
        raise RuntimeError(msg) from e
