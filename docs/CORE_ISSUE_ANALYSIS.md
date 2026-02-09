# 核心问题定位报告

## 问题概述
DSL 代码编译时出现大量语法错误，主要集中在 `RETURN` 语句、变量命名、CALL 语句转换三个方面。

## 详细问题分析

### 问题 1: RETURN 语句格式错误 ⭐⭐⭐（最严重）

**症状：**
```
❌ step_2_reorder_results: 语法错误 - invalid syntax (行 3)
❌ step_4_graph_database_search: 语法错误 - invalid syntax (行 3)
❌ step_5_process: 语法错误 - invalid syntax (行 3)
❌ step_6_compute_query_type: 语法错误 - invalid syntax (行 3)
```

**DSL 代码示例：**
```dsl
IF {{similarity}} > {{similarity_threshold}}
    RETURN CALL return_top_n_results({{top_n_vector_search}})
ELSE
    RETURN CALL return_top_n_results({{top_n_reordered_results}})
ENDIF
```

**根本原因：**
在 `prompt_codegenetate.py` 的 `_clean_line()` 方法中：
- 第 520-522 行：只有当行中包含 "CALL" 时，才会调用 `_translate_call()`
- 但是对于 `RETURN CALL xxx(...)` 这种格式，`_clean_line()` 只是简单地移除 `{{}}`，将 `RETURN` 保留
- 结果生成的是 Python 代码：`return CALL return_top_n_results(...)`，这在 Python 中是非法语法

**问题代码位置：**
`prompt_codegenetate.py:480-524`
```python
def _clean_line(self, line: str) -> str:
    """清理伪代码为 Python 代码（增强 FOR 循环转换）"""
    # 去除 {{}}
    cleaned = line.replace("{{", "").replace("}}", "")
    
    # ... 其他转换逻辑 ...
    
    # 处理 CALL - 只有当行中包含 CALL 时才处理
    if "CALL" in line:
        cleaned = self._translate_call(line)
    
    return cleaned
```

**为什么出错：**
- `RETURN CALL func(...)` 包含 "CALL"，会进入 `_translate_call()`
- 但 `_translate_call()` 只处理 `{{var}} = CALL func(...)` 格式
- 对于 `RETURN CALL func(...)` 格式，不匹配任何正则表达式，返回原字符串
- 最终生成 `return CALL func(...)`，语法错误

**正确转换应该是：**
```python
return await invoke_function('func', ...)
```

---

### 问题 2: 变量名以数字开头 ⭐⭐

**症状：**
```
❌ step_16_process: 语法错误 - invalid decimal literal (行 1)
```

**DSL 代码：**
```dsl
IF {{95th_percentile_response_time}} > 3
    CALL trigger_scaling()
ENDIF
```

**根本原因：**
- 变量名 `95th_percentile_response_time` 以数字开头
- Python 标识符规则：变量名不能以数字开头
- 虽然在 DSL 中使用了 `{{}}` 包裹，但转换后直接作为 Python 变量名
- 最终生成的 Python 函数参数包含 `95th_percentile_response_time`，这是非法语法

**问题代码位置：**
DSL 生成阶段（Prompt 3.0）就应该检查变量名合法性
目前只在验证阶段才检测，为时已晚

---

### 问题 3: CALL 语句缺少参数 ⭐

**症状：**
```
WARNING  | 无法解析 CALL 语句: IF CALL check_sensitive_words({{query}})
```

**DSL 代码：**
```dsl
IF CALL check_sensitive_words({{query}})
    RETURN CALL reject_service()
ENDIF
```

**根本原因：**
- `IF CALL func(...)` 格式中，`CALL` 被当作条件表达式的一部分
- `_clean_line()` 第 520-522 行的检查：`if "CALL" in line:` 会对这行调用 `_translate_call()`
- 但 `IF CALL check_sensitive_words(...)` 不符合 `_translate_call()` 的任何正则模式
- 因为它不匹配 `{{var}} = CALL func(...)` 格式
- `_translate_call()` 返回原字符串 `IF CALL check_sensitive_words(query)`
- 最终生成 `if CALL check_sensitive_words(query):` 语法错误

**问题代码位置：**
`prompt_codegenetate.py:383-433`
```python
def _translate_call(self, pseudo_line: str) -> str:
    cleaned = pseudo_line.replace("{{", "").replace("}}", "")
    
    # 容错模式1: 标准格式 result = CALL func(arg1, arg2)
    match = re.match(r'(\w+)\s*=\s*CALL\s+(\w+)\s*\((.*?)\)\s*$', cleaned)
    if match:
        result_var = match.group(1)
        func_name = match.group(2)
        args_str = match.group(3)
        return self._format_call(result_var, func_name, args_str)
    
    # ... 其他容错模式 ...
    
    # 无法解析，返回原始行并警告
    warning(f"无法解析 CALL 语句: {pseudo_line}")
    return cleaned  # ← 这里返回原字符串，导致语法错误
```

