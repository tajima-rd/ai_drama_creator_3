# -*- coding: utf-8 -*-
import os
import yaml
import re

from lib.schema.project import Project
from lib.genai import (
    LlmGenerator, 
    TtsGenerator, 
    GenerateTextConfig, 
    GeneratorVoiceConfig
)
from lib.function import (
    generate_dialogue, 
    generate_scene, 
    generate_sound_drama
)

# --- Project Setup ---
ROOT_DIR = "/home/yufujimoto/Git/ai_drama_creator_3"

class MainWindow():
    def __init__(self, project: Project):
        self.project = project
    
    def generate_all_dialogues(self):
        character_dir = self.project.get_working_path("character_path")
        profiles = []

        for character_file in sorted(os.listdir(character_dir)):
            character_path = os.path.join(character_dir, character_file)
            file_name = os.path.basename(character_file)
            label, _ = os.path.splitext(file_name)

            with open(character_path, "r", encoding="utf-8") as f:
                    profile = f.read()
            profiles.append([label, profile])

        ### Generate Dialogues
        plot_dir = self.project.get_working_path("plot_path")
        script_dir = self.project.get_working_path("script_path")

        count = 0

        for plot_file in sorted(os.listdir(plot_dir)):
            script_id = f"script_{count:03}"

            script_path = os.path.join(plot_dir, plot_file)
            output_path = os.path.join(script_dir, script_id + ".yaml")

            with open(script_path, "r", encoding="utf-8") as f:
                synoposis = f.read() 
            
            num_char = int(len(synoposis) * 2)

            generate_dialogue(project=self.project, synopsis=synoposis, profiles=profiles, output_file=output_path, num_char=num_char)

            print(f"{script_id} generated")

            count += 1
    
    def generate_all_scenes(self):
        ### Generate Scenes
        script_dir = self.project.get_working_path("script_path")
        scene_dir = self.project.get_working_path("scene_path")
        count = 0

        for script_file in sorted(os.listdir(script_dir)):
            scene_id = scene_id=f"scene_{count:03}"

            script_path = os.path.join(script_dir, script_file)
            output_scene_path = os.path.join(scene_dir, scene_id + ".yaml")

            with open(script_path, "r", encoding="utf-8") as f:
                dialog = f.read()
            
            generate_scene(project=self.project, scene_id=scene_id, dialog=dialog, output_file=output_scene_path)

            print(f"Generated scene {scene_id} from script file")

            count += 1

    def generate_all_sound(self):
         for scene in self.project.acts:
              generate_sound_drama(self.project, self.project.acts[scene])

              print(f"Generated sound for scene {self.project.acts[scene].title}")

def main():
    # Gemini APIキーの取得
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # プロジェクト構造の初期化
    project = Project(
        root_dir=ROOT_DIR, 
        api_key=api_key
    )

    # AIモデルの設定
    llm_config = GenerateTextConfig(
        thinking_level="MEDIUM", 
        temperature=0.7,
        system_instruction="あなたは優秀な音声ドラマの演出家です。簡潔に回答してください。"
    )
    tts_config = GeneratorVoiceConfig(
        temperature=1.0
    )

    project.llm_gen = LlmGenerator(api_key=api_key, config=llm_config)
    project.tts_gen = TtsGenerator(api_key=api_key, config=tts_config)
    
    app = MainWindow(project)

    print(app.project.acts)

    # app.generate_all_dialogues()
    # app.generate_all_scenes()
    # app.generate_all_sound()

    
    generate_sound_drama(app.project, app.project.acts["scene_000"])

# --- Execution Block ---
if __name__ == "__main__":
    main()
    
    # project.tts_gen.run_scene(scene=my_scene, config=project.tts_config)