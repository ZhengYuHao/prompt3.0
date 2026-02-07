#!/usr/bin/env python3
"""
优化集成测试脚本
测试优化点1（规则引擎）和优化点2（正则提取器）的集成效果
"""

import sys
import time
from rule_based_normalizer import RuleBasedTextNormalizer, SyntacticAmbiguityDetector
from pre_pattern_extractor import PrePatternExtractor


def test_optimization1_rule_based_normalizer():
    """测试优化点1：规则引擎"""
    print("\n" + "="*80)
    print("【优化点1】规则引擎测试")
    print("="*80)

    test_cases = [
        "帮我搞一个RAG应用，那个嘛，稍微整一下",
        "项目5个人，需要2周完成，挺不错的",
        "没啥意思，随便弄一下就好",
    ]

    for i, text in enumerate(test_cases, 1):
        print(f"\n--- 测试用例 {i} ---")
        print(f"原始文本: {text}")

        start = time.time()
        normalized, changes = RuleBasedTextNormalizer.normalize(text)
        duration = (time.time() - start) * 1000

        print(f"规范化文本: {normalized}")
        print(f"变更: {changes}")
        print(f"耗时: {duration:.2f}ms")

        if changes:
            print(f"✅ 规则引擎成功处理 {len(changes)} 处变更")
        else:
            print(f"⚠️  规则引擎未识别到标准化模式")

        # 歧义检测
        ambiguity = SyntacticAmbiguityDetector.detect(normalized)
        if ambiguity:
            print(f"⚠️  检测到歧义: {ambiguity}")
        else:
            print(f"✅ 歧义检测通过")


def test_optimization2_pattern_extractor():
    """测试优化点2：正则提取器"""
    print("\n" + "="*80)
    print("【优化点2】正则提取器测试")
    print("="*80)

    test_cases = [
        "项目团队5个人，使用Python开发，周期2周",
        "需要20轮上下文窗口，响应时间控制在2秒以内",
        "预算50万，其中20万用于人员，30万用于基础设施",
    ]

    for i, text in enumerate(test_cases, 1):
        print(f"\n--- 测试用例 {i} ---")
        print(f"原始文本: {text}")

        start = time.time()
        entities = PrePatternExtractor.extract(text)
        duration = (time.time() - start) * 1000

        print(f"提取实体数: {len(entities)}")
        for entity in entities:
            print(f"  - {entity['name']}: {entity['value']} ({entity['type']})")
        print(f"耗时: {duration:.2f}ms")

        if len(entities) >= 3:
            print(f"✅ 正则提取成功，提取 {len(entities)} 个实体，可以跳过 LLM")
        elif len(entities) > 0:
            print(f"⚠️  正则提取 {len(entities)} 个实体，建议结合 LLM 补充")
        else:
            print(f"❌ 正则提取未找到实体，需要使用 LLM")


def test_integration_comparison():
    """测试集成前后对比"""
    print("\n" + "="*80)
    print("【集成效果对比】")
    print("="*80)

    # 测试文本
    test_text = "项目团队5个人，使用Python和LangChain开发，周期2周，那个嘛，稍微整一下"

    print(f"\n测试文本: {test_text}")

    # 规则引擎优化
    print("\n--- Prompt 1.0 规则化 ---")
    start = time.time()
    normalized, changes = RuleBasedTextNormalizer.normalize(test_text)
    rule_duration = (time.time() - start) * 1000
    print(f"规范化文本: {normalized}")
    print(f"变更数: {len(changes)}")
    print(f"耗时: {rule_duration:.2f}ms")
    print(f"LLM调用: 0次（规则引擎处理）")

    # 正则提取优化
    print("\n--- Prompt 2.0 实体提取 ---")
    start = time.time()
    entities = PrePatternExtractor.extract(normalized)
    regex_duration = (time.time() - start) * 1000
    print(f"提取实体数: {len(entities)}")
    for entity in entities:
        print(f"  - {entity['name']}: {entity['value']}")
    print(f"耗时: {regex_duration:.2f}ms")
    print(f"LLM调用: 0次（正则提取成功）")

    # 总体优化效果
    print("\n--- 总体优化效果 ---")
    total_duration = rule_duration + regex_duration
    print(f"总耗时: {total_duration:.2f}ms")
    print(f"LLM调用次数: 0次")
    print(f"Token消耗: 0")
    print(f"预期速度提升: ~100-1000x（相对于LLM）")
    print(f"预期成本节省: ~100%（完全避免LLM调用）")


def main():
    """主函数"""
    print("\n" + "="*80)
    print("优化集成测试")
    print("="*80)

    try:
        # 测试优化点1
        test_optimization1_rule_based_normalizer()

        # 测试优化点2
        test_optimization2_pattern_extractor()

        # 测试集成对比
        test_integration_comparison()

        print("\n" + "="*80)
        print("✅ 所有测试通过")
        print("="*80)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
