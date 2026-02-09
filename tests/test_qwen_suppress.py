#!/usr/bin/env python3
"""
测试千问模型思考过程抑制功能

验证是否能够正确抑制模型的思考过程输出
"""

import sys
sys.path.insert(0, '/mnt/e/pyProject/prompt3.0')

from llm_client import UnifiedLLMClient

def test_suppress_thought_process():
    """测试抑制思考过程的功能"""

    print("=" * 70)
    print("测试千问模型思考过程抑制功能")
    print("=" * 70)

    client = UnifiedLLMClient()

    # 测试用例1：简单任务
    print("\n【测试1】简单任务：提取关键信息")
    print("-" * 70)

    system_prompt = "你是一个文本处理专家。"
    user_prompt = """从以下文本中提取所有数字：
项目需要5个人，预算50万，周期8周，3个测试环境。"""

    print(f"原始提示词:\n{user_prompt}")

    response = client.call(
        system_prompt=system_prompt,
        user_content=user_prompt,
        temperature=0.3
    )

    print(f"\nLLM 响应:\n{response.content}")

    # 检查是否包含思考过程
    has_thought_process = any([
        "好的" in response.content,
        "我现在" in response.content,
        "接下来" in response.content,
        "首先" in response.content,
        "然后" in response.content,
    ])

    if has_thought_process:
        print("\n❌ 检测到思考过程标记")
    else:
        print("\n✅ 未检测到思考过程标记")

    # 测试用例2：复杂任务
    print("\n" + "=" * 70)
    print("【测试2】复杂任务：生成结构化输出")
    print("-" * 70)

    user_prompt2 = """生成一个简单的 Python 函数：
函数名：add_numbers
功能：计算两个数的和
参数：a, b
返回值：和

只输出代码，不要其他文字。"""

    print(f"原始提示词:\n{user_prompt2}")

    response2 = client.call(
        system_prompt=system_prompt,
        user_content=user_prompt2,
        temperature=0.3
    )

    print(f"\nLLM 响应:\n{response2.content}")

    # 检查代码是否包含中文思考过程
    has_chinese_in_code = any([
        '好的' in response2.content,
        '我现在' in response2.content,
        '接下来' in response2.content,
        'def' in response2.content and '好的' in response2.content,
    ])

    if has_chinese_in_code:
        print("\n❌ 检测到代码中包含思考过程")
    else:
        print("\n✅ 代码中未检测到思考过程")

    # 测试用例3：检查抑制指令是否被正确添加
    print("\n" + "=" * 70)
    print("【测试3】验证抑制指令是否被添加")
    print("-" * 70)

    suppressed_prompt = client._suppress_thought_process("测试内容")

    if "不要输出任何思考过程" in suppressed_prompt:
        print("✅ 抑制指令已正确添加到提示词末尾")
        print(f"\n处理后的提示词（末尾部分）:\n{suppressed_prompt[-200:]}")
    else:
        print("❌ 抑制指令未被添加")

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)

if __name__ == '__main__':
    test_suppress_thought_process()
