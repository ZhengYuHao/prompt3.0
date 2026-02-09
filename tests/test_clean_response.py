#!/usr/bin/env python3
"""测试 LLM 响应清理功能"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from llm_client import UnifiedLLMClient

def test_clean_llm_response():
    """测试响应清理函数"""

    client = UnifiedLLMClient()

    test_cases = [
        {
            "name": "包含标准格式标签",
            "input": "<|im_start|>system<|im_end|>\n指令内容\n\ndef hello():\n    print('hello')",
            "expected": "指令内容\n\ndef hello():\n    print('hello')"
        },
        {
            "name": "包含多个格式标签",
            "input": "<|im_start|>user<|im_end|>你好<|im_start|>assistant<|im_end|>世界",
            "expected": "你好世界"
        },
        {
            "name": "正常代码（无标签）",
            "input": "def test():\n    return 42",
            "expected": "def test():\n    return 42"
        },
        {
            "name": "多余的换行",
            "input": "def test():\n\n\n    return 42",
            "expected": "def test():\n\n    return 42"
        },
        {
            "name": "完整的对话格式",
            "input": "<|im_start|>system<|im_end|>\n指令内容\n<|im_start|>user<|im_end|>\n用户输入<|im_start|>assistant<|im_end|>助手回复",
            "expected": "指令内容\n\n用户输入助手回复"
        }
    ]

    print("=" * 70)
    print("【测试 LLM 响应清理功能】")
    print("=" * 70)

    passed = 0
    failed = 0

    for i, case in enumerate(test_cases, 1):
        print(f"\n【测试 {i}】{case['name']}")
        print("-" * 70)

        # 调用清理函数
        result = client._clean_llm_response(case['input'])

        # 检查结果
        if result == case['expected']:
            print("✅ 通过")
            passed += 1
        else:
            print("❌ 失败")
            print(f"   输入:   {repr(case['input'][:50])}...")
            print(f"   期望:   {repr(case['expected'][:50])}...")
            print(f"   实际:   {repr(result[:50])}...")
            failed += 1

    # 总结
    print("\n" + "=" * 70)
    print(f"测试完成: {passed}/{len(test_cases)} 通过")
    if failed > 0:
        print(f"⚠️  {failed} 个测试失败")
        return False
    else:
        print("✅ 所有测试通过")
        return True

def test_with_real_llm():
    """测试真实 LLM 调用"""
    print("\n" + "=" * 70)
    print("【测试真实 LLM 调用】")
    print("=" * 70)

    try:
        client = UnifiedLLMClient()

        # 简单测试
        prompt = "生成一个 Python 函数，计算两个数的和"
        response = client.call(
            system_prompt="你是一个代码生成助手",
            user_content=prompt
        )

        print(f"\n响应长度: {len(response.content)} 字符")
        print(f"\n响应内容:\n{response.content}")

        # 检查是否包含格式标签
        if "<|im_start|>" in response.content or "<|im_end|>" in response.content:
            print("\n⚠️  响应中包含格式标签（清理可能失败）")
            return False
        else:
            print("\n✅ 响应中无格式标签（清理成功）")
            return True

    except Exception as e:
        print(f"\n❌ LLM 调用失败: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("LLM 响应清理功能测试")
    print("=" * 70)

    # 单元测试
    unit_test_passed = test_clean_llm_response()

    # 集成测试
    integration_test_passed = test_with_real_llm()

    # 总结
    print("\n" + "=" * 70)
    if unit_test_passed and integration_test_passed:
        print("✅ 所有测试通过")
        sys.exit(0)
    else:
        print("⚠️  部分测试失败")
        sys.exit(1)
