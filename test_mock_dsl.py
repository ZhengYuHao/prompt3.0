#!/usr/bin/env python3
"""测试模拟DSL转译方法"""

import sys
sys.path.insert(0, '.')

from llm_client import MockLLMClient

def test_mock_dsl_transpilation():
    """测试模拟DSL转译"""
    client = MockLLMClient()
    
    # 模拟DSLTranspiler._build_user_content的输出
    user_content = """【变量定义】
- user_name: String
- score: Integer
- items: List
- email_body: String
- summary: String
- user_list: List
- result: String

【逻辑描述】
如果用户是VIP，生成折扣邮件，否则生成普通邮件

【上下文】
这是一个邮件生成系统的需求。"""
    
    print("测试输入:")
    print(user_content)
    print("\n" + "="*60 + "\n")
    
    result = client._mock_dsl_transpilation(user_content)
    
    print("生成的DSL代码:")
    print(result)
    
    # 验证生成的代码是否包含预期的DEFINE语句
    assert "DEFINE {{user_name}}: String" in result, "缺少user_name定义"
    assert "DEFINE {{score}}: Integer" in result, "缺少score定义"
    assert "DEFINE {{result}}: String" in result, "缺少result定义"
    assert "IF" in result or "FOR" in result or "CALL" in result, "缺少控制流或函数调用"
    
    print("\n✅ 测试通过！")

if __name__ == "__main__":
    test_mock_dsl_transpilation()