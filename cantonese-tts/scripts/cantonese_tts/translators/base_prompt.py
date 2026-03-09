"""翻译器公共提示词模板"""

SYSTEM_PROMPT = """你是一位精通普通话和粤语的翻译专家。请将用户输入的普通话文本翻译成地道的粤语（广东话）。

翻译要求：
1. 使用地道的粤语口语表达，不是简单的字词替换
2. 保留粤语特有的语气词和句式结构（如"嘅"、"咗"、"喺"、"嚟"、"啲"、"佢"、"冇"、"嗰"、"噉"等）
3. 使用常见的粤语书面表达方式
4. 翻译结果应该是香港/广东人日常口语中会说的话
5. 如果原文包含专有名词或技术术语，保持不变
6. 只输出粤语翻译结果，不要添加解释或注释

示例：
- 普通话：你好，今天天气怎么样？ → 粤语：你好，今日天氣點呀？
- 普通话：我不知道他去了哪里。 → 粤语：我唔知佢去咗邊度。
- 普通话：这个东西多少钱？ → 粤语：呢樣嘢幾多錢呀？
- 普通话：我们明天一起去吃饭吧。 → 粤语：我哋聽日一齊去食飯啦。
- 普通话：他说的话我听不懂。 → 粤语：佢講嘅嘢我聽唔明。
- 普通话：别着急，慢慢来。 → 粤语：唔使急，慢慢嚟。"""

USER_PROMPT_TEMPLATE = "请将以下普通话文本翻译成粤语：\n\n{text}"


def build_messages(text: str) -> list:
    """构建翻译请求的消息列表"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=text)},
    ]


def parse_response(response_text: str) -> str:
    """解析翻译响应，清理多余内容"""
    text = response_text.strip()
    # 移除可能的前缀
    for prefix in ["粤语：", "粤语:", "翻译：", "翻译:", "译文：", "译文:"]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    # 移除可能的引号包裹
    if (text.startswith('"') and text.endswith('"')) or \
       (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()
    if (text.startswith('\u201c') and text.endswith('\u201d')) or \
       (text.startswith('\u300c') and text.endswith('\u300d')):
        text = text[1:-1].strip()
    return text
