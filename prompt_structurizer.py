"""
S.E.D.E Framework - Step 2: 实体抽取与变量定义 (Entity Extraction & Variable Definition)
充当编译器前端的词法分析角色,将自然语言中的常量与变量分离
版本: 2.0
"""

import json
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
from logger import info, warning, error, debug, setup_logger
from llm_client import UnifiedLLMClient, create_llm_client
from data_models import (
    DataType, VariableMeta, Prompt10Result, Prompt20Result,
    create_prompt20_result, generate_id, get_timestamp
)
from history_manager import HistoryManager, Prompt20History

# ========== 配置日志系统 ==========
logger = setup_logger("prompt3.0.step2")


# ========== 兼容性数据结构（保留旧接口） ==========
@dataclass
class VariableConstraints:
    """变量约束条件"""
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    allowed_values: Optional[List[str]] = None
    pattern: Optional[str] = None


@dataclass
class PromptStructure:
    """Prompt 2.0 结构化输出（兼容旧接口）"""
    template_text: str  # 带 {{variable}} 占位符的模板
    variable_registry: List[Dict]  # 变量注册表
    original_text: str  # 原始文本
    extraction_log: List[str]  # 提取日志


# ========== LLM 实体提取器 ==========
class LLMEntityExtractor:
    """LLM 实体提取接口 (语义扫描层) - 使用统一LLM客户端"""
    
    def __init__(
        self,
        llm_client: Optional[UnifiedLLMClient] = None,
        use_mock: bool = False
    ):
        """
        初始化实体提取器
        
        Args:
            llm_client: 统一LLM客户端实例
            use_mock: 是否使用模拟模式
        """
        self.llm = llm_client or create_llm_client(use_mock=use_mock)
        self.use_mock = use_mock

    def extract(self, text: str) -> List[Dict]:
        """
        调用 LLM 进行实体提取
        
        Args:
            text: 待抽取文本
            
        Returns:
            实体列表
        """
        if self.use_mock:
            return self._mock_extract(text)
        
        # 使用统一客户端的实体抽取功能
        return self.llm.extract_entities(text)
    
    def _mock_extract(self, text: str) -> List[Dict]:
        """模拟实体抽取（用于测试）"""
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
        
        return mock_entities


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


