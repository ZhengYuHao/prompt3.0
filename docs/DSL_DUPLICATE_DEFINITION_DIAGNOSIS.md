# DSL重复定义问题诊断报告

## 🔍 问题描述

**现象：** DSL生成后无法通过验证，出现多个重复定义的变量。

**错误信息：**
```
⚪[第4行] 重复定义: 变量 {{duration_天}} 已在第3行定义
⚪[第5行] 重复定义: 变量 {{duration_天}} 已在第3行定义
⚪[第6行] 重复定义: 变量 {{duration_分钟}} 已在第1行定义
⚪[第7行] 重复定义: 变量 {{duration_分钟}} 已在第1行定义
```

**问题文本：**
```
日志级别：错误日志保留90天，访问日志保留30天，调试日志保留7天。
监控指标：如果QPS低于10持续10分钟，触发告警；如果95分位响应时间超过3秒持续5分钟，触发扩容。
```

**变量提取结果：**
- "90天" → duration_天 (第1行)
- "30天" → duration_天 (第3行)
- "7天" → duration_天 (第4行)
- "10分钟" → duration_分钟 (第1行)
- "5分钟" → duration_分钟 (第6行)
- "2秒" → duration_秒 (单独定义)

**问题：** 相同单位的duration变量创建了多个同名变量，导致DSL中重复定义。

---

## 🔎 根本原因分析

### 问题位置：`llm_client.py` 第614-628行

```python
def _mock_entity_extraction(self, text: str) -> str:
    """模拟实体抽取"""
    import re
    entities = []
    
    # 识别数字+单位模式
    for match in re.finditer(r'(\d+)(年|周|月|天|小时|分钟)', text):
        entities.append({
            "name": f"duration_{match.group(2)}",  # ← 问题：相同单位创建同名变量
            "original_text": match.group(0),
            "start_index": match.start(),
            "end_index": match.end(),
            "type": "Integer",
            "value": int(match.group(1))
        })
    
    return json.dumps(entities, ensure_ascii=False)
```

### 问题根源：

**正则表达式匹配所有数字+单位模式**，但对于相同单位（如"天"），每次匹配都创建同名变量`duration_天`。

**示例：**
```python
文本: "日志保留90天，访问日志保留30天，调试日志保留7天"

匹配结果:
1. "90天" → {"name": "duration_天", "value": 90}
2. "30天" → {"name": "duration_天", "value": 30}  # ← 重复
3. "7天"  → {"name": "duration_天", "value": 7}   # ← 重复

结果: 3个同名变量 duration_天，导致DSL重复定义错误
```

---

## ✅ 解决方案

### 方案1：修复Mock实体提取（推荐）⭐

**修改文件：** `llm_client.py`

**修改内容：** 对于相同单位的duration变量，创建不同名称的变量

```python
def _mock_entity_extraction(self, text: str) -> str:
    """模拟实体抽取（修复重复定义问题）"""
    import re
    entities = []
    
    # 用于跟踪相同单位的计数
    unit_counter = {}
    
    # 识别数字+单位模式
    for match in re.finditer(r'(\d+)(年|周|月|天|小时|分钟)', text):
        unit = match.group(2)
        value = int(match.group(1))
        
        # 对相同单位进行计数，创建唯一名称
        count = unit_counter.get(unit, 0) + 1
        unit_counter[unit] = count
        
        # 如果是第一个该单位，使用标准名称
        if count == 1:
            var_name = f"duration_{unit}"
        else:
            # 如果是重复的单位，添加后缀或使用上下文
            var_name = f"duration_{unit}_{count}"
        
        entities.append({
            "name": var_name,
            "original_text": match.group(0),
            "start_index": match.start(),
            "end_index": match.end(),
            "type": "Integer",
            "value": value
        })
    
    # ... 其他实体提取逻辑
    
    return json.dumps(entities, ensure_ascii=False)
```

**效果：**
```
修复前:
  - "90天" → duration_天
  - "30天" → duration_天 (重复)
  - "7天"  → duration_天 (重复)

修复后:
  - "90天" → duration_天
  - "30天" → duration_天_2
  - "7天"  → duration_天_3
```

---

### 方案2：优化冲突解决器

**修改文件：** `prompt_structurizer.py`

**修改内容：** 在`EntityConflictResolver.resolve_overlaps()`中添加变量名去重逻辑

