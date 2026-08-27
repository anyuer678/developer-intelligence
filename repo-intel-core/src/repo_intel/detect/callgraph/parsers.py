"""五语言 tree-sitter 解析器（M4-03，移植自 evocode arch/*_parser.py）。

grammar 包按需在函数内导入：缺某个语言包只影响该语言，不拖垮整体。
Parser 非线程安全（C 层）→ 按线程缓存；Language 不可变可共享。
"""

from __future__ import annotations

import threading

from repo_intel.detect.callgraph.base import ArchNode, infer_node_type

_local = threading.local()

# 扩展名 → (语言标识, 解析函数名)
EXT_LANG = {
    ".py": "python",
    ".go": "go",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}


def _text(node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _parser_for(lang: str):
    import importlib

    mod_name = {
        "python": "tree_sitter_python",
        "go": "tree_sitter_go",
        "java": "tree_sitter_java",
        "javascript": "tree_sitter_javascript",
    }.get(lang)
    ts_lang = "language_typescript"
    if lang == "typescript":
        mod_name = "tree_sitter_typescript"
    if mod_name is None:  # pragma: no cover
        raise LookupError(lang)
    cache = getattr(_local, "parsers", None)
    if cache is None:
        cache = {}
        _local.parsers = cache
    if lang in cache:
        return cache[lang]
    from tree_sitter import Language, Parser

    mod = importlib.import_module(mod_name)
    language = getattr(mod, ts_lang)() if lang == "typescript" else mod.language()
    parser = Parser(Language(language))
    cache[lang] = parser
    return parser


def _call_names_generic(call_node, attr_type: str) -> list[str]:
    fn = call_node.child_by_field_name("function")
    if fn is None:
        return []
    if fn.type == "identifier":
        return [_text(fn)]
    if fn.type == attr_type:
        parts = _text(fn).split(".")
        if len(parts) >= 2:
            return [parts[0], parts[-1]]
    return []


def _collect_calls(node, call_type: str, attr_type: str) -> list[str]:
    out: list[str] = []

    def visit(n) -> None:
        if n.type == call_type:
            out.extend(_call_names_generic(n, attr_type))
        for c in n.children:
            visit(c)

    visit(node)
    return out


# ---------------------------------------------------------------- python


def parse_python_file(file_path: str, source: bytes):
    tree = _parser_for("python").parse(source)
    nodes: list[ArchNode] = []
    caller_calls: list[tuple[str, list[str]]] = []
    file_stem = file_path.rsplit("/", 1)[-1]
    for child in tree.root_node.children:
        if child.type in ("class_definition", "function_definition"):
            name_node = child.child_by_field_name("name")
            if name_node is None:
                continue
            name = _text(name_node)
            nodes.append(
                ArchNode(
                    node_key=name,
                    name=name,
                    node_type=infer_node_type(name, file_stem),
                    file_path=file_path,
                    line=child.start_point[0] + 1,
                ),
            )
            caller_calls.append(
                (name, _collect_calls(child, "call", "attribute")),
            )
    return nodes, caller_calls


# ---------------------------------------------------------------- go


def _receiver_type(node) -> str | None:
    receiver = node.child_by_field_name("receiver")
    if receiver is None:
        return None
    cleaned = _text(receiver).strip("()").replace("*", "").strip()
    parts = cleaned.split()
    return parts[-1] if parts else None


def parse_go_file(file_path: str, source: bytes):
    tree = _parser_for("go").parse(source)
    nodes: list[ArchNode] = []
    caller_calls: list[tuple[str, list[str]]] = []
    file_stem = file_path.rsplit("/", 1)[-1]
    seen: set[str] = set()
    for child in tree.root_node.children:
        if child.type == "function_declaration":
            name_node = child.child_by_field_name("name")
            if name_node is None:
                continue
            name = _text(name_node)
            nodes.append(
                ArchNode(
                    node_key=name,
                    name=name,
                    node_type=infer_node_type(name, file_stem),
                    file_path=file_path,
                    line=child.start_point[0] + 1,
                ),
            )
            caller_calls.append(
                (name, _collect_calls(child, "call_expression", "selector_expression")),
            )
        elif child.type == "method_declaration":
            recv = _receiver_type(child)
            if recv is None:
                continue
            if recv not in seen:
                seen.add(recv)
                nodes.append(
                    ArchNode(
                        node_key=recv,
                        name=recv,
                        node_type=infer_node_type(recv, file_stem),
                        file_path=file_path,
                        line=child.start_point[0] + 1,
                    ),
                )
            caller_calls.append(
                (recv, _collect_calls(child, "call_expression", "selector_expression")),
            )
    return nodes, caller_calls


# ---------------------------------------------------------------- javascript / typescript


def _js_symbol_name(node) -> str | None:
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return _text(name_node)
    if node.type in ("lexical_declaration", "variable_declaration"):
        decs = node.child_by_field_name("declarations")
        first = (
            decs.named_children[0]
            if decs is not None and decs.named_children
            else next(
                (c for c in node.named_children if c.type == "variable_declarator"),
                None,
            )
        )
        if first is not None:
            id_node = first.child_by_field_name("name")
            if id_node is not None:
                return _text(id_node)
    return None


def _parse_js_family(file_path: str, source: bytes, lang: str):
    tree = _parser_for(lang).parse(source)
    nodes: list[ArchNode] = []
    caller_calls: list[tuple[str, list[str]]] = []
    file_stem = file_path.rsplit("/", 1)[-1]
    for child in tree.root_node.children:
        target = child
        if child.type == "export_statement":
            inner = child.named_children[0] if child.named_children else None
            if inner is None:
                continue
            target = inner
        if target.type in (
            "class_declaration",
            "function_declaration",
            "generator_function_declaration",
            "lexical_declaration",
            "variable_declaration",
        ):
            name = _js_symbol_name(target)
            if name is None:
                continue
            nodes.append(
                ArchNode(
                    node_key=name,
                    name=name,
                    node_type=infer_node_type(name, file_stem),
                    file_path=file_path,
                    line=target.start_point[0] + 1,
                ),
            )
            caller_calls.append(
                (name, _collect_calls(target, "call_expression", "member_expression")),
            )
    return nodes, caller_calls


def parse_js_file(file_path: str, source: bytes):
    return _parse_js_family(file_path, source, "javascript")


def parse_ts_file(file_path: str, source: bytes):
    return _parse_js_family(file_path, source, "typescript")


# ---------------------------------------------------------------- java


def parse_java_file(file_path: str, source: bytes):
    tree = _parser_for("java").parse(source)
    nodes: list[ArchNode] = []
    caller_calls: list[tuple[str, list[str]]] = []
    file_stem = file_path.rsplit("/", 1)[-1]

    field_types: dict[str, str] = {}

    def _invocation_names(invocation) -> list[str]:
        obj = invocation.child_by_field_name("object")
        name = invocation.child_by_field_name("name")
        names: list[str] = []
        if obj is not None:
            if obj.type == "object_creation_expression":
                type_node = obj.child_by_field_name("type")
                names.append(_text(type_node) if type_node is not None else _text(obj))
            elif obj.type == "identifier" and _text(obj) in field_types:
                names.append(field_types[_text(obj)])
            elif obj.type == "field_access":
                names.append(_text(obj).split(".")[-1])
            else:
                names.append(_text(obj))
        if name is not None:
            names.append(_text(name))
        return names

    def _collect_invocations(node) -> list[str]:
        out: list[str] = []

        def visit(n) -> None:
            if n.type == "method_invocation":
                out.extend(_invocation_names(n))
            for c in n.children:
                visit(c)

        visit(node)
        return out

    def walk_class(node) -> None:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        name = _text(name_node)
        nodes.append(
            ArchNode(
                node_key=name,
                name=name,
                node_type=infer_node_type(name, file_stem),
                file_path=file_path,
                line=node.start_point[0] + 1,
            ),
        )
        body = node.child_by_field_name("body")
        if body is not None:
            for c in body.children:
                if c.type == "field_declaration":
                    declarator = c.child_by_field_name("declarator")
                    type_node = c.child_by_field_name("type")
                    if declarator is not None and type_node is not None:
                        field_types[_text(declarator)] = _text(type_node)
            caller_calls.append((name, _collect_invocations(body)))
            for c in body.children:
                if c.type == "class_declaration":
                    walk_class(c)

    for child in tree.root_node.children:
        if child.type == "class_declaration":
            walk_class(child)
    return nodes, caller_calls


_PARSE_FN = {
    "python": parse_python_file,
    "go": parse_go_file,
    "java": parse_java_file,
    "javascript": parse_js_file,
    "typescript": parse_ts_file,
}


def parser_for_extension(ext: str):
    """扩展名 → 解析函数；未支持返回 None。"""
    lang = EXT_LANG.get(ext.lower())
    return None if lang is None else _PARSE_FN[lang]
