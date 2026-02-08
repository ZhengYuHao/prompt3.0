# LLM 客户端配置指南

## 快速开始

### 1. 使用预定义配置（推荐）

```python
from llm_client import create_llm_client

# 使用 Qwen3-32B 配置
client = create_llm_client(config_name="qwen3-32b")
response = client.call_simple("你是谁", "你好")
```

### 2. 使用默认配置

```python
# 使用默认的 GPT-3.5 配置
client = create_llm_client()
```

### 3. 配置并覆盖参数

```python
# 使用 Qwen3 配置，但覆盖 temperature
client = create_llm_client(
    config_name="qwen3-32b",
    temperature=0.8,
    timeout=120
)
```

## 可用的预定义配置

| 配置名称 | 模型 | 地址 | API Key 来源 |
|---------|------|------|-------------|
| `default` | gpt-3.5-turbo | `LLM_BASE_URL` 环境变量 | `LLM_API_KEY` 环境变量 |
| `gpt-3.5` | gpt-3.5-turbo | `LLM_BASE_URL` 环境变量 | `LLM_API_KEY` 环境变量 |
| `gpt-4` | gpt-4 | `LLM_BASE_URL` 环境变量 | `LLM_API_KEY` 环境变量 |
| `qwen3-32b` | qwen3-32b-lb-pv | `QWEN_BASE_URL` 环境变量 | `QWEN_API_KEY` 环境变量 |
| `qwen3-custom` | qwen3-32b-lb-pv | `QWEN_BASE_URL` 环境变量 | `QWEN_API_KEY` 环境变量 |

## 环境变量配置

在项目根目录创建 `.env` 文件：

```env
# GPT 相关配置
LLM_BASE_URL=https://api.rcouyi.com/v1
LLM_API_KEY=your-api-key-here

# Qwen 相关配置
QWEN_BASE_URL=http://10.9.42.174:3000/v1
QWEN_API_KEY=sk-GdqVnpIJe597WlgwvjkY2kTARinXx8RzJ0T0Vq0h6TsSMj7A
```

**注意**：`.env` 文件应该添加到 `.gitignore`，避免敏感信息泄露。

## 手动配置（不使用预定义）

如果不想使用预定义配置，可以手动指定所有参数：

```python
client = create_llm_client(
    model="qwen3-32b-lb-pv",
    base_url="http://10.9.42.174:3000/v1",
    api_key="your-api-key",
    temperature=0.5,
    timeout=60
)
```

## 添加新的模型配置

在 `llm_client.py` 中的 `MODEL_CONFIGS` 字典添加新配置：

```python
MODEL_CONFIGS = {
    # ... 现有配置 ...
    
    "new-model": {
        "model": "your-model-name",
        "base_url": os.getenv("NEW_MODEL_BASE_URL", "http://your-url:3000/v1"),
        "api_key": os.getenv("NEW_MODEL_API_KEY", "default-key"),
    },
}
```

然后在 `LLMModel` 枚举中添加模型：

```python
class LLMModel(Enum):
    # ... 现有模型 ...
    NEW_MODEL = "your-model-name"
```

## 使用示例

查看 `example_llm_usage.py` 文件获取更多使用示例：

```bash
python example_llm_usage.py
```

## 常见问题

### Q: 如何切换到其他模型？

```python
# 使用 config_name 参数快速切换
client = create_llm_client(config_name="qwen3-32b")
```

### Q: API Key 从哪里读取？

- 如果使用预定义配置：优先从环境变量读取，如果未设置则使用默认值
- 如果手动配置：直接使用提供的参数值

### Q: 如何检查当前使用的是哪个配置？

查看日志输出，启动时会显示：
```
[LLM] 使用预定义配置: qwen3-32b
[LLM]   模型: qwen3-32b-lb-pv
[LLM]   地址: http://10.9.42.174:3000/v1
```

## 模型参数说明

| 参数 | 说明 | 默认值 | 范围 |
|------|------|--------|------|
| `model` | 模型名称 | gpt-3.5-turbo | - |
| `base_url` | API 基础地址 | 从配置读取 | - |
| `api_key` | API 密钥 | 从配置读取 | - |
| `temperature` | 温度参数（控制随机性） | 0.1 | 0.0-2.0 |
| `timeout` | 请求超时时间（秒） | 60 | - |
| `max_retries` | 最大重试次数 | 3 | - |

**temperature 说明：**
- 0.0：输出最确定，重复性好
- 0.5：平衡确定性和创造性
- 1.0+：输出更有创造性，但可能不稳定
