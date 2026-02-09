"""
历史记录查看工具
用于查看和导出处理历史记录
支持 Prompt 1.0、Prompt 2.0 和完整流水线历史
"""

from history_manager import HistoryManager
from logger import info


def view_prompt10_history(limit: int = 10):
    """查看最近的 Prompt 1.0 处理历史"""
    manager = HistoryManager()
    recent_history = manager.get_recent_history(limit=limit)
    
    if not recent_history:
        info("暂无 Prompt 1.0 处理历史记录")
        return
    
    info(f"\n找到 {len(recent_history)} 条 Prompt 1.0 处理记录:\n")
    
    for i, hist in enumerate(recent_history, 1):
        info(f"{'='*80}")
        info(f"记录 #{i}")
        manager.print_comparison(hist)
        info("\n")


def view_prompt20_history(limit: int = 10):
    """查看最近的 Prompt 2.0 处理历史"""
    manager = HistoryManager()
    recent_history = manager.get_recent_prompt20_history(limit=limit)
    
    if not recent_history:
        info("暂无 Prompt 2.0 处理历史记录")
        return
    
    info(f"\n找到 {len(recent_history)} 条 Prompt 2.0 处理记录:\n")
    
    for i, hist in enumerate(recent_history, 1):
        info(f"{'='*80}")
        info(f"记录 #{i} - ID: {hist.id}")
        info(f"{'='*80}")
        info(f"时间: {hist.timestamp}")
        info(f"关联 Prompt 1.0 ID: {hist.source_prompt10_id}")
        info(f"变量数量: {hist.variable_count}")
        info(f"类型分布: {hist.type_stats}")
        info(f"处理耗时: {hist.processing_time_ms}ms")
        info(f"\n【模板】:")
        info(hist.template_text[:200] + "..." if len(hist.template_text) > 200 else hist.template_text)
        info(f"\n【变量列表】:")
        for var in hist.variables[:5]:
            info(f"  • {var.get('variable')}: {var.get('value')} ({var.get('type')})")
        if len(hist.variables) > 5:
            info(f"  ... 还有 {len(hist.variables) - 5} 个变量")
        info("\n")


def view_pipeline_history(limit: int = 10):
    """查看最近的完整流水线历史"""
    manager = HistoryManager()
    recent_history = manager.get_recent_pipeline_history(limit=limit)
    
    if not recent_history:
        info("暂无流水线处理历史记录")
        return
    
    info(f"\n找到 {len(recent_history)} 条流水线处理记录:\n")
    
    for i, hist in enumerate(recent_history, 1):
        info(f"{'='*80}")
        info(f"流水线 #{i} - ID: {hist.pipeline_id}")
        manager.print_pipeline_comparison(hist)
        info("\n")


def export_pipeline_html(pipeline_id: str = None):
    """
    导出流水线HTML报告
    
    Args:
        pipeline_id: 指定流水线ID，如果为None则导出最新一条记录
    """
    manager = HistoryManager()
    
    if pipeline_id:
        history = manager.load_pipeline_history(pipeline_id)
        if not history:
            info(f"未找到流水线 ID 为 {pipeline_id} 的记录")
            return
        histories = [history]
    else:
        histories = manager.get_recent_pipeline_history(limit=1)
        if not histories:
            info("暂无流水线处理历史记录")
            return
    
    for hist in histories:
        manager.export_pipeline_html(hist)


def export_html(timestamp: str = None):
    """
    导出HTML格式的对比报告（Prompt 1.0）
    
    Args:
        timestamp: 指定时间戳，如果为None则导出最新一条记录
    """
    manager = HistoryManager()
    
    if timestamp:
        history = manager.get_history(timestamp)
        if not history:
            info(f"未找到时间戳为 {timestamp} 的记录")
            return
        histories = [history]
    else:
        histories = manager.get_recent_history(limit=1)
        if not histories:
            info("暂无处理历史记录")
            return
    
    for hist in histories:
        html_file = manager.export_comparison_html(hist)
        info(f"HTML报告已导出: {html_file}")


