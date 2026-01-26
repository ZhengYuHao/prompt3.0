"""
处理历史存储与对比展示模块
用于持久化存储每次处理的结果，并提供清晰的对比展示
支持完整流水线追踪
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from logger import info, warning, error


@dataclass
class ProcessingHistory:
    """单次处理历史记录（兼容旧格式）"""
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
class PipelineHistory:
    """完整流水线历史记录"""
    pipeline_id: str  # 流水线ID
    timestamp: str  # 开始时间戳
    raw_input: str  # 用户原始输入
    
    # 阶段1结果
    prompt10_original: str = ""
    prompt10_processed: str = ""
    prompt10_mode: str = ""
    prompt10_steps: List[Dict] = field(default_factory=list)
    prompt10_terminology_changes: Dict[str, str] = field(default_factory=dict)
    prompt10_ambiguity_detected: bool = False
    prompt10_status: str = ""
    prompt10_time_ms: int = 0
    
    # 阶段2结果
    prompt20_template: str = ""
    prompt20_variables: List[Dict] = field(default_factory=list)
    prompt20_time_ms: int = 0
    
    # 整体状态
    overall_status: str = ""
    total_time_ms: int = 0
    error_message: Optional[str] = None


class HistoryManager:
    """处理历史管理器"""
    
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
