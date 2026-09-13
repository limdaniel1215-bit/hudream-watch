from dataclasses import dataclass
from os import getenv
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required configuration: {name}")
    return value


@dataclass(frozen=True)
class Config:
    telegram_token: str
    allowed_user_id: int
    allowed_chat_id: int
    interval_seconds: int
    instltn_no: str
    sclpst: str
    profile_dir: Path
    db_path: Path


def load_config() -> Config:
    try:
        interval = int(getenv("CHECK_INTERVAL_SECONDS", "60"))
        allowed_user_id = int(_required("ALLOWED_TELEGRAM_USER_ID"))
        allowed_chat_id = int(_required("ALLOWED_TELEGRAM_CHAT_ID"))
    except ValueError as exc:
        raise RuntimeError("Telegram IDs and CHECK_INTERVAL_SECONDS must be integers") from exc
    if interval < 30:
        raise RuntimeError("CHECK_INTERVAL_SECONDS must be at least 30")
    return Config(
        telegram_token=_required("TELEGRAM_BOT_TOKEN"),
        allowed_user_id=allowed_user_id,
        allowed_chat_id=allowed_chat_id,
        interval_seconds=interval,
        instltn_no=getenv("HUDREAM_INSTLTN_NO", "156"),
        sclpst=getenv("HUDREAM_SCLPST", "1"),
        profile_dir=Path(getenv("HUDREAM_PROFILE_DIR", "profile")),
        db_path=Path(getenv("HUDREAM_DB_PATH", "data/watches.db")),
    )
