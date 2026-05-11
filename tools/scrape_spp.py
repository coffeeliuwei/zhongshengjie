#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最高人民检察院案例爬取工具
============================

抓取 spp.gov.cn 的案例文章（.shtml 服务端渲染，无需 JS）。
输出与 scrape_thepaper.py 相同格式，可直接被 filter_judicial_cases.py 过滤。

用法：
    python tools/scrape_spp.py                  # 默认：全部栏目
    python tools/scrape_spp.py --max-pages 20   # 每栏目最多20页
    python tools/scrape_spp.py --out E:/司法案例
"""

import argparse
import json
import re
import sys
import time
import random
from datetime import datetime
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("[!] 请先运行: pip install requests beautifulsoup4 lxml")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from core.config_loader import get_judicial_cases_dir
    DEFAULT_OUTPUT = get_judicial_cases_dir()
except Exception:
    DEFAULT_OUTPUT = Path("E:/司法案例")

BASE = "https://www.spp.gov.cn"

# 栏目：section_id → 显示名称
SECTIONS = {
    "zdgz": "典型案例",
    "tt":   "检察要闻",
    "jcyw": "检察动态",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.spp.gov.cn/",
}

DELAY_MIN, DELAY_MAX = 2.0, 4.0


def _sleep():
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


def _slug(text: str, maxlen: int = 40) -> str:
    text = re.sub(r'[^\w一-鿿]+', '_', text)
    return text.strip('_')[:maxlen]


def _get(url: str, retries: int = 3) -> requests.Response | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3 + attempt * 2)
            else:
                print(f"    [!] 失败: {url} -> {e}")
    return None


# ── 列表页 ───────────────────────────────────────────────────────────────────

def list_articles(section: str, max_pages: int) -> list[dict]:
    results = []
    seen: set[str] = set()
    pattern = re.compile(rf'/spp/{section}/(\d{{6}})/(t\d+_\d+)\.shtml')

    for page in range(1, max_pages + 1):
        if page == 1:
            url = f"{BASE}/spp/{section}/"
        else:
            url = f"{BASE}/spp/{section}/index_{page}.shtml"

        resp = _get(url)
        if resp is None:
            break

        resp.encoding = "utf-8"
        matches = pattern.findall(resp.text)
        new = 0
        for date_dir, file_id in matches:
            key = f"{date_dir}/{file_id}"
            if key in seen:
                continue
            seen.add(key)
            article_url = f"{BASE}/spp/{section}/{date_dir}/{file_id}.shtml"
            # 提取简单标题（链接前后的文字）
            # 从 href 前后文本拿标题，正式标题在文章页获取
            results.append({
                "url": article_url,
                "section": section,
                "key": key,
            })
            new += 1

        print(f"  [{SECTIONS.get(section, section)}] 第{page}页: {new} 篇新")
        if new == 0:
            break
        _sleep()

    return results


# ── 正文抓取 ─────────────────────────────────────────────────────────────────

def fetch_article(url: str) -> dict | None:
    resp = _get(url)
    if resp is None:
        return None

    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "lxml")

    # 标题
    title_tag = soup.find("h1") or soup.find(class_=re.compile(r'title'))
    title: str = title_tag.get_text(strip=True) if title_tag else ""
    if not title:
        t = soup.find("title")
        title = t.get_text(strip=True).split("_")[0].strip() if t else "未知标题"

    # 日期（从 URL 或页面）
    date_m = re.search(r'/(\d{4})(\d{2})/', url)
    date_str = f"{date_m.group(1)}-{date_m.group(2)}" if date_m else ""
    # 尝试从页面找更精确的日期
    for pat in [r'\d{4}年\d{1,2}月\d{1,2}日', r'\d{4}-\d{2}-\d{2}']:
        m = re.search(pat, soup.get_text())
        if m:
            date_str = m.group()
            break

    # 正文：最高检页面内容在 .content 或多个 <p> 里
    content_div = (
        soup.find(class_=re.compile(r'content|article|detail|news'))
        or soup.find(id=re.compile(r'content|article'))
    )
    if content_div:
        for tag in content_div(["script", "style", "nav", "aside"]):
            tag.decompose()
        paras = [p.get_text(strip=True) for p in content_div.find_all("p")]
    else:
        paras = [p.get_text(strip=True) for p in soup.find_all("p")]

    paras = [p for p in paras if len(p) > 20]
    content = "\n\n".join(paras)

    if len(content) < 80:
        return None

    return {"title": title, "date": date_str, "content": content}


# ── 保存 ─────────────────────────────────────────────────────────────────────

def save_article(output_dir: Path, meta: dict, detail: dict) -> Path:
    section_name: str = SECTIONS.get(meta["section"]) or meta["section"]
    cat_dir = output_dir / "spp" / _slug(section_name)
    cat_dir.mkdir(parents=True, exist_ok=True)

    date_prefix = re.sub(r'[^\d]', '', detail["date"])[:8] or datetime.now().strftime("%Y%m%d")
    filename = f"{date_prefix}_{_slug(detail['title'])}_{meta['key'].replace('/', '_')}.txt"
    filepath = cat_dir / filename

    lines = [
        "===META===",
        f"标题: {detail['title']}",
        f"日期: {detail['date']}",
        f"来源: 最高人民检察院",
        f"栏目: {section_name}",
        f"URL: {meta['url']}",
        "===CONTENT===",
        "",
        detail["content"],
    ]
    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


# ── 进度 ─────────────────────────────────────────────────────────────────────

def load_progress(output_dir: Path) -> set[str]:
    f = output_dir / "spp" / ".progress.json"
    if f.exists():
        try:
            return set(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return set()


def save_progress(output_dir: Path, done: set[str]):
    f = output_dir / "spp" / ".progress.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(list(done), ensure_ascii=False, indent=2), encoding="utf-8")


# ── 主流程 ───────────────────────────────────────────────────────────────────

def run(output_dir: Path, max_pages: int):
    done = load_progress(output_dir)
    print(f"[i] 已有进度: {len(done)} 篇已下载\n")

    all_metas: list[dict] = []
    for section in SECTIONS:
        print(f"[列表] {SECTIONS[section]} ({section})")
        metas = list_articles(section, max_pages)
        all_metas.extend(metas)
        print(f"  小计: {len(metas)} 篇\n")

    to_fetch = [m for m in all_metas if m["key"] not in done]
    # 去重
    seen_keys: set[str] = set()
    to_fetch_unique = []
    for m in to_fetch:
        if m["key"] not in seen_keys:
            seen_keys.add(m["key"])
            to_fetch_unique.append(m)

    print(f"[i] 本次需抓取: {len(to_fetch_unique)} 篇\n")

    ok = fail = 0
    for i, meta in enumerate(to_fetch_unique, 1):
        detail = fetch_article(meta["url"])
        if detail is None:
            print(f"[{i}/{len(to_fetch_unique)}] [!] 内容为空，跳过")
            fail += 1
        else:
            save_article(output_dir, meta, detail)
            done.add(meta["key"])
            save_progress(output_dir, done)
            title_short = detail['title'][:40].encode('gbk', errors='replace').decode('gbk')
            print(f"[{i}/{len(to_fetch_unique)}] [OK] {title_short} ({len(detail['content'])}z)")
            ok += 1
        _sleep()

    print(f"\n[完成] 成功 {ok} / 失败 {fail}")
    print(f"[目录] {output_dir / 'spp'}")


def main():
    parser = argparse.ArgumentParser(description="最高检案例爬取")
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--max-pages", type=int, default=15, help="每栏目最多页数（默认15）")
    args = parser.parse_args()

    output_dir = Path(args.out)
    print("=" * 56)
    print("  最高人民检察院案例爬取")
    print("=" * 56)
    print(f"  输出: {output_dir / 'spp'}")
    print(f"  栏目: {', '.join(SECTIONS.values())}")
    print(f"  每栏目最多: {args.max_pages} 页")
    print("=" * 56 + "\n")

    run(output_dir, args.max_pages)


if __name__ == "__main__":
    main()
