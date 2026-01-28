"""
完整流水线演示：prompt_preprocessor.py + prompt_structurizer.py 协同工作
展示从口语化输入到结构化模板的完整转换过程
"""

import json
import re
import time

# ============================================================================
# 导入项目模块
# ============================================================================

from logger import info, warning, error
from dataclasses import asdict
from data_models import (
    ProcessingMode, Prompt10Result, StepSnapshot, get_timestamp, generate_id,
    create_prompt20_result, convert_prompt20_to_dsl_input
)

# 导入预处理模块（原 1.py）
from prompt_preprocessor import PromptPreprocessor

# 导入结构化模块（原 2.py）
from prompt_structurizer import (
    PromptStructurizer,
    HallucinationFirewall,
    TypeCleaner,
    EntityConflictResolver,
    VariableMeta,
    LLMEntityExtractor  # 真实 LLM 实体抽取器
)

# 导入 DSL 编译器模块（原 prompt_dslcompiler.py）
from prompt_dslcompiler import SelfCorrectionLoop, ValidationResult

# 导入代码生成器模块（原 prompt_codegenetate.py）
from prompt_codegenetate import WaActCompiler

# 导入历史记录管理
from history_manager import HistoryManager, PipelineHistory


# ============================================================================
# 配置
# ============================================================================
# 是否使用模拟 LLM 客户端（设为 True 可避免真实 API 调用）
USE_MOCK = False  # 默认使用模拟客户端，避免意外 API 调用
# 如果要使用真实 LLM，请设置为 False 并确保配置了有效的 API 密钥
# USE_MOCK = False

# ============================================================================
# 复杂测试场景设计
# ============================================================================

# 原始口语化输入（故意设计得很口语化、不规范）
RAW_INPUT = """
帮我设计一个智能问答系统，需要处理多领域知识库的检索与推理。

首先，用户输入查询后，系统需要判断查询类型：如果是简单事实查询，走向量检索通道；如果是复杂推理查询，先进行意图分解，再走图数据库检索；如果是代码相关问题，则调用代码分析引擎。

向量检索模式下，如果相似度超过0.85，直接返回top-3结果；否则结合重排序模型重新评分，再返回top-5。检索失败时自动切换到混合检索模式。

图数据库检索时，需要沿着知识图谱进行2跳邻居探索，如果找到匹配节点则返回相关实体和关系，否则回退到全量搜索。每次查询都要缓存结果，缓存有效期30分钟。

代码分析引擎支持Python和Java代码，如果代码行数超过500行，只进行静态分析；如果少于500行，则进行完整语义分析并生成解释文档。

用户反馈环节：如果用户对结果不满意，点击"重新生成"时启用更强的推理模型；如果连续3次不满意，则自动升级到人工审核队列。

数据源配置：知识库A包含2000个医学文档，知识库B包含3000个技术文档，知识库C包含1500个法律文档。每个知识库都有独立的向量索引，向量维度统一为1536。

并发控制：系统支持最大50个并发请求，如果超过则排队等待。普通用户优先级设为1，VIP用户优先级设为5，管理员优先级设为10。

安全策略：所有查询内容经过敏感词过滤，如果检测到违规内容则拒绝服务并记录日志。对于金融类查询，需要二次确认用户身份。

响应时间要求：向量检索要在500ms内完成，图数据库检索在1秒内完成，代码分析在2秒内完成。总响应时间不超过3秒，否则降级服务。

日志级别：错误日志保留90天，访问日志保留30天，调试日志保留7天。所有日志都要上传到中央日志系统。

监控指标：QPS、平均响应时间、95分位响应时间、缓存命中率、检索准确率。如果QPS低于10持续10分钟，触发告警；如果95分位响应时间超过3秒持续5分钟，触发扩容。
""".strip()