def list_pipeline_histories(limit: int = 20):
    """列出所有流水线记录，显示 pipeline_id 和时间"""
    manager = HistoryManager()
    recent_history = manager.get_recent_pipeline_history(limit=limit)

    if not recent_history:
        info("暂无流水线处理历史记录")
        return

    info(f"\n找到 {len(recent_history)} 条流水线处理记录:\n")
    info(f"{'='*90}")
    info(f"{'序号':<4} {'Pipeline ID':<10} {'时间':<20} {'状态':<10} {'变量数':<6} {'模块数':<6}")
    info(f"{'='*90}")

    for i, hist in enumerate(recent_history, 1):
        prompt10_status = hist.prompt10_status or "unknown"
        prompt40_module_count = hist.prompt40_module_count or 0
        prompt20_variable_count = len(hist.prompt20_variables) if hist.prompt20_variables else 0

        info(f"{i:<4} {hist.pipeline_id:<10} {hist.timestamp:<20} {prompt10_status:<10} "
             f"{prompt20_variable_count:<6} {prompt40_module_count:<6}")

    info(f"{'='*90}")
    info(f"\n使用以下命令查看详情:")
    info(f"  python view_history.py show-pipeline <pipeline_id>    # 查看指定流水线详情")
    info(f"  python view_history.py export-pipeline <pipeline_id>  # 导出指定流水线报告")


def show_pipeline_detail(pipeline_id: str):
    """显示指定流水线的详细信息"""
    manager = HistoryManager()
    history = manager.load_pipeline_history(pipeline_id)

    if not history:
        info(f"未找到流水线 ID 为 {pipeline_id} 的记录")
        return

    info(f"\n{'='*90}")
    info(f"流水线详情 - ID: {pipeline_id}")
    info(f"{'='*90}")
    info(f"时间: {history.timestamp}")
    info(f"原始输入长度: {len(history.raw_input)} 字符")

    # Prompt 1.0 信息
    info(f"\n{'─'*90}")
    info(f"【阶段 1: Prompt 1.0 预处理】")
    info(f"{'─'*90}")
    info(f"Prompt 1.0 ID: {history.prompt10_id}")
    info(f"状态: {history.prompt10_status}")
    info(f"处理时间: {history.prompt10_time_ms}ms")
    info(f"模式: {history.prompt10_mode}")
    if history.prompt10_ambiguity_detected:
        warning("⚠️  检测到歧义")

    # Prompt 2.0 信息
    info(f"\n{'─'*90}")
    info(f"【阶段 2: Prompt 2.0 结构化】")
    info(f"{'─'*90}")
    info(f"Prompt 2.0 ID: {history.prompt20_id}")
    if history.prompt20_variables:
        info(f"变量数量: {len(history.prompt20_variables)}")
        info(f"\n变量列表 (前10个):")
        for i, var in enumerate(history.prompt20_variables[:10], 1):
            info(f"  {i}. {var['variable']}: {var['value']} ({var['type']})")
        if len(history.prompt20_variables) > 10:
            info(f"  ... 还有 {len(history.prompt20_variables) - 10} 个变量")

    # Prompt 3.0 信息
    info(f"\n{'─'*90}")
    info(f"【阶段 3: Prompt 3.0 DSL 编译】")
    info(f"{'─'*90}")
    info(f"DSL 编译时间: {history.prompt30_time_ms}ms")
    info(f"编译状态: {'成功' if history.prompt30_success else '失败'}")
    if history.prompt30_dsl_code:
        info(f"DSL 代码长度: {len(history.prompt30_dsl_code)} 字符")
    if history.prompt30_compile_history:
        compile_history = history.prompt30_compile_history
        info(f"编译策略: {compile_history.get('final_decision', 'unknown')}")

    # Prompt 4.0 信息
    info(f"\n{'─'*90}")
    info(f"【阶段 4: Prompt 4.0 代码生成】")
    info(f"{'─'*90}")
    info(f"代码生成时间: {history.prompt40_time_ms}ms")
    info(f"生成模块数: {history.prompt40_module_count}")

    if history.prompt40_step1_parsing:
        step1 = history.prompt40_step1_parsing
        info(f"\n  步骤1 - 词法解析: {step1.get('total_blocks', 0)} 个代码块")
    if history.prompt40_step4_generation:
        step4 = history.prompt40_step4_generation
        info(f"  步骤4 - 代码生成: {step4.get('total_modules', 0)} 个模块")


