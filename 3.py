"""
S.E.D.E (Software Engineering Driven Prompt Engineering)
第三步：逻辑重构与代码化 - 完整实现

核心理念：将自然语言的"思考逻辑"转换为"可执行的伪代码"
"""

import re
import json
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from copy import deepcopy
from logger import info, warning, error, debug


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


@dataclass
class ControlBlock:
    """控制块（IF/FOR等）"""
    block_type: str  # IF, FOR, WHILE
    condition: str
    start_line: int
    end_line: Optional[int] = None
    parent: Optional['ControlBlock'] = None
    children: List['ControlBlock'] = field(default_factory=list)


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
    
    def __str__(self):
        suggestion_text = f"\n  建议: {self.suggestion}" if self.suggestion else ""
        return f"[第{self.line_number}行] {self.error_type}: {self.message}{suggestion_text}"


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


# ============================================================
# 第三部分：DSL 转译器（Prompt 2.0 → DSL Code）
# ============================================================

class DSLTranspiler:
    """将结构化的 Prompt 2.0 转换为 DSL 伪代码"""
    
    def __init__(self):
        self.system_prompt = self._build_system_prompt()
    
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

**输入格式：**
你会收到包含变量定义和逻辑描述的结构化文本。

**输出格式：**
只输出符合 DSL 规范的伪代码，不要包含任何解释或额外文字。
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
        # 实际应用中这里调用 LLM API
        # 这里提供模拟实现
        
        dsl_code = []
        
        # 1. 生成变量定义区
        dsl_code.append("# ===== 变量定义区 =====")
        for var in prompt_2_0.get('variables', []):
            var_def = f"DEFINE {{{{{var['name']}}}}}: {var['type']}"
            if 'default' in var:
                var_def += f" = {var['default']}"
            dsl_code.append(var_def)
        
        dsl_code.append("")
        dsl_code.append("# ===== 逻辑控制区 =====")
        
        # 2. 转译逻辑（这里是示例，实际需要 LLM）
        logic = prompt_2_0.get('logic', '')
        
        # 简单的规则转换示例
        if '如果' in logic and 'VIP' in logic:
            dsl_code.append("IF {{user_type}} == \"VIP\"")
            dsl_code.append("    {{discount}} = 0.8")
            dsl_code.append("    {{email_body}} = CALL generate_discount_email({{user_name}}, {{discount}})")
            dsl_code.append("ELSE")
            dsl_code.append("    {{email_body}} = CALL generate_normal_email({{user_name}})")
            dsl_code.append("ENDIF")
        
        dsl_code.append("")
        dsl_code.append("# ===== 输出区 =====")
        dsl_code.append("RETURN {{email_body}}")
        
        return "\n".join(dsl_code)


# ============================================================
# 第四部分：DSL 静态分析器与验证器
# ============================================================

class DSLValidator:
    """DSL 静态代码分析器 - 核心防线"""
    
    def __init__(self):
        self.defined_vars: Dict[str, Variable] = {}
        self.control_stack: List[ControlBlock] = []
        self.function_calls: List[FunctionCall] = []
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []
        self.current_nesting = 0
        self.max_nesting = 0
    
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
                suggestion="检查每个 IF/FOR/WHILE 是否有对应的 ENDIF/ENDFOR/ENDWHILE"
            ))
        
        # 检查嵌套深度
        if self.max_nesting > 3:
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
        
        # 入栈
        block = ControlBlock(
            block_type='IF',
            condition=condition,
            start_line=line_num
        )
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
        self._check_variables_exist(line_num, [collection])
        
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
    """自我修正循环 - 当验证失败时自动修复"""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.transpiler = DSLTranspiler()
        self.validator = DSLValidator()
    
    def compile_with_retry(self, prompt_2_0: Dict[str, Any]) -> Tuple[bool, str, ValidationResult]:
        """
        带重试机制的编译
        
        Returns:
            (成功标志, DSL代码, 验证结果)
        """
        dsl_code = None
        result = None
        
        for attempt in range(self.max_retries):
            info(f"\n🔄 第 {attempt + 1} 次编译尝试...")
            
            # 转译
            dsl_code = self.transpiler.transpile(prompt_2_0)
            
            # 验证
            result = self.validator.validate(dsl_code)
            
            if result.is_valid:
                info(f"✅ 编译成功！")
                return True, dsl_code, result
            else:
                error(f"❌ 编译失败，发现 {len(result.errors)} 个错误")
                for err in result.errors[:3]:  # 只显示前3个错误
                    error(f"  {err}")
                
                if attempt < self.max_retries - 1:
                    # 准备错误反馈给 LLM
                    error_feedback = self._generate_error_feedback(dsl_code, result)
                    prompt_2_0['error_feedback'] = error_feedback
                    info(f"  正在准备修正...")
        
        error(f"\n❌ 经过 {self.max_retries} 次尝试仍未通过验证，需要人工介入")
        return False, dsl_code, result
    
    def _generate_error_feedback(self, dsl_code: str, result: ValidationResult) -> str:
        """生成错误反馈给 LLM"""
        feedback = ["你生成的伪代码存在以下问题：\n"]
        
        for error in result.errors:
            feedback.append(f"- {error}")
        
        feedback.append("\n请修正代码并重新输出完整的 DSL 代码。")
        
        return "\n".join(feedback)


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
        