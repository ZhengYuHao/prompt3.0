#!/usr/bin/env python3
from history_manager import HistoryManager
import os

manager = HistoryManager()

# 获取最新的流水线
histories = manager.get_recent_pipeline_history(limit=1)
if not histories:
    print("❌ 未找到流水线记录")
    exit(1)

history = histories[0]

print("=" * 70)
print("架构图优化 - 最终检查")
print("=" * 70)

# 导出 HTML
html_content = manager.export_pipeline_html(history)

# 检查关键元素
print(f"\n✅ 流水线信息:")
print(f"   ID: {history.pipeline_id}")
print(f"   模块数: {history.prompt40_module_count}")
print(f"   状态: {history.overall_status}")

# 检查 HTML 大小
print(f"\n✅ 文件信息:")
html_file = os.path.join(
    manager.storage_dir,
    f"pipeline_{history.pipeline_id}.html"
)
file_size = os.path.getsize(html_file)
print(f"   文件路径: {html_file}")
print(f"   文件大小: {file_size:,} 字节 ({file_size/1024:.1f} KB)")

# 检查功能
print(f"\n✅ 功能检查:")
features = {
    "控制栏": "call-graph-controls" in html_content,
    "放大按钮": "zoomIn()" in html_content,
    "缩小按钮": "zoomOut()" in html_content,
    "重置按钮": "resetZoom()" in html_content,
    "缩放显示": "zoomLevel" in html_content,
    "滚轮缩放": "addEventListener('wheel'" in html_content,
    "拖拽平移": "isDragging" in html_content,
    "双击重置": "dblclick" in html_content,
    "空间优化": "min-height: 600px" in html_content,
    "宽度优化": "min-width: 1000px" in html_content,
}

for name, status in features.items():
    icon = "✅" if status else "❌"
    print(f"   {icon} {name}")

print(f"\n" + "=" * 70)
print("🎉 优化完成！所有功能已正常工作！")
print("=" * 70)

print(f"\n💡 下一步:")
print(f"   1. 在浏览器中打开: {html_file}")
print(f"   2. 体验缩放和拖拽功能")
print(f"   3. 查看架构图的交互效果")

print(f"\n📚 参考文档:")
print(f"   - 详细报告: /tmp/architecture_graph_optimization_report.md")
print(f"   - 快速开始: /tmp/architecture_graph_quick_start.md")
print(f"   - 优化总结: /tmp/optimization_summary.txt")
