#代码实现
"""
WaAct S.E.D.E Framework - Step 4: 依赖分析、模块分解与代码生成
功能：将 Prompt 3.0 DSL 编译为可执行的模块化 Python 代码
作者：WaAct Compiler Team
版本：2.0
"""

import re
import json
import networkx as nx
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from logger import info, warning, error, debug


# ============================================================================
# 数据结构定义
# ============================================================================

class BlockType(Enum):
    """代码块类型枚举"""
    ASSIGN = "ASSIGN"          # 普通赋值
    CALL = "CALL"              # LLM 调用
    IF = "IF"                  # 条件判断
    ELIF = "ELIF"              # 否则如果分支
    ELSE = "ELSE"              # 否则分支
    ENDIF = "ENDIF"            # 条件结束
    FOR = "FOR"                # FOR循环
    ENDFOR = "ENDFOR"          # FOR循环结束
    WHILE = "WHILE"            # 循环（扩展）
    ENDWHILE = "ENDWHILE"      # 循环结束


@dataclass
class CodeBlock:
    """原子代码块"""
    id: str
    type: BlockType
    code_lines: List[str]
    inputs: Set[str] = field(default_factory=set)
    outputs: Set[str] = field(default_factory=set)
    dependencies: Set[str] = field(default_factory=set)
    line_number: int = 0
    is_async: bool = False  # 是否包含异步操作（LLM 调用）
    
    def __repr__(self):
        return f"Block({self.id}, {self.type.value}, ins={self.inputs}, outs={self.outputs})"


@dataclass
class ModuleDefinition:
    """模块定义（编译后的函数）"""
    name: str
    inputs: List[str]
    outputs: List[str]
    body_code: str
    is_async: bool = False
    original_blocks: List[CodeBlock] = field(default_factory=list)
    
    def to_python(self) -> str:
        """生成完整的 Python 函数代码"""
        async_prefix = "async " if self.is_async else ""
        return self.body_code


# ============================================================================
# 1. 增强型伪代码解析器
# ============================================================================

class PseudoCodeParser:
    """DSL 解析器 - 支持完整的控制流语法"""
    
    def __init__(self):
        # 变量模式：{{variable_name}}
        self.var_pattern = re.compile(r'\{\{(\w+)\}\}')
        # CALL 模式：CALL function_name(args)
        self.call_pattern = re.compile(r'CALL\s+(\w+)\s*\((.*?)\)')
        
    def _extract_vars(self, line: str) -> Set[str]:
        """提取行中的所有变量"""
        return set(self.var_pattern.findall(line))
    
    def _classify_block_type(self, line: str) -> BlockType:
        """识别代码块类型"""
        line_upper = line.upper().strip()
        if line_upper.startswith("IF "):
            return BlockType.IF
        elif line_upper.startswith("ELIF "):
            return BlockType.ELIF
        elif line_upper == "ELSE":
            return BlockType.ELSE
        elif line_upper == "ENDIF":
            return BlockType.ENDIF
        elif line_upper.startswith("FOR "):
            return BlockType.FOR
        elif line_upper == "ENDFOR":
            return BlockType.ENDFOR
        elif line_upper.startswith("WHILE "):
            return BlockType.WHILE
        elif line_upper == "ENDWHILE":
            return BlockType.ENDWHILE
        elif "CALL" in line:
            return BlockType.CALL
        else:
            return BlockType.ASSIGN
    
    def parse(self, dsl_code: str) -> List[CodeBlock]:
        """
        解析 DSL 代码为原子块列表（支持多行CALL语句）
        
        Args:
            dsl_code: Prompt 3.0 伪代码
            
        Returns:
            解析后的代码块列表
        """
        blocks = []
        lines = dsl_code.strip().split('\n')
        block_counter = 0
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 跳过空行和注释
            if not line or line.startswith("#") or line.startswith("DEFINE"):
                i += 1
                continue
            
            # 检查是否是多行CALL语句
            if "CALL" in line and "(" in line and ")" not in line:
                # 收集多行CALL的所有行
                call_lines = [line]
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()
                    if not next_line:
                        i += 1
                        continue
                    call_lines.append(next_line)
                    if ")" in next_line:
                        i += 1
                        break
                    i += 1
                
                # 合并为单个block
                full_call = '\n'.join(call_lines)
                block_type = BlockType.CALL
                
                # 提取变量
                vars_in_call = set()
                for cl in call_lines:
                    vars_in_call.update(self._extract_vars(cl))
                
                # 提取输出（从第一行）
                outputs = set()
                inputs = set()
                if "=" in call_lines[0]:
                    left, right = call_lines[0].split("=", 1)
                    outputs = self._extract_vars(left)
                
                # 从所有行提取输入
                for cl in call_lines:
                    if "=" in cl:
                        _, right = cl.split("=", 1)
                        inputs.update(self._extract_vars(right))
                
                blocks.append(CodeBlock(
                    id=f"OP_{block_counter}",
                    type=block_type,
                    code_lines=call_lines,
                    inputs=inputs,
                    outputs=outputs,
                    line_number=i - len(call_lines) + 1,
                    is_async=True
                ))
                block_counter += 1
                continue
            
            # 单行处理
            block_type = self._classify_block_type(line)
            vars_in_line = self._extract_vars(line)
            
            # 控制流语句
            if block_type in [BlockType.IF, BlockType.ELIF, BlockType.ELSE, BlockType.ENDIF,
                             BlockType.FOR, BlockType.ENDFOR,
                             BlockType.WHILE, BlockType.ENDWHILE]:
                blocks.append(CodeBlock(
                    id=f"CTRL_{block_counter}",
                    type=block_type,
                    code_lines=[line],
                    inputs=vars_in_line,
                    outputs=set(),
                    line_number=i + 1
                ))
                block_counter += 1
                i += 1
                continue
            
            # 赋值或函数调用
            if "=" in line:
                left, right = line.split("=", 1)
                outputs = self._extract_vars(left)
                inputs = self._extract_vars(right)

                is_async = "CALL" in right

                blocks.append(CodeBlock(
                    id=f"OP_{block_counter}",
                    type=block_type,
                    code_lines=[line],
                    inputs=inputs,
                    outputs=outputs,
                    line_number=i + 1,
                    is_async=is_async
                ))
                block_counter += 1
            # 修复 P0-1: 处理 RETURN CALL 语句（没有等号的情况）
            elif line.upper().startswith("RETURN") and "CALL" in line:
                # RETURN CALL 语句，提取变量
                inputs = vars_in_line
                outputs = set()  # RETURN 语句没有本地输出，直接返回

                blocks.append(CodeBlock(
                    id=f"OP_{block_counter}",
                    type=block_type,
                    code_lines=[line],
                    inputs=inputs,
                    outputs=outputs,
                    line_number=i + 1,
                    is_async=True  # RETURN CALL 也是异步的
                ))
                block_counter += 1
            # 修复 P1-2: 处理单纯的 CALL 语句（没有等号，也不是 RETURN CALL）
            elif line.upper().startswith("CALL") or ("CALL" in line and not line.upper().startswith("RETURN")):
                # 纯 CALL 语句，提取变量
                inputs = vars_in_line
                outputs = set()  # 无输出的调用

                blocks.append(CodeBlock(
                    id=f"OP_{block_counter}",
                    type=block_type,
                    code_lines=[line],
                    inputs=inputs,
                    outputs=outputs,
                    line_number=i + 1,
                    is_async=True
                ))
                block_counter += 1
            # 处理单纯 RETURN 语句（没有 CALL）
            elif line.upper().startswith("RETURN ") and "CALL" not in line:
                # RETURN var 语句，提取返回的变量作为输出
                inputs = vars_in_line
                # 手动提取 RETURN 后的变量名
                return_part = line.strip()[7:].strip()  # 去掉 "RETURN "
                outputs = set()
                if return_part and not return_part.startswith('await') and not return_part.startswith('invoke'):
                    # 简单变量名（不是表达式）
                    if ' ' not in return_part and not return_part.endswith(')'):
                        outputs.add(return_part)

                blocks.append(CodeBlock(
                    id=f"OP_{block_counter}",
                    type=block_type,
                    code_lines=[line],
                    inputs=inputs,
                    outputs=outputs,
                    line_number=i + 1,
                    is_async=False
                ))
                block_counter += 1
            # 处理其他普通语句（没有CALL，没有等号，比如条件表达式）
            elif block_type == BlockType.ASSIGN:
                inputs = vars_in_line
                outputs = set()

                blocks.append(CodeBlock(
                    id=f"OP_{block_counter}",
                    type=block_type,
                    code_lines=[line],
                    inputs=inputs,
                    outputs=outputs,
                    line_number=i + 1,
                    is_async=False
                ))
                block_counter += 1

            i += 1
        
        return blocks


