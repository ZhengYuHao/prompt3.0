"""
优化集成测试脚本
验证 P0 阶段的所有优化点是否正常工作
"""

import time
import json
from pipeline import PromptPipeline, process_prompt
from data_models import ProcessingMode
from logger import info, warning, error


def test_prompt10_optimization():
    """测试 Prompt 1.0 规则化优化"""
    info("\n" + "=" * 80)
    info("测试 1: Prompt 1.0 规则化优化")
    info("=" * 80)

    test_cases = [
        "帮我搞一个RAG的应用",
        "那个，帮我弄一下大模型的项目吧",
        "需要5个人，其中2个Java，3个Python",
    ]

    term_mapping = {
        "大模型": "大型语言模型(LLM)",
        "RAG": "检索增强生成(RAG)",
    }

    total_llm_calls = 0
    total_time = 0

    for i, test_input in enumerate(test_cases, 1):
        info(f"\n>>> 测试用例 {i}: {test_input}")

        pipeline = PromptPipeline(
            mode=ProcessingMode.DICTIONARY,
            term_mapping=term_mapping,
            use_mock_llm=False,
            enable_cache=False  # 暂时禁用缓存，测试规则引擎
        )

        start = time.time()
        result = pipeline.run(test_input, stop_on_ambiguity=False)
        elapsed = (time.time() - start) * 1000
        total_time += elapsed

        # 获取 LLM 调用次数
        llm_calls = result.prompt10_result.llm_calls_count if result.prompt10_result else 0
        total_llm_calls += llm_calls

        # 获取规则引擎统计
        rule_stats = result.prompt10_result.rule_engine_stats if result.prompt10_result and hasattr(result.prompt10_result, 'rule_engine_stats') else {}

        info(f"  处理时间: {elapsed:.2f}ms")
        info(f"  LLM 调用次数: {llm_calls}")
        info(f"  规则引擎变更: {rule_stats.get('normalization_changes', 0)} 处")
        info(f"  处理模式: {rule_stats.get('processing_mode', 'unknown')}")

    avg_time = total_time / len(test_cases)
    info(f"\n>>> 测试结果总结:")
    info(f"  平均处理时间: {avg_time:.2f}ms")
    info(f"  总 LLM 调用次数: {total_llm_calls}")
    info(f"  每个 case 平均 LLM 调用: {total_llm_calls / len(test_cases):.2f}")

    # 验证优化效果
    if total_llm_calls == 0:
        info("✅ Prompt 1.0 优化通过: LLM 调用为 0，规则引擎完全接管")
        return True
    else:
        warning(f"⚠️ Prompt 1.0 优化未完全生效: 仍有 {total_llm_calls} 次 LLM 调用")
        return False


def test_prompt20_optimization():
    """测试 Prompt 2.0 实体提取优化"""
    info("\n" + "=" * 80)
    info("测试 2: Prompt 2.0 实体提取优化")
    info("=" * 80)

    test_cases = [
        "项目需要5个人，为期2周",
        "预算50万，需要3个Java开发人员",
        "处理时间限制在2秒以内，支持中英文双语",
    ]

    total_llm_calls = 0
    total_time = 0
    total_regex_entities = 0

    for i, test_input in enumerate(test_cases, 1):
        info(f"\n>>> 测试用例 {i}: {test_input}")

        pipeline = PromptPipeline(
            mode=ProcessingMode.DICTIONARY,
            use_mock_llm=False,
            enable_cache=False  # 暂时禁用缓存
        )

        start = time.time()
        result = pipeline.run(test_input, stop_on_ambiguity=False)
        elapsed = (time.time() - start) * 1000
        total_time += elapsed

        # 获取优化统计
        opt_stats = {}
        if hasattr(pipeline, 'llm_client'):
            # 从 llm_client 获取统计（需要在实际调用中实现）
            opt_stats = getattr(pipeline.llm_client, '_last_optimization_stats', {})

        info(f"  处理时间: {elapsed:.2f}ms")
        info(f"  提取变量数: {len(result.prompt20_result.variables) if result.prompt20_result else 0}")

    avg_time = total_time / len(test_cases)
    info(f"\n>>> 测试结果总结:")
    info(f"  平均处理时间: {avg_time:.2f}ms")

    # 验证优化效果
    if avg_time < 100:  # 如果平均时间小于 100ms，说明优化有效
        info("✅ Prompt 2.0 优化通过: 处理速度显著提升")
        return True
    else:
        warning(f"⚠️ Prompt 2.0 优化效果有限: 平均处理时间 {avg_time:.2f}ms")
        return False