```python
class EntityConflictResolver:
    """处理重叠实体 (Overlapping Entities)"""
    
    @staticmethod
    def resolve_overlaps(entities: List[Dict]) -> List[Dict]:
        """
        最长覆盖原则: 优先保留更长的实体
        
        新增: 变量名去重逻辑
        """
        if not entities:
            return []
        
        # 第一步: 解决位置重叠
        non_overlapping = []
        last_end = -1
        sorted_entities = sorted(entities, key=lambda x: (x['start_index'], -(x['end_index'] - x['start_index'])))
        
        for entity in sorted_entities:
            start = entity['start_index']
            end = entity['end_index']
            
            if start >= last_end:
                non_overlapping.append(entity)
                last_end = end
            else:
                # 发生重叠,比较长度
                if len(non_overlapping) > 0:
                    last_entity = non_overlapping[-1]
                    current_length = end - start
                    last_length = last_entity['end_index'] - last_entity['start_index']
                    
                    if current_length > last_length:
                        # 替换为更长的实体
                        non_overlapping[-1] = entity
                        last_end = end
        
        # 第二步: 变量名去重（新增）
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

### 方案3：使用更智能的变量命名策略

**修改文件：** `llm_client.py`

**修改内容：** 根据上下文生成唯一的变量名

```python
def _mock_entity_extraction(self, text: str) -> str:
    """模拟实体抽取（使用上下文命名）"""
    import re
    entities = []
    
    # 识别数字+单位模式，使用上下文命名
    patterns = [
        (r'错误日志保留(\d+)天', 'error_log_retention_days'),
        (r'访问日志保留(\d+)天', 'access_log_retention_days'),
        (r'调试日志保留(\d+)天', 'debug_log_retention_days'),
        (r'(\d+)年经验', 'experience_years'),
        (r'(\d+)个(人|成员)', 'team_size'),
    ]
    
    for pattern, var_name in patterns:
        for match in re.finditer(pattern, text):
            value = int(match.group(1))
            entities.append({
                "name": var_name,
                "original_text": match.group(0),
                "start_index": match.start(),
                "end_index": match.end(),
                "type": "Integer",
                "value": value
            })
    
    # 对于未匹配的模式，使用通用名称
    general_pattern = r'(\d+)(年|周|月|天|小时|分钟)'
    for match in re.finditer(general_pattern, text):
        unit = match.group(2)
        value = int(match.group(1))
        
        # 检查是否已经被精确模式匹配
        original_text = match.group(0)
        already_matched = any(e['original_text'] == original_text for e in entities)
        
        if not already_matched:
            var_name = f"duration_{unit}"
            entities.append({
                "name": var_name,
                "original_text": original_text,
                "start_index": match.start(),
                "end_index": match.end(),
                "type": "Integer",
                "value": value
            })
    
    return json.dumps(entities, ensure_ascii=False)
```

---

## 📊 对比分析

### 方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **方案1**<br>修复Mock提取 | 简单直接<br>针对根本原因 | 只解决Mock<br>真实LLM可能仍有问题 | ⭐⭐⭐ |
| **方案2**<br>优化冲突解决器 | 通用性<br>适用于所有提取器 | 治标不治本<br>变量名可能不符合语义 | ⭐⭐ |
| **方案3**<br>上下文命名 | 变量名语义化<br>可读性最好 | 需要维护大量模式<br>覆盖不完整 | ⭐⭐⭐⭐ |

### 推荐实施策略

**立即行动（方案1 + 方案2）：**
1. 先实施方案1，修复Mock实体提取（解决当前问题）
2. 同时实施方案2，优化冲突解决器（防止未来问题）
3. 后续考虑方案3，改进变量命名策略

---

## 🎯 与优化模块的关系

### 问题分析：

**这个问题是否由优化模块引入？**

❌ **不是由优化模块引入**

**原因：**
1. 优化点1（规则引擎）只影响Prompt 1.0，不影响实体提取
2. 优化点2（正则提取器）在Mock模式下没有生效（返回0个实体）
3. 问题出现在`MockLLM._mock_entity_extraction()`方法中
4. 该方法在我修改之前就存在，问题是我修改之后运行才暴露出来

**证据：**
```python
# 从优化指标可以看到
prompt20_optimization_stats: {
    "regex_count": 0,  # ← 正则提取0个
    "llm_count": 7,    # ← LLM提取7个
    "llm_called": False, # ← Mock模式，未真实调用
}
```

### 结论：

✅ **优化模块本身没有问题**

❌ **问题在MockLLM的实体提取逻辑中**

❌ **这个问题在修改之前就存在，只是现在暴露出来了**

---

## 📋 修复优先级

### P0（立即修复）：
- ✅ 修复Mock实体提取的重复定义问题
- ✅ 确保DSL能够正确生成

### P1（短期修复）：
- ⏳ 优化冲突解决器，防止未来类似问题
- ⏳ 改进变量命名策略，提升可读性

### P2（长期优化）：
- ⏳ 使用真实LLM测试，验证修复效果
- ⏳ 持续优化实体提取逻辑

---

## 🔧 修复验证清单

### 修复后需要验证：

- [ ] Mock模式下DSL编译成功
- [ ] 无重复定义错误
- [ ] 生成的变量名唯一且语义化
- [ ] 实体提取覆盖所有需要变量化的内容
- [ ] DSL代码逻辑正确
- [ ] 最终代码生成成功

---

## 📝 总结

**问题：** MockLLM实体提取对相同单位创建同名变量，导致DSL重复定义错误

**根源：** `llm_client.py` 第620-628行的正则匹配逻辑

**影响：** DSL无法通过验证，代码生成失败

**解决方案：** 修复Mock实体提取，为相同单位创建唯一变量名

**与优化的关系：** 不是优化模块引入的问题，是MockLLM的已有缺陷

**推荐方案：** 方案1（修复Mock提取）+ 方案2（优化冲突解决器）

---

**文档版本**: 1.0
**创建时间**: 2026-02-07
**作者**: AI Assistant