# ============================================================================
# 2. 依赖图分析器（核心算法）
# ============================================================================

class DependencyAnalyzer:
    """依赖关系图构建与分析"""
    
    def __init__(self, blocks: List[CodeBlock]):
        self.blocks = blocks
        self.graph = nx.DiGraph()
        self.var_producer: Dict[str, str] = {}  # 变量定义表
        
    def build_graph(self):
        """构建依赖有向无环图（DAG）"""
        # Step 1: 添加节点并建立变量生产者映射
        for block in self.blocks:
            self.graph.add_node(
                block.id, 
                type=block.type.value, 
                data=block,
                is_async=block.is_async
            )
            
            # 记录变量的生产者
            for out_var in block.outputs:
                if out_var in self.var_producer:
                    warning(f"变量 {out_var} 被重复定义")
                self.var_producer[out_var] = block.id
        
        # Step 2: 建立依赖边
        for block in self.blocks:
            for in_var in block.inputs:
                producer_id = self.var_producer.get(in_var)
                
                if producer_id and producer_id != block.id:
                    self.graph.add_edge(producer_id, block.id, var=in_var)
                    block.dependencies.add(producer_id)
                elif not producer_id and block.type != BlockType.IF:
                    # IF 语句可以使用外部输入变量
                    warning(f"未定义变量: {in_var} 在块 {block.id} 中使用")
    
    def detect_cycles(self) -> bool:
        """检测循环依赖"""
        try:
            cycles = list(nx.simple_cycles(self.graph))
            if cycles:
                error(f"检测到循环依赖: {cycles}")
                return True
            return False
        except:
            return False
    
    def find_dead_code(self) -> List[str]:
        """查找死代码（孤岛节点）"""
        dead_blocks = []
        for node in self.graph.nodes():
            if self.graph.in_degree(node) == 0 and self.graph.out_degree(node) == 0:
                block_data = self.graph.nodes[node]['data']
                if block_data.type not in [BlockType.IF, BlockType.ELIF, BlockType.ELSE, BlockType.ENDIF]:
                    dead_blocks.append(node)
        return dead_blocks
    
    def topological_sort(self) -> List[str]:
        """拓扑排序 - 确定执行顺序"""
        try:
            return list(nx.topological_sort(self.graph))
        except nx.NetworkXError as e:
            raise ValueError(f"拓扑排序失败（可能存在循环依赖）: {e}")
    
    def analyze_clusters(self, strategy="io_isolation") -> List[List[CodeBlock]]:
        """
        模块聚类 - 将代码块分组为逻辑模块

        策略:
        - io_isolation: IO 隔离策略（每个 LLM 调用独立成模块）
        - control_flow: 控制流内聚策略
        - hybrid: 混合策略（推荐）

        修复：使用行号排序而非拓扑排序，保持控制流完整性
        """
        # 按源代码行号排序（而非拓扑排序），保持控制流完整
        sorted_blocks = sorted(self.blocks, key=lambda b: b.line_number)

        modules = []
        current_module = []

        # 控制流块类型
        control_flow_start_types = [BlockType.IF, BlockType.FOR, BlockType.WHILE]
        control_flow_middle_types = [BlockType.ELIF, BlockType.ELSE]
        control_flow_end_types = [BlockType.ENDIF, BlockType.ENDFOR, BlockType.ENDWHILE]
        control_flow_types = control_flow_start_types + control_flow_middle_types + control_flow_end_types

        in_control_flow = False  # 标记是否在控制流内部
        control_flow_depth = 0  # 控制流嵌套深度

        for block in sorted_blocks:

            # 如果遇到控制流开始
            if block.type in control_flow_start_types:
                # 先保存之前的模块（如果有）
                if current_module:
                    modules.append(current_module)
                    current_module = []
                in_control_flow = True
                control_flow_depth += 1
                current_module.append(block)
                continue

            # 如果遇到控制流结束
            if block.type in control_flow_end_types:
                current_module.append(block)
                # 控制流结束后切分
                if current_module:
                    modules.append(current_module)
                    current_module = []
                control_flow_depth = max(0, control_flow_depth - 1)
                if control_flow_depth == 0:
                    in_control_flow = False
                continue

            # 处理 ELIF 分支（特殊处理：与 IF 同级缩进）
            if block.type == BlockType.ELIF:
                # ELIF 必须在控制流内部
                if not in_control_flow:
                    warning(f"ELIF 语句不在控制流内部，将被视为普通代码")
                    current_module.append(block)
                else:
                    current_module.append(block)
                continue

            # 处理 ELSE 分支（特殊处理：与 IF 同级缩进）
            if block.type == BlockType.ELSE:
                # ELSE 必须在控制流内部
                if not in_control_flow:
                    warning(f"ELSE 语句不在控制流内部，将被视为普通代码")
                    current_module.append(block)
                else:
                    current_module.append(block)
                continue

            # 普通代码块（CALL, ASSIGN）
            current_module.append(block)

            # 切分条件
            should_split = False

            if not in_control_flow:  # 不在控制流内部时才考虑切分
                if strategy == "io_isolation":
                    # 每个 CALL 都独立成模块
                    should_split = block.type == BlockType.CALL

                elif strategy == "control_flow":
                    # 控制流边界切分（已在上方处理）
                    pass

                elif strategy == "hybrid":
                    # CALL 时切分
                    should_split = block.type == BlockType.CALL

            if should_split and current_module:
                modules.append(current_module)
                current_module = []

        if current_module:
            modules.append(current_module)

        return modules
    
    def visualize(self, output_file="dependency_graph.png"):
        """可视化依赖图"""
        try:
            import matplotlib.pyplot as plt
            
            pos = nx.spring_layout(self.graph, k=2, iterations=50)
            
            # 按类型着色
            color_map = {
                'CALL': '#ff6b6b',
                'ASSIGN': '#4ecdc4',
                'IF': '#ffe66d',
                'ELSE': '#ffe66d',
                'ENDIF': '#ffe66d'
            }
            
            node_colors = [color_map.get(self.graph.nodes[n]['type'], '#95a5a6') 
                          for n in self.graph.nodes()]
            
            plt.figure(figsize=(12, 8))
            nx.draw(self.graph, pos, 
                   node_color=node_colors,
                   node_size=2000,
                   with_labels=True,
                   font_size=8,
                   font_weight='bold',
                   arrows=True,
                   edge_color='gray')
            
            plt.title("代码依赖关系图 (Dependency DAG)", fontsize=14)
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            info(f"依赖图已保存至: {output_file}")
        except ImportError:
            warning("matplotlib 未安装，跳过可视化")


