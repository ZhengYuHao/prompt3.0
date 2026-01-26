"""
S.E.D.E Framework - Step 2: 实体抽取与变量定义 (Entity Extraction & Variable Definition)
充当编译器前端的词法分析角色,将自然语言中的常量与变量分离
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict

# ========== 配置日志系统 ==========
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# ========== 数据类型定义 ==========
class DataType(Enum):
    """允许的数据类型白名单"""
    STRING = "String"
    INTEGER = "Integer"
    BOOLEAN = "Boolean"
    LIST = "List"
    ENUM = "Enum"


@dataclass
class VariableConstraints:
    """变量约束条件"""
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    allowed_values: Optional[List[str]] = None
    pattern: Optional[str] = None


@dataclass
class VariableMeta:
    """变量元数据"""
    name: str  # 变量名 (英文, snake_case)
    original_text: str  # 原文中的精确片段
    value: Any  # 提取出的具体值
    data_type: str  # 数据类型
    start_index: int  # 在原文中的起始位置
    end_index: int  # 在原文中的结束位置
    constraints: Optional[VariableConstraints] = None
    source_context: str = "Prompt 1.0"


@dataclass
class PromptStructure:
    """Prompt 2.0 结构化输出"""
    template_text: str  # 带 {{variable}} 占位符的模板
    variable_registry: List[Dict]  # 变量注册表
    original_text: str  # 原始文本
    extraction_log: List[str]  # 提取日志


# ========== LLM 接口层 ==========
class LLMEntityExtractor:
    """LLM 实体提取接口 (语义扫描层)"""
    
    def __init__(self, model_name: str = "gpt-4"):
        self.model_name = model_name
        self.system_prompt = """你是一个实体抽取专家。你的任务是从文本中识别需要动态调整的"变量"。

严格规则:
1. 只输出 JSON 格式,不要有任何其他文字
2. 必须原样返回原文片段,严禁同义词替换
3. 必须返回精确的 start_index 和 end_index
4. 数据类型仅限: String, Integer, Boolean, List, Enum

输出格式:
[
  {
    "name": "变量英文名(snake_case)",
    "original_text": "原文精确片段",
    "start_index": 起始位置,
    "end_index": 结束位置,
    "type": "数据类型",
    "value": "当前值"
  }
]