def print_usage():
    """打印使用说明"""
    info("""
历史记录查看工具 - 使用说明
================================================================================

列出流水线记录:
  python view_history.py list [limit]              # 列出流水线记录（默认20条）

查看详细历史:
  python view_history.py prompt10 [limit]          # 查看 Prompt 1.0 历史
  python view_history.py prompt20 [limit]          # 查看 Prompt 2.0 历史
  python view_history.py pipeline [limit]          # 查看流水线摘要
  python view_history.py show-pipeline <pipeline_id>  # 查看指定流水线详情

导出 HTML 报告:
  python view_history.py export-prompt10 [timestamp]    # 导出 Prompt 1.0 报告
  python view_history.py export-pipeline [pipeline_id]  # 导出指定流水线报告

示例:
  python view_history.py list 30                    # 列出最近30条流水线记录
  python view_history.py show-pipeline a9b880b1     # 查看指定流水线详情
  python view_history.py export-pipeline a9b880b1   # 导出指定流水线报告
================================================================================
""")


def show_optimization_metrics(pipeline_id: str):
    """显示优化指标"""
    manager = HistoryManager()
    history = manager.load_pipeline_history(pipeline_id)

    if not history:
        info(f"未找到流水线 ID 为 {pipeline_id} 的记录")
        return

    info(f"\n{'='*90}")
    info(f"优化指标 - 流水线 {pipeline_id}")
    info(f"{'='*90}")

    # Prompt 1.0 优化指标
    if hasattr(history, 'prompt10_rule_stats') and history.prompt10_rule_stats:
        stats = history.prompt10_rule_stats
        info(f"\n【Prompt 1.0 规则化效果】")
        info(f"  处理模式: {stats.get('processing_mode', 'unknown')}")
        info(f"  LLM 调用次数: {stats.get('llm_calls', 0)}")
        info(f"  规范化变更: {stats.get('normalization_changes', 0)} 次")
        info(f"  歧义检测: {'是 ⚠️' if stats.get('ambiguity_detected') else '否 ✅'}")

        if stats.get('llm_calls', 0) == 0:
            info(f"  ⚡ Token 节省: ~1000 tokens")
            info(f"  ⚡ 速度提升: ~10-100x")

    # Prompt 2.0 优化指标
    if hasattr(history, 'prompt20_optimization_stats') and history.prompt20_optimization_stats:
        stats = history.prompt20_optimization_stats
        info(f"\n【Prompt 2.0 实体提取优化】")
        info(f"  正则提取: {stats.get('regex_count', 0)} 个")
        info(f"  LLM 提取: {stats.get('llm_count', 0)} 个")
        info(f"  合并结果: {stats.get('merged_count', 0)} 个")
        info(f"  调用 LLM: {'是' if stats.get('llm_called') else '否 ✅'}")

        if not stats.get('llm_called'):
            info(f"  ⚡ Token 节省: ~1000 tokens")

    # Prompt 3.0 优化指标
    if hasattr(history, 'prompt30_optimization_stats') and history.prompt30_optimization_stats:
        stats = history.prompt30_optimization_stats
        info(f"\n【Prompt 3.0 DSL 编译优化】")
        info(f"  代码构建: {'成功 ✅' if stats.get('code_build') else '失败'}")
        info(f"  LLM 回退: {'是' if stats.get('llm_fallback') else '否 ✅'}")
        info(f"  LLM 调用: {stats.get('llm_calls', 0)} 次")
        info(f"  编译耗时: {stats.get('compile_time_ms', 0)} ms")

        if not stats.get('llm_fallback'):
            info(f"  ⚡ Token 节省: ~1500 tokens")
            info(f"  ⚡ 速度提升: ~3-5x")

    # 总体优化效果
    total_llm_calls = 0
    if hasattr(history, 'prompt10_rule_stats') and history.prompt10_rule_stats:
        total_llm_calls += history.prompt10_rule_stats.get('llm_calls', 0)
    if hasattr(history, 'prompt20_optimization_stats') and history.prompt20_optimization_stats:
        total_llm_calls += history.prompt20_optimization_stats.get('llm_calls', 0)
    if hasattr(history, 'prompt30_optimization_stats') and history.prompt30_optimization_stats:
        total_llm_calls += history.prompt30_optimization_stats.get('llm_calls', 0)

    info(f"\n【总体优化效果】")
    info(f"  总 LLM 调用次数: {total_llm_calls}")
    info(f"  预估成本节省: {(4 - total_llm_calls) / 4 * 100:.1f}%")

    # 缓存统计
    if history.total_cache_hits > 0 or history.total_cache_misses > 0:
        hits = history.total_cache_hits or 0
        misses = history.total_cache_misses or 0
        total = hits + misses
        hit_rate = history.cache_hit_rate or 0.0

        info(f"\n【缓存统计】")
        info(f"  缓存命中: {hits} 次")
        info(f"  缓存未命中: {misses} 次")
        info(f"  命中率: {hit_rate*100:.1f}%")

        if total > 0:
            saved_tokens = hits * 500
            saved_cost = saved_tokens * 0.001 / 1000
            info(f"  ⚡ 节省 Token: ~{saved_tokens} tokens")
            info(f"  💰 节省成本: ~${saved_cost:.4f}")

    # 验证统计
    if hasattr(history, 'validation_stats') and history.validation_stats:
        stats = history.validation_stats
        info(f"\n【验证统计】")
        info(f"  模板填充错误: {stats.get('template_filling_errors', 0)}")
        info(f"  变量命名错误: {stats.get('variable_naming_errors', 0)}")
        info(f"  变量类型错误: {stats.get('variable_type_errors', 0)}")
        info(f"  验证耗时: {stats.get('total_validation_time_ms', 0)} ms")

    # 自动修复统计
    if hasattr(history, 'auto_fix_stats') and history.auto_fix_stats:
        stats = history.auto_fix_stats
        info(f"\n【自动修复统计】")
        info(f"  总修复次数: {stats.get('total_fixes', 0)}")
        info(f"  语法错误修复: {stats.get('syntax_errors_fixed', 0)}")
        info(f"  未定义变量修复: {stats.get('undefined_vars_fixed', 0)}")
        info(f"  控制流修复: {stats.get('control_flow_fixed', 0)}")
        info(f"  修复成功率: {stats.get('fix_success_rate', 0)*100:.1f}%")


