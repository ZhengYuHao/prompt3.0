# Prompt 3.0 智能代码生成系统

一个完整的自然语言到可执行代码的智能转换系统，支持口语化输入、结构化建模、DSL 编译和代码生成。

## ✨ 功能特性

### 核心能力

1. **Prompt 1.0 - 智能预处理**
   - 口语化表达标准化
   - 非标准术语识别与映射
   - 多种数据类型提取
   - LLM 语义重构

2. **Prompt 2.0 - 结构化建模**
   - LLM-Layer: 实体智能识别
   - Code-Layer: 幻觉防火墙与存在性校验
   - 强类型清洗与转换
   - 变量冲突解决（最长覆盖原则）
   - 动态模板生成

3. **Prompt 3.0 - DSL 编译**
   - 伪代码到 DSL 转译
   - 依赖分析与死代码检测
   - 循环依赖检测
   - 自动纠错机制

4. **Prompt 4.0 - 代码生成**
   - 模块聚类（支持多种策略）
   - Python 代码合成
   - 主工作流编排
   - 语法验证

### 处理流程

```
用户输入（口语化）
    ↓
[Stage 1] Prompt 1.0 预处理 → 标准化文本
    ↓
[Stage 2] Prompt 2.0 结构化 → 模板 + 变量表
    ↓
[Stage 3] Prompt 3.0 DSL 编译 → 伪代码
    ↓
[Stage 4] Prompt 4.0 代码生成 → Python 模块
    ↓
可执行的工作流代码
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装步骤

1. **克隆项目**
   ```bash
   cd /path/to/prompt3.0
   ```

2. **创建虚拟环境**（推荐）
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate  # Windows
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量**
   
   复制配置模板：
   ```bash
   cp .env.example .env
   ```
   
   编辑 `.env` 文件，填入你的 API 配置：
   ```env
   LLM_BASE_URL=https://api.rcouyi.com/v1
   LLM_API_KEY=your-api-key-here
   ```

### 运行示例

#### 完整流水线演示

运行从用户输入到代码生成的完整流程：

```bash
python3 demo_full_pipeline.py
```

示例输入：
```
帮我开发一个检索增强生成(RAG)应用，底层采用大型语言模型(LLM)，
处理链需支持三种以上的检索模式。团队有5个人，2个Java开发，3个Python开发。
项目周期8周，预算50万。技术栈用LangChain、Milvus和FastAPI。
需要支持多轮对话（20轮上下文），部署在Kubernetes集群，
采用微服务架构（10个服务）。集成Prometheus监控和ELK日志系统。
支持中英文双语，响应时间控制在2秒以内。
```

#### 单步测试

```bash
# 测试 Prompt 1.0 预处理
python3 demo_step2.py

# 测试 DSL 编译
python3 test_mock_dsl.py

# 测试数据模型
python3 test_models.py

# 查看历史记录
python3 view_history.py
```

## 📁 项目结构

```
prompt3.0/
├── data_models.py              # 统一数据模型定义
├── logger.py                 # 日志模块
├── llm_client.py             # LLM 客户端（支持 OpenAI 兼容 API）
├── history_manager.py         # 历史记录管理
│
├── prompt_preprocessor.py     # Prompt 1.0 预处理模块
├── prompt_structurizer.py     # Prompt 2.0 结构化模块
├── prompt_dslcompiler.py     # Prompt 3.0 DSL 编译器
├── prompt_codegenetate.py     # Prompt 4.0 代码生成器
│
├── pipeline.py               # 流水线封装
├── demo_full_pipeline.py     # 完整流水线演示
├── demo_step2.py          # 单步演示
│
├── processing_history/       # 处理历史记录目录
│   ├── history.json        # 预处理历史
│   └── pipeline_history.json  # 流水线历史
│
├── requirements.txt         # Python 依赖
├── .env.example           # 环境变量模板
└── .env                  # 环境变量配置（不提交）
```

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `LLM_BASE_URL` | LLM API 基础地址 | `https://api.rcouyi.com/v1` | 是 |
| `LLM_API_KEY` | LLM API 密钥 | - | 是 |

### 处理模式

- **dictionary**: 基于预定义词表进行术语映射（推荐）
- **smart**: 纯 LLM 智能处理
- **hybrid**: 混合模式

### 聚类策略

- **io_isolation**: 每个 LLM 调用独立成模块
- **control_flow**: 控制流内聚策略
- **hybrid**: 混合策略（推荐）

## 💡 使用示例

### Python API

```python
from pipeline import PromptPipeline
from data_models import ProcessingMode

# 初始化流水线
pipeline = PromptPipeline(
    mode=ProcessingMode.DICTIONARY,
    use_mock_llm=False  # 使用真实 LLM
)

# 处理用户输入
result = pipeline.process("""
    帮我开发一个RAG应用，用LangChain技术栈，
    团队5个人，项目周期8周。
""")

# 查看结果
print(f"状态: {result.status}")
print(f"模板: {result.prompt20_result.template}")
print(f"变量: {result.prompt20_result.variables}")
```

### 自定义处理

```python
# 仅使用 Prompt 1.0 预处理
from prompt_preprocessor import PromptPreprocessor

preprocessor = PromptPreprocessor()
result = preprocessor.process("用户输入文本")

# 仅使用 Prompt 2.0 结构化
from prompt_structurizer import PromptStructurizer

structurizer = PromptStructurizer()
result = structurizer.process(标准化文本)

# 仅使用 DSL 编译
from prompt_dslcompiler import SelfCorrectionLoop

compiler = SelfCorrectionLoop()
dsl_code = compiler.compile(用户需求)

# 仅使用代码生成
from prompt_codegenetate import WaActCompiler

code_gen = WaActCompiler()
modules, main_code = code_gen.compile(dsl_code)
```

## 📊 历史记录

所有处理结果会自动保存到 `processing_history/` 目录：

- `history.json`: Prompt 1.0 预处理历史
- `pipeline_history.json`: 完整流水线历史

可以使用 `view_history.py` 查看历史记录。

## 🐛 调试与测试

### 使用模拟 LLM

为避免 API 调用消耗，可以启用模拟模式：

```python
# 在 demo_full_pipeline.py 中设置
USE_MOCK = True

# 或在代码中
client = create_llm_client(use_mock=True)
```

### 日志级别

修改 `logger.py` 中的配置：
- `INFO`: 正常信息
- `DEBUG`: 详细调试信息
- `WARNING`: 警告信息
- `ERROR`: 错误信息

## 🔍 故障排除

### 常见问题

1. **ModuleNotFoundError: No module named 'openai'**
   ```bash
   pip install -r requirements.txt
   ```

2. **ModuleNotFoundError: No module named 'dotenv'**
   ```bash
   pip install python-dotenv
   ```

3. **API 调用失败**
   - 检查 `.env` 文件配置
   - 确认 API key 有效性
   - 检查网络连接

4. **语法验证失败**
   - 检查输入文本格式
   - 查看处理历史记录了解详细错误

## 📝 开发指南

### 添加新的处理模块

1. 在相应的模块文件中添加类/函数
2. 在 `data_models.py` 中定义数据模型
3. 在 `pipeline.py` 中集成新模块
4. 更新文档

### 运行测试

```bash
python3 test_models.py
python3 test_mock_dsl.py
```

## 📄 许可证

本项目仅供学习和研究使用。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 联系方式

如有问题，请提交 Issue。

---

**注意**: 请勿将 `.env` 文件提交到代码仓库，API 密钥应妥善保管。
