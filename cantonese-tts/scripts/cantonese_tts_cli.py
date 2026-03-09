#!/usr/bin/env python3
"""粤语翻译与语音合成 CLI 工具"""

import argparse
import sys
import os

# 确保包路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cantonese_tts.engine import CantoneseEngine
from cantonese_tts.evaluator import Evaluator
from cantonese_tts.registry import list_translators, list_tts_engines


def main():
    parser = argparse.ArgumentParser(
        description="普通话转粤语语音工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s --text "你好，今天天气怎么样？"
  %(prog)s --text "我想学粤语" --translator zhipu --tts edge
  %(prog)s --text "明天见" --translate-only
  %(prog)s --file input.txt --output output.mp3
  %(prog)s --evaluate
  %(prog)s --list-plugins
        """
    )

    # 输入选项
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--text", "-t", help="要翻译的普通话文本")
    input_group.add_argument("--file", "-f", help="从文件读取普通话文本")

    # 模式选项
    parser.add_argument("--translate-only", action="store_true",
                        help="仅翻译，不进行语音合成")
    parser.add_argument("--evaluate", "-e", action="store_true",
                        help="运行效果评测")
    parser.add_argument("--list-plugins", action="store_true",
                        help="列出所有可用插件")
    parser.add_argument("--validate", action="store_true",
                        help="验证配置")

    # 配置选项
    parser.add_argument("--config", "-c", help="YAML 配置文件路径")
    parser.add_argument("--translator", choices=["zhipu", "openai", "qwen"],
                        help="指定翻译器")
    parser.add_argument("--tts", choices=["edge", "tencent", "gtts"],
                        help="指定 TTS 引擎")
    parser.add_argument("--voice", help="指定 TTS 音色")

    # 输出选项
    parser.add_argument("--output", "-o", help="输出音频文件路径")
    parser.add_argument("--output-dir", default="./output",
                        help="输出目录（默认: ./output）")

    args = parser.parse_args()

    # 列出插件
    if args.list_plugins:
        print("\n📋 可用翻译器:")
        for name in list_translators():
            print(f"  - {name}")
        print("\n📋 可用 TTS 引擎:")
        for name in list_tts_engines():
            print(f"  - {name}")
        return

    # 运行评测
    if args.evaluate:
        evaluator = Evaluator(config_path=args.config)
        evaluator.run_full_evaluation()
        return

    # 加载配置并应用命令行覆盖
    from cantonese_tts.config import load_config
    config = load_config(args.config)

    if args.translator:
        config["translator"]["type"] = args.translator
    if args.tts:
        config["tts"]["type"] = args.tts
    if args.voice:
        config["tts"]["voice"] = args.voice
    if args.output_dir:
        config.setdefault("output", {})["dir"] = args.output_dir

    engine = CantoneseEngine(config=config)

    # 验证配置
    if args.validate:
        errors = engine.validate()
        if errors:
            print("❌ 配置验证失败:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        else:
            print("✅ 配置验证通过")
        return

    # 获取输入文本
    text = None
    if args.text:
        text = args.text
    elif args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            text = f.read().strip()

    if not text:
        parser.print_help()
        print("\n❌ 请提供输入文本（--text 或 --file）")
        sys.exit(1)

    print(f"\n📝 输入文本: {text}")

    # 执行翻译/合成
    if args.translate_only:
        result = engine.translate(text)
        print(f"\n📋 翻译结果:")
        print(f"  普通话: {result.source_text}")
        print(f"  粤  语: {result.cantonese_text}")
        print(f"  翻译器: {result.translator_name} ({result.model_name})")
    else:
        result = engine.convert(text, args.output)
        print(f"\n📋 完整结果:")
        print(f"  普通话: {result.translation.source_text}")
        print(f"  粤  语: {result.translation.cantonese_text}")
        print(f"  翻译器: {result.translation.translator_name} ({result.translation.model_name})")
        if result.tts:
            print(f"  音频文件: {result.tts.audio_path}")
            print(f"  TTS 引擎: {result.tts.engine_name} ({result.tts.voice_name})")


if __name__ == "__main__":
    main()