def show_cache_stats(pipeline_id: str = None):
    """显示缓存统计"""
    manager = HistoryManager()

    if pipeline_id:
        history = manager.load_pipeline_history(pipeline_id)
    else:
        histories = manager.get_recent_pipeline_history(limit=10)
        if not histories:
            info("暂无流水线处理历史记录")
            return
        history = histories[0]

    if not history:
        return

    info(f"\n{'='*90}")
    info(f"缓存统计 - 流水线 {history.pipeline_id}")
    info(f"{'='*90}")

    hits = history.total_cache_hits or 0
    misses = history.total_cache_misses or 0
    total = hits + misses
    hit_rate = history.cache_hit_rate or 0.0

    info(f"  缓存命中: {hits} 次")
    info(f"  缓存未命中: {misses} 次")
    info(f"  总调用: {total} 次")
    info(f"  命中率: {hit_rate*100:.1f}%")

    if total > 0:
        saved_tokens = hits * 500
        saved_cost = saved_tokens * 0.001 / 1000
        info(f"\n  ⚡ 节省 Token: ~{saved_tokens} tokens")
        info(f"  💰 节省成本: ~${saved_cost:.4f}")


def show_validation_details(pipeline_id: str):
    """显示验证详情"""
    manager = HistoryManager()
    history = manager.load_pipeline_history(pipeline_id)

    if not history:
        info(f"未找到流水线 ID 为 {pipeline_id} 的记录")
        return

    info(f"\n{'='*90}")
    info(f"验证详情 - 流水线 {history.pipeline_id}")
    info(f"{'='*90}")

    if hasattr(history, 'validation_stats') and history.validation_stats:
        stats = history.validation_stats
        info(f"  模板填充错误: {stats.get('template_filling_errors', 0)}")
        info(f"  变量命名错误: {stats.get('variable_naming_errors', 0)}")
        info(f"  变量类型错误: {stats.get('variable_type_errors', 0)}")
        info(f"  验证耗时: {stats.get('total_validation_time_ms', 0)} ms")
    else:
        info("  暂无验证统计信息")