# 术语映射表（prompt_preprocessor.py 使用）
TERM_MAPPING = {
    # 口语 → 专业术语
    "帮我": "请",
    "那个": "",
    "嘛": "",
    "吧": "",
    "这些": "",
    "那套": "等工具",
    # 技术术语标准化
    "RAG": "检索增强生成",
    "LLM": "大型语言模型",
    "chain": "处理链",
    "K8s": "Kubernetes",
    "ELK": "ELK日志系统",
    "QPS": "每秒查询率(QPS)",
    "top-3": "前3个结果",
    "top-5": "前5个结果",
    "向量索引": "向量索引(VI)",
    "知识图谱": "知识图谱(KG)",
    "缓存命中率": "缓存命中率(CRH)",
}


# 歧义词黑名单（会触发警告但不阻断）
AMBIGUITY_BLACKLIST = ["这个", "那个", "它", "他们", "某些"]


# ============================================================================
# 增强的实体抽取器（模拟真实 LLM）
# ============================================================================

class PipelineMockExtractor:
    """流水线专用的模拟抽取器"""
    
    def extract(self, text: str) -> list:
        """从标准化后的文本中抽取实体"""
        entities = []
        
        # ===== Integer 类型 =====
        # 数量模式
        int_patterns = [
            (r'(\d+)\s*种', 'mode_count'),
            (r'(\d+)\s*个人', 'team_size'),
            (r'(\d+)\s*个', 'count'),
            (r'(\d+)\s*周', 'duration_weeks'),
            (r'(\d+)\s*万', 'budget_wan'),
            (r'(\d+)\s*轮', 'context_rounds'),
            (r'(\d+)\s*秒', 'response_time_sec'),
            (r'约?\s*(\d+)\s*个服务', 'service_count'),
        ]
        
        for pattern, name in int_patterns:
            for match in re.finditer(pattern, text):
                full_match = match.group(0)
                entities.append({
                    "name": f"{name}_{len(entities)}",
                    "original_text": full_match,
                    "start_index": match.start(),
                    "end_index": match.end(),
                    "type": "Integer",
                    "value": full_match
                })
        
        # ===== String 类型：技术术语 =====
        tech_terms = [
            ("检索增强生成(RAG)", "technology"),
            ("基于API封装的应用", "app_type"),
            ("大型语言模型(LLM)", "model_type"),
            ("处理链(Chain)", "component"),
            ("LangChain", "framework"),
            ("Milvus", "database"),
            ("FastAPI", "framework"),
            ("Kubernetes", "platform"),
            ("ELK日志系统(Elasticsearch+Logstash+Kibana)", "monitoring"),
            ("Prometheus", "monitoring"),
            ("微服务架构", "architecture"),
            ("多轮对话", "feature"),
        ]
        
        for term, category in tech_terms:
            if term in text:
                idx = text.find(term)
                entities.append({
                    "name": f"{category}_{len(entities)}",
                    "original_text": term,
                    "start_index": idx,
                    "end_index": idx + len(term),
                    "type": "String",
                    "value": term
                })
        
        # ===== List 类型 =====
        # 技术栈列表
        tech_stack_match = re.search(r'技术栈[^，。]*[：:]\s*([^。]+(?:[、,，][^。]+)+)', text)
        if tech_stack_match:
            entities.append({
                "name": "tech_stack",
                "original_text": tech_stack_match.group(1).strip('。'),
                "start_index": tech_stack_match.start(1),
                "end_index": tech_stack_match.end(1),
                "type": "List",
                "value": tech_stack_match.group(1).strip('。')
            })
        
        # ===== Boolean 类型 =====
        bool_patterns = [
            (r'(需要|不需要)支持', 'support_required'),
            (r'(要|不要)支持', 'support_required'),
        ]
        for pattern, name in bool_patterns:
            match = re.search(pattern, text)
            if match:
                entities.append({
                    "name": f"{name}_{len(entities)}",
                    "original_text": match.group(0),
                    "start_index": match.start(),
                    "end_index": match.end(),
                    "type": "Boolean",
                    "value": match.group(1)
                })
        
        # ===== 语言支持 =====
        lang_match = re.search(r'(中英文双语|中文|英文)', text)
        if lang_match:
            entities.append({
                "name": "language_support",
                "original_text": lang_match.group(0),
                "start_index": lang_match.start(),
                "end_index": lang_match.end(),
                "type": "String",
                "value": lang_match.group(0)
            })
        
        # ===== 添加幻觉测试 =====
        entities.append({
            "name": "hallucination",
            "original_text": "这是虚构的内容不存在于原文",
            "start_index": 9999,
            "end_index": 10010,
            "type": "String",
            "value": "幻觉"
        })
        
        return entities


