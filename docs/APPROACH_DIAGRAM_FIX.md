# Approach 图生成 Bug 修复说明

## Bug 描述

### 问题现象
```
2026-02-02 16:19:08 | ERROR | history_manager.py:2203 | _generate_approach_diagram_mermaid() |
生成 Approach 图失败: unbalanced parenthesis at position 50
```

### 影响范围
- **直接影响**: LLM 生成 Approach 图失败
- **最终效果**: 业务流程图显示为默认模板（通用流程图），而不是基于实际代码的业务流程图
- **数据完整性**: HTML 报告可以正常显示，但业务逻辑不够精确

---

## Bug 根源

### 问题分析

1. **LLM 输出不稳定**
   - LLM 生成的 Mermaid 代码可能包含**括号不匹配**的语法错误
   - 例如：`Start([开始 --> End([结束])`（缺少闭合括号）

2. **正则表达式处理时抛出异常**
   - 代码在 2187-2193 行使用正则表达式清理 `:::className` 语法
   - 当 Mermaid 代码本身有语法错误时，正则表达式可能抛出异常

3. **错误处理不完善**
   - 原始代码虽然有 `try-except`，但只在最外层捕获异常
   - 没有对 LLM 返回的内容进行**基本语法验证**
   - 错误信息不够详细，难以调试

### 代码位置

**文件**: `history_manager.py`
**方法**: `_generate_approach_diagram_mermaid()`
**行号**: 2179-2193

---

## 修复方案

### 修复内容

在 `history_manager.py:2179` 之后添加了：

#### 1. 括号验证函数
```python
def validate_parentheses(code: str) -> tuple:
    """验证括号是否匹配"""
    stack = []
    brackets = {'(': ')', '[': ']', '{': '}'}
    position = 0

    for char in code:
        position += 1
        if char in brackets:
            stack.append(char)
        elif char in brackets.values():
            if not stack:
                return False, f"Unexpected closing bracket '{char}' at position {position}"
            if brackets[stack[-1]] != char:
                return False, f"Mismatched bracket at position {position}"
            stack.pop()

    if stack:
        return False, f"Unclosed brackets: {stack}"
    return True, ""
```

#### 2. 语法验证调用
```python
# 验证基本语法
is_valid, error_msg = validate_parentheses(mermaid_code)
if not is_valid:
    error(f"LLM 返回的 Mermaid 代码语法错误: {error_msg}")
    error(f"原始代码: {mermaid_code[:200]}...")
    return self._get_default_approach_diagram(context)
```

#### 3. 正则表达式异常处理
```python
try:
    for match in re.finditer(...):
        # 处理节点类映射
    mermaid_code = re.sub(r':::\w+', '', mermaid_code)
except Exception as regex_error:
    error(f"正则表达式清理失败: {regex_error}")
    return self._get_default_approach_diagram(context)
```

---

## 修复效果

### 改进点

1. ✅ **提前检测语法错误**
   - 在正则表达式处理前验证括号匹配
   - 避免在处理无效代码时抛出异常

2. ✅ **更详细的错误日志**
   - 明确指出错误类型（括号不匹配、位置）
   - 显示原始代码片段，便于调试

3. ✅ **更健壮的错误处理**
   - 正则表达式处理也添加了 try-except
   - 任何步骤失败都会优雅降级到默认模板

4. ✅ **不影响现有功能**
   - 正常代码流程不受影响
   - 错误情况下仍然返回可用的默认图

### 测试结果

运行 `test_approach_fix.py` 验证：

```
测试: 正常代码
✅ 验证通过
✅ 结果符合预期

测试: 缺少闭合括号
❌ 验证失败: Unclosed brackets: ['(', '[']
✅ 结果符合预期

测试: 多余闭合括号
❌ 验证失败: Unexpected closing bracket ')' at position 35
✅ 结果符合预期

测试: 方括号不匹配
❌ 验证失败: Mismatched bracket at position 30
✅ 结果符合预期

测试: 包含 :::className 语法
✅ 验证通过
✅ 结果符合预期
```

---

## 使用说明

### 重新生成 HTML 报告

```bash
# 使用修复后的代码重新生成报告
python3 view_history.py export-pipeline

# 或运行完整流水线
python3 demo_full_pipeline.py
```

### 查看日志

如果 LLM 仍然生成无效的 Mermaid 代码，现在会看到更详细的错误信息：

```
[ERROR] LLM 返回的 Mermaid 代码语法错误: Unexpected closing bracket ')' at position 50
[ERROR] 原始代码: graph TD\nStart([用户输入]) --> Process1(处理数据)) ...
```

### 降级行为

当验证失败时，系统会：
1. 记录详细的错误日志
2. 自动使用默认模板生成流程图
3. 确保 HTML 报告仍然可以正常显示

---

## 未来改进方向

### 短期
- [ ] 添加更多 Mermaid 语法验证规则（如节点命名规范）
- [ ] 改进 LLM Prompt，明确要求输出有效语法
- [ ] 添加 Mermaid 代码格式化功能

### 长期
- [ ] 集成 Mermaid 在线验证 API
- [ ] 支持用户自定义 Approach 图模板
- [ ] 添加 Approach 图编辑器（在 HTML 中）

---

## 相关文件

- **修复文件**: `history_manager.py:2179-2205`
- **测试文件**: `test_approach_fix.py`
- **诊断文件**: `diagnose_mermaid.py`
- **历史记录**: `processing_history/pipeline_cc2a387c.html`

---

## 总结

这个修复解决了 Approach 图生成过程中的语法验证问题，使得系统能够：

1. **更早发现问题**：在处理前验证代码语法
2. **提供更多信息**：详细的错误日志便于调试
3. **更健壮运行**：任何步骤失败都能优雅降级
4. **保持稳定性**：确保 HTML 报告始终可用

修复后，即使 LLM 生成无效的 Mermaid 代码，系统也能够：
- 识别问题
- 记录详细日志
- 降级到默认模板
- 保证用户体验
