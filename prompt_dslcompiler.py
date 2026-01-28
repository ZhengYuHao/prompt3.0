"""
S.E.D.E (Software Engineering Driven Prompt Engineering)
第三步：逻辑重构与代码化 - 完整实现

核心理念：将自然语言的"思考逻辑"转换为"可执行的伪代码"
"""

import re
import json
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from copy import deepcopy
from logger import info, warning, error, debug
from llm_client import create_llm_client


# ============================================================
# 第一部分：DSL 语法规范定义
# ============================================================

class VarType(Enum):
    """变量类型枚举"""
    STRING = "String"
    INTEGER = "Integer"
    FLOAT = "Float"
    BOOLEAN = "Boolean"
    LIST = "List"
    DICT = "Dict"
    ANY = "Any"


class DSLSyntax:
    """DSL 语法规范 - 极简、无歧义的领域特定语言"""
    
    # 关键字定义
    KEYWORDS = {
        'DEFINE', 'IF', 'ELSE', 'ELIF', 'ENDIF',
        'FOR', 'ENDFOR', 'WHILE', 'ENDWHILE',
        'CALL', 'RETURN', 'BREAK', 'CONTINUE'
    }
    
    # 运算符定义
    OPERATORS = {
        '==': 'equals',
        '!=': 'not_equals',
        '>': 'greater',
        '<': 'less',
        '>=': 'greater_equal',
        '<=': 'less_equal',
        'AND': 'logical_and',
        'OR': 'logical_or',
        'NOT': 'logical_not',
        'IN': 'contains'
    }
    
    # 语法模式（正则表达式）
    PATTERNS = {
        'DEFINE': r'^DEFINE\s+\{\{(\w+)\}\}\s*:\s*(\w+)(?:\s*=\s*(.+))?$',
        'ASSIGN': r'^\{\{(\w+)\}\}\s*=\s*(.+)$',
        'IF': r'^IF\s+(.+)$',
        'ELIF': r'^ELIF\s+(.+)$',
        'ELSE': r'^ELSE$',
        'ENDIF': r'^ENDIF$',
        'FOR': r'^FOR\s+\{\{(\w+)\}\}\s+IN\s+(.+)$',
        'ENDFOR': r'^ENDFOR$',
        'WHILE': r'^WHILE\s+(.+)$',
        'ENDWHILE': r'^ENDWHILE$',
        'CALL': r'CALL\s+(\w+)\(([^)]*)\)',
        'RETURN': r'^RETURN\s+(.+)$',
        'COMMENT': r'^#(.*)$'
    }
    
    @staticmethod
    def get_syntax_documentation() -> str:
        """获取 DSL 语法文档"""
        return """
# DSL 语法规范 v1.0

## 1. 变量声明与赋值
DEFINE {{variable_name}}: Type [= initial_value]
{{variable_name}} = value

支持类型: String, Integer, Float, Boolean, List, Dict, Any

示例:
DEFINE {{user_name}}: String
DEFINE {{score}}: Integer = 0
DEFINE {{items}}: List = []

## 2. 条件控制
IF condition
    # 代码块
ELIF condition
    # 代码块
ELSE
    # 代码块
ENDIF

条件支持运算符: ==, !=, >, <, >=, <=, AND, OR, NOT, IN

示例:
IF {{score}} >= 90
    {{grade}} = "A"
ELIF {{score}} >= 60
    {{grade}} = "B"
ELSE
    {{grade}} = "C"
ENDIF

## 3. 循环控制
FOR {{item}} IN {{collection}}
    # 代码块
ENDFOR

WHILE condition
    # 代码块
ENDWHILE

示例:
FOR {{user}} IN {{user_list}}
    {{result}} = CALL send_email({{user}})
ENDFOR

## 4. 函数调用（LLM生成接口）
{{result}} = CALL function_name(arg1, arg2, ...)

这是唯一允许调用 LLM 进行自然语言生成的接口。

示例:
{{email_body}} = CALL generate_email({{user_name}}, {{discount}})
{{summary}} = CALL summarize_text({{article}}, max_length=100)

## 5. 返回值
RETURN {{variable}}

## 6. 注释
# 这是注释

## 7. 约束规则
- 所有变量必须先 DEFINE 后使用
- 控制结构必须严格闭合（IF-ENDIF, FOR-ENDFOR）
- 禁止嵌套过深（建议最多3层）
- 变量名使用 {{var}} 格式包裹
- 一行一条语句，禁止分号分隔
"""


# ============================================================
# 第二部分：数据结构定义
# ============================================================

@dataclass
class Variable:
    """变量定义"""
    name: str
    var_type: VarType
    initial_value: Optional[Any] = None
    line_number: int = 0
    
    def __str__(self):
        return f"{{{{name}}}}: {self.var_type.value}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典"""
        return {
            'name': self.name,
            'var_type': self.var_type.value,
            'initial_value': self.initial_value,
            'line_number': self.line_number
        }


