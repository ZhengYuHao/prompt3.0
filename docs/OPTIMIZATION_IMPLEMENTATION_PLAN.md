# 极窄化LLM优化实施计划

## 📋 优化点总览

| 优先级 | 优化点 | 预期收益 | 实施难度 | 预计时间 |
|--------|--------|----------|----------|----------|
| P0 | 优化点1：Prompt 1.0 规则化 | LLM调用减少100% | 低 | 2-3天 |
| P0 | 优化点2：实体提取优化 | Token消耗降低60-70% | 中 | 3-4天 |
| P0 | 优化点5：缓存机制 | 速度提升100-1000x | 低 | 1-2天 |
| P1 | 优化点3：DSL 转译优化 | LLM使用率降低70% | 中 | 4-5天 |
| P1 | 优化点6：代码层验证覆盖度 | 确定性提升 | 中 | 2-3天 |
| P2 | 优化点4：自动修复增强 | LLM重试减少50-70% | 高 | 5-7天 |

---

## 🎯 P0阶段：高优先级优化（1-2周）

### 优化点1：Prompt 1.0 规则化

#### 目标
- 将 `prompt_preprocessor.py` 中的 LLM 语义重构替换为规则引擎
- LLM 调用次数：2次 → 0次
- 处理速度：提升10-100倍

#### 实施步骤

**步骤1.1：创建规则引擎模块**
```bash
touch /mnt/e/pyProject/prompt3.0/rule_based_normalizer.py
```

**文件内容：** 见下方 `rule_based_normalizer.py`

**步骤1.2：修改 `prompt_preprocessor.py`**
```python
# 第1行后添加导入
from rule_based_normalizer import RuleBasedTextNormalizer, SyntacticAmbiguityDetector

# 修改 _smooth_with_llm 方法（约第163行）
def _smooth_with_llm(self, text: str) -> str:
    """【规则操作】受限语义重构"""
    # 使用规则引擎替代 LLM
    normalized_text, changes = RuleBasedTextNormalizer.normalize(text)

    # 记录变更
    for change in changes:
        self.steps_log.append(f"✓ {change}")

    return normalized_text

# 修改 _detect_ambiguity 方法（约第195行）
def _detect_ambiguity(self, text: str) -> Optional[str]:
    """【规则操作】检测结构歧义"""
    # 使用句法分析器替代 LLM
    return SyntacticAmbiguityDetector.detect(text)
```

**步骤1.3：更新历史记录数据模型**

在 `history_manager.py` 的 `ProcessingHistory` 类中添加字段：
```python
@dataclass
class ProcessingHistory:
    # ... 现有字段 ...

    # 新增：规则引擎统计
    rule_engine_stats: Dict[str, Any] = field(default_factory=dict)
    # {
    #   "normalization_changes": 5,  # 规范化变更次数
    #   "ambiguity_detected": false,
    #   "llm_calls": 0,  # Prompt 1.0 阶段的 LLM 调用次数
    # }
```

**步骤1.4：在 `prompt_preprocessor.py` 中收集统计信息**

```python
def process(self, text: str) -> Dict[str, Any]:
    """处理文本（主入口）"""
    # ... 现有代码 ...

    # 统计信息
    stats = {
        "normalization_changes": len(changes),
        "ambiguity_detected": ambiguity_result is not None,
        "llm_calls": 0,  # 现在不再调用 LLM
        "processing_mode": "rule_based"  # 标记为规则引擎模式
    }

    # 保存到历史记录
    history.processing_time_ms = int(end_time * 1000)
    history.rule_engine_stats = stats  # 新增

    return {
        "success": ambiguity_result is None,
        "processed_text": smoothed_text,
        "mode": mode,
        "stats": stats  # 新增
    }
```

**步骤1.5：在 `view_history.py` 中添加可视化支持**

