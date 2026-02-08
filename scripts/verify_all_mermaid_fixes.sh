#!/bin/bash

echo "=========================================="
echo "Mermaid 综合修复验证脚本"
echo "=========================================="
echo ""

HTML_FILE="/mnt/e/pyProject/prompt3.0/processing_history/pipeline_d843f227.html"
ERRORS=0

# 1. 检查 CDN 链接
echo "1. CDN 链接检查"
echo "------------------------------------------"
CDN_URL=$(grep -o 'https://[^"]*mermaid[^"]*' "$HTML_FILE" | head -1)
if echo "$CDN_URL" | grep -q "jsdelivr.net"; then
    echo "✅ CDN: jsdelivr (推荐)"
elif echo "$CDN_URL" | grep -q "unpkg.com"; then
    echo "✅ CDN: unpkg (可用)"
elif echo "$CDN_URL" | grep -q "lib.baomitu.com"; then
    echo "⚠️  CDN: lib.baomitu (可能不可用)"
    ((ERRORS++))
else
    echo "❌ 未知的 CDN"
    ((ERRORS++))
fi
echo "   URL: $CDN_URL"
echo ""

# 2. 检查 CDN 是否可访问
echo "2. CDN 可访问性检查"
echo "------------------------------------------"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$CDN_URL" 2>/dev/null)
if [ "$STATUS" = "200" ]; then
    echo "✅ CDN 可访问 (HTTP 200)"
else
    echo "❌ CDN 不可访问 (HTTP $STATUS)"
    ((ERRORS++))
fi
echo ""

# 3. 检查保留关键字
echo "3. 保留关键字检查"
echo "------------------------------------------"
if grep -q "classDef\s\+end\>" "$HTML_FILE"; then
    echo "❌ 使用了保留关键字 'end'"
    grep -n "classDef\s\+end\>" "$HTML_FILE"
    ((ERRORS++))
else
    echo "✅ 没有使用保留关键字 'end'"
fi
echo ""

# 4. 检查是否正确使用了 'endNode'
echo "4. 类名 'endNode' 检查"
echo "------------------------------------------"
if grep -q "classDef\s\+endNode" "$HTML_FILE"; then
    echo "✅ 正确使用了 'endNode' 类名"
else
    echo "⚠️  没有找到 'endNode' 类名"
fi
echo ""

# 5. 检查特殊字符
echo "5. 特殊字符检查"
echo "------------------------------------------"
if grep -E '≤|≥|≠|→' "$HTML_FILE" | grep -q "mermaid"; then
    echo "❌ Mermaid 代码中包含不支持的特殊字符"
    ((ERRORS++))
else
    echo "✅ 没有不支持的特殊字符"
fi
echo ""

# 6. 检查图表类型声明
echo "6. Mermaid 图表类型检查"
echo "------------------------------------------"
if grep -q '<div class="mermaid"' "$HTML_FILE"; then
    MERMAID_START=$(grep -n '<div class="mermaid"' "$HTML_FILE" | head -1 | cut -d: -f1)
    NEXT_LINE=$((MERMAID_START + 2))
    GRAPH_TYPE=$(sed -n "${NEXT_LINE}p" "$HTML_FILE" | grep -o "graph [A-Z]*" || echo "")
    if [ -n "$GRAPH_TYPE" ]; then
        echo "✅ 找到图表类型: $GRAPH_TYPE"
    else
        echo "⚠️  未找到图表类型声明"
    fi
else
    echo "❌ 未找到 Mermaid 容器"
    ((ERRORS++))
fi
echo ""

# 7. 检查样式定义
echo "7. 样式定义检查"
echo "------------------------------------------"
CLASSDEF_COUNT=$(grep -c "classDef" "$HTML_FILE" || echo "0")
if [ "$CLASSDEF_COUNT" -ge 3 ]; then
    echo "✅ 找到 $CLASSDEF_COUNT 个样式定义"
else
    echo "⚠️  只找到 $CLASSDEF_COUNT 个样式定义"
fi
echo ""

# 8. 检查修复文档
echo "8. 修复文档检查"
echo "------------------------------------------"
DOCS=(
    "MERMAID_404_FIX.md"
    "MERMAID_KEYWORD_FIX.md"
    "MERMAID_RENDER_FIX_COMPLETE.md"
)
for doc in "${DOCS[@]}"; do
    if [ -f "/mnt/e/pyProject/prompt3.0/$doc" ]; then
        echo "✅ $doc"
    else
        echo "❌ $doc (缺失)"
    fi
done
echo ""

echo "=========================================="
echo "验证总结"
echo "=========================================="
echo ""
if [ $ERRORS -eq 0 ]; then
    echo "✅ 所有检查通过！"
    echo ""
    echo "请浏览器打开文件查看效果："
    echo "  $HTML_FILE"
    echo ""
    echo "预期效果："
    echo "  ✅ CDN 加载成功"
    echo "  ✅ 控制台无错误"
    echo "  ✅ Mermaid 图正常显示"
    echo "  ✅ 图表样式正确"
    exit 0
else
    echo "❌ 发现 $ERRORS 个错误"
    echo ""
    echo "请检查上述错误项并修复。"
    exit 1
fi