---

### 问题 4: IF 语句内部缺少缩进 ⭐⭐

**症状：**
```
❌ step_8_process: 语法错误 - expected an indented block after 'if' statement on line 3 (行 4)
❌ step_11_process: 语法错误 - expected an indented block after 'if' statement on line 3 (行 4)
❌ step_14_process: 语法错误 - expected an indented block after 'if' statement on line 3 (行 4)
❌ step_15_process: 语法错误 - expected an indented block after 'if' statement on line 3 (行 4)
❌ step_17_process: 语法错误 - expected an indented block after 'if' statement on line 3 (行 4)
```

**DSL 代码：**
```dsl
IF CALL check_sensitive_words({{query}})
    RETURN CALL reject_service()
ENDIF
```

**生成的 Python 代码（推测）：**
```python
async def step_X_process(query):
    """Auto-generated module"""
    if CALL check_sensitive_words(query):  # ← 行 3，有冒号
    return CALL reject_service()            # ← 行 4，没有缩进！
    return None
```

**根本原因：**
1. Parser 只处理了带 `=` 的赋值语句和 `RETURN CALL` 语句，没有处理单纯的 `CALL` 语句（如 `CALL trigger_scaling()`）
2. 导致 IF 块内部的 CALL 语句没有被解析成代码块，无法正确转换和缩进

**问题代码位置：**
`prompt_codegenetate.py:200-233` (原始版本)

**修复方案：**
在 `parse()` 方法中添加对单纯 CALL 语句的处理逻辑：
- 检测 `CALL func(...)` 格式（没有等号）
- 将其解析为独立的 CodeBlock
- 在 `_translate_call()` 方法中添加对应的转换模式

**修复后代码位置：**
`prompt_codegenetate.py:237-256` - 添加了对单纯 CALL 语句的解析
`prompt_codegenetate.py:508-540` - 在 `_translate_call()` 中添加了转换模式5和6

**测试结果：**
```python
async def step_1_trigger_scaling():
    """Auto-generated module"""
    if _95th_percentile_response_time > alert_threshold:
        await invoke_function('trigger_scaling')
    return None
```
✅ 语法验证通过

---

### 问题 5: 未定义变量警告 ⭐

**症状：**
```
WARNING  | 未定义变量: query 在块 OP_1 中使用
WARNING  | 未定义变量: knowledge_graph_hops 在块 OP_7 中使用
```

**DSL 代码：**
```dsl
DEFINE {{query_type}}: String
IF {{query_type}} == "simple_fact"
    {{similarity}} = CALL vector_search({{query}})  # ← query 未定义
ENDIF
```

**根本原因：**
- `query_type` 已定义，但 `query` 没有定义
- DSL 编译器（Prompt 3.0）没有检测到这个变量未定义
- 在依赖分析阶段才发出警告

---

## 问题优先级总结

| 问题 | 优先级 | 影响范围 | 难度 |
|------|--------|----------|------|
| 问题 1: RETURN CALL 格式错误 | P0 | 所有 RETURN 语句 | 中等 |
| 问题 2: 变量名以数字开头 | P0 | 特定变量 | 简单 |
| 问题 3: IF CALL 条件表达式 | P1 | 特定场景 | 中等 |
| 问题 4: IF 内部语句缩进 | P1 | 控制流 | 中等 |
| 问题 5: 未定义变量 | P2 | 特定场景 | 简单 |

## 修复方案建议

### 方案 1: 增强 RETURN 语句处理

在 `_clean_line()` 或 `_translate_call()` 中添加：
1. 检测 `RETURN CALL func(...)` 格式
2. 转换为 `return await invoke_function('func', ...)`

### 方案 2: 添加变量名合法性校验

在 DSL 生成阶段（Prompt 3.0）或代码生成阶段（Prompt 4.0）：
1. 检查变量名是否符合 Python 标识符规则
2. 变量名不能以数字开头
3. 只能包含字母、数字、下划线

### 方案 3: 增强条件语句解析

处理 `IF CALL func(...)` 格式：
1. 将 CALL 转换为 `await invoke_function(...)` 返回布尔值
2. 或将 `IF CALL func(...)` 改为独立调用 + 条件判断

### 方案 4: 确保控制流内聚

虽然已经修改了聚类逻辑，但需要确保：
1. FOR/IF 块和它们的内部语句在同一个模块
2. 控制流结束后才切分模块

### 方案 5: 增强变量定义检查

在 DSL 编译阶段：
1. 检查所有使用的变量是否已定义
2. 发出明确的错误或警告

---

## 修复总结 ✅

### 已完成的修复

#### 1. ✅ P0-1: RETURN CALL 语句格式错误
**修复位置：** `prompt_codegenetate.py:218-233`

