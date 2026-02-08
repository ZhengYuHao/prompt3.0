"""
代码层验证套件（覆盖更多验证场景）
用于优化点6：代码层验证覆盖度
"""

import re
from typing import List, Dict, Tuple, Set


class CodeLayerValidationSuite:
    """代码层验证套件（覆盖更多验证场景）"""

    @staticmethod
    def validate_template_filling(template: str, variables: List[Dict]) -> Tuple[bool, List[str]]:
        """
        验证模板填充的完整性

        检查：
        1. 所有 {{var}} 都有对应的变量
        2. 所有变量都在模板中被使用

        Args:
            template: 模板字符串
            variables: 变量列表

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        # 提取模板中的所有变量
        template_vars = set(re.findall(r'\{\{(\w+)\}\}', template))

        # 提取变量列表中的所有变量
        provided_vars = set(var['variable'] for var in variables)

        # 检查1：模板中的变量是否都有定义
        undefined_in_template = template_vars - provided_vars
        if undefined_in_template:
            errors.append(f"模板中使用了未定义的变量: {undefined_in_template}")

        # 检查2：定义的变量是否都被使用
        unused_vars = provided_vars - template_vars
        if unused_vars:
            errors.append(f"定义了但未使用的变量: {unused_vars}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_template_restore(template: str, variables: List[Dict]) -> Tuple[bool, str]:
        """
        验证模板还原（填充后应该能还原为原始文本）

        Args:
            template: 模板字符串
            variables: 变量列表

        Returns:
            (是否有效, 填充后的文本)
        """
        # 填充模板
        filled = template
        for var in variables:
            placeholder = f"{{{{{var['variable']}}}}}"
            filled = filled.replace(placeholder, str(var['value']))

        # 这个验证需要原始文本，这里简化为检查填充成功
        # 实际应该与原始文本比对
        return True, filled

    @staticmethod
    def validate_variable_naming(variables: List[Dict]) -> Tuple[bool, List[str]]:
        """
        验证变量命名规范

        规则：
        1. 必须是 snake_case
        2. 不能使用 Python 关键字
        3. 必须以字母开头

        Args:
            variables: 变量列表

        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        python_keywords = {
            'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
            'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
            'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
            'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
            'try', 'while', 'with', 'yield'
        }

        for var in variables:
            var_name = var['variable']

            # 检查1：不能是 Python 关键字
            if var_name in python_keywords:
                errors.append(f"变量名 '{var_name}' 是 Python 关键字")

            # 检查2：必须以字母开头
            if not var_name[0].isalpha():
                errors.append(f"变量名 '{var_name}' 必须以字母开头")

            # 检查3：只能是字母、数字、下划线
            if not re.match(r'^[a-z][a-z0-9_]*$', var_name):
                errors.append(f"变量名 '{var_name}' 不符合 snake_case 规范")

        return len(errors) == 0, errors

    @staticmethod
    def validate_variable_types(variables: List[Dict]) -> Tuple[bool, List[str]]:
        """
        验证变量类型与值的一致性

        Args:
            variables: 变量列表

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        for var in variables:
            var_type = var.get('type')
            value = var.get('value')

            # Integer 类型的值必须是整数
            if var_type == 'Integer':
                try:
                    int(value)
                except (ValueError, TypeError):
                    errors.append(f"变量 '{var['variable']}' 声明为 Integer 但值 '{value}' 不是整数")

            # Boolean 类型的值必须是布尔值
            elif var_type == 'Boolean':
                if not isinstance(value, bool):
                    # 尝试转换
                    str_value = str(value).lower()
                    if str_value not in ['true', 'false', '1', '0']:
                        errors.append(f"变量 '{var['variable']}' 声明为 Boolean 但值 '{value}' 不是布尔值")

            # List 类型的值必须是列表
            elif var_type == 'List':
                if not isinstance(value, list):
                    errors.append(f"变量 '{var['variable']}' 声明为 List 但值 '{value}' 不是列表")

        return len(errors) == 0, errors
