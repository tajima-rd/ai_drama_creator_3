import mimetypes
import os
from pydantic import BaseModel
from typing import List
from google import genai
from google.genai import types
from enum import Enum
from utils import AudioUtility
from drama import Scene, AudioPrompt
import tempfile
from pydub import AudioSegment

class ThinkingLevel(Enum):
    UNSPECIFIED = "THINKING_LEVEL_UNSPECIFIED"
    MINIMAL = "MINIMAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

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
    def __init__(self, api_key: str, output_dir: str, model_name: str = "gemini-3.1-flash-tts-preview"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.output_dir = output_dir

    def generate_prompt(self, prompt: AudioPrompt, config: GeneratorVoiceConfig, output_prefix: str, working_dir: str) -> List[str]:
        """Generates audio and returns a list of paths to temporary WAV files in the working_dir."""
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt.build_prompt())])]
        temp_paths = []

        file_index = 0
        for chunk in self.client.models.generate_content_stream(
            model=self.model_name,
            contents=contents,
            config=config.to_gemini_config(voice_name=prompt.actor.voice_name),
        ):
            if not chunk.parts: continue

            part = chunk.parts[0]
            if part.inline_data:
                data = part.inline_data.data
                mime = part.inline_data.mime_type
                ext = mimetypes.guess_extension(mime) or ".wav"

                if ext == ".wav" and not mime.startswith("audio/wav"):
                    data = AudioUtility.convert_to_wav(data, mime)

                file_name = f"{output_prefix}_{file_index}{ext}"
                full_path = os.path.join(working_dir, file_name)

                AudioUtility.save_binary_file(full_path, data)
                temp_paths.append(full_path)
                file_index += 1

        return temp_paths

    def run_scene(self, scene: Scene, config: GeneratorVoiceConfig):
        print(f"Starting Scene [{scene.scene_id}]: {scene.title}")

        # Create a temporary directory for the intermediate segments
        with tempfile.TemporaryDirectory() as tmp_dir:
            print(f"Created temporary workspace: {tmp_dir}")
            combined_audio = AudioSegment.empty()

            sorted_prompts = sorted(scene.prompts, key=lambda p: p.order)

            for prompt in sorted_prompts:
                prefix = f"segment_{scene.scene_id}_{prompt.order}"
                # Generate segments inside the temporary directory
                paths = self.generate_prompt(prompt, config, output_prefix=prefix, working_dir=tmp_dir)

                # Load and concatenate segments
                for path in paths:
                    segment = AudioSegment.from_wav(path)
                    combined_audio += segment

            # Export final combined MP3 to the main output directory
            final_filename = f"{scene.scene_id}_final.mp3"
            final_path = os.path.join(self.output_dir, final_filename)
            combined_audio.export(final_path, format="mp3")
            print(f"\nSUCCESS: Final combined audio saved to: {final_path}")

        print("Cleanup complete: Temporary directory and WAV segments removed automatically.")

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
class LlmGenerator:
    def __init__(self, api_key: str, model_name: str = "gemini-3.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def generate_text(self, prompt_text: str, config: GenerateTextConfig) -> str:
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
            config=config.to_gemini_config(),
        ):
            if chunk.text:
                print(chunk.text, end="", flush=True)
                full_response.append(chunk.text)
                
        print() # 改行用
        return "".join(full_response)