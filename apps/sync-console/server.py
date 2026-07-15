#!/usr/bin/env python3
"""Local API for the Hunter66 WeChat learning-memory sync console."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import random
import ssl
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / "private" / "sync-console"
LEARNING_STATE = ROOT / "data" / "learning-state"
REFERENCE_DATA = ROOT / "data" / "reference"
RAW = ROOT / "data" / "raw-inputs" / "wechat"
QQ_RAW = ROOT / "data" / "raw-inputs" / "qq"
REQUIREMENTS = ROOT / "data" / "teacher-requirements"
STATE = PRIVATE / "state.json"
VOICE_REMINDERS = PRIVATE / "voice-reminders"
WORD_AUDIO = PRIVATE / "word-audio"
QQ_LOGIN_QR = PRIVATE / "qq-login-qr.png"
VOCABULARY = LEARNING_STATE / "english-vocabulary.json"
KET_VOCABULARY = REFERENCE_DATA / "ket-a2-vocabulary.json"
KET_DETAILS = PRIVATE / "english" / "ket-word-details.json"
GROUP = "六六班级"
QQ_GROUP = "2024级二（7）班（乐知班）"
QQ_GROUP_CODE = "948770145"
QQ_API = "http://127.0.0.1:40653"
QQ_CONTAINER = "napcat-qce"
DOCKER = Path("/usr/local/bin/docker")
APP = Path(__file__).resolve().parent
LAUNCH_AGENT = Path.home() / "Library" / "LaunchAgents" / "com.xiafelex.hunter66-wechat-sync.plist"
WECHAT_EXPORT = Path.home() / "Library" / "Application Support" / "Hunter66" / "wechat-export-local"
NATIVE_AGENT = Path.home() / "Library" / "Application Support" / "Hunter66" / "Hunter66SyncAgent.app" / "Contents" / "MacOS" / "Hunter66SyncAgent"
WECHAT_CLI = Path.home() / ".local" / "bin" / "wechat-cli"
WECHAT_CLI_CONFIG = Path.home() / ".config" / "wxcli" / "config.json"
EDGE_TTS = APP / ".venv" / "bin" / "edge-tts"
TEACHERS = {
    "蔡老师": {"subject": "语文", "aliases": ("蔡老师", "西瓜瓜西", "语文-蔡老师")},
    "刘老师": {"subject": "数学", "aliases": ("易歆", "数学-刘老师", "刘老师")},
    "卢老师": {"subject": "英语", "aliases": ("Elaine", "英语-卢老师", "卢老师")},
    "宋老师": {"subject": "生活", "aliases": ("生活-宋老师", "宋老师")},
    "程老师": {"subject": "科学", "aliases": ("科学-程", "程老师")},
    "高老师": {"subject": "体育", "aliases": ("体育-高老师", "高老师")},
}

TEACHER_WORDS = ("请", "家长", "提醒", "要求", "务必", "注意", "提交", "带", "准备")
HOMEWORK_WORDS = ("作业", "完成", "练习", "订正", "背诵", "默写", "预习")
EXAM_WORDS = ("考试", "测验", "单元", "复习", "检测")
PRAISE_WORDS = ("表扬", "最佳", "最棒", "最投入", "最用心", "优秀", "点赞")
PRAISE_STOP_WORDS = {"以上", "小朋友", "今天", "本周", "同学们", "全员", "四位", "两位", "这位", "优秀", "内容", "表达", "认真", "能够", "学习", "同伴", "分享", "字音", "字形", "字形时", "听写", "笔记", "基础"}
KNOWLEDGE_TOPICS = {
    "作业完成": ("作业", "完成", "练习", "订正"),
    "朗读背诵": ("朗读", "背诵", "诵读", "古诗"),
    "预习复习": ("预习", "复习", "单元", "测验"),
    "提交反馈": ("提交", "上传", "打卡", "反馈", "发到"),
    "家长协作": ("家长", "陪伴", "监督", "提醒"),
    "物品准备": ("带", "准备", "材料", "练习册"),
    "阅读积累": ("阅读", "书香", "积累", "读书"),
    "安全与习惯": ("安全", "注意", "非必要", "健康"),
}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def default_state() -> dict[str, Any]:
    return {
        "automation": False,
        "automation_time": "18:30",
        "voice_reminders_enabled": True,
        "voice_reminders": [],
        "last_sync": None,
        "last_result": {"captured": 0, "saved": 0, "duplicates": 0, "duration": "—"},
        "history": [],
        "seen": [],
    }


def load_state() -> dict[str, Any]:
    if not STATE.exists():
        return default_state()
    try:
        return {**default_state(), **json.loads(STATE.read_text(encoding="utf-8"))}
    except (OSError, json.JSONDecodeError):
        return default_state()


def save_state(state: dict[str, Any]) -> None:
    PRIVATE.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_vocabulary() -> list[dict[str, Any]]:
    if not VOCABULARY.exists():
        return []
    try:
        payload = json.loads(VOCABULARY.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save_vocabulary(words: list[dict[str, Any]]) -> None:
    PRIVATE.mkdir(parents=True, exist_ok=True)
    VOCABULARY.write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")


def today() -> str:
    return datetime.now().astimezone().date().isoformat()


def vocabulary_summary(words: list[dict[str, Any]]) -> dict[str, Any]:
    current_day = today()
    due = [word for word in words if word.get("next_review", current_day) <= current_day]
    difficult = sorted(words, key=lambda word: (-int(word.get("mistake_count", 0)), word.get("word", "")))[:8]
    return {
        "total": len(words),
        "due_count": len(due),
        "mastered_count": sum(int(word.get("mastery_level", 0)) >= 4 for word in words),
        "today": sorted(due, key=lambda word: (-int(word.get("mistake_count", 0)), word.get("word", "")))[:30],
        "difficult": difficult,
        "all": sorted(words, key=lambda word: (word.get("next_review", ""), word.get("word", ""))),
    }


def enrich_vocabulary_links(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach hand-entered mistakes to the KET library and fill missing meanings."""
    changed = False
    for record in words:
        matched = find_ket_vocabulary_word(str(record.get("word", "")))
        if not matched:
            continue
        if record.get("ket_word_id") != matched["id"]:
            record["ket_word_id"] = matched["id"]
            changed = True
        if not record.get("meaning"):
            detail = ket_word_detail(matched["word"])
            if detail.get("translation"):
                record["meaning"] = detail["translation"]
                changed = True
    if changed:
        save_vocabulary(words)
    return words


def load_ket_vocabulary() -> list[dict[str, str]]:
    try:
        return json.loads(KET_VOCABULARY.read_text(encoding="utf-8")).get("entries", [])
    except (OSError, json.JSONDecodeError):
        return []


def ket_word_forms(item: dict[str, Any]) -> set[str]:
    """Return searchable forms for entries such as 'centimetre/centimeter (cm)'."""
    source = str(item.get("word", "")).lower().strip()
    forms = {source}
    forms.update(match.strip() for match in re.findall(r"\(([^)]+)\)", source))
    without_notes = re.sub(r"\s*\([^)]*\)", "", source).strip()
    forms.add(without_notes)
    forms.update(part.strip() for part in without_notes.split("/"))
    return {form for form in forms if form}


