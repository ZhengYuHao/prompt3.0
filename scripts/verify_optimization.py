#!/usr/bin/env python3
from history_manager import HistoryManager

manager = HistoryManager()
histories = manager.get_recent_pipeline_history(limit=1)

if histories:
    history = histories[0]
    html_content = manager.export_pipeline_html(history)
    
    features = {
        '显示空间优化': 'min-height: 600px' in html_content,
        '缩放按钮': 'zoomIn()' in html_content and 'zoomOut()' in html_content,
        '鼠标滚轮': "addEventListener('wheel'" in html_content,
        '拖拽功能': 'isDragging' in html_content,
        '重置功能': 'resetZoom()' in html_content,
        '缩放比例显示': 'zoomLevel' in html_content,
        '用户提示': '提示：可以使用鼠标滚轮缩放' in html_content,
        'Mermaid优化': 'useMaxWidth: false' in html_content,
    }
    
    print('=' * 60)
    print('架构图优化 - 最终验证')
    print('=' * 60)
    print()
    
    passed = 0
    for feature, status in features.items():
        icon = '✅' if status else '❌'
        print(f'{icon} {feature}')
        if status:
            passed += 1
    
    print()
    print('=' * 60)
    print(f'结果: {passed}/{len(features)} 项通过')
    print('=' * 60)
    
    if passed == len(features):
        print('\n🎉 所有功能都已成功实现！')
        
        import os
        html_file = os.path.join(
            manager.storage_dir,
            f'pipeline_{history.pipeline_id}.html'
        )
        print(f'\n📁 生成的 HTML 文件:')
        print(f'   {html_file}')
        
        print(f'\n💡 快速体验:')
        print(f'   - 使用按钮缩放')
        print(f'   - 使用鼠标滚轮缩放')
        print(f'   - 拖拽平移图表')
        print(f'   - 双击重置视图')
        
        print(f'\n📚 相关文档:')
        print(f'   - 完整报告: /tmp/architecture_graph_optimization_report.md')
        print(f'   - 快速开始: /tmp/architecture_graph_quick_start.md')
