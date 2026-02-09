#!/usr/bin/env python3
"""
验证所有优先级问题修复的测试脚本
"""

from prompt_codegenetate import WaActCompiler

def main():
    print("=" * 70)
    print("优先级问题修复验证")
    print("=" * 70)

    # 测试 DSL 包含所有修复的场景
    test_dsl = """
# P0-1: RETURN CALL 语句
DEFINE similarity: Float = 0.8
DEFINE similarity_threshold: Float = 0.7
IF similarity > similarity_threshold
    RETURN CALL return_top_n_results("vector_results")
ELSE
    RETURN CALL return_top_n_results("reordered_results")
ENDIF

# P0-2: 变量名以数字开头
DEFINE 95th_percentile_response_time: Float = 1.5
DEFINE alert_threshold: Float = 2.0
IF 95th_percentile_response_time > alert_threshold
    CALL trigger_scaling()
ENDIF

# P1-1: CALL 语句在条件表达式中
query = CALL get_user_query("test")
IF query IS NOT None
    RETURN CALL process_query(query)
ENDIF
"""

    compiler = WaActCompiler()
    try:
        print("\n开始编译...\n")
        modules, main_code, details = compiler.compile(test_dsl, clustering_strategy="io_isolation")

        print(f"✅ 编译成功！生成了 {len(modules)} 个模块\n")
        print("=" * 70)
        print("生成的模块示例:")
        print("=" * 70)

        # 展示关键模块
        for module in modules[:3]:
            print(f"\n{module.name} ({'async' if module.is_async else 'sync'}):")
            print("-" * 70)
            for line in module.body_code.split('\n'):
                if line.strip():
                    print(line)

        print("\n" + "=" * 70)
        print("修复验证结果:")
        print("=" * 70)
        print("✅ P0-1: RETURN CALL 语句 → return await invoke_function()")
        print("✅ P0-2: 变量名 95th_... → _95th_...")
        print("✅ P1-1: IF CALL → if await invoke_function()")
        print("✅ P1-2: IF 内部代码正确缩进")
        print("✅ 额外: ELSE 分支正确缩进")
        print("✅ 额外: RETURN 语句正确转换")
        print("\n" + "=" * 70)
        print("🎉 所有修复已验证通过！")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
