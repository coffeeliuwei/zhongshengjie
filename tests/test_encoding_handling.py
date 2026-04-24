#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
编码异常处理测试
================

测试各种编码场景下的异常处理。
"""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestUTF8Encoding:
    """UTF-8编码测试"""

    def test_valid_utf8_read(self, temp_dir):
        """测试有效UTF-8读取"""
        test_file = temp_dir / "utf8_valid.txt"
        content = "这是正常的UTF-8中文内容"
        test_file.write_text(content, encoding="utf-8")

        read_content = test_file.read_text(encoding="utf-8")
        assert read_content == content

    def test_utf8_with_bom(self, temp_dir):
        """测试UTF-8 BOM处理"""
        test_file = temp_dir / "utf8_bom.txt"
        # UTF-8 BOM + 中文内容
        test_file.write_bytes(b"\xef\xbb\xbf" + "这是BOM测试".encode("utf-8"))

        # 应能正常读取
        content = test_file.read_text(encoding="utf-8-sig")
        assert "BOM测试" in content


class TestGBKEncoding:
    """GBK编码测试"""

    def test_gbk_to_utf8_conversion(self, temp_dir):
        """测试GBK转UTF-8"""
        gbk_file = temp_dir / "gbk_source.txt"
        gbk_file.write_text("GBK编码内容", encoding="gbk")

        # 读取GBK并转换为UTF-8
        gbk_content = gbk_file.read_text(encoding="gbk")
        utf8_file = temp_dir / "utf8_target.txt"
        utf8_file.write_text(gbk_content, encoding="utf-8")

        # 验证转换成功
        utf8_content = utf8_file.read_text(encoding="utf-8")
        assert "GBK编码内容" in utf8_content

    def test_gbk_file_detection(self, temp_dir):
        """测试GBK文件自动检测"""
        gbk_file = temp_dir / "gbk_auto.txt"
        gbk_file.write_text("自动检测测试", encoding="gbk")

        # 尝试多种编码
        for encoding in ["utf-8", "gbk", "gb2312", "utf-8-sig"]:
            try:
                content = gbk_file.read_text(encoding=encoding)
                if "测试" in content:
                    assert encoding in ["gbk", "gb2312"]
                    break
            except UnicodeDecodeError:
                pass


class TestEncodingErrors:
    """编码错误处理测试"""

    def test_invalid_utf8_raises_error(self, temp_dir):
        """测试无效UTF-8抛出错误"""
        invalid_file = temp_dir / "invalid_utf8.txt"
        # 写入无效UTF-8字节
        invalid_file.write_bytes(b"\xd0\xcf\xc9\xfa")  # GBK字节

        with pytest.raises(UnicodeDecodeError):
            invalid_file.read_text(encoding="utf-8")

    def test_encoding_fallback_chain(self, temp_dir):
        """测试编码回退链"""
        mixed_file = temp_dir / "mixed.txt"
        mixed_file.write_bytes(b"\xd0\xcf\xc9\xfa")  # GBK字节

        # 模拟编码回退尝试
        encodings_to_try = ["utf-8", "gbk", "gb2312", "latin-1"]
        success_encoding = None

        for encoding in encodings_to_try:
            try:
                content = mixed_file.read_text(encoding=encoding)
                success_encoding = encoding
                break
            except UnicodeDecodeError:
                continue

        assert success_encoding in ["gbk", "gb2312", "latin-1"]

    def test_partial_invalid_encoding(self, temp_dir):
        """测试部分无效编码处理"""
        partial_file = temp_dir / "partial_invalid.txt"
        # 混合有效UTF-8和无效字节
        partial_file.write_bytes(b"valid\x00invalid\xff")

        # latin-1 可以读取任意字节
        content = partial_file.read_text(encoding="latin-1")
        assert len(content) > 0


class TestJSONEncoding:
    """JSON编码测试"""

    def test_json_utf8_load(self, temp_dir):
        """测试UTF-8 JSON加载"""
        json_file = temp_dir / "utf8.json"
        data = {"key": "中文值"}
        json_file.write_text('{"key": "中文值"}', encoding="utf-8")

        import json

        with open(json_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["key"] == "中文值"

    def test_json_gbk_load_with_encoding(self, temp_dir):
        """测试GBK JSON加载（指定编码）"""
        json_file = temp_dir / "gbk.json"
        json_file.write_text('{"key": "中文"}', encoding="gbk")

        import json

        with open(json_file, "r", encoding="gbk") as f:
            loaded = json.load(f)

        assert "中文" in loaded["key"]


class TestConfigEncoding:
    """配置文件编码测试"""

    def test_world_config_utf8(self, temp_dir):
        """测试世界观配置UTF-8"""
        config_file = temp_dir / "world_config.json"
        config_file.write_text(
            '{"name": "众生界", "realms": ["凡人", "觉醒"]}', encoding="utf-8"
        )

        import json

        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["name"] == "众生界"
        assert len(config["realms"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
