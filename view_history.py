"""
历史记录查看工具
用于查看和导出处理历史记录
"""

from history_manager import HistoryManager
from logger import info


def view_history(limit: int = 10):
    """查看最近的处理历史"""
    manager = HistoryManager()
    recent_history = manager.get_recent_history(limit=limit)
    
    if not recent_history:
        info("暂无处理历史记录")
        return
    
    info(f"\n找到 {len(recent_history)} 条最近的处理记录:\n")
    
    for i, hist in enumerate(recent_history, 1):
        info(f"{'='*80}")
        info(f"记录 #{i}")
        manager.print_comparison(hist)
        info("\n")


def export_html(timestamp: str = None):
    """
    导出HTML格式的对比报告
    
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


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "view":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            view_history(limit)
        elif sys.argv[1] == "export":
            timestamp = sys.argv[2] if len(sys.argv) > 2 else None
            export_html(timestamp)
        else:
            info("用法:")
            info("  python view_history.py view [limit]  # 查看最近N条记录")
            info("  python view_history.py export [timestamp]  # 导出HTML报告")
    else:
        view_history()
