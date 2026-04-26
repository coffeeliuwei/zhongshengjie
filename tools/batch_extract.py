#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量外部小说提炼入口（单一命令）
=====================================

顺序执行完整提炼流程：
  1. 案例提炼（case_builder 管道：C4清洗 + Bigram熵 + MinHash去重 + 28场景类型）
  2. 语义案例提炼（unified_case_extractor：Ex3语义分组，写同一 cases/ 目录）
  3. 10维度提炼（unified_extractor：技法/角色关系/情感弧/对话风格等）
  4. 场景自动发现（scene_discoverer）
  5. 同步案例到 Qdrant case_library_v2
  6. 同步10维度到各自 Qdrant collection

用法：
  python tools/batch_extract.py              # 全量提炼
  python tools/batch_extract.py --limit 100  # 测试模式，每维度限100本
  python tools/batch_extract.py --skip-case  # 跳过案例提炼，只跑10维度
  python tools/batch_extract.py --sync-only  # 只同步，不提炼
"""

import sys
import os
import subprocess
import argparse
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CASE_SCRIPTS = PROJECT_ROOT / ".case-library" / "scripts"
TOOLS = PROJECT_ROOT / "tools"
NOVEL_EXTRACTOR = PROJECT_ROOT / ".novel-extractor"


def log(msg: str):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def run_step(label: str, cmd: list, cwd=None) -> bool:
    """运行一个子步骤，失败时打印警告但不中断整体流程"""
    log(label)
    print(f">> {' '.join(str(c) for c in cmd)}\n")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, env=env)
    if result.returncode != 0:
        print(f"\n[WARN] {label} 退出码 {result.returncode}，继续下一步")
        return False
    return True


def step1_case_builder(py: str, limit: int = 0):
    """案例提炼：先 --convert 转格式，再 --extract 关键词匹配管道（含 C4+Bigram熵+MinHash）"""
    convert_cmd = [py, str(TOOLS / "case_builder.py"), "--convert"]
    if limit:
        convert_cmd += ["--limit", str(limit)]
    run_step("Step 1a/6 格式转换 (case_builder --convert)", convert_cmd)

    cmd = [py, str(TOOLS / "case_builder.py"), "--extract"]
    if limit:
        cmd += ["--limit", str(limit)]
    run_step("Step 1b/6 案例提炼 (case_builder --extract)", cmd)


def step2_semantic_case(py: str, limit: int = 0):
    """语义案例提炼：unified_case_extractor Ex3语义分组"""
    cmd = [py, str(CASE_SCRIPTS / "unified_case_extractor.py"), "--extract"]
    if limit:
        cmd += ["--limit", str(limit)]
    run_step("Step 2/6 语义案例提炼 (unified_case_extractor)", cmd, cwd=CASE_SCRIPTS)


def step3_dimensions(py: str, limit: int = 0):
    """10维度提炼：technique/角色关系/情感弧/对话风格等"""
    cmd = [py, str(TOOLS / "unified_extractor.py"), "--force"]
    if limit:
        cmd += ["--limit", str(limit)]
    run_step("Step 3/6 10维度提炼 (unified_extractor)", cmd)


def step3b_cleanup_jsonl():
    """删除各维度的 JSONL 原始积累文件（_all.json 已保存，JSONL 不再需要）"""
    from pathlib import Path
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from core.config_loader import get_config
        output_dir = Path(get_config().get("extractor", {}).get("output_dir", r"E:\novel_extracted"))
    except Exception:
        output_dir = Path(r"E:\novel_extracted")

    total_bytes = 0
    removed = 0
    for jsonl in output_dir.rglob("*_items.jsonl"):
        try:
            total_bytes += jsonl.stat().st_size
            jsonl.unlink()
            removed += 1
        except Exception as e:
            print(f"  [WARN] 无法删除 {jsonl}: {e}")
    print(f"[CLEANUP] 删除 {removed} 个 JSONL 文件，释放 {total_bytes/1024/1024/1024:.1f} GB")


def step4_scene_discovery(py: str):
    """场景自动发现：从未分类片段中发现新场景类型"""
    scene_discoverer = TOOLS / "scene_discoverer.py"
    if not scene_discoverer.exists():
        print("[SKIP] scene_discoverer.py 不存在，跳过场景发现")
        return
    run_step("Step 4/6 场景自动发现 (scene_discoverer)", [py, str(scene_discoverer), "--discover"])


def step5_sync_cases(py: str):
    """同步案例到 Qdrant case_library_v2"""
    run_step(
        "Step 5/6 同步案例 → Qdrant case_library_v2",
        [py, str(CASE_SCRIPTS / "sync_to_qdrant.py"), "--docker", "--no-resume"],
    )


def step6_sync_dimensions(py: str):
    """同步已支持的维度到 Qdrant（novel/technique/case）"""
    migrate = TOOLS / "archived_migrations" / "migrate_lite_resumable.py"
    if not migrate.exists():
        print("[SKIP] migrate_lite_resumable.py 不存在，跳过维度同步")
        return

    # migrate_lite_resumable.py 只支持这三个集合
    # 新维度（character_relation/dialogue_style 等）尚无专用 sync 脚本，跳过
    collections = ["novel", "technique", "case"]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    log("Step 6/6 同步维度 → Qdrant (novel/technique/case)")
    for col in collections:
        print(f"\n  同步 {col}...")
        result = subprocess.run(
            [py, str(migrate), "--collection", col],
            cwd=PROJECT_ROOT,
            env=env,
        )
        if result.returncode != 0:
            print(f"  [WARN] {col} 同步失败，继续")


def main():
    parser = argparse.ArgumentParser(description="批量外部小说提炼入口")
    parser.add_argument("--limit", type=int, default=0, help="每维度限制处理小说数（0=不限）")
    parser.add_argument("--skip-case", action="store_true", help="跳过案例提炼（Step 1-2）")
    parser.add_argument("--skip-dims", action="store_true", help="跳过10维度提炼（Step 3）")
    parser.add_argument("--sync-only", action="store_true", help="只同步，跳过所有提炼步骤")
    args = parser.parse_args()

    py = sys.executable
    start = time.time()

    print(f"\n{'='*60}")
    print(f"  众生界 批量外部小说提炼")
    print(f"  模式: {'sync-only' if args.sync_only else 'full'}")
    if args.limit:
        print(f"  限制: 每维度 {args.limit} 本（测试模式）")
    print(f"{'='*60}")

    if not args.sync_only:
        if not args.skip_case:
            step1_case_builder(py, args.limit)
            step2_semantic_case(py, args.limit)
        if not args.skip_dims:
            step3_dimensions(py, args.limit)
            step3b_cleanup_jsonl()
            step4_scene_discovery(py)

    step5_sync_cases(py)
    step6_sync_dimensions(py)

    elapsed = int(time.time() - start)
    print(f"\n[DONE] 批量提炼完成，总耗时 {elapsed//3600}h{(elapsed%3600)//60}m{elapsed%60}s")


if __name__ == "__main__":
    main()