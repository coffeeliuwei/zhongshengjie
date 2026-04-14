# ADR-004: 模块间通信与依赖规则

## 状态
提议

## 上下文

当前core/目录下有39个Python文件，分布在6个子目录中。模块间存在以下问题：

1. 部分模块间的导入关系不够清晰
2. 配置加载存在两套实现（已部分统一）
3. 模块边界没有强制约束

## 决策

制定以下模块间通信和依赖规则：

### 依赖方向规则

```
Conversation → Creation → Retrieval
Conversation → Evaluation → Retrieval
Data → Retrieval
所有模块 → Shared
```

**禁止**：
- 反向依赖（如Retrieval依赖Creation）
- 跨层依赖（如Conversation直接依赖Data）
- 循环依赖（A→B→A）

### 通信方式规则

| 通信类型 | 方式 | 场景 |
|----------|------|------|
| 同步请求 | 函数/方法调用 | 创作调度检索 |
| 异步通知 | 事件发布/订阅 | 数据变更通知 |
| 数据共享 | 共享内核(Shared) | 通用类型定义 |

### 共享内核内容

shared/目录只允许包含：
- 通用类型定义（Dimension, Phase, SceneType等枚举）
- 通用工具函数（日志、序列化）
- 接口定义（Repository接口、Plugin接口）
- 配置加载器

**禁止**在shared中放置业务逻辑。

### 强制检查

使用import-linter工具在CI中检查依赖规则：

```ini
[importlinter:contract]
name = Conversation must not depend on Data
type = independence
modules =
    core.conversation
    core.data

[importlinter:contract]
name = No circular imports
type = layers
layers =
    core.conversation
    core.creation | core.evaluation
    core.retrieval
    core.data
    core.shared
```

## 后果

### 积极的

1. 模块边界清晰，修改一个模块不会意外影响其他模块
2. 可以独立测试每个模块
3. 未来拆分为微服务时有明确的接口边界

### 消极的

1. 增加开发约束，有时需要绕路调用
2. 需要维护import-linter配置
3. 初期重构工作量较大
