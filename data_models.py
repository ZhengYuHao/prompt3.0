"""
统一数据模型定义
提供所有模块共用的数据结构
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


# ============================================================================
# 枚举定义
# ============================================================================

class ProcessingMode(Enum):
    """处理模式枚举"""
    DICTIONARY = "dictionary"  # 基于词表
    SMART = "smart"           # 纯LLM智能
    HYBRID = "hybrid"         # 混合模式


class ProcessingStatus(Enum):
    """处理状态枚举"""
    SUCCESS = "success"       # 成功
    AMBIGUITY = "ambiguity"   # 检测到歧义
    ERROR = "error"           # 处理错误
    PARTIAL = "partial"       # 部分成功


class DataType(Enum):
    """变量数据类型白名单"""
    STRING = "String"
    INTEGER = "Integer"
    FLOAT = "Float"
    BOOLEAN = "Boolean"
    LIST = "List"
    ENUM = "Enum"


# ============================================================================
# 中间步骤快照
# ============================================================================

@dataclass
class StepSnapshot:
    """单个处理步骤的快照"""
    step_name: str           # 步骤名称
    step_index: int          # 步骤序号
    input_text: str          # 输入文本
    output_text: str         # 输出文本
    changes: Dict[str, str]  # 变更记录
    duration_ms: int         # 耗时（毫秒）
    notes: List[str] = field(default_factory=list)  # 备注信息
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def get_diff_summary(self) -> str:
        """获取变更摘要"""
        if self.input_text == self.output_text:
            return "无变更"
        if not self.changes:
            return "文本已修改"
        return f"变更 {len(self.changes)} 处: {list(self.changes.keys())}"


# ============================================================================
# 阶段1: Prompt 1.0 预处理结果
# ============================================================================

@dataclass
class Prompt10Result:
    """
    Prompt 1.0 预处理结果
    prompt_preprocessor.py 的输出，同时也是 prompt_structurizer.py 的输入
    """
    # 基本信息
    id: str                          # 唯一标识符
    timestamp: str                   # 处理时间戳
    mode: str                        # 处理模式
    
    # 文本信息
    original_text: str               # 原始输入文本
    processed_text: str              # 处理后的文本
    
    # 处理详情
    steps: List[StepSnapshot]        # 中间步骤快照
    terminology_changes: Dict[str, str]  # 术语替换记录
    
    # 状态信息
    status: str                      # 处理状态
    ambiguity_detected: bool         # 是否检测到歧义
    ambiguity_details: Optional[str] = None  # 歧义详情
    
    # 日志
    steps_log: List[str] = field(default_factory=list)  # 步骤日志
    warnings: List[str] = field(default_factory=list)   # 警告信息
    
    # 性能指标
    processing_time_ms: int = 0      # 总处理时间（毫秒）
    llm_calls_count: int = 0         # LLM 调用次数
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        # 将 StepSnapshot 列表转换为字典列表
        data['steps'] = [step.to_dict() if hasattr(step, 'to_dict') else step for step in self.steps]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Prompt10Result':
        """从字典创建实例"""
        # 将步骤字典转换为 StepSnapshot 对象
        if 'steps' in data and data['steps']:
            data['steps'] = [
                StepSnapshot(**step) if isinstance(step, dict) else step 
                for step in data['steps']
            ]
        return cls(**data)
    
    def is_success(self) -> bool:
        """判断是否成功"""
        return self.status == ProcessingStatus.SUCCESS.value
    
    def get_step_by_name(self, name: str) -> Optional[StepSnapshot]:
        """根据名称获取步骤"""
        for step in self.steps:
            if step.step_name == name:
                return step
        return None


# ============================================================================
# 阶段2: Prompt 2.0 结构化结果
# ============================================================================

@dataclass
class VariableMeta:
    """变量元数据"""
    name: str                  # 变量名 (英文, snake_case)
    original_text: str         # 原文中的精确片段
    value: Any                 # 提取出的具体值
    data_type: str             # 数据类型
    start_index: int           # 在原文中的起始位置
    end_index: int             # 在原文中的结束位置
    source_context: str = ""   # 来源上下文
    constraints: Optional[Dict] = None  # 约束条件
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Prompt20Result:
    """
    Prompt 2.0 结构化结果
    prompt_structurizer.py 的输出
    """
    # 基本信息
    id: str                          # 唯一标识符
    timestamp: str                   # 处理时间戳
    source_prompt10_id: str          # 来源 Prompt 1.0 的 ID
    
    # 模板信息
    template_text: str               # 带 {{variable}} 占位符的模板
    original_text: str               # 原始文本（来自 Prompt 1.0）
    
    # 变量信息
    variables: List[VariableMeta]    # 变量列表
    variable_registry: List[Dict]    # 变量注册表（兼容旧格式）
    
    # 日志
    extraction_log: List[str] = field(default_factory=list)  # 提取日志
    
    # 性能指标
    processing_time_ms: int = 0      # 处理时间（毫秒）
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['variables'] = [v.to_dict() if hasattr(v, 'to_dict') else v for v in self.variables]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Prompt20Result':
        """从字典创建实例"""
        if 'variables' in data and data['variables']:
            data['variables'] = [
                VariableMeta(**v) if isinstance(v, dict) else v 
                for v in data['variables']
            ]
        return cls(**data)
    
    def fill_template(self, values: Optional[Dict[str, Any]] = None) -> str:
        """
        使用值填充模板
        
        Args:
            values: 变量值字典，如果为None则使用默认值
            
        Returns:
            填充后的文本
        """
        result = self.template_text
        for var in self.variables:
            placeholder = f"{{{{{var.name}}}}}"
            value = values.get(var.name, var.value) if values else var.value
            result = result.replace(placeholder, str(value))
        return result


# ============================================================================
# 完整处理链结果
# ============================================================================

@dataclass
class FullPipelineResult:
    """
    完整处理链结果
    包含 Prompt 1.0 和 Prompt 2.0 的所有信息
    """
    # 基本信息
    pipeline_id: str                 # 流水线唯一标识
    timestamp: str                   # 开始处理时间
    
    # 原始输入
    raw_input: str                   # 用户原始输入
    
    # 阶段结果
    prompt10_result: Optional[Prompt10Result] = None  # 阶段1结果
    prompt20_result: Optional[Prompt20Result] = None  # 阶段2结果
    
    # 最终输出
    final_template: str = ""         # 最终模板
    final_variables: List[Dict] = field(default_factory=list)  # 最终变量表
    
    # 状态
    overall_status: str = "pending"  # 整体状态
    error_message: Optional[str] = None  # 错误信息
    
    # 性能
    total_time_ms: int = 0           # 总处理时间
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'pipeline_id': self.pipeline_id,
            'timestamp': self.timestamp,
            'raw_input': self.raw_input,
            'prompt10_result': self.prompt10_result.to_dict() if self.prompt10_result else None,
            'prompt20_result': self.prompt20_result.to_dict() if self.prompt20_result else None,
            'final_template': self.final_template,
            'final_variables': self.final_variables,
            'overall_status': self.overall_status,
            'error_message': self.error_message,
            'total_time_ms': self.total_time_ms
        }
    
    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    def is_success(self) -> bool:
        """判断整体是否成功"""
        return self.overall_status == ProcessingStatus.SUCCESS.value


# ============================================================================
# 工具函数
# ============================================================================

def generate_id() -> str:
    """生成唯一 ID"""
    import uuid
    return str(uuid.uuid4())[:8]


def get_timestamp() -> str:
    """获取当前时间戳"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_prompt10_result(
    original_text: str,
    processed_text: str,
    mode: str,
    steps: List[StepSnapshot] = None,
    terminology_changes: Dict[str, str] = None,
    status: str = ProcessingStatus.SUCCESS.value,
    ambiguity_detected: bool = False,
    **kwargs
) -> Prompt10Result:
    """创建 Prompt10Result 的便捷函数"""
    return Prompt10Result(
        id=generate_id(),
        timestamp=get_timestamp(),
        mode=mode,
        original_text=original_text,
        processed_text=processed_text,
        steps=steps or [],
        terminology_changes=terminology_changes or {},
        status=status,
        ambiguity_detected=ambiguity_detected,
        **kwargs
    )


