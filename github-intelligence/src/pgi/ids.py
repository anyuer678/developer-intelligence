"""全局实体 ID 契约（04 号计划书 DS-0 / ADR-002）。

格式：{connector}:{type}:{native_id}
示例：github:repo:anyuer678/lumen · github:commit:owner/name@sha
规则：connector/type 小写受限字符集；native_id 保留原始大小写，禁止含 ':'
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

_PATTERN = re.compile(r"^([a-z0-9_-]+):([a-z_]+):(.+)$")


class EntityIdError(ValueError):
    """非法实体 ID。"""


def build(connector: str, entity_type: str, native_id: str) -> str:
    if not re.fullmatch(r"[a-z0-9_-]+", connector):
        raise EntityIdError(f"connector 非法: {connector!r}")
    if not re.fullmatch(r"[a-z_]+", entity_type):
        raise EntityIdError(f"entity_type 非法: {entity_type!r}")
    if not native_id or ":" in native_id:
        raise EntityIdError(f"native_id 为空或含冒号: {native_id!r}")
    return f"{connector}:{entity_type}:{native_id}"


def parse(entity_id: str) -> tuple[str, str, str]:
    m = _PATTERN.match(entity_id)
    if not m:
        raise EntityIdError(f"实体 ID 格式非法: {entity_id!r}")
    return m.group(1), m.group(2), m.group(3)


def normalize_content(text: str) -> str:
    """content_hash 前的归一化：NFC + CRLF→LF + 去行尾空白。"""
    text = unicodedata.normalize("NFC", text)
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    return "\n".join(lines)


def content_hash(data: str | bytes) -> str:
    if isinstance(data, str):
        data = normalize_content(data).encode("utf-8")
    return hashlib.sha256(data).hexdigest()
