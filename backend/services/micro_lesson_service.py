"""Reusable deterministic micro lesson helpers."""

from __future__ import annotations

from typing import cast

from models import (
    ComicPanel,
    FillBlankQuestion,
    LearningPlan,
    MicroDialogueLine,
    MicroLesson,
    MicroVocabularyItem,
)


def learning_plan_from_state(state: dict) -> LearningPlan:
    return LearningPlan(
        estimated_total_days=int(state["estimated_total_days"]),
        current_day=int(state["current_day"]),
        summary_zh=str(state["summary_zh"]),
    )


def _vocab(word: str, phonetic: str, pronunciation: str, definition: str, example: str, example_translation: str) -> MicroVocabularyItem:
    return MicroVocabularyItem(
        word=word,
        phonetic=phonetic,
        pronunciation_zh=pronunciation,
        definition_zh=definition,
        example_sentence=example,
        example_translation=example_translation,
    )


MICRO_LESSON_TEMPLATES: list[dict[str, object]] = [
    {
        "theme": "subject/verb/object",
        "sentence": "We raise prices today.",
        "translation_zh": "我們今天調高價格。",
        "subject_text": "We",
        "verb_text": "raise",
        "object_text": "prices",
        "grammar_note": "英文商務短句常用「主詞 + 動詞 + 受詞」：We 是主詞，raise 是動詞，prices 是受詞。",
        "toeic_usage_note": "TOEIC 通知常看到 raise prices（調高價格）、raise questions（提出問題）、raise concerns（提出疑慮）。",
        "blank": "We ___ prices today.",
        "choices": ["raise", "raises", "raising"],
        "answer": "raise",
        "words": [
            ("raise", "/reɪz/", "雷茲", "提高；調高", "We raise prices today.", "我們今天調高價格。"),
            ("price", "/praɪs/", "普賴斯", "價格", "The price is high.", "價格很高。"),
            ("today", "/təˈdeɪ/", "特 Day", "今天", "We meet today.", "我們今天見面。"),
            ("customer", "/ˈkʌstəmər/", "卡斯特默", "顧客", "Customers need help.", "顧客需要協助。"),
            ("report", "/rɪˈpɔːrt/", "瑞破特", "報告", "I read the report.", "我閱讀那份報告。"),
        ],
    },
    {
        "theme": "present simple",
        "sentence": "She checks email every morning.",
        "translation_zh": "她每天早上查看電子郵件。",
        "subject_text": "She",
        "verb_text": "checks",
        "object_text": "email",
        "grammar_note": "描述每天、每週會做的例行事情時，用現在簡單式。主詞是 he/she/it 時，動詞通常加 -s 或 -es。",
        "toeic_usage_note": "TOEIC 常用現在簡單式描述工作習慣，例如 checks email（查看郵件）或 sends reports（寄報告）。",
        "blank": "She ___ email every morning.",
        "choices": ["checks", "check", "checking"],
        "answer": "checks",
        "words": [
            ("check", "/tʃek/", "切克", "檢查；查看", "She checks email every morning.", "她每天早上查看電子郵件。"),
            ("email", "/ˈiːmeɪl/", "伊妹兒", "電子郵件", "I send an email.", "我寄一封電子郵件。"),
            ("morning", "/ˈmɔːrnɪŋ/", "摩寧", "早上", "The meeting is in the morning.", "會議在早上。"),
            ("routine", "/ruːˈtiːn/", "如 Teen", "例行習慣", "This is my routine.", "這是我的例行習慣。"),
            ("desk", "/desk/", "戴斯克", "書桌；辦公桌", "The file is on the desk.", "檔案在桌上。"),
        ],
    },
    {
        "theme": "be verb",
        "sentence": "The report is ready.",
        "translation_zh": "報告準備好了。",
        "subject_text": "The report",
        "verb_text": "is",
        "object_text": "ready",
        "grammar_note": "be 動詞可以連接主詞和狀態。The report 是主詞，is 表示「是／處於」，ready 是狀態。",
        "toeic_usage_note": "辦公室通知常說 a report is ready（報告好了）或 a room is available（會議室可用）。",
        "blank": "The report ___ ready.",
        "choices": ["is", "are", "be"],
        "answer": "is",
        "words": [
            ("report", "/rɪˈpɔːrt/", "瑞破特", "報告", "The report is ready.", "報告準備好了。"),
            ("ready", "/ˈredi/", "瑞迪", "準備好的", "The room is ready.", "房間準備好了。"),
            ("available", "/əˈveɪləbəl/", "阿 Vei 了薄", "可用的；有空的", "The manager is available.", "經理現在有空。"),
            ("room", "/ruːm/", "如姆", "房間；會議室", "The room is quiet.", "房間很安靜。"),
            ("file", "/faɪl/", "發イル", "檔案", "The file is ready.", "檔案準備好了。"),
        ],
    },
    {
        "theme": "noun phrase",
        "sentence": "The new invoice needs approval.",
        "translation_zh": "新的發票需要核准。",
        "subject_text": "The new invoice",
        "verb_text": "needs",
        "object_text": "approval",
        "grammar_note": "名詞片語可以把形容詞放在主要名詞前面。The new invoice 整組都是主詞。",
        "toeic_usage_note": "TOEIC 郵件常寫 invoice needs approval（發票需要核准）或 request needs approval（請求需要核准）。",
        "blank": "The new invoice ___ approval.",
        "choices": ["needs", "need", "needing"],
        "answer": "needs",
        "words": [
            ("invoice", "/ˈɪnvɔɪs/", "因 Voice", "發票；請款單", "The invoice needs approval.", "發票需要核准。"),
            ("approval", "/əˈpruːvəl/", "阿普魯佛", "核准；同意", "We need approval today.", "我們今天需要核准。"),
            ("new", "/nuː/", "努", "新的", "This is a new form.", "這是一份新表格。"),
            ("form", "/fɔːrm/", "佛姆", "表格", "Please sign the form.", "請簽這份表格。"),
            ("request", "/rɪˈkwest/", "瑞 Quest", "請求；申請", "The request is urgent.", "這項請求很緊急。"),
        ],
    },
    {
        "theme": "TOEIC email sentence",
        "sentence": "Please confirm the meeting time.",
        "translation_zh": "請確認會議時間。",
        "subject_text": "(you)",
        "verb_text": "confirm",
        "object_text": "the meeting time",
        "grammar_note": "這是祈使句，真正的主詞省略了，可以理解成 you。「Please」是禮貌標記，不是主詞。",
        "toeic_usage_note": "TOEIC 郵件常用 Please + 原形動詞，請讀者 confirm（確認）、review（檢查）或 attach（附上）資料。",
        "blank": "Please ___ the meeting time.",
        "choices": ["confirm", "confirms", "confirmed"],
        "answer": "confirm",
        "words": [
            ("confirm", "/kənˈfɜːrm/", "肯 Ferm", "確認", "Please confirm the meeting time.", "請確認會議時間。"),
            ("meeting", "/ˈmiːtɪŋ/", "米 Ting", "會議", "The meeting starts at ten.", "會議十點開始。"),
            ("time", "/taɪm/", "泰姆", "時間", "What time is the call?", "電話會議是幾點？"),
            ("attach", "/əˈtætʃ/", "阿 Ta 奇", "附上；附加", "Please attach the file.", "請附上檔案。"),
            ("review", "/rɪˈvjuː/", "瑞 View", "檢查；複習", "Please review the note.", "請檢查這則備註。"),
        ],
    },
    {
        "theme": "business phone sentence",
        "sentence": "May I speak with Anna?",
        "translation_zh": "我可以和 Anna 說話嗎？",
        "subject_text": "I",
        "verb_text": "speak",
        "object_text": "with Anna",
        "grammar_note": "May I + 原形動詞是禮貌問法，常用來請求允許。",
        "toeic_usage_note": "TOEIC 電話情境常出現 May I speak with...?（我可以和……說話嗎？）。",
        "blank": "May I ___ with Anna?",
        "choices": ["speak", "speaks", "speaking"],
        "answer": "speak",
        "words": [
            ("speak", "/spiːk/", "斯匹克", "說話", "May I speak with Anna?", "我可以和 Anna 說話嗎？"),
            ("call", "/kɔːl/", "摳", "電話；通話", "I have a call.", "我有一通電話。"),
            ("message", "/ˈmesɪdʒ/", "妹 Sidj", "訊息；留言", "Please leave a message.", "請留訊息。"),
            ("available", "/əˈveɪləbəl/", "阿 Vei 了薄", "有空的", "Anna is available now.", "Anna 現在有空。"),
            ("phone", "/foʊn/", "風", "電話", "The phone is ringing.", "電話正在響。"),
        ],
    },
    {
        "theme": "review day",
        "sentence": "We review one sentence again.",
        "translation_zh": "我們再複習一個句子。",
        "subject_text": "We",
        "verb_text": "review",
        "object_text": "one sentence",
        "grammar_note": "複習日會重複舊句型，讓你看到主詞、動詞、受詞時更快反應。",
        "toeic_usage_note": "短複習可以加強 TOEIC 常見的 email、phone、office 句型。",
        "blank": "We ___ one sentence again.",
        "choices": ["review", "reviews", "reviewing"],
        "answer": "review",
        "words": [
            ("review", "/rɪˈvjuː/", "瑞 View", "複習；檢查", "We review one sentence again.", "我們再複習一個句子。"),
            ("sentence", "/ˈsentəns/", "森 Ten 斯", "句子", "This sentence is useful.", "這個句子很實用。"),
            ("again", "/əˈɡen/", "阿 Gen", "再一次", "Please say it again.", "請再說一次。"),
            ("practice", "/ˈpræktɪs/", "普 Rack 提斯", "練習", "Practice every day.", "每天練習。"),
            ("goal", "/ɡoʊl/", "勾歐", "目標", "My goal is clear.", "我的目標很清楚。"),
        ],
    },
]


