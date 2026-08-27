"""pydantic 模型 = JSON Schema 单一来源。

约定（见计划书 01 §四）：
- JSON 输出字段名为 camelCase 别名，与计划书 Schema v1.0 样例一致；
- 字段三态：null（没测）/ 数值（测到）/ 缺省——M1+ 模块在 M0 输出中恒为 null；
- 硬约束：已有字段不得改名/删除/改类型，只能新增可选字段。
"""

from __future__ import annotations

from dataclasses import field
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "1.0"


class CamelModel(BaseModel):
    """统一 camelCase 序列化别名；构造时仍可用 snake_case 字段名。"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---------------------------------------------------------------- 工具/仓库元信息


class ToolInfo(CamelModel):
    name: str = "repo-intel-core"
    version: str


class VcsInfo(CamelModel):
    type: str | None = None
    head_branch: str | None = None
    is_dirty: bool | None = None


class RepoInfo(CamelModel):
    path: str
    name: str
    vcs: VcsInfo | None = None


# ---------------------------------------------------------------- M0 实测字段


class LanguageStat(CamelModel):
    name: str
    pct: float
    files: int
    loc: int


class TopLevelDir(CamelModel):
    path: str
    file_count: int
    role: str | None = None  # guessed-entry / guessed-frontend / null


class StructureInfo(CamelModel):
    top_level_dirs: list[TopLevelDir] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)


class LargestFile(CamelModel):
    path: str  # 相对仓库根的 posix 风格路径
    loc: int


class ComplexityHotspot(CamelModel):
    path: str
    signal: str  # 例: "long-file loc=520" / "deep-nesting indent=28"


class TestEvidence(CamelModel):
    test_file_count: int = 0
    ratio_to_source: float | None = None  # 测试文件 / 全部代码文件
    frameworks: list[str] = field(default_factory=list)  # pytest / vitest / go-test ...


class TodoStats(CamelModel):
    """字节级大小写敏感计数（口径见 ADR）。"""

    todo_count: int = 0
    fixme_count: int = 0


class Metrics(CamelModel):
    total_loc: int = 0
    total_files: int = 0  # 含数据/文档类文件
    largest_files: list[LargestFile] = Field(default_factory=list)
    complexity_hotspots: list[ComplexityHotspot] = Field(default_factory=list)
    test_evidence: TestEvidence | None = None
    todos: TodoStats | None = None


class WarningItem(CamelModel):
    code: str
    detail: str


# ---------------------------------------------------------------- M1+ 预留（M0 恒为 null）


class EntryCandidate(CamelModel):
    file: str
    type: str | None = None  # cli / server / gui / lib
    confidence: float | None = None
    evidence: list[str] = Field(default_factory=list)


class ModuleInfo(CamelModel):
    name: str
    root_path: str
    files: int = 0
    responsibility: str | None = None  # 语义判断归上层 LLM，引擎留空
    cohesion_score: float | None = None


class InternalDep(CamelModel):
    frm: str  # from 是保留字
    to: str
    weight: int | None = None  # 聚合的导入次数（M1 起填充）


class ExternalDep(CamelModel):
    name: str
    version: str | None = None
    kind: str | None = None  # runtime / dev
    usage_files: int = 0
    risk: str | None = None  # M4-02: HIGH(EOL) / MEDIUM(接近EOL)；未命中为 None
    risk_reason: str | None = None


class DependencyGraph(CamelModel):
    internal: list[InternalDep] = Field(default_factory=list)
    external: list[ExternalDep] = Field(default_factory=list)


class FrameworkHit(CamelModel):
    name: str
    version: str | None = None
    category: str | None = None
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)


class BuildRun(CamelModel):
    build_system: list[str] = Field(default_factory=list)
    install_cmd: list[str] = Field(default_factory=list)
    dev_cmd: list[str] = Field(default_factory=list)
    test_cmd: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)


class GraphViolation(CamelModel):
    violation_type: str  # LAYER_VIOLATION / CYCLE
    description: str
    severity: str
    suggestion: str
    source_node_key: str | None = None
    target_node_key: str | None = None


class CallGraphNode(CamelModel):
    node_key: str
    name: str
    node_type: str  # CONTROLLER/SERVICE/REPOSITORY/ENTITY/UTIL/OTHER
    file_path: str
    line: int = 0
    in_degree: int = 0
    out_degree: int = 0


class CallGraphEdge(CamelModel):
    source_node_key: str
    target_node_key: str
    relation: str = "CALL"


class CallGraph(CamelModel):
    """函数级调用图（M4-03，可选能力：需安装 tree-sitter [arch] extra）。"""

    nodes: list[CallGraphNode] = Field(default_factory=list)
    edges: list[CallGraphEdge] = Field(default_factory=list)
    violations: list[GraphViolation] = Field(default_factory=list)


class GitMeta(CamelModel):
    """M3 可选模块；git 不存在时整体为 null。"""

    first_commit_at: str | None = None
    last_commit_at: str | None = None
    commit_count: int = 0
    contributor_count: int = 0
    activity_by_month: dict[str, int] = Field(default_factory=dict)
    branch_count: int | None = None
    tag_count: int | None = None


# ---------------------------------------------------------------- 顶层 Profile


class RepoProfile(CamelModel):
    schema_version: str = SCHEMA_VERSION
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    tool: ToolInfo
    repo: RepoInfo

    # ---- M0 实测 ----
    languages: list[LanguageStat] = Field(default_factory=list)
    structure: StructureInfo = Field(default_factory=StructureInfo)
    metrics: Metrics = Field(default_factory=Metrics)
    warnings: list[WarningItem] = Field(default_factory=list)

    # ---- M1+ 预留（三态中的"模块未启用"：恒为 null）----
    entry_points: list[EntryCandidate] | None = None
    modules: list[ModuleInfo] | None = None
    dependency_graph: DependencyGraph | None = None
    frameworks: list[FrameworkHit] | None = None
    build_run: BuildRun | None = None
    call_graph: CallGraph | None = None  # M4-03 可选能力（tree-sitter [arch] extra）
    git: GitMeta | None = None
