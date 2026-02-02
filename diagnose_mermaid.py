#!/usr/bin/env python3
"""
Mermaid 诊断工具
"""

from history_manager import HistoryManager
import os

def diagnose():
    print("=" * 70)
    print("Mermaid 诊断工具")
    print("=" * 70)

    manager = HistoryManager()
    histories = manager.get_recent_pipeline_history(limit=1)

    if not histories:
        print("❌ 未找到流水线记录")
        return

    history = histories[0]
    print(f"\n📊 流水线 ID: {history.pipeline_id}")

    # 生成 Mermaid 代码
    try:
        approach_diagram = manager._generate_approach_diagram_mermaid(history)
        print(f"✅ Mermaid 代码生成成功")
    except Exception as e:
        print(f"❌ Mermaid 代码生成失败: {e}")
        return

    print(f"\n生成的 Mermaid 代码:")
    print("=" * 70)
    print(approach_diagram)
    print("=" * 70)

    # 创建测试 HTML 文件
    test_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Mermaid 测试</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
</head>
<body>
    <h1>Mermaid 测试（降级到 10.6.1）</h1>
    <div class="mermaid">
{approach_diagram}
    </div>
    <hr>
    <h2>原始代码</h2>
    <pre style="background:#f0f0f0;padding:20px;border:1px solid #ccc;">
{approach_diagram}
    </pre>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose',
            flowchart: {{
                useMaxWidth: false,
                htmlLabels: true
            }},
            logLevel: 'error'
        }});
    </script>
</body>
</html>
"""

    test_file = "mermaid_test.html"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_html)

    print(f"\n✅ 测试 HTML 文件已创建: {test_file}")
    print(f"💡 请在浏览器中打开 {test_file} 进行测试")
    print(f"\n📝 测试说明:")
    print(f"   1. 在浏览器中打开 {test_file}")
    print(f"   2. 检查图表是否正常显示")
    print(f"   3. 如果正常显示，说明 Mermaid 10.6.1 版本可用")
    print(f"   4. 如果仍然显示错误，请查看浏览器控制台（F12）")

    print(f"\n🔗 在线测试:")
    print(f"   访问 https://mermaid.live/")
    print(f"   将上面的 Mermaid 代码粘贴进去测试")

if __name__ == "__main__":
    diagnose()