@dataclass
class ControlBlock:
    """控制块（IF/FOR等）"""
    block_type: str  # IF, FOR, WHILE
    condition: str
    start_line: int
    end_line: Optional[int] = None
    parent: Optional['ControlBlock'] = None
    children: List['ControlBlock'] = field(default_factory=list)
    const_condition: Optional[bool] = None
    has_else: bool = False


@dataclass
class DSLSchema:
    """DSL 配置：限制可用语法集合"""
    allowed_keywords: Set[str] = field(default_factory=lambda: {
        'DEFINE', 'IF', 'ELSE', 'ELIF', 'ENDIF',
        'FOR', 'ENDFOR', 'WHILE', 'ENDWHILE',
        'CALL', 'RETURN', 'BREAK', 'CONTINUE'
    })

    def is_keyword_allowed(self, keyword: str) -> bool:
        return keyword in self.allowed_keywords


@dataclass
class FunctionCall:
    """函数调用"""
    function_name: str
    arguments: List[str]
    result_var: Optional[str] = None
    line_number: int = 0


@dataclass
class ValidationError:
    """验证错误"""
    line_number: int
    error_type: str
    message: str
    suggestion: Optional[str] = None
    severity: str = "P2"  # P0:致命, P1:严重, P2:警告

    def __str__(self):
        suggestion_text = f"\n  建议: {self.suggestion}" if self.suggestion else ""
        severity_icon = {"P0": "🔴", "P1": "🟡", "P2": "⚪"}.get(self.severity, "")
        return f"{severity_icon}[第{self.line_number}行] {self.error_type}: {self.message}{suggestion_text}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # 分析结果
    defined_variables: Dict[str, Variable] = field(default_factory=dict)
    function_calls: List[FunctionCall] = field(default_factory=list)
    control_blocks: List[ControlBlock] = field(default_factory=list)
    max_nesting_depth: int = 0
    
    def get_report(self) -> str:
        """生成验证报告"""
        report = []
        
        if self.is_valid:
            report.append("✅ 验证通过！DSL 代码符合规范。\n")
        else:
            report.append("❌ 验证失败！发现以下错误：\n")
            for error in self.errors:
                report.append(f"  {error}\n")
        
        if self.warnings:
            report.append("\n⚠️  警告：")
            for warning in self.warnings:
                report.append(f"  - {warning}")
        
        report.append(f"\n📊 代码统计:")
        report.append(f"  - 定义变量: {len(self.defined_variables)} 个")
        report.append(f"  - 函数调用: {len(self.function_calls)} 次")
        report.append(f"  - 控制块: {len(self.control_blocks)} 个")
        report.append(f"  - 最大嵌套深度: {self.max_nesting_depth}")
        
        return "\n".join(report)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典"""
        return {
            'is_valid': self.is_valid,
            'errors': [asdict(error) for error in self.errors],
            'warnings': self.warnings,
            'defined_variables': {name: var.to_dict() for name, var in self.defined_variables.items()},
            'function_calls': [asdict(fc) for fc in self.function_calls],
            'control_blocks': [asdict(cb) for cb in self.control_blocks],
            'max_nesting_depth': self.max_nesting_depth
        }


# ============================================================
# 第三部分：DSL 转译器（Prompt 2.0 → DSL Code）
# ============================================================

class DSLTranspiler:
    """将结构化的 Prompt 2.0 转换为 DSL 伪代码"""
    
    def __init__(self, llm_client=None):
        """
        初始化 DSL 转译器
        
        Args:
            llm_client: LLM 客户端实例，如果为 None 则使用真实客户端
        """
        self.system_prompt = self._build_system_prompt()
        self.llm_client = llm_client or create_llm_client(use_mock=False)
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return f"""你是一个专业的逻辑重构编译器前端。

你的任务是将自然语言描述的逻辑转换为严格的 DSL 伪代码。

{DSLSyntax.get_syntax_documentation()}

**核心原则：**
1. 不要执行任务，只生成代码
2. 将所有"如果...那么..."转换为 IF-ENDIF
3. 将所有"对于每个..."转换为 FOR-ENDFOR
4. 将所有"生成/写/创建"等动作转换为 CALL 函数调用
5. 严格使用 {{{{variable}}}} 包裹所有变量
6. 确保所有变量在使用前都已 DEFINE

**重要约束：**
- 只使用【变量定义】中列出的变量名称
- 绝对不要创造新的变量名称（如 user_input, query_type 等）
- 如果逻辑描述中提到但变量列表中没有，请使用变量定义中已有的最接近的变量名
- 每个变量在使用前必须先用 DEFINE 声明，类型必须匹配给定的类型

**输入格式：**
你会收到包含变量定义和逻辑描述的结构化文本。

**输出格式：**
只输出符合 DSL 规范的伪代码，不要包含任何解释或额外文字。

