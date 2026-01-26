"""
2.py 模块功能演示
展示实体抽取与变量定义的完整流程
"""

import json
import re
from typing import List, Dict, Any

# 导入 2.py 的核心组件
import sys
sys.path.insert(0, '.')

from logger import info, warning, error

# ============================================================================
# 增强的模拟 LLM 抽取器（模拟真实 LLM 的复杂输出）
# ============================================================================

class EnhancedMockExtractor:
    """增强版模拟抽取器，模拟真实 LLM 的各种情况"""
    
    def extract(self, text: str) -> List[Dict]:
        """
        模拟 LLM 抽取结果，包含：
        - 正确的实体
        - 幻觉实体（测试防火墙）
        - 重叠实体（测试冲突解决）
        - 多种数据类型
        """
        entities = []
        
        # ===== 1. Integer 类型：数字+单位 =====
        for match in re.finditer(r'(\d+)(年|周|月|天|小时|人|个|名|次)', text):
            unit_map = {
                '年': 'years', '周': 'weeks', '月': 'months', 
                '天': 'days', '小时': 'hours', '人': 'people',
                '个': 'count', '名': 'people', '次': 'times'
            }
            entities.append({
                "name": f"{unit_map.get(match.group(2), 'value')}_{len(entities)}",
                "original_text": match.group(0),
                "start_index": match.start(),
                "end_index": match.end(),
                "type": "Integer",
                "value": match.group(0)  # 原始文本，让 TypeCleaner 提取数字
            })
        
        # ===== 2. String 类型：专业术语/角色 =====
        tech_terms = [
            ("Java程序员", "role"),
            ("Python开发", "skill"),
            ("数据分析", "focus_area"),
            ("机器学习", "focus_area"),
            ("前端开发", "skill"),
            ("后端架构", "skill"),
            ("项目经理", "role"),
            ("RAG系统", "system_type"),
            ("向量数据库", "component"),
            ("Embedding模型", "component"),
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
        
        # ===== 3. List 类型：逗号/顿号分隔 =====
        list_patterns = [
            (r'包括[：:]\s*([^。，]+(?:[、,，][^。，]+)+)', 'items'),
            (r'涵盖[：:]\s*([^。，]+(?:[、,，][^。，]+)+)', 'coverage'),
            (r'技术栈[：:]\s*([^。]+)', 'tech_stack'),
        ]
        for pattern, name in list_patterns:
            match = re.search(pattern, text)
            if match:
                entities.append({
                    "name": f"{name}_{len(entities)}",
                    "original_text": match.group(1),
                    "start_index": match.start(1),
                    "end_index": match.end(1),
                    "type": "List",
                    "value": match.group(1)
                })
        
        # ===== 4. Boolean 类型 =====
        bool_patterns = [
            (r'(需要|不需要)(认证|审核|测试)', 'require'),
            (r'(是否)(必须|可选)', 'optional'),
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
                    "value": match.group(1)  # "需要" 或 "不需要"
                })
        
        # ===== 5. 模拟 LLM 幻觉（防火墙测试） =====
        # 添加一个原文中不存在的实体
        entities.append({
            "name": "hallucination_test",
            "original_text": "这是LLM虚构的内容",  # 原文中不存在
            "start_index": 999,
            "end_index": 1010,
            "type": "String",
            "value": "幻觉内容"
        })
        
        # ===== 6. 模拟重叠实体（冲突解决测试） =====
        # 如果有 "3年经验"，同时添加 "3年" 和 "3年经验"
        exp_match = re.search(r'(\d+年)(经验|工作经验)', text)
        if exp_match:
            # 短实体
            entities.append({
                "name": "short_duration",
                "original_text": exp_match.group(1),  # "3年"
                "start_index": exp_match.start(1),
                "end_index": exp_match.end(1),
                "type": "Integer",
                "value": exp_match.group(1)
            })
            # 长实体（应该被保留）
            entities.append({
                "name": "full_experience",
                "original_text": exp_match.group(0),  # "3年经验"
                "start_index": exp_match.start(),
                "end_index": exp_match.end(),
                "type": "String",
                "value": exp_match.group(0)
            })
        
        return entities


