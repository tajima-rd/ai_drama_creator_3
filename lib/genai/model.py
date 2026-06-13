import mimetypes
import os
from pydantic import BaseModel
from typing import List
from google import genai
from google.genai import types
from enum import Enum
from lib.utils import AudioUtility

class ThinkingLevel(Enum):
    UNSPECIFIED = "THINKING_LEVEL_UNSPECIFIED"
    MINIMAL = "MINIMAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class GenerateTextConfig(BaseModel):
    # Pydanticの定義に則り、型として ThinkingLevel Enum を指定します
    thinking_level: ThinkingLevel = ThinkingLevel.MEDIUM
    top_p: float = 0.95
    top_k: int = 50
    temperature: float = 0.7
    system_instruction: str = ""

    # Pydantic v2 の仕様に基づき、任意の型（Enum等）の扱いを許可
    model_config = {"arbitrary_types_allowed": True}

    def to_gemini_config(self) -> types.GenerateContentConfig:
        # GenerateContentConfig の直下の引数として直接指定します
        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=self.thinking_level.value,
            ),
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            tools=[
                types.Tool(url_context=types.UrlContext()),
            ],
            system_instruction=[
                types.Part.from_text(text=self.system_instruction)
            ]
        )

class GeneratorVoiceConfig(BaseModel):
    temperature: float = 1.0
    response_modalities: List[str] = ["audio"]

    def to_gemini_config(self, voice_name: str) -> types.GenerateContentConfig:
        speech_config = types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        )
        return types.GenerateContentConfig(
            temperature=self.temperature,
            response_modalities=self.response_modalities,
            speech_config=speech_config,
        )

class TtsGenerator:
    def __init__(self, api_key: str, model_name: str = "gemini-3.1-flash-tts-preview", config:GeneratorVoiceConfig=None):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.config = config

    def generate_sound(self, voice_name, prompt: str, working_dir: str) -> List[str]:
        """Generates audio and returns a list of paths to temporary WAV files in the working_dir."""

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        temp_paths = []

        file_index = 0
        for chunk in self.client.models.generate_content_stream(
            model=self.model_name,
            contents=contents,
            config=self.config.to_gemini_config(voice_name=voice_name),
        ):
            if not chunk.parts: continue

            part = chunk.parts[0]
            if part.inline_data:
                data = part.inline_data.data
                mime = part.inline_data.mime_type
                ext = mimetypes.guess_extension(mime) or ".wav"

                if ext == ".wav" and not mime.startswith("audio/wav"):
                    data = AudioUtility.convert_to_wav(data, mime)

                file_name = f"sound_{file_index}{ext}"
                full_path = os.path.join(working_dir, file_name)

                AudioUtility.save_binary_file(full_path, data)
                temp_paths.append(full_path)
                file_index += 1
        return temp_paths        
        
class LlmGenerator:
    def __init__(self, api_key: str, model_name: str = "gemini-3.5-flash", config:GenerateTextConfig=None):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.config = config

    def generate_text(self, prompt_text: str) -> str:
        """
        テキストプロンプトを受け付け、指定された設定（Thinking/Search）の元で
        ストリーミング生成を行い、最終結果の文字列を返します。
        """
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt_text)],
            ),
        ]
        
        full_response = []
        
        for chunk in self.client.models.generate_content_stream(
            model=self.model_name,
            contents=contents,
            config=self.config.to_gemini_config(),
        ):
            if chunk.text:
                full_response.append(chunk.text)
                
        print() # 改行用
        return "".join(full_response)

