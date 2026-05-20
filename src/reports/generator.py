"""
评审报告生成器
- 基于数据库评审结果生成 Markdown 格式报告
- 包含评分概览、详细评审意见、改进建议
"""
from typing import List, Dict, Optional
from datetime import datetime


class ReportGenerator:
    """评审报告生成器"""

    def generate(
        self,
        submission_id: str,
        team_name: str,
        question_title: str,
        dimension_scores: List[Dict],
        final_score: Dict,
        verification_results: List[Dict],
        sandbox_result: Optional[Dict] = None,
    ) -> str:
        """生成 Markdown 评审报告"""
        lines = []

        # 标题
        lines.append(f"# 评审报告: {team_name}")
        lines.append(f"")
        lines.append(f"**赛题**: {question_title}  ")
        lines.append(f"**作品ID**: {submission_id}  ")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
        lines.append("")

        # 评分概览
        lines.append("## 评分概览")
        lines.append("")
        lines.append("| 维度 | 得分 | 置信度 | 评审模型 |")
        lines.append("|------|------|--------|----------|")
        for ds in dimension_scores:
            lines.append(
                f"| {self._dim_name(ds['dimension'])} | {ds['score']} | "
                f"{ds.get('confidence', '-')} | {ds.get('llm_model', '-')} |"
            )
        lines.append("")

        # 总分
        if final_score:
            lines.append(f"**加权总分**: {final_score.get('total_score', '-')}  ")
            lines.append(f"**整体置信度**: {final_score.get('confidence', '-')}  ")
            if final_score.get('human_review_required'):
                lines.append("⚠️ **需要人工复核**")
            lines.append("")

        # 沙箱执行结果
        if sandbox_result:
            lines.append("## 沙箱执行结果")
            lines.append("")
            lines.append(f"- **构建状态**: {sandbox_result.get('build_status', 'N/A')}")
            lines.append(f"- **退出码**: {sandbox_result.get('build_exit_code', 'N/A')}")
            if sandbox_result.get('test_results'):
                tr = sandbox_result['test_results']
                lines.append(f"- **测试**: 通过 {tr.get('passed', 0)}/{tr.get('total', 0)}")
            lines.append("")

        # 详细评审意见
        lines.append("## 详细评审意见")
        lines.append("")
        for ds in dimension_scores:
            dim = ds['dimension']
            lines.append(f"### {self._dim_name(dim)} ({ds['score']}分)")
            lines.append("")
            if ds.get('reasoning'):
                lines.append(f"**评语**: {ds['reasoning']}")
                lines.append("")
            if ds.get('strengths'):
                lines.append("**亮点**:")
                for s in ds['strengths']:
                    lines.append(f"- {s}")
                lines.append("")
            if ds.get('weaknesses'):
                lines.append("**不足**:")
                for w in ds['weaknesses']:
                    lines.append(f"- {w}")
                lines.append("")
            if ds.get('improvements'):
                lines.append("**改进建议**:")
                for i in ds['improvements']:
                    lines.append(f"- {i}")
                lines.append("")

        # Verifier 结果
        if verification_results:
            lines.append("## Verifier 交叉验证")
            lines.append("")
            for vr in verification_results:
                lines.append(
                    f"- **{self._dim_name(vr['dimension'])}**: "
                    f"原始 {vr.get('original_score', '-')} → "
                    f"验证 {vr.get('verified_score', '-')} "
                    f"(偏差: {vr.get('deviation', '-')})"
                )
            lines.append("")

        # 总结
        lines.append("---")
        lines.append("*本报告由 AI 评审系统自动生成，仅供参考。*")

        return "\n".join(lines)

    def _dim_name(self, key: str) -> str:
        names = {
            "functionality": "功能正确性",
            "code_quality": "代码质量",
            "architecture": "架构设计",
            "innovation": "创新性",
            "documentation": "文档完整性",
            "testing": "测试覆盖",
        }
        return names.get(key, key)