```python
def show_optimization_metrics(pipeline_id: str):
    """显示优化指标"""
    manager = HistoryManager()
    history = manager.load_pipeline_history(pipeline_id)

    if not history:
        info(f"未找到流水线 ID 为 {pipeline_id} 的记录")
        return

    info(f"\n{'='*90}")
    info(f"优化指标 - 流水线 {pipeline_id}")
    info(f"{'='*90}")

    # Prompt 1.0 优化指标
    if hasattr(history, 'prompt10_rule_stats') and history.prompt10_rule_stats:
        stats = history.prompt10_rule_stats
        info(f"\n【Prompt 1.0 规则化效果】")
        info(f"  处理模式: {stats.get('processing_mode', 'unknown')}")
        info(f"  LLM 调用次数: {stats.get('llm_calls', 0)}")
        info(f"  规范化变更: {stats.get('normalization_changes', 0)} 次")
        info(f"  歧义检测: {'是 ⚠️' if stats.get('ambiguity_detected') else '否 ✅'}")

    # Prompt 2.0 优化指标
    if hasattr(history, 'prompt20_optimization_stats'):
        # ... 见步骤2.6

    # 总体优化效果
    total_llm_calls = (
        history.prompt10_rule_stats.get('llm_calls', 0) if hasattr(history, 'prompt10_rule_stats') else 0 +
        history.prompt20_optimization_stats.get('llm_calls', 0) if hasattr(history, 'prompt20_optimization_stats') else 0 +
        history.prompt30_optimization_stats.get('llm_calls', 0) if hasattr(history, 'prompt30_optimization_stats') else 0
    )
    info(f"\n【总体优化效果】")
    info(f"  总 LLM 调用次数: {total_llm_calls}")
    info(f"  预估成本节省: {(4 - total_llm_calls) / 4 * 100:.1f}%")
    info(f"  处理速度提升: {self._calculate_speedup(history):.1f}x")
```

**预期效果：**
- ✅ LLM 调用：2次 → 0次
- ✅ 处理速度：2-4秒 → 0.05-0.2秒
- ✅ 成本：降低100%
- ✅ 可视化：在 view_history.py 中可查看优化指标

---

### 优化点2：实体提取优化

#### 目标
- 使用正则预处理 + 极简 Prompt
- Token 消耗降低 60-70%
- 正则模式 100% 准确

#### 实施步骤

**步骤2.1：创建正则提取模块**
```bash
touch /mnt/e/pyProject/prompt3.0/pre_pattern_extractor.py
```

**文件内容：** 见下方 `pre_pattern_extractor.py`

**步骤2.2：修改 `llm_client.py` 的 `extract_entities` 方法**

```python
# 添加导入
from pre_pattern_extractor import PrePatternExtractor

def extract_entities(self, text: str) -> List[Dict[str, Any]]:
    """优化的实体抽取（极窄化LLM）"""

    # 步骤1：正则预处理
    regex_entities = PrePatternExtractor.extract(text)

    # 如果正则提取足够（比如提取了3+个实体），直接返回
    if len(regex_entities) >= 3:
        debug(f"[实体提取] 正则提取成功，提取 {len(regex_entities)} 个实体，跳过 LLM")
        return regex_entities

    # 步骤2：使用极简 Prompt
    system_prompt = """从文本中提取可配置的参数变量。

规则：
- 提取具体数字、时间值（如：3年、5人、50万、2周）
- 提取技术选项（如：Python/Java、Milvus/Pinecone）
- 不提取固定需求描述（如：需要支持、用大模型做底座）
- 不提取架构描述（如：微服务架构）

输出JSON数组：
[{"name": "变量名", "original_text": "原文", "start_index": 起始位置, "end_index": 结束位置, "type": "类型", "value": "值"}]

示例：
输入: "项目5个人，周期2周，用LangChain和Milvus"
输出: [{"name": "team_size", "original_text": "5个人", "start_index": 2, "end_index": 6, "type": "Integer", "value": 5}, {"name": "duration_weeks", "original_text": "2周", "start_index": 9, "end_index": 11, "type": "Integer", "value": 2}, {"name": "tech_stack", "original_text": "LangChain和Milvus", "start_index": 16, "end_index": 29, "type": "List", "value": ["LangChain", "Milvus"]}]"""

    response = self.call(system_prompt, text, temperature=0.1)
    llm_entities = self._parse_entities(response.content, text)

    # 步骤3：合并结果（正则优先）
    merged_entities = PrePatternExtractor.merge_with_llm(regex_entities, llm_entities)

    # 收集统计信息
    stats = {
        "regex_count": len(regex_entities),
        "llm_count": len(llm_entities),
        "merged_count": len(merged_entities),
        "llm_called": len(regex_entities) < 3
    }

    debug(f"[实体提取] 统计: {stats}")

    return merged_entities, stats  # 返回统计信息
```

