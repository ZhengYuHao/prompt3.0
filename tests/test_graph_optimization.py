#!/usr/bin/env python3
"""
测试架构图优化功能
"""

from history_manager import HistoryManager

def test_architecture_graph_optimization():
    """测试架构图的显示优化"""
    
    print("=" * 60)
    print("测试架构图优化功能")
    print("=" * 60)
    
    manager = HistoryManager()
    
    # 获取最新的流水线记录
    histories = manager.get_recent_pipeline_history(limit=5)
    
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
        print("⚠️  未找到有多个模块的流水线，使用最新记录")
        target_history = histories[0]
    
    print(f"\n📊 选择流水线: {target_history.pipeline_id}")
    print(f"   模块数量: {target_history.prompt40_module_count}")
    
    # 导出 HTML
    print(f"\n💾 导出 HTML 报告...")
    html_content = manager.export_pipeline_html(target_history)
    print(f"   ✅ 导出成功")
    print(f"   文件大小: {len(html_content)} 字符")
    
    # 验证功能
    print(f"\n✅ 功能验证:")
    
    # 1. 检查显示空间优化
    has_large_container = 'min-height: 600px' in html_content
    has_min_width = 'min-width: 1000px' in html_content
    has_large_padding = 'padding: 20px' in html_content
    
    print(f"\n   📐 显示空间优化:")
    print(f"      容器最小高度 (600px): {'✅' if has_large_container else '❌'}")
    print(f"      图表最小宽度 (1000px): {'✅' if has_min_width else '❌'}")
    print(f"      优化的内边距: {'✅' if has_large_padding else '❌'}")
    
    # 2. 检查缩放控制
    has_zoom_in = "zoomIn()" in html_content
    has_zoom_out = "zoomOut()" in html_content
    has_reset = "resetZoom()" in html_content
    has_zoom_level = 'zoomLevel' in html_content
    
    print(f"\n   🔍 缩放控制:")
    print(f"      放大按钮: {'✅' if has_zoom_in else '❌'}")
    print(f"      缩小按钮: {'✅' if has_zoom_out else '❌'}")
    print(f"      重置按钮: {'✅' if has_reset else '❌'}")
    print(f"      缩放比例显示: {'✅' if has_zoom_level else '❌'}")
    
    # 3. 检查鼠标滚轮缩放
    has_wheel_event = "addEventListener('wheel'" in html_content
    has_zoom_delta = "delta = e.deltaY" in html_content
    has_update_zoom = "updateZoom()" in html_content
    
    print(f"\n   🖱️  鼠标滚轮缩放:")
    print(f"      滚轮事件监听: {'✅' if has_wheel_event else '❌'}")
    print(f"      滚轮方向检测: {'✅' if has_zoom_delta else '❌'}")
    print(f"      动态缩放更新: {'✅' if has_update_zoom else '❌'}")
    
    # 4. 检查拖拽功能
    has_mousedown = "addEventListener('mousedown'" in html_content
    has_mousemove = "addEventListener('mousemove'" in html_content
    has_dragging = "isDragging" in html_content
    
    print(f"\n   ✋ 拖拽功能:")
    print(f"      鼠标按下事件: {'✅' if has_mousedown else '❌'}")
    print(f"      鼠标移动事件: {'✅' if has_mousemove else '❌'}")
    print(f"      拖拽状态管理: {'✅' if has_dragging else '❌'}")
    
    # 5. 检查 Mermaid 配置
    has_max_width_disabled = 'useMaxWidth: false' in html_content
    has_security_loose = "securityLevel: 'loose'" in html_content
    
    print(f"\n   🎨 Mermaid 配置:")
    print(f"      禁用最大宽度限制: {'✅' if has_max_width_disabled else '❌'}")
    print(f"      宽松安全级别: {'✅' if has_security_loose else '❌'}")
    
    # 6. 检查交互提示
    has_hint = "提示：可以使用鼠标滚轮缩放" in html_content or "双击重置缩放" in html_content
    
    print(f"\n   💡 用户提示:")
    print(f"      交互提示文本: {'✅' if has_hint else '❌'}")
    
    # 总结
    all_checks = [
        has_large_container, has_min_width, has_large_padding,
        has_zoom_in, has_zoom_out, has_reset, has_zoom_level,
        has_wheel_event, has_zoom_delta, has_update_zoom,
        has_mousedown, has_mousemove, has_dragging,
        has_max_width_disabled, has_security_loose, has_hint
    ]
    
    passed = sum(all_checks)
    total = len(all_checks)
    
    print(f"\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} 项通过 ✅" if passed == total else f"测试结果: {passed}/{total} 项通过 ⚠️")
    print("=" * 60)
    
    # 显示文件路径
    import os
    html_file = os.path.join(
        manager.storage_dir,
        f"pipeline_{target_history.pipeline_id}.html"
    )
    
    print(f"\n📁 HTML 文件路径: {html_file}")
    print(f"\n💡 在浏览器中打开文件，可以体验以下功能:")
    print(f"   1. 点击放大/缩小按钮调整图表大小")
    print(f"   2. 使用鼠标滚轮快速缩放")
    print(f"   3. 拖拽图表查看不同区域")
    print(f"   4. 双击图表重置缩放")
    
    return passed == total

if __name__ == "__main__":
    success = test_architecture_graph_optimization()
    exit(0 if success else 1)
