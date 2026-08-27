"""Evolution Timeline 算法引擎（03 计划书 §模块E 的确定性部分）。

输入：repo-intel-core `signals` 月度信号包 JSON（本地 git 仓即可产出——零 GitHub API）
输出：阶段化 Timeline（label 留空，命名交上层 LLM；本模块只做确定性切片与边界检测）

时序锁说明：纯函数分析层，无任何网络/采集代码（ADR-006 偏差记录）。
"""

from __future__ import annotations

import math

SCHEMA_VERSION = "1.0"

_W_DIR = 2.0
_W_DEP = 2.0
_W_TERM = 1.0


def _features(bucket: dict) -> dict[tuple[str, str], float]:
    vec: dict[tuple[str, str], float] = {}
    for d in bucket.get("new_dirs") or []:
        vec[("dir", d)] = vec.get(("dir", d), 0.0) + _W_DIR
    for dep in bucket.get("deps_added") or []:
        vec[("dep", dep)] = vec.get(("dep", dep), 0.0) + _W_DEP
    for term in bucket.get("top_terms") or []:
        vec[("term", term)] = vec.get(("term", term), 0.0) + _W_TERM
    return vec


def _cosine(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _month_index(month: str) -> int:
    y, m = month.split("-")
    return int(y) * 12 + int(m) - 1


def merge_sparse_buckets(
    months: list[dict],
    min_bucket_commits: int = 2,
    max_merge_span: int = 3,
) -> list[dict]:
    """稀疏月合并：只有低活跃月（commits < 阈值）才并入邻近桶。

    规则：
    - 活跃月独立成桶；
    - 积压的低活跃月优先并入**前一个桶**（跨度 ≤ max_merge_span），否则自立门户；
    - 无 commits 的桶剔除。
    """
    buckets: list[dict] = []
    pending: list[dict] = []

    def _merge(last: dict, p: dict) -> None:
        last["commits"] += p["commits"]
        last["contributors"] = max(last["contributors"], p["contributors"])
        last["new_dirs"] += p["new_dirs"]
        last["deps_added"] += p["deps_added"]
        last["top_terms"] += p["top_terms"]
        last.setdefault("merged_months", []).append(p["month"])

    def flush(attach_to_last: bool) -> None:
        while pending:
            p = pending.pop(0)
            if (
                attach_to_last
                and buckets
                and _month_index(p["month"]) - _month_index(buckets[-1]["month"]) <= max_merge_span
            ):
                _merge(buckets[-1], p)
            else:
                buckets.append(p)

    for m in months:
        if m.get("commits", 0) >= min_bucket_commits:
            flush(True)  # 先安置此前积压的低活跃月
            buckets.append(dict(m))
        else:
            pending.append(m)
    flush(True)  # 尾部低活跃月回挂最后桶（跨度内），避免悬挂碎桶
    return [b for b in buckets if b.get("commits", 0) > 0]


def detect_boundaries(buckets: list[dict], theta: float = 0.6) -> list[int]:
    """返回边界索引（bucket 下标，即新阶段的第一个桶）。恒含 0。

    规则：① 日历缺口（相邻桶月份不连续）强制切分；
          ② 特征余弦相似度 < theta 切分。
    """
    cuts = [0]
    feats = [_features(b) for b in buckets]
    for i in range(1, len(buckets)):
        gap = _month_index(buckets[i]["month"]) - _month_index(buckets[i - 1]["month"]) > 1
        sim = _cosine(feats[i - 1], feats[i])
        if gap or sim < theta:
            cuts.append(i)
    return cuts


def build_stages(buckets: list[dict], cuts: list[int]) -> list[dict]:
    stages: list[dict] = []
    for s_idx, start in enumerate(cuts):
        end = cuts[s_idx + 1] if s_idx + 1 < len(cuts) else len(buckets)
        group = buckets[start:end]
        if not group:
            continue
        stats = {
            "commits": sum(b["commits"] for b in group),
            "max_contributors": max(b["contributors"] for b in group),
            "new_dirs": sorted({d for b in group for d in b.get("new_dirs", [])}),
            "deps_added": sorted({d for b in group for d in b.get("deps_added", [])}),
            "top_terms": sorted({t for b in group for t in b.get("top_terms", [])})[:8],
        }
        stages.append(
            {
                "index": len(stages),
                "start": group[0]["month"],
                "end": group[-1]["month"],
                "months": [b["month"] for b in group],
                "stats": stats,
                "label": None,  # 命名归上层 LLM（--labels 可注入）
            },
        )
    # 过小阶段并入邻居（<2 桶且非唯一阶段）
    merged: list[dict] = []
    for st in stages:
        if len(st["months"]) < 2 and len(stages) > 1 and merged:
            merged[-1]["end"] = st["end"]
            merged[-1]["months"].extend(st["months"])
            m = merged[-1]["stats"]
            s = st["stats"]
            m["commits"] += s["commits"]
            m["new_dirs"] = sorted(set(m["new_dirs"]) | set(s["new_dirs"]))
            m["deps_added"] = sorted(set(m["deps_added"]) | set(s["deps_added"]))
        else:
            merged.append(st)
    for i, st in enumerate(merged):
        st["index"] = i
    return merged


def run_timeline(
    pack: dict,
    theta: float = 0.6,
    labels: dict[str, str] | None = None,
) -> dict:
    months = pack.get("months") or []
    if not months:
        raise ValueError("信号包为空：months 缺失或为空列表")

    buckets = merge_sparse_buckets(months)
    cuts = detect_boundaries(buckets, theta=theta)
    stages = build_stages(buckets, cuts)
    if labels:
        for idx, name in labels.items():
            if 0 <= int(idx) < len(stages):
                stages[int(idx)]["label"] = name

    return {
        "schemaVersion": SCHEMA_VERSION,
        "repo": pack.get("repo"),
        "theta": theta,
        "truncated": bool(pack.get("truncated")),
        "boundaries": [buckets[i]["month"] for i in cuts],
        "stages": stages,
    }


# ---------------------------------------------------------------- 渲染器


def render_text(tl: dict) -> str:
    lines = [f"# Evolution Timeline — {tl['repo']} (θ={tl['theta']})"]
    for prev, st in zip([None, *tl["stages"][:-1]], tl["stages"], strict=False):
        if prev is not None:
            lines.append("~~~~~~ boundary ~~~~~~")
        s = st["stats"]
        label = st["label"] or f"Stage {st['index'] + 1}"
        lines.append(
            f"{st['start']} ─▶ {st['end']} │ {label} │ commits={s['commits']} "
            f"dirs=+{','.join(s['new_dirs'][:3]) or '-'} "
            f"deps=+{','.join(s['deps_added'][:3]) or '-'}",
        )
    return "\n".join(lines)


def render_gantt(tl: dict) -> str:
    out = ["gantt", f"  title {tl['repo']} 演化阶段", "  dateFormat YYYY-MM"]
    for st in tl["stages"]:
        label = (st["label"] or f"Stage {st['index'] + 1}").replace(":", " ")
        end_year, end_m = st["end"].split("-")
        nxt = int(end_m) + 1
        end = f"{end_year}-{nxt:02d}" if nxt <= 12 else f"{int(end_year) + 1}-01"
        out.append(f"  {label} :s{st['index']}, {st['start']}-01, {end}-01")
    return "\n".join(out)


def load_pack(path: str) -> dict:
    import json

    with Path_(path).open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "months" not in data:
        raise ValueError("信号包格式错误：需要含 months 的 JSON 对象")
    return data


def Path_(path: str):  # 薄别名便于测试 monkeypatch
    from pathlib import Path as _P

    return _P(path)
