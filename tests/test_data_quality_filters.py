# tests/test_data_quality_filters.py
"""
案例库数据质量过滤器测试
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ────────────────────────────────────────────────
# 测试 _is_ad_paragraph
# ────────────────────────────────────────────────

class TestIsAdParagraph:
    def _call(self, text: str) -> bool:
        from tools.case_builder import _is_ad_paragraph
        return _is_ad_paragraph(text)

    def test_detects_website_url(self):
        assert self._call("本书来自www.abada.cn免费txt小说下载站") is True

    def test_detects_http_url(self):
        assert self._call("更多内容请访问 https://example.com/read") is True

    def test_detects_download_pattern(self):
        assert self._call("免费下载小说请访问本站书库") is True

    def test_detects_qq_group(self):
        assert self._call("有问题请加QQ群123456789讨论") is True

    def test_detects_monthly_ticket(self):
        assert self._call("求月票！求推荐票！") is True

    def test_allows_clean_fiction(self):
        assert self._call("他拔出长剑，寒芒一闪，敌人应声倒下。") is False

    def test_allows_fiction_with_www_mention(self):
        assert self._call("她在网络小说里看到了这个名字，心中一动。") is False


# ────────────────────────────────────────────────
# 测试 _is_catalog_page
# ────────────────────────────────────────────────

class TestIsCatalogPage:
    def _call(self, text: str) -> bool:
        from tools.case_builder import _is_catalog_page
        return _is_catalog_page(text)

    def test_detects_chapter_list(self):
        toc = "\n".join([
            "第一章 主角登场",
            "第二章 初遇仙缘",
            "第三章 突破境界",
            "第四章 宗门考核",
            "第五章 天才辈出",
        ])
        assert self._call(toc) is True

    def test_detects_mixed_toc(self):
        toc = "\n".join([
            "前言",
            "第1章 序幕",
            "第2章 开始",
            "第3章 高潮",
            "第4章 结局",
            "后记",
        ])
        assert self._call(toc) is True

    def test_allows_chapter_content_with_few_titles(self):
        content = (
            "萧炎翻开书页，看到第一章写着：修炼之道，在于坚持。\n"
            "他深吸一口气，心中默念。\n"
            "第二章的内容更加深奥，让他皱起眉头思索。\n"
            "窗外，月光洒落，清风徐来。"
        )
        assert self._call(content) is False

    def test_short_paragraph_not_catalog(self):
        assert self._call("第一章 主角") is False


# ────────────────────────────────────────────────
# 测试 _get_chinese_ratio
# ────────────────────────────────────────────────

class TestGetChineseRatio:
    def _call(self, text: str) -> float:
        from tools.case_builder import _get_chinese_ratio
        return _get_chinese_ratio(text)

    def test_pure_chinese(self):
        assert self._call("汉字测试内容") > 0.9

    def test_mixed_url_text(self):
        ratio = self._call("www.abada.cn下载站")
        assert ratio < 0.6

    def test_empty_string(self):
        assert self._call("") == 0.0

    def test_english_only(self):
        assert self._call("Hello World") < 0.1


# ────────────────────────────────────────────────
# 测试 _is_sentence_complete
# ────────────────────────────────────────────────

class TestIsSentenceComplete:
    def _call(self, text: str) -> bool:
        from tools.case_builder import _is_sentence_complete
        return _is_sentence_complete(text)

    def test_ends_with_period(self):
        assert self._call("他转身离去。") is True

    def test_ends_with_exclamation(self):
        assert self._call("你竟敢！") is True

    def test_ends_with_question(self):
        assert self._call("这是为什么？") is True

    def test_ends_with_right_quote(self):
        assert self._call('他说："走吧。"') is True

    def test_incomplete_sentence(self):
        assert self._call("然后他走") is False

    def test_ends_with_comma(self):
        assert self._call("他走向前，") is False


# ────────────────────────────────────────────────
# 测试 _info_density
# ────────────────────────────────────────────────

class TestInfoDensity:
    def _call(self, text: str) -> float:
        from tools.case_builder import _info_density
        return _info_density(text)

    def test_high_density_prose(self):
        prose = "萧炎深吸一口气，体内斗气如洪水般涌动，冲击着金丹境的瓶颈。"
        assert self._call(prose) > 0.3

    def test_low_density_repetition(self):
        repeated = "啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊"
        assert self._call(repeated) < 0.1

    def test_empty_string(self):
        assert self._call("") == 0.0


# ────────────────────────────────────────────────
# 测试 _split_paragraphs 集成
# ────────────────────────────────────────────────

class TestSplitParagraphsFiltering:
    def _call(self, text: str):
        from tools.case_builder import CaseBuilder
        builder = CaseBuilder.__new__(CaseBuilder)
        return builder._split_paragraphs(text)

    def test_ad_paragraph_excluded(self):
        content = (
            "本书来自www.abada.cn免费txt小说下载站\n\n"
            "萧炎静静地站在山顶，望着远处连绵的山脉，心中涌起一股豪情。"
            "他深知，若要在这修炼界立足，只有不断变强，才是唯一的出路。"
            "夕阳西下，金色的光芒洒落在他的身上，仿佛预示着他即将踏上的征途。"
            "风中带着一丝凉意，却也夹杂着属于这片土地特有的气息。"
        )
        results = self._call(content)
        # 广告段落不应出现
        assert not any("abada" in p for p in results)
        # 正文段落应保留
        assert any("萧炎" in p for p in results)

    def test_catalog_page_excluded(self):
        toc_block = "\n".join([
            "第一章 开篇",
            "第二章 相遇",
            "第三章 对决",
            "第四章 突破",
            "第五章 归来",
        ])
        content = toc_block + "\n\n" + "萧炎拾起那枚晶莹的丹药，神识渗入其中。"
        results = self._call(content)
        assert not any("第一章 开篇" in p for p in results)

    def test_low_chinese_ratio_excluded(self):
        content = (
            "www.abada.cn/download/free/novel.txt abc123 english only\n\n"
            "萧炎凝视着远方，眼神坚毅。这一战，他必须赢。"
        )
        results = self._call(content)
        assert not any("abada" in p for p in results)


# ────────────────────────────────────────────────
# 测试 UUID 确定性
# ────────────────────────────────────────────────

class TestUUIDDeterminism:
    def test_same_case_id_same_uuid(self):
        import uuid
        case_id = "abc123def456"
        u1 = str(uuid.uuid5(uuid.NAMESPACE_DNS, case_id))
        u2 = str(uuid.uuid5(uuid.NAMESPACE_DNS, case_id))
        assert u1 == u2

    def test_different_case_ids_different_uuid(self):
        import uuid
        u1 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "content_hash_aaa"))
        u2 = str(uuid.uuid5(uuid.NAMESPACE_DNS, "content_hash_bbb"))
        assert u1 != u2

# ────────────────────────────────────────────────
# P2 进阶测试
# ────────────────────────────────────────────────

class TestCleanLines:
    def _call(self, text: str) -> str:
        from tools.case_builder import _clean_lines
        return _clean_lines(text)

    def test_removes_javascript_line(self):
        text = "他拔出了剑。\nJavaScript is required.\n剑光闪烁。"
        result = self._call(text)
        assert "javascript" not in result.lower()
        assert "他拔出了剑" in result
        assert "剑光闪烁" in result

    def test_removes_copyright_line(self):
        text = "版权所有 不得转载\n萧炎凝视远方，目光坚毅。"
        result = self._call(text)
        assert "版权所有" not in result
        assert "萧炎凝视远方" in result

    def test_keeps_clean_prose(self):
        text = "他仰望星空，心中一片澄明。\n这一刻，所有的烦恼都烟消云散。"
        result = self._call(text)
        assert "仰望星空" in result


class TestBigramEntropy:
    def _call(self, text: str) -> float:
        from tools.case_builder import _bigram_entropy
        return _bigram_entropy(text)

    def test_normal_prose_high_entropy(self):
        prose = (
            "萧炎深吸一口气，体内斗气奔涌，如同一条蛟龙盘踞丹田。"
            "他凝神静气，缓缓抬起右手，掌心一点火光瞬间化作滔天烈焰。"
            "众人倒吸凉气，谁也没想到他竟能将异火驾驭到这般地步。"
        )
        assert self._call(prose) > 6.0

    def test_repeated_text_low_entropy(self):
        text = "他打了他，他打了他，他打了他，" * 10
        assert self._call(text) < 5.0

    def test_short_text_returns_zero(self):
        assert self._call("短") == 0.0
