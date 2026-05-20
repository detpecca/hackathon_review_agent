"""
LangGraph 评审工作流定义
- 基于有向无环图（DAG）的多Agent协作评审流程
- 状态管理: ReviewState 贯穿整个工作流
- 节点: Preprocess -> [并行:Functional,Quality,Arch,Innovation] -> Verifier -> Decision

对应PRD Section 4.3 工作流引擎
"""
from typing import TypedDict, Annotated, List, Optional
from operator import add

try:
    from langgraph.graph import StateGraph, END
except ImportError:
    StateGraph = None
    END = None

from src.agents.functional import FunctionalReviewAgent
from src.agents.quality import CodeQualityAgent
from src.agents.architecture import ArchitectureReviewAgent
from src.agents.innovation import InnovationReviewAgent
from src.agents.verifier import VerifierCrossCheckAgent


# ============================================================
# 状态定义
# ============================================================
class ReviewState(TypedDict, total=False):
    """评审工作流全局状态"""
    # 输入
    submission_id: str
    team_id: str
    question_id: int
    question_description: str
    baseline_description: str
    file_path: str
    project_metadata: dict

    # 预处理输出
    parsed_files: dict
    file_tree: str
    dependencies: dict

    # 沙箱执行输出
    build_status: str
    build_exit_code: int
    build_stderr: str
    test_results: Optional[dict]
    static_analysis: Optional[dict]

    # 各Agent评审输出
    functional_score: dict
    quality_score: dict
    architecture_score: dict
    innovation_score: dict

    # Verifier输出
    verification_results: List[dict]
    needs_human_review: bool
    human_review_reason: str

    # 最终输出
    final_scores: dict
    report_path: Optional[str]
    status: str


# ============================================================
# 节点函数
# ============================================================
def preprocess_node(state: ReviewState) -> ReviewState:
    """
    预处理节点:
    1. 从MinIO下载作品
    2. 解压ZIP/TAR.GZ
    3. 识别项目类型和语言
    4. 提取关键文件
    5. 构建目录树
    6. 解析依赖信息
    """
    # TODO: 实现完整的预处理逻辑
    # Phase 4 简化版: 从已有 metadata 构建 parsed_files
    metadata = state.get("project_metadata", {})
    state["parsed_files"] = metadata.get("parsed_files", {"README.md": {"language": "markdown", "content_preview": metadata.get("description", "")}})
    state["file_tree"] = metadata.get("file_tree", "README.md\n")
    state["dependencies"] = metadata.get("dependencies", {})
    return state


def sandbox_test_node(state: ReviewState) -> ReviewState:
    """
    沙箱测试节点:
    1. 在Docker容器中构建项目
    2. 执行自动化测试
    3. 运行静态分析
    4. 采集执行指标
    """
    # TODO: Phase 5 实现完整的沙箱执行
    # Phase 4 简化版: 标记为构建成功
    state["build_status"] = "success"
    state["build_exit_code"] = 0
    state["build_stderr"] = ""
    state["test_results"] = {"total": 0, "passed": 0, "failed": 0, "coverage": 0, "duration_ms": 0}
    state["static_analysis"] = {"lint_errors": 0, "lint_warnings": 0, "avg_complexity": 0, "max_complexity": 0, "duplication": 0, "security_issues": [], "dependency_vulns": []}
    return state


def functional_review_node(state: ReviewState) -> ReviewState:
    """功能评审Agent"""
    agent = FunctionalReviewAgent()
    result = agent.review_from_state(state)
    state["functional_score"] = result
    return state


def quality_review_node(state: ReviewState) -> ReviewState:
    """代码质量评审Agent"""
    agent = CodeQualityAgent()
    result = agent.review_from_state(state)
    state["quality_score"] = result
    return state


def architecture_review_node(state: ReviewState) -> ReviewState:
    """架构评审Agent"""
    agent = ArchitectureReviewAgent()
    result = agent.review_from_state(state)
    state["architecture_score"] = result
    return state


def innovation_review_node(state: ReviewState) -> ReviewState:
    """创新性感知Agent"""
    agent = InnovationReviewAgent()
    result = agent.review_from_state(state)
    state["innovation_score"] = result
    return state