识别原则:
- 数字、时间、人名、专有名词 -> 变量
- 通用描述、固定格式文本 -> 常量
- 优先识别最长匹配项"""

    def extract(self, text: str) -> str:
        """
        调用 LLM 进行实体提取
        实际生产环境应使用 OpenAI Function Calling 或 Claude 的 Structured Output
        """
        # 这里是模拟实现,实际应调用真实 LLM API
        return self._mock_llm_call(text)
    
    def _mock_llm_call(self, text: str) -> str:
        """模拟 LLM 返回 (用于演示)"""
        # 智能识别常见模式
        mock_entities = []
        
        # 识别数字+单位模式 (如 "3年", "2周")
        for match in re.finditer(r'(\d+)(年|周|月|天|小时|分钟)', text):
            mock_entities.append({
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
                mock_entities.append({
                    "name": f"tech_term_{len(mock_entities)}",
                    "original_text": term,
                    "start_index": idx,
                    "end_index": idx + len(term),
                    "type": "String",
                    "value": term
                })
        
        return json.dumps(mock_entities, ensure_ascii=False)


# ========== 幻觉防火墙 ==========
class HallucinationFirewall:
    """防止 LLM 虚构原文中不存在的内容"""
    
    @staticmethod
    def validate_existence(entity: Dict, original_text: str) -> Tuple[bool, str]:
        """
        存在性校验: 确保 LLM 提取的片段真实存在于原文
        """
        original_snippet = entity.get('original_text', '')
        
        # 精确匹配
        if original_snippet in original_text:
            return True, "精确匹配通过"
        
        # 模糊匹配 (处理空格、标点差异)
        normalized_snippet = re.sub(r'\s+', '', original_snippet)
        normalized_text = re.sub(r'\s+', '', original_text)
        
        if normalized_snippet in normalized_text:
            return True, "模糊匹配通过"
        
        return False, f"幻觉检测: '{original_snippet}' 不存在于原文"
    
    @staticmethod
    def validate_index(entity: Dict, original_text: str) -> bool:
        """验证索引位置的准确性"""
        start = entity.get('start_index', -1)
        end = entity.get('end_index', -1)
        original_snippet = entity.get('original_text', '')
        
        if start == -1 or end == -1:
            return False
        
        if start < 0 or end > len(original_text) or start >= end:
            return False
        
        extracted = original_text[start:end]
        return extracted == original_snippet


# ========== 强类型清洗器 ==========
class TypeCleaner:
    """强类型清洗与转换 (Code-Layer)"""
    
    # Boolean 归一化映射表
    BOOLEAN_MAP = {
        '是': True, '要': True, '需要': True, '对': True, 'yes': True, 'true': True, '1': True,
        '否': False, '不': False, '不要': False, '错': False, 'no': False, 'false': False, '0': False
    }
    
    @classmethod
    def clean(cls, value: Any, target_type: str) -> Tuple[Any, str]:
        """
        类型清洗与转换
        返回: (转换后的值, 实际类型)
        """
        try:
            if target_type == DataType.INTEGER.value:
                return cls._clean_integer(value)
            
            elif target_type == DataType.BOOLEAN.value:
                return cls._clean_boolean(value)
            
            elif target_type == DataType.LIST.value:
                return cls._clean_list(value)
            
            elif target_type == DataType.ENUM.value:
                return cls._clean_enum(value)
            
            else:  # String (默认)
                return str(value), DataType.STRING.value
                
        except Exception as e:
            logger.warning(f"类型转换失败: {value} -> {target_type}, 错误: {e}, 降级为 String")
            return str(value), DataType.STRING.value
    
    @staticmethod
    def _clean_integer(value: Any) -> Tuple[int, str]:
        """Integer 清洗"""
        if isinstance(value, int):
            return value, DataType.INTEGER.value
        
        # 从字符串中提取数字
        if isinstance(value, str):
            numbers = re.findall(r'-?\d+', value)
            if numbers:
                return int(numbers[0]), DataType.INTEGER.value
        
        raise ValueError(f"无法解析为整数: {value}")
    
    @classmethod
    def _clean_boolean(cls, value: Any) -> Tuple[bool, str]:
        """Boolean 清洗"""
        if isinstance(value, bool):
            return value, DataType.BOOLEAN.value
        
        str_value = str(value).strip().lower()
        if str_value in cls.BOOLEAN_MAP:
            return cls.BOOLEAN_MAP[str_value], DataType.BOOLEAN.value
        
        raise ValueError(f"无法解析为布尔值: {value}")
    
    @staticmethod
    def _clean_list(value: Any) -> Tuple[List, str]:
        """List 清洗 - 检测逗号、顿号分隔符"""
        if isinstance(value, list):
            return value, DataType.LIST.value
        
        if isinstance(value, str):
            # 尝试多种分隔符
            for separator in [',', '、', '，', ';', '；']:
                if separator in value:
                    items = [item.strip() for item in value.split(separator)]
                    return items, DataType.LIST.value
            
            # 单元素列表
            return [value], DataType.LIST.value
        
        return [str(value)], DataType.LIST.value
    
    @staticmethod
    def _clean_enum(value: Any) -> Tuple[str, str]:
        """Enum 清洗"""
        return str(value), DataType.ENUM.value


# ========== 实体冲突解析器 ==========
class EntityConflictResolver:
    """处理重叠实体 (Overlapping Entities)"""
    
    @staticmethod
    def resolve_overlaps(entities: List[Dict]) -> List[Dict]:
        """
        最长覆盖原则: 优先保留更长的实体
        例: "3年经验" vs "3年", 保留 "3年经验"
        """
        if not entities:
            return []
        
        # 按起始位置排序
        sorted_entities = sorted(entities, key=lambda x: (x['start_index'], -(x['end_index'] - x['start_index'])))
        
        non_overlapping = []
        last_end = -1
        
        for entity in sorted_entities:
            start = entity['start_index']
            end = entity['end_index']
            
            # 如果当前实体与上一个不重叠
            if start >= last_end:
                non_overlapping.append(entity)
                last_end = end
            else:
                # 发生重叠,比较长度
                if len(non_overlapping) > 0:
                    last_entity = non_overlapping[-1]
                    current_length = end - start
                    last_length = last_entity['end_index'] - last_entity['start_index']
                    
                    if current_length > last_length:
                        # 替换为更长的实体
                        non_overlapping[-1] = entity
                        last_end = end
        
        return non_overlapping


# ========== 核心处理引擎 ==========
class PromptStructurizer:
    """Prompt 结构化处理引擎 (主控制器)"""
    
    def __init__(self, llm_extractor: Optional[LLMEntityExtractor] = None):
        self.llm_extractor = llm_extractor or LLMEntityExtractor()
        self.firewall = HallucinationFirewall()
        self.type_cleaner = TypeCleaner()
        self.conflict_resolver = EntityConflictResolver()
        self.extraction_log = []
    
    def process(self, clean_text: str) -> PromptStructure:
        """
        主处理流程
        输入: Prompt 1.0 (已清洗文本)
        输出: PromptStructure (Prompt 2.0)
        """
        logger.info(f"开始结构化处理: {clean_text[:50]}...")
        self.extraction_log = []
        
        # ===== 阶段 2.1: 语义扫描与实体定位 (LLM-Layer) =====
        llm_response = self.llm_extractor.extract(clean_text)
        raw_entities = json.loads(llm_response)
        self._log(f"LLM 识别到 {len(raw_entities)} 个候选实体")
        
        # ===== 阶段 2.2: 幻觉防火墙与存在性校验 (Code-Layer) =====
        validated_entities = []
        for entity in raw_entities:
            is_valid, msg = self.firewall.validate_existence(entity, clean_text)
            if not is_valid:
                self._log(f"❌ {msg}")
                continue
            
            # 验证索引准确性
            if not self.firewall.validate_index(entity, clean_text):
                self._log(f"⚠️  索引不匹配: {entity['original_text']}, 尝试修正")
                # 自动修正索引
                entity = self._fix_entity_index(entity, clean_text)
            
            validated_entities.append(entity)
            self._log(f"✓ 验证通过: {entity['original_text']}")
        
        # ===== 解决实体冲突 =====
        resolved_entities = self.conflict_resolver.resolve_overlaps(validated_entities)
        self._log(f"冲突解析完成,保留 {len(resolved_entities)} 个实体")
        
        # ===== 阶段 2.3: 强类型清洗与转换 (Code-Layer) =====
        variable_metas = []
        for entity in resolved_entities:
            cleaned_value, actual_type = self.type_cleaner.clean(
                entity['value'], 
                entity['type']
            )
            
            var_meta = VariableMeta(
                name=entity['name'],
                original_text=entity['original_text'],
                value=cleaned_value,
                data_type=actual_type,
                start_index=entity['start_index'],
                end_index=entity['end_index']
            )
            variable_metas.append(var_meta)
            self._log(f"类型转换: {entity['original_text']} -> {actual_type} = {cleaned_value}")
        
        # ===== 阶段 2.4: 模板生成与变量注入 (Code-Layer) =====
        template_text = self._generate_template(clean_text, variable_metas)
        
        # ===== 生成变量注册表 =====
        variable_registry = [
            {
                "variable": var.name,
                "value": var.value,
                "type": var.data_type,
                "original_text": var.original_text,
                "source_context": var.source_context
            }
            for var in variable_metas
        ]
        
        logger.info("✅ Prompt 2.0 生成完毕")
        
        return PromptStructure(
            template_text=template_text,
            variable_registry=variable_registry,
            original_text=clean_text,
            extraction_log=self.extraction_log
        )
    
    def _generate_template(self, original_text: str, variables: List[VariableMeta]) -> str:
        """
        生成模板文本 (防误伤策略: 索引定位替换)
        """
        # 按位置倒序排序,从后往前替换 (防止索引偏移)
        sorted_vars = sorted(variables, key=lambda v: v.start_index, reverse=True)
        
        result = original_text
        for var in sorted_vars:
            placeholder = f"{{{{{var.name}}}}}"
            result = (
                result[:var.start_index] + 
                placeholder + 
                result[var.end_index:]
            )
        
        return result
    
    def _fix_entity_index(self, entity: Dict, text: str) -> Dict:
        """自动修正实体索引"""
        snippet = entity['original_text']
        idx = text.find(snippet)
        if idx != -1:
            entity['start_index'] = idx
            entity['end_index'] = idx + len(snippet)
        return entity
    
    def _log(self, message: str):
        """记录处理日志"""
        self.extraction_log.append(message)
        logger.info(message)


# ========== 使用示例 ==========
def main():
    """演示完整流程"""
    
    # 输入: Prompt 1.0 (已清洗文本)
    input_text = "请为一位有3年经验的Java程序员生成一个为期2周的Python学习计划,重点关注数据分析。"
    
    print("=" * 60)
    print("S.E.D.E Framework - Step 2: 实体抽取与变量定义")
    print("=" * 60)
    print(f"\n【输入 - Prompt 1.0】:\n{input_text}\n")
    
    # 创建处理器
    structurizer = PromptStructurizer()
    
    # 执行处理
    result = structurizer.process(input_text)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("【输出 - Prompt 2.0 模板】:")
    print("=" * 60)
    print(result.template_text)
    
    print("\n" + "=" * 60)
    print("【变量注册表 (Variable Registry)】:")
    print("=" * 60)
    print(json.dumps(result.variable_registry, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 60)
    print("【处理日志】:")
    print("=" * 60)
    for log in result.extraction_log:
        print(f"  {log}")
    
    print("\n" + "=" * 60)
    print("【验证: 模板回填】:")
    print("=" * 60)
    # 演示如何使用模板
    filled_template = result.template_text
    for var in result.variable_registry:
        placeholder = f"{{{{{var['variable']}}}}}"
        filled_template = filled_template.replace(placeholder, str(var['value']))
    print(filled_template)
    print(f"\n原文一致性: {filled_template == input_text}")


if __name__ == "__main__":
    main()



    #如何使用
    # 1. 创建处理器
    structurizer = PromptStructurizer()

    # 2. 处理文本
    result = structurizer.process("您的 Prompt 1.0 文本")

    # 3. 获取结果
    template = result.template_text  # 带占位符的模板
    variables = result.variable_registry  # 变量定义表