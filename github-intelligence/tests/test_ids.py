"""TASK-P0-02 验收：实体 ID 契约。"""

from __future__ import annotations

import pytest

from pgi.ids import EntityIdError, build, content_hash, normalize_content, parse


def test_build_and_parse_roundtrip():
    eid = build("github", "repo", "anyuer678/lumen")
    assert eid == "github:repo:anyuer678/lumen"
    assert parse(eid) == ("github", "repo", "anyuer678/lumen")


def test_native_id_keeps_case_and_symbols():
    eid = build("github", "commit", "o/n@a1B2c3")
    assert parse(eid)[2] == "o/n@a1B2c3"


@pytest.mark.parametrize(
    "connector,etype,native",
    [
        ("GitHub", "repo", "x"),  # 大写 connector
        ("github", "Repo", "x"),  # 大写 type
        ("github", "repo", ""),  # 空 native
        ("github", "repo", "a:b"),  # 冒号
        ("gb#", "repo", "x"),
    ],
)
def test_invalid_inputs_raise(connector, etype, native):
    with pytest.raises(EntityIdError):
        build(connector, etype, native)


def test_parse_invalid_format():
    with pytest.raises(EntityIdError):
        parse("no-colon-here")


def test_content_hash_stable_across_crlf_and_nfc():
    a = "hello\r\nworld\r\n"
    b = "hello\nworld\n"  # 仅换行符风格不同 → 同哈希
    assert content_hash(a) == content_hash(b)
    assert content_hash("café") == content_hash("cafe\u0301")  # NFC 归一


def test_trailing_newline_is_semantic():
    # 结构差异（结尾换行有无）视为不同内容——哈希要的是稳定，不是美观
    assert content_hash("x\n") != content_hash("x")


def test_bytes_passthrough_unnormalized():
    raw = b"\xff\xfe raw bytes"
    assert len(content_hash(raw)) == 64


def test_normalize_trailing_whitespace():
    # 行尾空白去除；结构（含结尾换行）保持原样——哈希只需稳定不需美观
    assert normalize_content("a \r\n b\r\n") == "a\n b\n"
