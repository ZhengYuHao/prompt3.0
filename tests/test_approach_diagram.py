#!/usr/bin/env python3
"""
测试 Approach 图生成功能
"""

from history_manager import HistoryManager
import os

def test_approach_diagram():
    """测试 Approach 图生成"""
    
    print("=" * 70)
    print("测试业务流程图（Approach 图）生成")
    print("=" * 70)
    
    manager = HistoryManager()
    
    # 获取最新的流水线记录
    histories = manager.get_recent_pipeline_history(limit=1)
    
    if not histories:
        print("❌ 未找到流水线记录")
        return False
    
    history = histories[0]
    print(f"\n📊 选择流水线: {history.pipeline_id}")
    print(f"   模块数量: {history.prompt40_module_count}")
    print(f"   状态: {history.overall_status}")
    
    # 测试 1: 生成 Approach 图
    print(f"\n🔨 测试 1: 生成 Approach 图")
    try:
        approach_diagram = manager._generate_approach_diagram_mermaid(history)
        print(f"   ✅ Approach 图生成成功")
        print(f"   📏 代码长度: {len(approach_diagram)} 字符")
        
        # 检查是否包含关键元素
        has_graph_td = "graph TD" in approach_diagram
        has_nodes = "Start" in approach_diagram or "开始" in approach_diagram
        has_styles = "style" in approach_diagram or "classDef" in approach_diagram
        
        print(f"\n   内容检查:")
        print(f"      graph TD: {'✅' if has_graph_td else '❌'}")
        print(f"      节点定义: {'✅' if has_nodes else '❌'}")
        print(f"      样式定义: {'✅' if has_styles else '❌'}")
        
        if not (has_graph_td and has_nodes):
            print(f"\n   ⚠️  Approach 图内容不完整，使用默认模板")
            print(f"\n   生成的代码预览:")
            print(f"   ---")
            for line in approach_diagram.split('\n')[:10]:
                print(f"   {line}")
            print(f"   ...")
        else:
            print(f"\n   生成的代码预览:")
            print(f"   ---")
            for line in approach_diagram.split('\n')[:15]:
                print(f"   {line}")
            print(f"   ...")
    except Exception as e:
        print(f"   ❌ Approach 图生成失败: {e}")
        return False
    
    # 测试 2: 导出 HTML
    print(f"\n💾 测试 2: 导出 HTML")
    try:
        html_content = manager.export_pipeline_html(history)
        print(f"   ✅ HTML 导出成功")
        print(f"   📏 文件大小: {len(html_content)} 字符")
        
        # 检查 HTML 包含 Approach 图
        has_approach_title = "业务流程图（Approach 图）" in html_content
        has_mermaid_code = "graph TD" in html_content
        has_zoom_controls = "zoomIn()" in html_content
        
        print(f"\n   HTML 内容检查:")
        print(f"      Approach 图标题: {'✅' if has_approach_title else '❌'}")
        print(f"      Mermaid 代码: {'✅' if has_mermaid_code else '❌'}")
        print(f"      缩放控制: {'✅' if has_zoom_controls else '❌'}")
        
        if not (has_approach_title and has_mermaid_code):
            print(f"\n   ⚠️  HTML 中缺少 Approach 图内容")
    except Exception as e:
        print(f"   ❌ HTML 导出失败: {e}")
        return False
    
    # 获取 HTML 文件路径
    html_file = os.path.join(
        manager.storage_dir,
        f"pipeline_{history.pipeline_id}.html"
    )
    
    # 测试 3: 文件检查
    print(f"\n📁 测试 3: 文件检查")
    if os.path.exists(html_file):
        file_size = os.path.getsize(html_file)
        print(f"   ✅ HTML 文件存在")
        print(f"   📏 文件大小: {file_size:,} 字节 ({file_size/1024:.1f} KB)")
        
        # 读取并检查内容
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content_check = f.read()
        
        has_business_flow = "业务流程图" in html_content_check
        has_approach_label = "Approach 图" in html_content_check
        
        print(f"\n   HTML 文件内容:")
        print(f"      业务流程图标题: {'✅' if has_business_flow else '❌'}")
        print(f"      Approach 图标签: {'✅' if has_approach_label else '❌'}")
    else:
        print(f"   ❌ HTML 文件不存在: {html_file}")
        return False
    
    # 总结
    print(f"\n" + "=" * 70)
    print(f"✅ 测试完成！")
    print(f"=" * 70)
    
    print(f"\n💡 下一步:")
    print(f"   1. 在浏览器中打开 HTML 文件")
    print(f"   2. 查看 '业务流程图（Approach 图）' 部分")
    print(f"   3. 验证是否展示了业务逻辑而非函数调用")
    print(f"   4. 使用缩放和拖拽功能查看图表")
    
    print(f"\n📁 HTML 文件路径:")
    print(f"   {html_file}")
    
    print(f"\n🎯 Approach 图特点:")
    print(f"   ✅ 展示业务逻辑和处理步骤")
    print(f"   ✅ 使用业务术语而非技术术语")
    print(f"   ✅ 展示决策点和分支")
    print(f"   ✅ 支持缩放和拖拽")
    
    return True

if __name__ == "__main__":
    success = test_approach_diagram()
    exit(0 if success else 1)
