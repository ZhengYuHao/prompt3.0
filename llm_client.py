"""
统一的 LLM 客户端模块
提供 OpenAI 兼容的 API 调用接口，供所有模块共用
"""

import os
import json
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum
from logger import info, warning, error, debug
from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore


# ============================================================================
# 配置常量
# ============================================================================

# 加载环境变量
load_dotenv()

# 从环境变量读取配置，提供默认值
DEFAULT_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "https://api.rcouyi.com/v1"
)
DEFAULT_API_KEY = os.getenv(
    "LLM_API_KEY",
    ""  # 默认为空，强制从环境变量配置
)


class LLMModel(Enum):
    """支持的模型枚举"""
    GPT_35_TURBO = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo"
    QWEN3_32B = "qwen3-32b-lb-pv"


# ============================================================================
# 预定义模型配置
# ============================================================================

MODEL_CONFIGS = {
    "default": {
        "model": LLMModel.GPT_35_TURBO.value,
        "base_url": os.getenv("LLM_BASE_URL", "https://api.rcouyi.com/v1"),
        "api_key": os.getenv("LLM_API_KEY", ""),
    },
    "gpt-3.5": {
        "model": LLMModel.GPT_35_TURBO.value,
        "base_url": os.getenv("LLM_BASE_URL", "https://api.rcouyi.com/v1"),
        "api_key": os.getenv("LLM_API_KEY", ""),
    },
    "gpt-4": {
        "model": LLMModel.GPT_4.value,
        "base_url": os.getenv("LLM_BASE_URL", "https://api.rcouyi.com/v1"),
        "api_key": os.getenv("LLM_API_KEY", ""),
    },
    "qwen3-32b": {
        "model": LLMModel.QWEN3_32B.value,
        "base_url": os.getenv("QWEN_BASE_URL", "http://10.9.42.174:3000/v1"),
        "api_key": os.getenv("QWEN_API_KEY", "sk-GdqVnpIJe597WlgwvjkY2kTARinXx8RzJ0T0Vq0h6TsSMj7A"),
    },
    "qwen3-custom": {
        "model": LLMModel.QWEN3_32B.value,
        "base_url": os.getenv("QWEN_BASE_URL", "http://10.9.42.174:3000/v1"),
        "api_key": os.getenv("QWEN_API_KEY", "sk-GdqVnpIJe597WlgwvjkY2kTARinXx8RzJ0T0Vq0h6TsSMj7A"),
    },
}


@dataclass
class LLMResponse:
    """LLM 响应数据类"""
    content: str  # 响应内容
    model: str  # 使用的模型
    usage: Optional[Dict[str, int]] = None  # token 使用情况
    raw_response: Optional[Any] = None  # 原始响应对象


# ============================================================================
# 统一 LLM 客户端
# ============================================================================

