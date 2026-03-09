"""翻译和 TTS 效果评测模块"""

import os
import time
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .base import TranslationResult, TTSResult
from .registry import get_translator, get_tts_engine, list_translators, list_tts_engines
from .config import load_config

# 确保插件被加载
from . import translators
from . import tts_engines

# 默认评测语句
DEFAULT_TEST_SENTENCES = [
    {
        "mandarin": "你好，今天天气怎么样？",
        "reference": "你好，今日天氣點呀？",
        "category": "日常问候",
    },
    {
        "mandarin": "我不知道他去了哪里。",
        "reference": "我唔知佢去咗邊度。",
        "category": "日常对话",
    },
    {
        "mandarin": "这个东西多少钱？",
        "reference": "呢樣嘢幾多錢呀？",
        "category": "购物",
    },
    {
        "mandarin": "我们明天一起去吃饭吧。",
        "reference": "我哋聽日一齊去食飯啦。",
        "category": "邀约",
    },
    {
        "mandarin": "他说的话我听不懂。",
        "reference": "佢講嘅嘢我聽唔明。",
        "category": "日常对话",
    },
    {
        "mandarin": "别着急，慢慢来。",
        "reference": "唔使急，慢慢嚟。",
        "category": "安慰",
    },
    {
        "mandarin": "你吃过饭了吗？",
        "reference": "你食咗飯未呀？",
        "category": "问候",
    },
    {
        "mandarin": "这件事情很难办。",
        "reference": "呢件事好難搞。",
        "category": "表达感受",
    },
    {
        "mandarin": "我在这里等你很久了。",
        "reference": "我喺呢度等咗你好耐喇。",
        "category": "表达状态",
    },
    {
        "mandarin": "下班以后我们去喝茶。",
        "reference": "收工之後我哋去飲茶。",
        "category": "邀约",
    },
]

# 粤语特征词汇表（用于评估翻译质量）
CANTONESE_MARKERS = [
    "嘅", "咗", "喺", "嚟", "啲", "佢", "冇", "嗰", "噉", "嘢",
    "唔", "係", "邊", "點", "幾", "畀", "攞", "返", "落", "入",
    "食", "飲", "揸", "睇", "傾", "搵", "諗", "驚", "鍾意", "得閒",
    "嗮", "晒", "哋", "啦", "喎", "囉", "咩", "呀", "吖", "㗎",
    "未", "先", "仲", "都", "就", "而家", "聽日", "尋日", "琴日", "收工",
]


def calculate_cantonese_score(text: str) -> float:
    """计算文本的粤语特征得分 (0-1)"""
    if not text:
        return 0.0
    found = sum(1 for marker in CANTONESE_MARKERS if marker in text)
    # 每个句子平均期望包含 3-5 个粤语特征词
    score = min(found / 4.0, 1.0)
    return round(score, 2)


def simple_char_similarity(text1: str, text2: str) -> float:
    """简单的字符级相似度"""
    if not text1 or not text2:
        return 0.0
    set1 = set(text1)
    set2 = set(text2)
    intersection = set1 & set2
    union = set1 | set2
    return round(len(intersection) / len(union), 2) if union else 0.0


