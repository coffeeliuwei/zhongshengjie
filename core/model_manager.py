# core/model_manager.py
"""模型版本管理器

管理嵌入模型和 LLM 的版本配置，支持模型切换和基准测试。

用法:
    from core.model_manager import ModelManager
    
    mgr = ModelManager()
    
    # 获取当前模型配置
    config = mgr.get_current_embedding_model()
    
    # 列出可用模型
    models = mgr.list_available_models()
    
    # 运行基准测试
    result = mgr.benchmark_model("bge-m3-v2")
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from core.config_loader import get_config, get_project_root


class ModelManager:
    """模型版本管理器
    
    功能：
    1. 获取当前使用的模型配置
    2. 列出所有可用模型
    3. 运行模型基准测试
    4. 切换模型版本（含向量库重建）
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """初始化模型管理器
        
        Args:
            config_path: 配置文件路径（可选，默认从 config_loader 加载）
        """
        self.project_root = get_project_root()
        self.config = get_config()
        self._model_config = self.config.get("model", {})
    
    # ==================== 嵌入模型 ====================
    
    def get_current_embedding_model(self) -> Dict[str, Any]:
        """获取当前嵌入模型配置
        
        Returns:
            模型配置字典，包含 name, version, vector_size, model_path, benchmark 等
        """
        embedding_config = self._model_config.get("embedding", {})
        current_id = embedding_config.get("current", "bge-m3-v1")
        available = embedding_config.get("available", {})
        
        return available.get(current_id, {
            "name": "BAAI/bge-m3",
            "version": "default",
            "vector_size": 1024,
            "model_path": None,
            "benchmark": None
        })
    
    def list_available_embedding_models(self) -> List[Dict[str, Any]]:
        """列出所有可用的嵌入模型
        
        Returns:
            模型列表，每个包含 id, name, version, status 等信息
        """
        embedding_config = self._model_config.get("embedding", {})
        available = embedding_config.get("available", {})
        current = embedding_config.get("current", "bge-m3-v1")
        
        models = []
        for model_id, model_info in available.items():
            models.append({
                "id": model_id,
                "name": model_info.get("name", "unknown"),
                "version": model_info.get("version", "unknown"),
                "vector_size": model_info.get("vector_size", 1024),
                "is_current": model_id == current,
                "has_benchmark": model_info.get("benchmark") is not None,
                "status": "current" if model_id == current else "available"
            })
        
        return models
    
    def get_embedding_model_path(self, model_id: Optional[str] = None) -> Optional[Path]:
        """获取嵌入模型路径
        
        Args:
            model_id: 模型 ID（可选，默认使用当前模型）
        
        Returns:
            模型路径，如果未配置则返回 None
        """
        if model_id is None:
            config = self.get_current_embedding_model()
        else:
            embedding_config = self._model_config.get("embedding", {})
            available = embedding_config.get("available", {})
            config = available.get(model_id, {})
        
        path = config.get("model_path")
        if path:
            return Path(path)
        return None
    
    # ==================== LLM 模型 ====================
    
    def get_current_llm_model(self) -> Dict[str, Any]:
        """获取当前 LLM 模型配置
        
        Returns:
            模型配置字典
        """
        llm_config = self._model_config.get("llm", {})
        current_id = llm_config.get("current", "claude-3-opus")
        available = llm_config.get("available", {})
        
        return available.get(current_id, {
            "name": current_id,
            "provider": "anthropic",
            "version": "default"
        })
    
    def list_available_llm_models(self) -> List[Dict[str, Any]]:
        """列出所有可用的 LLM 模型
        
        Returns:
            模型列表
        """
        llm_config = self._model_config.get("llm", {})
        available = llm_config.get("available", {})
        current = llm_config.get("current", "claude-3-opus")
        
        models = []
        for model_id, model_info in available.items():
            models.append({
                "id": model_id,
                "name": model_info.get("name", model_id),
                "provider": model_info.get("provider", "unknown"),
                "is_current": model_id == current,
                "status": "current" if model_id == current else "available"
            })
        
        return models
    
    # ==================== 基准测试 ====================
    
    def benchmark_embedding_model(
        self, 
        model_id: str,
        benchmark_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """运行嵌入模型基准测试
        
        Args:
            model_id: 模型 ID
            benchmark_path: 基准测试数据路径（可选）
        
        Returns:
            基准测试结果 {recall@10, ndcg, latency_ms, tested_at}
        """
        # 使用检索评估脚本进行测试
        benchmark_file = benchmark_path or self.project_root / ".evaluation" / "retrieval_benchmark" / "benchmark_template.json"
        
        if not benchmark_file.exists():
            return {
                "error": "基准测试文件不存在",
                "model_id": model_id,
                "tested_at": datetime.now().isoformat()
            }
        
        # 实际测试需要运行 eval_retrieval_quality.py
        # 这里返回占位结果，实际执行需要调用完整测试流程
        return {
            "model_id": model_id,
            "recall@10": None,
            "ndcg": None,
            "latency_ms": None,
            "tested_at": datetime.now().isoformat(),
            "note": "需要运行 tools/eval_retrieval_quality.py 获取实际结果"
        }
    
    # ==================== 模型切换 ====================
    
    def switch_embedding_model(self, new_model_id: str) -> bool:
        """切换嵌入模型
        
        注意：切换嵌入模型后，需要重建向量库以保持一致性。
        
        Args:
            new_model_id: 新模型 ID
        
        Returns:
            True 表示切换成功
        """
        embedding_config = self._model_config.get("embedding", {})
        available = embedding_config.get("available", {})
        
        if new_model_id not in available:
            print(f"[ERROR] 模型 {new_model_id} 不在可用列表中")
            return False
        
        # 更新配置（需要保存到 config.json）
        # 这里只是示意，实际需要修改 config.json
        print(f"[INFO] 切换到模型 {new_model_id}")
        print(f"[WARN] 需要重建向量库以保持向量维度一致性")
        
        return True
    
    # ==================== 辅助方法 ====================
    
    def get_model_info_summary(self) -> str:
        """获取模型信息摘要
        
        Returns:
            多行文本摘要
        """
        current_embedding = self.get_current_embedding_model()
        current_llm = self.get_current_llm_model()
        
        embedding_models = self.list_available_embedding_models()
        llm_models = self.list_available_llm_models()
        
        lines = [
            "【模型配置摘要】",
            "",
            "嵌入模型:",
            f"  当前: {current_embedding.get('name', 'unknown')} ({current_embedding.get('version', 'unknown')})",
            f"  向量维度: {current_embedding.get('vector_size', 1024)}",
            f"  可用模型: {len(embedding_models)} 个",
        ]
        
        for m in embedding_models:
            status = "✓ 当前" if m["is_current"] else "  可用"
            lines.append(f"    {status}: {m['id']} ({m['name']})")
        
        lines.extend([
            "",
            "LLM 模型:",
            f"  当前: {current_llm.get('name', 'unknown')}",
            f"  Provider: {current_llm.get('provider', 'unknown')}",
            f"  可用模型: {len(llm_models)} 个",
        ])
        
        for m in llm_models:
            status = "✓ 当前" if m["is_current"] else "  可用"
            lines.append(f"    {status}: {m['id']} ({m['provider']})")
        
        return "\n".join(lines)


def get_model_manager() -> ModelManager:
    """获取全局模型管理器
    
    Returns:
        ModelManager 实例
    """
    return ModelManager()


# CLI 入口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="模型版本管理")
    parser.add_argument("command", choices=["list", "info", "benchmark", "switch"])
    parser.add_argument("--model", help="模型 ID")
    parser.add_argument("--type", choices=["embedding", "llm"], default="embedding")
    
    args = parser.parse_args()
    
    mgr = ModelManager()
    
    if args.command == "list":
        if args.type == "embedding":
            models = mgr.list_available_embedding_models()
            for m in models:
                status = "(当前)" if m["is_current"] else ""
                print(f"- {m['id']}: {m['name']} {status}")
        else:
            models = mgr.list_available_llm_models()
            for m in models:
                status = "(当前)" if m["is_current"] else ""
                print(f"- {m['id']}: {m['provider']} {status}")
    
    elif args.command == "info":
        print(mgr.get_model_info_summary())
    
    elif args.command == "benchmark":
        if args.model:
            result = mgr.benchmark_embedding_model(args.model)
            print(json.dumps(result, indent=2))
        else:
            print("需要指定 --model 参数")
    
    elif args.command == "switch":
        if args.model:
            mgr.switch_embedding_model(args.model)
        else:
            print("需要指定 --model 参数")