**修复内容：**
- 在 `parse()` 方法中添加了对 `RETURN CALL` 语句的特殊处理
- 在 `_translate_call()` 方法中添加了匹配 RETURN CALL 的正则表达式模式

**测试结果：**
```python
# DSL: RETURN CALL return_top_n_results(top_n_vector_search, top_n)
# Python: return await invoke_function('return_top_n_results', top_n_vector_search=top_n_vector_search, top_n=top_n)
```

---

#### 2. ✅ P0-2: 变量名以数字开头
**修复位置：**
- `prompt_codegenetate.py:662-675` - `_sanitize_identifier()` 方法
- `prompt_codegenetate.py:695-730` - `_sanitize_line_variables()` 方法
- `prompt_codegenetate.py:529-540` - `_format_call()` 方法中的参数清理

**修复内容：**
- 实现了变量名清理方法 `_sanitize_identifier()`
- 为以数字开头的变量名添加下划线前缀
- 在 `_clean_line()` 中调用清理方法处理所有变量引用

**测试结果：**
```python
# DSL: IF 95th_percentile_response_time > alert_threshold
# Python: if _95th_percentile_response_time > alert_threshold:
```

---

#### 3. ✅ P1-1: CALL 语句在条件表达式中
**修复位置：** `prompt_codegenetate.py:590-627`

**修复内容：**
- 在 `_clean_line()` 方法中添加了对 `IF CALL` 的特殊处理
- 转换为 `if await invoke_function('func', ...):`

**测试结果：**
```python
# DSL: IF CALL check_sensitive_words({{query}})
# Python: if await invoke_function('check_sensitive_words', query=query):
```

---

#### 4. ✅ P1-2: IF 语句内部缺少缩进 & 单纯 CALL 语句解析
**修复位置：**
- `prompt_codegenetate.py:235-256` - 添加对单纯 CALL 语句的解析
- `prompt_codegenetate.py:508-542` - 添加单纯 CALL 语句的转换模式
- `prompt_codegenetate.py:802-814` - ELSE 分支缩进修复

**修复内容：**
- Parser 增加对 `CALL func()` 格式的解析（无等号）
- `_translate_call()` 增加模式5和6处理单纯 CALL
- ELSE 分支特殊处理，确保与 IF 同级缩进

**测试结果：**
```python
# DSL:
#   IF 95th_percentile_response_time > alert_threshold
#       CALL trigger_scaling()
#   ENDIF
# Python:
#   if _95th_percentile_response_time > alert_threshold:
#       await invoke_function('trigger_scaling')
```

---

#### 5. ✅ 额外修复：RETURN 语句转换 & 重复 return 处理
**修复位置：**
- `prompt_codegenetate.py:684-688` - RETURN 语句转换
- `prompt_codegenetate.py:258-273` - RETURN 语句输出变量提取
- `prompt_codegenetate.py:884-896` - 避免 return 语句重复

**修复内容：**
- 将 `RETURN var` 转换为 `return var`
- 正确提取 RETURN 语句中的变量作为模块输出
- 避免当已有 RETURN 语句时再添加默认 return

**测试结果：**
```python
# DSL: RETURN result
# Python: return result
# （且不再重复添加 return None）
```

---

### 修复统计

| 问题编号 | 优先级 | 状态 | 涉及文件 | 修改行数 |
|---------|--------|------|---------|---------|
| P0-1    | P0     | ✅ 完成 | prompt_codegenetate.py | ~30 行 |
| P0-2    | P0     | ✅ 完成 | prompt_codegenetate.py | ~50 行 |
| P1-1    | P1     | ✅ 完成 | prompt_codegenetate.py | ~20 行 |
| P1-2    | P1     | ✅ 完成 | prompt_codegenetate.py | ~80 行 |
| 额外1   | -      | ✅ 完成 | prompt_codegenetate.py | ~10 行 |
| 额外2   | -      | ✅ 完成 | prompt_codegenetate.py | ~20 行 |

---

### 测试结果

所有修复已通过综合测试：
- ✅ 语法验证通过
- ✅ RETURN CALL 正确转换
- ✅ 变量名清理正确
- ✅ IF CALL 正确转换
- ✅ IF 语句缩进正确
- ✅ ELSE 分支缩进正确
- ✅ RETURN 语句正确转换
- ✅ 无重复 return 语句

---

### 待处理问题

| 问题编号 | 优先级 | 状态 | 说明 |
|---------|--------|------|------|
| P2      | P2     | 🔄 待处理 | 未定义变量警告 |

**说明：** P2 问题属于 DSL 生成阶段的变量定义检查，需要在 Prompt 3.0 或 Prompt 2.0 阶段处理，不属于 Prompt 4.0 代码生成阶段的修复范围。

