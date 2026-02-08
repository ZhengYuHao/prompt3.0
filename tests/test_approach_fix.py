#!/usr/bin/env python3
"""
测试 Approach 图修复

验证括号验证和错误处理是否正常工作
"""

from history_manager import HistoryManager

def test_parentheses_validation():
    """测试括号验证功能"""

    manager = HistoryManager()

    # 测试用例：包含不匹配括号的 Mermaid 代码
    test_cases = [
        {
            'name': '正常代码',
            'code': 'graph TD\nStart([开始]) --> End([结束])',
            'should_pass': True
        },
        {
            'name': '缺少闭合括号',
            'code': 'graph TD\nStart([开始 --> End([结束])',
            'should_pass': False
        },
        {
            'name': '多余闭合括号',
            'code': 'graph TD\nStart([开始]) --> End([结束]))',
            'should_pass': False
        },
        {
            'name': '方括号不匹配',
            'code': 'graph TD\nStart[开始] --> End(结束])',
            'should_pass': False
        },
        {
            'name': '包含 :::className 语法',
            'code': 'graph TD\nStart([开始]):::start --> End([结束])',
            'should_pass': True
        }
    ]

    print("=" * 60)
    print("测试括号验证功能")
    print("=" * 60)

    for test in test_cases:
        print(f"\n测试: {test['name']}")
        print(f"代码: {test['code'][:50]}...")

        # 调用内部验证函数
        is_valid, error_msg = manager._validate_parentheses(test['code'])

        if is_valid:
            print(f"✅ 验证通过")
        else:
            print(f"❌ 验证失败: {error_msg}")

        if is_valid == test['should_pass']:
            print(f"✅ 结果符合预期")
        else:
            print(f"❌ 结果不符合预期 (预期: {'通过' if test['should_pass'] else '失败'})")

if __name__ == '__main__':
    # 先从 history_manager 导入验证函数
    import sys
    sys.path.insert(0, '/mnt/e/pyProject/prompt3.0')

    from history_manager import HistoryManager
    import types

    # 将验证函数添加到 HistoryManager 类
    def validate_parentheses(self, code: str) -> tuple:
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

    # 动态添加方法
    HistoryManager._validate_parentheses = validate_parentheses

    # 运行测试
    test_parentheses_validation()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
