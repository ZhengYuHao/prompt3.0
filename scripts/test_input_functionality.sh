#!/bin/bash
# 测试 demo_full_pipeline.py 的文件输入功能

echo "======================================"
echo "测试 demo_full_pipeline.py 文件输入功能"
echo "======================================"
echo ""

# 测试1: 默认输入模式
echo "【测试1】默认输入模式（无参数）"
echo "命令: python3 demo_full_pipeline.py"
echo "预期: 使用硬编码的默认输入"
echo ""

# 测试2: 文件存在且有内容
echo "【测试2】文件存在且有内容"
echo "命令: python3 demo_full_pipeline.py input_example.txt"
echo "预期: 从文件读取输入"
echo ""

# 测试3: 文件不存在
echo "【测试3】文件不存在"
echo "命令: python3 demo_full_pipeline.py non_existent.txt"
echo "预期: 显示错误，回退到默认输入"
echo ""

# 测试4: 文件为空
echo "【测试4】文件为空"
echo "需手动创建空文件并测试"
echo ""

echo "======================================"
echo "测试说明"
echo "======================================"
echo ""
echo "如需完整测试，请运行以下命令："
echo ""
echo "# 测试默认输入"
echo "python3 demo_full_pipeline.py | head -30"
echo ""
echo "# 测试文件输入"
echo "python3 demo_full_pipeline.py input_example.txt | head -30"
echo ""
echo "# 测试错误处理"
echo "python3 demo_full_pipeline.py non_existent.txt | head -20"
echo ""
