"""
提示词预处理与标准化系统 (Prompt Preprocessing & Standardization System)
版本: 2.0
支持模式: 
  - 词表模式 (Dictionary Mode): 基于预定义术语映射和歧义词黑名单
  - 智能模式 (Smart Mode): 纯LLM驱动的自适应处理
"""

import os
import re
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Literal
from dataclasses import dataclass
from enum import Enum
from logger import info, warning, error, debug
from history_manager import HistoryManager, ProcessingHistory

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore


# ============================================================================
# 数据结构定义
# ============================================================================

@dataclass
class ProcessingResult:
    """预处理结果数据类"""
    original_text: str
    processed_text: str
    steps_log: List[str]
    warnings: List[str]
    terminology_changes: Dict[str, str]
    ambiguity_detected: bool


class ProcessingMode(Enum):
    """处理模式枚举"""
    DICTIONARY = "dictionary"  # 基于词表
    SMART = "smart"           # 纯LLM智能
    HYBRID = "hybrid"         # 混合模式


# ============================================================================
# LLM 接口封装（桥接 GPT，兼容 OpenAI API）
# ============================================================================

# 默认桥接地址与 Key；生产环境建议使用环境变量 RCOUYI_API_KEY，勿将 key 提交仓库
RCOUYI_BASE_URL = "https://api.rcouyi.com/v1"
RCOUYI_API_KEY_DEFAULT = "sk-0JL8T592b6roD3uaDaD0Ac0f081c4040810d978e38CdAa01"