**代码结构模板：**
```
# 变量定义（必须先定义所有变量）
DEFINE {{variable1}}: Type1 [= value1]
DEFINE {{variable2}}: Type2 [= value2]
...

# 逻辑实现
IF {{condition1}}
    ...
ENDIF

FOR {{item}} IN {{collection}}
    ...
ENDFOR
```
"""
    
    def transpile(self, prompt_2_0: Dict[str, Any]) -> str:
        """
        转译 Prompt 2.0 到 DSL 代码
        
        Args:
            prompt_2_0: {
                'variables': [{'name': 'user_name', 'type': 'String', ...}],
                'logic': '如果用户是VIP，生成折扣邮件，否则生成普通邮件',
                'context': '...'
            }
        
        Returns:
            DSL 伪代码字符串
        """
        # 构建用户输入：将变量定义和逻辑描述组合
        user_content = self._build_user_content(prompt_2_0)
        
        # 调用 LLM 进行转译
        info(f"[DSL转译] 调用 LLM 进行逻辑重构...")
        response = self.llm_client.call(self.system_prompt, user_content)
        dsl_code = response.content.strip()
        
        # 验证响应格式：确保是纯代码，没有额外解释
        dsl_code = self._clean_llm_response(dsl_code)
        
        info(f"[DSL转译] 生成代码长度: {len(dsl_code)} 字符")
        debug(f"[DSL转译] 生成代码:\n{dsl_code}")
        
        return dsl_code
    
    def _build_user_content(self, prompt_2_0: Dict[str, Any]) -> str:
        """构建发送给 LLM 的用户输入"""
        parts = []
        
        # 1. 变量定义部分
        if prompt_2_0.get('variables'):
            parts.append("【变量定义】")
            for var in prompt_2_0['variables']:
                var_def = f"- {var['name']}: {var['type']}"
                if 'default' in var:
                    var_def += f" = {var['default']}"
                parts.append(var_def)
        
        # 2. 逻辑描述部分
        if prompt_2_0.get('logic'):
            parts.append("")
            parts.append("【逻辑描述】")
            parts.append(prompt_2_0['logic'])
        
        # 3. 上下文部分（如果有）
        if prompt_2_0.get('context'):
            parts.append("")
            parts.append("【上下文】")
            parts.append(prompt_2_0['context'])
        
        # 4. 错误反馈部分（如果有，用于自我修正循环）
        if prompt_2_0.get('error_feedback'):
            parts.append("")
            parts.append("【错误反馈】")
            parts.append(prompt_2_0['error_feedback'])
            parts.append("请根据上述错误反馈修正你的 DSL 代码。")
        
        return "\n".join(parts)
    
    def _clean_llm_response(self, response: str) -> str:
        """清理 LLM 响应，移除代码块标记和额外解释"""
        # 移除常见的代码块标记
        code_blocks = [
            ("```dsl", "```"),
            ("```python", "```"),
            ("```", "```"),
        ]
        
        cleaned = response
        
        # 尝试提取代码块内容
        for start_marker, end_marker in code_blocks:
            if start_marker in cleaned:
                # 提取第一个代码块的内容
                start_idx = cleaned.find(start_marker) + len(start_marker)
                end_idx = cleaned.find(end_marker, start_idx)
                if end_idx != -1:
                    cleaned = cleaned[start_idx:end_idx].strip()
                    break
        
        # 移除可能的额外解释行（以 # 开头但不在代码块中）
        lines = cleaned.split('\n')
        code_lines = []
        in_code = True
        
        for line in lines:
            stripped = line.strip()
            # 跳过空行和纯注释行（除非是代码的一部分）
            if not stripped or (stripped.startswith('#') and not stripped.startswith('# =====')):
                continue
            code_lines.append(line)
        
        return '\n'.join(code_lines)


# ============================================================
# 第四部分：DSL 静态分析器与验证器
# ============================================================

class DSLValidator:
    """DSL 静态代码分析器 - 核心防线"""
    
    def __init__(self, schema: Optional[DSLSchema] = None):
        self.defined_vars: Dict[str, Variable] = {}
        self.control_stack: List[ControlBlock] = []
        self.function_calls: List[FunctionCall] = []
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []
        self.current_nesting = 0
        self.max_nesting = 0
        self.schema = schema or DSLSchema()
    
    def validate(self, dsl_code: str) -> ValidationResult:
        """执行完整的静态分析"""
        self._reset()
        
        lines = dsl_code.split('\n')
        
        # 第一遍：构建符号表
        for line_num, line in enumerate(lines, 1):
            self._parse_line(line_num, line)
        
        # 检查控制流闭合
        if self.control_stack:
            unclosed = [block.block_type for block in self.control_stack]
            self.errors.append(ValidationError(
                line_number=len(lines),
                error_type="控制流未闭合",
                message=f"存在未闭合的控制结构: {unclosed}",
                suggestion="检查每个 IF/FOR/WHILE 是否有对应的 ENDIF/ENDFOR/ENDWHILE",
                severity="P0"
            ))
        
        # 检查嵌套深度
        if self.max_nesting > 5:
            self.warnings.append(f"嵌套深度过深({self.max_nesting}层)，建议重构为函数调用")
        
        # 构建结果
        result = ValidationResult(
            is_valid=len(self.errors) == 0,
            errors=self.errors,
            warnings=self.warnings,
            defined_variables=self.defined_vars,
            function_calls=self.function_calls,
            max_nesting_depth=self.max_nesting
        )
        
        return result
    
    def _reset(self):
        """重置验证器状态"""
        self.defined_vars = {}
        self.control_stack = []
        self.function_calls = []
        self.errors = []
        self.warnings = []
        self.current_nesting = 0
        self.max_nesting = 0
    
    def _parse_line(self, line_num: int, line: str):
        """解析单行代码"""
        line = line.strip()
        
        # 跳过空行和注释
        if not line or line.startswith('#'):
            return
        
        # 0. 语法关键字白名单检查
        keyword_match = re.match(r'^([A-Z]+)\b', line)
        if keyword_match:
            keyword = keyword_match.group(1)
            if not self.schema.is_keyword_allowed(keyword):
                self.errors.append(ValidationError(
                    line_number=line_num,
                    error_type="语法禁用",
                    message=f"关键字 {keyword} 不在允许的 DSL 语法集合中",
                    suggestion=f"允许关键字: {', '.join(sorted(self.schema.allowed_keywords))}"
                ))
                return
        
        # 1. 检查 DEFINE 语句
        if line.startswith('DEFINE'):
            self._parse_define(line_num, line)
            return
        
        # 2. 检查控制流
        if line.startswith('IF'):
            self._parse_if(line_num, line)
            return
        
        if line.startswith('ELIF'):
            self._parse_elif(line_num, line)
            return
        
        if line.startswith('ELSE'):
            self._parse_else(line_num, line)
            return
        
        if line.startswith('ENDIF'):
            self._parse_endif(line_num, line)
            return
        
        if line.startswith('FOR'):
            self._parse_for(line_num, line)
            return
        
        if line.startswith('ENDFOR'):
            self._parse_endfor(line_num, line)
            return
        
        if line.startswith('WHILE'):
            self._parse_while(line_num, line)
            return
        
        if line.startswith('ENDWHILE'):
            self._parse_endwhile(line_num, line)
            return
        
        # 3. 检查赋值和函数调用
        if '=' in line:
            self._parse_assignment(line_num, line)
            return
        
        # 4. 检查 RETURN
        if line.startswith('RETURN'):
            self._parse_return(line_num, line)
            return
    
    def _parse_define(self, line_num: int, line: str):
        """解析 DEFINE 语句"""
        match = re.match(DSLSyntax.PATTERNS['DEFINE'], line)
        if not match:
            self.errors.append(ValidationError(
                line_number=line_num,
                error_type="语法错误",
                message=f"DEFINE 语句格式错误",
                suggestion="正确格式: DEFINE {{var_name}}: Type [= value]"
            ))
            return
        
        var_name, type_str, initial_value = match.groups()
        
        # 检查是否重复定义
        if var_name in self.defined_vars:
            self.errors.append(ValidationError(
                line_number=line_num,
                error_type="重复定义",
                message=f"变量 {{{{{var_name}}}}} 已在第{self.defined_vars[var_name].line_number}行定义",
                suggestion=f"删除重复定义或使用赋值语句"
            ))
            return
        
        # 检查类型是否合法
        try:
            var_type = VarType[type_str.upper()]
        except KeyError:
            self.errors.append(ValidationError(
                line_number=line_num,
                error_type="类型错误",
                message=f"未知的类型: {type_str}",
                suggestion=f"支持的类型: {', '.join([t.value for t in VarType])}"
            ))
            return
        
        # 注册变量
        self.defined_vars[var_name] = Variable(
            name=var_name,
            var_type=var_type,
            initial_value=initial_value,
            line_number=line_num
        )
    
    def _parse_if(self, line_num: int, line: str):
        """解析 IF 语句"""
        match = re.match(DSLSyntax.PATTERNS['IF'], line)
        if not match:
            self.errors.append(ValidationError(
                line_number=line_num,
                error_type="语法错误",
                message="IF 语句格式错误",
                suggestion="正确格式: IF condition"
            ))
            return
        
        condition = match.group(1)
        self._check_condition_variables(line_num, condition)
        self._check_condition_types(line_num, condition)
        
        # 入栈
        block = ControlBlock(
            block_type='IF',
            condition=condition,
            start_line=line_num
        )
        block.const_condition = self._detect_constant_condition(condition)
        self.control_stack.append(block)
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)
    
    def _parse_elif(self, line_num: int, line: str):
        """解析 ELIF 语句"""
        if not self.control_stack or self.control_stack[-1].block_type != 'IF':
            self.errors.append(ValidationError(
                line_number=line_num,
                error_type="控制流错误",
                message="ELIF 没有匹配的 IF",
                suggestion="ELIF 必须在 IF 语句块内"
            ))
    
    def _parse_else(self, line_num: int, line: str):
        """解析 ELSE 语句"""
        if not self.control_stack or self.control_stack[-1].block_type != 'IF':
            self.errors.append(ValidationError(
                line_number=line_num,
                error_type="控制流错误",
                message="ELSE 没有匹配的 IF",
                suggestion="ELSE 必须在 IF 语句块内"
            ))
        else:
            self.control_stack[-1].has_else = True
            if self.control_stack[-1].const_condition is True:
                self.warnings.append("检测到 IF 条件恒为 True，ELSE 分支为死代码")
            if self.control_stack[-1].const_condition is False:
                self.warnings.append("检测到 IF 条件恒为 False，IF 分支为死代码")
    
    def _parse_endif(self, line_num: int, line: str):
        """解析 ENDIF 语句"""
        if not self.control_stack or self.control_stack[-1].block_type != 'IF':
            self.errors.append(ValidationError(
                line_number=line_num,
                error_type="控制流错误",
                message="ENDIF 没有匹配的 IF",
                suggestion="检查 IF-ENDIF 配对"
            ))
        else:
            block = self.control_stack.pop()
            block.end_line = line_num
            self.current_nesting -= 1
            if block.const_condition is False and not block.has_else:
                self.warnings.append("检测到 IF 条件恒为 False，且无 ELSE，整个分支为死代码")
    
    def _parse_for(self, line_num: int, line: str):
        """解析 FOR 语句"""
        match = re.match(DSLSyntax.PATTERNS['FOR'], line)
        if not match:
            self.errors.append(ValidationError(
                line_number=line_num,
                error_type="语法错误",
                message="FOR 语句格式错误",
                suggestion="正确格式: FOR {{item}} IN {{collection}}"
            ))
            return
        
        item_var, collection = match.groups()
        vars_in_collection = re.findall(r'\{\{(\w+)\}\}', collection)
        self._check_variables_exist(line_num, vars_in_collection)
        
        block = ControlBlock(
            block_type='FOR',
            condition=f"{item_var} IN {collection}",
            start_line=line_num
        )
        self.control_stack.append(block)
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)
    
    def _parse_endfor(self, line_num: int, line: str):
        """解析 ENDFOR 语句"""
        if not self.control_stack or self.control_stack[-1].block_type != 'FOR':
            self.errors.append(ValidationError(
                line_number=line_num,
                error_type="控制流错误",
                message="ENDFOR 没有匹配的 FOR",
                suggestion="检查 FOR-ENDFOR 配对"
            ))
        else:
            block = self.control_stack.pop()
            block.end_line = line_num
            self.current_nesting -= 1
    
    def _parse_while(self, line_num: int, line: str):
        """解析 WHILE 语句"""
        match = re.match(DSLSyntax.PATTERNS['WHILE'], line)
        if not match:
            self.errors.append(ValidationError(
                line_number=line_num,
                error_type="语法错误",
                message="WHILE 语句格式错误"
            ))
            return
        
        condition = match.group(1)
        self._check_condition_variables(line_num, condition)
        self._check_condition_types(line_num, condition)
        
        block = ControlBlock(
            block_type='WHILE',
            condition=condition,
            start_line=line_num
        )
        self.control_stack.append(block)
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)
    
    def _parse_endwhile(self, line_num: int, line: str):
        """解析 ENDWHILE 语句"""
        if not self.control_stack or self.control_stack[-1].block_type != 'WHILE':
            self.errors.append(ValidationError(
                line_number=line_num,
                error_type="控制流错误",
                message="ENDWHILE 没有匹配的 WHILE"
            ))
        else:
            block = self.control_stack.pop()
            block.end_line = line_num
            self.current_nesting -= 1
    
    def _parse_assignment(self, line_num: int, line: str):
        """解析赋值语句"""
        # 提取 CALL 函数
        call_matches = re.finditer(DSLSyntax.PATTERNS['CALL'], line)
        for match in call_matches:
            func_name = match.group(1)
            args_str = match.group(2)
            args = [arg.strip() for arg in args_str.split(',') if arg.strip()]
            
            # 检查参数中的变量
            self._check_variables_in_args(line_num, args)
            
            # 记录函数调用
            result_var = None
            if line.startswith('{{'):
                result_match = re.match(r'\{\{(\w+)\}\}\s*=', line)
                if result_match:
                    result_var = result_match.group(1)
            
            self.function_calls.append(FunctionCall(
                function_name=func_name,
                arguments=args,
                result_var=result_var,
                line_number=line_num
            ))
        
        # 检查赋值左侧的变量
        assign_match = re.match(DSLSyntax.PATTERNS['ASSIGN'], line)
        if assign_match:
            var_name = assign_match.group(1)
            if var_name not in self.defined_vars:
                self.errors.append(ValidationError(
                    line_number=line_num,
                    error_type="未定义变量",
                    message=f"变量 {{{{{var_name}}}}} 在使用前未定义",
                    suggestion=f"在代码开头添加: DEFINE {{{{{var_name}}}}}: Type"
                ))
            rhs = assign_match.group(2)
            rhs_vars = re.findall(r'\{\{(\w+)\}\}', rhs)
            self._check_variables_exist(line_num, rhs_vars)
    
    def _parse_return(self, line_num: int, line: str):
        """解析 RETURN 语句"""
        match = re.match(DSLSyntax.PATTERNS['RETURN'], line)
        if match:
            return_expr = match.group(1)
            vars_in_expr = re.findall(r'\{\{(\w+)\}\}', return_expr)
            self._check_variables_exist(line_num, vars_in_expr)
    
    def _check_condition_variables(self, line_num: int, condition: str):
        """检查条件中的变量"""
        vars_in_condition = re.findall(r'\{\{(\w+)\}\}', condition)
        self._check_variables_exist(line_num, vars_in_condition)
    
    def _check_condition_types(self, line_num: int, condition: str):
        """检查条件中的类型安全"""
        comparison_pattern = r'(.+?)\s*(==|!=|>=|<=|>|<|IN)\s*(.+)'
        match = re.match(comparison_pattern, condition.strip())
        if not match:
            return
        
        left, op, right = match.groups()
        left_type = self._infer_expr_type(left.strip())
        right_type = self._infer_expr_type(right.strip())
        
        if op in ('>', '<', '>=', '<='):
            if left_type not in (VarType.INTEGER, VarType.FLOAT, VarType.ANY) or \
               right_type not in (VarType.INTEGER, VarType.FLOAT, VarType.ANY):
                self.errors.append(ValidationError(
                    line_number=line_num,
                    error_type="类型错误",
                    message=f"比较运算 {op} 仅支持数字类型，当前为 {left_type.value} 与 {right_type.value}",
                    suggestion="将变量类型改为 Integer/Float，或改用 == / !="
                ))
        
        if op == 'IN':
            if right_type not in (VarType.LIST, VarType.DICT, VarType.ANY):
                self.errors.append(ValidationError(
                    line_number=line_num,
                    error_type="类型错误",
                    message=f"IN 运算右侧必须为 List/Dict，当前为 {right_type.value}",
                    suggestion="确保集合类型变量为 List 或 Dict"
                ))
    
    def _infer_expr_type(self, expr: str) -> VarType:
        """推断表达式类型"""
        var_match = re.fullmatch(r'\{\{(\w+)\}\}', expr)
        if var_match:
            var_name = var_match.group(1)
            if var_name in self.defined_vars:
                return self.defined_vars[var_name].var_type
            return VarType.ANY
        
        literal_type = self._infer_literal_type(expr)
        return literal_type
    
    def _infer_literal_type(self, value: str) -> VarType:
        """推断字面量类型"""
        value = value.strip()
        if re.fullmatch(r'".*"', value) or re.fullmatch(r"'.*'", value):
            return VarType.STRING
        if value.lower() in ('true', 'false'):
            return VarType.BOOLEAN
        if re.fullmatch(r'\d+', value):
            return VarType.INTEGER
        if re.fullmatch(r'\d+\.\d+', value):
            return VarType.FLOAT
        if value.startswith('[') and value.endswith(']'):
            return VarType.LIST
        if value.startswith('{') and value.endswith('}'):
            return VarType.DICT
        return VarType.ANY
    
    def _detect_constant_condition(self, condition: str) -> Optional[bool]:
        """检测恒真/恒假条件"""
        cond = condition.strip().lower()
        if cond == 'true':
            return True
        if cond == 'false':
            return False
        simple_eq = re.fullmatch(r'(\d+)\s*==\s*(\d+)', cond)
        if simple_eq:
            return int(simple_eq.group(1)) == int(simple_eq.group(2))
        return None
    
    def _check_variables_in_args(self, line_num: int, args: List[str]):
        """检查函数参数中的变量"""
        for arg in args:
            vars_in_arg = re.findall(r'\{\{(\w+)\}\}', arg)
            self._check_variables_exist(line_num, vars_in_arg)
    
    def _check_variables_exist(self, line_num: int, var_names: List[str]):
        """检查变量是否已定义"""
        for var_name in var_names:
            if var_name not in self.defined_vars:
                self.errors.append(ValidationError(
                    line_number=line_num,
                    error_type="未定义变量",
                    message=f"变量 {{{{{var_name}}}}} 在使用前未定义",
                    suggestion=f"在代码开头添加: DEFINE {{{{{var_name}}}}}: Type"
                ))


# ============================================================
# 第五部分：自我修正循环
# ============================================================

class SelfCorrectionLoop:
    """自我修正循环 - 策略 D：混合错误处理"""

    def __init__(self, max_retries: int = 3, use_mock: bool = False, auto_fix_threshold: int = 3):
        """
        初始化自我修正循环

        Args:
            max_retries: 最大重试次数
            use_mock: 是否使用模拟 LLM 客户端
            auto_fix_threshold: 自动修复阈值，错误数小于等于此值时尝试自动修复
        """
        self.max_retries = max_retries
        self.llm_client = create_llm_client(use_mock=use_mock)
        self.transpiler = DSLTranspiler(llm_client=self.llm_client)
        self.validator = DSLValidator()
        self.auto_fix_threshold = auto_fix_threshold

    def compile_with_retry(self, prompt_2_0: Dict[str, Any]) -> Tuple[bool, str, ValidationResult, Dict[str, Any]]:
        """
        带重试机制的编译（策略 D 实现）

        Returns:
            (成功标志, DSL代码, 验证结果, 诊断信息)
        """
        dsl_code = None
        result = None
        history = {
            'attempts': [],
            'final_decision': '',
            'error_summary': {}
        }

        for attempt in range(self.max_retries):
            info(f"\n🔄 第 {attempt + 1} 次编译尝试...")

            # 转译
            dsl_code = self.transpiler.transpile(prompt_2_0)

            # 验证
            result = self.validator.validate(dsl_code)

            # 错误分级
            error_analysis = self._analyze_errors(result.errors)

            # 记录本次尝试
            history['attempts'].append({
                'attempt': attempt + 1,
                'total_errors': len(result.errors),
                'error_analysis': error_analysis
            })

            if result.is_valid:
                info(f"✅ 编译成功！")
                history['final_decision'] = 'success'
                return True, dsl_code, result, history
            else:
                error(f"❌ 编译失败，发现 {len(result.errors)} 个错误")
                for err in result.errors[:5]:  # 显示前5个错误
                    error(f"  {err}")

                # 策略 D：根据错误数量决定处理方式
                if attempt < self.max_retries - 1:
                    if error_analysis['p0_count'] + error_analysis['p1_count'] <= self.auto_fix_threshold:
                        # 尝试自动修复 + LLM 重试
                        fixed_dsl, fix_count = self._auto_fix_syntax_errors(dsl_code, result.errors)
                        if fix_count > 0:
                            info(f"  🔧 自动修复了 {fix_count} 个语法错误")
                            # 验证修复后的代码
                            temp_result = self.validator.validate(fixed_dsl)
                            if temp_result.is_valid:
                                info(f"  ✅ 自动修复成功！")
                                history['final_decision'] = 'auto_fixed'
                                return True, fixed_dsl, temp_result, history
                            else:
                                info(f"  ⚠️  自动修复不完整，继续 LLM 重试...")
                                dsl_code = fixed_dsl
                                result = temp_result

                    # 准备错误反馈给 LLM
                    error_feedback = self._generate_error_feedback(dsl_code, result, error_analysis)
                    prompt_2_0['error_feedback'] = error_feedback
                    info(f"  正在准备修正...")

        # 所有尝试都失败，生成诊断报告
        error(f"\n❌ 经过 {self.max_retries} 次尝试仍未通过验证")
        self._generate_diagnostic_report(result, history)
        history['final_decision'] = 'failed'
        history['error_summary'] = self._analyze_errors(result.errors)
        return False, dsl_code, result, history

    def _analyze_errors(self, errors: List[ValidationError]) -> Dict[str, int]:
        """分析错误严重程度"""
        analysis = {'p0_count': 0, 'p1_count': 0, 'p2_count': 0, 'total': len(errors)}

        for error in errors:
            severity = getattr(error, 'severity', 'P2')
            if severity == 'P0':
                analysis['p0_count'] += 1
            elif severity == 'P1':
                analysis['p1_count'] += 1
            else:
                analysis['p2_count'] += 1

        return analysis

    def _auto_fix_syntax_errors(self, dsl_code: str, errors: List[ValidationError]) -> Tuple[str, int]:
        """
        自动修复简单语法错误

        支持的修复类型：
        - IF 缺少条件 → IF True
        - 未闭合的控制流 → 自动添加 ENDIF/ENDFOR
        - 多余的空行 → 删除
        """
        lines = dsl_code.split('\n')
        fixed_lines = []
        fix_count = 0
        control_stack = []

        for line in lines:
            stripped = line.strip()

            # 修复 IF 缺少条件
            if stripped == 'IF' or stripped.startswith('IF ') and len(stripped) == 2:
                fixed_lines.append(line.replace('IF', 'IF True'))
                fix_count += 1
                continue

            # 跟踪控制流
            if stripped in ['IF', 'FOR', 'WHILE']:
                control_stack.append(stripped)
            elif stripped in ['ENDIF', 'ENDFOR', 'ENDWHILE']:
                if control_stack:
                    control_stack.pop()
            elif stripped.startswith('IF'):
                control_stack.append('IF')
            elif stripped.startswith('FOR'):
                control_stack.append('FOR')
            elif stripped.startswith('WHILE'):
                control_stack.append('WHILE')

            fixed_lines.append(line)

        # 修复未闭合的控制流
        while control_stack:
            block_type = control_stack.pop()
            if block_type == 'IF':
                fixed_lines.append('ENDIF')
            elif block_type == 'FOR':
                fixed_lines.append('ENDFOR')
            elif block_type == 'WHILE':
                fixed_lines.append('ENDWHILE')
            fix_count += 1

        return '\n'.join(fixed_lines), fix_count

    def _generate_error_feedback(self, dsl_code: str, result: ValidationResult, error_analysis: Dict[str, int]) -> str:
        """生成详细的错误反馈给 LLM"""
        feedback = [f"你生成的伪代码存在以下问题：\n"]
        feedback.append(f"总错误数: {len(result.errors)}")
        feedback.append(f"  - P0 致命错误: {error_analysis['p0_count']}")
        feedback.append(f"  - P1 严重错误: {error_analysis['p1_count']}")
        feedback.append(f"  - P2 警告: {error_analysis['p2_count']}\n")

        # 按严重程度分组显示错误
        p0_errors = [e for e in result.errors if getattr(e, 'severity', 'P2') == 'P0']
        p1_errors = [e for e in result.errors if getattr(e, 'severity', 'P2') == 'P1']

        if p0_errors:
            feedback.append("【致命错误（必须修复）】")
            for error in p0_errors[:5]:  # 只显示前5个
                feedback.append(f"  - {error}")
            feedback.append("")

        if p1_errors:
            feedback.append("【严重错误（建议修复）】")
            for error in p1_errors[:5]:
                feedback.append(f"  - {error}")
            feedback.append("")

        # 提供修正建议
        feedback.append("【修正要求】")
        feedback.append("1. 必须修复所有 P0 致命错误")
        feedback.append("2. 优先修复 P1 严重错误")
        feedback.append("3. 确保所有 IF/FOR/WHILE 都有对应的 ENDIF/ENDFOR/ENDWHILE")
        feedback.append("4. 所有变量使用前必须先 DEFINE 声明")
        feedback.append("5. 重新输出完整的 DSL 代码，不要只输出修改的部分\n")

        return "\n".join(feedback)

    def _generate_diagnostic_report(self, result: ValidationResult, history: Dict[str, Any]):
        """生成诊断报告"""
        # 如果没有 error_summary，则实时分析
        if 'error_summary' not in history:
            error_analysis = self._analyze_errors(result.errors)
            history['error_summary'] = error_analysis
        else:
            error_analysis = history['error_summary']

        info("\n" + "=" * 80)
        info("DSL 编译失败诊断报告")
        info("=" * 80)
        info(f"\n尝试次数: {len(history['attempts'])}/{self.max_retries}")
        info(f"最终结果: 失败")
        info(f"\n错误统计:")
        info(f"  P0 致命错误: {error_analysis.get('p0_count', 0)}")
        info(f"  P1 严重错误: {error_analysis.get('p1_count', 0)}")
        info(f"  P2 警告: {error_analysis.get('p2_count', 0)}")
        info(f"  总错误数: {error_analysis.get('total', len(result.errors))}")

        info(f"\n关键错误（前10个）:")
        for i, err in enumerate(result.errors[:10], 1):
            info(f"  {i}. {err}")

        p0_count = error_analysis.get('p0_count', 0)
        p1_count = error_analysis.get('p1_count', 0)

        info(f"\n【处理建议】")
        if p0_count + p1_count <= 3:
            info(f"✓ 建议：自动修复 P0 错误 + 继续执行")
        elif p0_count + p1_count <= 10:
            info(f"✓ 建议：")
            info(f"  1. 人工修正 DSL 代码")
            info(f"  2. 重新生成（增强 Prompt）")
            info(f"  3. 调整原始需求 → 回到 Prompt 2.0")
        else:
            info(f"✗ 建议：强制人工介入")
            info(f"  - 检查原始需求是否过于复杂")
            info(f"  - 考虑拆分为多个子任务")
            info(f"  - 审查 Prompt 2.0 的变量提取是否准确")

        info(f"\n【选项】")
        info(f"选项1: 修改原始需求并重新运行")
        info(f"选项2: 人工编辑 DSL 代码并手动验证")
        info(f"选项3: 查看 debug 日志获取更多信息")

        info("=" * 80)


# ============================================================
# 第六部分：完整流程示例
# ============================================================

def main():
    """完整的逻辑重构与代码化流程演示"""
    
    info("=" * 60)
    info("S.E.D.E 第三步：逻辑重构与代码化")
    info("=" * 60)
    
    # 1. 准备输入：Prompt 2.0（来自第二步）
    prompt_2_0 = {
        'variables': [
            {'name': 'user_name', 'type': 'String'},
            {'name': 'score', 'type': 'Integer'},
            {'name': 'items', 'type': 'List'},
            {'name': 'email_body', 'type': 'String'},
            {'name': 'summary', 'type': 'String'},
            {'name': 'user_list', 'type': 'List'},
            {'name': 'result', 'type': 'String'}
        ],
        'functions': [
            {'name': 'send_email', 'arguments': ['user'], 'result': 'email_body'},
            {'name': 'summarize_text', 'arguments': ['article', 'max_length'], 'result': 'summary'}
        ]   }
    # 2. 执行完整流程
    compiler = SelfCorrectionLoop()
    success, dsl_code, result = compiler.compile_with_retry(prompt_2_0)
    if success:
        info("\n✅ 编译成功！")
        info("DSL 代码:")
        info(dsl_code)
        info("\n验证结果:")
        info(result.get_report())
    else:
        error("\n❌ 编译失败，需要人工介入")
        info("DSL 代码:")
        info(dsl_code)

        
if __name__ == "__main__":
    main()