def show_auto_fix_stats(pipeline_id: str):
    """显示自动修复统计"""
    manager = HistoryManager()
    history = manager.load_pipeline_history(pipeline_id)

    if not history:
        info(f"未找到流水线 ID 为 {pipeline_id} 的记录")
        return

    info(f"\n{'='*90}")
    info(f"自动修复统计 - 流水线 {history.pipeline_id}")
    info(f"{'='*90}")

    if hasattr(history, 'auto_fix_stats') and history.auto_fix_stats:
        stats = history.auto_fix_stats
        info(f"  总修复次数: {stats.get('total_fixes', 0)}")
        info(f"  语法错误修复: {stats.get('syntax_errors_fixed', 0)}")
        info(f"  未定义变量修复: {stats.get('undefined_vars_fixed', 0)}")
        info(f"  控制流修复: {stats.get('control_flow_fixed', 0)}")
        info(f"  修复成功率: {stats.get('fix_success_rate', 0)*100:.1f}%")
    else:
        info("  暂无自动修复统计信息")


def compare_pipelines(pipeline_id1: str, pipeline_id2: str):
    """对比两个流水线的优化效果"""
    manager = HistoryManager()
    history1 = manager.load_pipeline_history(pipeline_id1)
    history2 = manager.load_pipeline_history(pipeline_id2)

    if not history1 or not history2:
        info("未找到指定的流水线记录")
        return

    info(f"\n{'='*90}")
    info(f"对比分析 - {pipeline_id1} vs {pipeline_id2}")
    info(f"{'='*90}")

    # Prompt 1.0 对比
    info(f"\n【Prompt 1.0】")
    stats1 = history1.prompt10_rule_stats or {}
    stats2 = history2.prompt10_rule_stats or {}
    info(f"  {pipeline_id1}: LLM调用={stats1.get('llm_calls', 0)}, 变更={stats1.get('normalization_changes', 0)}")
    info(f"  {pipeline_id2}: LLM调用={stats2.get('llm_calls', 0)}, 变更={stats2.get('normalization_changes', 0)}")

    # Prompt 2.0 对比
    info(f"\n【Prompt 2.0】")
    stats1 = history1.prompt20_optimization_stats or {}
    stats2 = history2.prompt20_optimization_stats or {}
    info(f"  {pipeline_id1}: 正则={stats1.get('regex_count', 0)}, LLM={stats1.get('llm_count', 0)}")
    info(f"  {pipeline_id2}: 正则={stats2.get('regex_count', 0)}, LLM={stats2.get('llm_count', 0)}")

    # Prompt 3.0 对比
    info(f"\n【Prompt 3.0】")
    stats1 = history1.prompt30_optimization_stats or {}
    stats2 = history2.prompt30_optimization_stats or {}
    info(f"  {pipeline_id1}: 代码构建={stats1.get('code_build', False)}, LLM回退={stats1.get('llm_fallback', False)}")
    info(f"  {pipeline_id2}: 代码构建={stats2.get('code_build', False)}, LLM回退={stats2.get('llm_fallback', False)}")

    # 缓存对比
    info(f"\n【缓存】")
    hit_rate1 = history1.cache_hit_rate or 0.0
    hit_rate2 = history2.cache_hit_rate or 0.0
    info(f"  {pipeline_id1}: 命中率={hit_rate1*100:.1f}%")
    info(f"  {pipeline_id2}: 命中率={hit_rate2*100:.1f}%")