# ============================================================================
# 完整流水线演示
# ============================================================================

def run_full_pipeline():
    """执行完整流水线"""
    
    info("\n" + "█" * 80)
    info("█" + " " * 30 + "完整流水线演示" + " " * 32 + "█")
    info("█" + " " * 20 + "预处理模块 + 结构化模块 协同工作" + " " * 18 + "█")
    info("█" * 80)
    
    # =========================================================================
    # 阶段 0: 展示原始输入
    # =========================================================================
    info("\n" + "=" * 80)
    info("【阶段 0: 原始用户输入】")
    info("=" * 80)
    info("\n" + RAW_INPUT)
    
    info("\n📝 输入特点分析:")
    info("  • 包含口语化表达: '那个'、'吧'、'嘛'、'搞'、'弄'")
    info("  • 包含非标准术语: '套壳'、'大模型'、'K8s'、'ELK'")
    info("  • 包含多种数据类型: 数字、列表、布尔值")
    info("  • 文本结构松散，需要标准化")
    
    # =========================================================================
    # 阶段 1: Prompt 1.0 预处理
    # =========================================================================
    info("\n\n" + "=" * 80)
    info("【阶段 1: Prompt 1.0 预处理 (prompt_preprocessor)】")
    info("=" * 80)
    
    info("\n📋 术语映射表:")
    for old, new in list(TERM_MAPPING.items())[:8]:
        if new:
            info(f"    '{old}' → '{new}'")
        else:
            info(f"    '{old}' → (删除)")
    info("    ... (共 {} 条映射)".format(len(TERM_MAPPING)))
    
    # 创建预处理器
    preprocessor = PromptPreprocessor(
        mode=ProcessingMode.DICTIONARY,
        term_mapping=TERM_MAPPING,
        ambiguity_blacklist=AMBIGUITY_BLACKLIST,
        use_mock_llm=USE_MOCK,  # 根据配置选择模拟或真实LLM
        enable_deep_check=False  # 关闭深度检测以便演示继续
    )
    
    info("\n>>> 开始预处理...")
    start_time = time.time()
    
    # 执行预处理
    prompt10_result = preprocessor.process(
        RAW_INPUT,
        save_history=True,  # 保存历史记录
        show_comparison=False
    )
    
    preprocessing_time = int((time.time() - start_time) * 1000)
    
    # 展示预处理结果
    info("\n" + "─" * 80)
    info("【Prompt 1.0 处理结果】")
    info("─" * 80)
    
    info(f"\n✅ 处理状态: {prompt10_result.status}")
    info(f"⏱️  处理耗时: {preprocessing_time}ms")
    
    # 展示术语替换
    if prompt10_result.terminology_changes:
        info("\n📝 术语替换记录:")
        for old, new in prompt10_result.terminology_changes.items():
            info(f"    '{old}' → '{new}'")
    
    # 展示处理步骤
    if prompt10_result.steps:
        info("\n📊 处理步骤:")
        for step in prompt10_result.steps:
            info(f"    {step.step_index}. {step.step_name} ({step.duration_ms}ms)")
    
    info("\n📄 标准化后的文本:")
    info("─" * 60)
    processed_text = prompt10_result.processed_text
    info(processed_text)
    info("─" * 60)
    
    # 对比展示
    info("\n🔍 关键变化对比:")
    comparisons = [
        ("那个，帮我搞一个RAG的套壳应用吧", "帮我开发一个检索增强生成(RAG)的基于API封装的应用"),
        ("大模型做底座", "大型语言模型(LLM)做底座"),
        ("chain的话复杂一点", "处理链(Chain)的话复杂一点"),
        ("K8s集群", "Kubernetes集群"),
        ("ELK那套", "ELK日志系统(Elasticsearch+Logstash+Kibana)那套"),
    ]
    for old_phrase, expected_new in comparisons:
        if old_phrase in RAW_INPUT:
            info(f"    原: {old_phrase}")
            info(f"    新: {expected_new}")
            info("")
    
    # =========================================================================
    # 阶段 2: Prompt 2.0 结构化
    # =========================================================================
    info("\n\n" + "=" * 80)
    info("【阶段 2: Prompt 2.0 结构化 (prompt_structurizer)】")
    info("=" * 80)
    
    info("\n>>> 输入: Prompt 1.0 处理后的标准化文本")
    
    # 使用 LLM 实体抽取器（根据配置选择模拟或真实）
    extractor = LLMEntityExtractor(use_mock=USE_MOCK)
    
    # 阶段 2.1: 语义扫描
    info("\n" + "─" * 60)
    info("【2.1 语义扫描与实体定位 (LLM-Layer)】")
    info("─" * 60)
    
    raw_entities = extractor.extract(processed_text)
    info(f"\n识别到 {len(raw_entities)} 个候选实体:")
    
    for i, entity in enumerate(raw_entities[:10], 1):
        info(f"  {i:2}. [{entity['type']:8}] \"{entity['original_text'][:20]}{'...' if len(entity['original_text']) > 20 else ''}\"")
    if len(raw_entities) > 10:
        info(f"  ... 还有 {len(raw_entities) - 10} 个")
    
    # 阶段 2.2: 幻觉防火墙
    info("\n" + "─" * 60)
    info("【2.2 幻觉防火墙与存在性校验 (Code-Layer)】")
    info("─" * 60)
    
    firewall = HallucinationFirewall()
    validated_entities = []
    rejected = []
    
    for entity in raw_entities:
        is_valid, msg = firewall.validate_existence(entity, processed_text)
        if is_valid:
            # 修正索引
            if not firewall.validate_index(entity, processed_text):
                snippet = entity['original_text']
                idx = processed_text.find(snippet)
                if idx != -1:
                    entity['start_index'] = idx
                    entity['end_index'] = idx + len(snippet)
            validated_entities.append(entity)
        else:
            rejected.append(entity)
    
    info(f"\n✅ 通过验证: {len(validated_entities)} 个")
    info(f"❌ 被拒绝 (幻觉): {len(rejected)} 个")
    for r in rejected:
        warning(f"    拒绝: \"{r['original_text'][:30]}...\" - 不存在于原文")
    
    # 阶段 2.3: 冲突解决
    info("\n" + "─" * 60)
    info("【2.3 重叠实体冲突解决 (最长覆盖原则)】")
    info("─" * 60)
    
    resolver = EntityConflictResolver()
    resolved_entities = resolver.resolve_overlaps(validated_entities)
    
    removed_count = len(validated_entities) - len(resolved_entities)
    info(f"\n冲突解决: {len(validated_entities)} → {len(resolved_entities)} 个 (移除 {removed_count} 个重叠)")
    
    # 阶段 2.4: 强类型清洗
    info("\n" + "─" * 60)
    info("【2.4 强类型清洗与转换 (Code-Layer)】")
    info("─" * 60)
    
    cleaner = TypeCleaner()
    variable_metas = []
    
    info("\n类型转换详情:")
    for entity in resolved_entities:
        cleaned_value, actual_type = cleaner.clean(entity['value'], entity['type'])
        
        var_meta = VariableMeta(
            name=entity['name'],
            original_text=entity['original_text'],
            value=cleaned_value,
            data_type=actual_type,
            start_index=entity['start_index'],
            end_index=entity['end_index']
        )
        variable_metas.append(var_meta)
        
        # 显示有意义的转换
        if str(entity['value']) != str(cleaned_value) or entity['type'] != actual_type:
            info(f"  🔄 \"{entity['original_text'][:15]}{'...' if len(entity['original_text']) > 15 else ''}\":")
            info(f"      {entity['value']} ({entity['type']}) → {cleaned_value} ({actual_type})")
    
    # 阶段 2.5: 模板生成
    info("\n" + "─" * 60)
    info("【2.5 模板生成与变量注入 (Code-Layer)】")
    info("─" * 60)
    
    sorted_vars = sorted(variable_metas, key=lambda v: v.start_index, reverse=True)
    template = processed_text
    
    for var in sorted_vars:
        placeholder = f"{{{{{var.name}}}}}"
        template = template[:var.start_index] + placeholder + template[var.end_index:]
    
    info("\n📝 生成的模板 (Prompt 2.0):")
    info("─" * 60)
    # 分行显示模板
    for line in template.split('\n'):
        info(line)
    info("─" * 60)
    
    # =========================================================================
    # 最终输出
    # =========================================================================
    info("\n\n" + "=" * 80)
    info("【最终输出: 变量注册表 (Variable Registry)】")
    info("=" * 80)
    
    variable_registry = []
    for var in variable_metas:
        registry_entry = {
            "variable": var.name,
            "original_text": var.original_text,
            "value": var.value,
            "type": var.data_type,
        }
        variable_registry.append(registry_entry)
    
    info(json.dumps(variable_registry, indent=2, ensure_ascii=False))

    # =========================================================================
    # 阶段3: Prompt 3.0 DSL 编译准备
    # =========================================================================
    info("\n>>> 准备 Prompt 2.0 结果用于 DSL 编译...")

    # 创建 Prompt20Result 对象
    prompt20_result = create_prompt20_result(
        source_prompt10_id=prompt10_result.id,
        original_text=processed_text,
        template_text=template,
        variables=variable_metas,
        processing_time_ms=0  # 实际应该计算，这里先设为0
    )

    # 转换为 DSL 编译器输入格式
    dsl_input = convert_prompt20_to_dsl_input(prompt20_result)
    info(f"✅ Prompt 2.0 结果已准备，包含 {len(prompt20_result.variables)} 个变量")

    # =========================================================================
    # 验证与应用示例
    # =========================================================================
    info("\n\n" + "=" * 80)
    info("【验证: 模板回填还原】")
    info("=" * 80)
    
    filled = template
    for var in variable_metas:
        placeholder = f"{{{{{var.name}}}}}"
        filled = filled.replace(placeholder, var.original_text)
    
    is_match = filled == processed_text
    info(f"\n还原后与 Prompt 1.0 一致: {'✅ 是' if is_match else '❌ 否'}")
    
    # 实际应用示例
    info("\n\n" + "=" * 80)
    info("【实际应用: 动态参数调整示例】")
    info("=" * 80)
    
    # 模拟参数调整
    adjustments = {
        "duration_weeks": ("8周", "12周"),
        "budget_wan": ("50万", "80万"),
        "team_size": ("5个人", "10个人"),
        "context_rounds": ("20轮", "50轮"),
    }
    
    info("\n用户调整参数:")
    for key, (old_val, new_val) in adjustments.items():
        info(f"  • {old_val} → {new_val}")
    
    customized = template
    for var in variable_metas:
        placeholder = f"{{{{{var.name}}}}}"
        # 检查是否需要替换
        replaced = False
        for key, (old_val, new_val) in adjustments.items():
            if key in var.name and var.original_text == old_val:
                customized = customized.replace(placeholder, new_val)
                replaced = True
                break
        if not replaced:
            customized = customized.replace(placeholder, var.original_text)
    
    info("\n📄 定制后的需求文档:")
    info("─" * 60)
    for line in customized.split('\n'):
        info(line)
    info("─" * 60)

    # =========================================================================
    # 阶段3: Prompt 3.0 DSL 编译
    # =========================================================================
    info("\n\n" + "=" * 80)
    info("【阶段 3: Prompt 3.0 DSL 编译 (prompt_dslcompiler)】")
    info("=" * 80)

    info("\n>>> 开始 DSL 编译...")
    start_time = time.time()

    # 创建自我修正循环编译器（策略 D）
    compiler = SelfCorrectionLoop(max_retries=3, use_mock=USE_MOCK, auto_fix_threshold=3)
    success, dsl_code, validation_result, compile_history = compiler.compile_with_retry(dsl_input)

    dsl_compile_time = int((time.time() - start_time) * 1000)

    # 检查编译状态
    compile_decision = compile_history.get('final_decision', 'unknown')

    if success or compile_decision == 'partial_auto_fixed':
        if compile_decision == 'partial_auto_fixed':
            warning(f"\n⚠️  DSL 部分修复成功（自动修复后仍有少量错误）！耗时: {dsl_compile_time}ms")
        else:
            info(f"\n✅ DSL 编译成功！耗时: {dsl_compile_time}ms")
        info("\n📄 生成的 DSL 代码:")
        info("─" * 60)
        for line in dsl_code.split('\n'):
            info(line)
        info("─" * 60)

        info("\n📊 验证结果:")
        info(validation_result.get_report())

        # 如果是部分修复状态，显示警告信息
        if compile_decision == 'partial_auto_fixed':
            warning("\n⚠️  注意：DSL 代码仍有少量验证错误，但已尝试进入代码生成阶段")
            if validation_result.errors:
                info("剩余错误:")
                for err in validation_result.errors:
                    error(f"  {err}")

        # =========================================================================
        # 阶段 4: Prompt 4.0 代码生成
        # =========================================================================
        info("\n\n" + "=" * 80)
        info("【阶段 4: Prompt 4.0 代码生成 (prompt_codegenetate)】")
        info("=" * 80)

        info("\n>>> 开始代码生成...")
        start_time_codegen = time.time()

        # 创建代码编译器
        code_compiler = WaActCompiler()
        try:
            modules, main_code, compile_details = code_compiler.compile(
                dsl_code,
                clustering_strategy="hybrid",
                visualize=False
            )

            codegen_time = int((time.time() - start_time_codegen) * 1000)
            info(f"\n✅ 代码生成成功！耗时: {codegen_time}ms")

            # 显示生成的模块
            info("\n📦 生成的模块:")
            for i, module in enumerate(modules, 1):
                info(f"  {i}. {module.name} ({'async' if module.is_async else 'sync'})")

            # 显示主工作流代码
            info("\n📄 主工作流代码:")
            info("─" * 60)
            for line in main_code.split('\n'):
                info(line)
            info("─" * 60)

            # 导出到文件
            output_file = "generated_workflow.py"
            code_compiler.export_to_file(modules, main_code, output_file)
            info(f"\n💾 代码已导出到: {output_file}")
        except Exception as e:
            error(f"\n❌ 代码生成失败: {e}")
            warning("DSL 代码存在严重错误，无法生成可执行代码")
            modules = []
            main_code = ""
            compile_details = {
                'step1_parsing': {'status': 'failed', 'reason': str(e)},
                'step2_dependency': {'status': 'skipped', 'reason': 'Parsing failed'},
                'step3_clustering': {'status': 'skipped', 'reason': 'Parsing failed'},
                'step4_generation': {'status': 'skipped', 'reason': 'Parsing failed'},
                'step5_orchestration': {'status': 'skipped', 'reason': 'Parsing failed'}
            }
            codegen_time = int((time.time() - start_time_codegen) * 1000)
    else:
        warning(f"\n⚠️  DSL 编译失败！耗时: {dsl_compile_time}ms")
        info("\n📄 生成的 DSL 代码 (有错误):")
        info("─" * 60)
        for line in dsl_code.split('\n'):
            info(line)
        info("─" * 60)

        info("\n❌ 验证错误:")
        for err in validation_result.errors[:5]:
            error(f"  {err}")

        # DSL 编译失败时，跳过代码生成阶段，但保留空数据
        info("\n>>> DSL 编译失败，跳过代码生成阶段")
        modules = []
        main_code = ""
        compile_details = {
            'step1_parsing': {'status': 'skipped', 'reason': 'DSL compilation failed'},
            'step2_dependency': {'status': 'skipped', 'reason': 'DSL compilation failed'},
            'step3_clustering': {'status': 'skipped', 'reason': 'DSL compilation failed'},
            'step4_generation': {'status': 'skipped', 'reason': 'DSL compilation failed'},
            'step5_orchestration': {'status': 'skipped', 'reason': 'DSL compilation failed'}
        }
        codegen_time = 0

    # =========================================================================
    # 总结
    # =========================================================================
    info("\n\n" + "█" * 80)
    info("█" + " " * 32 + "流水线总结" + " " * 34 + "█")
    info("█" * 80)
    
    info(f"""
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📊 处理统计                                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 原始输入长度: {len(RAW_INPUT):4} 字符                                              │
│ 标准化后长度: {len(processed_text):4} 字符                                              │
│ 术语替换数量: {len(prompt10_result.terminology_changes):4} 处                                              │
│ 识别变量数量: {len(variable_metas):4} 个                                              │
│ 变量类型分布:                                                                │
│   - Integer: {len([v for v in variable_metas if v.data_type == 'Integer']):2} 个                                                        │
│   - String:  {len([v for v in variable_metas if v.data_type == 'String']):2} 个                                                        │
│   - List:    {len([v for v in variable_metas if v.data_type == 'List']):2} 个                                                        │
│   - Boolean: {len([v for v in variable_metas if v.data_type == 'Boolean']):2} 个                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 🎯 预处理模块贡献 (Prompt 1.0 预处理)                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ • 口语化表达消除: '那个'、'吧'、'嘛'、'搞' → 规范书面语                     │
│ • 术语标准化: '套壳'→'基于API封装的应用', 'K8s'→'Kubernetes'                │
│ • 语法修正: 使文本结构更清晰规范                                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 🎯 结构化模块贡献 (Prompt 2.0 结构化)                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ • 实体抽取: 从标准化文本中识别所有可参数化的变量                            │
│ • 幻觉防御: 拒绝 LLM 虚构的不存在实体                                        │
│ • 类型清洗: '8周'→8(Integer), '需要支持'→True(Boolean)                      │
│ • 模板生成: 生成可复用的参数化模板                                          │
└─────────────────────────────────────────────────────────────────────────────┘
""")
    
    info("█" * 80)
    info("█" + " " * 32 + "演示完成" + " " * 36 + "█")
    info("█" * 80)
    
    # =========================================================================
    # 保存完整流水线历史记录
    # =========================================================================
    info("\n>>> 保存流水线历史记录...")
    
    # 统计变量类型
    type_stats = {}
    for var in variable_metas:
        dtype = var.data_type
        type_stats[dtype] = type_stats.get(dtype, 0) + 1
    
    # 准备第四阶段数据
    prompt40_modules_dict = []
    prompt40_module_count = 0
    prompt40_main_code = ""
    prompt40_time_ms = 0
    prompt40_step1_parsing = {}
    prompt40_step2_dependency = {}
    prompt40_step3_clustering = {}
    prompt40_step4_generation = {}
    prompt40_step5_orchestration = {}

    if success:
        # 转换 ModuleDefinition 对象为字典，排除不可序列化的字段
        for module in modules:
            module_dict = {
                'name': module.name,
                'inputs': module.inputs,
                'outputs': module.outputs,
                'is_async': module.is_async,
            }
            prompt40_modules_dict.append(module_dict)
        prompt40_module_count = len(modules)
        prompt40_main_code = main_code
        prompt40_time_ms = codegen_time

        # 保存编译步骤详情
        prompt40_step1_parsing = compile_details.get('step1_parsing', {})
        prompt40_step2_dependency = compile_details.get('step2_dependency', {})
        prompt40_step3_clustering = compile_details.get('step3_clustering', {})
        prompt40_step4_generation = compile_details.get('step4_generation', {})
        prompt40_step5_orchestration = compile_details.get('step5_orchestration', {})

    # 创建流水线历史记录
    pipeline_history = PipelineHistory(
        pipeline_id=generate_id(),
        timestamp=get_timestamp(),
        raw_input=RAW_INPUT,

        # 阶段1结果
        prompt10_id=prompt10_result.id,
        prompt10_original=prompt10_result.original_text,
        prompt10_processed=prompt10_result.processed_text,
        prompt10_mode=prompt10_result.mode,
        prompt10_steps=[s.to_dict() for s in prompt10_result.steps],
        prompt10_terminology_changes=prompt10_result.terminology_changes,
        prompt10_ambiguity_detected=prompt10_result.ambiguity_detected,
        prompt10_status=prompt10_result.status,
        prompt10_time_ms=prompt10_result.processing_time_ms,

        # 阶段2结果
        prompt20_id=generate_id(),
        prompt20_template=template,
        prompt20_variables=variable_registry,
        prompt20_variable_count=len(variable_metas),
        prompt20_type_stats=type_stats,
        prompt20_extraction_log=[],
        prompt20_time_ms=0,

        # 阶段3结果 (DSL编译) - 无论成功失败都记录 DSL 代码和验证结果
        prompt30_id=generate_id(),
        prompt30_dsl_code=dsl_code,  # 总是记录 DSL 代码
        prompt30_validation_result=validation_result.to_dict(),  # 总是记录验证结果
        prompt30_time_ms=dsl_compile_time,
        prompt30_compile_history=compile_history,  # 新增：编译历史（策略 D）
        prompt30_success=success,  # 新增：编译成功标志

        # 阶段4结果 (代码生成)
        prompt40_id=generate_id(),
        prompt40_modules=prompt40_modules_dict,
        prompt40_module_count=prompt40_module_count,
        prompt40_main_code=prompt40_main_code,
        prompt40_time_ms=prompt40_time_ms,

        # 阶段4子步骤详情
        prompt40_step1_parsing=prompt40_step1_parsing,
        prompt40_step2_dependency=prompt40_step2_dependency,
        prompt40_step3_clustering=prompt40_step3_clustering,
        prompt40_step4_generation=prompt40_step4_generation,
        prompt40_step5_orchestration=prompt40_step5_orchestration,

        # 整体状态 - 根据编译决策判断
        total_time_ms=prompt10_result.processing_time_ms + dsl_compile_time + prompt40_time_ms,
        error_message=None
    )

    # 根据编译决策更新整体状态
    if compile_decision == 'success':
        pipeline_history.overall_status = "success"
    elif compile_decision == 'partial_auto_fixed':
        pipeline_history.overall_status = "partial"  # DSL有误但能生成代码
    else:
        pipeline_history.overall_status = "partial"  # DSL失败
    
    # 保存历史记录
    history_manager = HistoryManager()
    history_manager.save_pipeline_history(pipeline_history)
    
    info(f"✅ 流水线历史已保存: {pipeline_history.pipeline_id}")
    info(f"📁 查看历史: python3 view_history.py pipeline")
    info(f"📄 导出报告: python3 view_history.py export-pipeline")


if __name__ == "__main__":
    run_full_pipeline()
