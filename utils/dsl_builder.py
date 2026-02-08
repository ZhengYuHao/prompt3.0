"""
DSL 代码构建器（代码主导，LLM 辅助）
用于 Prompt 3.0 阶段的 DSL 转译优化
"""

import re
from typing import List, Dict, Optional


class DSLBuilder:
    """DSL 代码构建器（代码层主导，LLM 辅助）"""

    # 自然语言到 DSL 模式的映射
    NL_PATTERNS = {
        # IF 条件
        (r'如果(.+?)，?就(.+)', 'IF {condition}\n    {action}\nENDIF'),
        (r'如果(.+?)，?那么(.+)', 'IF {condition}\n    {action}\nENDIF'),
        (r'当(.+?)时，?(.+)', 'IF {condition}\n    {action}\nENDIF'),

        # FOR 循环
        (r'对(.+?)中每个(.+?)，?(.+)', 'FOR {{item}} IN {{collection}}\n    {action}\nENDFOR'),
        (r'遍历(.+?)，?(.+)', 'FOR {{item}} IN {{collection}}\n    {action}\nENDFOR'),

        # 函数调用
        (r'调用(.+?)函数', 'CALL {function_name}()'),
        (r'生成(.+?)', 'CALL generate_{thing}()'),
        (r'返回(.+?)', 'RETURN {expression}'),
    }

    @classmethod
    def parse_with_patterns(cls, logic_text: str) -> Optional[str]:
        """
        使用预定义模式解析自然语言逻辑

        Args:
            logic_text: 逻辑文本

        Returns:
            DSL 代码或 None（如果无法解析）
        """
        dsl_lines = []
        lines = logic_text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            matched = False
            for pattern, template in cls.NL_PATTERNS:
                match = re.match(pattern, line)
                if match:
                    # 提取组并填充模板
                    groups = match.groups()
                    try:
                        dsl_line = template.format(*groups)
                        dsl_lines.append(dsl_line)
                        matched = True
                        break
                    except Exception:
                        continue

            if not matched:
                # 无法解析的行，标记为需要 LLM 处理
                return None

        if dsl_lines:
            return '\n'.join(dsl_lines)
        return None

    @classmethod
    def build_from_variables(cls, variables: List[Dict], logic_text: str) -> str:
        """
        从变量定义和逻辑文本构建 DSL

        策略：
        1. 使用代码生成 DEFINE 语句
        2. 使用模式匹配生成控制流
        3. 只在必要时调用 LLM

        Args:
            variables: 变量列表
            logic_text: 逻辑文本

        Returns:
            DSL 代码
        """
        dsl_parts = []

        # 1. 生成 DEFINE 语句（代码层，100%确定）
        dsl_parts.append("# 配置参数定义")
        for var in variables:
            var_def = f'DEFINE {{{{var["variable"]}}}}: {var["type"]}'
            if 'value' in var and var['value'] is not None:
                var_def += f' = {var["value"]}'
            dsl_parts.append(var_def)

        dsl_parts.append("")

        # 2. 尝试用模式匹配解析逻辑（代码层）
        pattern_dsl = cls.parse_with_patterns(logic_text)
        if pattern_dsl:
            dsl_parts.append(pattern_dsl)
            return '\n'.join(dsl_parts)

        # 3. 模式匹配失败，回退到 LLM（极简 Prompt）
        dsl_parts.append("# 逻辑实现")
        dsl_parts.append(cls._llm_translate(logic_text, variables))

        return '\n'.join(dsl_parts)

    @classmethod
    def _llm_translate(cls, logic_text: str, variables: List[Dict]) -> str:
        """
        使用 LLM 翻译逻辑（极简 Prompt）

        Args:
            logic_text: 逻辑文本
            variables: 变量列表

        Returns:
            DSL 代码
        """
        # 极简 Prompt（不包含语法文档）
        prompt = f"""将以下自然语言逻辑转换为 DSL 代码。

可用变量：
{chr(10).join(f'  - {{{{v["variable"]}}}} ({v["type"]})' for v in variables)}

DSL 语法：
- IF condition: ... ENDIF
- FOR {{item}} IN {{collection}}: ... ENDFOR
- CALL function_name(arg1, arg2)
- RETURN {{variable}}

逻辑描述：
{logic_text}

只输出 DSL 代码，不要任何解释。"""

        from llm_client import create_llm_client
        llm_client = create_llm_client(use_mock=False)
        response = llm_client.call(prompt, logic_text, temperature=0.1)

        return response.content.strip()
