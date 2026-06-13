import os
import re
import yaml
import tempfile

from pydub import AudioSegment

from lib.schema import Project, Scene
from lib.genai import (
     generate_sound_drama_prompt,
     generate_dialogue_prompt,
     generate_transcript_prompt
)

def generate_sound_drama(project: Project, scene: Scene):
    print(f"Starting Scene [{scene.scene_id}]: {scene.title}")

    sound_dir = project.get_working_path("sound_path")
    final_filename = f"{scene.scene_id}.mp3"
    final_path = os.path.join(sound_dir, final_filename)

    with tempfile.TemporaryDirectory() as tmp_dir:
        print(f"Created temporary workspace: {tmp_dir}")
        combined_audio = AudioSegment.empty()

        sorted_transcript = sorted(scene.transcript, key=lambda p: p.order)

        for transcript in sorted_transcript:
            prefix = f"segment_{scene.scene_id}_{transcript.order}"
            voice_name = transcript.actor.voice_name
            prompt = generate_sound_drama_prompt(transcript)
            
            # Generate segments inside the temporary directory
            paths = project.tts_gen.generate_sound(voice_name=voice_name, prompt=prompt, working_dir=tmp_dir)

            # Load and concatenate segments
            for path in paths:
                segment = AudioSegment.from_wav(path)
                combined_audio += segment

        print(f"\nSUCCESS: Final combined audio saved to: {final_path}")
        combined_audio.export(final_path, format="mp3")

        print("Cleanup complete: Temporary directory and WAV segments removed automatically.")

def generate_dialogue(project, synopsis, profiles, output_file, num_char=350):
    prompt = generate_dialogue_prompt(synopsis, profiles, num_char=num_char)

    response_text = project.llm_gen.generate_text(prompt_text=prompt)

    with open(output_file, "w") as f:
            f.write(response_text)

def generate_scene(project, scene_id, dialog, output_file):
    character_map = project.get_character_map()
    
    prompt = generate_transcript_prompt(scene_id=scene_id, character_map=character_map, dialog=dialog)

    response_text = project.llm_gen.generate_text(prompt)
    cleaned_text = re.sub(
        r"^```yaml\s*$\n|^```\s*$\n?", "", response_text, flags=re.MULTILINE
    )

    with open(output_file, "w") as f:
            f.write(cleaned_text)

    project.load_scenes_yaml(yaml.safe_load(cleaned_text))

    print(f"Scene {scene_id} generated successfully.")