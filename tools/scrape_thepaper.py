#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
澎湃新闻犯罪/司法案例爬取工具
================================

抓取澎湃新闻法治栏目及关键词搜索结果，保存为结构化 .txt 文件供人工审阅。

用法：
    python tools/scrape_thepaper.py                        # 默认：全部关键词+法治栏目
    python tools/scrape_thepaper.py --keywords 杀人 诈骗  # 只抓指定关键词
    python tools/scrape_thepaper.py --channel-only         # 只抓法治栏目（不搜关键词）
    python tools/scrape_thepaper.py --limit 200            # 每个关键词最多200篇
    python tools/scrape_thepaper.py --out E:/司法案例      # 指定输出目录

输出格式：
    {output_dir}/thepaper/{keyword_or_channel}/{YYYYMMDD}_{slug}.txt
    每个 txt 文件头部含 META 块，正文紧随其后，便于人工审阅。
"""

import argparse
import json
import re
import sys
import time
import random
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("[!] 缺少依赖，请先运行：pip install requests beautifulsoup4 lxml")
    sys.exit(1)

# 从 config.json 读取输出目录，找不到时降级到硬编码默认值
def _default_output() -> Path:
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from core.config_loader import get_judicial_cases_dir
        return get_judicial_cases_dir()
    except Exception:
        return Path("E:/司法案例")

# ── 默认配置 ──────────────────────────────────────────────────────────────────

DEFAULT_OUTPUT = _default_output()

# 搜索关键词（覆盖主要刑事案件类型）
DEFAULT_KEYWORDS = [
    "杀人案", "命案侦破", "故意杀人",
    "强奸案", "性侵",
    "抢劫案", "入室抢劫",
    "诈骗案", "电信诈骗",
    "绑架案",
    "毒品案",
    "黑社会", "黑恶势力",
    "审判 案件",
    "死刑 案件",
    "冤案 平反",
    "悬案 侦破",
]

# 澎湃频道 ID
# 说明：澎湃搜索页为 JS 渲染，requests 无法直接获取结果，改为按频道抓取
# 每次调用 load_index.jsp 返回该频道最新 9 篇，定期运行可持续积累
FAZHI_CHANNELS = {
    "实时案情": "25435",   # ★ 法治子栏目：实时案情（最精准）
    "法治":     "25635",   # 法治主频道
    "深度资讯": "25464",   # 深度资讯
    "深度":     "27224",   # 深度报道
    "社会":     "25718",   # 社会新闻（含犯罪报道）
    "法律实务": "25437",   # 牛街的法律/法律实务
    "一号专题": "25422",   # 专题报道
    "湃客_法律":"26916",   # 湃客法律频道
    "地方新闻": "25910",   # 地方社会新闻
    "暗访调查": "25911",   # 调查性报道
}

BASE_URL = "https://www.thepaper.cn"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.thepaper.cn/",
}

# 请求间隔（秒），防止被封
DELAY_MIN = 2.0
DELAY_MAX = 5.0

# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _sleep():
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


def _slug(text: str, maxlen: int = 40) -> str:
    text = re.sub(r'[^\w一-鿿]+', '_', text)
    return text.strip('_')[:maxlen]


def _article_id_from_url(url: str | None) -> str | None:
    if not url:
        return None
    m = re.search(r'newsDetail_forward_(\d+)', url)
    return m.group(1) if m else None


def _href(tag) -> str:
    """BeautifulSoup tag.get("href") → plain str，消除 AttributeValueList 类型歧义。"""
    val = tag.get("href")
    if val is None:
        return ""
    return val if isinstance(val, str) else str(val[0]) if val else ""


def _get(url: str, params: dict | None = None, retries: int = 3) -> requests.Response | None:
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt < retries - 1:
                print(f"    [重试 {attempt+1}/{retries}] {e}")
                time.sleep(3 + attempt * 2)
            else:
                print(f"    [!] 请求失败: {url} → {e}")
                return None


# ── 搜索模块（Baidu 站内搜索）────────────────────────────────────────────────
# 澎湃新闻搜索页为 JS 渲染，改用 Baidu「site:thepaper.cn 关键词」定向抓取

BAIDU_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.baidu.com/",
}


def search_articles(keyword: str, max_pages: int = 5) -> list[dict]:
    """
    通过 Baidu 站内搜索「site:thepaper.cn keyword」获取澎湃文章 URL。
    每页约 10 条，max_pages 控制最大页数。
    """
    results = []
    seen_ids: set[str] = set()
    query = f"site:thepaper.cn {keyword}"

    for page in range(max_pages):
        pn = page * 10  # Baidu 分页参数
        resp = _get(
            "https://www.baidu.com/s",
            params={"wd": query, "pn": pn, "rn": 10},
        )
        if resp is None:
            break

        resp.encoding = "utf-8"

        # 直接从 HTML 文本提取澎湃文章 ID（Baidu 结果页内嵌了真实 URL）
        found_on_page = 0
        all_links = re.findall(
            r'thepaper\.cn/newsDetail_forward_(\d+)',
            resp.text
        )
        for art_id in all_links:
            if art_id in seen_ids:
                continue
            seen_ids.add(art_id)
            href = f"https://www.thepaper.cn/newsDetail_forward_{art_id}"
            results.append({
                "id": art_id,
                "title": "待获取",
                "date": "",
                "url": href,
                "source": "baidu_search",
                "keyword": keyword,
            })
            found_on_page += 1

        print(f"  Baidu搜索「{keyword}」第{page+1}页：找到 {found_on_page} 条")
        if found_on_page == 0:
            break
        _sleep()

    return results


# ── 频道模块 ─────────────────────────────────────────────────────────────────

def channel_articles(channel_name: str, channel_id: str, max_pages: int = 20) -> list[dict]:
    """
    抓取指定频道的文章列表。
    澎湃频道加载接口：load_index.jsp?nodeids=ID&index=PAGE
    """
    results = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/load_index.jsp"
        params = {"nodeids": channel_id, "index": page}
        resp = _get(url, params=params)
        if resp is None:
            break

        soup = BeautifulSoup(resp.text, "lxml")
        # 澎湃频道页用 CSS Modules 混淆 class，直接按 href 模式全量找链接
        a_tags = soup.find_all("a", href=re.compile(r'/newsDetail_forward_\d+'))

        found_on_page = 0
        for a_tag in a_tags:
            href = _href(a_tag)
            if not href.startswith("http"):
                href = urljoin(BASE_URL, href)

            art_id = _article_id_from_url(href)
            if not art_id or art_id in seen_ids:
                continue
            seen_ids.add(art_id)

            # 标题从父容器文本拼出，实际标题在文章页再准确获取
            parent = a_tag.parent
            title = (parent.get_text(strip=True) if parent else "") or a_tag.get_text(strip=True) or "待获取"

            results.append({
                "id": art_id,
                "title": title[:60],
                "date": "",
                "url": href,
                "source": "channel",
                "keyword": channel_name,
            })
            found_on_page += 1

        print(f"  频道「{channel_name}」第{page}页：找到 {found_on_page} 条")

        if found_on_page == 0:
            break

        _sleep()

    return results


# ── 正文抓取 ─────────────────────────────────────────────────────────────────

def fetch_article_content(url: str) -> dict | None:
    """
    抓取单篇文章正文，返回 {title, date, content, author}。
    """
    resp = _get(url)
    if resp is None:
        return None

    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "lxml")

    # 标题（澎湃用 CSS Modules，class 含 title__ 前缀）
    title_tag = soup.find("h1", class_=re.compile(r'title'))
    if not title_tag:
        title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "未知标题"

    # 日期（ant-space-item 中找日期格式文本）
    date_str = ""
    for div in soup.find_all(class_=re.compile(r'ant-space-item')):
        txt = div.get_text(strip=True)
        if re.search(r'\d{4}-\d{2}-\d{2}', txt):
            date_str = txt.strip()
            break

    # 作者/来源（headerContent 区域的 <a> 标签）
    header = soup.find(class_=re.compile(r'headerContent|left__'))
    author = ""
    if header:
        a_tags = header.find_all("a")
        author = " ".join(a.get_text(strip=True) for a in a_tags if a.get_text(strip=True))

    # 正文（cententWrap 或 newsContent 容器）
    content_tag = (
        soup.find(class_=re.compile(r'cententWrap|newsContent|article-content'))
        or soup.find("article")
    )
    if content_tag:
        for tag in content_tag(["script", "style", "figure", "aside", "nav"]):
            tag.decompose()
        paragraphs = [p.get_text(strip=True) for p in content_tag.find_all("p")]
        paragraphs = [p for p in paragraphs if len(p) > 10]
        content = "\n\n".join(paragraphs)
    else:
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 20]
        content = "\n\n".join(paragraphs)

    if len(content) < 100:
        return None  # 内容太少，跳过

    return {
        "title": title,
        "date": date_str,
        "author": author,
        "content": content,
    }


# ── 保存 ─────────────────────────────────────────────────────────────────────

def save_article(output_dir: Path, category: str, meta: dict, detail: dict) -> Path:
    """
    保存为 META + 正文 的 .txt 文件。
    """
    cat_dir = output_dir / "thepaper" / _slug(category)
    cat_dir.mkdir(parents=True, exist_ok=True)

    date_prefix = re.sub(r'[^\d]', '', detail["date"])[:8] or datetime.now().strftime("%Y%m%d")
    filename = f"{date_prefix}_{_slug(detail['title'])}_{meta['id']}.txt"
    filepath = cat_dir / filename

    lines = [
        "===META===",
        f"标题: {detail['title']}",
        f"日期: {detail['date']}",
        f"作者: {detail['author']}",
        f"来源: 澎湃新闻",
        f"栏目: {category}",
        f"URL: {meta['url']}",
        f"文章ID: {meta['id']}",
        "===CONTENT===",
        "",
        detail["content"],
    ]
    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


# ── 进度管理 ─────────────────────────────────────────────────────────────────

def load_progress(output_dir: Path) -> set[str]:
    progress_file = output_dir / "thepaper" / ".progress.json"
    if progress_file.exists():
        try:
            return set(json.loads(progress_file.read_text(encoding="utf-8")))
        except Exception:
            pass
    return set()


def save_progress(output_dir: Path, done_ids: set[str]):
    progress_file = output_dir / "thepaper" / ".progress.json"
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    progress_file.write_text(json.dumps(list(done_ids), ensure_ascii=False, indent=2), encoding="utf-8")


# ── 主流程 ───────────────────────────────────────────────────────────────────

def run(
    keywords: list[str],
    channels: dict[str, str],
    output_dir: Path,
    limit_per_keyword: int,
    channel_only: bool,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    done_ids = load_progress(output_dir)
    print(f"[i] 已有进度：{len(done_ids)} 篇已下载，自动跳过")

    # 收集待抓取文章元信息
    all_metas: list[dict] = []

    if not channel_only:
        max_pages = max(1, limit_per_keyword // 10)
        for kw in keywords:
            print(f"\n[搜索] 关键词：{kw}")
            metas = search_articles(kw, max_pages=max_pages)
            all_metas.extend(metas)
            print(f"  合计 {len(metas)} 条")

    for ch_name, ch_id in channels.items():
        print(f"\n[频道] {ch_name} (id={ch_id})")
        metas = channel_articles(ch_name, ch_id, max_pages=20)
        all_metas.extend(metas)
        print(f"  合计 {len(metas)} 条")

    # 去重
    seen_ids: set[str] = set()
    unique_metas = []
    for m in all_metas:
        if m["id"] not in seen_ids:
            seen_ids.add(m["id"])
            unique_metas.append(m)

    print(f"\n[i] 去重后共 {len(unique_metas)} 篇，跳过已下载 {len(done_ids)} 篇")

    to_fetch = [m for m in unique_metas if m["id"] not in done_ids]
    print(f"[i] 本次需抓取：{len(to_fetch)} 篇\n")

    success = 0
    fail = 0

    for i, meta in enumerate(to_fetch, 1):
        print(f"[{i}/{len(to_fetch)}] {meta['title'][:40]}")
        detail = fetch_article_content(meta["url"])

        if detail is None:
            print(f"    [!] 内容抓取失败，跳过")
            fail += 1
        else:
            filepath = save_article(output_dir, meta["keyword"], meta, detail)
            done_ids.add(meta["id"])
            save_progress(output_dir, done_ids)
            print(f"    [OK] 已保存 -> {filepath.name}({len(detail['content'])} 字)")
            success += 1

        _sleep()

    print(f"\n[完成] 成功 {success} 篇 / 失败 {fail} 篇")
    print(f"[目录] {output_dir / 'thepaper'}")


# ── 入口 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="澎湃新闻犯罪案例爬取")
    parser.add_argument("--keywords", nargs="+", default=DEFAULT_KEYWORDS,
                        help="搜索关键词列表（默认使用内置列表）")
    parser.add_argument("--channel-only", action="store_true",
                        help="只抓法治栏目，不搜索关键词")
    parser.add_argument("--limit", type=int, default=100,
                        help="每个关键词最多抓取篇数（默认100）")
    parser.add_argument("--out", type=str, default=str(DEFAULT_OUTPUT),
                        help=f"输出根目录（默认 {DEFAULT_OUTPUT}）")
    args = parser.parse_args()

    output_dir = Path(args.out)

    print("=" * 60)
    print("  澎湃新闻犯罪/司法案例爬取工具")
    print("=" * 60)
    print(f"  输出目录: {output_dir / 'thepaper'}")
    print(f"  关键词数: {len(args.keywords)}")
    print(f"  每词上限: {args.limit} 篇")
    print(f"  请求间隔: {DELAY_MIN}–{DELAY_MAX} 秒")
    print("=" * 60)
    print()

    run(
        keywords=args.keywords,
        channels=FAZHI_CHANNELS,
        output_dir=output_dir,
        limit_per_keyword=args.limit,
        channel_only=args.channel_only,
    )


if __name__ == "__main__":
    main()
