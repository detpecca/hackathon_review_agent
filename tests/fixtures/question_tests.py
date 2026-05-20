"""
赛题标准测试用例注入模板
对应PRD Section 5.2 FR-TST-03 自定义测试注入

每道赛题定义一组注入式测试用例，在沙箱执行时自动注入到作品中。
测试用例覆盖核心功能、边界条件和异常处理。

Claude Code应据此实现:
1. 从数据库加载对应question_id的测试用例
2. 将测试代码写入作品项目目录
3. 执行测试并收集结果

TODO: 以下测试用例需要根据实际赛题需求细化
"""
from typing import Dict, List


# ============================================================
# Q1: 招投标信息聚合工具
# ============================================================
Q1_TESTS = """
\"\"\"
招投标信息聚合工具 - 标准测试用例
测试目标: 验证数据抓取、聚合、去重、API功能
\"\"\"
import pytest
import json
import time
from unittest.mock import patch, MagicMock


class TestBidDataAggregator:
    \"\"\"测试招投标数据抓取功能\"\"\"

    def test_fetch_from_single_source(self):
        \"\"\"测试从单一来源抓取数据\"\"\"
        # TODO: 根据实际接口调整
        result = aggregator.fetch("http://test.example.com/bids")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_fetch_multiple_sources(self):
        \"\"\"测试从多个来源并发抓取\"\"\"
        sources = ["http://test1.com", "http://test2.com", "http://test3.com"]
        results = aggregator.fetch_multiple(sources)
        assert len(results) == len(sources)

    def test_handle_network_timeout(self):
        \"\"\"测试网络超时处理\"\"\"
        with patch('requests.get', side_effect=TimeoutError):
            result = aggregator.fetch("http://timeout.com")
            assert result == [] or result is None  # 应优雅处理

    def test_handle_http_error(self):
        \"\"\"测试HTTP错误处理 (404, 500等)\"\"\"
        with patch('requests.get', return_value=MagicMock(status_code=500)):
            result = aggregator.fetch("http://error.com")
            assert result == [] or result is None

    def test_duplicate_detection(self):
        \"\"\"测试重复数据检测和去重\"\"\"
        raw_data = [
            {"id": "B001", "title": "Project A"},
            {"id": "B001", "title": "Project A"},  # 重复
            {"id": "B002", "title": "Project B"},
        ]
        deduped = aggregator.deduplicate(raw_data)
        assert len(deduped) == 2

    def test_data_normalization(self):
        \"\"\"测试数据标准化（字段统一）\"\"\"
        raw = [
            {"project_name": "Test", "amount": "100万"},
            {"title": "Test2", "price": "2000000"},
        ]
        normalized = aggregator.normalize(raw)
        assert all("title" in item for item in normalized)

    def test_api_response_format(self):
        \"\"\"测试API返回JSON格式\"\"\"
        import flask  # or fastapi testclient
        # response = client.get("/api/bids")
        # assert response.status_code == 200
        # assert response.content_type == "application/json"
        pass  # TODO: 根据实际框架调整

    def test_pagination_support(self):
        \"\"\"测试分页功能\"\"\"
        # response = client.get("/api/bids?page=2&limit=10")
        # assert "items" in response.json()
        # assert "total" in response.json()
        pass  # TODO

    def test_search_functionality(self):
        \"\"\"测试搜索功能\"\"\"
        # results = aggregator.search(keyword="市政工程")
        # assert all("市政" in r.get("title", "") for r in results)
        pass  # TODO

    def test_rate_limiting(self):
        \"\"\"测试对目标网站的限速请求\"\"\"
        start = time.time()
        for _ in range(5):
            aggregator.fetch("http://test.com")
        elapsed = time.time() - start
        assert elapsed >= 2.0  # 假设限速 2秒内最多5次


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""


# ============================================================
# Q2: 文件整理助手
# ============================================================
Q2_TESTS = """
\"\"\"
文件整理助手 - 标准测试用例
测试目标: 验证文件分类、整理、去重功能
\"\"\"
import pytest
import os
import tempfile
import shutil
from pathlib import Path