**步骤2.3：更新 `Prompt20History` 数据模型**

在 `history_manager.py` 中添加字段：
```python
@dataclass
class Prompt20History:
    # ... 现有字段 ...

    # 新增：优化统计
    optimization_stats: Dict[str, Any] = field(default_factory=dict)
    # {
    #   "regex_count": 5,  # 正则提取数量
    #   "llm_count": 2,   # LLM 提取数量
    #   "merged_count": 7,  # 合并后数量
    #   "llm_called": false  # 是否调用了 LLM
    # }
```

**步骤2.4：在 `prompt_structurizer.py` 中保存统计信息**

```python
def process(self, input_text: str, prompt10_id: str) -> Dict[str, Any]:
    """结构化处理（主入口）"""

    # 提取实体（带统计信息）
    entities, stats = self.llm.extract_entities(input_text)

    # ... 现有处理逻辑 ...

    # 保存历史记录
    history = Prompt20History(
        id=self.history_manager._generate_id(),
        timestamp=datetime.now().isoformat(),
        source_prompt10_id=prompt10_id,
        input_text=input_text,
        template_text=template,
        variables=variables,
        variable_count=len(variables),
        type_stats=type_stats,
        extraction_log=self.steps_log,
        processing_time_ms=int((end_time - start_time) * 1000),
        optimization_stats=stats  # 新增
    )

    return {
        "id": history.id,
        "variables": variables,
        "template": template,
        "stats": stats  # 新增
    }
```

**步骤2.5：在 `PipelineHistory` 中添加字段**

```python
@dataclass
class PipelineHistory:
    # ... 现有字段 ...

    # Prompt 2.0 优化统计
    prompt20_optimization_stats: Dict[str, Any] = field(default_factory=dict)
```

**步骤2.6：在 `view_history.py` 中添加可视化支持**

```python
def show_optimization_metrics(pipeline_id: str):
    """显示优化指标（步骤1.5的扩展）"""
    # ... 步骤1.5的代码 ...

    # Prompt 2.0 优化指标
    if history.prompt20_optimization_stats:
        stats = history.prompt20_optimization_stats
        info(f"\n【Prompt 2.0 实体提取优化】")
        info(f"  正则提取: {stats.get('regex_count', 0)} 个")
        info(f"  LLM 提取: {stats.get('llm_count', 0)} 个")
        info(f"  合并结果: {stats.get('merged_count', 0)} 个")
        info(f"  调用 LLM: {'是' if stats.get('llm_called') else '否 ✅'}")

        if not stats.get('llm_called'):
            info(f"  ⚡ Token 节省: ~1000 tokens")
```

**预期效果：**
- ✅ Token 消耗：降低 60-70%
- ✅ 正则提取：100% 准确
- ✅ LLM 调用：50% → 0%（常见case）
- ✅ 可视化：清晰展示正则 vs LLM 的贡献

---

### 优化点5：缓存机制

#### 目标
- 避免重复 LLM 调用
- 重复请求速度提升 100-1000倍
- 成本降低 30-50%

#### 实施步骤

**步骤5.1：创建缓存模块**
```bash
touch /mnt/e/pyProject/prompt3.0/cached_llm_client.py
```

**文件内容：** 见下方 `cached_llm_client.py`

**步骤5.2：修改 `llm_client.py` 的 `UnifiedLLMClient`**

