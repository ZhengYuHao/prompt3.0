#!/bin/bash

echo "======================================"
echo "Mermaid CDN 验证脚本"
echo "======================================"
echo ""

# 检查生成的 HTML 文件中的 CDN 链接
echo "1. 检查生成的 HTML 文件中的 CDN 链接:"
echo "--------------------------------------"
grep -n "mermaid.min.js" /mnt/e/pyProject/prompt3.0/processing_history/pipeline_d843f227.html
echo ""

# 测试 CDN 链接是否可用
echo "2. 测试 CDN 链接是否可用:"
echo "--------------------------------------"
CDN_URL="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$CDN_URL")

if [ "$STATUS" -eq 200 ]; then
    echo "✅ CDN 链接可用 (HTTP 200)"
    echo "   URL: $CDN_URL"
else
    echo "❌ CDN 链接不可用 (HTTP $STATUS)"
    echo "   URL: $CDN_URL"
fi
echo ""

# 检查修复文档
echo "3. 检查修复文档:"
echo "--------------------------------------"
if [ -f "/mnt/e/pyProject/prompt3.0/MERMAID_404_FIX.md" ]; then
    echo "✅ 修复文档已创建: MERMAID_404_FIX.md"
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
echo "  - /mnt/e/pyProject/prompt3.0/test_mermaid_fix.html"
echo ""
echo "预期效果："
echo "  ✅ 控制台无 'Unexpected token' 错误"
echo "  ✅ 控制台无 'Mermaid.js 加载失败' 错误"
echo "  ✅ Mermaid 图正常显示"
