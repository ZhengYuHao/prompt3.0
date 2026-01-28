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
