"""
增强型 DSL 自动修复器（最大化代码层修复）
用于优化点4：自动修复增强
"""

import re
from typing import List, Dict, Tuple
from collections import defaultdict


class EnhancedDSLAutoFixer:
    """增强型 DSL 自动修复器（最大化代码层修复）"""

    @classmethod
    def fix(cls, dsl_code: str, errors: List) -> Tuple[str, Dict]:
        """
        自动修复 DSL 错误

        Args:
            dsl_code: DSL 代码
            errors: 错误列表

        Returns:
            (修复后的代码, 修复统计)
        """
        stats = {
            'total_fixed': 0,
            'fix_by_type': {},
            'remaining_errors': 0
        }

        lines = dsl_code.split('\n')
        fixed_lines = lines.copy()

        # 按错误类型分组
        errors_by_type = defaultdict(list)
        for error in errors:
            errors_by_type[error.error_type].append(error)

        # 类型1：语法错误（IF/FOR 缺少条件）
        if '语法错误' in errors_by_type:
            fixed, count = cls._fix_syntax_errors(fixed_lines, errors_by_type['语法错误'])
            fixed_lines = fixed
            stats['total_fixed'] += count
            stats['fix_by_type']['语法错误'] = count

        # 类型2：未定义变量
        if '未定义变量' in errors_by_type:
            fixed, count = cls._fix_undefined_variables(fixed_lines, errors_by_type['未定义变量'])
            fixed_lines = fixed
            stats['total_fixed'] += count
            stats['fix_by_type']['未定义变量'] = count

        # 类型3：控制流未闭合
        if '控制流未闭合' in errors_by_type:
            fixed, count = cls._fix_unclosed_control_flow(fixed_lines, errors_by_type['控制流未闭合'])
            fixed_lines = fixed
            stats['total_fixed'] += count
            stats['fix_by_type']['控制流未闭合'] = count

        # 类型4：类型错误（强制类型转换）
        if '类型错误' in errors_by_type:
            fixed, count = cls._fix_type_errors(fixed_lines, errors_by_type['类型错误'])
            fixed_lines = fixed
            stats['total_fixed'] += count
            stats['fix_by_type']['类型错误'] = count

        # 重新验证
        fixed_code = '\n'.join(fixed_lines)
        temp_validator = DSLValidatorMock()
        temp_result = temp_validator.validate(fixed_code)
        stats['remaining_errors'] = len(temp_result.errors)

        return fixed_code, stats

    @classmethod
    def _fix_syntax_errors(cls, lines: List[str], errors: List) -> Tuple[List[str], int]:
        """修复语法错误"""
        fixed_count = 0

        for error in errors:
            line_num = error.line_number - 1  # 转换为0-based
            if 0 <= line_num < len(lines):
                line = lines[line_num].strip()

                # IF 缺少条件 → IF True
                if line == 'IF' or (line.startswith('IF ') and len(line) == 2):
                    lines[line_num] = lines[line_num].replace('IF', 'IF True')
                    fixed_count += 1

                # FOR 缺少 IN → FOR {{item}} IN {{collection}}
                elif line.startswith('FOR ') and 'IN' not in line:
                    # 提取变量名
                    var_match = re.search(r'FOR\s+\{\{(\w+)\}\}', line)
                    if var_match:
                        var_name = var_match.group(1)
                        lines[line_num] = f'FOR {{{{{var_name}}}}} IN {{collection}}'
                        fixed_count += 1

        return lines, fixed_count

    @classmethod
    def _fix_undefined_variables(cls, lines: List[str], errors: List) -> Tuple[List[str], int]:
        """修复未定义变量错误"""
        fixed_count = 0

        # 收集所有未定义的变量
        undefined_vars = set()
        for error in errors:
            match = re.search(r'\{\{(\w+)\}\}', error.message)
            if match:
                undefined_vars.add(match.group(1))

        # 在文件开头添加 DEFINE 语句
        if undefined_vars:
            define_lines = []
            for var_name in undefined_vars:
                # 推断类型
                var_type = cls._infer_variable_type(lines, var_name)
                define_lines.append(f'DEFINE {{{{{var_name}}}}}: {var_type}')

            # 在第一个非注释行之前插入
            insert_index = 0
            while insert_index < len(lines) and lines[insert_index].strip().startswith('#'):
                insert_index += 1

            lines = lines[:insert_index] + define_lines + [''] + lines[insert_index:]
            fixed_count = len(undefined_vars)

        return lines, fixed_count

    @classmethod
    def _infer_variable_type(cls, lines: List[str], var_name: str) -> str:
        """推断变量类型"""
        var_pattern = re.compile(r'\{\{' + re.escape(var_name) + r'\}\}')

        for line in lines:
            if var_pattern.search(line):
                # 检查使用上下文
                if '>' in line or '<' in line or '>=' in line or '<=' in line:
                    return 'Integer'
                elif '==' in line and '"' in line:
                    return 'String'
                elif 'IN' in line:
                    return 'List'

        return 'Any'

    @classmethod
    def _fix_unclosed_control_flow(cls, lines: List[str], errors: List) -> Tuple[List[str], int]:
        """修复控制流未闭合"""
        fixed_count = 0
        control_stack = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            if stripped.startswith('IF ') or stripped == 'IF':
                control_stack.append(('IF', i))
            elif stripped.startswith('FOR ') or stripped == 'FOR':
                control_stack.append(('FOR', i))
            elif stripped.startswith('WHILE ') or stripped == 'WHILE':
                control_stack.append(('WHILE', i))
            elif stripped == 'ENDIF':
                if control_stack and control_stack[-1][0] == 'IF':
                    control_stack.pop()
            elif stripped == 'ENDFOR':
                if control_stack and control_stack[-1][0] == 'FOR':
                    control_stack.pop()
            elif stripped == 'ENDWHILE':
                if control_stack and control_stack[-1][0] == 'WHILE':
                    control_stack.pop()

        # 添加缺少的闭合标签
        for block_type, _ in reversed(control_stack):
            if block_type == 'IF':
                lines.append('ENDIF')
            elif block_type == 'FOR':
                lines.append('ENDFOR')
            elif block_type == 'WHILE':
                lines.append('ENDWHILE')
            fixed_count += 1

        return lines, fixed_count

    @classmethod
    def _fix_type_errors(cls, lines: List[str], errors: List) -> Tuple[List[str], int]:
        """修复类型错误（添加类型转换）"""
        fixed_count = 0

        # 这个更复杂，需要分析具体的类型不匹配
        # 简化版本：对于 Integer 比较中的 String 变量，添加 int() 转换
        for error in errors:
            if '类型错误' in error.error_type:
                # 提取变量名
                match = re.search(r'\{\{(\w+)\}\}', error.message)
                if match:
                    var_name = match.group(1)
                    line_num = error.line_number - 1

                    if 0 <= line_num < len(lines):
                        # 尝试添加类型转换
                        line = lines[line_num]
                        pattern = r'\{\{' + re.escape(var_name) + r'\}\}'
                        replacement = f'int({{{{var_name}}})'

                        # 只在比较操作中替换
                        if re.search(r'[><=].*' + pattern, line):
                            lines[line_num] = line.replace(match.group(0), replacement)
                            fixed_count += 1

        return lines, fixed_count