```python
# 添加导入
from cached_llm_client import CachedLLMClient

# 在 __init__ 方法中（约第50行）
def __init__(self, use_mock: bool = False, enable_cache: bool = True):
    # ... 现有代码 ...

    # 添加缓存选项
    self.enable_cache = enable_cache
    if enable_cache:
        self.cache_client = CachedLLMClient(self)
    else:
        self.cache_client = None

# 修改 call 方法（约第150行）
def call(self, system_prompt: str, user_content: str, **kwargs) -> LLMResponse:
    """调用 LLM（带缓存）"""

    if self.enable_cache and self.cache_client:
        # 使用缓存客户端
        return self.cache_client.call(system_prompt, user_content, **kwargs)
    else:
        # 直接调用
        return self._call_without_cache(system_prompt, user_content, **kwargs)

def _call_without_cache(self, system_prompt: str, user_content: str, **kwargs) -> LLMResponse:
    """不使用缓存的调用"""
    # ... 原有调用逻辑 ...
```

**步骤5.3：更新历史记录数据模型**

在 `ProcessingHistory`, `Prompt20History`, `PipelineHistory` 中添加字段：
```python
@dataclass
class ProcessingHistory:
    # ... 现有字段 ...
    cache_hit: bool = False  # 是否命中缓存
```

```python
@dataclass
class Prompt20History:
    # ... 现有字段 ...
    cache_hits: int = 0  # 缓存命中次数
    cache_misses: int = 0  # 缓存未命中次数
```

```python
@dataclass
class PipelineHistory:
    # ... 现有字段 ...

    # 缓存统计
    total_cache_hits: int = 0
    total_cache_misses: int = 0
    cache_hit_rate: float = 0.0
```

**步骤5.4：在 `cached_llm_client.py` 中收集统计信息**

```python
class CachedLLMClient:
    def __init__(self, base_client: UnifiedLLMClient, cache_size: int = 1000):
        self.base_client = base_client
        self.cache_size = cache_size
        self.hits = 0
        self.misses = 0

    def call(self, system_prompt: str, user_content: str, **kwargs) -> LLMResponse:
        """调用（带缓存）"""
        cache_key = self._make_cache_key(system_prompt, user_content)

        # 检查缓存
        cache_file = f".cache/llm_{cache_key}.json"
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                    self.hits += 1
                    debug(f"[缓存] 命中: {cache_key[:16]}...")
                    return LLMResponse(**cached, from_cache=True)  # 标记来自缓存
        except Exception:
            pass

        # 调用 LLM
        self.misses += 1
        response = self.base_client.call(system_prompt, user_content, **kwargs)

        # 保存到缓存
        try:
            os.makedirs('.cache', exist_ok=True)
            with open(cache_file, 'w') as f:
                json.dump({
                    'content': response.content,
                    'model': response.model,
                    'usage': response.usage
                }, f)
        except Exception:
            pass

        return response

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total > 0 else 0.0
        }
```

**步骤5.5：在 `view_history.py` 中添加可视化支持**

```python
def show_cache_stats(pipeline_id: str = None):
    """显示缓存统计"""
    manager = HistoryManager()

    if pipeline_id:
        history = manager.load_pipeline_history(pipeline_id)
    else:
        histories = manager.get_recent_pipeline_history(limit=10)
        if not histories:
            info("暂无流水线处理历史记录")
            return
        history = histories[0]

    if not history:
        return

    info(f"\n{'='*90}")
    info(f"缓存统计 - 流水线 {history.pipeline_id}")
    info(f"{'='*90}")

    hits = history.total_cache_hits or 0
    misses = history.total_cache_misses or 0
    total = hits + misses
    hit_rate = history.cache_hit_rate or 0.0

    info(f"  缓存命中: {hits} 次")
    info(f"  缓存未命中: {misses} 次")
    info(f"  总调用: {total} 次")
    info(f"  命中率: {hit_rate*100:.1f}%")

    if total > 0:
        saved_tokens = hits * 500  # 估算每次调用节省 500 tokens
        saved_cost = saved_tokens * 0.001 / 1000  # 估算成本
        info(f"\n  ⚡ 节省 Token: ~{saved_tokens} tokens")
        info(f"  💰 节省成本: ~${saved_cost:.4f}")
```

**预期效果：**
- ✅ 重复请求速度提升 100-1000x
- ✅ 成本降低 30-50%
- ✅ 可视化：清晰展示缓存命中率和节省效果

---

