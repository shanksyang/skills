"""腾讯云 TTS 引擎插件"""

import base64
import json
from pathlib import Path

from ..base import TTSEngine, TTSResult
from ..registry import register_tts_engine

# 腾讯云粤语音色
CANTONESE_VOICES = {
    101019: "智彤（粤语女声）",
}

DEFAULT_VOICE_TYPE = 101019


@register_tts_engine("tencent")
class TencentTTSEngine(TTSEngine):
    """使用腾讯云语音合成进行粤语语音合成"""

    def __init__(self, secret_id: str = "", secret_key: str = "",
                 voice_type: int = 0, region: str = "ap-guangzhou",
                 sample_rate: int = 16000, codec: str = "mp3", **kwargs):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.voice_type = voice_type or DEFAULT_VOICE_TYPE
        self.region = region
        self.sample_rate = sample_rate
        self.codec = codec

    def synthesize(self, text: str, output_path: Path) -> TTSResult:
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.tts.v20190823 import tts_client, models

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cred = credential.Credential(self.secret_id, self.secret_key)
        http_profile = HttpProfile()
        http_profile.endpoint = "tts.tencentcloudapi.com"
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        client = tts_client.TtsClient(cred, self.region, client_profile)

        req = models.TextToVoiceRequest()
        req.Text = text
        req.SessionId = f"cantonese-tts-{hash(text) & 0xFFFFFFFF:08x}"
        req.Volume = 5
        req.Speed = 0
        req.VoiceType = self.voice_type
        req.PrimaryLanguage = 1  # 中文
        req.SampleRate = self.sample_rate
        req.Codec = self.codec
        req.ModelType = 1

        resp = client.TextToVoice(req)

        # 解码音频数据并写入文件
        audio_data = base64.b64decode(resp.Audio)
        with open(output_path, "wb") as f:
            f.write(audio_data)

        voice_desc = CANTONESE_VOICES.get(self.voice_type, f"VoiceType={self.voice_type}")

        return TTSResult(
            text=text,
            audio_path=output_path,
            engine_name="tencent-tts",
            voice_name=f"{self.voice_type} ({voice_desc})",
            format=self.codec,
        )

    def validate(self) -> bool:
        if not self.secret_id or not self.secret_key:
            return False
        try:
            from tencentcloud.tts.v20190823 import tts_client
            return True
        except ImportError:
            return False

    def list_voices(self) -> list:
        return [
            {"id": k, "name": v, "gender": "Female"}
            for k, v in CANTONESE_VOICES.items()
        ]
