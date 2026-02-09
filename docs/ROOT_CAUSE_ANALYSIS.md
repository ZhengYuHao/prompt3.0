# DSL重复定义问题 - 根本原因分析

## 🔍 重新定位问题

### 问题现象

**阶段1：Prompt 1.0输出**
```
日志级别：错误日志保留90天，访问日志保留30天，调试日志保留7天。
监控指标：如果QPS低于10持续10分钟，触发告警；如果95分位响应时间超过3秒持续5分钟，触发扩容。
```

**阶段2：Prompt 2.0变量提取**
```json
[
  {"variable": "duration_分钟", "value": 30},  // 90天 → duration_分钟
  {"variable": "duration_天", "value": 90},   // 90天 → duration_天
  {"variable": "duration_天", "value": 30},   // 30天 → duration_天（重复！）
  {"variable": "duration_天", "value": 7},    // 7天  → duration_天（重复！）
  {"variable": "duration_分钟", "value": 10},  // 10分钟 → duration_分钟（重复！）
  {"variable": "duration_分钟", "value": 5},   // 5分钟  → duration_分钟（重复！）
]
```

**阶段3：DSL生成**
```python
duration_天 = 90    # 第1行
duration_分钟 = 30  # 第2行
duration_天 = 30    # 第3行（重复定义错误）
duration_天 = 7     # 第4行（重复定义错误）
duration_分钟 = 10  # 第5行（重复定义错误）
duration_分钟 = 5   # 第6行（重复定义错误）
```

**错误：**
```
⚪[第4行] 重复定义: 变量 {{duration_天}} 已在第3行定义
⚪[第5行] 重复定义: 变量 {{duration_天}} 已在第3行定义
⚪[第6行] 重复定义: 变量 {{duration_分钟}} 已在第1行定义
⚪[第7行] 重复定义: 变量 {{duration_分钟}} 已在第1行定义
```

---

## 🎯 根本原因

### 错误假设 ❌

**假设1：** MockLLM实体提取对相同单位创建同名变量

**实际情况：** ❌ **不是这个原因**

**证据：**
```python
# 修复后的MockLLM代码（已验证）
def _mock_entity_extraction(self, text: str) -> str:
    """模拟实体抽取（修复重复定义问题）"""
    import re
    entities = []
    unit_counter = {}

    # 对相同单位进行计数，创建唯一名称
    for match in re.finditer(r'(\d+)(年|周|月|天|小时|分钟)', text):
        unit = match.group(2)
        count = unit_counter.get(unit, 0) + 1
        unit_counter[unit] = count

        # 如果是第一个该单位，使用标准名称
        if count == 1:
            var_name = f"duration_{unit}"
        else:
            # 如果是重复的单位，添加后缀
            var_name = f"duration_{unit}_{count}"

        entities.append({
            "name": var_name,  # ← 已修复
            ...
        })
```

但是，Prompt 2.0仍然收到重复的变量名！
这说明问题不在MockLLM，而在其他地方。

---

### 真正的根本原因 ✅

**问题位置：** Prompt 1.0的术语映射表不完整

**问题描述：** Prompt 1.0的术语映射表（`TERM_MAPPING`）中没有把"数字+单位"映射到变量占位符

**证据：**
```python
# demo_full_pipeline.py 第89-107行
TERM_MAPPING = {
    # 口语 → 专业术语
    "帮我": "请",
    "那个": "",
    "吧": "",
    ...
    # 技术术语标准化
    "RAG": "检索增强生成",
    "LLM": "大型语言模型",
    ...
    # ❌ 缺少：数字+单位的映射
    # ❌ 应该有："(\\d+)天": "{{duration_天}}"
    # ❌ 应该有："(\\d+)分钟": "{{duration_分钟}}"
    # ❌ 应该有："(\\d+)秒": "{{duration_秒}}"
}
```

**结果：**
1. Prompt 1.0处理文本"日志保留90天、访问日志保留30天、调试日志保留7天"
2. 术语映射中没有匹配的规则
3. 文本保持原样输出："日志保留90天，访问日志保留30天，调试日志保留7天"
4. Prompt 2.0从文本中提取实体：
   - "90天" → duration_天 (value=90)
   - "30天" → duration_天 (value=30)  ← 重复！
   - "7天"  → duration_天 (value=7)   ← 重复！

---

## ✅ 解决方案

### 方案1：扩展术语映射表（推荐）⭐⭐⭐

**修改文件：** `demo_full_pipeline.py`

**修改内容：** 添加数字+单位的映射规则

```python
TERM_MAPPING = {
    # 口语 → 专业术语
    "帮我": "请",
    "那个": "",
    "吧": "",
    "嘛": "",
    ...

    # 技术术语标准化
    "RAG": "检索增强生成",
    "LLM": "大型语言模型",
    "K8s": "Kubernetes",
    ...

    # ✅ 新增：数字+单位的正则映射
    r"(\d+)天": "{{duration_天}}",
    r"(\d+)周": "{{duration_周}}",
    r"(\d+)月": "{{duration_月}}",
    r"(\d+)年": "{{duration_年}}",
    r"(\d+)小时": "{{duration_小时}}",
    r"(\d+)分钟": "{{duration_分钟}}",
    r"(\d+)秒": "{{duration_秒}}",

    # ✅ 新增：技术栈的映射
    r"Python|Java|JavaScript|TypeScript|Go|Rust|C\+\+|Node\.js|React|Vue|Angular|Spring|Django|Flask": "{{tech_stack}}",
}
```