def verifier_node(state: ReviewState) -> ReviewState:
    """
    Verifier交叉验证节点:
    对四个维度的评分进行独立验证
    """
    verifier = VerifierCrossCheckAgent()
    dimensions = [
        ("functionality", state.get("functional_score", {})),
        ("code_quality", state.get("quality_score", {})),
        ("architecture", state.get("architecture_score", {})),
        ("innovation", state.get("innovation_score", {})),
    ]

    verification_results = []
    needs_human_review = False
    reasons = []

    for dim_name, score_data in dimensions:
        if not score_data:
            continue

        result = verifier.verify_dimension(
            dimension=dim_name,
            original_score=score_data.get("score", 0),
            original_reason=score_data.get("reason", ""),
            original_strengths=score_data.get("strengths", []),
            original_weaknesses=score_data.get("weaknesses", []),
            state=state,
        )

        verification_results.append({
            "dimension": dim_name,
            "original_score": score_data.get("score", 0),
            "verified_score": result.get("your_score", score_data.get("score", 0)),
            "deviation": result.get("deviation", 0),
            "confidence": result.get("confidence", 1.0),
            "needs_human_review": result.get("needs_human_review", False),
            "verification_reason": result.get("verification_reason", ""),
        })

        if result.get("needs_human_review", False):
            needs_human_review = True
            reasons.append(f"{dim_name}: deviation={result.get('deviation', 0)}")

    state["verification_results"] = verification_results
    state["needs_human_review"] = needs_human_review
    state["human_review_reason"] = "; ".join(reasons) if reasons else ""
    return state


def decision_node(state: ReviewState) -> ReviewState:
    """
    决策节点:
    - 汇总各维度评分
    - 判定是否需人工复核
    """
    scores = {
        "functionality": state.get("functional_score", {}).get("score", 0),
        "code_quality": state.get("quality_score", {}).get("score", 0),
        "architecture": state.get("architecture_score", {}).get("score", 0),
        "innovation": state.get("innovation_score", {}).get("score", 0),
    }

    # 计算平均分作为总分
    total = sum(scores.values()) / len(scores) if scores else 0

    state["status"] = "completed"
    state["final_scores"] = {
        "total_score": round(total, 2),
        "confidence": 0.75,
        "dimension_scores": scores,
        "needs_human_review": state.get("needs_human_review", False),
    }
    return state


def generate_report_node(state: ReviewState) -> ReviewState:
    """生成评审报告节点"""
    # TODO: Phase 6 实现完整报告生成
    state["status"] = "completed"
    state["report_path"] = None
    return state


# ============================================================
# 条件边路由函数
# ============================================================
def route_after_preprocessing(state: ReviewState) -> str:
    """预处理后路由"""
    if state.get("parsed_files") is None or len(state["parsed_files"]) == 0:
        state["status"] = "failed"
        return "failed"
    return "sandbox_test"


def route_after_sandbox(state: ReviewState) -> str:
    """沙箱执行后进入并行评审"""
    return "parallel_review"


def route_after_verifier(state: ReviewState) -> str:
    """Verifier后路由"""
    if state.get("needs_human_review", False):
        return "human_review"
    return "report"


# ============================================================
# 构建工作流图
# ============================================================
def build_review_workflow():
    """构建评审DAG工作流"""
    if StateGraph is None:
        return None

    workflow = StateGraph(ReviewState)

    workflow.add_node("preprocess", preprocess_node)
    workflow.add_node("sandbox_test", sandbox_test_node)
    workflow.add_node("functional_review", functional_review_node)
    workflow.add_node("quality_review", quality_review_node)
    workflow.add_node("architecture_review", architecture_review_node)
    workflow.add_node("innovation_review", innovation_review_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("decision", decision_node)
    workflow.add_node("generate_report", generate_report_node)

    workflow.set_entry_point("preprocess")

    workflow.add_conditional_edges(
        "preprocess",
        route_after_preprocessing,
        {"sandbox_test": "sandbox_test", "failed": END},
    )

    workflow.add_conditional_edges(
        "sandbox_test",
        route_after_sandbox,
        {"parallel_review": "functional_review"},
    )

    workflow.add_edge("functional_review", "quality_review")
    workflow.add_edge("quality_review", "architecture_review")
    workflow.add_edge("architecture_review", "innovation_review")
    workflow.add_edge("innovation_review", "verifier")

    workflow.add_conditional_edges(
        "verifier",
        route_after_verifier,
        {"human_review": "decision", "report": "generate_report"},
    )

    workflow.add_edge("generate_report", END)
    workflow.add_edge("decision", END)

    return workflow.compile()


review_workflow = build_review_workflow()