class TestFileOrganizer:
    \"\"\"测试文件整理功能\"\"\"

    def setup_method(self):
        \"\"\"创建临时混乱目录\"\"\"
        self.test_dir = tempfile.mkdtemp()
        # 创建各种类型文件
        for name in ["photo1.jpg", "photo2.png", "doc1.pdf", "doc2.docx",
                     "song1.mp3", "video1.mp4", "script.py", "readme.txt",
                     "data1.csv", "backup.tar.gz", "photo1.jpg"]:  # 重复文件
            Path(self.test_dir, name).touch()

    def teardown_method(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_detect_file_types(self):
        \"\"\"测试文件类型识别\"\"\"
        files = organizer.scan(self.test_dir)
        assert len(files) > 0

    def test_categorize_by_type(self):
        \"\"\"测试按类型分类\"\"\"
        result = organizer.categorize(self.test_dir)
        assert "images" in result or "photos" in result
        assert "documents" in result or "docs" in result

    def test_remove_duplicates(self):
        \"\"\"测试重复文件检测和移除\"\"\"
        result = organizer.deduplicate(self.test_dir)
        # photo1.jpg出现了两次，去重后应只剩一个
        jpg_files = list(Path(self.test_dir).glob("**/*.jpg"))
        # TODO: 根据实际行为断言

    def test_handle_empty_directory(self):
        \"\"\"测试空目录处理\"\"\"
        empty_dir = tempfile.mkdtemp()
        result = organizer.organize(empty_dir)
        assert result == {} or result == []
        shutil.rmtree(empty_dir)

    def test_handle_special_characters(self):
        \"\"\"测试特殊字符文件名\"\"\"
        special_file = Path(self.test_dir, "文件 [test] (1).txt")
        special_file.touch()
        result = organizer.scan(self.test_dir)
        assert any("文件" in str(f) for f in result)

    def test_preserve_original_structure_option(self):
        \"\"\"测试保留原始结构选项\"\"\"
        # organizer.organize(self.test_dir, preserve_structure=True)
        # 断言原始子目录被保留
        pass  # TODO

    def test_dry_run_mode(self):
        \"\"\"测试试运行模式（不实际移动文件）\"\"\"
        # result = organizer.organize(self.test_dir, dry_run=True)
        # assert 文件未被实际移动
        pass  # TODO


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""


# ============================================================
# Q5: PPT文档结构化检索与问答
# ============================================================
Q5_TESTS = """
\"\"\"
PPT文档结构化检索与问答 - 标准测试用例
测试目标: 验证文档解析、检索、问答功能
\"\"\"
import pytest


class TestPPTRetrievalQA:
    \"\"\"测试PPT检索与问答\"\"\"

    def test_parse_pptx_structure(self):
        \"\"\"测试PPTX文件解析\"\"\"
        result = parser.parse("test.pptx")
        assert "slides" in result or "pages" in result
        assert len(result.get("slides", [])) > 0

    def test_extract_text_content(self):
        \"\"\"测试文本内容提取\"\"\"
        content = parser.extract_text("test.pptx")
        assert len(content) > 0
        assert isinstance(content, str)

    def test_semantic_search(self):
        \"\"\"测试语义检索\"\"\"
        results = engine.search(query="第三季度营收", top_k=5)
        assert len(results) <= 5
        assert all("score" in r or "similarity" in r for r in results)

    def test_question_answering(self):
        \"\"\"测试问答功能\"\"\"
        answer = qa.answer("公司的主要产品是什么？")
        assert isinstance(answer, str)
        assert len(answer) > 0

    def test_handle_empty_query(self):
        \"\"\"测试空查询处理\"\"\"
        result = engine.search(query="", top_k=5)
        assert result == [] or result is None

    def test_support_pdf_input(self):
        \"\"\"测试PDF文件支持\"\"\"
        result = parser.parse("test.pdf")
        assert result is not None

    def test_support_ppt_input(self):
        \"\"\"测试旧版PPT支持\"\"\"
        result = parser.parse("test.ppt")
        assert result is not None

    def test_large_file_handling(self):
        \"\"\"测试大文件处理（>50MB）\"\"\"
        # 应能处理不OOM
        pass  # TODO: 需要实际大文件

    def test_indexing_performance(self):
        \"\"\"测试索引构建性能\"\"\"
        import time
        start = time.time()
        engine.index(["doc1.pptx", "doc2.pptx"])
        elapsed = time.time() - start
        assert elapsed < 30  # 应在30秒内完成


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""


# ============================================================
# 测试用例注册表
# ============================================================
QUESTION_TEST_TEMPLATES: Dict[str, str] = {
    "Q1": Q1_TESTS,   # 招投标信息聚合工具
    "Q2": Q2_TESTS,   # 文件整理助手
    "Q3": None,       # 嵌入式开发 - 需要硬件模拟
    "Q4": None,       # AI记忆管理 - 需要Benchmark
    "Q5": Q5_TESTS,   # PPT检索问答
    "Q6": None,       # 论文复现 - 需要图像对比
    "Q7": None,       # Rust OS - 需要特殊环境
}


def get_test_template(question_code: str) -> str:
    \"\"\"
    获取指定赛题的测试用例模板

    Args:
        question_code: 赛题编号 (Q1-Q7)

    Returns:
        测试代码字符串，如果该赛题不支持注入测试则返回None
    \"\"\"
    return QUESTION_TEST_TEMPLATES.get(question_code)


def list_supported_questions() -> List[str]:
    \"\"\"获取支持注入测试的赛题列表\"\"\"
    return [k for k, v in QUESTION_TEST_TEMPLATES.items() if v is not None]