def print_usage():
    """打印使用说明"""
    info("""
历史记录查看工具 - 使用说明
================================================================================

列出流水线记录:
  python view_history.py list [limit]              # 列出流水线记录（默认20条）

查看详细历史:
  python view_history.py prompt10 [limit]          # 查看 Prompt 1.0 历史
  python view_history.py prompt20 [limit]          # 查看 Prompt 2.0 历史
  python view_history.py pipeline [limit]          # 查看流水线摘要
  python view_history.py show-pipeline <pipeline_id>  # 查看指定流水线详情

导出 HTML 报告:
  python view_history.py export-prompt10 [timestamp]    # 导出 Prompt 1.0 报告
  python view_history.py export-pipeline [pipeline_id]  # 导出指定流水线报告

优化指标查看（新增）:
  python view_history.py metrics <pipeline_id>       # 显示所有优化指标
  python view_history.py cache-stats <pipeline_id>   # 显示缓存统计
  python view_history.py validation <pipeline_id>    # 显示验证详情
  python view_history.py auto-fix <pipeline_id>     # 显示自动修复统计
  python view_history.py compare <pipeline_id1> <pipeline_id2>  # 对比优化效果

示例:
  python view_history.py list 30                    # 列出最近30条流水线记录
  python view_history.py show-pipeline a9b880b1     # 查看指定流水线详情
  python view_history.py export-pipeline a9b880b1   # 导出指定流水线报告
  python view_history.py metrics a9b880b1           # 查看优化指标
  python view_history.py cache-stats a9b880b1       # 查看缓存统计
================================================================================""")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "list":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            list_pipeline_histories(limit)

        elif cmd == "prompt10":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            view_prompt10_history(limit)

        elif cmd == "prompt20":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            view_prompt20_history(limit)

        elif cmd == "pipeline":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            view_pipeline_history(limit)

        elif cmd == "show-pipeline":
            if len(sys.argv) < 3:
                info("错误: 请指定 pipeline_id")
                info("用法: python view_history.py show-pipeline <pipeline_id>")
            else:
                show_pipeline_detail(sys.argv[2])

        elif cmd == "export-prompt10":
            timestamp = sys.argv[2] if len(sys.argv) > 2 else None
            export_html(timestamp)

        elif cmd == "export-pipeline":
            pipeline_id = sys.argv[2] if len(sys.argv) > 2 else None
            export_pipeline_html(pipeline_id)

        # 新增：优化指标相关命令
        elif cmd == "metrics":
            if len(sys.argv) < 3:
                info("错误: 请指定 pipeline_id")
                info("用法: python view_history.py metrics <pipeline_id>")
            else:
                show_optimization_metrics(sys.argv[2])

        elif cmd == "cache-stats":
            pipeline_id = sys.argv[2] if len(sys.argv) > 2 else None
            show_cache_stats(pipeline_id)

        elif cmd == "validation":
            if len(sys.argv) < 3:
                info("错误: 请指定 pipeline_id")
                info("用法: python view_history.py validation <pipeline_id>")
            else:
                show_validation_details(sys.argv[2])

        elif cmd == "auto-fix":
            if len(sys.argv) < 3:
                info("错误: 请指定 pipeline_id")
                info("用法: python view_history.py auto-fix <pipeline_id>")
            else:
                show_auto_fix_stats(sys.argv[2])

        elif cmd == "compare":
            if len(sys.argv) < 4:
                info("错误: 请指定两个 pipeline_id")
                info("用法: python view_history.py compare <pipeline_id1> <pipeline_id2>")
            else:
                compare_pipelines(sys.argv[2], sys.argv[3])

        # 兼容旧命令
        elif cmd == "view":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            view_prompt10_history(limit)

        elif cmd == "export":
            timestamp = sys.argv[2] if len(sys.argv) > 2 else None
            export_html(timestamp)

        else:
            print_usage()
    else:
        # 默认列出流水线记录
        list_pipeline_histories()