def test_cache_optimization():
    """测试缓存机制优化"""
    info("\n" + "=" * 80)
    info("测试 3: 缓存机制优化")
    info("=" * 80)

    test_input = "帮我搞一个RAG的应用"

    # 第一次运行（不使用缓存）
    info("\n>>> 第一次运行（不使用缓存）:")
    pipeline1 = PromptPipeline(
        mode=ProcessingMode.DICTIONARY,
        use_mock_llm=False,
        enable_cache=True  # 启用缓存
    )

    start1 = time.time()
    result1 = pipeline1.run(test_input)
    time1 = (time.time() - start1) * 1000

    # 获取缓存统计
    cache_stats1 = pipeline1.llm_client.get_cache_stats()

    info(f"  处理时间: {time1:.2f}ms")
    info(f"  缓存命中: {cache_stats1.get('hits', 0)}")
    info(f"  缓存未命中: {cache_stats1.get('misses', 0)}")

    # 第二次运行（应该命中缓存）
    info("\n>>> 第二次运行（应该命中缓存）:")
    pipeline2 = PromptPipeline(
        mode=ProcessingMode.DICTIONARY,
        use_mock_llm=False,
        enable_cache=True
    )

    start2 = time.time()
    result2 = pipeline2.run(test_input)
    time2 = (time.time() - start2) * 1000

    # 获取缓存统计
    cache_stats2 = pipeline2.llm_client.get_cache_stats()

    info(f"  处理时间: {time2:.2f}ms")
    info(f"  缓存命中: {cache_stats2.get('hits', 0)}")
    info(f"  缓存未命中: {cache_stats2.get('misses', 0)}")

    # 计算加速比
    if time2 > 0:
        speedup = time1 / time2
        info(f"\n>>> 缓存加速效果:")
        info(f"  加速比: {speedup:.2f}x")

        if speedup > 2:
            info("✅ 缓存优化通过: 加速效果显著")
            return True
        else:
            warning(f"⚠️ 缓存优化效果有限: 加速比 {speedup:.2f}x")
            return False
    else:
        warning("⚠️ 无法计算加速比")
        return False


def test_overall_optimization():
    """测试整体优化效果"""
    info("\n" + "=" * 80)
    info("测试 4: 整体优化效果")
    info("=" * 80)

    test_input = "帮我设计一个5人的团队，开发基于RAG的智能问答系统，预计需要2个月"

    # 创建流水线（启用所有优化）
    pipeline = PromptPipeline(
        mode=ProcessingMode.DICTIONARY,
        term_mapping={
            "大模型": "大型语言模型(LLM)",
            "RAG": "检索增强生成(RAG)",
        },
        use_mock_llm=False,
        enable_cache=True
    )

    # 运行完整流水线
    start = time.time()
    result = pipeline.run(test_input)
    total_time = (time.time() - start) * 1000

    # 收集优化统计
    llm_calls = result.prompt10_result.llm_calls_count if result.prompt10_result else 0
    rule_stats = result.prompt10_result.rule_engine_stats if result.prompt10_result and hasattr(result.prompt10_result, 'rule_engine_stats') else {}
    cache_stats = pipeline.llm_client.get_cache_stats()

    info(f"\n>>> 整体优化统计:")
    info(f"  总处理时间: {total_time:.2f}ms")
    info(f"  LLM 调用次数: {llm_calls}")
    info(f"  规则引擎变更: {rule_stats.get('normalization_changes', 0)} 处")
    info(f"  缓存命中率: {cache_stats.get('hit_rate', 0) * 100:.2f}%")
    info(f"  提取变量数: {len(result.prompt20_result.variables) if result.prompt20_result else 0}")

    # 评估整体效果
    if llm_calls == 0 and total_time < 3000:
        info("✅ 整体优化通过: LLM 调用为 0，处理速度满足要求")
        return True
    else:
        warning(f"⚠️ 整体优化有待改进: LLM 调用 {llm_calls} 次，处理时间 {total_time:.2f}ms")
        return False


def main():
    """主测试函数"""
    info("\n" + "█" * 80)
    info("█" + " " * 25 + "优化集成测试" + " " * 39 + "█")
    info("█" * 80)

    results = {
        "Prompt 1.0 规则化": None,
        "Prompt 2.0 实体提取": None,
        "缓存机制": None,
        "整体优化效果": None
    }

    try:
        results["Prompt 1.0 规则化"] = test_prompt10_optimization()
    except Exception as e:
        error(f"Prompt 1.0 测试失败: {e}")
        results["Prompt 1.0 规则化"] = False

    try:
        results["Prompt 2.0 实体提取"] = test_prompt20_optimization()
    except Exception as e:
        error(f"Prompt 2.0 测试失败: {e}")
        results["Prompt 2.0 实体提取"] = False

    try:
        results["缓存机制"] = test_cache_optimization()
    except Exception as e:
        error(f"缓存机制测试失败: {e}")
        results["缓存机制"] = False

    try:
        results["整体优化效果"] = test_overall_optimization()
    except Exception as e:
        error(f"整体优化测试失败: {e}")
        results["整体优化效果"] = False

    # 总结报告
    info("\n" + "█" * 80)
    info("█" + " " * 30 + "测试总结" + " " * 36 + "█")
    info("█" * 80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    info(f"\n>>> 测试结果:")
    for test_name, passed_flag in results.items():
        status = "✅ 通过" if passed_flag else "❌ 失败"
        info(f"  {test_name}: {status}")

    info(f"\n>>> 总体评估:")
    info(f"  通过: {passed}/{total}")
    if passed == total:
        info("  🎉 所有优化点测试通过！")
    elif passed >= total * 0.75:
        info("  ⚠️ 大部分优化点测试通过，需要进一步优化")
    else:
        info("  ❌ 多数优化点测试未通过，需要重点改进")

    # 导出测试报告
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "pass_rate": passed / total if total > 0 else 0
        }
    }

    report_file = "optimization_test_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    info(f"\n>>> 测试报告已保存: {report_file}")

    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
