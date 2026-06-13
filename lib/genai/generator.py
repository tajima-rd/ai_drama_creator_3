from lib.schema.drama import Scene, Transcript
from lib.schema.prompt import (
    Prompt, 
    Section, 
    TextBlock, 
    BulletInstruction, 
    StepInstruction, 
    MandatoryRule, 
    ForbiddenRule, 
    OutputFormat
)

# ※もし既存のクラス（例: ScriptManagerなど）のメソッドにする場合は、引数に `self` を含めてください。
def generate_sound_drama_prompt(transcript: Transcript) -> str:
    """
    prompt.py のコンポーネント指向設計に基づき、
    オーディオプロファイルとディレクション指示のプロンプトを動的に構造化して生成します。
    """
    # -----------------------------------------------------------------
    # 1. 前処理（動的な文字列の制御）
    # -----------------------------------------------------------------
    # Personality Description
    pers_desc = transcript.actor.personality_description if transcript.actor.personality_description else ""
    
    # Style / Dynamics のリスト構築
    style_items = [transcript.directors_note.style]
    if transcript.directors_note.dynamics:
        style_items.append(f"Dynamics: {transcript.directors_note.dynamics}")
        
    # Pace と Accent のテキストブロック化
    pace_text = f"Pace: {transcript.directors_note.pace}"
    accent_text = f"Accent: {transcript.actor.accent}"

    # -----------------------------------------------------------------
    # 2. コンポーネントツリーの構築
    # -----------------------------------------------------------------
    prompt_instance = Prompt(components=[
        
        # ## "パーソナリティタイトル" と説明
        Section(title=f"AUDIO PROFILE: {transcript.actor.character_name}", children=[
            Section(title=f'"{transcript.actor.personality_title}"', children=[
                TextBlock(pers_desc)
            ]) if pers_desc else TextBlock(f'"{transcript.actor.personality_title}"')
        ]),

        # 場面設定
        Section(title=f"THE SCENE: {transcript.context}", children=[
            TextBlock(transcript.scene_description)
        ]),

        # ディレクターズノート
        Section(title="DIRECTOR'S NOTES", children=[
            Section(title="Style", children=[
                BulletInstruction(items=style_items)
            ]),
            TextBlock(pace_text),
            TextBlock(accent_text),
            
            # 実際の原稿・セリフ
            Section(title="TRANSCRIPT", children=[
                TextBlock(transcript.text)
            ])
        ])
    ])

    # 完全に構造化されたマークダウン文字列を返却
    return prompt_instance.to_text()

def generate_transcript_prompt(scene_id, character_map: list[list[str]], dialog: str) -> str:
    """
    引数のキャラクターマップ（任意の人数）と原稿テキストを組み込み、
    完全にコンポーネント指向で構造化されたプロンプト文字列を生成して返却する。
    """

    role_desc = (
        "あなたは優秀な音声ドラマのディレクターであり、スクリプトエディターです。\n"
        "提供された日本語の対話原稿を分析し、指定されたYAMLフォーマットに完全に変換して出力してください。"
    )

    yaml_template = (
        f"scene_id: \"{scene_id}\"\n"
        "title: \"Impressions of the Inn and the Multitalented Owner\"\n"
        "transcripts:\n"
        "  - actor_name: \"actor_name\"\n"
        "    context: \"Outside the hotel entrance, looking at the snowy landscape, daytime.\"\n"
        "    scene: \"actor_name_1 looks around the white world with excitement and turns to actor_name_2.\"\n"
        "    directors_note:\n"
        "      style: \"Bright, enthusiastic, and loving tone\"\n"
        "      pace: \"Moderate\"\n"
        "    text: \"[excited] ねえ喜一くん、あらためて宿の玄関を出て...（以下、感情タグを交えたセリフ）\"\n"
        "    order: 1"
    )

    # キャラクターマッピングの動的生成
    mapping_lines = []

    # zipは使わず、リストから直接 [input_name, actor_name] を分解して取り出す
    for input_name, actor_name in character_map:
        mapping_lines.append(f"「{input_name}」 ➡ actor_name: \"{actor_name}\"")

    # プロンプトツリーの構築（ご提示いただいた理想的な構造）
    prompt_instance = Prompt(components=[
        
        Section(title="システム定義", children=[
            Section(title="役割", children=[
                TextBlock(role_desc)
            ]),
            Section(title="出力仕様と絶対ルール", children=[
                MandatoryRule(
                    BulletInstruction(items=[
                        "出力は、必ずマークダウンのコードブロック（```yaml から ``` まで）の中にすべて含めてください。",
                        "完全なYAMLのみを出力してください。"
                    ])
                ),
                ForbiddenRule(
                    BulletInstruction(items=[
                        "コードブロックの前後には、挨拶、解説、説明などの余計なテキストを一切出力しないでください。"
                    ])
                ),
                OutputFormat(format_type="YAML", template=yaml_template)
            ])
        ]),

        Section(title="変換・演出ルール", children=[
            StepInstruction(steps=[
                f"キャラクターのマッピング:\n   原稿の登場人物を、以下のように機械的に置き換えてください。\n" + "\n".join([f"   - {line}" for line in mapping_lines]),
                "音声感情タグの挿入:\n   セリフ（transcript）の適切だと思う場所（文頭や文末、感情の変化点）に、以下のタグを必ず散りばめてください。\n   [amazed], [crying], [curious], [excited], [sighs], [gasp], [giggles], [laughs], [mischievously], [panicked], [sarcastic], [serious], [shouting], [tired], [trembling], [whispers], [very_fast], [very_slow]\n   ※1つのセリフに複数入れても構いません。",
                "演出指示（directors_note / scene）の補完:\n   原稿のトーンやセリフの内容から読み取れる「場所・状況（context）」「動き（scene）」「話し方（style）」「速度（pace: Moderate/Fast/Slow）」を推測し、英語で具体的に記述してください。",
                "順序（order）:\n   1 から始まる連番にしてください。"
            ])
        ]),

        Section(title="入力データ", children=[
            Section(title="変換対象の原稿", children=[
                TextBlock(dialog)
            ])
        ])
    ])

    return prompt_instance.to_text()