# ============================================================================
# 导入 2.py 的核心类
# ============================================================================

# 读取并执行 2.py（排除 main 部分）
with open('2.py', 'r', encoding='utf-8') as f:
    code = f.read()
    # 只执行到 main 函数之前
    code_parts = code.split("# ========== 使用示例 ==========")
    exec(code_parts[0])


# ============================================================================
# 演示函数
# ============================================================================

def demo_complex_extraction():
    """演示复杂场景下的实体抽取"""
    
    # 复杂测试文本（包含多种实体类型）
    test_text = """
请为一位有5年经验的Java程序员设计一个为期3周的培训计划。
培训内容包括：Python开发、数据分析、机器学习基础。
团队规模为8人，每周培训3次，每次2小时。
技术栈: FastAPI、PostgreSQL、Redis、Docker。
该培训需要认证，完成后可获得内部资质证书。
最终目标是让学员能够独立开发RAG系统，涵盖向量数据库、Embedding模型的使用。
""".strip()

    info("=" * 80)
    info("【2.py 模块功能完整演示】")
    info("=" * 80)
    
    info("\n" + "─" * 80)
    info("【输入文本 - Prompt 1.0】")
    info("─" * 80)
    info(test_text)
    
    # ===== 阶段 2.1: 语义扫描 =====
    info("\n" + "=" * 80)
    info("【阶段 2.1: 语义扫描与实体定位 (LLM-Layer)】")
    info("=" * 80)
    
    extractor = EnhancedMockExtractor()
    raw_entities = extractor.extract(test_text)
    
    info(f"\nLLM 识别到 {len(raw_entities)} 个候选实体:")
    for i, entity in enumerate(raw_entities, 1):
        info(f"  {i}. [{entity['type']:8}] \"{entity['original_text']}\" "
             f"(位置: {entity['start_index']}-{entity['end_index']})")
    
    # ===== 阶段 2.2: 幻觉防火墙 =====
    info("\n" + "=" * 80)
    info("【阶段 2.2: 幻觉防火墙与存在性校验 (Code-Layer)】")
    info("=" * 80)
    
    firewall = HallucinationFirewall()
    validated_entities = []
    rejected_count = 0
    
    for entity in raw_entities:
        is_valid, msg = firewall.validate_existence(entity, test_text)
        if is_valid:
            # 检查索引
            if not firewall.validate_index(entity, test_text):
                # 自动修正索引
                snippet = entity['original_text']
                idx = test_text.find(snippet)
                if idx != -1:
                    entity['start_index'] = idx
                    entity['end_index'] = idx + len(snippet)
                    info(f"  ⚠️  索引已修正: \"{snippet}\" -> 位置 {idx}-{idx+len(snippet)}")
            
            validated_entities.append(entity)
            info(f"  ✅ 验证通过: \"{entity['original_text']}\"")
        else:
            rejected_count += 1
            warning(f"  ❌ 拒绝 (幻觉检测): \"{entity['original_text']}\" - {msg}")
    
    info(f"\n📊 防火墙统计: 通过 {len(validated_entities)} 个, 拒绝 {rejected_count} 个")
    
    # ===== 冲突解决 =====
    info("\n" + "=" * 80)
    info("【重叠实体冲突解决 (最长覆盖原则)】")
    info("=" * 80)
    
    resolver = EntityConflictResolver()
    before_count = len(validated_entities)
    resolved_entities = resolver.resolve_overlaps(validated_entities)
    after_count = len(resolved_entities)
    
    if before_count != after_count:
        info(f"  🔄 冲突解决: {before_count} 个 -> {after_count} 个 (移除 {before_count - after_count} 个重叠实体)")
        info("  💡 示例: \"3年\" 与 \"3年经验\" 重叠，保留更长的 \"3年经验\"")
    else:
        info(f"  ✅ 无冲突: 保留全部 {after_count} 个实体")
    
    # ===== 阶段 2.3: 强类型清洗 =====
    info("\n" + "=" * 80)
    info("【阶段 2.3: 强类型清洗与转换 (Code-Layer)】")
    info("=" * 80)
    
    cleaner = TypeCleaner()
    variable_metas = []
    
    for entity in resolved_entities:
        original_value = entity['value']
        original_type = entity['type']
        cleaned_value, actual_type = cleaner.clean(original_value, original_type)
        
        var_meta = VariableMeta(
            name=entity['name'],
            original_text=entity['original_text'],
            value=cleaned_value,
            data_type=actual_type,
            start_index=entity['start_index'],
            end_index=entity['end_index']
        )
        variable_metas.append(var_meta)
        
        # 显示类型转换详情
        type_changed = original_type != actual_type
        value_changed = str(original_value) != str(cleaned_value)
        
        if type_changed or value_changed:
            info(f"  🔄 \"{entity['original_text']}\":")
            info(f"      原始: {original_value} ({original_type})")
            info(f"      转换: {cleaned_value} ({actual_type})")
        else:
            info(f"  ✅ \"{entity['original_text']}\": {cleaned_value} ({actual_type})")
    
    # ===== 阶段 2.4: 模板生成 =====
    info("\n" + "=" * 80)
    info("【阶段 2.4: 模板生成与变量注入 (Code-Layer)】")
    info("=" * 80)
    
    # 按位置倒序排序，从后往前替换
    sorted_vars = sorted(variable_metas, key=lambda v: v.start_index, reverse=True)
    template = test_text
    
    for var in sorted_vars:
        placeholder = f"{{{{{var.name}}}}}"
        template = template[:var.start_index] + placeholder + template[var.end_index:]
    
    info("\n【生成的模板 - Prompt 2.0】")
    info("─" * 80)
    info(template)
    
    # ===== 变量注册表 =====
    info("\n" + "=" * 80)
    info("【变量注册表 (Variable Registry)】")
    info("=" * 80)
    
    variable_registry = []
    for var in variable_metas:
        registry_entry = {
            "variable": var.name,
            "original_text": var.original_text,
            "value": var.value,
            "type": var.data_type,
            "position": f"{var.start_index}-{var.end_index}"
        }
        variable_registry.append(registry_entry)
    
    info(json.dumps(variable_registry, indent=2, ensure_ascii=False))
    
    # ===== 验证：模板回填 =====
    info("\n" + "=" * 80)
    info("【验证: 模板回填还原】")
    info("=" * 80)
    
    filled_template = template
    for var in variable_metas:
        placeholder = f"{{{{{var.name}}}}}"
        filled_template = filled_template.replace(placeholder, var.original_text)
    
    is_identical = filled_template == test_text
    info(f"\n还原后与原文一致: {'✅ 是' if is_identical else '❌ 否'}")
    
    if not is_identical:
        info("\n【差异对比】")
        info(f"原文长度: {len(test_text)}, 还原长度: {len(filled_template)}")
    
    # ===== 使用示例 =====
    info("\n" + "=" * 80)
    info("【实际应用: 动态参数替换示例】")
    info("=" * 80)
    
    # 模拟用户修改参数
    new_values = {
        "years_0": "10年",       # 原 "5年经验" 中的年份
        "weeks_1": "6周",        # 原 "3周"
        "people_2": "15人",      # 原 "8人"
    }
    
    info("\n假设用户想修改以下参数:")
    for var_name, new_val in new_values.items():
        for var in variable_metas:
            if var.name == var_name:
                info(f"  • {var.original_text} → {new_val}")
    
    customized = template
    for var_name, new_val in new_values.items():
        placeholder = f"{{{{{var_name}}}}}"
        if placeholder in customized:
            customized = customized.replace(placeholder, new_val)
    
    # 填充未修改的变量
    for var in variable_metas:
        placeholder = f"{{{{{var.name}}}}}"
        if placeholder in customized:
            customized = customized.replace(placeholder, var.original_text)
    
    info("\n【定制后的文本】")
    info("─" * 80)
    info(customized)
    
    info("\n" + "=" * 80)
    info("【演示完成】")
    info("=" * 80)


if __name__ == "__main__":
    demo_complex_extraction()