## 🔧 P1阶段：中优先级优化（2-3周）

### 优化点3：DSL 转译优化

#### 目标
- 代码主导 DSL 构建（70%）
- Prompt 长度降低 80%
- LLM 使用率降低 70%

#### 实施步骤

**步骤3.1：创建 DSL 构建器**
```bash
touch /mnt/e/pyProject/prompt3.0/dsl_builder.py
```

**文件内容：** 见下方 `dsl_builder.py`

**步骤3.2：修改 `prompt_dslcompiler.py`**

```python
# 添加导入
from dsl_builder import DSLBuilder

# 修改 compile 方法（约第300行）
def compile(self, template: str, variables: List[Dict]) -> Dict[str, Any]:
    """编译 DSL（优化版）"""

    start_time = time.time()

    # 步骤1：尝试用代码构建
    try:
        dsl_code = DSLBuilder.build_from_variables(variables, template)
        debug(f"[DSL编译] 代码构建成功")

        # 验证
        result = self.validator.validate(dsl_code)
        if result.is_valid:
            end_time = time.time()
            return {
                "success": True,
                "dsl_code": dsl_code,
                "validation_result": result,
                "llm_called": False,  # 未调用 LLM
                "compile_time_ms": int((end_time - start_time) * 1000)
            }
    except Exception as e:
        debug(f"[DSL编译] 代码构建失败: {e}")

    # 步骤2：回退到 LLM
    debug(f"[DSL编译] 回退到 LLM")
    return self._compile_with_llm(template, variables, start_time)
```

**步骤3.3：更新历史记录数据模型**

```python
@dataclass
class PipelineHistory:
    # ... 现有字段 ...

    # Prompt 3.0 优化统计
    prompt30_optimization_stats: Dict[str, Any] = field(default_factory=dict)
    # {
    #   "code_build": True,  # 是否使用代码构建
    #   "llm_fallback": False,  # 是否回退到 LLM
    #   "compile_time_ms": 1500,  # 编译耗时
    #   "llm_calls": 0  # LLM 调用次数
    # }
```

**步骤3.4：在 `view_history.py` 中添加可视化支持**

```python
def show_optimization_metrics(pipeline_id: str):
    """显示优化指标（步骤1.5的扩展）"""
    # ... 步骤1.5和2.6的代码 ...

    # Prompt 3.0 优化指标
    if history.prompt30_optimization_stats:
        stats = history.prompt30_optimization_stats
        info(f"\n【Prompt 3.0 DSL 编译优化】")
        info(f"  代码构建: {'成功 ✅' if stats.get('code_build') else '失败'}")
        info(f"  LLM 回退: {'是' if stats.get('llm_fallback') else '否 ✅'}")
        info(f"  LLM 调用: {stats.get('llm_calls', 0)} 次")
        info(f"  编译耗时: {stats.get('compile_time_ms', 0)} ms")

        if not stats.get('llm_fallback'):
            info(f"  ⚡ Token 节省: ~1500 tokens")
            info(f"  ⚡ 速度提升: ~3-5x")
```

**预期效果：**
- ✅ Token 消耗：降低 80%
- ✅ LLM 使用率：降低 70%
- ✅ 编译速度：提升 3-5倍
- ✅ 可视化：展示代码构建 vs LLM 的对比

---

### 优化点6：代码层验证覆盖度

#### 目标
- 增加验证规则覆盖
- 提升代码层修复能力
- 减少不必要的 LLM 重试

#### 实施步骤

**步骤6.1：创建增强验证模块**
```bash
touch /mnt/e/pyProject/prompt3.0/enhanced_validator.py
```

**文件内容：** 见下方 `enhanced_validator.py`

**步骤6.2：集成到现有验证流程**

