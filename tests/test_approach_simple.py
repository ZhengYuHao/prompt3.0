#!/usr/bin/env python3
from history_manager import HistoryManager
import os

print("=" * 70)
print("测试业务流程图（Approach 图）生成")
print("=" * 70)

manager = HistoryManager()
histories = manager.get_recent_pipeline_history(limit=1)

if not histories:
    print("❌ 未找到流水线记录")
    exit(1)

history = histories[0]
print(f"\n📊 选择流水线: {history.pipeline_id}")
print(f"   模块数量: {history.prompt40_module_count}")

print(f"\n🔨 生成 Approach 图...")
approach_diagram = manager._generate_approach_diagram_mermaid(history)
print(f"   ✅ Approach 图生成成功")
print(f"   📏 代码长度: {len(approach_diagram)} 字符")

print(f"\n   生成的代码预览:")
print(f"   ---")
for line in approach_diagram.split('\n')[:20]:
    print(f"   {line}")
print(f"   ...")

print(f"\n💾 导出 HTML...")
html_content = manager.export_pipeline_html(history)
print(f"   ✅ HTML 导出成功")

has_approach = "业务流程图（Approach 图）" in html_content
has_mermaid = "graph TD" in html_content

print(f"\n   HTML 内容检查:")
print(f"      Approach 图标题: {'✅' if has_approach else '❌'}")
print(f"      Mermaid 代码: {'✅' if has_mermaid else '❌'}")

html_file = os.path.join(
    manager.storage_dir,
    f"pipeline_{history.pipeline_id}.html"
)

print(f"\n📁 HTML 文件: {html_file}")

print(f"\n" + "=" * 70)
print(f"✅ 测试完成！")
print(f"=" * 70)
