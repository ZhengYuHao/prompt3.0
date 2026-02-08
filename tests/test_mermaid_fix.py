#!/usr/bin/env python3
"""
测试 Mermaid 语法修复
"""

from history_manager import HistoryManager

def test_mermaid_syntax():
    print("=" * 70)
    print("测试 Mermaid 语法修复")
    print("=" * 70)

    manager = HistoryManager()
    histories = manager.get_recent_pipeline_history(limit=1)

    if not histories:
        print("❌ 未找到流水线记录")
        return False

    history = histories[0]
    print(f"\n📊 选择流水线: {history.pipeline_id}")

    print(f"\n🔨 生成 Approach 图...")
    try:
        approach_diagram = manager._generate_approach_diagram_mermaid(history)
        print(f"   ✅ Approach 图生成成功")
        print(f"   📏 代码长度: {len(approach_diagram)} 字符")
    except Exception as e:
        print(f"   ❌ 生成失败: {e}")
        return False

    print(f"\n   生成的 Mermaid 代码:")
    print(f"   ---")
    for line in approach_diagram.split('\n'):
        print(f"   {line}")
    print(f"   ---")

    # 检查语法
    print(f"\n🔍 语法检查:")
    checks = {
        "graph TD": "graph TD" in approach_diagram,
        "classDef": "classDef" in approach_diagram,
        "class 关键字": "class Start" in approach_diagram or "class Process" in approach_diagram,
        "无 ::: 语法": ":::" not in approach_diagram,
    }

    all_passed = True
    for name, status in checks.items():
        icon = "✅" if status else "❌"
        print(f"   {icon} {name}")
        if not status:
            all_passed = False

    # 生成 HTML
    print(f"\n💾 生成 HTML...")
    try:
        html_content = manager.export_pipeline_html(history)
        print(f"   ✅ HTML 生成成功")
        print(f"   📏 文件大小: {len(html_content)} 字符")
    except Exception as e:
        print(f"   ❌ HTML 生成失败: {e}")
        return False

    # 检查 HTML 中的 Mermaid 代码
    print(f"\n🔍 HTML 中的 Mermaid 代码检查:")
    html_checks = {
        "包含 graph TD": "graph TD" in html_content,
        "包含 classDef": "classDef" in html_content,
        "包含 class 定义": "class Start" in html_content,
        "无 ::: 语法": ":::" not in html_content,
    }

    for name, status in html_checks.items():
        icon = "✅" if status else "❌"
        print(f"   {icon} {name}")
        if not status:
            all_passed = False

    # 总结
    print(f"\n" + "=" * 70)
    if all_passed:
        print("✅ 所有测试通过！Mermaid 语法修复成功！")
    else:
        print("⚠️  部分测试失败")
    print("=" * 70)

    print(f"\n💡 下一步:")
    print(f"   1. 在浏览器中打开生成的 HTML 文件")
    print(f"   2. 检查业务流程图是否正常显示")
    print(f"   3. 体验缩放和拖拽功能")

    return all_passed

if __name__ == "__main__":
    success = test_mermaid_syntax()
    exit(0 if success else 1)
