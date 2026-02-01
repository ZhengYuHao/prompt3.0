#!/usr/bin/env python3
"""
测试工作流调用关系图功能
"""

from history_manager import HistoryManager

def test_architecture_graph():
    """测试架构图生成功能"""
    print("=" * 60)
    print("测试工作流调用关系图功能")
    print("=" * 60)

    manager = HistoryManager()

    # 获取最新的流水线记录
    histories = manager.get_recent_pipeline_history(limit=10)

    if not histories:
        print("❌ 未找到流水线记录")
        return False

    # 找一个有多个模块的流水线
    target_history = None
    for history in histories:
        if history.prompt40_module_count >= 2:
            target_history = history
            break

    if not target_history:
        print("⚠️  未找到有多个模块的流水线，使用第一个记录")
        target_history = histories[0]

    print(f"\n📊 流水线信息:")
    print(f"  ID: {target_history.pipeline_id}")
    print(f"  时间: {target_history.timestamp}")
    print(f"  状态: {target_history.overall_status}")
    print(f"  模块数量: {target_history.prompt40_module_count}")

    # 生成 Mermaid 代码
    print(f"\n🔨 生成 Mermaid 代码...")
    mermaid_code = manager._generate_call_graph_mermaid(target_history)
    print(f"  ✅ Mermaid 代码生成成功 ({len(mermaid_code)} 字符)")

    # 导出 HTML
    print(f"\n💾 导出 HTML 报告...")
    html_content = manager.export_pipeline_html(target_history)
    print(f"  ✅ HTML 报告已生成 ({len(html_content)} 字符)")

    # 从导出路径中获取文件路径
    import os
    html_file = os.path.join(
        manager.storage_dir,
        f"pipeline_{target_history.pipeline_id}.html"
    )
    print(f"  📁 文件路径: {html_file}")

    # 验证 HTML 包含架构图
    print(f"\n✅ 验证 HTML 内容...")
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content_check = f.read()

    checks = [
        ("包含 Mermaid.js CDN", '<script src="https://cdn.jsdelivr.net/npm/mermaid' in html_content),
        ("包含架构图标题", '工作流调用关系图' in html_content),
        ("包含 Mermaid 代码块", '<div class="mermaid">' in html_content),
        ("包含输入节点", 'Input([用户输入' in html_content),
        ("包含主工作流节点", 'Main[main_workflow' in html_content),
        ("包含样式定义", 'classDef sync fill:#fff3cd' in html_content),
    ]

    all_passed = True
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"  {status} {check_name}")
        if not result:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！")
        print(f"📖 打开 HTML 查看效果: {html_file}")
    else:
        print("❌ 部分测试失败")
    print("=" * 60)

    return all_passed

if __name__ == "__main__":
    success = test_architecture_graph()
    exit(0 if success else 1)