def create_prompt20_result(
    source_prompt10_id: str,
    original_text: str,
    template_text: str,
    variables: List[VariableMeta] = None,
    **kwargs
) -> Prompt20Result:
    """创建 Prompt20Result 的便捷函数"""
    vars_list = variables or []
    variable_registry = [
        {
            "variable": var.name,
            "value": var.value,
            "type": var.data_type,
            "original_text": var.original_text,
            "source_context": var.source_context
        }
        for var in vars_list
    ]
    
    return Prompt20Result(
        id=generate_id(),
        timestamp=get_timestamp(),
        source_prompt10_id=source_prompt10_id,
        original_text=original_text,
        template_text=template_text,
        variables=vars_list,
        variable_registry=variable_registry,
        **kwargs
    )


def convert_prompt20_to_dsl_input(prompt20_result: Prompt20Result) -> Dict[str, Any]:
    """
    将 Prompt20Result 转换为 DSL 编译器所需的输入格式
    
    Args:
        prompt20_result: Prompt 2.0 结构化结果
        
    Returns:
        DSL 编译器输入字典，包含 variables 和 logic 字段
    """
    variables = []
    for var in prompt20_result.variables:
        var_dict = {
            'name': var.name,
            'type': var.data_type,
        }
        if var.value is not None:
            var_dict['default'] = var.value
        variables.append(var_dict)
    
    return {
        'variables': variables,
        'logic': prompt20_result.original_text,  # 使用原始文本作为逻辑描述
        'context': 'Converted from Prompt 2.0'
    }