def generate_dialogue_prompt(synopsis_text: str, profiles: list[list[str]], num_char: int = 350) -> str:

    profile_blocks = []

    # zipは使わず、リストから直接 [input_name, actor_name] を分解して取り出す
    for character, profile in profiles:
        profile_blocks.append(TextBlock(f"[{character}]:```\n{profile}\n```"))


    # 1. 役割の定義
    role_desc = (
        "与えられた[登場人物のキャラクタープロファイル]と[あらすじ]からキャラクター同士の自然な掛け合い（セリフ）を創作するシナリオライターです。\n"
        "AI Studioなどでそのまま再生・流し込みができるよう、完全にセリフテキストのみで構成された美しい会話劇を出力してください。"
    )

    # 2. 期待する出力フォーマットのテンプレート
    output_template = (
        'キャラクターA：セリフ。\n'
        'キャラクターB：セリフ。\n'
        'キャラクターA：セリフ。\n'
        '※「キャラクター名：」で始まり、セリフが続く形式を維持してください。'
    )

    # 3. コンポーネントツリーの構築 (prompt.py の仕様に完全準拠)
    prompt_instance = Prompt(
        components=[
            # --- 第1セクション: システム定義 ---
            Section(
                title="システム定義",
                children=[
                    Section(title="役割", children=[TextBlock(role_desc)]),
                    Section(
                        title="出力仕様と絶対ルール",
                        children=[
                            # 絶対に守らせたいルール群
                            MandatoryRule(
                                BulletInstruction(
                                    items=[
                                        "ストーリーの主軸は「あらすじ」にしたがってください。別の話は混ぜないでください。",
                                        "「ト書き」「状況説明」「(ため息をつく)」などのカッコ書きのアクションは、一切出力しないでください。",
                                        "出力は、完全に「キャラクター名：セリフ」の形式のみとしてください。",
                                        "空行（改行）を適度に入れ、読みやすい会話劇にしてください。",
                                        "与えられた「登場人物のキャラクタープロファイル」を元に、セリフの口調に深く反映させてください。",
                                        f"文字数は全体で{num_char}文字となるように出力してください。"
                                    ]
                                )
                            ),
                            # 絶対にやらせたくないルール群
                            ForbiddenRule(
                                BulletInstruction(
                                    items=[
                                        "セリフの前後や、出力の冒頭・末尾に、挨拶、解説、補足説明などの余計なテキストを絶対に含めないでください。",
                                        "「登場人物のキャラクタープロファイル」はあくまで、登場人物の背景設定です。「あらすじ」に混ぜないでください。"
                                    ]
                                )
                            ),
                            # 出力フォーマットの明示
                            OutputFormat(
                                format_type="text", template=output_template
                            ),
                        ],
                    ),
                ],
            ),
            # --- 第2セクション: 入力データ ---
            Section(
                title="入力データ",
                children=[
                    Section(
                        title="変換対象のあらすじ",
                        children=[TextBlock(synopsis_text)],
                    ),
                    Section(
                        title="登場人物のキャラクタープロファイル",
                        children=profile_blocks
                    )
                ],
            ),
        ]
    )

    # 構造化されたプロンプトテキストを返却
    return prompt_instance.to_text()