class LLMInterface:
    """LLM 调用接口：桥接 https://api.rcouyi.com/v1（OpenAI 兼容）"""
    
    def __init__(
        self,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.1,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.model = model
        self.temperature = temperature
        self.base_url = base_url or os.environ.get("RCOUYI_BASE_URL", RCOUYI_BASE_URL)
        self.api_key = api_key or os.environ.get("RCOUYI_API_KEY", RCOUYI_API_KEY_DEFAULT)
        self._client: Optional["OpenAI"] = None
    
    def _get_client(self) -> "OpenAI":
        if OpenAI is None:
            raise RuntimeError("请先安装 openai: pip install openai")
        if self._client is None:
            self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        return self._client
    
    def call(self, system_prompt: str, user_content: str) -> str:
        """
        调用桥接 GPT API（OpenAI 兼容）。
        """
        info(f"[LLM调用] 模型: {self.model}, Temperature: {self.temperature}")
        debug(f"[System] {system_prompt[:100]}...")
        debug(f"[User] {user_content[:100]}...")
        
        client = self._get_client()
        resp = client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
        return text


# ============================================================================
# 核心预处理器
# ============================================================================

class PromptPreprocessor:
    """提示词预处理核心引擎"""
    
    def __init__(
        self,
        mode: ProcessingMode = ProcessingMode.DICTIONARY,
        term_mapping: Optional[Dict[str, str]] = None,
        ambiguity_blacklist: Optional[List[str]] = None,
        llm_interface: Optional[LLMInterface] = None,
        enable_deep_check: bool = True
    ):
        """
        初始化预处理器
        
        Args:
            mode: 处理模式 (dictionary/smart/hybrid)
            term_mapping: 术语映射表 {'旧词': '标准词'}
            ambiguity_blacklist: 歧义词黑名单
            llm_interface: LLM接口实例
            enable_deep_check: 是否启用深度结构歧义检测
        """
        self.mode = mode
        self.term_mapping = term_mapping or {}
        self.ambiguity_blacklist = ambiguity_blacklist or []
        self.llm = llm_interface or LLMInterface()
        self.enable_deep_check = enable_deep_check
        
        # 日志记录
        self.processing_log: List[str] = []
        self.warnings: List[str] = []
        
        # 历史记录管理器
        self.history_manager = HistoryManager()
    
    # ========================================================================
    # 阶段 1.1: 术语标准化 (基于规则)
    # ========================================================================
    
    def _normalize_terminology(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        【纯代码操作】术语强一致性对齐
        
        策略: 最长匹配原则 (Longest Match First)
        返回: (处理后文本, 替换记录字典)
        """
        if not self.term_mapping:
            return text, {}
        
        changes: Dict[str, str] = {}
        occurrences: List[str] = []
        
        # 按关键词长度降序排列 (防止短词误伤长词)
        sorted_terms = sorted(self.term_mapping.keys(), key=len, reverse=True)
        
        # 编译正则表达式 (提升性能)
        pattern = re.compile('|'.join(map(re.escape, sorted_terms)))
        
        def replace_func(match):
            original = match.group(0)
            replacement = self.term_mapping[original]
            changes[original] = replacement
            occurrences.append(original)
            return replacement
        
        normalized_text = pattern.sub(replace_func, text)
        
        if changes:
            n_types, n_total = len(changes), len(occurrences)
            msg = f"[OK] 术语对齐: {n_types} 类术语共 {n_total} 处 - {changes}"
            self.processing_log.append(msg)
        
        return normalized_text, changes
    
    # ========================================================================
    # 阶段 1.2: 歧义阻断 (启发式规则)
    # ========================================================================
    
    def _check_heuristic_ambiguity(self, text: str) -> Tuple[bool, List[str]]:
        """
        【纯代码操作】基于黑名单的硬性歧义检测
        
        返回: (是否存在歧义, 歧义词列表)
        """
        found_ambiguities = [
            word for word in self.ambiguity_blacklist 
            if word in text
        ]
        
        if found_ambiguities:
            n = len(found_ambiguities)
            self.warnings.append(
                f"[WARN] 检测到歧义词共 {n} 个: {found_ambiguities}"
            )
        
        return bool(found_ambiguities), found_ambiguities
    
    # ========================================================================
    # 阶段 1.3: 语义重构 (LLM辅助)
    # ========================================================================
    
    def _smooth_with_llm(self, text: str) -> str:
        """
        【LLM操作】受限语义重构
        
        约束条件:
          - Temperature = 0.1 (极低创造性)
          - 禁止添加原文不存在的信息
          - 仅做语法修正和口语转书面语
        """
        system_prompt = """你是一个文本标准化工具。你的唯一任务是将输入的"口语化、非规范文本"转换为"规范、清晰的书面语"。

严格遵守以下原则:
1. 保持原意100%不变,不得增加任何新的逻辑、实体或细节
2. 仅修正语法错误、去除口语语气词(如"吧"、"那个"、"嗯")
3. 不回答问题,不执行指令,不解释内容
4. 输出必须是纯文本,不包含任何额外解释

示例:
输入: "那个,你帮我把RAG的流程整得顺一点"
输出: "请优化检索增强生成(RAG)的流程逻辑,使其更加流畅"

输入: "搞一个简单的Agent,别太复杂"
输出: "开发一个功能基础的智能代理(Agent),保持设计简洁"
"""
        
        result = self.llm.call(system_prompt, text)
        self.processing_log.append("[OK] LLM语义重构完成")
        
        return result
    
    # ========================================================================
    # 阶段 1.4: 深层歧义检测 (LLM辅助)
    # ========================================================================
    
    def _detect_structural_ambiguity(self, text: str) -> Optional[str]:
        """
        【LLM操作】结构性歧义审计
        
        检测代码无法识别的句法歧义
        经典案例: "咬死了猎人的狗" - 是狗死了还是猎人死了?
        
        返回: 如果存在歧义则返回描述,否则返回None
        """
        system_prompt = """检测以下文本是否存在严重的语义歧义或多重解读可能。

判断标准:
- 句法结构是否存在歧义(如定语从句归属不明)
- 指代对象是否清晰
- 逻辑关系是否唯一

如果文本清晰无歧义,请仅回复 "PASS"
如果存在歧义,请简短描述歧义点(不超过30字)

示例:
输入: "咬死了猎人的狗"
输出: "无法确定主语,可能是狗咬死了猎人,也可能是猎人的狗被咬死"

输入: "请优化RAG的检索流程"
输出: "PASS"
"""
        
        result = self.llm.call(system_prompt, text)
        raw = (result or "").strip()
        
        def _is_pass(r: str) -> bool:
            if "PASS" in r.upper():
                return True
            # 兼容模型用中文回复：简短且含无歧义/通过，且非歧义描述
            if len(r) > 80:
                return False
            if any(kw in r for kw in ("无歧义", "通过", "无严重歧义", "清晰无歧义")):
                if not any(bad in r for bad in ("存在歧义", "有歧义", "存在严重歧义")):
                    return True
            return False
        
        if _is_pass(raw):
            self.processing_log.append("[OK] 结构歧义检查: 通过")
            return None
        self.warnings.append(f"[WARN] 检测到句法歧义: {raw}")
        return raw
    
    # ========================================================================
    # 智能模式: 纯LLM端到端处理
    # ========================================================================
    
    def _smart_process(self, text: str) -> str:
        """
        【纯LLM模式】端到端智能处理
        
        适用场景:
          - 没有预定义词表
          - 需要处理全新领域
          - 对灵活性要求高于确定性
        """
        system_prompt = """你是一个高级提示词预处理系统。你的任务是将用户的原始输入标准化为清晰、无歧义的规范文本。

处理要求:
1. 术语标准化: 将口语化、非正式术语转换为技术标准术语
   - "套壳" → "基于API的封装应用"
   - "大模型" → "大型语言模型(LLM)"
   
2. 语法规范化: 修正口语化表达
   - 去除语气词("吧"、"嗯"、"那个")
   - 转换为书面语
   
3. 歧义消除: 如果发现严重歧义,在文本后添加 [AMBIGUITY: 描述]
   
4. 信息保真: 绝对不添加原文不存在的信息

输出格式: 纯文本(如有歧义则在末尾添加标记)

示例:
输入: "帮我搞一个RAG的大模型应用,chain要复杂一点"
输出: "开发一个基于检索增强生成(RAG)的大型语言模型应用,处理链(Chain)需要具备较高的复杂度"

输入: "这个需求没啥意思"
输出: "这个需求价值较低 [AMBIGUITY: '没意思'可能指:1.无趣 2.无意义 3.无商业价值]"
"""
        
        result = self.llm.call(system_prompt, text)
        
        # 检查是否包含歧义标记
        if "[AMBIGUITY:" in result:
            ambiguity_part = result.split("[AMBIGUITY:")[1].split("]")[0]
            self.warnings.append(f"[WARN] LLM检测到歧义: {ambiguity_part}")
            result = result.split("[AMBIGUITY:")[0].strip()
        
        self.processing_log.append("[OK] 智能模式处理完成")
        return result
    
    # ========================================================================
    # 主处理流程
    # ========================================================================
    
    def process(self, raw_text: str, save_history: bool = True, show_comparison: bool = True) -> ProcessingResult:
        """
        主处理入口
        
        执行流程:
          Dictionary模式: 规则 → LLM润色 → 歧义检测
          Smart模式: 纯LLM端到端
          Hybrid模式: 规则 + LLM智能兜底
        
        Args:
            raw_text: 原始输入文本
            save_history: 是否保存处理历史
            show_comparison: 是否显示对比结果
        """
        # 记录处理开始时间
        start_time = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 重置日志
        self.processing_log = []
        self.warnings = []
        
        info(f"\n{'='*60}")
        info(f"[开始处理] 模式: {self.mode.value}")
        info(f"[原始输入] {raw_text}")
        info(f"{'='*60}\n")
        
        terminology_changes = {}
        ambiguity_detected = False
        processed_text = raw_text
        success = False
        
        try:
            if self.mode == ProcessingMode.SMART:
                # 纯智能模式
                processed_text = self._smart_process(raw_text)
                
            else:
                # 词表模式 或 混合模式
                
                # 步骤1: 术语对齐 (代码层)
                processed_text, terminology_changes = self._normalize_terminology(
                    processed_text
                )
                
                # 步骤2: 硬性歧义阻断 (代码层)
                has_ambiguity, ambiguous_words = self._check_heuristic_ambiguity(
                    processed_text
                )
                
                if has_ambiguity:
                    ambiguity_detected = True
                    # 即使检测到歧义词，也先进行LLM修复，然后再抛出异常
                    # 这样用户可以看到修复后的结果
                    info("[INFO] 检测到歧义词，但将继续进行LLM修复以展示修复结果...")
                    processed_text = self._smooth_with_llm(processed_text)
                    # 保存修复后的文本，然后抛出异常
                    self.processing_log.append(f"[WARN] 检测到歧义词 {ambiguous_words}，但已生成修复版本")
                    raise ValueError(
                        f"【流程中断】检测到歧义词 {ambiguous_words}\n"
                        f"建议: 请明确指代对象后重新输入\n"
                        f"【修复后的文本】: {processed_text}"
                    )
                
                # 步骤3: LLM语义重构 (LLM层) - 这里会修复文本
                processed_text = self._smooth_with_llm(processed_text)
                
                # 步骤4: 深层歧义检测 (LLM层)
                if self.enable_deep_check:
                    structural_ambiguity = self._detect_structural_ambiguity(
                        processed_text
                    )
                    if structural_ambiguity:
                        ambiguity_detected = True
                        # 保存修复后的文本，然后抛出异常
                        self.processing_log.append(f"[WARN] 检测到句法歧义: {structural_ambiguity}")
                        raise ValueError(
                            f"【流程中断】检测到句法歧义\n"
                            f"详情: {structural_ambiguity}\n"
                            f"【修复后的文本】: {processed_text}"
                        )
            
            success = True
            info("\n[处理完成] [OK]")
            
        except ValueError as e:
            error("\n[处理失败] [FAIL]")
            # 避免在 Windows GBK 下打印含中文的 e 导致 UnicodeEncodeError 崩溃
            _msg = str(e)
            if "检测到歧义词" in _msg or "检测到句法歧义" in _msg:
                warning("(歧义阻断，已拦截 — 属预期行为)")
                # 即使有歧义，也构建结果对象以展示修复后的文本
                result = ProcessingResult(
                    original_text=raw_text,
                    processed_text=processed_text,  # 保存修复后的文本
                    steps_log=self.processing_log,
                    warnings=self.warnings,
                    terminology_changes=terminology_changes,
                    ambiguity_detected=True
                )
                # 展示修复结果
                info("\n" + "─"*60)
                info("【修复结果展示】:")
                info("─"*60)
                info(f"原始文本: {raw_text}")
                info(f"修复后文本: {processed_text}")
                if result.terminology_changes:
                    info("\n术语替换:")
                    for old, new in result.terminology_changes.items():
                        info(f"  {old} → {new}")
                info("─"*60)
                
                # 保存历史记录
                if save_history:
                    self._save_processing_history(
                        timestamp, raw_text, processed_text, terminology_changes,
                        ambiguity_detected, success=False, start_time=start_time
                    )
                
                return result  # 返回结果而不是抛出异常，让调用者可以看到修复结果
            raise
        
        # 构建结果对象
        result = ProcessingResult(
            original_text=raw_text,
            processed_text=processed_text,
            steps_log=self.processing_log,
            warnings=self.warnings,
            terminology_changes=terminology_changes,
            ambiguity_detected=ambiguity_detected
        )
        
        # 打印处理日志
        self._print_result(result)
        
        # 保存历史记录
        if save_history:
            self._save_processing_history(
                timestamp, raw_text, processed_text, terminology_changes,
                ambiguity_detected, success=True, start_time=start_time
            )
            
            # 显示对比
            if show_comparison:
                history = self.history_manager.get_history(timestamp)
                if history:
                    self.history_manager.print_comparison(history)
        
        return result
    
    def _save_processing_history(
        self,
        timestamp: str,
        original_text: str,
        processed_text: str,
        terminology_changes: Dict[str, str],
        ambiguity_detected: bool,
        success: bool,
        start_time: float
    ):
        """保存处理历史"""
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        history = ProcessingHistory(
            timestamp=timestamp,
            original_text=original_text,
            processed_text=processed_text,
            mode=self.mode.value,
            steps_log=self.processing_log.copy(),
            warnings=self.warnings.copy(),
            terminology_changes=terminology_changes.copy(),
            ambiguity_detected=ambiguity_detected,
            success=success,
            processing_time_ms=processing_time_ms
        )
        
        try:
            self.history_manager.save_history(history)
        except Exception as e:
            warning(f"保存处理历史失败: {e}")
    
    def _print_result(self, result: ProcessingResult):
        """打印处理结果"""
        info("\n" + "─"*60)
        info("处理日志:")
        for log in result.steps_log:
            info(f"  {log}")
        
        if result.warnings:
            info("\n警告信息:")
            for warn_msg in result.warnings:
                warning(f"  {warn_msg}")
        
        if result.terminology_changes:
            info("\n术语替换:")
            for old, new in result.terminology_changes.items():
                info(f"  {old} → {new}")
        
        info("\n" + "─"*60)
        info(f"[最终输出]\n{result.processed_text}")
        info("="*60 + "\n")


# ============================================================================
# 配置加载器
# ============================================================================

class ConfigLoader:
    """配置文件加载器"""
    
    @staticmethod
    def load_term_mapping(file_path: str) -> Dict[str, str]:
        """加载术语映射表 (JSON格式)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            warning(f"配置文件不存在: {file_path},使用默认配置")
            return {}
    
    @staticmethod
    def load_blacklist(file_path: str) -> List[str]:
        """加载歧义词黑名单 (每行一个词)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            warning(f"配置文件不存在: {file_path},使用默认配置")
            return []
    
    @staticmethod
    def get_default_term_mapping() -> Dict[str, str]:
        """默认术语映射表"""
        return {
            "套壳": "基于API的封装应用",
            "大模型": "大型语言模型(LLM)",
            "chain": "处理链(Chain)",
            "RAG": "检索增强生成(RAG)",
            "幻觉": "模型幻觉(Hallucination)",
            "微调": "模型微调(Fine-tuning)",
            "Agent": "智能代理(Agent)",
            "Prompt": "提示词(Prompt)",
            "CoT": "思维链(Chain-of-Thought)"
        }
    
    @staticmethod
    def get_default_blacklist() -> List[str]:
        """默认歧义词黑名单"""
        return [
            "意思", "那个", "随便", "搞一下", "弄一下", "弄好",
            "稍微", "简单点", "复杂点", "看着办",
            "差不多", "大概", "可能"
        ]


# ============================================================================
# 复杂示例（约200字，用于验证术语密集 + 歧义阻断）
# ============================================================================

COMPLEX_EXAMPLE_TERMINOLOGY = (
    "我们想做一个基于大模型的智能应用，用RAG做检索增强，配合Agent做决策。"
    "链式处理chain要设计得完整一点，避免出现幻觉。可以考虑用CoT做推理，Prompt要写清楚。"
    "如果效果不好再考虑微调，不要搞成那种套壳的玩意儿。"
    "另外检索模块要能处理多轮对话，保持上下文一致。"
    "整体希望检索准、生成稳，尽量少出现幻觉，必要时再上微调优化效果。"
)

COMPLEX_EXAMPLE_AMBIGUITY = (
    "这个需求你看着办吧，我们大概想要一个RAG加大模型的应用，chain要复杂点，别搞一下那种简单的。"
    "意思就是能检索、能生成就行，稍微像样一点，差不多满足业务就成。"
    "具体你随便弄一下，弄好就成。不需要搞太复杂点，可能加个Agent、用点RAG就差不多了。"
    "你那边先弄好一版，我们再看效果，那个具体的实现细节你们随便定就行。"
)


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # ------------------------------------------------------------------------
    # 场景1: 词表模式 (Dictionary Mode) - 最高确定性
    # ------------------------------------------------------------------------
    info("\n" + "█"*60)
    info("█  场景1: 词表模式 (基于预定义规则)")
    info("█"*60)
    
    processor_dict = PromptPreprocessor(
        mode=ProcessingMode.DICTIONARY,
        term_mapping=ConfigLoader.get_default_term_mapping(),
        ambiguity_blacklist=ConfigLoader.get_default_blacklist(),
        enable_deep_check=True
    )
    
    test_case_1 = "帮我搞一个RAG的大模型应用,chain要复杂一点。"
    
    try:
        result1 = processor_dict.process(test_case_1)
    except ValueError as e:
        error(f"处理失败: {e}")
    
    
    # ------------------------------------------------------------------------
    # 场景2: 歧义词触发中断
    # ------------------------------------------------------------------------
    info("\n" + "█"*60)
    info("█  场景2: 歧义词检测 (触发中断)")
    info("█"*60)
    
    test_case_2 = "这个需求没啥意思,你看着办。"
    
    try:
        result2 = processor_dict.process(test_case_2)
    except ValueError as e:
        info("[OK] 成功拦截歧义输入")
    
    
    # ------------------------------------------------------------------------
    # 场景3: 智能模式 (Smart Mode) - 无需配置词表
    # ------------------------------------------------------------------------
    info("\n" + "█"*60)
    info("█  场景3: 智能模式 (纯LLM驱动)")
    info("█"*60)
    
    processor_smart = PromptPreprocessor(
        mode=ProcessingMode.SMART,
        enable_deep_check=False  # 智能模式已内置歧义检测
    )
    
    test_case_3 = "我想做个类似ChatGPT的东西,但要能联网搜索,还要能记住上下文。"
    
    try:
        result3 = processor_smart.process(test_case_3)
    except ValueError as e:
        error(f"处理失败: {e}")
    
    
    # ------------------------------------------------------------------------
    # 场景4: 从配置文件加载 (生产环境推荐)
    # ------------------------------------------------------------------------
    info("\n" + "█"*60)
    info("█  场景4: 配置文件加载示例")
    info("█"*60)
    
    # 示例: 如何保存配置到文件
    # import json
    # with open('term_mapping.json', 'w', encoding='utf-8') as f:
    #     json.dump(ConfigLoader.get_default_term_mapping(), f, 
    #               ensure_ascii=False, indent=2)
    
    # with open('ambiguity_blacklist.txt', 'w', encoding='utf-8') as f:
    #     f.write('\n'.join(ConfigLoader.get_default_blacklist()))
    
    # 加载配置
    # term_map = ConfigLoader.load_term_mapping('term_mapping.json')
    # blacklist = ConfigLoader.load_blacklist('ambiguity_blacklist.txt')
    
    info("""
配置文件格式:

1. term_mapping.json (术语映射表):
{
  "套壳": "基于API的封装应用",
  "大模型": "大型语言模型(LLM)"
}

2. ambiguity_blacklist.txt (歧义词黑名单,每行一个):
意思
那个
随便
搞一下
    """)
    
    
    # ------------------------------------------------------------------------
    # 场景5: 复杂示例 - 术语密集（约200字，无歧义词，应完整通过）
    # ------------------------------------------------------------------------
    info("\n" + "█"*60)
    info("█  场景5: 复杂示例 - 术语密集（约200字）")
    info("█"*60)
    
    try:
        result5 = processor_dict.process(COMPLEX_EXAMPLE_TERMINOLOGY)
        info(f"  [统计] 术语替换 {len(result5.terminology_changes)} 类，"
              f"步骤数 {len(result5.steps_log)}，警告数 {len(result5.warnings)}")
    except ValueError as e:
        error(f"  处理失败: {e}")
    
    
    # ------------------------------------------------------------------------
    # 场景6: 复杂示例 - 歧义触发（约200字，含多处黑名单词，应拦截）
    # 说明：此场景预期「处理失败」— 流程在歧义检测阶段中断，即成功拦截。
    # ------------------------------------------------------------------------
    info("\n" + "█"*60)
    info("█  场景6: 复杂示例 - 歧义触发（约200字）")
    info("█"*60)
    
    try:
        result6 = processor_dict.process(COMPLEX_EXAMPLE_AMBIGUITY)
        warning("  [未预期] 应被歧义拦截却通过了")
    except ValueError as e:
        info("  [OK] 成功拦截歧义输入（复杂长文本）")
        try:
            detail = str(e).replace("\n", " ").strip()
            info(f"  [详情] {detail[:200]}{'...' if len(detail) > 200 else ''}")
        except Exception:
            info("  [详情] 已拦截，含黑名单歧义词。")
    
    
    info("\n" + "█"*60)
    info("█  系统演示完成")
    info("█"*60)
    info("""
使用建议:

1. 词表模式: 适用于术语固定的专业领域(法律、医疗、金融)
   - 优势: 100%准确,零Token消耗(术语对齐阶段)
   - 劣势: 需要维护词表

2. 智能模式: 适用于通用场景或新兴领域
   - 优势: 无需配置,适应性强
   - 劣势: 完全依赖LLM,成本较高

3. 生产环境推荐: 混合模式
   - 核心术语用词表强制对齐
   - 未覆盖的部分交给LLM智能处理

4. 历史记录功能:
   - 每次处理都会自动保存到 processing_history/history.json
   - 使用 history_manager 可以查看和对比历史记录
   - 支持导出HTML格式的对比报告
""")
    
    
    # ------------------------------------------------------------------------
    # 场景7: 查看处理历史记录
    # ------------------------------------------------------------------------
    info("\n" + "█"*60)
    info("█  场景7: 查看处理历史记录")
    info("█"*60)
    
    history_manager = HistoryManager()
    recent_history = history_manager.get_recent_history(limit=5)
    
    if recent_history:
        info(f"\n找到 {len(recent_history)} 条最近的处理记录:")
        for i, hist in enumerate(recent_history, 1):
            info(f"\n记录 {i}:")
            info(f"  时间: {hist.timestamp}")
            info(f"  模式: {hist.mode}")
            info(f"  状态: {'✅ 成功' if hist.success else '⚠️ 检测到歧义'}")
            info(f"  原始文本: {hist.original_text[:50]}...")
            info(f"  处理后文本: {hist.processed_text[:50]}...")
        
        # 展示最新一条记录的详细对比
        if recent_history:
            info("\n" + "="*60)
            info("最新记录的详细对比:")
            info("="*60)
            history_manager.print_comparison(recent_history[0])
    else:
        info("暂无处理历史记录")



# -----------------------------------------------------------------------------
# 生产环境：建议通过环境变量配置 RCOUYI_BASE_URL / RCOUYI_API_KEY，勿提交 key。
# 依赖: pip install openai
# -----------------------------------------------------------------------------



