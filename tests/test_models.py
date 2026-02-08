"""
测试 API Key 支持的模型
"""

from openai import OpenAI

# API 配置
BASE_URL = "https://api.rcouyi.com/v1"
API_KEY = "sk-0JL8T592b6roD3uaDaD0Ac0f081c4040810d978e38CdAa01"

# 常见模型列表
MODELS_TO_TEST = [
    # GPT-3.5 系列
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
    "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-1106",
    
    # GPT-4 系列
    "gpt-4",
    "gpt-4-turbo",
    "gpt-4-turbo-preview",
    "gpt-4-0125-preview",
    "gpt-4-1106-preview",
    "gpt-4o",
    "gpt-4o-mini",
    
    # Claude 系列
    "claude-3-opus",
    "claude-3-sonnet", 
    "claude-3-haiku",
    "claude-3-5-sonnet",
    
    # 其他
    "deepseek-chat",
    "deepseek-coder",
    "qwen-turbo",
    "qwen-plus",
]


def test_model(client: OpenAI, model: str) -> tuple:
    """
    测试单个模型是否可用
    
    Returns:
        (是否成功, 响应信息)
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
            timeout=10
        )
        return True, response.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg:
            return False, "不支持"
        elif "404" in error_msg:
            return False, "模型不存在"
        elif "401" in error_msg:
            return False, "认证失败"
        else:
            return False, error_msg[:50]


def main():
    print("=" * 60)
    print("API Key 模型支持测试")
    print("=" * 60)
    print(f"API 端点: {BASE_URL}")
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-4:]}")
    print("=" * 60)
    print()
    
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=15)
    
    supported = []
    unsupported = []
    
    print("开始测试模型...")
    print("-" * 60)
    
    for model in MODELS_TO_TEST:
        success, msg = test_model(client, model)
        status = "✅ 可用" if success else "❌ 不可用"
        print(f"  {model:25} {status:12} {msg if not success else ''}")
        
        if success:
            supported.append(model)
        else:
            unsupported.append(model)
    
    print()
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"\n✅ 支持的模型 ({len(supported)} 个):")
    for m in supported:
        print(f"   • {m}")
    
    print(f"\n❌ 不支持的模型 ({len(unsupported)} 个):")
    for m in unsupported:
        print(f"   • {m}")
    
    print()
    print("=" * 60)
    if supported:
        print(f"推荐使用: {supported[0]}")
    else:
        print("警告: 没有找到可用的模型！")
    print("=" * 60)


if __name__ == "__main__":
    main()
