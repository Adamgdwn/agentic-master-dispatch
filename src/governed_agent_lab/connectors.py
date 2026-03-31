from __future__ import annotations

import os
import sqlite3
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ConnectorSpec:
    key: str
    label: str
    env_vars: tuple[str, ...]
    tool_script: str
    scope: str
    notes: str


CONNECTORS = (
    ConnectorSpec(
        key="perplexity",
        label="Perplexity",
        env_vars=("PERPLEXITY_API_KEY",),
        tool_script="tools/perplexity_search.py",
        scope="External research",
        notes="Use API keys, not browser passwords.",
    ),
    ConnectorSpec(
        key="openai",
        label="ChatGPT / OpenAI API",
        env_vars=("OPENAI_API_KEY",),
        tool_script="tools/openai_responses.py",
        scope="Model-backed analysis",
        notes="Prefer API access over account sharing.",
    ),
    ConnectorSpec(
        key="genspark_bridge",
        label="Genspark Bridge",
        env_vars=("GENSPARK_BRIDGE_URL", "GENSPARK_BRIDGE_TOKEN"),
        tool_script="tools/http_service_bridge.py",
        scope="Local bridge for authenticated tools",
        notes="Wrap browser-only tools behind a narrow local bridge.",
    ),
    ConnectorSpec(
        key="sqlite_readonly",
        label="SQLite Read-Only",
        env_vars=("SQLITE_DB_PATH",),
        tool_script="tools/sqlite_readonly.py",
        scope="Local database inspection",
        notes="Use dedicated read-only datasets where possible.",
    ),
)


def load_tool_profiles(config_path: Path) -> dict:
    if not config_path.exists():
        return {"connector": []}
    return tomllib.loads(config_path.read_text(encoding="utf-8"))


def load_local_env(env_path: Path) -> dict[str, str]:
    loaded: dict[str, str] = {}
    if not env_path.exists():
        return loaded

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value
            loaded[key] = value
    return loaded


def connector_statuses(config_path: Path) -> list[dict[str, object]]:
    profiles = load_tool_profiles(config_path)
    configured_profiles = {item["key"]: item for item in profiles.get("connector", [])}
    statuses = []
    for connector in CONNECTORS:
        env_ready = all(os.environ.get(name) for name in connector.env_vars)
        statuses.append(
            {
                "key": connector.key,
                "label": connector.label,
                "env_vars": list(connector.env_vars),
                "tool_script": connector.tool_script,
                "scope": connector.scope,
                "notes": connector.notes,
                "configured": env_ready,
                "profile_enabled": bool(configured_profiles.get(connector.key, {}).get("enabled", False)),
            }
        )
    return statuses


def test_connector(connector_key: str) -> dict[str, object]:
    if connector_key == "openai":
        return _test_openai()
    if connector_key == "perplexity":
        return _test_perplexity()
    if connector_key == "genspark_bridge":
        return _test_bridge()
    if connector_key == "sqlite_readonly":
        return _test_sqlite()
    raise ValueError(f"Unknown connector: {connector_key}")


def _test_openai() -> dict[str, object]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"ok": False, "message": "OPENAI_API_KEY is not set"}
    request = Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    return _url_test(request, "OpenAI API reachable")


def _test_perplexity() -> dict[str, object]:
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        return {"ok": False, "message": "PERPLEXITY_API_KEY is not set"}
    request = Request(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=b'{"model":"sonar-pro","messages":[{"role":"user","content":"ping"}]}',
        method="POST",
    )
    return _url_test(request, "Perplexity API reachable")


def _test_bridge() -> dict[str, object]:
    bridge_url = os.environ.get("GENSPARK_BRIDGE_URL")
    bridge_token = os.environ.get("GENSPARK_BRIDGE_TOKEN")
    if not bridge_url or not bridge_token:
        return {"ok": False, "message": "GENSPARK_BRIDGE_URL and GENSPARK_BRIDGE_TOKEN must be set"}
    request = Request(
        bridge_url.rstrip("/") + "/health",
        headers={"Authorization": f"Bearer {bridge_token}"},
        method="GET",
    )
    return _url_test(request, "Bridge reachable")


def _test_sqlite() -> dict[str, object]:
    db_path = os.environ.get("SQLITE_DB_PATH")
    if not db_path:
        return {"ok": False, "message": "SQLITE_DB_PATH is not set"}
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return {"ok": False, "message": f"SQLite connection failed: {exc}"}
    return {"ok": True, "message": "SQLite database reachable in read-only mode"}


def _url_test(request: Request, success_message: str) -> dict[str, object]:
    try:
        with urlopen(request, timeout=20) as response:
            return {
                "ok": True,
                "message": success_message,
                "status": getattr(response, "status", 200),
            }
    except URLError as exc:
        return {"ok": False, "message": str(exc)}
