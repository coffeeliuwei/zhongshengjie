# 链路 B · Skip 记录

**Skip 原因**：
- 自动模式无法接受 stdin 输入确认
- 链路 B 需真实 LLM API 调用（5 写手 + 1 鉴赏师，约 $0.1-1）
- 按 M5 计划 §1.4 规定，自动模式默认跳过链路 B

**后续补做建议**：
1. 用户手动确认运行链路 B
2. 或在交互模式下重新执行 M5 步骤 3.2
3. 命令示例：
   ```bash
   python -m core create --workflow  # 列可用场景
   python -m core create --scene "<场景类型>" --chapter "M5验证_$(date +%Y%m%d_%H%M)"
   ```

**状态**：skip（非失败）