# ADR-003: 插件化扩展机制

## 状态
提议

## 上下文

当前系统扩展新功能需要修改多处代码。典型场景：

1. 新增作家Agent：需修改场景映射配置、创作调度逻辑、评估维度定义
2. 新增评估维度：需修改评估器、技法库维度映射、案例库过滤规则
3. 新增检索源：需修改统一检索API、结果合并逻辑

每次扩展都涉及多文件修改，耦合度高，容易遗漏。

## 决策

设计插件化扩展机制，核心接口包括：

### WriterPlugin - 作家插件

```python
class WriterPlugin(ABC):
    @property
    @abstractmethod
    def id(self) -> str: ...
    
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    @abstractmethod
    def specialty(self) -> List[Dimension]: ...
    
    @property
    @abstractmethod
    def phase_preference(self) -> Phase: ...
    
    @abstractmethod
    def compose(self, context: CompositionContext) -> str: ...
    
    def get_technique_dimension(self) -> Dimension:
        """默认返回专长的主维度"""
        return self.specialty[0]
```

### EvaluationPlugin - 评估插件

```python
class EvaluationPlugin(ABC):
    @property
    @abstractmethod
    def dimension(self) -> Dimension: ...
    
    @abstractmethod
    def evaluate(self, content: str, context: EvalContext) -> Score: ...
    
    @abstractmethod
    def get_constraints(self) -> List[Constraint]: ...
```

### RetrievalPlugin - 检索插件

```python
class RetrievalPlugin(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str: ...
    
    @abstractmethod
    def search(self, query: str, filters: Dict, top_k: int) -> List[Result]: ...
    
    def merge_results(self, existing: List[Result], new: List[Result]) -> List[Result]:
        """默认合并策略：按相似度排序去重"""
        ...
```

### 插件注册机制

```python
class PluginRegistry:
    _writers: Dict[str, WriterPlugin] = {}
    _evaluators: Dict[str, EvaluationPlugin] = {}
    _retrievers: Dict[str, RetrievalPlugin] = {}
    
    def register_writer(self, plugin: WriterPlugin): ...
    def register_evaluator(self, plugin: EvaluationPlugin): ...
    def register_retriever(self, plugin: RetrievalPlugin): ...
    
    def get_writer(self, writer_id: str) -> WriterPlugin: ...
    def get_evaluator(self, dimension: Dimension) -> EvaluationPlugin: ...
    def get_retrievers(self) -> List[RetrievalPlugin]: ...
```

## 后果

### 积极的

1. 新增作家只需实现WriterPlugin接口并注册
2. 新增评估维度只需实现EvaluationPlugin
3. 第三方可以开发自己的插件
4. 测试可以mock插件，隔离测试

### 消极的

1. 接口设计需要足够抽象，避免频繁变更
2. 插件间交互需要明确的通信协议
3. 插件版本管理增加复杂度

## 实施步骤

1. Phase 1: 定义核心接口（WriterPlugin优先）
2. Phase 2: 将现有5位作家迁移为插件实现
3. Phase 3: 实现EvaluationPlugin接口
4. Phase 4: 实现RetrievalPlugin接口
5. Phase 5: 文档化插件开发指南
