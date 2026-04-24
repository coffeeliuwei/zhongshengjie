"""
并行入库脚本 - 同时入库多个维度
使用多进程并行处理，加速入库速度
"""

import subprocess
import sys
from pathlib import Path
import time

# 维度列表（按数据量排序，大的先处理）
DIMENSIONS = [
    "worldview_element_v1",  # 40万条，最慢
    "power_vocabulary_v1",  # 87K条
    "character_relation_v1",  # 198K条
    "emotion_arc_v1",  # 2K条
    "dialogue_style_v1",  # 405条
    "foreshadow_pair_v1",  # 2K条
    "power_cost_v1",  # 140条
    "author_style_v1",  # 3K条
]


def run_parallel(dimensions: list, max_workers: int = 3):
    """并行入库多个维度

    Args:
        dimensions: 维度列表
        max_workers: 最大并行数（建议不超过3，避免内存溢出）
    """
    script_dir = Path(__file__).parent
    sync_script = script_dir / "sync_to_qdrant.py"

    print(f"[并行入库] 启动 {max_workers} 个进程")
    print(f"[维度列表] {dimensions}")

    processes = []
    active_dims = []

    for i, dim in enumerate(dimensions):
        if len(processes) >= max_workers:
            # 等待一个进程完成
            print(f"\n[等待] 已达到最大并行数 {max_workers}，等待进程完成...")
            while processes:
                for j, (proc, dim_name) in enumerate(processes):
                    if proc.poll() is not None:  # 进程已完成
                        if proc.returncode == 0:
                            print(f"[完成] {dim_name} 入库完成")
                        else:
                            print(
                                f"[错误] {dim_name} 入库失败，返回码: {proc.returncode}"
                            )
                        processes.pop(j)
                        break
                time.sleep(5)

        # 启动新进程
        print(f"\n[启动] 入库维度: {dim}")
        proc = subprocess.Popen(
            [sys.executable, str(sync_script), "--sync", dim],
            cwd=str(script_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        processes.append((proc, dim))
        print(f"  PID: {proc.pid}")

    # 等待所有进程完成
    print(f"\n[等待] 等待剩余 {len(processes)} 个进程完成...")
    while processes:
        for j, (proc, dim_name) in enumerate(processes):
            if proc.poll() is not None:
                if proc.returncode == 0:
                    print(f"[完成] {dim_name} 入库完成")
                else:
                    print(f"[错误] {dim_name} 入库失败")
                processes.pop(j)
                break
        time.sleep(5)

    print("\n[完成] 所有维度入库完成")

    # 打印最终状态
    subprocess.run(
        [sys.executable, str(sync_script), "--status"],
        cwd=str(script_dir),
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="并行入库多个维度")
    parser.add_argument("--workers", type=int, default=2, help="并行进程数（建议2-3）")
    parser.add_argument("--dimensions", nargs="+", help="指定维度（默认全部）")

    args = parser.parse_args()

    dims = args.dimensions or DIMENSIONS

    # 验证维度名称
    valid_dims = []
    for dim in dims:
        if dim in DIMENSIONS or dim.endswith("_v1"):
            valid_dims.append(dim)
        else:
            print(f"[警告] 未知维度: {dim}")

    if valid_dims:
        run_parallel(dimensions=valid_dims, max_workers=args.workers)


if __name__ == "__main__":
    main()
