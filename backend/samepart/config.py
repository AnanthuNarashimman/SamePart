"""Runtime configuration. Everything is environment-driven so the same build runs against
a hosted model, a local open-weight model, or a deterministic stub."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    db_url: str = os.getenv("SAMEPART_DB_URL", "sqlite:///samepart.db")
    dictionary_dir: Path = REPO_ROOT / os.getenv("SAMEPART_DICTIONARY_DIR", "dictionaries")
    # Families added at runtime are written here and loaded on every boot after the built-in
    # ones. Under SAMEPART_DATA_DIR so that on a host it sits on the persistent volume.
    families_dir: Path = Path(
        os.getenv("SAMEPART_FAMILIES_DIR")
        or (Path(os.environ["SAMEPART_DATA_DIR"]) / "families" if os.getenv("SAMEPART_DATA_DIR")
            else REPO_ROOT / "data" / "generated" / "families"))

    azure_endpoint: str | None = os.getenv("AZURE_OPENAI_ENDPOINT") or None
    azure_api_key: str | None = os.getenv("AZURE_OPENAI_API_KEY") or None
    azure_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    azure_chat_deployment: str | None = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or None
    azure_embedding_deployment: str | None = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT") or None

    @property
    def has_azure(self) -> bool:
        return bool(
            self.azure_endpoint
            and self.azure_api_key
            and self.azure_chat_deployment
        )


settings = Settings()