def build_micro_lesson(day_index: int, total_days: int) -> MicroLesson:
    template = MICRO_LESSON_TEMPLATES[(day_index - 1) % len(MICRO_LESSON_TEMPLATES)]
    template_words = cast(list[tuple[str, str, str, str, str, str]], template["words"])
    template_choices = cast(list[str], template["choices"])
    sentence = str(template["sentence"])
    words = [
        _vocab(str(word), str(phonetic), str(pronunciation), str(definition), str(example), str(example_translation))
        for word, phonetic, pronunciation, definition, example, example_translation in template_words
    ]

    return MicroLesson(
        day_index=day_index,
        total_days=total_days,
        target_exam="TOEIC 600",
        sentence=sentence,
        translation_zh=str(template["translation_zh"]),
        subject_text=str(template["subject_text"]),
        verb_text=str(template["verb_text"]),
        object_text=str(template["object_text"]),
        reading_order_steps=[
            f"先找主詞：{template['subject_text']}。",
            f"再找動詞：{template['verb_text']}。",
            f"最後找受詞或補語：{template['object_text']}。",
        ],
        grammar_note=str(template["grammar_note"]),
        toeic_usage_note=str(template["toeic_usage_note"]),
        vocabulary_items=words,
        dialogue_lines=[
            MicroDialogueLine(speaker="A", english=sentence, translation_zh=str(template["translation_zh"])),
            MicroDialogueLine(speaker="B", english="Good. Please say it again.", translation_zh="很好。請再說一次。"),
        ],
        reading_passage=(
            "A learner reads one short sentence. "
            f"The coach asks for the subject, verb, and object: {sentence} "
            "中文提示：先看誰做動作，再看動作，最後看動作影響誰或什麼。"
        ),
        comic_panels=[
            ComicPanel(
                panel=1,
                english=f"Day {day_index}: {template['theme']}",
                translation_zh=f"第 {day_index} 天：每日短課",
                scene_prompt="A friendly coach showing a sentence card.",
            ),
            ComicPanel(
                panel=2,
                english=f"Subject: {template['subject_text']}",
                translation_zh=f"主詞：{template['subject_text']}",
                scene_prompt="Highlight the subject phrase.",
            ),
            ComicPanel(
                panel=3,
                english=f"Verb: {template['verb_text']}",
                translation_zh=f"動詞：{template['verb_text']}",
                scene_prompt="Highlight the verb.",
            ),
            ComicPanel(
                panel=4,
                english=sentence,
                translation_zh=str(template["translation_zh"]),
                scene_prompt="Learner reading the full sentence.",
            ),
        ],
        fill_blank_question=FillBlankQuestion(
            prompt=str(template["blank"]),
            choices=[str(choice) for choice in template_choices],
            correct_answer=str(template["answer"]),
            explanation=str(template["grammar_note"]),
        ),
    )
