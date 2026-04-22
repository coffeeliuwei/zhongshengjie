"""提炼子进程生命周期管理

负责启动 .novel-extractor/run.py、追踪 PID、查询状态。
设计文档：docs/superpowers/specs/2026-04-15-data-extraction-connection-design.md
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional


def _default_extractor_dir() -> Path:
    return Path(__file__).parents[2] / ".novel-extractor"


class ExtractionRunner:
    """管理 .novel-extractor/run.py 子进程"""

    def __init__(self, extractor_dir: Optional[Path] = None):
        self.extractor_dir = extractor_dir or _default_extractor_dir()
        self.pid_file = self.extractor_dir / "extraction.pid"

    def is_running(self) -> bool:
        """检测提炼子进程是否存活；清理孤儿 PID 文件"""
        if not self.pid_file.exists():
            return False
        try:
            pid = int(self.pid_file.read_text().strip())
            # os.kill(pid, 0) on Windows sends CTRL_C_EVENT instead of checking
            # existence, causing KeyboardInterrupt when pid == os.getpid().
            # Use OpenProcess (Windows) or signal 0 (Unix) instead.
            if sys.platform == "win32":
                import ctypes
                handle = ctypes.windll.kernel32.OpenProcess(0x0400, False, pid)
                if handle == 0:
                    raise OSError("process not found")
                ctypes.windll.kernel32.CloseHandle(handle)
            else:
                os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            try:
                self.pid_file.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    def get_status(self) -> dict:
        """调用 run.py --status，返回原始输出和运行状态"""
        if not self.extractor_dir.exists():
            return {"raw": "提炼工具目录未找到", "running": False}
        result = subprocess.run(
            [sys.executable, "run.py", "--status"],
            cwd=self.extractor_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return {
            "raw": result.stdout or result.stderr or "（无输出）",
            "running": self.is_running(),
        }

    def start(self, mode: str) -> dict:
        """启动提炼子进程。

        Args:
            mode: "incremental"（默认续传）或 "full"（强制重跑）

        Returns:
            {"started": True, "pid": int, "mode": str}
            或 {"started": False, "status": dict}（已在运行）
        """
        if self.is_running():
            return {"started": False, "status": self.get_status()}

        if not self.extractor_dir.exists():
            raise FileNotFoundError(f"提炼工具目录不存在：{self.extractor_dir}")

        cmd = [sys.executable, "run.py", "--all"]
        if mode == "full":
            cmd.append("--no-resume")

        proc = subprocess.Popen(
            cmd,
            cwd=self.extractor_dir,
            start_new_session=True,
        )
        self.pid_file.write_text(str(proc.pid))
        return {"started": True, "pid": proc.pid, "mode": mode}
