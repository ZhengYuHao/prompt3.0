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


def print_usage():
    """打印使用说明"""
    info("""
历史记录查看工具 - 使用说明
================================================================================

查看历史记录:
  python view_history.py prompt10 [limit]     # 查看 Prompt 1.0 历史（默认10条）
  python view_history.py prompt20 [limit]     # 查看 Prompt 2.0 历史
  python view_history.py pipeline [limit]     # 查看完整流水线历史

导出 HTML 报告:
  python view_history.py export-prompt10 [timestamp]   # 导出 Prompt 1.0 报告
  python view_history.py export-pipeline [pipeline_id] # 导出流水线报告

示例:
  python view_history.py pipeline 5           # 查看最近5条流水线记录
  python view_history.py export-pipeline      # 导出最新流水线报告
================================================================================
""")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "prompt10":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            view_prompt10_history(limit)
        
        elif cmd == "prompt20":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            view_prompt20_history(limit)
        
        elif cmd == "pipeline":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            view_pipeline_history(limit)
        
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
        # 默认显示流水线历史
        view_pipeline_history()