class UnifiedLLMClient:
    """
    统一的 LLM 客户端
    
    功能：
    - 提供标准化的 API 调用接口
    - 支持多种调用模式（普通对话、结构化输出、实体抽取等）
    - 统一的错误处理和日志记录
    """
    
    def __init__(
        self,
        model: str = LLMModel.QWEN3_32B.value,
        temperature: float = 0.1,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 60
    ):
        """
        初始化 LLM 客户端
        
        Args:
            model: 模型名称
            temperature: 温度参数（0-2，越低越确定性）
            base_url: API 基础 URL
            api_key: API 密钥
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
        """
        self.model = model
        self.temperature = temperature
        self.base_url = base_url or os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL)
        self.api_key = api_key or os.environ.get("LLM_API_KEY", DEFAULT_API_KEY)
        self.max_retries = max_retries
        self.timeout = timeout
        self._client: Optional["OpenAI"] = None
    
    def _get_client(self) -> "OpenAI":
        """获取或创建 OpenAI 客户端实例"""
        if OpenAI is None:
            raise RuntimeError("请先安装 openai: pip install openai")
        if self._client is None:
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=self.timeout
            )
        return self._client
    
    def _clean_llm_response(self, content: str) -> str:
        """
        清理 LLM 响应中的格式标签和脏数据

        Args:
            content: 原始 LLM 响应内容

        Returns:
            清理后的内容
        """
        import re

        # 移除完整的格式标签（包括角色名）
        # 匹配格式：<|im_start|>role 或 <|im_end|>
        patterns_to_remove = [
            r'<\|im_start\|>\s*\w+\s*',  # <|im_start|>role 格式
            r'<\|im_end\|>',              # <|im_end|> 格式
            r'<\|.*?\|>',                 # 其他 <|xxx|> 格式的标签
            r'<think>.*?</think>',        # Qwen 思考过程标签
            r'<思考>.*?</思考>',          # 中文思考过程标签
        ]

        cleaned = content
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL)

        # 清理多余的空白字符
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)  # 多个空行变成两个

        # 清理开头的空白字符（包括换行符、空格、制表符、软回车等）
        cleaned = re.sub(r'^[\s\r\n\t\u2028\u2029]+', '', cleaned)

        # 清理结尾的空白字符
        cleaned = re.sub(r'[\s\r\n\t\u2028\u2029]+$', '', cleaned)

        return cleaned

    def _suppress_thought_process(self, user_content: str) -> str:
        """
        在用户提示词末尾添加指令，抑制模型的思考过程输出

        Args:
            user_content: 原始用户提示词

        Returns:
            添加了抑制指令的提示词
        """
        suppress_instruction = """

【关键要求】
1. 直接输出最终结果，不展示思考过程
2. 禁止使用以下任何标记：|im_start|>、|im_end|>、<思考>、</思考> 等
3. 禁止使用引导词：好的、我现在需要、接下来、首先、然后等
4. 输出内容必须符合要求的格式
5. 保持输出简洁精确，不要多余解释
"""

        return user_content + suppress_instruction

    def call(
        self,
        system_prompt: str,
        user_content: str,
        temperature: Optional[float] = None,
        model: Optional[str] = None
    ) -> LLMResponse:
        """
        基础对话调用

        Args:
            system_prompt: 系统提示词
            user_content: 用户输入
            temperature: 可选的温度覆盖
            model: 可选的模型覆盖

        Returns:
            LLMResponse 对象
        """
        _model = model or self.model
        _temp = temperature if temperature is not None else self.temperature

        # 如果是千问模型，在系统提示词中添加强抑制指令
        if "qwen" in _model.lower():
            suppress_thought = """

【禁止输出思考过程】
- 直接输出最终结果
- 严禁输出推理步骤、思考过程或中间想法
- 严禁使用"好的"、"我现在需要"、"接下来"等引导词
- 只输出符合要求格式的内容
- 输出必须简洁精确
"""
            system_prompt = system_prompt + suppress_thought

        info(f"[LLM调用] 模型: {_model}, Temperature: {_temp}")
        debug(f"[System] {system_prompt[:100]}...")
        debug(f"[User] {user_content[:100]}...")

        client = self._get_client()
        
        for attempt in range(self.max_retries):
            try:
                resp = client.chat.completions.create(
                    model=_model,
                    temperature=_temp,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                )
                
                content = (resp.choices[0].message.content or "").strip()

                # 清理响应中的格式标签和脏数据
                content = self._clean_llm_response(content)

                usage = None
                if hasattr(resp, 'usage') and resp.usage:
                    usage = {
                        "prompt_tokens": resp.usage.prompt_tokens,
                        "completion_tokens": resp.usage.completion_tokens,
                        "total_tokens": resp.usage.total_tokens
                    }

                debug(f"[LLM响应] 长度: {len(content)} 字符")
                
                return LLMResponse(
                    content=content,
                    model=_model,
                    usage=usage,
                    raw_response=resp
                )
                
            except Exception as e:
                warning(f"LLM 调用失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    error(f"LLM 调用最终失败: {e}")
                    raise
        
        raise RuntimeError("LLM 调用失败，已超过最大重试次数")
    
    def call_simple(
        self,
        system_prompt: str,
        user_content: str,
        temperature: Optional[float] = None
    ) -> str:
        """
        简单调用，直接返回字符串
        
        Args:
            system_prompt: 系统提示词
            user_content: 用户输入
            temperature: 可选的温度覆盖
            
        Returns:
            响应文本
        """
        response = self.call(system_prompt, user_content, temperature)
        return response.content
    
    def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        实体抽取
        
        Args:
            text: 待抽取文本
            entity_types: 期望的实体类型列表
            
        Returns:
            实体列表
        """
        types_hint = ""
        if entity_types:
            types_hint = f"实体类型限定: {', '.join(entity_types)}\n"
        
        system_prompt = f"""你是一个实体抽取专家。你的任务是从文本中识别需要动态调整的"变量"。

{types_hint}核心原则：
1. 变量 = 可配置参数（具体数字、时间值、可选项）
2. 常量 = 固定需求描述、功能列表、技术限制

识别规则：
✅ 提取为变量：
- 具体数字：3年、5人、50万、20轮
- 时间相关：2周、8周
- 可选项：Python/Java、Milvus/Pinecone
- 专有名词：K8s、LangChain、RAG
- 技术栈列表：如 "LangChain、Milvus、FastAPI"

❌ 不提取（视为常量）：
- 功能需求描述："需要支持多轮对话"、"用大模型做底座"、"支持中英文双语"
- 固定配置："响应时间控制在2秒以内"、"上下文窗口存20轮"（如果没有数字）
- 架构描述："微服务架构"、"分布式系统"
- 通用动词："需要"、"要"、"支持"、"实现"（单独出现时）

特殊情况处理：
- "需要支持多轮对话，上下文窗口存20轮" → 只提取 "20轮" 作为变量
- "团队5个人，其中2个Java，3个Python" → 只提取 "5个人" 为 team_size，不拆分 Java/Python 人数
- "用LangChain、Milvus、FastAPI" → 整体提取为 tech_stack 变量，类型为 List

输出格式（JSON 数组）:
[
  {{
    "name": "变量英文名(snake_case)",
    "original_text": "原文精确片段",
    "start_index": 起始位置,
    "end_index": 结束位置,
    "type": "数据类型",
    "value": "当前值"
  }}
]

示例对比：

示例1:
原文: "项目团队5个人，其中2个Java，3个Python"
✓ 正确提取: [{{"name": "team_size", "original_text": "5个人", "value": 5, "type": "Integer"}}]
✗ 错误提取: [{{"name": "java_developers", "original_text": "2个Java", ...}}, {{"name": "python_developers", "original_text": "3个Python", ...}}]

示例2:
原文: "需要支持多轮对话，上下文窗口存20轮"
✓ 正确提取: [{{"name": "context_rounds", "original_text": "20轮", "value": 20, "type": "Integer"}}]
✗ 错误提取: [{{"name": "multi_turn_dialogue", "original_text": "多轮对话", ...}}]

示例3:
原文: "用LangChain、Milvus、FastAPI"
✓ 正确提取: [{{"name": "tech_stack", "original_text": "LangChain、Milvus、FastAPI", "value": ["LangChain", "Milvus", "FastAPI"], "type": "List"}}]
✗ 错误: 将每个技术单独提取为变量

示例4:
原文: "支持中英文双语，响应时间控制在2秒以内"
✓ 正确提取: [{{"name": "response_time_limit", "original_text": "2秒", "value": 2, "type": "Integer"}}]
✗ 错误提取: [{{"name": "bilingual_support", "original_text": "中英文双语", ...}}]

严格规则:
1. 只输出 JSON 数组格式，不要有任何其他文字
2. 必须原样返回原文片段，严禁同义词替换
3. 必须返回精确的 start_index 和 end_index
4. 数据类型仅限: String, Integer, Boolean, List, Enum
5. 优先识别最长匹配项（如 "5个人" 优于 "5"）
6. 如果描述包含动词+名词但没有数字，大概率是固定需求，不要提取"""
        
        response = self.call(system_prompt, text)

        # 打印原始响应用于调试
        debug(f"[实体抽取] LLM 原始响应:\n{response.content}\n")

        try:
            entities = json.loads(response.content)
            if isinstance(entities, list):
                info(f"[实体抽取] 识别到 {len(entities)} 个实体")
                return entities
            else:
                warning(f"[实体抽取] 响应格式不是数组，实际类型: {type(entities)}")
                return []
        except json.JSONDecodeError as e:
            warning(f"[实体抽取] JSON 解析失败: {e}")
            return []
    
    def detect_ambiguity(self, text: str) -> Optional[str]:
        """
        检测文本歧义
        
        Args:
            text: 待检测文本
            
        Returns:
            如果存在歧义则返回描述，否则返回 None
        """
        system_prompt = """检测以下文本是否存在严重的语义歧义或多重解读可能。

判断标准:
- 句法结构是否存在歧义(如定语从句归属不明)
- 指代对象是否清晰
- 逻辑关系是否唯一

如果文本清晰无歧义,请仅回复 "PASS"
如果存在歧义,请简短描述歧义点(不超过30字)

示例:
输入: "咬死了猎人的狗"
输出: "无法确定主语,可能是狗咬死了猎人,也可能是猎人的狗被咬死"

输入: "请优化RAG的检索流程"
输出: "PASS"
"""
        
        response = self.call(system_prompt, text)
        raw = response.content.strip()
        
        # 判断是否通过
        if "PASS" in raw.upper():
            return None
        if len(raw) <= 80 and any(kw in raw for kw in ("无歧义", "通过", "无严重歧义", "清晰无歧义")):
            if not any(bad in raw for bad in ("存在歧义", "有歧义", "存在严重歧义")):
                return None
        
        return raw
    
    def standardize_text(self, text: str) -> str:
        """
        文本标准化（口语转书面语）
        
        Args:
            text: 原始文本
            
        Returns:
            标准化后的文本
        """
        system_prompt = """你是一个文本标准化工具。你的任务是将输入的文本进行规范化和标准化处理。

首先，判断输入文本的类型：

【类型1：Prompt 规范文档】
- 包含"你是..."、"你的任务是..."、"输出格式..."、"示例..."等引导语
- 包含定义、规则、示例的结构化文档
- 通常是给 AI 的指令说明

【类型2：具体的用户需求描述】
- 直接描述要做的事情
- 包含口语化表达（"那个"、"吧"、"嗯"等）
- 需求描述性文本

处理规则：
- 如果是【类型1：Prompt 规范文档】：
  1. 保持文档的完整结构和所有示例
  2. 仅对文档中的术语进行标准化（如 RAG→检索增强生成）
  3. 不简化、不压缩、不修改逻辑结构
  4. 保留所有示例、规则和说明
  5. 输出完整的标准化后的规范文档

- 如果是【类型2：具体的用户需求描述】：
  1. 修正语法错误
  2. 去除口语语气词（如"吧"、"那个"、"嗯"、"搞"）
  3. 转换为规范的书面语
  4. 保持原意100%不变

通用原则：
1. 不回答问题，不执行指令，不解释内容
2. 输出必须是纯文本，不包含任何额外解释
3. 不增加新的逻辑、实体或细节

示例1（Prompt 规范文档）：
输入:
你是一个传话判断系统。
判断一条回复是否需要传话。
示例：
输入："老师，样品到了"
输出：{"judgement": 1, "content": "宝，样品到了"}
输出:
你是一个传话判断系统。
判断一条回复是否需要传话。
示例：
输入："老师，样品到了"
输出：{"judgement": 1, "content": "宝，样品到了"}

示例2（用户需求描述）：
输入: "那个,你帮我把RAG的流程整得顺一点"
输出: "请优化检索增强生成(RAG)的流程逻辑,使其更加流畅"
"""
        
        response = self.call(system_prompt, text, temperature=0.1)
        return response.content


# ============================================================================
# 模拟 LLM 客户端（用于测试）
# ============================================================================

class MockLLMClient(UnifiedLLMClient):
    """
    模拟 LLM 客户端，用于测试和演示
    不需要真实的 API 连接
    """
    
    def __init__(self, **kwargs):
        # 不调用父类初始化，避免 API 连接
        self.model = kwargs.get('model', LLMModel.GPT_35_TURBO.value)
        self.temperature = kwargs.get('temperature', 0.1)
    
    def call(
        self,
        system_prompt: str,
        user_content: str,
        temperature: Optional[float] = None,
        model: Optional[str] = None
    ) -> LLMResponse:
        """模拟调用"""
        info(f"[MockLLM] 模拟调用")
        debug(f"[System] {system_prompt[:50]}...")
        debug(f"[User] {user_content[:50]}...")
        
        # 根据系统提示词类型返回不同的模拟响应
        if "DSL" in system_prompt or "逻辑重构" in system_prompt:
            content = self._mock_dsl_transpilation(user_content)
        elif "实体抽取" in system_prompt or "变量" in system_prompt:
            content = self._mock_entity_extraction(user_content)
        elif "歧义" in system_prompt:
            content = self._mock_ambiguity_detection(user_content)
        elif "标准化" in system_prompt or "书面语" in system_prompt:
            content = self._mock_standardization(user_content)
        else:
            content = f"[模拟响应] {user_content[:50]}..."
        
        return LLMResponse(
            content=content,
            model=self.model,
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        )
    
    def _mock_entity_extraction(self, text: str) -> str:
        """模拟实体抽取"""
        import re
        entities = []
        
        # 识别数字+单位模式
        for match in re.finditer(r'(\d+)(年|周|月|天|小时|分钟)', text):
            entities.append({
                "name": f"duration_{match.group(2)}",
                "original_text": match.group(0),
                "start_index": match.start(),
                "end_index": match.end(),
                "type": "Integer",
                "value": int(match.group(1))
            })
        
        # 识别专业术语
        tech_terms = ["Java程序员", "Python", "数据分析", "机器学习", "前端开发"]
        for term in tech_terms:
            if term in text:
                idx = text.find(term)
                entities.append({
                    "name": f"tech_term_{len(entities)}",
                    "original_text": term,
                    "start_index": idx,
                    "end_index": idx + len(term),
                    "type": "String",
                    "value": term
                })
        
        return json.dumps(entities, ensure_ascii=False)
    
    def _mock_ambiguity_detection(self, text: str) -> str:
        """模拟歧义检测"""
        ambiguous_patterns = ["意思", "那个", "随便", "看着办", "差不多"]
        for pattern in ambiguous_patterns:
            if pattern in text:
                return f"检测到歧义表达: '{pattern}' 含义不明确"
        return "PASS"
    
    def _mock_standardization(self, text: str) -> str:
        """模拟文本标准化"""
        # 简单的替换规则
        result = text
        replacements = {
            "搞一个": "开发一个",
            "弄一下": "处理",
            "那个": "",
            "吧": "",
            "嗯": "",
        }
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result.strip()

    def _mock_dsl_transpilation(self, user_content: str) -> str:
        """模拟DSL转译：解析用户输入并生成DSL伪代码"""
        import re
        
        # 解析变量定义
        variables = []
        in_variable_section = False
        lines = user_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('【变量定义】'):
                in_variable_section = True
                continue
            elif line.startswith('【'):
                # 进入其他部分
                in_variable_section = False
                continue
            
            if in_variable_section and line.startswith('-'):
                # 格式: - var_name: Type [= value]
                match = re.match(r'-\s*(\w+):\s*(\w+)(?:\s*=\s*(.+))?', line)
                if match:
                    var_name, var_type, initial_value = match.groups()
                    variables.append({
                        'name': var_name,
                        'type': var_type,
                        'initial_value': initial_value
                    })
        
        # 解析逻辑描述（简单关键词检测）
        logic = ""
        in_logic_section = False
        for line in lines:
            line = line.strip()
            if line.startswith('【逻辑描述】'):
                in_logic_section = True
                continue
            elif line.startswith('【'):
                in_logic_section = False
                continue
            
            if in_logic_section:
                logic = line
                break
        
        # 构建DSL代码
        dsl_lines = []
        
        # 1. 变量定义
        for var in variables:
            if var['initial_value']:
                dsl_lines.append(f"DEFINE {{{{{var['name']}}}}}: {var['type']} = {var['initial_value']}")
            else:
                dsl_lines.append(f"DEFINE {{{{{var['name']}}}}}: {var['type']}")
        
        # 确保 result 变量被定义（如果尚未定义）
        result_var_defined = any(var['name'] == 'result' for var in variables)
        if not result_var_defined:
            dsl_lines.append("DEFINE {{result}}: String")
        
        # 2. 根据逻辑描述生成控制流
        if '如果' in logic or '若' in logic:
            # 简单条件语句
            dsl_lines.append("")
            dsl_lines.append("# 条件判断")
            dsl_lines.append("IF {{condition}} == true")
            dsl_lines.append("    {{result}} = CALL process_success()")
            dsl_lines.append("ELSE")
            dsl_lines.append("    {{result}} = CALL process_failure()")
            dsl_lines.append("ENDIF")
        
        if '对于每个' in logic or '遍历' in logic:
            # 简单循环
            dsl_lines.append("")
            dsl_lines.append("# 循环处理")
            dsl_lines.append("FOR {{item}} IN {{collection}}")
            dsl_lines.append("    {{result}} = CALL process_item({{item}})")
            dsl_lines.append("ENDFOR")
        
        # 如果没有生成任何控制流，添加一个默认的CALL
        if len(dsl_lines) <= len(variables) + (1 if not result_var_defined else 0):
            dsl_lines.append("")
            dsl_lines.append("# 默认处理")
            dsl_lines.append("{{result}} = CALL generate_output()")
        
        # 3. 添加返回语句
        dsl_lines.append("")
        dsl_lines.append("RETURN {{result}}")
        
        return '\n'.join(dsl_lines)


# ============================================================================
# 工厂函数
# ============================================================================

def create_llm_client(
    use_mock: bool = False,
    config_name: Optional[str] = None,
    **kwargs
) -> UnifiedLLMClient:
    """
    创建 LLM 客户端的工厂函数
    
    Args:
        use_mock: 是否使用模拟客户端
        config_name: 预定义配置名称，可选值: "default", "gpt-3.5", "gpt-4", "qwen3-32b"
        **kwargs: 传递给客户端的其他参数（可覆盖配置中的值）
        
    Returns:
        LLM 客户端实例
        
    Examples:
        # 使用默认配置
        client = create_llm_client()
        
        # 使用预定义的 Qwen3 配置
        client = create_llm_client(config_name="qwen3-32b")
        
        # 使用配置但覆盖部分参数
        client = create_llm_client(config_name="qwen3-32b", temperature=0.5)
    """
    if use_mock:
        info("[LLM] 使用模拟客户端")
        return MockLLMClient(**kwargs)
    
    # 如果指定了配置名称，则应用配置
    if config_name:
        if config_name not in MODEL_CONFIGS:
            available = ", ".join(MODEL_CONFIGS.keys())
            raise ValueError(f"未知的配置名称: {config_name}, 可用配置: {available}")
        
        config = MODEL_CONFIGS[config_name]
        info(f"[LLM] 使用预定义配置: {config_name}")
        info(f"[LLM]  模型: {config['model']}")
        info(f"[LLM]  地址: {config['base_url']}")
        
        # 合并配置：预定义配置 + kwargs（kwargs优先级更高）
        merged_kwargs = {**config, **kwargs}
        return UnifiedLLMClient(**merged_kwargs)
    else:
        info("[LLM] 使用真实客户端（自定义配置）")
        return UnifiedLLMClient(**kwargs)


# ============================================================================
# 异步调用支持（可选）
# ============================================================================

async def invoke_function(func_name: str, **kwargs) -> Any:
    """
    异步函数调用接口（供 generated_workflow.py 使用）
    
    Args:
        func_name: 函数名称
        **kwargs: 函数参数
        
    Returns:
        函数执行结果
    """
    client = create_llm_client()
    
    # 构建调用提示词
    system_prompt = f"执行函数: {func_name}"
    user_content = json.dumps(kwargs, ensure_ascii=False)
    
    response = client.call(system_prompt, user_content)
    return response.content


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    # 方式1: 使用预定义配置（推荐）
    print("=" * 60)
    print("方式1: 使用预定义配置")
    print("=" * 60)
    
    # 使用 Qwen3-32B 配置
    qwen_client = create_llm_client(config_name="qwen3-32b")
    response = qwen_client.call_simple("你是一个助手", "你好，你是谁？")
    info(f"Qwen3 响应: {response[:100]}...")
    
    # 方式2: 使用默认配置
    print("\n" + "=" * 60)
    print("方式2: 使用默认配置")
    print("=" * 60)
    
    default_client = create_llm_client()
    
    # 测试实体抽取
    entities = default_client.extract_entities(
        "请为一位有3年经验的Java程序员生成一个为期2周的Python学习计划"
    )
    info(f"抽取到的实体: {json.dumps(entities, ensure_ascii=False, indent=2)}")
    
    # 测试歧义检测
    ambiguity = default_client.detect_ambiguity("这个需求没啥意思,你看着办")
    info(f"歧义检测结果: {ambiguity}")
    
    # 测试文本标准化
    standardized = default_client.standardize_text("那个,帮我搞一个RAG的应用吧")
    info(f"标准化结果: {standardized}")
    
    # 方式3: 使用配置并覆盖参数
    print("\n" + "=" * 60)
    print("方式3: 使用配置并覆盖参数")
    print("=" * 60)
    
    custom_client = create_llm_client(
        config_name="qwen3-32b",
        temperature=0.8,
        timeout=120
    )
    info("已创建自定义 Qwen3 客户端（temperature=0.8, timeout=120）")
    
    # 显示可用的配置列表
    print("\n" + "=" * 60)
    print("可用的预定义配置:")
    print("=" * 60)
    for name, config in MODEL_CONFIGS.items():
        print(f"- {name}: {config['model']} @ {config['base_url']}")