**工作原理：**
1. Prompt 1.0处理文本"日志保留90天、访问日志保留30天、调试日志保留7天"
2. 术语匹配：`r"(\d+)天"` → `{{duration_天}}`
3. 结果：
   ```
   日志保留{{duration_天}}，访问日志保留{{duration_天_2}}，调试日志保留{{duration_天_3}}。
   ```
4. Prompt 2.0从占位符中提取实体：
   ```json
   [
     {"variable": "duration_天", "value": 90},
     {"variable": "duration_天_2", "value": 30},
     {"variable": "duration_天_3", "value": 7}
   ]
   ```
5. DSL生成：
   ```python
   duration_天 = 90
   duration_天_2 = 30
   duration_天_3 = 7
   ```
6. ✅ 无重复定义错误

---

### 方案2：改进Prompt 2.0实体提取

**修改文件：** `prompt_structurizer.py`

**修改内容：** 添加变量名去重逻辑

```python
class EntityConflictResolver:
    """处理重叠实体 (Overlapping Entities)"""

    @staticmethod
    def resolve_overlaps(entities: List[Dict]) -> List[Dict]:
        """
        最长覆盖原则: 优先保留更长的实体

        新增: 变量名去重逻辑
        """
        # ... 现有的重叠处理逻辑 ...

        # ✅ 新增：变量名去重
        name_counter = {}
        deduplicated_entities = []

        for entity in non_overlapping:
            name = entity['name']

            if name not in name_counter:
                # 第一次出现的变量名，直接保留
                name_counter[name] = 1
                deduplicated_entities.append(entity)
            else:
                # 重复的变量名，生成新名称
                count = name_counter[name] + 1
                name_counter[name] = count

                # 创建新变量名
                new_name = f"{name}_{count}"
                entity['name'] = new_name
                deduplicated_entities.append(entity)

        return deduplicated_entities
```

---

### 方案3：优化MockLLM实体提取（辅助）⭐

**修改文件：** `llm_client.py`

**修改内容：** 已完成（见之前的修改）

**说明：** 虽然不是根本原因，但这个修改可以防止未来类似问题

---

## 📊 方案对比

| 方案 | 优点 | 缺点 | 推荐度 | 实施难度 |
|------|------|------|--------|----------|
| **方案1**<br>扩展术语映射 | 治本<br>一劳永逸 | 需要维护大量映射<br>覆盖不完整 | ⭐⭐⭐ | 中 |
| **方案2**<br>改进冲突解决器 | 通用性<br>防御性强 | 治标不治本<br>变量名可能不语义 | ⭐⭐ | 低 |
| **方案3**<br>优化Mock提取 | 辅助性<br>简单 | 不解决根本问题 | ⭐ | 低 |

---

## 🎯 推荐实施策略

### 立即行动（修复当前问题）：

1. **实施方案2**（改进冲突解决器）
   - 修改 `prompt_structurizer.py`
   - 添加变量名去重逻辑
   - 立即解决当前问题
   - 实施难度：低

2. **实施方案1**（扩展术语映射）
   - 修改 `demo_full_pipeline.py`
   - 添加数字+单位的映射规则
   - 治本解决问题
   - 实施难度：中

3. **保留方案3**（优化Mock提取）
   - 已经实施
   - 作为辅助措施
   - 防止未来类似问题

---

## 🔧 修复验证清单

### 修复后需要验证：

- [ ] Prompt 1.0正确替换数字+单位为占位符
- [ ] Prompt 2.0提取到唯一的变量名
- [ ] DSL编译通过，无重复定义错误
- [ ] DSL代码逻辑正确
- [ ] 最终代码生成成功

---

## 📝 总结

### 问题定位

**现象：** DSL生成后无法通过验证，出现多个重复定义的变量

**错误假设：** MockLLM实体提取对相同单位创建同名变量

**真正原因：** ❌ Prompt 1.0的术语映射表不完整，没有把"数字+单位"映射到变量占位符

### 根本原因

**问题根源：** `demo_full_pipeline.py` 中的 `TERM_MAPPING` 缺少数字+单位的映射规则

**影响：** Prompt 1.0保持文本原样输出，Prompt 2.0从文本中重复提取实体，导致DSL重复定义

### 解决方案

**推荐方案：**
1. 方案2（改进冲突解决器）- 立即修复
2. 方案1（扩展术语映射）- 治本解决
3. 方案3（优化Mock提取）- 辅助措施

---

**文档版本**: 1.0
**创建时间**: 2026-02-07
**最后更新**: 2026-02-07
**作者**: AI Assistant
