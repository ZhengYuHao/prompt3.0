#!/usr/bin/env python3
import os

html_file = "processing_history/pipeline_12b62a0b.html"

if os.path.exists(html_file):
    print("=" * 70)
    print("验证生成的 HTML 文件")
    print("=" * 70)
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\n✅ 文件存在: {html_file}")
    
    checks = {
        "Approach 图标题": "业务流程图（Approach 图）" in content,
        "Mermaid 代码": "graph TD" in content,
        "业务流程图标记": "业务流程图（默认生成）" in content,
        "缩放控制": "zoomIn()" in content,
        "交互提示": "此图展示业务逻辑" in content,
    }
    
    print(f"\n内容检查:")
    for name, status in checks.items():
        print(f"  {name}: {'✅' if status else '❌'}")
    
    all_passed = all(checks.values())
    
    print(f"\n" + "=" * 70)
    if all_passed:
        print("✅ 所有检查通过！")
    else:
        print("⚠️  部分检查未通过")
    print("=" * 70)
    
    print(f"\n💡 下一步:")
    print(f"   1. 在浏览器中打开: {html_file}")
    print(f"   2. 查看 '业务流程图（Approach 图）' 部分")
    print(f"   3. 体验缩放和拖拽功能")
else:
    print(f"❌ 文件不存在: {html_file}")