# ========== 实体后处理校验器 ==========
class EntityPostValidator:
    """后处理实体校验器 - 过滤掉固定描述而非变量的实体"""
    
    # 固定描述关键词（包含这些词且没有数字的可能是固定需求）
    FIXED_DESCRIPTION_KEYWORDS = ["需要", "要", "支持", "确保", "实现", "提供", "用", "采用"]
    
    # 常见固定需求模式（整体不提取为变量）
    FIXED_DEMAND_PATTERNS = [
        r"需要支持.*对话",  # "需要支持多轮对话"
        r"支持.*双语",  # "支持中英文双语"
        r"用.*做底座",  # "用大模型做底座"
        r"响应时间控制在.*以内",  # 整体为配置描述
        r"上下文窗口存.*轮",  # 有数字但要单独提取
        r"用LangChain.*Milvus.*FastAPI",  # 技术栈整体提取
    ]
    
    # 变量关键词（表明是可配置参数）
    VARIABLE_KEYWORDS = ["个", "人", "万", "年", "周", "月", "天", "轮", "秒", "小时", "分钟"]
    
    @classmethod
    def filter_entities(cls, entities: List[Dict], original_text: str) -> Tuple[List[Dict], List[str]]:
        """
        过滤掉固定描述而非变量的实体
        
        Returns:
            (过滤后的实体列表, 过滤日志列表)
        """
        filtered = []
        filter_logs = []
        
        for entity in entities:
            orig_text = entity.get('original_text', '')
            entity_name = entity.get('name', '')
            filter_reason = cls._should_filter(orig_text, entity_name)
            
            if filter_reason:
                filter_logs.append(f"过滤: '{orig_text}' - {filter_reason}")
                continue
            
            filtered.append(entity)
        
        return filtered, filter_logs
    
    @classmethod
    def _should_filter(cls, text: str, entity_name: str) -> Optional[str]:
        """判断是否应该过滤该实体，返回过滤原因或 None"""
        # 规则1: 包含固定描述关键词但没有数字 -> 可能是固定需求
        if any(kw in text for kw in cls.FIXED_DESCRIPTION_KEYWORDS):
            # 检查是否有数字
            if not re.search(r'\d+', text):
                # 特殊情况：技术栈列表（如 "LangChain、Milvus、FastAPI"）
                if not cls._is_tech_stack(text):
                    return "包含需求描述关键词但无数字，可能是固定需求"
        
        # 规则2: 明确的固定需求描述（即使有数字也要过滤）
        # "需要支持多轮对话" - 整体描述
        if text in ["需要支持多轮对话", "需要中英文双语", "用大模型做底座"]:
            return "明确的固定需求描述"
        
        # "响应时间控制在2秒以内" - 配置描述，应只提取 "2秒"
        if "响应时间控制" in text:
            return "配置描述，应只提取数值部分"
        
        # 规则3: 细分变量（如 "java_developers"）-> 如果原文有总人数，只保留总人数
        if re.search(r'(java|python|frontend|backend).*developers?', entity_name, re.IGNORECASE):
            return "细分变量，建议合并为团队总人数"
        
        # 规则4: 检查是否包含变量关键词
        has_variable_keyword = any(kw in text for kw in cls.VARIABLE_KEYWORDS)
        if not has_variable_keyword:
            # 没有变量关键词的可能是固定描述
            # 但技术栈、专有名词例外
            if not cls._is_tech_stack(text) and not cls._is_proper_noun(text):
                return "不包含变量关键词，可能是固定描述"
        
        return None
    
    @classmethod
    def _is_tech_stack(cls, text: str) -> bool:
        """判断是否为技术栈列表"""
        tech_indicators = ["LangChain", "Milvus", "FastAPI", "K8s", "Kubernetes", "ELK", "Prometheus", "Grafana"]
        return any(tech in text for tech in tech_indicators) and "、" in text
    
    @classmethod
    def _is_proper_noun(cls, text: str) -> bool:
        """判断是否为专有名词（技术术语）"""
        proper_nouns = [
            # 技术框架/平台
            "RAG", "LLM", "API", "K8s", "Kubernetes",
            "LangChain", "Milvus", "FastAPI",
            # 编程语言
            "Python", "Java", "JavaScript", "TypeScript",
            "C++", "C#", "Go", "Rust", "PHP", "Ruby",
            # 数据科学/机器学习
            "机器学习", "深度学习", "数据分析", "人工智能",
            "AI", "ML", "DL", "TensorFlow", "PyTorch",
            # 数据库/存储
            "MySQL", "PostgreSQL", "MongoDB", "Redis",
            "Elasticsearch", "Milvus", "向量数据库",
            # 开发领域
            "前端开发", "后端开发", "全栈开发",
            "Web开发", "移动开发", "数据科学",
            # 其他技术术语
            "微服务", "容器化", "DevOps", "CI/CD"
        ]
        return any(noun in text for noun in proper_nouns)
    
    @staticmethod
    def merge_duplicate_entities(entities: List[Dict]) -> List[Dict]:
        """
        合并重复或重叠的实体
        
        例如：
        - "5个人" 和 "5" → 保留 "5个人"
        - "8周" 和 "周" → 保留 "8周"
        """
        if not entities:
            return []
        
        merged = []
        processed_indices = set()
        
        for i, entity1 in enumerate(entities):
            if i in processed_indices:
                continue
            
            orig_text1 = entity1.get('original_text', '')
            
            # 查找是否有其他实体包含当前实体
            for j, entity2 in enumerate(entities):
                if i >= j or j in processed_indices:
                    continue
                
                orig_text2 = entity2.get('original_text', '')
                
                # 如果 entity1 包含 entity2，保留 entity1（更长的）
                if orig_text2 in orig_text1:
                    processed_indices.add(j)
                    logger.info(f"合并实体: '{orig_text2}' → '{orig_text1}'")
            
            merged.append(entity1)
            processed_indices.add(i)
        
        return merged


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
    
    def __init__(
        self,
        llm_client: Optional[UnifiedLLMClient] = None,
        use_mock: bool = False
    ):
        """
        初始化结构化处理引擎
        
        Args:
            llm_client: 统一LLM客户端实例
            use_mock: 是否使用模拟模式
        """
        self.llm_extractor = LLMEntityExtractor(
            llm_client=llm_client,
            use_mock=use_mock
        )
        self.firewall = HallucinationFirewall()
        self.type_cleaner = TypeCleaner()
        self.conflict_resolver = EntityConflictResolver()
        self.entity_validator = EntityPostValidator()  # 新增：后处理校验器
        self.extraction_log = []
        self.use_mock = use_mock
        self.history_manager = HistoryManager()
    
    def process_from_prompt10(
        self, 
        prompt10_result: Prompt10Result,
        save_history: bool = True
    ) -> Prompt20Result:
        """
        从 Prompt 1.0 结果进行处理
        
        Args:
            prompt10_result: Prompt 1.0 的处理结果
            save_history: 是否保存历史记录
            
        Returns:
            Prompt20Result: Prompt 2.0 结构化结果
        """
        start_time = time.time()
        
        # 使用 Prompt 1.0 的处理后文本
        clean_text = prompt10_result.processed_text
        
        # 调用核心处理流程
        structure = self.process(clean_text)
        
        # 构建 VariableMeta 列表
        variables = [
            VariableMeta(
                name=reg["variable"],
                original_text=reg["original_text"],
                value=reg["value"],
                data_type=reg["type"],
                start_index=0,  # 简化处理
                end_index=len(reg["original_text"]),
                source_context=reg.get("source_context", "Prompt 1.0")
            )
            for reg in structure.variable_registry
        ]
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        result = Prompt20Result(
            id=generate_id(),
            timestamp=get_timestamp(),
            source_prompt10_id=prompt10_result.id,
            original_text=prompt10_result.processed_text,
            template_text=structure.template_text,
            variables=variables,
            variable_registry=structure.variable_registry,
            extraction_log=structure.extraction_log,
            processing_time_ms=processing_time_ms
        )
        
        # 保存历史记录
        if save_history:
            self._save_history(result)
        
        return result
    
    def _save_history(self, result: Prompt20Result):
        """保存 Prompt 2.0 处理历史"""
        # 统计变量类型
        type_stats = {}
        for var in result.variables:
            dtype = var.data_type
            type_stats[dtype] = type_stats.get(dtype, 0) + 1
        
        history = Prompt20History(
            id=result.id,
            timestamp=result.timestamp,
            source_prompt10_id=result.source_prompt10_id,
            input_text=result.original_text,
            template_text=result.template_text,
            variables=result.variable_registry,
            variable_count=len(result.variables),
            type_stats=type_stats,
            extraction_log=result.extraction_log,
            processing_time_ms=result.processing_time_ms
        )
        
        try:
            self.history_manager.save_prompt20_history(history)
        except Exception as e:
            warning(f"保存 Prompt 2.0 历史记录失败: {e}")
    
    def process(self, clean_text: str) -> PromptStructure:
        """
        主处理流程
        输入: Prompt 1.0 (已清洗文本)
        输出: PromptStructure (Prompt 2.0)
        """
        logger.info(f"开始结构化处理: {clean_text[:50]}...")
        self.extraction_log = []
        
        # ===== 阶段 2.1: 语义扫描与实体定位 (LLM-Layer) =====
        raw_entities = self.llm_extractor.extract(clean_text)
        # 兼容处理：确保是列表
        if isinstance(raw_entities, str):
            raw_entities = json.loads(raw_entities)
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
        
        # ===== 阶段 2.2.5: 后处理校验（过滤固定描述）=====
        filtered_entities, filter_logs = self.entity_validator.filter_entities(resolved_entities, clean_text)
        for log in filter_logs:
            self._log(f"🔍 {log}")
        self._log(f"后处理校验完成,保留 {len(filtered_entities)} 个变量")
        
        # ===== 阶段 2.3: 强类型清洗与转换 (Code-Layer) =====
        variable_metas = []
        for entity in filtered_entities:  # 修复：使用过滤后的实体
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
    
    info("=" * 60)
    info("S.E.D.E Framework - Step 2: 实体抽取与变量定义")
    info("=" * 60)
    info(f"\n【输入 - Prompt 1.0】:\n{input_text}\n")
    
    # 创建处理器（使用模拟模式）
    structurizer = PromptStructurizer(use_mock=False)  # 使用真实LLM
    
    # 方式1: 直接处理文本
    result = structurizer.process(input_text)
    
    # 输出结果
    info("\n" + "=" * 60)
    info("【输出 - Prompt 2.0 模板】:")
    info("=" * 60)
    info(result.template_text)
    
    info("\n" + "=" * 60)
    info("【变量注册表 (Variable Registry)】:")
    info("=" * 60)
    info(json.dumps(result.variable_registry, indent=2, ensure_ascii=False))
    
    info("\n" + "=" * 60)
    info("【处理日志】:")
    info("=" * 60)
    for log in result.extraction_log:
        info(f"  {log}")
    
    # 方式2: 从 Prompt10Result 处理
    info("\n\n" + "=" * 60)
    info("【演示: 从 Prompt10Result 处理】")
    info("=" * 60)
    
    # 模拟一个 Prompt10Result
    mock_prompt10 = Prompt10Result(
        id="test123",
        timestamp=get_timestamp(),
        mode="dictionary",
        original_text="帮我搞个RAG应用",
        processed_text=input_text,  # 使用已处理文本
        steps=[],
        terminology_changes={},
        status="success",
        ambiguity_detected=False
    )
    
    prompt20_result = structurizer.process_from_prompt10(mock_prompt10)
    
    info(f"\n来源 Prompt 1.0 ID: {prompt20_result.source_prompt10_id}")
    info(f"生成 Prompt 2.0 ID: {prompt20_result.id}")
    info(f"模板: {prompt20_result.template_text}")
    info(f"变量数量: {len(prompt20_result.variables)}")
    
    info("\n" + "=" * 60)
    info("【验证: 模板回填】:")
    info("=" * 60)
    # 演示如何使用模板
    filled_template = result.template_text
    for var in result.variable_registry:
        placeholder = f"{{{{{var['variable']}}}}}"
        filled_template = filled_template.replace(placeholder, str(var['value']))
    info(filled_template)
    info(f"\n原文一致性: {filled_template == input_text}")


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