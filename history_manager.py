"""
处理历史存储与对比展示模块
用于持久化存储每次处理的结果，并提供清晰的对比展示
支持完整流水线追踪：Prompt 1.0 + Prompt 2.0
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from logger import info, warning, error


@dataclass
class ProcessingHistory:
    """单次处理历史记录（兼容旧格式 - Prompt 1.0）"""
    timestamp: str  # 处理时间戳
    original_text: str  # 原始输入
    processed_text: str  # 处理后文本
    mode: str  # 处理模式
    steps_log: List[str]  # 处理步骤日志
    warnings: List[str]  # 警告信息
    terminology_changes: Dict[str, str]  # 术语替换记录
    ambiguity_detected: bool  # 是否检测到歧义
    success: bool  # 是否成功处理（无歧义）
    processing_time_ms: Optional[int] = None  # 处理耗时（毫秒）


@dataclass
class Prompt20History:
    """Prompt 2.0 结构化历史记录"""
    id: str                              # 唯一标识
    timestamp: str                       # 处理时间戳
    source_prompt10_id: str              # 关联的 Prompt 1.0 ID
    
    # 输入输出
    input_text: str                      # 输入文本（来自 Prompt 1.0）
    template_text: str                   # 生成的模板
    
    # 变量信息
    variables: List[Dict] = field(default_factory=list)  # 变量列表
    variable_count: int = 0              # 变量数量
    
    # 类型统计
    type_stats: Dict[str, int] = field(default_factory=dict)  # 按类型统计
    
    # 日志
    extraction_log: List[str] = field(default_factory=list)
    
    # 性能
    processing_time_ms: int = 0


@dataclass
class PipelineHistory:
    """完整流水线历史记录"""
    pipeline_id: str  # 流水线ID
    timestamp: str  # 开始时间戳
    raw_input: str  # 用户原始输入
    
    # 阶段1结果
    prompt10_id: str = ""
    prompt10_original: str = ""
    prompt10_processed: str = ""
    prompt10_mode: str = ""
    prompt10_steps: List[Dict] = field(default_factory=list)
    prompt10_terminology_changes: Dict[str, str] = field(default_factory=dict)
    prompt10_ambiguity_detected: bool = False
    prompt10_status: str = ""
    prompt10_time_ms: int = 0
    
    # 阶段2结果
    prompt20_id: str = ""
    prompt20_template: str = ""
    prompt20_variables: List[Dict] = field(default_factory=list)
    prompt20_variable_count: int = 0
    prompt20_type_stats: Dict[str, int] = field(default_factory=dict)
    prompt20_extraction_log: List[str] = field(default_factory=list)
    prompt20_time_ms: int = 0
    
    # 阶段3结果 (DSL编译)
    prompt30_id: str = ""
    prompt30_dsl_code: str = ""
    prompt30_validation_result: Dict[str, Any] = field(default_factory=dict)
    prompt30_time_ms: int = 0
    prompt30_compile_history: Dict[str, Any] = field(default_factory=dict)  # 策略 D：编译历史
    prompt30_success: bool = True  # 策略 D：编译成功标志
    
    # 阶段4结果 (代码生成)
    prompt40_id: str = ""
    prompt40_modules: List[Dict] = field(default_factory=list)
    prompt40_module_count: int = 0
    prompt40_main_code: str = ""
    prompt40_time_ms: int = 0
    prompt40_module_bodies: Dict[str, str] = field(default_factory=dict)  # 添加模块函数体代码

    # 阶段4子步骤详情
    prompt40_step1_parsing: Dict[str, Any] = field(default_factory=dict)  # 词法解析
    prompt40_step2_dependency: Dict[str, Any] = field(default_factory=dict)  # 依赖分析
    prompt40_step3_clustering: Dict[str, Any] = field(default_factory=dict)  # 模块聚类
    prompt40_step4_generation: Dict[str, Any] = field(default_factory=dict)  # 代码生成
    prompt40_step5_orchestration: Dict[str, Any] = field(default_factory=dict)  # 主控编排

    # 整体状态
    overall_status: str = ""
    total_time_ms: int = 0
    error_message: Optional[str] = None


class HistoryManager:
    """处理历史管理器"""

    def _generate_step_details_html(self, history: PipelineHistory) -> str:
        """生成第四步编译步骤详情的 HTML"""
        html = '<div class="step-cards">'

        # Step 1: 词法解析
        if history.prompt40_step1_parsing:
            step1 = history.prompt40_step1_parsing
            total_blocks = step1.get('total_blocks', 0)
            block_types = step1.get('block_types', {})
            blocks = step1.get('blocks', [])

            block_types_str = ", ".join([f"{k}: {v}" for k, v in block_types.items()])

            blocks_preview = ""
            if blocks:
                for block in blocks[:3]:  # 只显示前3个块
                    block_id = block.get('id', 'N/A')
                    block_type = block.get('type', 'N/A')
                    block_inputs = ", ".join(block.get('inputs', []))
                    block_outputs = ", ".join(block.get('outputs', []))
                    is_async = '异步' if block.get('is_async') else '同步'
                    blocks_preview += f"""
                        <div class="change-item">
                            <strong>Block {block_id}</strong> ({block_type}, {is_async})<br>
                            &nbsp;&nbsp;输入: {block_inputs or '无'}<br>
                            &nbsp;&nbsp;输出: {block_outputs or '无'}
                        </div>
                    """
                if len(blocks) > 3:
                    blocks_preview += f'<div class="change-item" style="color:#666;">... 还有 {len(blocks) - 3} 个代码块</div>'

            html += f"""
                <div class="step-card">
                    <div class="step-header">
                        <span class="step-number">1</span>
                        <span class="step-title">词法解析</span>
                        <span class="step-duration"></span>
                    </div>
                    <div class="step-body">
                        <div class="step-section">
                            <h5>统计信息</h5>
                            <div class="change-item">代码块总数: {total_blocks}</div>
                            <div class="change-item">类型分布: {block_types_str}</div>
                        </div>
                        <div class="step-section">
                            <h5>代码块详情 (前3个)</h5>
                            {blocks_preview}
                        </div>
                    </div>
                </div>
            """

        # Step 2: 依赖分析
        if history.prompt40_step2_dependency:
            step2 = history.prompt40_step2_dependency
            has_cycles = step2.get('has_cycles', False)
            dead_code_count = step2.get('dead_code_count', 0)
            dead_code_blocks = step2.get('dead_code_blocks', [])
            node_count = step2.get('node_count', 0)
            edge_count = step2.get('edge_count', 0)
            topological_order = step2.get('topological_order', [])

            dead_code_str = ""
            if dead_code_blocks:
                dead_code_str = ", ".join(dead_code_blocks[:5])
                if len(dead_code_blocks) > 5:
                    dead_code_str += f" ... 还有 {len(dead_code_blocks) - 5} 个"

            topological_str = ""
            if topological_order:
                topological_str = " → ".join(topological_order[:8])
                if len(topological_order) > 8:
                    topological_str += f" ... 还有 {len(topological_order) - 8} 个"

            html += f"""
                <div class="step-card">
                    <div class="step-header">
                        <span class="step-number">2</span>
                        <span class="step-title">依赖分析</span>
                        <span class="step-duration"></span>
                    </div>
                    <div class="step-body">
                        <div class="step-section">
                            <h5>图结构</h5>
                            <div class="change-item">节点数量: {node_count}</div>
                            <div class="change-item">边数量: {edge_count}</div>
                            <div class="change-item">循环依赖: {'是 ❌' if has_cycles else '否 ✅'}</div>
                        </div>
                        <div class="step-section">
                            <h5>死代码检测</h5>
                            <div class="change-item">发现 {dead_code_count} 个死代码块</div>
                            {f'<div class="change-item">死代码: {dead_code_str}</div>' if dead_code_blocks else ''}
                        </div>
                        <div class="step-section">
                            <h5>拓扑排序</h5>
                            <div class="change-item" style="word-break:break-all;">{topological_str or '无'}</div>
                        </div>
                    </div>
                </div>
            """

        # Step 3: 模块聚类
        if history.prompt40_step3_clustering:
            step3 = history.prompt40_step3_clustering
            strategy = step3.get('strategy', 'hybrid')
            total_clusters = step3.get('total_clusters', 0)
            clusters = step3.get('clusters', [])

            clusters_str = ""
            if clusters:
                for cluster in clusters[:4]:  # 只显示前4个簇
                    cluster_id = cluster.get('cluster_id', 0)
                    block_count = cluster.get('block_count', 0)
                    block_ids = ", ".join(cluster.get('blocks', [])[:5])
                    if len(cluster.get('blocks', [])) > 5:
                        block_ids += " ..."
                    clusters_str += f"""
                        <div class="change-item">
                            <strong>模块 {cluster_id}</strong> ({block_count} 个代码块)<br>
                            &nbsp;&nbsp;代码块: {block_ids}
                        </div>
                    """
                if len(clusters) > 4:
                    clusters_str += f'<div class="change-item" style="color:#666;">... 还有 {len(clusters) - 4} 个模块</div>'

            html += f"""
                <div class="step-card">
                    <div class="step-header">
                        <span class="step-number">3</span>
                        <span class="step-title">模块聚类</span>
                        <span class="step-duration"></span>
                    </div>
                    <div class="step-body">
                        <div class="step-section">
                            <h5>聚类策略</h5>
                            <div class="change-item">策略类型: <strong>{strategy}</strong></div>
                            <div class="change-item">模块总数: {total_clusters}</div>
                        </div>
                        <div class="step-section">
                            <h5>聚类结果 (前4个)</h5>
                            {clusters_str}
                        </div>
                    </div>
                </div>
            """

        # Step 4: 代码生成
        if history.prompt40_step4_generation:
            step4 = history.prompt40_step4_generation
            total_modules = step4.get('total_modules', 0)
            async_modules = step4.get('async_modules', 0)
            sync_modules = step4.get('sync_modules', 0)
            modules = step4.get('modules', [])

            modules_str = ""
            if modules:
                for i, module in enumerate(modules[:4]):  # 只显示前4个模块
                    name = module.get('name', 'N/A')
                    inputs = module.get('inputs', [])
                    outputs = module.get('outputs', [])
                    is_async = module.get('is_async', False)
                    # 直接从 module 对象获取 body_code
                    body_code = module.get('body_code', '')
                    
                    inputs_str = ", ".join(inputs) if inputs else "无"
                    outputs_str = ", ".join(outputs) if outputs else "无"
                    mode_str = '<span class="badge-async">异步</span>' if is_async else '<span class="badge-sync">同步</span>'
                    
                    # 转义代码中的特殊字符
                    if body_code:
                        escaped_code = body_code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        # 显示函数体的前10行
                        code_lines = escaped_code.split('\n')
                        code_preview = "\n".join(code_lines[:10])
                        if len(code_lines) > 10:
                            code_preview += "\n        ... 还有 {} 行".format(len(code_lines) - 10)
                        code_preview_html = f'<pre style="background:#f5f5f5; padding:10px; border-radius:4px; font-size:12px; line-height:1.6; color:#333; max-height:200px; overflow-y:auto;">{code_preview}</pre>'
                    else:
                        code_preview_html = '<p style="color:#999; font-style:italic;">暂无函数体代码</p>'
                    
                    modules_str += f"""
                        <div class="change-item">
                            <strong>{i}. {name}</strong><br>
                            &nbsp;&nbsp;输入: {inputs_str or '无'}<br>
                            &nbsp;&nbsp;输出: {outputs_str or '无'}<br>
                            &nbsp;&nbsp;{mode_str}
                        </div>
                        <div style="margin-top:10px; padding:10px; background:#f9f9fa; border-left:4px solid #f093fb; border-radius:4px;">
                            <strong style="color:#f093fb; display:block; margin-bottom:5px;">函数实现:</strong>
                            {code_preview_html}
                        </div>
                    """
                if len(modules) > 4:
                    modules_str += f'<div class="change-item" style="color:#666;">... 还有 {len(modules) - 4} 个模块</div>'

            html += f"""
                <div class="step-card">
                    <div class="step-header">
                        <span class="step-number">4</span>
                        <span class="step-title">代码生成</span>
                        <span class="step-duration"></span>
                    </div>
                    <div class="step-body">
                        <div class="step-section">
                            <h5>生成统计</h5>
                            <div class="change-item">总模块数: {total_modules}</div>
                            <div class="change-item">异步模块: {async_modules}</div>
                            <div class="change-item">同步模块: {sync_modules}</div>
                        </div>
                        <div class="step-section">
                            <h5>模块详情 (前4个)</h5>
                            {modules_str}
                        </div>
                    </div>
                </div>
            """

        # Step 5: 主控编排
        if history.prompt40_step5_orchestration:
            step5 = history.prompt40_step5_orchestration
            main_inputs = step5.get('main_inputs', [])
            input_count = step5.get('input_count', 0)
            main_code = step5.get('main_code', '')

            inputs_str = ", ".join(main_inputs) if main_inputs else "无"

            main_code_preview = ""
            if main_code:
                code_lines = main_code.split('\n')
                for line in code_lines[:5]:  # 只显示前5行
                    escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    main_code_preview += f'<div class="note-item">{escaped_line}</div>'
                if len(code_lines) > 5:
                    main_code_preview += f'<div class="note-item" style="color:#666;">... 还有 {len(code_lines) - 5} 行</div>'

            html += f"""
                <div class="step-card">
                    <div class="step-header">
                        <span class="step-number">5</span>
                        <span class="step-title">主控编排</span>
                        <span class="step-duration"></span>
                    </div>
                    <div class="step-body">
                        <div class="step-section">
                            <h5>外部输入参数</h5>
                            <div class="change-item">参数数量: {input_count}</div>
                            <div class="change-item" style="word-break:break-all;">{inputs_str}</div>
                        </div>
                        <div class="step-section">
                            <h5>主工作流代码 (预览)</h5>
                            {main_code_preview}
                        </div>
                    </div>
                </div>
            """

        html += '</div>'
        return html
    
    def __init__(self, storage_dir: str = "processing_history"):
        """
        初始化历史管理器
        
        Args:
            storage_dir: 存储目录路径
        """
        self.storage_dir = storage_dir
        self.history_file = os.path.join(storage_dir, "history.json")
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
            info(f"创建历史记录存储目录: {self.storage_dir}")
    
    def save_history(self, history: ProcessingHistory) -> str:
        """
        保存处理历史
        
        Args:
            history: 处理历史记录
            
        Returns:
            记录ID（时间戳）
        """
        # 加载现有历史
        all_history = self.load_all_history()
        
        # 添加新记录
        all_history[history.timestamp] = asdict(history)
        
        # 保存到文件
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(all_history, f, ensure_ascii=False, indent=2)
            info(f"历史记录已保存: {history.timestamp}")
            return history.timestamp
        except Exception as e:
            error(f"保存历史记录失败: {e}")
            raise
    
    def load_all_history(self) -> Dict[str, Dict]:
        """加载所有历史记录"""
        if not os.path.exists(self.history_file):
            return {}
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            warning(f"加载历史记录失败: {e}")
            return {}
    
    def get_history(self, timestamp: str) -> Optional[ProcessingHistory]:
        """获取指定时间戳的历史记录"""
        all_history = self.load_all_history()
        record = all_history.get(timestamp)
        if record:
            return ProcessingHistory(**record)
        return None
    
    def get_recent_history(self, limit: int = 10) -> List[ProcessingHistory]:
        """获取最近的处理历史"""
        all_history = self.load_all_history()
        # 按时间戳排序（最新的在前）
        sorted_timestamps = sorted(all_history.keys(), reverse=True)
        recent_timestamps = sorted_timestamps[:limit]
        
        return [
            ProcessingHistory(**all_history[ts])
            for ts in recent_timestamps
        ]
    
    def format_comparison(self, history: ProcessingHistory) -> str:
        """
        格式化对比展示
        
        Args:
            history: 处理历史记录
            
        Returns:
            格式化的对比文本
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"处理时间: {history.timestamp}")
        lines.append(f"处理模式: {history.mode}")
        lines.append(f"处理状态: {'✅ 成功' if history.success else '⚠️ 检测到歧义'}")
        lines.append("=" * 80)
        
        # 原始文本 vs 处理后文本对比
        lines.append("\n【文本对比】")
        lines.append("-" * 80)
        lines.append("原始文本:")
        lines.append(f"  {history.original_text}")
        lines.append("\n处理后文本:")
        lines.append(f"  {history.processed_text}")
        lines.append("-" * 80)
        
        # 术语替换
        if history.terminology_changes:
            lines.append("\n【术语替换】")
            lines.append("-" * 80)
            for old, new in history.terminology_changes.items():
                lines.append(f"  {old} → {new}")
            lines.append("-" * 80)
        
        # 处理步骤
        if history.steps_log:
            lines.append("\n【处理步骤】")
            lines.append("-" * 80)
            for i, step in enumerate(history.steps_log, 1):
                lines.append(f"  {i}. {step}")
            lines.append("-" * 80)
        
        # 警告信息
        if history.warnings:
            lines.append("\n【警告信息】")
            lines.append("-" * 80)
            for warning_msg in history.warnings:
                lines.append(f"  ⚠️  {warning_msg}")
            lines.append("-" * 80)
        
        # 歧义检测
        if history.ambiguity_detected:
            lines.append("\n【歧义检测】")
            lines.append("-" * 80)
            lines.append("  ⚠️  检测到歧义，已拦截")
            lines.append("-" * 80)
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)
    
    def print_comparison(self, history: ProcessingHistory):
        """打印对比展示"""
        comparison_text = self.format_comparison(history)
        info("\n" + comparison_text)
    
    def export_comparison_html(self, history: ProcessingHistory, output_file: Optional[str] = None) -> str:
        """
        导出为HTML格式的对比展示
        
        Args:
            history: 处理历史记录
            output_file: 输出文件路径（可选）
            
        Returns:
            HTML内容
        """
        if output_file is None:
            output_file = os.path.join(
                self.storage_dir,
                f"comparison_{history.timestamp.replace(':', '-').replace(' ', '_')}.html"
            )
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>处理对比 - {history.timestamp}</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .meta {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .meta-item {{
            margin: 5px 0;
        }}
        .status-success {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .status-warning {{
            color: #FF9800;
            font-weight: bold;
        }}
        .comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }}
        .text-box {{
            border: 2px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            background: #fafafa;
        }}
        .text-box.original {{
            border-color: #ff6b6b;
        }}
        .text-box.processed {{
            border-color: #4CAF50;
        }}
        .text-box h3 {{
            margin-top: 0;
            color: #333;
        }}
        .text-content {{
            white-space: pre-wrap;
            word-wrap: break-word;
            line-height: 1.6;
        }}
        .changes {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .changes h3 {{
            margin-top: 0;
            color: #856404;
        }}
        .change-item {{
            margin: 8px 0;
            padding: 8px;
            background: white;
            border-radius: 3px;
        }}
        .old {{
            color: #d32f2f;
            text-decoration: line-through;
        }}
        .new {{
            color: #388e3c;
            font-weight: bold;
        }}
        .steps {{
            background: #e3f2fd;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .steps h3 {{
            margin-top: 0;
            color: #1565c0;
        }}
        .step-item {{
            margin: 8px 0;
            padding: 8px;
            background: white;
            border-radius: 3px;
        }}
        .warnings {{
            background: #fff3e0;
            border-left: 4px solid #ff9800;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .warnings h3 {{
            margin-top: 0;
            color: #e65100;
        }}
        .warning-item {{
            margin: 8px 0;
            padding: 8px;
            background: white;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📝 处理对比报告</h1>
        
        <div class="meta">
            <div class="meta-item"><strong>处理时间:</strong> {history.timestamp}</div>
            <div class="meta-item"><strong>处理模式:</strong> {history.mode}</div>
            <div class="meta-item"><strong>处理状态:</strong> 
                <span class="{'status-success' if history.success else 'status-warning'}">
                    {'✅ 成功' if history.success else '⚠️ 检测到歧义'}
                </span>
            </div>
        </div>
        
        <div class="comparison">
            <div class="text-box original">
                <h3>📄 原始文本</h3>
                <div class="text-content">{history.original_text}</div>
            </div>
            <div class="text-box processed">
                <h3>✨ 处理后文本</h3>
                <div class="text-content">{history.processed_text}</div>
            </div>
        </div>
"""
        
        # 术语替换
        if history.terminology_changes:
            html += """
        <div class="changes">
            <h3>🔄 术语替换</h3>
"""
            for old, new in history.terminology_changes.items():
                html += f"""
            <div class="change-item">
                <span class="old">{old}</span> → <span class="new">{new}</span>
            </div>
"""
            html += """
        </div>
"""
        
        # 处理步骤
        if history.steps_log:
            html += """
        <div class="steps">
            <h3>⚙️ 处理步骤</h3>
"""
            for i, step in enumerate(history.steps_log, 1):
                html += f"""
            <div class="step-item">{i}. {step}</div>
"""
            html += """
        </div>
"""
        
        # 警告信息
        if history.warnings:
            html += """
        <div class="warnings">
            <h3>⚠️ 警告信息</h3>
"""
            for warning_msg in history.warnings:
                html += f"""
            <div class="warning-item">{warning_msg}</div>
"""
            html += """
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        
        # 保存HTML文件
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)
            info(f"HTML对比报告已保存: {output_file}")
        except Exception as e:
            error(f"保存HTML报告失败: {e}")
        
        return html
    
    # ========================================================================
    # Prompt 2.0 历史记录管理
    # ========================================================================
    
    def save_prompt20_history(self, history: Prompt20History) -> str:
        """
        保存 Prompt 2.0 处理历史
        
        Args:
            history: Prompt 2.0 历史记录
            
        Returns:
            记录ID
        """
        prompt20_file = os.path.join(self.storage_dir, "prompt20_history.json")
        
        # 加载现有历史
        all_history = {}
        if os.path.exists(prompt20_file):
            try:
                with open(prompt20_file, 'r', encoding='utf-8') as f:
                    all_history = json.load(f)
            except Exception:
                pass
        
        # 添加新记录
        all_history[history.id] = asdict(history)
        
        # 保存到文件
        try:
            with open(prompt20_file, 'w', encoding='utf-8') as f:
                json.dump(all_history, f, ensure_ascii=False, indent=2)
            info(f"Prompt 2.0 历史记录已保存: {history.id}")
            return history.id
        except Exception as e:
            error(f"保存 Prompt 2.0 历史记录失败: {e}")
            raise
    
    def load_prompt20_history(self, record_id: str) -> Optional[Prompt20History]:
        """加载指定的 Prompt 2.0 历史记录"""
        prompt20_file = os.path.join(self.storage_dir, "prompt20_history.json")
        
        if not os.path.exists(prompt20_file):
            return None
        
        try:
            with open(prompt20_file, 'r', encoding='utf-8') as f:
                all_history = json.load(f)
            record = all_history.get(record_id)
            if record:
                return Prompt20History(**record)
        except Exception as e:
            warning(f"加载 Prompt 2.0 历史记录失败: {e}")
        
        return None
    
    def get_recent_prompt20_history(self, limit: int = 10) -> List[Prompt20History]:
        """获取最近的 Prompt 2.0 处理历史"""
        prompt20_file = os.path.join(self.storage_dir, "prompt20_history.json")
        
        if not os.path.exists(prompt20_file):
            return []
        
        try:
            with open(prompt20_file, 'r', encoding='utf-8') as f:
                all_history = json.load(f)
            
            # 按时间戳排序
            sorted_ids = sorted(
                all_history.keys(),
                key=lambda x: all_history[x].get('timestamp', ''),
                reverse=True
            )
            
            return [
                Prompt20History(**all_history[id])
                for id in sorted_ids[:limit]
            ]
        except Exception as e:
            warning(f"加载 Prompt 2.0 历史记录失败: {e}")
            return []
    
    # ========================================================================
    # 完整流水线历史记录管理
    # ========================================================================
    
    def save_pipeline_history(self, history: PipelineHistory) -> str:
        """
        保存完整流水线历史记录
        
        Args:
            history: 流水线历史记录
            
        Returns:
            流水线ID
        """
        pipeline_file = os.path.join(self.storage_dir, "pipeline_history.json")
        
        # 加载现有历史
        all_history = {}
        if os.path.exists(pipeline_file):
            try:
                with open(pipeline_file, 'r', encoding='utf-8') as f:
                    all_history = json.load(f)
            except Exception:
                pass
        
        # 添加新记录
        all_history[history.pipeline_id] = asdict(history)
        
        # 保存到文件
        try:
            with open(pipeline_file, 'w', encoding='utf-8') as f:
                json.dump(all_history, f, ensure_ascii=False, indent=2)
            info(f"流水线历史记录已保存: {history.pipeline_id}")
            return history.pipeline_id
        except Exception as e:
            error(f"保存流水线历史记录失败: {e}")
            raise
    
    def load_pipeline_history(self, pipeline_id: str) -> Optional[PipelineHistory]:
        """加载指定的流水线历史记录"""
        pipeline_file = os.path.join(self.storage_dir, "pipeline_history.json")
        
        if not os.path.exists(pipeline_file):
            return None
        
        try:
            with open(pipeline_file, 'r', encoding='utf-8') as f:
                all_history = json.load(f)
            record = all_history.get(pipeline_id)
            if record:
                return PipelineHistory(**record)
        except Exception as e:
            warning(f"加载流水线历史记录失败: {e}")
        
        return None
    
    def get_recent_pipeline_history(self, limit: int = 10) -> List[PipelineHistory]:
        """获取最近的流水线历史"""
        pipeline_file = os.path.join(self.storage_dir, "pipeline_history.json")
        
        if not os.path.exists(pipeline_file):
            return []
        
        try:
            with open(pipeline_file, 'r', encoding='utf-8') as f:
                all_history = json.load(f)
            
            sorted_ids = sorted(
                all_history.keys(),
                key=lambda x: all_history[x].get('timestamp', ''),
                reverse=True
            )
            
            return [
                PipelineHistory(**all_history[id])
                for id in sorted_ids[:limit]
            ]
        except Exception as e:
            warning(f"加载流水线历史记录失败: {e}")
            return []
    
    # ========================================================================
    # 完整流水线对比展示
    # ========================================================================
    
    def format_pipeline_comparison(self, history: PipelineHistory) -> str:
        """
        格式化完整流水线对比展示
        
        Args:
            history: 流水线历史记录
            
        Returns:
            格式化的对比文本
        """
        lines = []
        
        # 标题
        lines.append("█" * 80)
        lines.append("█" + " " * 28 + "完整流水线处理报告" + " " * 29 + "█")
        lines.append("█" * 80)
        lines.append("")
        lines.append(f"流水线 ID: {history.pipeline_id}")
        lines.append(f"处理时间: {history.timestamp}")
        lines.append(f"整体状态: {history.overall_status}")
        lines.append(f"总耗时: {history.total_time_ms}ms")
        lines.append("")
        
        # ===== 阶段 1: Prompt 1.0 =====
        lines.append("=" * 80)
        lines.append("【阶段 1: Prompt 1.0 预处理】")
        lines.append("=" * 80)
        lines.append("")
        lines.append("┌─ 原始输入 ─────────────────────────────────────────────────────────────────┐")
        for line in history.raw_input.split('\n'):
            lines.append(f"│ {line}")
        lines.append("└────────────────────────────────────────────────────────────────────────────┘")
        lines.append("")
        lines.append("┌─ 标准化输出 (Prompt 1.0) ───────────────────────────────────────────────────┐")
        for line in history.prompt10_processed.split('\n'):
            lines.append(f"│ {line}")
        lines.append("└────────────────────────────────────────────────────────────────────────────┘")
        lines.append("")
        
        # 处理步骤详情
        if history.prompt10_steps:
            lines.append("【处理步骤详情】")
            for i, step in enumerate(history.prompt10_steps, 1):
                lines.append(f"\n  步骤 {i}: {step.get('step_name', 'N/A')}")
                lines.append(f"    耗时: {step.get('duration_ms', 0)}ms")
                changes = step.get('changes', {})
                if changes:
                    lines.append(f"    变更: {len(changes)} 处")
                    for old, new in list(changes.items())[:3]:  # 只显示前3个
                        new_str = f"'{new}'" if new else "(删除)"
                        lines.append(f"      • '{old}' → {new_str}")
                    if len(changes) > 3:
                        lines.append(f"      ... 还有 {len(changes) - 3} 处变更")
            lines.append("")
        
        # 术语替换
        if history.prompt10_terminology_changes:
            lines.append("【术语替换】")
            for old, new in history.prompt10_terminology_changes.items():
                if new:
                    lines.append(f"  • '{old}' → '{new}'")
                else:
                    lines.append(f"  • '{old}' → (删除)")
            lines.append("")
        
        lines.append(f"处理耗时: {history.prompt10_time_ms}ms | 状态: {history.prompt10_status}")
        lines.append("")
        
        # ===== 阶段 2: Prompt 2.0 =====
        lines.append("=" * 80)
        lines.append("【阶段 2: Prompt 2.0 结构化】")
        lines.append("=" * 80)
        lines.append("")
        lines.append("┌─ 参数化模板 (Prompt 2.0) ───────────────────────────────────────────────────┐")
        for line in history.prompt20_template.split('\n'):
            lines.append(f"│ {line}")
        lines.append("└────────────────────────────────────────────────────────────────────────────┘")
        lines.append("")
        
        # 变量注册表
        lines.append("【变量注册表】")
        lines.append(f"共 {history.prompt20_variable_count} 个变量")
        if history.prompt20_type_stats:
            stats_str = ", ".join([f"{k}: {v}" for k, v in history.prompt20_type_stats.items()])
            lines.append(f"类型分布: {stats_str}")
        lines.append("")
        
        for var in history.prompt20_variables[:10]:  # 只显示前10个
            lines.append(f"  • {var.get('variable', 'N/A')}: {var.get('value', 'N/A')} ({var.get('type', 'N/A')})")
            lines.append(f"    原文: \"{var.get('original_text', 'N/A')}\"")
        
        if len(history.prompt20_variables) > 10:
            lines.append(f"  ... 还有 {len(history.prompt20_variables) - 10} 个变量")
        
        lines.append("")
        lines.append(f"处理耗时: {history.prompt20_time_ms}ms")
        lines.append("")

        # ===== 阶段 3: Prompt 3.0 DSL 编译 =====
        lines.append("=" * 80)
        lines.append("【阶段 3: Prompt 3.0 DSL 编译】")
        lines.append("=" * 80)
        lines.append("")
        
        if history.prompt30_dsl_code:
            lines.append("┌─ 生成的 DSL 代码 (Prompt 3.0) ───────────────────────────────────────────────┐")
            dsl_lines = history.prompt30_dsl_code.split('\n')
            for line in dsl_lines[:20]:  # 最多显示20行
                lines.append(f"│ {line}")
            if len(dsl_lines) > 20:
                lines.append(f"│ ... 还有 {len(dsl_lines) - 20} 行")
            lines.append("└────────────────────────────────────────────────────────────────────────────┘")
            lines.append("")
            
            # 验证结果
            if history.prompt30_validation_result:
                valid = history.prompt30_validation_result.get('is_valid', False)
                errors = history.prompt30_validation_result.get('errors', [])
                warnings = history.prompt30_validation_result.get('warnings', [])
                defined_vars = history.prompt30_validation_result.get('defined_variables', {})
                function_calls = history.prompt30_validation_result.get('function_calls', [])
                
                lines.append(f"验证状态: {'✅ 通过' if valid else '❌ 失败'}")
                lines.append(f"定义变量数: {len(defined_vars)} 个")
                lines.append(f"函数调用数: {len(function_calls)} 个")
                if errors:
                    lines.append(f"错误数量: {len(errors)} 个")
                if warnings:
                    lines.append(f"警告数量: {len(warnings)} 个")
        else:
            lines.append("  未进行 DSL 编译")
        
        lines.append("")
        lines.append(f"处理耗时: {history.prompt30_time_ms}ms")
        lines.append("")

        # ===== 阶段 4: Prompt 4.0 代码生成 =====
        lines.append("=" * 80)
        lines.append("【阶段 4: Prompt 4.0 代码生成】")
        lines.append("=" * 80)
        lines.append("")
        
        if history.prompt40_modules:
            lines.append(f"【工作流模块】共 {history.prompt40_module_count} 个模块")
            lines.append("")
            for i, module in enumerate(history.prompt40_modules, 1):
                module_name = module.get('name', 'N/A')
                inputs = module.get('inputs', [])
                outputs = module.get('outputs', [])
                is_async = module.get('is_async', False)
                lines.append(f"  模块 {i}: {module_name}")
                lines.append(f"    输入变量: {', '.join(inputs) if inputs else '无'}")
                lines.append(f"    输出变量: {', '.join(outputs) if outputs else '无'}")
                lines.append(f"    执行模式: {'异步' if is_async else '同步'}")
                lines.append("")
            
            lines.append("┌─ 主工作流代码 (Prompt 4.0) ───────────────────────────────────────────────┐")
            code_lines = history.prompt40_main_code.split('\n')
            for line in code_lines[:30]:  # 最多显示30行
                lines.append(f"│ {line}")
            if len(code_lines) > 30:
                lines.append(f"│ ... 还有 {len(code_lines) - 30} 行")
            lines.append("└────────────────────────────────────────────────────────────────────────────┘")
        else:
            lines.append("  未进行代码生成")
        
        lines.append("")
        lines.append(f"处理耗时: {history.prompt40_time_ms}ms")
        lines.append("")

        # ===== 总结 =====
        lines.append("=" * 80)
        lines.append("【处理总结】")
        lines.append("=" * 80)
        lines.append(f"  原始输入长度: {len(history.raw_input)} 字符")
        lines.append(f"  标准化后长度: {len(history.prompt10_processed)} 字符")
        lines.append(f"  识别变量数量: {history.prompt20_variable_count} 个")
        lines.append(f"  DSL 编译状态: {'✅ 成功' if history.prompt30_dsl_code else '❌ 未执行'}")
        lines.append(f"  代码生成状态: {'✅ 成功' if history.prompt40_modules else '❌ 未执行'}")
        lines.append(f"  总处理耗时: {history.total_time_ms}ms")
        lines.append("")
        lines.append(f"  阶段 1 (预处理): {history.prompt10_time_ms}ms ({history.prompt10_time_ms / history.total_time_ms * 100:.1f}%)")
        lines.append(f"  阶段 2 (结构化): {history.prompt20_time_ms}ms ({history.prompt20_time_ms / history.total_time_ms * 100:.1f}%)")
        lines.append(f"  阶段 3 (DSL编译): {history.prompt30_time_ms}ms ({history.prompt30_time_ms / history.total_time_ms * 100:.1f}%)")
        lines.append(f"  阶段 4 (代码生成): {history.prompt40_time_ms}ms ({history.prompt40_time_ms / history.total_time_ms * 100:.1f}%)")
        lines.append("█" * 80)
        
        return "\n".join(lines)
    
    def print_pipeline_comparison(self, history: PipelineHistory):
        """打印流水线对比展示"""
        comparison_text = self.format_pipeline_comparison(history)
        info("\n" + comparison_text)
    
    def export_pipeline_html(self, history: PipelineHistory, output_file: Optional[str] = None) -> str:
        """
        导出完整流水线为HTML格式
        
        Args:
            history: 流水线历史记录
            output_file: 输出文件路径
            
        Returns:
            HTML内容
        """
        if output_file is None:
            output_file = os.path.join(
                self.storage_dir,
                f"pipeline_{history.pipeline_id}.html"
            )
        
        # 变量表格HTML
        variables_html = ""
        for var in history.prompt20_variables:
            variables_html += f"""
                <tr>
                    <td><code>{var.get('variable', 'N/A')}</code></td>
                    <td>"{var.get('original_text', 'N/A')}"</td>
                    <td><strong>{var.get('value', 'N/A')}</strong></td>
                    <td><span class="type-badge">{var.get('type', 'N/A')}</span></td>
                </tr>
"""
        
        # 处理步骤HTML
        steps_html = ""
        for i, step in enumerate(history.prompt10_steps, 1):
            step_name = step.get('step_name', f'Step {i}')
            duration = step.get('duration_ms', 0)
            changes = step.get('changes', {})
            notes = step.get('notes', [])
            
            changes_html = ""
            if changes:
                for old, new in list(changes.items())[:3]:
                    new_str = f"'{new}'" if new else "(删除)"
                    changes_html += f'<div class="change-item"><span class="old">{old}</span> → <span class="new">{new_str}</span></div>'
                if len(changes) > 3:
                    changes_html += f'<div class="change-item">... 还有 {len(changes) - 3} 处变更</div>'
            else:
                changes_html = '<div class="change-item">无变更</div>'
            
            notes_html = "".join([f'<div class="note-item">• {note}</div>' for note in notes])
            
            steps_html += f"""
                <div class="step-card">
                    <div class="step-header">
                        <span class="step-number">{i}</span>
                        <span class="step-title">{step_name}</span>
                        <span class="step-duration">{duration}ms</span>
                    </div>
                    <div class="step-body">
                        <div class="step-section">
                            <h5>变更记录</h5>
                            {changes_html}
                        </div>
                        {f'<div class="step-section"><h5>备注</h5>{notes_html}</div>' if notes else ''}
                    </div>
                </div>
"""
        
        # 术语替换HTML
        terminology_html = ""
        for old, new in history.prompt10_terminology_changes.items():
            if new:
                terminology_html += f'<div class="term-item"><span class="old">{old}</span> → <span class="new">{new}</span></div>'
            else:
                terminology_html += f'<div class="term-item"><span class="old">{old}</span> → <span class="deleted">(删除)</span></div>'
        
        # DSL 代码 HTML
        dsl_code_html = ""
        if history.prompt30_dsl_code:
            escaped_dsl = history.prompt30_dsl_code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            dsl_code_html = f"""
                <div class="text-box dsl-code">
                    <pre>{escaped_dsl}</pre>
                </div>
            """
        else:
            dsl_code_html = '<p style="color:#999; font-style:italic;">未生成 DSL 代码</p>'
        
        # 验证结果 HTML
        validation_html = ""
        if history.prompt30_validation_result:
            valid = history.prompt30_validation_result.get('is_valid', False)
            errors = history.prompt30_validation_result.get('errors', [])
            warnings = history.prompt30_validation_result.get('warnings', [])
            defined_vars = history.prompt30_validation_result.get('defined_variables', {})
            function_calls = history.prompt30_validation_result.get('function_calls', [])
            
            validation_html = f"""
                <div class="validation-result">
                    <p><strong>验证状态:</strong> {'✅ 通过' if valid else '❌ 失败'}</p>
                    <p><strong>定义变量:</strong> {len(defined_vars)} 个</p>
                    <p><strong>函数调用:</strong> {len(function_calls)} 个</p>
                    <p><strong>错误数量:</strong> {len(errors)} 个</p>
                    <p><strong>警告数量:</strong> {len(warnings)} 个</p>
                </div>
            """
        else:
            validation_html = '<p style="color:#999; font-style:italic;">无验证结果</p>'
        
        # 模块列表HTML
        modules_html = ""
        if history.prompt40_modules:
            for i, module in enumerate(history.prompt40_modules, 1):
                module_name = module.get('name', 'N/A')
                inputs = module.get('inputs', [])
                outputs = module.get('outputs', [])
                is_async = module.get('is_async', False)
                
                inputs_str = ", ".join(inputs) if inputs else "无"
                outputs_str = ", ".join(outputs) if outputs else "无"
                mode_str = '<span class="badge-async">异步</span>' if is_async else '<span class="badge-sync">同步</span>'
                
                modules_html += f"""
                    <div class="module-card">
                        <div class="module-header">
                            <span class="module-number">{i}</span>
                            <span class="module-name">{module_name}</span>
                            {mode_str}
                        </div>
                        <div class="module-body">
                            <div><strong>输入:</strong> {inputs_str}</div>
                            <div><strong>输出:</strong> {outputs_str}</div>
                        </div>
                    </div>
"""
        else:
            modules_html = '<p style="color:#999; font-style:italic;">未生成工作流模块</p>'
        
        # 主代码 HTML
        main_code_html = ""
        if history.prompt40_main_code:
            escaped_code = history.prompt40_main_code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            main_code_html = f"""
                <div class="text-box main-code">
                    <pre>{escaped_code}</pre>
                </div>
            """
        else:
            main_code_html = '<p style="color:#999; font-style:italic;">未生成主代码</p>'

        # 第四步编译步骤详情 HTML
        step_details_html = self._generate_step_details_html(history)
        
        # 生成业务流程图（Approach 图）的 Mermaid 代码
        info("正在生成业务流程图...")
        approach_diagram_mermaid = self._generate_approach_diagram_mermaid(history)
        info(f"业务流程图生成完成 ({len(approach_diagram_mermaid)} 字符)")

        # 时间百分比计算
        time1_pct = history.prompt10_time_ms / history.total_time_ms * 100 if history.total_time_ms > 0 else 0
        time2_pct = history.prompt20_time_ms / history.total_time_ms * 100 if history.total_time_ms > 0 else 0
        time3_pct = history.prompt30_time_ms / history.total_time_ms * 100 if history.total_time_ms > 0 else 0
        time4_pct = history.prompt40_time_ms / history.total_time_ms * 100 if history.total_time_ms > 0 else 0
        
        # 定义变量和函数调用数量
        defined_vars_count = len(history.prompt30_validation_result.get('defined_variables', {})) if history.prompt30_validation_result else 0
        function_calls_count = len(history.prompt30_validation_result.get('function_calls', [])) if history.prompt30_validation_result else 0
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>流水线报告 - {history.pipeline_id}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 10px;
        }}
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }}
        .meta-bar {{
            display: flex;
            justify-content: space-around;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .meta-item {{
            text-align: center;
        }}
        .meta-item .label {{
            color: #666;
            font-size: 12px;
        }}
        .meta-item .value {{
            font-size: 18px;
            font-weight: bold;
            color: #333;
        }}
        .stage {{
            margin: 30px 0;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            overflow: hidden;
        }}
        .stage-header {{
            padding: 15px 20px;
            font-weight: bold;
            color: white;
        }}
        .stage-1 .stage-header {{ background: linear-gradient(90deg, #667eea, #764ba2); }}
        .stage-2 .stage-header {{ background: linear-gradient(90deg, #11998e, #38ef7d); }}
        .stage-3 .stage-header {{ background: linear-gradient(90deg, #ff7e5f, #feb47b); }}
        .stage-4 .stage-header {{ background: linear-gradient(90deg, #f093fb, #f5576c); }}
        .stage-content {{
            padding: 20px;
        }}
        .text-box {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 15px 0;
            border-radius: 0 8px 8px 0;
            white-space: pre-wrap;
            font-family: 'Consolas', monospace;
            line-height: 1.8;
            max-height: 400px;
            overflow-y: auto;
        }}
        .text-box.template {{ border-left-color: #11998e; }}
        .text-box.dsl-code {{ border-left-color: #ff7e5f; }}
        .text-box.main-code {{ border-left-color: #f093fb; max-height: 500px; }}
        .term-changes {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 15px 0;
        }}
        .term-item {{
            background: #fff3cd;
            padding: 8px 12px;
            border-radius: 20px;
            font-size: 14px;
        }}
        .old {{ color: #d32f2f; text-decoration: line-through; }}
        .new {{ color: #388e3c; font-weight: bold; }}
        .deleted {{ color: #999; font-style: italic; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        th {{
            background: #f8f9fa;
            font-weight: bold;
        }}
        .type-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        .type-badge {{ background: #e3f2fd; color: #1976d2; }}
        code {{
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', monospace;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-card .number {{
            font-size: 32px;
            font-weight: bold;
        }}
        .stat-card .label {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .step-cards {{
            display: grid;
            gap: 15px;
        }}
        .step-card {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }}
        .step-header {{
            background: #f8f9fa;
            padding: 12px 15px;
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        .step-number {{
            background: #667eea;
            color: white;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14px;
        }}
        .step-title {{
            flex: 1;
            font-weight: bold;
        }}
        .step-duration {{
            color: #666;
            font-size: 14px;
        }}
        .step-body {{
            padding: 15px;
        }}
        .step-section {{
            margin-bottom: 15px;
        }}
        .step-section:last-child {{ margin-bottom: 0; }}
        .step-section h5 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 14px;
            font-weight: bold;
        }}
        .change-item {{
            padding: 5px 0;
            font-size: 14px;
        }}
        .note-item {{
            padding: 3px 0;
            color: #666;
            font-size: 14px;
        }}
        .module-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
        }}
        .module-card {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }}
        .module-header {{
            background: linear-gradient(90deg, #f093fb, #f5576c);
            color: white;
            padding: 12px 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .module-number {{
            background: rgba(255,255,255,0.3);
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 12px;
        }}
        .module-name {{
            flex: 1;
            font-weight: bold;
        }}
        .badge-async, .badge-sync {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
        }}
        .badge-async {{ background: #4CAF50; }}
        .badge-sync {{ background: #2196F3; }}
        .module-body {{
            padding: 15px;
            font-size: 14px;
        }}
        .module-body div {{
            margin: 5px 0;
        }}
        .time-breakdown {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }}
        .time-item {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #e0e0e0;
        }}
        .time-item:last-child {{ border-bottom: none; }}
        .time-bar {{
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            margin-top: 5px;
            overflow: hidden;
        }}
        .time-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s ease;
        }}
        .time-fill.stage-2 {{ background: linear-gradient(90deg, #11998e, #38ef7d); }}
        .time-fill.stage-3 {{ background: linear-gradient(90deg, #ff7e5f, #feb47b); }}
        .time-fill.stage-4 {{ background: linear-gradient(90deg, #f093fb, #f5576c); }}

        /* 调用关系图样式 - 优化显示空间 */
        .call-graph-container {{
            background: #f8f9fa;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            padding: 20px;
            margin: 30px 0;
            overflow: hidden;
            position: relative;
            min-height: 600px;
        }}
        .call-graph-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .call-graph-controls {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        .control-btn {{
            padding: 8px 16px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }}
        .control-btn:hover {{
            background: #0056b3;
        }}
        .control-btn.reset {{
            background: #6c757d;
        }}
        .control-btn.reset:hover {{
            background: #545b62;
        }}
        .zoom-level {{
            background: #e9ecef;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            min-width: 80px;
            text-align: center;
        }}
        .mermaid-wrapper {{
            width: 100%;
            height: 100%;
            overflow: auto;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: grab;
        }}
        .mermaid-wrapper:active {{
            cursor: grabbing;
        }}
        .mermaid {{
            display: block;
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transition: transform 0.1s ease;
            transform-origin: center center;
            min-width: 1000px;
        }}
        .zoom-hint {{
            text-align: center;
            color: #6c757d;
            font-size: 12px;
            margin-top: 10px;
            font-style: italic;
        }}
    </style>
    <!-- 引入 Mermaid.js 用于渲染架构图 -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
</head>
<body>
    <div class="container">
        <h1>📊 完整流水线处理报告</h1>
        <p class="subtitle">Prompt 1.0 预处理 → Prompt 2.0 结构化 → Prompt 3.0 DSL 编译 → Prompt 4.0 代码生成</p>
        
        <div class="meta-bar">
            <div class="meta-item">
                <div class="label">流水线 ID</div>
                <div class="value">{history.pipeline_id}</div>
            </div>
            <div class="meta-item">
                <div class="label">处理时间</div>
                <div class="value">{history.timestamp}</div>
            </div>
            <div class="meta-item">
                <div class="label">状态</div>
                <div class="value">{'✅ ' + history.overall_status if history.overall_status == 'success' else '⚠️ ' + history.overall_status}</div>
            </div>
            <div class="meta-item">
                <div class="label">总耗时</div>
                <div class="value">{history.total_time_ms}ms</div>
            </div>
        </div>
        
        <!-- 阶段 1 -->
        <div class="stage stage-1">
            <div class="stage-header">📝 阶段 1: Prompt 1.0 预处理 (耗时 {history.prompt10_time_ms}ms)</div>
            <div class="stage-content">
                <h4>原始输入</h4>
                <div class="text-box">{history.raw_input}</div>
                
                <h4>标准化输出</h4>
                <div class="text-box">{history.prompt10_processed}</div>
                
                <h4>处理步骤详情 ({len(history.prompt10_steps)} 个步骤)</h4>
                <div class="step-cards">
                    {steps_html if steps_html else '<p style="color:#999">无处理步骤记录</p>'}
                </div>
                
                <h4>术语替换 ({len(history.prompt10_terminology_changes)} 处)</h4>
                <div class="term-changes">{terminology_html if terminology_html else '<span style="color:#999">无术语替换</span>'}</div>
            </div>
        </div>
        
        <!-- 阶段 2 -->
        <div class="stage stage-2">
            <div class="stage-header">🔧 阶段 2: Prompt 2.0 结构化 (耗时 {history.prompt20_time_ms}ms)</div>
            <div class="stage-content">
                <h4>参数化模板</h4>
                <div class="text-box template">{history.prompt20_template}</div>
                
                <h4>变量注册表 ({history.prompt20_variable_count} 个变量)</h4>
                <table>
                    <thead>
                        <tr>
                            <th>变量名</th>
                            <th>原文片段</th>
                            <th>提取值</th>
                            <th>类型</th>
                        </tr>
                    </thead>
                    <tbody>
                        {variables_html}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- 阶段 3 -->
        <div class="stage stage-3">
            <div class="stage-header">⚙️ 阶段 3: Prompt 3.0 DSL 编译 (耗时 {history.prompt30_time_ms}ms)</div>
            <div class="stage-content">
                <h4>生成的 DSL 代码</h4>
                {dsl_code_html}
                
                <h4>验证结果</h4>
                {validation_html}
            </div>
        </div>
        
        <!-- 阶段 4 -->
        <div class="stage stage-4">
            <div class="stage-header">💻 阶段 4: Prompt 4.0 代码生成 (耗时 {history.prompt40_time_ms}ms)</div>
            <div class="stage-content">
                <h4>业务流程图（Approach 图）</h4>
                <div class="call-graph-container">
                    <div class="call-graph-header">
                        <span><strong>交互控制</strong></span>
                        <div class="call-graph-controls">
                            <button class="control-btn" onclick="zoomIn()">🔍 放大 (+)</button>
                            <button class="control-btn" onclick="zoomOut()">🔍 缩小 (-)</button>
                            <button class="control-btn reset" onclick="resetZoom()">↺ 重置</button>
                            <span class="zoom-level" id="zoomLevel">100%</span>
                        </div>
                    </div>
                    <div class="mermaid-wrapper" id="mermaidWrapper">
                        <div class="mermaid" id="mermaidDiagram">
{approach_diagram_mermaid}
                        </div>
                    </div>
                    <div class="zoom-hint">
                        💡 提示：此图展示业务逻辑和处理流程，使用鼠标滚轮缩放，或拖拽移动图片
                    </div>
                </div>

                <h4>编译步骤详情</h4>
                {step_details_html}

                <h4>工作流模块 ({history.prompt40_module_count} 个)</h4>
                <div class="module-cards">
                    {modules_html}
                </div>

                <h4>主工作流代码</h4>
                {main_code_html}
            </div>
        </div>
        
        <!-- 统计 -->
        <div class="stats">
            <div class="stat-card">
                <div class="number">{len(history.raw_input)}</div>
                <div class="label">原始字符数</div>
            </div>
            <div class="stat-card">
                <div class="number">{len(history.prompt10_processed)}</div>
                <div class="label">标准化字符数</div>
            </div>
            <div class="stat-card">
                <div class="number">{len(history.prompt10_terminology_changes)}</div>
                <div class="label">术语替换</div>
            </div>
            <div class="stat-card">
                <div class="number">{history.prompt20_variable_count}</div>
                <div class="label">识别变量</div>
            </div>
            <div class="stat-card">
                <div class="number">{history.prompt40_module_count}</div>
                <div class="label">工作流模块</div>
            </div>
            <div class="stat-card">
                <div class="number">{defined_vars_count}</div>
                <div class="label">定义变量</div>
            </div>
            <div class="stat-card">
                <div class="number">{function_calls_count}</div>
                <div class="label">函数调用</div>
            </div>
            <div class="stat-card">
                <div class="number">{history.total_time_ms}</div>
                <div class="label">总耗时(ms)</div>
            </div>
        </div>
        
        <!-- 时间分解 -->
        <div class="time-breakdown">
            <h3 style="margin-top:0;">⏱️ 耗时分解</h3>
            <div class="time-item">
                <span>阶段 1: 预处理</span>
                <span>{history.prompt10_time_ms}ms ({time1_pct:.1f}%)</span>
            </div>
            <div class="time-bar">
                <div class="time-fill" style="width: {time1_pct}%;"></div>
            </div>
            <div class="time-item">
                <span>阶段 2: 结构化</span>
                <span>{history.prompt20_time_ms}ms ({time2_pct:.1f}%)</span>
            </div>
            <div class="time-bar">
                <div class="time-fill stage-2" style="width: {time2_pct}%;"></div>
            </div>
            <div class="time-item">
                <span>阶段 3: DSL 编译</span>
                <span>{history.prompt30_time_ms}ms ({time3_pct:.1f}%)</span>
            </div>
            <div class="time-bar">
                <div class="time-fill stage-3" style="width: {time3_pct}%;"></div>
            </div>
            <div class="time-item">
                <span>阶段 4: 代码生成</span>
                <span>{history.prompt40_time_ms}ms ({time4_pct:.1f}%)</span>
            </div>
            <div class="time-bar">
                <div class="time-fill stage-4" style="width: {time4_pct}%;"></div>
            </div>
        </div>
    </div>

    <!-- 初始化 Mermaid.js 和缩放功能 -->
    <script>
        // 初始化 Mermaid
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose',
            flowchart: {{
                useMaxWidth: false,  // 禁用最大宽度限制
                htmlLabels: true
            }},
            // 添加更多配置选项
            logLevel: 'error',  // 只显示错误日志
            suppressErrorRendering: false,  // 不隐藏错误
        }});

        // 监听 Mermaid 渲染错误
        window.addEventListener('error', function(e) {{
            if (e.message && e.message.includes('mermaid')) {{
                console.error('Mermaid 渲染错误:', e);
            }}
        }});

        // 缩放和平移功能
        let currentZoom = 1;
        let isDragging = false;
        let startX, startY, scrollLeft, scrollTop;
        const mermaidDiagram = document.getElementById('mermaidDiagram');
        const mermaidWrapper = document.getElementById('mermaidWrapper');
        const zoomLevelDisplay = document.getElementById('zoomLevel');

        function updateZoom() {{
            // 限制缩放范围: 0.3x - 3.0x
            currentZoom = Math.max(0.3, Math.min(3.0, currentZoom));
            mermaidDiagram.style.transform = `scale(${{currentZoom}})`;
            zoomLevelDisplay.textContent = `${{Math.round(currentZoom * 100)}}%`;
        }}

        function zoomIn() {{
            currentZoom += 0.1;
            updateZoom();
        }}

        function zoomOut() {{
            currentZoom -= 0.1;
            updateZoom();
        }}

        function resetZoom() {{
            currentZoom = 1;
            updateZoom();
            mermaidWrapper.scrollTo({{
                left: 0,
                top: 0,
                behavior: 'smooth'
            }});
        }}

        // 鼠标滚轮缩放
        mermaidWrapper.addEventListener('wheel', function(e) {{
            e.preventDefault();
            const delta = e.deltaY > 0 ? -0.1 : 0.1;
            currentZoom += delta;
            updateZoom();
        }});

        // 鼠标拖拽平移
        mermaidWrapper.addEventListener('mousedown', function(e) {{
            isDragging = true;
            startX = e.pageX - mermaidWrapper.offsetLeft;
            startY = e.pageY - mermaidWrapper.offsetTop;
            scrollLeft = mermaidWrapper.scrollLeft;
            scrollTop = mermaidWrapper.scrollTop;
        }});

        mermaidWrapper.addEventListener('mouseleave', function() {{
            isDragging = false;
        }});

        mermaidWrapper.addEventListener('mouseup', function() {{
            isDragging = false;
        }});

        mermaidWrapper.addEventListener('mousemove', function(e) {{
            if (!isDragging) return;
            e.preventDefault();
            const x = e.pageX - mermaidWrapper.offsetLeft;
            const y = e.pageY - mermaidWrapper.offsetTop;
            const walkX = (x - startX) * 1.5;  // 平滑系数
            const walkY = (y - startY) * 1.5;
            mermaidWrapper.scrollLeft = scrollLeft - walkX;
            mermaidWrapper.scrollTop = scrollTop - walkY;
        }});

        // 双击重置缩放
        mermaidWrapper.addEventListener('dblclick', function() {{
            resetZoom();
        }});
    </script>
</body>
</html>
"""
        
        # 保存HTML文件
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)
            info(f"流水线HTML报告已保存: {output_file}")
        except Exception as e:
            error(f"保存流水线HTML报告失败: {e}")
        
        return html
    
    def _generate_call_graph_mermaid(self, history: PipelineHistory) -> str:
        """
        生成工作流调用关系图的 Mermaid 语法
        
        Args:
            history: 流水线历史记录
            
        Returns:
            Mermaid graph 语法
        """
        mermaid_lines = ["graph TD", "    %% 工作流调用关系图", ""]
        
        # 添加输入节点
        mermaid_lines.append("    Input([用户输入<br/>input_params]):::input")
        mermaid_lines.append("")
        
        # 添加主工作流节点
        mermaid_lines.append("    Main[main_workflow<br/>主控流程]:::main")
        mermaid_lines.append("")
        
        # 从主工作流到输入节点的连接
        mermaid_lines.append("    Input --> Main")
        mermaid_lines.append("")
        
        # 添加模块节点
        if history.prompt40_modules:
            modules = history.prompt40_modules
            step4_gen = history.prompt40_step4_generation
            
            # 获取模块聚类信息
            clusters = step4_gen.get('clusters', []) if step4_gen else []
            
            # 按照聚类分组显示模块
            if clusters:
                cluster_dict = {}
                # 为每个聚类分配模块
                for cluster_info in clusters:
                    cluster_id = cluster_info.get('cluster_id', 'unknown')
                    block_ids = cluster_info.get('blocks', [])
                    cluster_dict[cluster_id] = block_ids
                
                # 创建节点
                for i, module in enumerate(modules):
                    module_name = module.get('name', f'module_{i}')
                    is_async = module.get('is_async', False)
                    inputs = module.get('inputs', [])
                    outputs = module.get('outputs', [])
                    
                    # 节点样式
                    node_style = ":::async" if is_async else ":::sync"
                    node_id = f"Step{i}"
                    
                    # 节点标签
                    input_str = ", ".join(inputs[:3]) + ("..." if len(inputs) > 3 else "")
                    output_str = ", ".join(outputs[:3]) + ("..." if len(outputs) > 3 else "")
                    
                    label = f"{module_name}<br/><sub>({input_str}) → ({output_str})</sub>"
                    
                    mermaid_lines.append(f"    {node_id}[{label}]{node_style}")
                
                mermaid_lines.append("")
                
                # 添加边：主工作流调用所有模块
                for i, module in enumerate(modules):
                    node_id = f"Step{i}"
                    mermaid_lines.append(f"    Main --> {node_id}")
                
                mermaid_lines.append("")
            else:
                # 如果没有聚类信息，简单列出所有模块
                for i, module in enumerate(modules):
                    module_name = module.get('name', f'module_{i}')
                    is_async = module.get('is_async', False)
                    
                    node_style = ":::async" if is_async else ":::sync"
                    node_id = f"Step{i}"
                    
                    mermaid_lines.append(f"    {node_id}[{module_name}]{node_style}")
                    mermaid_lines.append(f"    Main --> {node_id}")
                
                mermaid_lines.append("")
        
        # 添加输出节点
        mermaid_lines.append("    Output([返回结果<br/>final_output]):::output")
        mermaid_lines.append("")
        
        # 从最后一个模块到输出节点的连接
        if history.prompt40_modules:
            last_step_id = f"Step{len(history.prompt40_modules) - 1}"
            mermaid_lines.append(f"    {last_step_id} --> Output")
        else:
            mermaid_lines.append("    Main --> Output")
        
        mermaid_lines.append("")
        
        # 添加图例
        mermaid_lines.append("    %% 样式定义")
        mermaid_lines.append("    classDef input fill:#d4edda,stroke:#28a745,stroke-width:2px;")
        mermaid_lines.append("    classDef main fill:#e1f5ff,stroke:#007bff,stroke-width:3px;")
        mermaid_lines.append("    classDef sync fill:#fff3cd,stroke:#ffc107,stroke-width:2px;")
        mermaid_lines.append("    classDef async fill:#f8d7da,stroke:#dc3545,stroke-width:2px;")
        mermaid_lines.append("    classDef output fill:#d4edda,stroke:#28a745,stroke-width:2px;")
        
        return "\n".join(mermaid_lines)
    
    def _generate_approach_diagram_mermaid(self, history: PipelineHistory) -> str:
        """
        生成业务流程图（Approach 图）的 Mermaid 语法
        
        使用 LLM 分析代码和需求，生成展示业务逻辑的流程图
        
        Args:
            history: 流水线历史记录
            
        Returns:
            Mermaid graph TD 语法
        """
        # 导入 LLM 客户端
        from llm_client import UnifiedLLMClient
        import json
        
        llm_client = UnifiedLLMClient()
        
        # 准备上下文信息
        context = {
            'business_requirement': history.prompt10_processed or "无需求描述",
            'module_count': len(history.prompt40_modules) if history.prompt40_modules else 0,
            'modules': [],
        }
        
        # 提取模块信息
        if history.prompt40_modules:
            for i, module in enumerate(history.prompt40_modules):
                context['modules'].append({
                    'index': i,
                    'name': module.get('name', f'module_{i}'),
                    'description': module.get('description', '无描述'),
                    'inputs': module.get('inputs', []),
                    'outputs': module.get('outputs', []),
                    'is_async': module.get('is_async', False),
                })
        
        # 获取 DSL 代码
        dsl_code = history.prompt30_dsl_code or ""
        
        # 构建 LLM Prompt
        prompt = f"""你是一个业务架构分析师。请基于以下信息，生成一个展示业务流程的 Mermaid 流程图。

## 业务需求
{context['business_requirement']}

## 模块信息（{context['module_count']} 个）
{json.dumps(context['modules'], indent=2, ensure_ascii=False)}

## DSL 代码
{dsl_code[:2000] if len(dsl_code) > 2000 else dsl_code}

## 要求

1. **重点展示业务逻辑，而非函数调用**
   - 体现数据处理的主要步骤
   - 展示决策点和分支逻辑
   - 使用业务术语，避免技术细节

2. **节点命名规范**
   - 使用业务术语（如：判断场景类型、生成响应内容）
   - 避免使用函数名（如：step_1_compute_xxx）
   - 节点名称简洁明了（不超过 15 个字）

3. **流程图结构**
   - graph TD: 从上到下的流程图
   - 使用菱形（{{条件}}）表示决策点
   - 使用矩形（[步骤]）表示处理步骤
   - 使用圆角（（开始/结束））表示起点和终点

4. **样式要求**
   - 决策节点使用黄色系
   - 处理节点使用蓝色系
   - 起始/结束节点使用绿色系
   - 保持图表清晰易读

5. **输出格式**
   - 只输出 Mermaid graph TD 代码
   - 不包含任何解释文字
   - 不使用 ```mermaid ``` 标记

## 输出示例

graph TD
    Start([用户输入]) --> Check{{是否需要特殊处理?}}
    Check -->|是| Identify[识别场景类型]
    Check -->|否| Generate[直接生成]
    Identify --> Create[创建响应内容]
    Generate --> Format[格式化输出]
    Create --> Format
    Format --> End([返回结果])

    classDef start fill:#d4edda,stroke:#28a745,stroke-width:2px;
    classDef end fill:#d4edda,stroke:#28a745,stroke-width:2px;
    classDef decision fill:#fff3cd,stroke:#ffc107,stroke-width:2px;
    classDef process fill:#e1f5ff,stroke:#007bff,stroke-width:2px;

    class Start start;
    class End end;
    class Check decision;
    class Identify process;
    class Create process;
    class Generate process;
    class Format process;

请根据上述信息生成业务流程图："""
        
        try:
            # 调用 LLM 生成 Mermaid 代码
            system_prompt = """你是一个业务架构分析师，擅长将代码和技术实现转换为清晰的业务流程图。"""
            response = llm_client.call(
                system_prompt=system_prompt,
                user_content=prompt,
                temperature=0.3  # 使用较低的温度以获得更稳定的输出
            )
            mermaid_code = response.content.strip()

            # 清理输出
            mermaid_code = mermaid_code.strip()

            # 移除可能的 markdown 标记
            if mermaid_code.startswith('```'):
                mermaid_code = mermaid_code.split('```')[1]
                if mermaid_code.startswith('mermaid'):
                    mermaid_code = mermaid_code[7:]
            if mermaid_code.endswith('```'):
                mermaid_code = mermaid_code[:-3]

            mermaid_code = mermaid_code.strip()

            # 清理不兼容的 Mermaid 10.x 语法
            # 移除 :::className 语法，替换为正确的 class 定义
            import re

            # 基本语法验证：检查括号是否匹配
            def validate_parentheses(code: str) -> tuple:
                """验证括号是否匹配"""
                stack = []
                brackets = {'(': ')', '[': ']', '{': '}'}
                position = 0

                for char in code:
                    position += 1
                    if char in brackets:
                        stack.append(char)
                    elif char in brackets.values():
                        if not stack:
                            return False, f"Unexpected closing bracket '{char}' at position {position}"
                        if brackets[stack[-1]] != char:
                            return False, f"Mismatched bracket at position {position}"
                        stack.pop()

                if stack:
                    return False, f"Unclosed brackets: {stack}"
                return True, ""

            # 验证基本语法
            is_valid, error_msg = validate_parentheses(mermaid_code)
            if not is_valid:
                error(f"LLM 返回的 Mermaid 代码语法错误: {error_msg}")
                error(f"原始代码: {mermaid_code[:200]}...")
                return self._get_default_approach_diagram(context)

            # 提取所有节点和它们的类
            node_class_map = {}
            class_pattern = r'(\w+)\([^\)]+\)|(\w+)\[[^\]]+\)|(\w+)\{\{[^}]+\}\}\s*:::(\w+)'

            # 查找所有使用 :::className 的节点
            try:
                for match in re.finditer(r'(\w+)\([^\)]+\)|(\w+)\[[^\]]+\)|(\w+)\{\{[^}]+\}\}):::(\w+)', mermaid_code):
                    node_def = match.group(1)
                    class_name = match.group(4)
                    node_class_map[node_def] = class_name

                # 移除 :::className 语法
                mermaid_code = re.sub(r':::\w+', '', mermaid_code)
            except Exception as regex_error:
                error(f"正则表达式清理失败: {regex_error}")
                return self._get_default_approach_diagram(context)

            # 验证是否包含 graph TD
            if 'graph TD' not in mermaid_code:
                # 如果 LLM 返回的不是 Mermaid 代码，使用默认模板
                return self._get_default_approach_diagram(context)
            
            return mermaid_code
            
        except Exception as e:
            error(f"生成 Approach 图失败: {e}")
            # 返回默认的流程图
            return self._get_default_approach_diagram(context)
    
    def _get_default_approach_diagram(self, context: dict) -> str:
        """
        生成默认的业务流程图（当 LLM 调用失败时使用）

        Args:
            context: 上下文信息

        Returns:
            Mermaid graph TD 语法
        """
        mermaid_lines = ["graph TD", "    %% 业务流程图（默认生成）", ""]

        # 添加起始节点
        mermaid_lines.append("    Start([用户输入])")
        mermaid_lines.append("")

        # 根据模块数量生成处理步骤
        if context['module_count'] > 0:
            # 添加判断节点
            mermaid_lines.append("    Process1[处理输入数据]")
            mermaid_lines.append("    Start --> Process1")
            mermaid_lines.append("")

            # 添加中间处理步骤
            for i in range(1, context['module_count']):
                mermaid_lines.append(f"    Process{i+1}[处理步骤 {i+1}]")
                mermaid_lines.append(f"    Process{i} --> Process{i+1}")

            mermaid_lines.append("")

        # 添加结束节点
        mermaid_lines.append("    End([返回结果])")

        if context['module_count'] > 0:
            mermaid_lines.append(f"    Process{context['module_count']} --> End")
        else:
            mermaid_lines.append("    Start --> End")

        mermaid_lines.append("")

        # 添加样式定义（使用 style 语法，更稳定）
        mermaid_lines.append("    %% 样式定义")
        mermaid_lines.append("    style Start fill:#d4edda,stroke:#28a745,stroke-width:2px")
        mermaid_lines.append("    style End fill:#d4edda,stroke:#28a745,stroke-width:2px")
        for i in range(1, context['module_count'] + 1):
            mermaid_lines.append(f"    style Process{i} fill:#e1f5ff,stroke:#007bff,stroke-width:2px")

        return "\n".join(mermaid_lines)