# ============================================================================
# 3. 模块代码生成器
# ============================================================================

class ModuleSynthesizer:
    """将代码块簇转换为 Python 函数"""
    
    def __init__(self):
        self.llm_client_import = "from llm_client import invoke_function"
        
    def _translate_call(self, pseudo_line: str) -> str:
        """
        将伪代码的 CALL 转换为 Python LLM 调用（增强容错性）
        
        示例:
        {{result}} = CALL generate_outline({{topic}}, {{level}})
        =>
        result = await invoke_function('generate_outline', topic=topic, level=level)
        
        支持的容错模式:
        - 缺失右括号: {{result}} = CALL func(
        - 参数为空: {{result}} = CALL func()
        - 参数包含中文字符
        """
        # 提取变量名（去除 {{}}）
        cleaned = pseudo_line.replace("{{", "").replace("}}", "")
        
        # 容错模式1: 标准格式 result = CALL func(arg1, arg2)
        match = re.match(r'(\w+)\s*=\s*CALL\s+(\w+)\s*\((.*?)\)\s*$', cleaned)
        if match:
            result_var = match.group(1)
            func_name = match.group(2)
            args_str = match.group(3)
            return self._format_call(result_var, func_name, args_str)
        
        # 容错模式2: 缺失右括号 result = CALL func(
        match = re.match(r'(\w+)\s*=\s*CALL\s+(\w+)\s*\(\s*$', cleaned)
        if match:
            result_var = match.group(1)
            func_name = match.group(2)
            return f"{result_var} = await invoke_function('{func_name}')"
        
        # 容错模式3: 参数后跟换行 result = CALL func(arg1, arg2
        match = re.match(r'(\w+)\s*=\s*CALL\s+(\w+)\s*\((.*?)\s*$', cleaned)
        if match:
            result_var = match.group(1)
            func_name = match.group(2)
            args_str = match.group(3)
            return self._format_call(result_var, func_name, args_str)
        
        # 容错模式5: 单纯 CALL 语句（没有等号）CALL func(arg1, arg2)
        match = re.match(r'CALL\s+(\w+)\s*\((.*?)\)\s*$', cleaned)
        if match:
            func_name = match.group(1)
            args_str = match.group(2)

            if not args_str.strip():
                return f"await invoke_function('{func_name}')"

            # 处理参数
            args = []
            for arg in args_str.split(','):
                arg = arg.strip()
                if arg:
                    if '=' in arg:
                        parts = arg.split('=', 1)
                        if len(parts) == 2:
                            param_name = self._sanitize_identifier(parts[0].strip())
                            param_value = parts[1].strip()
                            if param_value and not (param_value.startswith('"') or param_value.startswith("'")):
                                param_value = self._sanitize_identifier(param_value)
                            args.append(f"{param_name}={param_value}")
                    else:
                        cleaned_arg = self._sanitize_identifier(arg)
                        args.append(f"{cleaned_arg}={cleaned_arg}")

            kwargs_str = ', '.join(args) if args else ''
            return f"await invoke_function('{func_name}'{', ' + kwargs_str if kwargs_str else ''})"

        # 容错模式6: 单纯 CALL 语句（没有等号，没有参数）CALL func
        match = re.match(r'CALL\s+(\w+)\s*$', cleaned)
        if match:
            func_name = match.group(1)
            return f"await invoke_function('{func_name}')"

        # 容错模式7: 多行参数（匹配到参数名列表）
        match = re.match(r'(\w+)\s*=\s*CALL\s+(\w+)', cleaned)
        if match:
            result_var = match.group(1)
            func_name = match.group(2)
            warning(f"CALL 语句格式不完整，使用默认调用: {pseudo_line}")
            return f"{result_var} = await invoke_function('{func_name}')"

        # 无法解析，返回原始行并警告
        warning(f"无法解析 CALL 语句: {pseudo_line}")
        return cleaned
    
    def _format_call(self, result_var: str, func_name: str, args_str: str) -> str:
        """格式化参数并生成 invoke_function 调用"""
        # 清理结果变量名
        result_var = self._sanitize_identifier(result_var)
        
        if not args_str.strip():
            return f"{result_var} = await invoke_function('{func_name}')"
        """格式化参数并生成 invoke_function 调用"""
        if not args_str.strip():
            return f"{result_var} = await invoke_function('{func_name}')"
        
        # 解析参数（支持中文变量名、逗号分隔）
        args = []
        for arg in args_str.split(','):
            arg = arg.strip()
            if arg:
                # 检查是否是参数赋值格式 param=value
                if '=' in arg:
                    # 清理参数名和值
                    parts = arg.split('=', 1)
                    if len(parts) == 2:
                        param_name = self._sanitize_identifier(parts[0].strip())
                        param_value = parts[1].strip()
                        # 清理值部分（如果是变量名）
                        if param_value and not (param_value.startswith('"') or param_value.startswith("'")):
                            param_value = self._sanitize_identifier(param_value)
                        args.append(f"{param_name}={param_value}")
                else:
                    # 纯变量名，转换为 keyword argument
                    cleaned_arg = self._sanitize_identifier(arg)
                    args.append(f"{cleaned_arg}={cleaned_arg}")
        
        kwargs_str = ', '.join(args)
        return f"{result_var} = await invoke_function('{func_name}', {kwargs_str})"
    
    def _clean_line(self, line: str) -> str:
        """清理伪代码为 Python 代码（增强 FOR 循环转换）"""
        # 去除 {{}}
        cleaned = line.replace("{{", "").replace("}}", "")

        # 修复 P1-1: 处理 IF CALL 语句（必须在去除 {{}} 后立即处理）
        # 检查是否是 "IF CALL func(...)" 格式
        if re.match(r'^IF\s+CALL\s+\w+', cleaned, flags=re.IGNORECASE):
            match = re.match(r'IF\s+CALL\s+(\w+)\s*\((.*?)\)\s*$', cleaned, flags=re.IGNORECASE)
            if match:
                func_name = match.group(1)
                args_str = match.group(2)
                # 格式化参数
                if args_str.strip():
                    args = []
                    for arg in args_str.split(','):
                        arg = arg.strip()
                        if arg:
                            if '=' in arg:
                                parts = arg.split('=', 1)
                                if len(parts) == 2:
                                    param_name = self._sanitize_identifier(parts[0].strip())
                                    param_value = parts[1].strip()
                                    if param_value and not (param_value.startswith('"') or param_value.startswith("'")):
                                        param_value = self._sanitize_identifier(param_value)
                                    args.append(f"{param_name}={param_value}")
                            else:
                                cleaned_arg = self._sanitize_identifier(arg)
                                args.append(f"{cleaned_arg}={cleaned_arg}")
                    kwargs_str = ', '.join(args)
                    return f"if await invoke_function('{func_name}', {kwargs_str}):"
                else:
                    return f"if await invoke_function('{func_name}'):"

        # 修复 P0-1: 处理 RETURN CALL 语句
        # 将 "RETURN CALL func(...)" 转换为 "return await invoke_function('func', ...)"
        if re.match(r'^RETURN\s+CALL\s+\w+', cleaned, flags=re.IGNORECASE):
            match = re.match(r'RETURN\s+CALL\s+(\w+)\s*\((.*?)\)\s*$', cleaned, flags=re.IGNORECASE)
            if match:
                func_name = match.group(1)
                args_str = match.group(2)
                # 格式化参数
                if args_str.strip():
                    args = []
                    for arg in args_str.split(','):
                        arg = arg.strip()
                        if arg:
                            if '=' in arg:
                                # 清理参数名和值
                                parts = arg.split('=', 1)
                                if len(parts) == 2:
                                    param_name = self._sanitize_identifier(parts[0].strip())
                                    param_value = parts[1].strip()
                                    # 清理值部分（如果是变量名）
                                    if param_value and not (param_value.startswith('"') or param_value.startswith("'")):
                                        param_value = self._sanitize_identifier(param_value)
                                    args.append(f"{param_name}={param_value}")
                            else:
                                # 纯变量名，转换为 keyword argument
                                cleaned_arg = self._sanitize_identifier(arg)
                                args.append(f"{cleaned_arg}={cleaned_arg}")
                    kwargs_str = ', '.join(args)
                    return f"return await invoke_function('{func_name}', {kwargs_str})"
                else:
                    return f"return await invoke_function('{func_name}')"

        # 转换控制流
        cleaned = re.sub(r'^IF\s+', 'if ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^ELIF\s+', 'elif ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^ELSE$', 'else:', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^ENDIF$', '', cleaned, flags=re.IGNORECASE)

        # 确保 elif 语句以冒号结尾（如果还没有）
        if cleaned.strip().startswith('elif ') and not cleaned.strip().endswith(':'):
            cleaned = cleaned.strip() + ':'

        # 增强 FOR 循环转换（支持多种格式）
        # 格式1: FOR var IN range(end)
        match = re.match(r'^FOR\s+(\w+)\s+IN\s+range\((\w+)\)\s*$', cleaned, flags=re.IGNORECASE)
        if match:
            loop_var, end_var = match.groups()
            cleaned = f"for {loop_var} in range({end_var}):"
        # 格式2: FOR var IN range(start, end)
        elif not re.search(r'for\s+\w+\s+in\s+', cleaned, flags=re.IGNORECASE):
            # 尝试原有的 {{}} 格式
            match = re.sub(r'^FOR\s+\{\{(\w+)\}\}\s+IN\s+\{\{(\w+)\}\}', r'for \1 in \2:', cleaned, flags=re.IGNORECASE)
            if match != cleaned:
                cleaned = match
            # 尝试简化格式: FOR var IN iterable
            elif re.match(r'^FOR\s+\w+\s+IN\s+\w+\s*$', cleaned, flags=re.IGNORECASE):
                cleaned = re.sub(r'^FOR\s+(\w+)\s+IN\s+(\w+)', r'for \1 in \2:', cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r'^ENDFOR$', '', cleaned, flags=re.IGNORECASE)

        # 转换逻辑运算符（DSL -> Python）
        cleaned = re.sub(r'\bAND\b', ' and ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bOR\b', ' or ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bNOT\b', ' not ', cleaned, flags=re.IGNORECASE)

        # 转换 IS NOT 运算符（DSL -> Python）
        cleaned = re.sub(r'\bIS\s+NOT\b', ' is not ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bIS\b', ' is ', cleaned, flags=re.IGNORECASE)

        # 转换 IN 运算符（DSL -> Python）
        cleaned = re.sub(r'\bIN\b', ' in ', cleaned)

        # 确保if语句以冒号结尾（如果还没有）
        if cleaned.strip().startswith('if ') and not cleaned.strip().endswith(':'):
            cleaned = cleaned.strip() + ':'

        # 处理 RETURN 语句（将 RETURN 转换为小写的 return）
        if cleaned.strip().startswith("RETURN "):
            # 提取 RETURN 后的内容
            return_expr = cleaned.strip()[7:].strip()
            cleaned = f"return {return_expr}"

        # 处理 CALL（非 IF CALL 的情况）
        if "CALL" in line:
            cleaned = self._translate_call(line)

        # 修复 P0-2: 清理非 CALL 行中的变量引用
        # 查找所有可能的标识符（不以数字开头的字母数字下划线组合）
        # 但要跳过关键字、字符串、数字等
        cleaned = self._sanitize_line_variables(cleaned)

        return cleaned
    
    def _sanitize_line_variables(self, line: str) -> str:
        """
        清理代码行中的变量引用，使其符合 Python 标识符规范
        只处理非 CALL 语句中的变量引用
        """
        # 定义 Python 关键字，不进行替换
        python_keywords = {
            'if', 'else', 'elif', 'for', 'while', 'in', 'and', 'or', 'not',
            'is', 'none', 'true', 'false', 'return', 'def', 'async', 'await',
            'import', 'from', 'class', 'pass', 'break', 'continue', 'elif'
        }
        
        # 查找所有标识符（包括以数字开头的）
        # 匹配：字母、数字、下划线的组合（包括以数字开头的）
        tokens = re.findall(r'\b[a-zA-Z0-9_]+\b', line)
        
        # 对每个 token 检查是否需要清理
        for token in set(tokens):
            token_lower = token.lower()
            # 跳过关键字
            if token_lower in python_keywords:
                continue
            # 跳过纯数字
            if token.isdigit():
                continue
            # 如果以数字开头，需要清理
            if token[0].isdigit():
                sanitized = self._sanitize_identifier(token)
                # 替换所有出现的位置（作为独立单词）
                line = re.sub(r'\b' + re.escape(token) + r'\b', sanitized, line)
        
        return line
    
    def _sanitize_identifier(self, identifier: str) -> str:
        """
        清理变量名，确保符合 Python 标识符规范
        - 不能以数字开头
        - 只能包含字母、数字、下划线
        """
        # 如果以数字开头，添加下划线前缀
        if identifier and identifier[0].isdigit():
            identifier = '_' + identifier
        
        # 替换非字母数字下划线字符为下划线
        identifier = re.sub(r'[^a-zA-Z0-9_]', '_', identifier)
        
        return identifier
    
    def generate_module(self, cluster: List[CodeBlock], module_id: int) -> ModuleDefinition:
        """生成单个模块的 Python 代码"""

        # 收集输入输出
        all_inputs = set()
        all_outputs = set()
        internal_vars = set()
        body_lines = []
        is_async = False

        for block in cluster:
            all_inputs.update(block.inputs)
            all_outputs.update(block.outputs)
            internal_vars.update(block.outputs)

            if block.is_async:
                is_async = True

        # 修复 P0-2: 清理变量名，确保符合 Python 标识符规范
        external_inputs = sorted([self._sanitize_identifier(v) for v in all_inputs - internal_vars])
        final_outputs = sorted([self._sanitize_identifier(v) for v in all_outputs])

        # 生成函数名
        func_name = self._generate_function_name(cluster, module_id)

        # 组装函数体
        async_kw = "async " if is_async else ""
        code_lines = [f"{async_kw}def {func_name}({', '.join(external_inputs)}):"]
        code_lines.append('    """Auto-generated module"""')

        # 控制流状态跟踪
        control_flow_depth = 0  # 控制流嵌套深度
        control_flow_types = [BlockType.IF, BlockType.FOR, BlockType.WHILE]
        control_flow_middle_types = [BlockType.ELIF, BlockType.ELSE]
        control_flow_end_types = [BlockType.ENDIF, BlockType.ENDFOR, BlockType.ENDWHILE]

        # 标记是否已经包含 RETURN 语句
        has_return_statement = False

        # 转换代码行并处理多行CALL语句
        for block in cluster:
            block_type = block.type

            # 处理控制流开始（IF/FOR/WHILE）
            if block_type in control_flow_types:
                for line in block.code_lines:
                    if line.strip():
                        cleaned = self._clean_line(line)
                        if cleaned and cleaned.strip():
                            # 控制流语句本身与函数体同级（4个空格）
                            code_lines.append(f"    {cleaned}")
                # 控制流深度增加，后续代码需要缩进
                control_flow_depth += 1

            # 处理控制流结束（ENDIF/ENDFOR/ENDWHILE）
            elif block_type in control_flow_end_types:
                # 控制流结束，深度减少
                control_flow_depth = max(0, control_flow_depth - 1)
                # ENDIF/ENDFOR 等不生成代码（Python 使用缩进）
                continue

            # 处理 ELSE 分支（特殊处理：与 IF 同级缩进）
            elif block_type == BlockType.ELSE:
                for line in block.code_lines:
                    if line.strip():
                        cleaned = self._clean_line(line)
                        if cleaned and cleaned.strip():
                            # ELSE 冒号与 IF 同级（4个空格）
                            if cleaned.strip() == "else:" or cleaned.strip() == "else":
                                code_lines.append(f"    else:")
                            # ELSE 内部代码（8个空格，保持与 IF 体内相同深度）
                            else:
                                indent = "    " + "    " * control_flow_depth
                                code_lines.append(f"{indent}{cleaned}")
                # ELSE 后面的代码缩进应该与 IF 体内相同
                continue

            # 处理 ELIF 分支（特殊处理：与 IF 同级缩进）
            elif block_type == BlockType.ELIF:
                for line in block.code_lines:
                    if line.strip():
                        cleaned = self._clean_line(line)
                        if cleaned and cleaned.strip():
                            # ELIF 冒号与 IF 同级（4个空格）
                            if cleaned.strip().startswith("elif"):
                                code_lines.append(f"    {cleaned.strip()}")
                            # ELIF 内部代码（8个空格，保持与 IF 体内相同深度）
                            else:
                                indent = "    " + "    " * control_flow_depth
                                code_lines.append(f"{indent}{cleaned}")
                # ELIF 后面的代码缩进应该与 IF 体内相同
                continue

            # 处理普通代码块（CALL, ASSIGN, RETURN）
            else:
                # 计算当前缩进级别：基础缩进4个空格 + 控制流深度
                indent = "    " + "    " * control_flow_depth

                # 检查是否是多行CALL block
                is_multiline_call = len(block.code_lines) > 1 and any("CALL" in line for line in block.code_lines)

                if is_multiline_call:
                    # 多行CALL：合并后一次性转换
                    translated = self._parse_multiline_call(block.code_lines)
                    if translated and translated.strip():
                        code_lines.append(f"{indent}{translated}")
                else:
                    # 单行处理
                    for line in block.code_lines:
                        # 检查原始行是否包含CALL
                        if "CALL" in line:
                            # 单行CALL，直接转换
                            if '(' in line and ')' in line:
                                cleaned = self._clean_line(line)
                                code_lines.append(f"{indent}{cleaned}")
                            else:
                                # 异常情况：单行CALL不完整，尝试处理
                                warning(f"单行CALL语句格式异常: {line}")
                                cleaned = self._clean_line(line)
                                if cleaned and cleaned.strip():
                                    code_lines.append(f"{indent}{cleaned}")
                        elif line.strip():
                            # 其他代码行（ASSIGN, RETURN等）
                            cleaned = self._clean_line(line)
                            if cleaned and cleaned.strip():
                                code_lines.append(f"{indent}{cleaned}")
                                # 检查是否是 RETURN 语句
                                if cleaned.strip().startswith('return '):
                                    has_return_statement = True

        # 返回值
        if has_return_statement:
            # 如果已经有 RETURN 语句，不再添加默认 return
            pass
        elif final_outputs:
            code_lines.append(f"    return {', '.join(final_outputs)}")
        else:
            code_lines.append("    return None")

        body_code = '\n'.join(code_lines)

        return ModuleDefinition(
            name=func_name,
            inputs=external_inputs,
            outputs=final_outputs,
            body_code=body_code,
            is_async=is_async,
            original_blocks=cluster
        )
    
    def _flush_call_buffer(self, code_lines: List[str], call_buffer: List[str]) -> None:
        """将多行CALL语句缓冲区转换为单行并添加到code_lines"""
        if not call_buffer:
            return
        
        # 检查缓冲区中是否有CALL语句
        has_call = any("CALL" in line for line in call_buffer)
        
        if has_call:
            # 直接解析多行CALL
            translated = self._parse_multiline_call(call_buffer)
            if translated and translated.strip():
                code_lines.append(f"    {translated}")
        else:
            # 普通参数行，直接转换后添加
            for line in call_buffer:
                cleaned = self._clean_line(line)
                if cleaned and cleaned.strip():
                    code_lines.append(f"    {cleaned}")
    
    def _parse_multiline_call(self, lines: List[str]) -> str:
        """解析多行CALL语句"""
        if not lines:
            return ""
        
        # 第一行: {{result}} = CALL func_name(
        first_line = lines[0].replace("{{", "").replace("}}", "").strip()
        match = re.match(r'(\w+)\s*=\s*CALL\s+(\w+)\s*\(\s*$', first_line)
        if not match:
            warning(f"无法解析多行CALL起始行: {first_line}")
            return ""
        
        result_var = match.group(1)
        func_name = match.group(2)
        
        # 收集参数
        args = []
        for line in lines[1:]:
            cleaned = line.replace("{{", "").replace("}}", "").strip()
            # 移除尾随逗号
            if cleaned.endswith(','):
                cleaned = cleaned[:-1].strip()
            if cleaned and '=' in cleaned:
                args.append(cleaned)
        
        # 生成invoke_function调用
        kwargs_str = ', '.join(args)
        if kwargs_str:
            return f"{result_var} = await invoke_function('{func_name}', {kwargs_str})"
        else:
            return f"{result_var} = await invoke_function('{func_name}')"
        
        body_code = '\n'.join(code_lines)
        
        return ModuleDefinition(
            name=func_name,
            inputs=external_inputs,
            outputs=final_outputs,
            body_code=body_code,
            is_async=is_async,
            original_blocks=cluster
        )
    
    def _generate_function_name(self, cluster: List[CodeBlock], module_id: int) -> str:
        """智能生成函数名"""
        # 优先使用 CALL 的函数名
        for block in cluster:
            if block.type == BlockType.CALL:
                match = re.search(r'CALL\s+(\w+)', block.code_lines[0])
                if match:
                    return f"step_{module_id}_{match.group(1)}"

        # 否则使用输出变量名（需要清理 {{}} 和确保符合 Python 标识符规范）
        for block in cluster:
            if block.outputs:
                var_name = list(block.outputs)[0]
                # 先去除 {{}}，再清理标识符
                var_name_cleaned = var_name.replace("{{", "").replace("}}", "")
                var_name_sanitized = self._sanitize_identifier(var_name_cleaned)
                return f"step_{module_id}_compute_{var_name_sanitized}"

        return f"step_{module_id}_process"
    
    def generate_orchestrator(self, modules: List[ModuleDefinition],
                             main_inputs: List[str]) -> str:
        """生成主控函数（工作流编排器） - 验证 is_async 标记正确性"""

        has_async = any(m.is_async for m in modules)
        async_kw = "async " if has_async else ""
        
        lines = [
            f"{async_kw}def main_workflow(input_params: dict):",
            '    """',
            '    主工作流 - 自动生成',
            '    ',
            f'    Args:',
            f'        input_params: 包含 {main_inputs} 的字典',
            '    ',
            '    Returns:',
            '        执行结果上下文',
            '    """',
            '    # 初始化上下文',
            '    ctx = input_params.copy()',
            ''
        ]

        for i, module in enumerate(modules, 1):
            lines.append(f'    # Module {i}: {module.name}')
            
            # 准备参数
            args = ', '.join([f'ctx.get("{arg}")' for arg in module.inputs])
            
            # 根据模块的 is_async 状态决定是否使用 await
            await_kw = "await " if module.is_async else ""
            
            if module.outputs:
                targets = ', '.join([f'ctx["{out}"]' for out in module.outputs])
                lines.append(f'    {targets} = {await_kw}{module.name}({args})')
            else:
                lines.append(f'    {await_kw}{module.name}({args})')
            
            lines.append('')
        
        lines.append('    return ctx')
        
        return '\n'.join(lines)


# ============================================================================
# 4. 主编译器入口
# ============================================================================

class WaActCompiler:
    """WaAct 编译器 - 完整流程"""
    
    def __init__(self):
        self.parser = PseudoCodeParser()
        self.synthesizer = ModuleSynthesizer()
        
    def compile(self, dsl_code: str,
                clustering_strategy: str = "hybrid",
                visualize: bool = False) -> Tuple[List[ModuleDefinition], str, Dict[str, Any]]:
        """
        编译 DSL 为可执行 Python 代码

        Args:
            dsl_code: Prompt 3.0 伪代码
            clustering_strategy: 聚类策略 (io_isolation/control_flow/hybrid)
            visualize: 是否生成依赖图可视化

        Returns:
            (模块列表, 主函数代码, 编译步骤详情)
        """
        info("=" * 60)
        info("WaAct Compiler v2.0 - 开始编译")
        info("=" * 60)

        # 收集步骤详情
        compile_details = {}

        # Stage 1: 词法解析
        info("\n[Stage 1] 词法解析 (Lexical Parsing)...")
        blocks = self.parser.parse(dsl_code)
        info(f"✅ 解析出 {len(blocks)} 个代码块")

        # 收集 Stage 1 详情
        block_types_count = {}
        for block in blocks:
            block_type = block.type.value
            block_types_count[block_type] = block_types_count.get(block_type, 0) + 1

        compile_details['step1_parsing'] = {
            'total_blocks': len(blocks),
            'block_types': block_types_count,
            'blocks': [
                {
                    'id': block.id,
                    'type': block.type.value,
                    'line_number': block.line_number,
                    'is_async': block.is_async,
                    'inputs': list(block.inputs),
                    'outputs': list(block.outputs),
                    'code_lines': block.code_lines
                }
                for block in blocks
            ]
        }

        # Stage 2: 依赖分析
        info("\n[Stage 2] 依赖分析 (Dependency Analysis)...")
        analyzer = DependencyAnalyzer(blocks)
        analyzer.build_graph()

        # 循环检测
        has_cycles = analyzer.detect_cycles()
        if has_cycles:
            raise ValueError("❌ 编译失败：检测到循环依赖")

        # 死代码检测
        dead_code = analyzer.find_dead_code()
        if dead_code:
            warning(f"发现 {len(dead_code)} 个死代码块: {dead_code}")

        # 拓扑排序
        topological_order = analyzer.topological_sort()

        info("✅ 依赖图构建完成")

        # 收集 Stage 2 详情
        compile_details['step2_dependency'] = {
            'has_cycles': has_cycles,
            'dead_code_count': len(dead_code),
            'dead_code_blocks': dead_code,
            'topological_order': topological_order,
            'edge_count': analyzer.graph.number_of_edges(),
            'node_count': analyzer.graph.number_of_nodes()
        }

        if visualize:
            analyzer.visualize()

        # Stage 3: 模块聚类
        info(f"\n[Stage 3] 模块聚类 (Strategy: {clustering_strategy})...")
        clusters = analyzer.analyze_clusters(clustering_strategy)
        info(f"✅ 拆分为 {len(clusters)} 个模块")

        # 收集 Stage 3 详情
        compile_details['step3_clustering'] = {
            'strategy': clustering_strategy,
            'total_clusters': len(clusters),
            'clusters': [
                {
                    'cluster_id': i,
                    'block_count': len(cluster),
                    'blocks': [block.id for block in cluster]
                }
                for i, cluster in enumerate(clusters, 1)
            ]
        }

        # Stage 4: 代码生成
        info("\n[Stage 4] 代码生成 (Code Synthesis)...")
        modules = []

        for i, cluster in enumerate(clusters, 1):
            module = self.synthesizer.generate_module(cluster, i)
            modules.append(module)
            info(f"  ├─ Module {i}: {module.name} "
                  f"({'async' if module.is_async else 'sync'})")

        # 收集 Stage 4 详情
        compile_details['step4_generation'] = {
            'total_modules': len(modules),
            'async_modules': sum(1 for m in modules if m.is_async),
            'sync_modules': sum(1 for m in modules if not m.is_async),
            'modules': [
                {
                    'name': module.name,
                    'inputs': module.inputs,
                    'outputs': module.outputs,
                    'is_async': module.is_async,
                    'body_code': module.body_code,
                    'original_block_count': len(module.original_blocks)
                }
                for module in modules
            ]
        }

        # Stage 4.5: 语法验证
        info("\n[Stage 4.5] 语法验证 (Syntax Validation)...")
        self._validate_generated_code(modules)

        # Stage 5: 主控生成
        info("\n[Stage 5] 主控编排 (Orchestration)...")
        main_inputs = self._extract_main_inputs(blocks)
        main_code = self.synthesizer.generate_orchestrator(modules, main_inputs)
        info("✅ 主工作流生成完成")

        # 收集 Stage 5 详情
        compile_details['step5_orchestration'] = {
            'main_inputs': main_inputs,
            'input_count': len(main_inputs),
            'main_code': main_code
        }

        info("\n" + "=" * 60)
        info("编译成功！")
        info("=" * 60)

        return modules, main_code, compile_details
    
    def _extract_main_inputs(self, blocks: List[CodeBlock]) -> List[str]:
        """提取工作流的外部输入参数"""
        all_inputs = set()
        all_outputs = set()
        
        for block in blocks:
            all_inputs.update(block.inputs)
            all_outputs.update(block.outputs)
        
        # 外部输入 = 使用但未生产的变量
        external = all_inputs - all_outputs
        return sorted(list(external))
    
    def _validate_generated_code(self, modules: List[ModuleDefinition]) -> None:
        """验证生成的代码语法正确性（AST 解析）"""
        import ast
        import io
        import sys
        
        errors = []
        warnings_list = []
        
        for module in modules:
            try:
                # 尝试解析生成的代码为 AST
                ast.parse(module.body_code)
                debug(f"  ✅ {module.name}: 语法正确")
            except SyntaxError as e:
                error_msg = f"  ❌ {module.name}: 语法错误 - {e.msg} (行 {e.lineno})"
                errors.append(error_msg)
                error(error_msg)
                # 打印出错的代码用于调试
                error(f"\n--- {module.name} 代码内容 ---")
                for i, line in enumerate(module.body_code.split('\n'), 1):
                    error(f"{i:3}|{line}")
                error(f"--- {module.name} 代码结束 ---\n")
                continue
            
            # 检查是否有残留的 DSL 关键字
            dsl_keywords = ['CALL', 'FOR round IN', '{{', '}}', 'ENDIF', 'ENDFOR']
            for keyword in dsl_keywords:
                if keyword in module.body_code:
                    warning_msg = f"  ⚠️ {module.name}: 发现残留的 DSL 关键字 '{keyword}'"
                    warnings_list.append(warning_msg)
                    warning(warning_msg)
            
            # 检查是否所有 CALL 语句都已转换
            if 'CALL' in module.body_code and 'await invoke_function' not in module.body_code:
                error_msg = f"  ❌ {module.name}: CALL 语句未正确转换"
                errors.append(error_msg)
                error(error_msg)
            
            # 检查异步标记一致性
            if module.is_async and 'await' not in module.body_code and 'async def' not in module.body_code:
                warning_msg = f"  ⚠️ {module.name}: 标记为 async 但未使用 await"
                warnings_list.append(warning_msg)
                warning(warning_msg)
            elif not module.is_async and 'await' in module.body_code:
                warning_msg = f"  ⚠️ {module.name}: 标记为 sync 但包含 await"
                warnings_list.append(warning_msg)
                warning(warning_msg)
        
        # 汇总报告
        if errors:
            raise ValueError(
                f"语法验证失败，发现 {len(errors)} 个错误：\n" + "\n".join(errors)
            )
        
        if warnings_list:
            info(f"发现 {len(warnings_list)} 个警告，请检查代码质量")
        
        info("✅ 语法验证通过")
    
    def export_to_file(self, modules: List[ModuleDefinition], 
                       main_code: str, 
                       output_path: str = "agent_workflow.py"):
        """导出为完整的 Python 文件"""
        
        lines = [
            '"""',
            'Auto-generated by WaAct Compiler',
            'DO NOT EDIT THIS FILE MANUALLY',
            '"""',
            '',
            'from typing import Dict, Any',
            'from llm_client import invoke_function  # 需要实现 LLM 客户端',
            '',
            ''
        ]
        
        # 添加所有模块
        for module in modules:
            lines.append(module.to_python())
            lines.append('\n')
        
        # 添加主函数
        lines.append(main_code)
        lines.append('\n\n')
        
        # 添加测试入口
        lines.extend([
            'if __name__ == "__main__":',
            '    import asyncio',
            '    ',
            '    # 测试输入',
            '    test_input = {',
            '        # TODO: 填充实际参数',
            '    }',
            '    ',
            '    result = asyncio.run(main_workflow(test_input))',
            '    from logger import info',
            '    info("执行结果:", result)'
        ])
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        info(f"\n✅ 代码已导出至: {output_path}")


# ============================================================================
# 5. 测试用例
# ============================================================================

if __name__ == "__main__":
    # 测试 DSL
    test_dsl = """
# 用户等级判断与内容生成工作流

IF {{experience_years}} > 3
    {{level}} = "Expert"
    {{complexity}} = 0.9
ELSE
    {{level}} = "Novice"
    {{complexity}} = 0.3
ENDIF

{{outline}} = CALL generate_outline({{level}}, {{complexity}})
{{content}} = CALL expand_content({{outline}})
{{final_doc}} = CALL polish_text({{content}}, {{level}})
"""
    
    # 执行编译
    compiler = WaActCompiler()
    modules, main_code = compiler.compile(
        test_dsl, 
        clustering_strategy="hybrid",
        visualize=False  # 设为 True 需要 matplotlib
    )
    
    # 打印结果
    info("\n" + "=" * 60)
    info("生成的模块代码:")
    info("=" * 60)
    
    for i, module in enumerate(modules, 1):
        info(f"\n{'─' * 60}")
        info(f"Module {i}: {module.name}")
        info('─' * 60)
        info(module.to_python())
    
    info("\n" + "=" * 60)
    info("主工作流代码:")
    info("=" * 60)
    info(main_code)
    
    # 导出文件
    compiler.export_to_file(modules, main_code, "generated_workflow.py")