class Evaluator:
    """翻译和 TTS 效果评测器"""

    def __init__(self, config: Optional[Dict] = None, config_path: Optional[str] = None,
                 test_sentences: Optional[List[Dict]] = None):
        self.config = config or load_config(config_path)
        self.test_sentences = test_sentences or DEFAULT_TEST_SENTENCES
        self.output_dir = Path(self.config.get("output", {}).get("dir", "./output")) / "evaluation"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_test_sentences(self, path: str):
        """从 YAML 文件加载测试语句"""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        self.test_sentences = data.get("sentences", data)

    def evaluate_translator(self, translator_name: str, **kwargs) -> Dict:
        """评测单个翻译器"""
        print(f"\n{'='*60}")
        print(f"📝 评测翻译器: {translator_name}")
        print(f"{'='*60}")

        try:
            translator = get_translator(translator_name, **kwargs)
            if not translator.validate():
                return {"name": translator_name, "error": "验证失败（缺少 API Key？）", "results": []}
        except Exception as e:
            return {"name": translator_name, "error": str(e), "results": []}

        results = []
        total_cantonese_score = 0
        total_similarity = 0

        for i, sentence in enumerate(self.test_sentences):
            mandarin = sentence["mandarin"]
            reference = sentence.get("reference", "")
            category = sentence.get("category", "")

            print(f"\n  [{i+1}/{len(self.test_sentences)}] {category}")
            print(f"  普通话: {mandarin}")

            try:
                start = time.time()
                result = translator.translate(mandarin)
                elapsed = time.time() - start

                cantonese_score = calculate_cantonese_score(result.cantonese_text)
                similarity = simple_char_similarity(result.cantonese_text, reference) if reference else 0

                print(f"  粤　语: {result.cantonese_text}")
                if reference:
                    print(f"  参　考: {reference}")
                print(f"  粤语特征分: {cantonese_score:.2f} | 相似度: {similarity:.2f} | 耗时: {elapsed:.2f}s")

                total_cantonese_score += cantonese_score
                total_similarity += similarity

                results.append({
                    "mandarin": mandarin,
                    "translated": result.cantonese_text,
                    "reference": reference,
                    "category": category,
                    "cantonese_score": cantonese_score,
                    "similarity": similarity,
                    "time_seconds": round(elapsed, 2),
                })
            except Exception as e:
                print(f"  ❌ 翻译失败: {e}")
                results.append({
                    "mandarin": mandarin,
                    "reference": reference,
                    "error": str(e),
                })

        count = len([r for r in results if "error" not in r])
        avg_score = total_cantonese_score / count if count else 0
        avg_similarity = total_similarity / count if count else 0

        print(f"\n📊 {translator_name} 评测汇总:")
        print(f"  成功: {count}/{len(self.test_sentences)}")
        print(f"  平均粤语特征分: {avg_score:.2f}")
        print(f"  平均参考相似度: {avg_similarity:.2f}")

        return {
            "name": translator_name,
            "results": results,
            "summary": {
                "success_count": count,
                "total_count": len(self.test_sentences),
                "avg_cantonese_score": round(avg_score, 2),
                "avg_similarity": round(avg_similarity, 2),
            },
        }

    def evaluate_tts(self, tts_name: str, cantonese_texts: Optional[List[str]] = None,
                     **kwargs) -> Dict:
        """评测单个 TTS 引擎"""
        print(f"\n{'='*60}")
        print(f"🔊 评测 TTS 引擎: {tts_name}")
        print(f"{'='*60}")

        try:
            engine = get_tts_engine(tts_name, **kwargs)
            if not engine.validate():
                return {"name": tts_name, "error": "验证失败", "results": []}
        except Exception as e:
            return {"name": tts_name, "error": str(e), "results": []}

        if cantonese_texts is None:
            cantonese_texts = [s.get("reference", "") for s in self.test_sentences if s.get("reference")]

        results = []
        tts_dir = self.output_dir / tts_name
        tts_dir.mkdir(parents=True, exist_ok=True)

        for i, text in enumerate(cantonese_texts[:5]):  # 限制测试数量
            print(f"\n  [{i+1}/{min(len(cantonese_texts), 5)}] {text}")

            output_file = tts_dir / f"test_{i+1}.mp3"

            try:
                start = time.time()
                result = engine.synthesize(text, output_file)
                elapsed = time.time() - start

                file_size = output_file.stat().st_size if output_file.exists() else 0

                print(f"  ✅ 已生成: {output_file} ({file_size} bytes, {elapsed:.2f}s)")

                results.append({
                    "text": text,
                    "audio_file": str(output_file),
                    "file_size_bytes": file_size,
                    "time_seconds": round(elapsed, 2),
                    "voice": result.voice_name,
                })
            except Exception as e:
                print(f"  ❌ 合成失败: {e}")
                results.append({
                    "text": text,
                    "error": str(e),
                })

        count = len([r for r in results if "error" not in r])

        print(f"\n📊 {tts_name} 评测汇总:")
        print(f"  成功: {count}/{len(results)}")
        if count > 0:
            avg_time = sum(r.get("time_seconds", 0) for r in results if "error" not in r) / count
            print(f"  平均合成耗时: {avg_time:.2f}s")

        return {
            "name": tts_name,
            "results": results,
            "summary": {
                "success_count": count,
                "total_count": len(results),
            },
        }

    def run_full_evaluation(self) -> Dict:
        """运行完整评测（所有可用翻译器 + 所有可用 TTS 引擎）"""
        print("\n" + "="*70)
        print("🧪 粤语翻译与语音合成 - 完整效果评测")
        print(f"   测试语句数: {len(self.test_sentences)}")
        print(f"   评测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)

        report = {
            "timestamp": datetime.now().isoformat(),
            "test_sentences_count": len(self.test_sentences),
            "translators": [],
            "tts_engines": [],
        }

        # 评测所有翻译器
        available_translators = list_translators()
        for name in available_translators:
            config_key = {
                "zhipu": "ZHIPU_API_KEY",
                "openai": "OPENAI_API_KEY",
                "qwen": "DASHSCOPE_API_KEY",
            }
            api_key = os.environ.get(config_key.get(name, ""), "")
            if api_key:
                kwargs = {"api_key": api_key}
                if name == "qwen":
                    kwargs["base_url"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
                result = self.evaluate_translator(name, **kwargs)
                report["translators"].append(result)
            else:
                print(f"\n⏭ 跳过翻译器 {name}（未配置 {config_key.get(name, 'API_KEY')}）")
                report["translators"].append({
                    "name": name,
                    "skipped": True,
                    "reason": f"未配置 {config_key.get(name, 'API_KEY')}",
                })

        # 收集粤语参考文本用于 TTS 测试
        cantonese_texts = [s.get("reference", "") for s in self.test_sentences if s.get("reference")]

        # 评测所有 TTS 引擎
        available_engines = list_tts_engines()
        for name in available_engines:
            if name == "tencent":
                sid = os.environ.get("TENCENT_SECRET_ID", "")
                skey = os.environ.get("TENCENT_SECRET_KEY", "")
                if sid and skey:
                    result = self.evaluate_tts(name, cantonese_texts,
                                               secret_id=sid, secret_key=skey)
                    report["tts_engines"].append(result)
                else:
                    print(f"\n⏭ 跳过 TTS {name}（未配置腾讯云凭据）")
                    report["tts_engines"].append({
                        "name": name, "skipped": True,
                        "reason": "未配置 TENCENT_SECRET_ID/TENCENT_SECRET_KEY",
                    })
            elif name == "edge":
                try:
                    result = self.evaluate_tts(name, cantonese_texts)
                    report["tts_engines"].append(result)
                except Exception as e:
                    report["tts_engines"].append({"name": name, "error": str(e)})
            elif name == "gtts":
                try:
                    result = self.evaluate_tts(name, cantonese_texts)
                    report["tts_engines"].append(result)
                except Exception as e:
                    report["tts_engines"].append({"name": name, "error": str(e)})

        # 生成报告
        self._print_summary(report)
        self._save_report(report)

        return report

    def _print_summary(self, report: Dict):
        """打印评测总结"""
        print("\n" + "="*70)
        print("📊 评测总结报告")
        print("="*70)

        print("\n🔤 翻译器对比:")
        print(f"  {'翻译器':<12} {'粤语特征分':<12} {'参考相似度':<12} {'成功率':<10}")
        print(f"  {'-'*46}")
        for t in report["translators"]:
            if t.get("skipped") or t.get("error"):
                status = t.get("reason") or t.get("error", "未知错误")
                print(f"  {t['name']:<12} {'跳过':<12} {status}")
            else:
                s = t.get("summary", {})
                print(f"  {t['name']:<12} {s.get('avg_cantonese_score', 0):<12.2f} "
                      f"{s.get('avg_similarity', 0):<12.2f} "
                      f"{s.get('success_count', 0)}/{s.get('total_count', 0)}")

        print(f"\n🔊 TTS 引擎对比:")
        print(f"  {'引擎':<12} {'成功率':<12} {'状态':<20}")
        print(f"  {'-'*44}")
        for t in report["tts_engines"]:
            if t.get("skipped") or t.get("error"):
                status = t.get("reason") or t.get("error", "未知错误")
                print(f"  {t['name']:<12} {'跳过':<12} {status}")
            else:
                s = t.get("summary", {})
                print(f"  {t['name']:<12} {s.get('success_count', 0)}/{s.get('total_count', 0):<8} ✅")

        print(f"\n📁 评测音频和报告保存在: {self.output_dir}")

    def _save_report(self, report: Dict):
        """保存评测报告"""
        report_file = self.output_dir / f"evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"📄 评测报告已保存: {report_file}")