def find_ket_vocabulary_word(word: str) -> dict[str, str] | None:
    query = str(word).lower().strip()
    return next((item for item in load_ket_vocabulary() if query in ket_word_forms(item)), None)


def load_ket_details() -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(KET_DETAILS.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_ket_details(details: dict[str, dict[str, Any]]) -> None:
    KET_DETAILS.parent.mkdir(parents=True, exist_ok=True)
    KET_DETAILS.write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")


def ket_word_detail(word: str) -> dict[str, Any]:
    """Fetch lightweight pronunciation and definition data only when a word is opened."""
    key = word.lower()
    details = load_ket_details()
    if key in details and details[key].get("translation") and "audio_us" in details[key] and "audio_uk" in details[key]:
        return details[key]
    detail: dict[str, Any] = {"word": word, "phonetic": "", "audio": "", "audio_us": "", "audio_uk": "", "definition": "", "translation": "", "image": ""}
    # The desktop bundle's Python does not inherit macOS's CA bundle. These are
    # fixed public dictionary endpoints and no personal data is sent.
    public_dictionary_context = ssl._create_unverified_context()
    try:
        with urlopen(f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(key)}", timeout=8, context=public_dictionary_context) as response:
            entry = json.loads(response.read().decode("utf-8"))[0]
        detail["phonetic"] = entry.get("phonetic", "")
        audio_urls = [item.get("audio", "") for item in entry.get("phonetics", []) if item.get("audio")]
        detail["audio_us"] = next((url for url in audio_urls if "-us" in url.lower()), "")
        detail["audio_uk"] = next((url for url in audio_urls if "-uk" in url.lower() or "-gb" in url.lower()), "")
        detail["audio"] = detail["audio_us"] or detail["audio_uk"] or (audio_urls[0] if audio_urls else "")
        meanings = entry.get("meanings", [])
        if meanings:
            detail["definition"] = meanings[0].get("definitions", [{}])[0].get("definition", "")
    except (OSError, ValueError, IndexError, KeyError):
        pass
    try:
        with urlopen(f"https://api.mymemory.translated.net/get?q={quote(key)}&langpair=en%7Czh-CN", timeout=8, context=public_dictionary_context) as response:
            detail["translation"] = json.loads(response.read().decode("utf-8")).get("responseData", {}).get("translatedText", "")
    except (OSError, ValueError):
        pass
    detail["method"] = "先看图或中文理解意思，再听读三遍；遮住英文自己拼写，最后用这个词说一句和生活有关的话。"
    details[key] = detail
    save_ket_details(details)
    return detail


def ket_memory_plan(words: list[str]) -> dict[str, Any]:
    library = {item["word"].lower(): item for item in load_ket_vocabulary()}
    requested = []
    for word in words:
        cleaned = re.sub(r"\s+", " ", str(word).strip()).lower()
        if cleaned and cleaned not in requested:
            requested.append(cleaned)
    matched = [library[word] for word in requested if word in library]
    unmatched = [word for word in requested if word not in library]
    details = load_ket_details()
    cards = [{**item, "meaning": details.get(item["word"].lower(), {}).get("translation", "")} for item in matched]
    groups = [cards[index:index + 4] for index in range(0, len(cards), 4)]
    return {
        "groups": groups, "unmatched": unmatched,
        "steps": [
            "场景联想：每组四词放进同一个熟悉场景，先说中文意思，再看英文。",
            "主动回忆：遮住英文，只看中文，按顺序写出或说出英文。",
            "交错拼写：打乱四词顺序，逐个拼写；不会的词单独标记。",
            "间隔复习：10 分钟后、次日、3 天后、7 天后各快速回忆一次。",
        ],
    }


def ket_test_words(count: int) -> dict[str, Any]:
    words = load_ket_vocabulary()
    if not words:
        raise RuntimeError("KET 词库尚未准备好。")
    count = max(1, min(int(count), 100, len(words)))
    return {"total": len(words), "items": random.SystemRandom().sample(words, count)}


def listening_choice_options(word: str) -> dict[str, Any]:
    words = load_ket_vocabulary()
    if len(words) < 4:
        raise RuntimeError("词库词条不足，暂时无法生成听力选项。")
    target = find_ket_vocabulary_word(word) or {"id": "custom", "word": word}
    pool = [item for item in words if item.get("id") != target.get("id") and item.get("word", "").lower() != str(word).lower()]
    randomizer = random.SystemRandom()
    none_of_above = randomizer.randrange(5) == 0
    if none_of_above:
        choices = randomizer.sample(pool, 4)
    else:
        choices = [target, *randomizer.sample(pool, 3)]
        randomizer.shuffle(choices)
    return {
        "choices": [{"id": item.get("id", item["word"]), "word": item["word"]} for item in choices],
        "answer": target["word"],
        "none_of_above": none_of_above,
    }


def ket_pronunciation(word: str, accent: str) -> str:
    clean_word = re.sub(r"[^a-zA-Z' -]", "", word).strip()
    if not clean_word:
        raise RuntimeError("单词发音内容无效。")
    accent = "uk" if accent == "uk" else "us"
    filename = f"{hashlib.sha1(f'{accent}:{clean_word.lower()}'.encode()).hexdigest()[:16]}.mp3"
    path = WORD_AUDIO / filename
    if not path.is_file():
        WORD_AUDIO.mkdir(parents=True, exist_ok=True)
        voice = "en-GB-SoniaNeural" if accent == "uk" else "en-US-AvaNeural"
        try:
            subprocess.run([str(EDGE_TTS), "--voice", voice, "--text", clean_word, "--write-media", str(path)], check=True, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as error:
            path.unlink(missing_ok=True)
            raise RuntimeError("神经英语发音暂时无法生成。") from error
    return filename


def daily_example_for_word(word: str) -> dict[str, str]:
    """Create a short, speakable sentence for a dictation prompt without an LLM call."""
    clean_word = re.sub(r"[^a-zA-Z' -]", "", word).strip().lower()
    if not clean_word:
        raise RuntimeError("单词例句内容无效。")
    examples = {
        "because": ("I took my umbrella because it was raining.", "因为下雨了，我带了雨伞。"),
        "beetle": ("I saw a small beetle on the path to school.", "我在上学路上看到了一只小甲虫。"),
        "rucksack": ("I put my lunch box in my rucksack before school.", "上学前，我把午餐盒放进了背包。"),
        "backpack": ("My backpack is by the door, ready for school.", "我的书包在门边，已经准备好去上学了。"),
        "breakfast": ("I eat breakfast with my family before school.", "上学前，我和家人一起吃早餐。"),
        "library": ("We borrowed two books from the library today.", "今天我们从图书馆借了两本书。"),
        "beautiful": ("The park looks beautiful in the morning sun.", "公园在晨光下看起来很美。"),
    }
    if clean_word in examples:
        sentence, translation = examples[clean_word]
        return {"word": clean_word, "sentence": sentence, "translation": translation}

    entry = next((item for item in load_ket_vocabulary() if item.get("word", "").lower() == clean_word), {})
    part_of_speech = str(entry.get("part_of_speech", ""))
    selector = int(hashlib.sha1(clean_word.encode()).hexdigest()[:8], 16)
    if "v" in part_of_speech:
        templates = [
            (f"I want to {clean_word} after school today.", f"今天放学后，我想要{clean_word}。"),
            (f"We can {clean_word} together before dinner.", f"晚饭前，我们可以一起{clean_word}。"),
            (f"My teacher asked us to {clean_word} in class.", f"老师让我们在课堂上{clean_word}。"),
        ]
    elif "adj" in part_of_speech:
        templates = [
            (f"The park looks {clean_word} in the morning sun.", f"公园在晨光下看起来很{clean_word}。"),
            (f"It was a {clean_word} day at school.", f"今天在学校是很{clean_word}的一天。"),
            (f"My new picture is {clean_word}.", f"我的新画很{clean_word}。"),
        ]
    elif "adv" in part_of_speech:
        templates = [
            (f"Please read the sentence {clean_word}.", f"请{clean_word}地读这句话。"),
            (f"We walked {clean_word} to the classroom.", f"我们{clean_word}地走向教室。"),
            (f"I finished my homework {clean_word} today.", f"今天我{clean_word}地完成了作业。"),
        ]
    elif "n" in part_of_speech:
        templates = [
            (f"We talked about {clean_word} in class today.", f"今天课堂上我们谈到了{clean_word}。"),
            (f"Our teacher showed us {clean_word} today.", f"今天老师向我们展示了{clean_word}。"),
            (f"I wrote about {clean_word} in my notebook.", f"我在笔记本里写了关于{clean_word}的内容。"),
        ]
    else:
        templates = [
            (f"We used {clean_word} in an English sentence today.", f"今天我们在一句英语句子中用了{clean_word}。"),
            (f"Please try {clean_word} in your next sentence.", f"请在下一句中试着用{clean_word}。"),
            (f"I saw {clean_word} in my English book this morning.", f"今天早上我在英语书里看到了{clean_word}。"),
        ]
    sentence, translation = templates[selector % len(templates)]
    return {"word": clean_word, "sentence": sentence, "translation": translation}


def dictation_example(word: str, accent: str) -> dict[str, str]:
    example = daily_example_for_word(word)
    example["audio_url"] = f"/word-audio/{ket_pronunciation(example['sentence'], accent)}"
    return example


def practice_meaning(word: str) -> dict[str, str]:
    detail = ket_word_detail(word)
    return {"word": word, "meaning": detail.get("translation", "")}


def add_vocabulary_word(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    word = re.sub(r"\s+", "", str(payload.get("word", ""))).lower()
    if not re.fullmatch(r"[a-z][a-z'\-]{0,78}", word):
        raise RuntimeError("请输入一个有效的英文单词。")
    meaning = str(payload.get("meaning", "")).strip()[:160]
    error_type = str(payload.get("error_type", "拼写")).strip()[:24] or "拼写"
    source = str(payload.get("source", "自主发现")).strip()[:48] or "自主发现"
    note = str(payload.get("note", "")).strip()[:300]
    ket_word_id = str(payload.get("ket_word_id", "")).strip()
    if not ket_word_id:
        matched = find_ket_vocabulary_word(word)
        ket_word_id = matched["id"] if matched else ""
    if not meaning and ket_word_id:
        matched = next((item for item in load_ket_vocabulary() if item["id"] == ket_word_id), None)
        if matched:
            meaning = ket_word_detail(matched["word"]).get("translation", "")[:160]
    words = enrich_vocabulary_links(load_vocabulary())
    existing = next((item for item in words if item.get("word") == word), None)
    timestamp = now()
    if existing:
        existing.update({
            "meaning": meaning or existing.get("meaning", ""), "error_type": error_type, "source": source,
            "note": note or existing.get("note", ""), "ket_word_id": ket_word_id or existing.get("ket_word_id", ""),
            "mastery_level": 0, "next_review": today(), "updated_at": timestamp,
        })
        existing["mistake_count"] = int(existing.get("mistake_count", 0)) + 1
        existing.setdefault("review_history", []).append({"at": timestamp, "result": "再次录入"})
        record, created = existing, False
    else:
        record = {
            "id": hashlib.sha1(f"{word}:{timestamp}".encode()).hexdigest()[:12], "word": word, "meaning": meaning,
            "error_type": error_type, "source": source, "note": note, "created_at": timestamp, "updated_at": timestamp,
            "ket_word_id": ket_word_id, "mistake_count": 1, "mastery_level": 0, "next_review": today(), "review_history": [],
        }
        words.append(record)
        created = True
    save_vocabulary(words)
    return record, created


def review_vocabulary_word(word_id: str, result: str) -> dict[str, Any]:
    words = load_vocabulary()
    record = next((item for item in words if item.get("id") == word_id), None)
    if record is None:
        raise RuntimeError("未找到这个单词。")
    if result not in {"known", "fuzzy", "unknown", "repeat"}:
        raise RuntimeError("复习结果无效。")
    current_day = datetime.now().astimezone().date()
    level = int(record.get("mastery_level", 0))
    if result == "known":
        level = min(level + 1, 5)
        interval = (1, 3, 7, 14, 30)[level - 1]
    elif result == "fuzzy":
        level = max(level - 1, 0)
        interval = 1
    elif result == "repeat":
        interval = 0
    else:
        level = 0
        interval = 0
        record["mistake_count"] = int(record.get("mistake_count", 0)) + 1
    record["mastery_level"] = level
    record["next_review"] = (current_day + timedelta(days=interval)).isoformat()
    record["updated_at"] = now()
    record.setdefault("review_history", []).append({"at": record["updated_at"], "result": result})
    record["review_history"] = record["review_history"][-50:]
    save_vocabulary(words)
    return record


def delete_vocabulary_word(word_id: str) -> str:
    words = load_vocabulary()
    record = next((item for item in words if item.get("id") == word_id), None)
    if record is None:
        raise RuntimeError("未找到这个错词。")
    save_vocabulary([item for item in words if item.get("id") != word_id])
    return str(record.get("word", "这个单词"))


def category_for(text: str) -> str:
    if any(word in text for word in EXAM_WORDS):
        return "考试提醒"
    if any(word in text for word in TEACHER_WORDS):
        return "老师要求"
    if any(word in text for word in HOMEWORK_WORDS):
        return "作业"
    return "普通消息"


def praise_subject(text: str) -> str:
    if any(word in text for word in ("听写", "字音", "字形", "词语", "朗读", "读写绘", "阅读", "书香", "感悟")):
        return "语文"
    if any(word in text for word in ("数学", "计算", "口算", "应用题")):
        return "数学"
    if "英语" in text:
        return "英语"
    return "综合"


def teacher_profile(sender: str) -> tuple[str, str] | None:
    """Return the display name and subject for a known teacher identity."""
    for name, profile in TEACHERS.items():
        if sender in profile["aliases"]:
            return name, str(profile["subject"])
    return None


def praise_names(text: str) -> list[str]:
    if not any(word in text for word in PRAISE_WORDS):
        return []
    snippets = re.findall(r"(?:表扬|最佳[—:：])\s*([^。！？\n]{1,80})", text)
    names: list[str] = []
    for snippet in snippets:
        for item in re.split(r"[、，,]\s*", snippet):
            cleaned = re.sub(r"(?:小朋友|副组长|小组长|四位|两位|全员|同学|同学们)", "", item).strip(" :：-—“”\"")
            if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", cleaned) and cleaned not in PRAISE_STOP_WORDS and cleaned not in names:
                names.append(cleaned)
    role_patterns = [
        r"(?:的|[“\"、,:：\s])([\u4e00-\u9fff]{2,4})(?:副组长|小组长)",
        r"(?:副组长|小组长)[、，,]\s*([\u4e00-\u9fff]{2,4})",
    ]
    for pattern in role_patterns:
        for name in re.findall(pattern, text):
            if name not in PRAISE_STOP_WORDS and name not in names:
                names.append(name)
    return names


def reminder_text(message: dict[str, str]) -> str:
    """Create a short, speakable reminder instead of reading a whole group post."""
    content = re.sub(r"https?://\S+", "", message["text"])
    content = re.sub(r"\[[^\]\n]{1,24}\]", "", content)
    content = re.sub(r"\s+", " ", content).strip(" ，,。！？!?").rstrip("。！？!?")
    content = content[:150]
    subject = message.get("teacher_subject") or "学习"
    teacher = message.get("sender") or "老师"
    teacher_title = teacher if teacher.endswith("老师") else f"{teacher}老师"
    return f"六六，今天的{subject}作业，{teacher_title}是这样要求的：{content}。记得认真完成，做完自己检查一遍。"


def is_homework_message(message: dict[str, str]) -> bool:
    return message["category"] == "作业" or any(word in message["text"] for word in HOMEWORK_WORDS)


def play_voice_reminder(reminder: dict[str, str]) -> None:
    audio_path = VOICE_REMINDERS / reminder["file"]
    if audio_path.is_file():
        subprocess.Popen(["afplay", str(audio_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def create_voice_reminder(message: dict[str, str], *, play: bool = False) -> dict[str, str] | None:
    """Use the installed macOS Mandarin voice and retain an audio replay locally."""
    if not is_homework_message(message) or message["message_type"] == "附件":
        return None
    text = reminder_text(message)
    VOICE_REMINDERS.mkdir(parents=True, exist_ok=True)
    base = f"{message['message_date']}-{message['id']}"
    aiff_path = VOICE_REMINDERS / f"{base}.aiff"
    audio_path = VOICE_REMINDERS / f"{base}.m4a"
    neural_audio_path = VOICE_REMINDERS / f"{base}.mp3"
    engine = "本机语音"
    try:
        if EDGE_TTS.exists():
            try:
                subprocess.run([str(EDGE_TTS), "--voice", "zh-CN-XiaoxiaoNeural", "--rate=-8%", "--text", text, "--write-media", str(neural_audio_path)], check=True, capture_output=True, text=True, timeout=60)
                audio_path = neural_audio_path
                engine = "自然语音"
            except subprocess.SubprocessError:
                neural_audio_path.unlink(missing_ok=True)
        if engine == "本机语音":
            subprocess.run(["say", "-v", "Tingting", "-r", "175", "-o", str(aiff_path), text], check=True, capture_output=True, text=True, timeout=45)
            subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(aiff_path), str(audio_path)], check=True, capture_output=True, text=True, timeout=45)
            aiff_path.unlink(missing_ok=True)
    except (OSError, subprocess.SubprocessError):
        aiff_path.unlink(missing_ok=True)
        audio_path.unlink(missing_ok=True)
        neural_audio_path.unlink(missing_ok=True)
        return None
    reminder = {"id": message["id"], "text": text, "created_at": now(), "file": audio_path.name, "engine": engine}
    if play:
        play_voice_reminder(reminder)
    return reminder


def is_recent_homework(message: dict[str, str]) -> bool:
    source_time = message.get("source_time", "")
    try:
        timestamp = datetime.fromisoformat(source_time.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.astimezone()
    except (TypeError, ValueError):
        return False
    age_seconds = (datetime.now(timestamp.tzinfo) - timestamp).total_seconds()
    return 0 <= age_seconds <= 15 * 60 and is_homework_message(message) and message.get("message_type") != "附件"


def build_teacher_knowledge_graph(records: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build an explainable local graph from the teachers' actual messages."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    for teacher, profile in TEACHERS.items():
        messages = [record for record in records if record["sender"] == teacher]
        topic_counts: Counter[str] = Counter()
        category_counts: Counter[str] = Counter(record["category"] for record in messages)
        source_counts: Counter[str] = Counter("QQ" if record.get("source") == "qq_group" else "微信" for record in messages)
        attachment_count = sum(record["message_type"] == "附件" for record in messages)
        praise_count = sum(bool(praise_names(record["content"])) for record in messages)
        for record in messages:
            text = record["content"]
            for topic, words in KNOWLEDGE_TOPICS.items():
                if any(word in text for word in words):
                    topic_counts[topic] += 1
        styles: list[str] = []
        if category_counts["作业"] + category_counts["老师要求"] + category_counts["考试提醒"] >= 3:
            styles.append("任务明确")
        if topic_counts["家长协作"]:
            styles.append("家校协作")
        if attachment_count:
            styles.append("资料支持")
        if praise_count:
            styles.append("鼓励反馈")
        if topic_counts["安全与习惯"]:
            styles.append("习惯关注")
        if not styles:
            styles.append("持续观察")
        teacher_id = f"teacher:{teacher}"
        nodes.append({"id": teacher_id, "kind": "teacher", "label": teacher, "subject": profile["subject"], "count": len(messages)})
        topics = [{"name": topic, "count": count} for topic, count in topic_counts.most_common(5)]
        for topic in topics:
            topic_id = f"topic:{teacher}:{topic['name']}"
            nodes.append({"id": topic_id, "kind": "topic", "label": topic["name"], "count": topic["count"]})
            edges.append({"source": teacher_id, "target": topic_id, "count": topic["count"]})
        examples = [
            {"date": message["message_date"], "content": message["content"], "category": message["category"]}
            for message in messages
            if message["category"] != "普通消息" or message["message_type"] == "附件"
        ][:3]
        profiles.append({
            "teacher": teacher, "subject": profile["subject"], "message_count": len(messages),
            "topics": topics, "styles": styles, "attachments": attachment_count,
            "requirements": category_counts["老师要求"], "homework": category_counts["作业"],
            "sources": dict(source_counts), "examples": examples,
        })
    return nodes, {"profiles": profiles, "edges": edges}


def message_id(message: dict[str, str]) -> str:
    if message.get("external_id"):
        return hashlib.sha256(message["external_id"].encode("utf-8")).hexdigest()[:16]
    source = "|".join((message.get("sender", ""), message.get("text", ""), message.get("message_date", message.get("captured_at", "")[:10])))
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def markdown_escape(value: str) -> str:
    return value.replace("\n", " ").replace("\r", " ").strip()


def persist_message(message: dict[str, str]) -> None:
    source = message.get("source", "wechat_cli")
    raw_root = QQ_RAW if source == "qq_qce" else RAW
    group = QQ_GROUP if source == "qq_qce" else GROUP
    source_label = "qq_group" if source == "qq_qce" else "wechat_group"
    raw_root.mkdir(parents=True, exist_ok=True)
    identifier = message["id"]
    captured = message["captured_at"]
    date = captured[:10]
    category = message["category"]
    content = message["text"].strip()
    raw_path = raw_root / f"{date}-{identifier}.md"
    raw_path.write_text(
        "\n".join((
            "---", "type: raw_input", f"source: {source_label}", f"group: {group}",
            f"captured_at: {captured}", f"message_id: {identifier}",
            f"category: {category}", f"sender: {markdown_escape(message.get('sender', 'UNKNOWN'))}",
            f"teacher_subject: {markdown_escape(message.get('teacher_subject', ''))}",
            f"source_time: {markdown_escape(message.get('source_time', ''))}",
            f"message_date: {markdown_escape(message.get('message_date', date))}",
            f"message_type: {markdown_escape(message.get('message_type', '文字'))}",
            "---", "", f"# {group} 群消息", "", content, "",
        )), encoding="utf-8"
    )
    if category == "老师要求":
        REQUIREMENTS.mkdir(parents=True, exist_ok=True)
        source_name = "qq" if source == "qq_qce" else "wechat"
        req_path = REQUIREMENTS / f"{date}-{source_name}-{identifier}.md"
        req_path.write_text(
            "\n".join((
                "---", "type: teacher_requirement", f"source: {source_label}", f"group: {group}",
                f"date: {date}", "status: active", f"raw_message: ../raw-inputs/{source_name}/{raw_path.name}",
                "---", "", "# 老师要求", "", content, "", "## 下次检查", "", "- ", "",
            )), encoding="utf-8"
        )


def read_accessibility_messages() -> list[dict[str, str]]:
    """Read visible messages using the same macOS Accessibility approach as WeChat-MCP."""
    try:
        from collector import collect_visible_messages
    except ModuleNotFoundError as error:
        raise RuntimeError("采集组件尚未安装。请先运行 setup_local_collector.py。") from error
    return collect_visible_messages(GROUP, limit=60)


def database_export_ready() -> bool:
    return (WECHAT_EXPORT / "decrypted" / "contact" / "contact.db").exists() and (WECHAT_EXPORT / "export_chat.py").exists()


def read_database_messages() -> list[dict[str, str]]:
    """Read the selected group from a locally decrypted WeChat database."""
    export_dir = PRIVATE / "database-export"
    export_dir.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "export_chat.py", "--name", GROUP, "--output", str(export_dir)]
    completed = subprocess.run(
        command, cwd=WECHAT_EXPORT, capture_output=True, text=True, timeout=120
    )
    payload = export_dir / "chat.json"
    if completed.returncode != 0 or not payload.exists():
        details = (completed.stderr or completed.stdout or "没有生成群聊导出文件").strip()
        raise RuntimeError(f"数据库导出未完成：{details[-300:]}")
    records = json.loads(payload.read_text(encoding="utf-8"))
    return [
        {"sender": str(item.get("sender", "群成员")), "text": str(item.get("content", "")), "source_time": str(item.get("time", ""))}
        for item in records[-120:]
    ]


def wechat_cli_ready() -> bool:
    """Check local bootstrap state without touching WeChat on every page refresh."""
    if not WECHAT_CLI.exists() or not WECHAT_CLI_CONFIG.exists():
        return False
    try:
        config = json.loads(WECHAT_CLI_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(config.get("wxid") and config.get("keys"))


def read_wechat_cli_messages() -> list[dict[str, str]]:
    completed = subprocess.run(
        [str(WECHAT_CLI), "timeline", GROUP, "--limit", "500"], capture_output=True, text=True, timeout=120
    )
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout or "wechat-cli 无法读取群记录")[-400:])
    try:
        messages = json.loads(completed.stdout)["data"]["messages"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise RuntimeError("wechat-cli 返回的群记录格式无效。") from error
    records: list[dict[str, str]] = []
    for item in messages:
        profile = teacher_profile(str(item.get("sender", "")))
        if profile is None:
            continue
        teacher_name, teacher_subject = profile
        identity = item.get("id", {})
        timestamp = str(item.get("time_iso") or item.get("time") or "")
        records.append({
            "sender": teacher_name,
            "teacher_subject": teacher_subject,
            "text": str(item.get("text", "")),
            "source_time": timestamp,
            "message_date": timestamp[:10],
            "message_type": "附件" if item.get("kind") == "file" else "文字",
            "external_id": str(identity.get("server_id_str") or f"{identity.get('talker', '')}:{identity.get('local_id', '')}"),
        })
    return records


def read_group_messages() -> tuple[str, list[dict[str, str]]]:
    """Prefer robust database export; fall back to live visible-message capture."""
    if wechat_cli_ready():
        return "wechat_cli", read_wechat_cli_messages()
    if database_export_ready():
        return "database", read_database_messages()
    try:
        from screen_collector import collect_visible_messages
        return "screen_ocr", collect_visible_messages(GROUP, limit=60)
    except ModuleNotFoundError:
        return "accessibility", read_accessibility_messages()


def qq_access_token() -> str:
    """Read the QCE token from its Docker volume without persisting it locally."""
    command = [
        str(DOCKER), "exec", QQ_CONTAINER, "python3", "-c",
        "import json; print(json.load(open('/app/.qq-chat-exporter/security.json'))['accessToken'])",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=15)
    token = completed.stdout.strip()
    if completed.returncode or not token:
        raise RuntimeError("QQ 同步容器尚未就绪，请先打开 Docker Desktop 并完成 QQ 登录。")
    return token


def qq_api_request(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    token = qq_access_token()
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = Request(
        f"{QQ_API}{path}", data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    try:
        with urlopen(request, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise RuntimeError(f"QQ 本地同步服务无法读取：{error}") from error
    if not result.get("success"):
        raise RuntimeError(str(result.get("error", {}).get("message", "QQ 本地同步服务返回错误")))
    return result.get("data", {})


def qq_connection_state() -> str:
    try:
        return "online" if qq_api_request("/api/system/status").get("online") else "offline"
    except RuntimeError:
        return "unavailable"


def qq_ready() -> bool:
    return qq_connection_state() == "online"


def copy_qq_login_qr() -> bool:
    """Copy the container QR image into local-only application state."""
    QQ_LOGIN_QR.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [str(DOCKER), "cp", f"{QQ_CONTAINER}:/app/napcat/cache/qrcode.png", str(QQ_LOGIN_QR)],
        capture_output=True, text=True, timeout=20,
    )
    return completed.returncode == 0 and QQ_LOGIN_QR.is_file() and QQ_LOGIN_QR.stat().st_size > 0


def start_qq_login() -> None:
    """Restart the offline QCE session and wait for its newly generated QR code."""
    QQ_LOGIN_QR.unlink(missing_ok=True)
    completed = subprocess.run([str(DOCKER), "restart", QQ_CONTAINER], capture_output=True, text=True, timeout=90)
    if completed.returncode:
        raise RuntimeError((completed.stderr or "无法重启 QQ 登录容器")[-300:])
    # NapCat needs a short boot before it overwrites its QR file.  Waiting here
    # prevents the desktop app from presenting the QR code from a prior session.
    time.sleep(12)
    for _ in range(20):
        if copy_qq_login_qr():
            return
        time.sleep(0.5)
    raise RuntimeError("QQ 登录二维码尚未准备好，请稍后重新尝试。")


def qq_message_text(elements: list[dict[str, Any]]) -> tuple[str, str]:
    """Turn QCE rich message elements into a compact record for the learning vault."""
    parts: list[str] = []
    attachment = False
    for element in elements:
        text = element.get("textElement") or {}
        if text.get("content"):
            parts.append(str(text["content"]))
        file_info = element.get("fileElement") or {}
        picture = element.get("picElement") or {}
        if file_info:
            attachment = True
            parts.append(str(file_info.get("fileName") or "[文件]"))
        elif picture:
            attachment = True
            parts.append("[图片]")
        elif element.get("pttElement") or element.get("videoElement"):
            attachment = True
            parts.append("[语音或视频]")
    return " ".join(part for part in parts if part).strip(), "附件" if attachment else "文字"


def read_qq_messages() -> list[dict[str, str]]:
    data = qq_api_request("/api/messages/fetch", {
        "peer": {"chatType": 2, "peerUid": QQ_GROUP_CODE}, "page": 1, "limit": 500, "batchSize": 500,
    })
    records: list[dict[str, str]] = []
    for item in data.get("messages", []):
        sender_candidates = (
            str(item.get("sendRemarkName") or ""), str(item.get("sendMemberName") or ""), str(item.get("sendNickName") or ""),
        )
        profile = next((teacher_profile(sender) for sender in sender_candidates if teacher_profile(sender)), None)
        if profile is None:
            continue
        sender, subject = profile
        text, message_type = qq_message_text(item.get("elements") or [])
        if not text:
            continue
        timestamp = int(str(item.get("msgTime") or "0"))
        source_time = datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds") if timestamp else ""
        records.append({
            "sender": sender, "teacher_subject": subject, "text": text, "source_time": source_time,
            "message_date": source_time[:10], "message_type": message_type,
            "external_id": f"qq:{item.get('msgId', '')}",
        })
    return records


def wechat_ready() -> bool:
    try:
        if wechat_cli_ready():
            return True
        if database_export_ready():
            return True
        from screen_collector import screen_ocr_ready
        if screen_ocr_ready():
            return True
        from collector import accessibility_diagnostics
        return bool(accessibility_diagnostics().get("elements"))
    except ModuleNotFoundError:
        return False


def collector_setup_hint() -> str:
    try:
        from collector import accessibility_diagnostics, accessibility_is_trusted
        if not accessibility_is_trusted():
            return "请在系统设置 → 隐私与安全性 → 辅助功能中，允许运行本服务的终端；随后再授予屏幕录制权限。"
        if not accessibility_diagnostics().get("elements"):
            return "当前微信版本未公开聊天控件。同步台将使用屏幕 OCR；请先为运行服务的 Codex 或终端授予“屏幕录制”权限。"
    except ModuleNotFoundError:
        return "请先运行一次 setup_local_collector.py，并在系统设置中授权终端的辅助功能和屏幕录制。"
    return "微信已就绪。点击同步即可读取“六六班级”的最新可见消息。"


def screen_recording_ready() -> bool:
    try:
        from screen_collector import screen_recording_authorized
        return screen_recording_authorized()
    except ModuleNotFoundError:
        return False


def run_sync(input_messages: list[dict[str, str]] | None = None, input_source: str | None = None) -> dict[str, Any]:
    started = time.monotonic()
    state = load_state()
    source, messages = (input_source or "import", input_messages) if input_messages is not None else read_group_messages()
    captured_at = now()
    seen = set(state.get("seen", []))
    fresh: list[dict[str, str]] = []
    duplicates = 0
    for message in messages:
        text = message.get("text", "").strip()
        if not text:
            continue
        normalized = {
            "text": text, "sender": message.get("sender", "UNKNOWN"), "captured_at": captured_at,
            "source_time": message.get("source_time", ""), "source": source,
            "message_date": message.get("message_date", captured_at[:10]),
            "message_type": message.get("message_type", "附件" if any(text.lower().endswith(ext) for ext in (".pdf", ".m4a", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip")) else "文字"),
            "teacher_subject": message.get("teacher_subject", ""),
            "external_id": message.get("external_id", ""),
        }
        normalized["id"] = message_id(normalized)
        normalized["category"] = category_for(text)
        if normalized["id"] in seen:
            duplicates += 1
            continue
        persist_message(normalized)
        fresh.append(normalized)
        seen.add(normalized["id"])

    new_reminders: list[dict[str, str]] = []
    if state.get("voice_reminders_enabled", True):
        for message in fresh:
            reminder = create_voice_reminder(message)
            if reminder:
                new_reminders.append(reminder)
        # History imports may contain many old assignments.  Only speak the most
        # recent new assignment, while still retaining all generated recordings.
        recent_homework = [message for message in fresh if is_recent_homework(message)]
        if recent_homework:
            latest = max(recent_homework, key=lambda message: message.get("source_time", ""))
            reminder = next((item for item in new_reminders if item["id"] == latest["id"]), None)
            if reminder:
                play_voice_reminder(reminder)
        state["voice_reminders"] = [*new_reminders, *state.get("voice_reminders", [])][:30]

    duration = f"00:00:{int(time.monotonic() - started):02d}"
    result = {"captured": len(messages), "saved": len(fresh), "duplicates": duplicates, "duration": duration}
    entry = {"id": hashlib.sha1(captured_at.encode()).hexdigest()[:10], "finished_at": captured_at, "status": "success", **result}
    state["seen"] = list(seen)[-800:]
    state["last_sync"] = captured_at
    state["last_result"] = result
    state["history"] = [entry, *state.get("history", [])][:20]
    save_state(state)
    return {"result": result, "fresh": fresh, "reminders": new_reminders, "source": source}


def run_qq_sync() -> dict[str, Any]:
    return run_sync(read_qq_messages(), "qq_qce")


def build_dashboard() -> dict[str, Any]:
    state = load_state()
    vocabulary = vocabulary_summary(enrich_vocabulary_links(load_vocabulary()))
    ket_words = load_ket_vocabulary()
    records: list[dict[str, str]] = []
    for raw_root in (RAW, QQ_RAW):
        if not raw_root.exists():
            continue
        for path in sorted(raw_root.glob("*.md"), reverse=True):
            text = path.read_text(encoding="utf-8")
            meta, _, body = text.partition("---\n\n")
            metadata = dict(line.split(": ", 1) for line in meta.splitlines() if ": " in line)
            raw_sender = metadata.get("sender", "群成员")
            profile = teacher_profile(raw_sender)
            records.append({
                "id": metadata.get("message_id", path.stem), "content": body.strip().split("\n", 1)[-1] if body else "",
                "captured_at": metadata.get("captured_at", ""), "category": metadata.get("category", "普通消息"),
                "sender": profile[0] if profile else raw_sender,
                "message_date": metadata.get("message_date", metadata.get("captured_at", "")[:10]),
                "message_type": metadata.get("message_type", "文字"),
                "teacher_subject": profile[1] if profile else metadata.get("teacher_subject", "语文" if raw_sender == "蔡老师" else ""),
                "source_time": metadata.get("source_time", ""), "source": metadata.get("source", "wechat_group"), "sync_status": "已同步",
            })
    teacher_records = [record for record in records if record["sender"] in TEACHERS]
    homework_items = [
        record for record in teacher_records
        if record["message_type"] != "附件" and is_homework_message({**record, "text": record["content"]})
    ]
    homework_items.sort(key=lambda item: (item["message_date"], item.get("source_time", "")), reverse=True)
    daily: dict[str, list[dict[str, str]]] = {}
    for record in teacher_records:
        if record["category"] not in {"作业", "老师要求", "考试提醒"} and record["message_type"] != "附件":
            continue
        daily.setdefault(record["message_date"], []).append(record)
    daily_requirements = [
        {
            "date": date,
            "items": sorted(items, key=lambda item: item.get("source_time", "")),
            "homework_count": sum(item["category"] == "作业" for item in items),
            "requirement_count": sum(item["category"] == "老师要求" for item in items),
            "attachment_count": sum(item["message_type"] == "附件" for item in items),
        }
        for date, items in sorted(daily.items(), reverse=True)
    ]
    praise_records = []
    praise_totals: dict[str, dict[str, Any]] = {}
    for record in teacher_records:
        for student in praise_names(record["content"]):
            subject = record["teacher_subject"] or praise_subject(record["content"])
            praise_records.append({"student": student, "subject": subject, "teacher": record["sender"], "date": record["message_date"], "content": record["content"], "id": record["id"], "source": record.get("source", "wechat_group")})
            summary = praise_totals.setdefault(student, {"student": student, "count": 0, "subjects": {}})
            summary["count"] += 1
            summary["subjects"][subject] = summary["subjects"].get(subject, 0) + 1
    praise_leaderboard = sorted(praise_totals.values(), key=lambda item: (-item["count"], item["student"]))
    graph_nodes, teacher_knowledge_graph = build_teacher_knowledge_graph(teacher_records)
    return {
        "group": GROUP, "wechat_ready": wechat_ready(), "qq_ready": qq_ready(), "qq_status": qq_connection_state(), "qq_group": QQ_GROUP, "last_sync": state["last_sync"],
        "automation": state["automation"], "automation_time": state["automation_time"],
        "voice_reminders_enabled": state.get("voice_reminders_enabled", True),
        "voice_reminders": state.get("voice_reminders", []),
        "last_result": state["last_result"], "history": state["history"], "recent_messages": records[:8],
        "teachers": [{"name": name, "subject": profile["subject"]} for name, profile in TEACHERS.items()],
        "teacher_messages": teacher_records[:120],
        "teacher_stats": {"total": len(teacher_records), "text": sum(record["message_type"] == "文字" for record in teacher_records), "attachment": sum(record["message_type"] == "附件" for record in teacher_records)},
        "homework_items": homework_items[:120],
        "daily_requirements": daily_requirements,
        "teacher_knowledge_graph": {"nodes": graph_nodes, **teacher_knowledge_graph},
        "praise_records": sorted(praise_records, key=lambda item: item["date"], reverse=True),
        "praise_leaderboard": praise_leaderboard,
        "vocabulary": vocabulary,
        "ket_library": {"total": len(ket_words), "source": "Cambridge A2 Key Vocabulary List, August 2025"},
        "screen_recording": screen_recording_ready(),
        "setup_hint": (
            "已连接本地微信数据库，可读取完整历史、日期、发送者与附件。" if wechat_cli_ready()
            else "已检测到本地解密聊天数据库，将优先从数据库同步。" if database_export_ready()
            else collector_setup_hint()
        ),
    }


def update_automation(enabled: bool) -> None:
    state = load_state()
    state["automation"] = enabled
    save_state(state)
    if enabled:
        if not (wechat_cli_ready() or NATIVE_AGENT.exists()):
            raise RuntimeError("本地微信数据读取尚未初始化。请先完成 wechat-cli 的 wxkey bootstrap。")
        LAUNCH_AGENT.parent.mkdir(parents=True, exist_ok=True)
        python = sys.executable
        plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>Label</key><string>com.xiafelex.hunter66-wechat-sync</string>
<key>ProgramArguments</key><array><string>{python}</string><string>{APP / 'automation_runner.py'}</string></array>
<key>StartCalendarInterval</key><dict><key>Hour</key><integer>18</integer><key>Minute</key><integer>30</integer></dict>
<key>StandardOutPath</key><string>{PRIVATE / 'automation.log'}</string>
<key>StandardErrorPath</key><string>{PRIVATE / 'automation.error.log'}</string></dict></plist>'''
        LAUNCH_AGENT.write_text(plist, encoding="utf-8")
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(LAUNCH_AGENT)], capture_output=True)
        subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(LAUNCH_AGENT)], check=True, capture_output=True)
    elif LAUNCH_AGENT.exists():
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(LAUNCH_AGENT)], capture_output=True)
        LAUNCH_AGENT.unlink()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP / "dist"), **kwargs)

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/api/ket-vocabulary":
            query = parse_qs(parsed_path.query).get("query", [""])[0].strip().lower()
            words = load_ket_vocabulary()
            items = [
                {**item, "aliases": sorted(ket_word_forms(item))}
                for item in words
                if not query or any(query in form for form in ket_word_forms(item))
            ][:80]
            self.send_json({"total": len(words), "items": items})
            return
        if parsed_path.path == "/api/ket-vocabulary/detail":
            word = parse_qs(parsed_path.query).get("word", [""])[0].strip()
            if not word:
                self.send_json({"detail": "请选择一个单词。"}, HTTPStatus.BAD_REQUEST)
                return
            self.send_json(ket_word_detail(word))
            return
        if parsed_path.path == "/api/ket-vocabulary/pronunciation":
            params = parse_qs(parsed_path.query)
            filename = ket_pronunciation(params.get("word", [""])[0], params.get("accent", ["us"])[0])
            self.send_json({"url": f"/word-audio/{filename}"})
            return
        if parsed_path.path == "/api/english-practice/dictation-example":
            params = parse_qs(parsed_path.query)
            word = params.get("word", [""])[0]
            accent = params.get("accent", ["us"])[0]
            self.send_json(dictation_example(word, accent))
            return
        if parsed_path.path == "/api/english-practice/meaning":
            word = parse_qs(parsed_path.query).get("word", [""])[0].strip()
            if not word:
                self.send_json({"detail": "请选择一个单词。"}, HTTPStatus.BAD_REQUEST)
                return
            self.send_json(practice_meaning(word))
            return
        if parsed_path.path == "/api/qq/status":
            state = qq_connection_state()
            self.send_json({"state": state, "ready": state == "online", "group": QQ_GROUP})
            return
        if parsed_path.path == "/api/qq/login-qr":
            if not QQ_LOGIN_QR.is_file() and not copy_qq_login_qr():
                self.send_json({"detail": "QQ 登录二维码尚未准备好。"}, HTTPStatus.NOT_FOUND)
                return
            body = QQ_LOGIN_QR.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/dashboard":
            self.send_json(build_dashboard())
            return
        if parsed_path.path.startswith("/voice-reminders/"):
            filename = Path(unquote(parsed_path.path)).name
            audio_path = VOICE_REMINDERS / filename
            if not audio_path.is_file() or audio_path.suffix not in {".m4a", ".mp3"}:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = audio_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "audio/mpeg" if audio_path.suffix == ".mp3" else "audio/mp4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed_path.path.startswith("/word-audio/"):
            filename = Path(unquote(parsed_path.path)).name
            audio_path = WORD_AUDIO / filename
            if not audio_path.is_file() or audio_path.suffix != ".mp3":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = audio_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/diagnostics":
            try:
                from collector import accessibility_diagnostics
                self.send_json(accessibility_diagnostics())
            except Exception as error:
                self.send_json({"detail": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        if self.path.startswith("/api/"):
            self.send_json({"detail": "未找到接口"}, HTTPStatus.NOT_FOUND)
            return
        if self.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        try:
            if self.path == "/api/ket-vocabulary/listening-options":
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                word = str(payload.get("word", "")).strip()
                if not word:
                    raise RuntimeError("请选择一个单词生成听力选项。")
                self.send_json(listening_choice_options(word))
                return
            if self.path == "/api/ket-vocabulary/test":
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                self.send_json(ket_test_words(int(payload.get("count", 35))))
                return
            if self.path == "/api/ket-vocabulary/memory-plan":
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                words = payload.get("words", [])
                if not isinstance(words, list):
                    raise RuntimeError("请按多个单词生成记忆计划。")
                self.send_json(ket_memory_plan(words))
                return
            if self.path == "/api/vocabulary":
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                record, created = add_vocabulary_word(payload)
                message = f"已把 {record['word']} 加入错词本。" if created else f"已更新 {record['word']}，它会重新进入今日复习。"
                self.send_json({"message": message, "dashboard": build_dashboard()})
                return
            if self.path == "/api/vocabulary/review":
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                record = review_vocabulary_word(str(payload.get("word_id", "")), str(payload.get("result", "")))
                self.send_json({"message": f"已记录 {record['word']} 的复习结果。", "dashboard": build_dashboard()})
                return
            if self.path == "/api/vocabulary/delete":
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                word = delete_vocabulary_word(str(payload.get("word_id", "")))
                self.send_json({"message": f"已删除错词 {word}。", "dashboard": build_dashboard()})
                return
            if self.path == "/api/qq/login/start":
                start_qq_login()
                self.send_json({"message": "请使用手机 QQ 扫描二维码登录。", "state": qq_connection_state()})
                return
            if self.path == "/api/sync":
                sync = run_sync()
                source_label = "群消息" if sync["source"] == "wechat_cli" else "可见消息"
                self.send_json({"message": f"已读取 {sync['result']['captured']} 条{source_label}，归档 {sync['result']['saved']} 条新学习记录。", "dashboard": build_dashboard()})
                return
            if self.path == "/api/sync/qq":
                sync = run_qq_sync()
                self.send_json({"message": f"已读取 {sync['result']['captured']} 条 QQ 班级群消息，归档 {sync['result']['saved']} 条新学习记录。", "dashboard": build_dashboard()})
                return
            if self.path == "/api/automation":
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                update_automation(bool(payload.get("enabled")))
                message = "已开启每日 18:30 自动检查。" if payload.get("enabled") else "已关闭自动检查。"
                self.send_json({"message": message, "dashboard": build_dashboard()})
                return
            if self.path == "/api/voice-reminders":
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                state = load_state()
                state["voice_reminders_enabled"] = bool(payload.get("enabled"))
                save_state(state)
                message = "已开启新作业语音提醒。" if state["voice_reminders_enabled"] else "已关闭新作业语音提醒。"
                self.send_json({"message": message, "dashboard": build_dashboard()})
                return
            if self.path == "/api/voice-reminders/generate":
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                homework_id = str(payload.get("message_id", ""))
                dashboard = build_dashboard()
                homework = next((item for item in dashboard["homework_items"] if item["id"] == homework_id), None)
                if homework is None:
                    raise RuntimeError("未找到这条作业记录。")
                reminder = create_voice_reminder({**homework, "text": homework["content"]}, play=True)
                if reminder is None:
                    raise RuntimeError("这条消息无法生成语音提醒。")
                state = load_state()
                state["voice_reminders"] = [reminder, *[item for item in state.get("voice_reminders", []) if item["id"] != reminder["id"]]][:30]
                save_state(state)
                self.send_json({"message": "已生成并播放作业语音提醒。", "dashboard": build_dashboard()})
                return
            if self.path == "/api/permissions/request-screen-recording":
                from screen_collector import request_screen_recording_access
                already_granted = request_screen_recording_access()
                if not already_granted:
                    subprocess.run([
                        "open",
                        "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
                    ], check=False)
                message = "屏幕录制权限已可用。" if already_granted else "已打开“屏幕录制”系统设置页，请允许 Codex、Terminal、iTerm 或 Python 中实际运行同步服务的项目。"
                self.send_json({"message": message, "dashboard": build_dashboard()})
                return
            self.send_json({"detail": "未找到接口"}, HTTPStatus.NOT_FOUND)
        except Exception as error:
            self.send_json({"detail": str(error)}, HTTPStatus.BAD_REQUEST)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync-once", action="store_true")
    parser.add_argument("--sync-input", type=Path)
    args = parser.parse_args()
    if args.sync_input:
        payload = json.loads(args.sync_input.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise SystemExit("同步输入必须是消息 JSON 数组。")
        result = run_sync(payload, "screen_agent")
        print(json.dumps(result["result"], ensure_ascii=False))
        return
    if args.sync_once:
        result = run_sync()
        print(json.dumps(result["result"], ensure_ascii=False))
        return
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()


if __name__ == "__main__":
    main()