```python
# 在 prompt_dslcompiler.py 中
from enhanced_validator import CodeLayerValidationSuite

def _validate_with_enhanced_rules(self, dsl_code: str, variables: List[Dict]) -> ValidationResult:
    """使用增强规则验证"""
    # 1. 模板填充验证
    is_valid, errors = CodeLayerValidationSuite.validate_template_filling(dsl_code, variables)

    # 2. 变量命名验证
    is_valid, name_errors = CodeLayerValidationSuite.validate_variable_naming(variables)

    # 3. 变量类型验证
    is_valid, type_errors = CodeLayerValidationSuite.validate_variable_types(variables)

    # 合并错误
    all_errors = errors + name_errors + type_errors

    return ValidationResult(
        is_valid=len(all_errors) == 0,
        errors=[ValidationError(line=0, error_type="增强验证", message=err) for err in all_errors]
    )
```

**步骤6.3：更新历史记录数据模型**

```python
@dataclass
class PipelineHistory:
    # ... 现有字段 ...

    # 验证统计
    validation_stats: Dict[str, Any] = field(default_factory=dict)
    # {
    #   "template_filling_errors": 0,
    #   "variable_naming_errors": 0,
    #   "variable_type_errors": 0,
    #   "total_validation_time_ms": 50
    # }
```

**步骤6.4：在 `view_history.py` 中添加可视化支持**

```python
def show_validation_details(pipeline_id: str):
    """显示验证详情"""
    manager = HistoryManager()
    history = manager.load_pipeline_history(pipeline_id)

    if not history:
        return

    info(f"\n{'='*90}")
    info(f"验证详情 - 流水线 {history.pipeline_id}")
    info(f"{'='*90}")

    if history.validation_stats:
        stats = history.validation_stats
        info(f"  模板填充错误: {stats.get('template_filling_errors', 0)}")
        info(f"  变量命名错误: {stats.get('variable_naming_errors', 0)}")
        info(f"  变量类型错误: {stats.get('variable_type_errors', 0)}")
        info(f"  验证耗时: {stats.get('total_validation_time_ms', 0)} ms")
```

**预期效果：**
- ✅ 验证覆盖度：提升 50%
- ✅ 早期错误发现：提升 30%
- ✅ 可视化：清晰展示各类验证错误

---

## 🚀 P2阶段：低优先级优化（长期）

### 优化点4：自动修复增强

#### 目标
- 增强代码层修复能力
- LLM 重试减少 50-70%
- 自动修复成功率提升到 70-80%

#### 实施步骤

**步骤4.1：创建增强自动修复模块**
```bash
touch /mnt/e/pyProject/prompt3.0/enhanced_auto_fixer.py
```

**文件内容：** 见下方 `enhanced_auto_fixer.py`

**步骤4.2：集成智能重试策略**

```python
# 在 prompt_dslcompiler.py 中
from enhanced_auto_fixer import EnhancedDSLAutoFixer, SmartRetryStrategy

def _auto_fix_syntax_errors(self, dsl_code: str, errors: List[ValidationError]) -> Tuple[str, int]:
    """自动修复语法错误（增强版）"""
    return EnhancedDSLAutoFixer.fix(dsl_code, errors)

def _should_retry_with_llm(self, result: ValidationResult) -> bool:
    """判断是否需要 LLM 重试"""
    should_retry, reason = SmartRetryStrategy.should_retry_with_llm(result)
    debug(f"[重试策略] {reason}")
    return should_retry
```

**步骤4.3：更新历史记录数据模型**

```python
@dataclass
class PipelineHistory:
    # ... 现有字段 ...

    # 自动修复统计
    auto_fix_stats: Dict[str, Any] = field(default_factory=dict)
    # {
    #   "total_fixes": 5,  # 总修复次数
    #   "syntax_errors_fixed": 3,  # 语法错误修复
    #   "undefined_vars_fixed": 2,  # 未定义变量修复
    #   "fix_success_rate": 0.8  # 修复成功率
    # }
```

**步骤4.4：在 `view_history.py` 中添加可视化支持**

```python
def show_auto_fix_stats(pipeline_id: str):
    """显示自动修复统计"""
    manager = HistoryManager()
    history = manager.load_pipeline_history(pipeline_id)

    if not history:
        return

    info(f"\n{'='*90}")
    info(f"自动修复统计 - 流水线 {history.pipeline_id}")
    info(f"{'='*90}")

    if history.auto_fix_stats:
        stats = history.auto_fix_stats
        info(f"  总修复次数: {stats.get('total_fixes', 0)}")
        info(f"  语法错误修复: {stats.get('syntax_errors_fixed', 0)}")
        info(f"  未定义变量修复: {stats.get('undefined_vars_fixed', 0)}")
        info(f"  控制流修复: {stats.get('control_flow_fixed', 0)}")
        info(f"  修复成功率: {stats.get('fix_success_rate', 0)*100:.1f}%")
```

