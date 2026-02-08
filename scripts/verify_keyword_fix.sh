#!/bin/bash

echo "======================================"
echo "Mermaid 保留关键字验证脚本"
echo "======================================"
echo ""

# 检查是否有使用保留关键字 'end'
echo "1. 检查是否使用了保留关键字 'end':"
echo "--------------------------------------"
if grep -E "classDef\s+end\s" /mnt/e/pyProject/prompt3.0/processing_history/pipeline_d843f227.html | grep -v "endNode" > /dev/null; then
    echo "❌ 错误：使用了保留关键字 'end'"
    grep -n "classDef\s+end\s" /mnt/e/pyProject/prompt3.0/processing_history/pipeline_d843f227.html
else
    echo "✅ 正确：没有使用保留关键字 'end'"
fi
echo ""

# 检查是否正确使用了 'endNode'
echo "2. 检查是否正确使用了 'endNode':"
echo "--------------------------------------"
if grep -q "classDef endNode" /mnt/e/pyProject/prompt3.0/processing_history/pipeline_d843f227.html; then
    echo "✅ 正确：使用了 'endNode' 类名"
    grep -n "classDef endNode" /mnt/e/pyProject/prompt3.0/processing_history/pipeline_d843f227.html
else
    echo "❌ 错误：没有使用 'endNode' 类名"
fi
echo ""

# 显示所有的 classDef 定义
echo "3. 显示所有的 classDef 定义:"
echo "--------------------------------------"
grep -n "classDef" /mnt/e/pyProject/prompt3.0/processing_history/pipeline_d843f227.html
echo ""

# 检查修复文档
echo "4. 检查修复文档:"
echo "--------------------------------------"
if [ -f "/mnt/e/pyProject/prompt3.0/MERMAID_KEYWORD_FIX.md" ]; then
    echo "✅ 修复文档已创建: MERMAID_KEYWORD_FIX.md"
else
    echo "❌ 修复文档不存在"
fi
echo ""

echo "======================================"
echo "验证完成"
echo "======================================"
echo ""
echo "请浏览器打开以下文件验证效果："
echo "  - /mnt/e/pyProject/prompt3.0/processing_history/pipeline_d843f227.html"
echo ""
echo "预期效果："
echo "  ✅ 控制台无 'Parse error' 错误"
echo "  ✅ 控制台无 'Expecting ... got end' 错误"
echo "  ✅ Mermaid 图正常显示"
echo "  ✅ 开始/结束节点显示为绿色"
