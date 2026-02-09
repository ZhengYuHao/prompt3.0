"""
LLM 客户端使用示例
展示如何使用不同的模型配置
"""

from llm_client import create_llm_client, MODEL_CONFIGS, LLMModel


def example_1_use_qwen3():
    """示例1: 使用预定义的 Qwen3-32B 配置"""
    print("\n【示例1】使用预定义的 Qwen3-32B 配置")
    print("-" * 50)
    
    # 一行代码切换到 Qwen3-32B
    client = create_llm_client(config_name="qwen3-32b")
    
    response = client.call_simple(
        system_prompt="你是一个专业的编程助手",
        user_content="请用Python写一个快速排序算法"
    )
    
    print(f"响应: {response[:200]}...")


def example_2_use_default():
    """示例2: 使用默认配置（GPT-3.5）"""
    print("\n【示例2】使用默认配置（GPT-3.5）")
    print("-" * 50)
    
    client = create_llm_client()  # 不指定 config_name，使用默认配置
    
    response = client.call_simple(
        system_prompt="你是一个翻译助手",
        user_content="将以下英文翻译成中文: Hello, World!"
    )
    
    print(f"响应: {response}")


def example_3_custom_config():
    """示例3: 使用预定义配置并覆盖部分参数"""
    print("\n【示例3】使用预定义配置并覆盖参数")
    print("-" * 50)
    
    client = create_llm_client(
        config_name="qwen3-32b",  # 基础配置
        temperature=0.8,          # 覆盖 temperature
        timeout=120,              # 覆盖 timeout
    )
    
    response = client.call_simple(
        system_prompt="你是一个创意写作助手",
        user_content="写一个关于人工智能的小故事（50字以内）"
    )
    
    print(f"响应: {response}")


def example_4_list_configs():
    """示例4: 列出所有可用的配置"""
    print("\n【示例4】所有可用的预定义配置")
    print("-" * 50)
    
    for name, config in MODEL_CONFIGS.items():
        print(f"配置名称: {name}")
        print(f"  模型: {config['model']}")
        print(f"  地址: {config['base_url']}")
        print(f"  API Key: {config['api_key'][:20]}..." if config['api_key'] else "  API Key: 未设置")
        print()


def example_5_manual_config():
    """示例5: 完全手动配置（不使用预定义配置）"""
    print("\n【示例5】完全手动配置")
    print("-" * 50)
    
    # 不使用 config_name，手动指定所有参数
    client = create_llm_client(
        model="qwen3-32b-lb-pv",
        base_url="http://10.9.42.174:3000/v1",
        api_key="sk-GdqVnpIJe597WlgwvjkY2kTARinXx8RzJ0T0Vq0h6TsSMj7A",
        temperature=0.5,
        timeout=60
    )
    
    response = client.call_simple(
        system_prompt="你是一个数学助手",
        user_content="计算 123 * 456 = ?"
    )
    
    print(f"响应: {response}")


def example_6_switch_model():
    """示例6: 在不同模型之间切换"""
    print("\n【示例6】在不同模型之间切换")
    print("-" * 50)
    
    # 使用 Qwen3
    qwen_client = create_llm_client(config_name="qwen3-32b")
    qwen_response = qwen_client.call_simple(
        system_prompt="你是一个助手",
        user_content="用一句话介绍你自己"
    )
    print(f"Qwen3: {qwen_response[:100]}...")
    
    # 切换到默认模型
    default_client = create_llm_client()
    default_response = default_client.call_simple(
        system_prompt="你是一个助手",
        user_content="用一句话介绍你自己"
    )
    print(f"默认: {default_response[:100]}...")


if __name__ == "__main__":
    print("=" * 60)
    print("LLM 客户端使用示例")
    print("=" * 60)
    
    # 运行所有示例
    example_4_list_configs()  # 先显示配置列表
    
    # 取消注释以运行各个示例
    example_1_use_qwen3()
    example_2_use_default()
    example_3_custom_config()
    example_5_manual_config()
    example_6_switch_model()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成")
    print("=" * 60)