class SmartRetryStrategy:
    """智能重试策略（减少 LLM 调用）"""

    # 可以通过代码层修复的错误类型
    CODE_FIXABLE_ERRORS = {
        '语法错误',
        '未定义变量',
        '控制流未闭合',
        '类型错误',
        '重复定义'
    }

    # 需要 LLM 介入的错误类型
    LLM_REQUIRED_ERRORS = {
        '逻辑错误',
        '语义错误',
        '变量命名规范',
        '复杂逻辑结构'
    }

    @classmethod
    def should_retry_with_llm(cls, result) -> Tuple[bool, str]:
        """
        判断是否需要 LLM 重试

        Args:
            result: 验证结果

        Returns:
            (是否需要 LLM 重试, 原因说明)
        """
        # 如果没有错误，不需要重试
        if result.is_valid:
            return False, "验证通过"

        # 统计错误类型
        error_types = set(err.error_type for err in result.errors)

        # 情况1：所有错误都可以通过代码修复 → 不需要 LLM
        code_fixable = error_types.issubset(cls.CODE_FIXABLE_ERRORS)
        if code_fixable:
            return False, f"所有错误({len(result.errors)}个)都可以通过代码层修复"

        # 情况2：既有代码可修复，又有需要 LLM 的 → 需要 LLM
        has_llm_required = not error_types.isdisjoint(cls.LLM_REQUIRED_ERRORS)
        if has_llm_required:
            return True, f"存在需要 LLM 介入的错误: {error_types.intersection(cls.LLM_REQUIRED_ERRORS)}"

        # 情况3：未知错误类型 → 保守起见，需要 LLM
        return True, "存在未知错误类型，需要 LLM 介入"

    @classmethod
    def estimate_fix_potential(cls, result) -> float:
        """
        估计代码层修复的潜力

        Args:
            result: 验证结果

        Returns:
            0-1 之间的值，1 表示 100% 可以修复
        """
        if result.is_valid:
            return 1.0

        code_fixable_count = sum(
            1 for err in result.errors
            if err.error_type in cls.CODE_FIXABLE_ERRORS
        )

        return code_fixable_count / len(result.errors)


class DSLValidatorMock:
    """DSL 验证器 Mock（用于测试）"""

    def validate(self, dsl_code: str):
        """验证 DSL 代码（Mock）"""
        class MockResult:
            is_valid = True
            errors = []

        return MockResult()