**预期效果：**
- ✅ LLM 重试：减少 50-70%
- ✅ 自动修复成功率：提升到 70-80%
- ✅ 可视化：展示各类修复的统计

---

## 📊 持久化数据汇总

### history_manager.py 需要添加的字段

```python
@dataclass
class ProcessingHistory:
    # ... 现有字段 ...
    rule_engine_stats: Dict[str, Any] = field(default_factory=dict)
    cache_hit: bool = False

@dataclass
class Prompt20History:
    # ... 现有字段 ...
    optimization_stats: Dict[str, Any] = field(default_factory=dict)
    cache_hits: int = 0
    cache_misses: int = 0

@dataclass
class PipelineHistory:
    # ... 现有字段 ...
    prompt10_rule_stats: Dict[str, Any] = field(default_factory=dict)
    prompt20_optimization_stats: Dict[str, Any] = field(default_factory=dict)
    prompt30_optimization_stats: Dict[str, Any] = field(default_factory=dict)
    total_cache_hits: int = 0
    total_cache_misses: int = 0
    cache_hit_rate: float = 0.0
    validation_stats: Dict[str, Any] = field(default_factory=dict)
    auto_fix_stats: Dict[str, Any] = field(default_factory=dict)
```

### view_history.py 需要添加的命令

```python
# 新增命令：
# python view_history.py metrics <pipeline_id>           # 显示所有优化指标
# python view_history.py cache-stats <pipeline_id>       # 显示缓存统计
# python view_history.py validation <pipeline_id>        # 显示验证详情
# python view_history.py auto-fix <pipeline_id>          # 显示自动修复统计
# python view_history.py compare <pipeline_id1> <pipeline_id2>  # 对比优化效果
```

---

## 🎯 实施时间表

### 第1周：P0阶段
- Day 1-3: 优化点1（Prompt 1.0 规则化）
- Day 4-7: 优化点2（实体提取优化）

### 第2周：P0阶段 + P1阶段
- Day 8-9: 优化点5（缓存机制）
- Day 10-14: 优化点3（DSL 转译优化）

### 第3周：P1阶段
- Day 15-17: 优化点6（代码层验证覆盖度）
- Day 18-21: 测试、调试、文档

### 第4-5周：P2阶段（可选）
- Day 22-28: 优化点4（自动修复增强）
- Day 29-35: 全面测试、性能优化

---

## ✅ 验收标准

### 功能验收
- [ ] P0优化全部实施完成
- [ ] 所有新增字段正确持久化
- [ ] view_history.py 支持所有新增命令
- [ ] 缓存命中率 > 30%（重复场景）
- [ ] LLM 调用次数减少 > 50%

### 性能验收
- [ ] 标准需求处理速度提升 > 2倍
- [ ] Token 消耗降低 > 60%
- [ ] 自动修复成功率 > 70%

### 可视化验收
- [ ] 优化指标清晰展示
- [ ] 缓存统计准确显示
- [ ] 对比功能正常工作

---

## 📝 注意事项

1. **向后兼容**：所有新增字段使用 `field(default_factory=dict)` 确保向后兼容
2. **数据迁移**：旧的历史记录不会有新增字段，需要在代码中做判空处理
3. **缓存清理**：缓存文件存储在 `.cache/` 目录，建议定期清理
4. **A/B测试**：建议保留原版本的代码，进行A/B测试对比
5. **监控告警**：新增优化指标后，需要监控是否出现异常下降

---

## 🚀 下一步行动

1. ✅ 立即开始实施优化点1（最简单，效果最明显）
2. ✅ 创建所有新模块的基础框架
3. ✅ 在 view_history.py 中添加统计展示功能
4. ✅ 逐步集成各个优化点
5. ✅ 建立A/B测试框架
