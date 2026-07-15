from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class SyncRecordTests(unittest.TestCase):
    def test_categories_cover_learning_group_signals(self) -> None:
        self.assertEqual(server.category_for("请家长提醒孩子带好练习册"), "老师要求")
        self.assertEqual(server.category_for("今晚完成数学作业并订正"), "作业")
        self.assertEqual(server.category_for("下周有英语单元测验，请复习"), "考试提醒")

    def test_persisted_message_uses_stable_deduplication_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "raw"
            requirements = Path(directory) / "requirements"
            message = {
                "id": "abc123", "captured_at": "2026-07-11T18:30:00+08:00",
                "category": "老师要求", "sender": "群成员", "text": "请明天带好练习册。",
            }
            with patch.object(server, "RAW", raw), patch.object(server, "REQUIREMENTS", requirements):
                server.persist_message(message)
            self.assertTrue((raw / "2026-07-11-abc123.md").exists())
            self.assertTrue((requirements / "2026-07-11-wechat-abc123.md").exists())

    def test_message_id_uses_message_date_instead_of_sync_time(self) -> None:
        first = {"sender": "蔡老师", "text": "请完成练习。", "message_date": "2026-07-10", "captured_at": "2026-07-11T18:30:00+08:00"}
        later = {**first, "captured_at": "2026-07-12T18:30:00+08:00"}
        self.assertEqual(server.message_id(first), server.message_id(later))

    def test_persisted_message_keeps_teacher_filter_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "raw"
            message = {
                "id": "teacher001", "captured_at": "2026-07-11T18:30:00+08:00", "category": "老师要求",
                "sender": "蔡老师", "text": "暑假练习册.pdf", "message_date": "2026-07-10", "message_type": "附件",
                "teacher_subject": "语文",
            }
            with patch.object(server, "RAW", raw), patch.object(server, "REQUIREMENTS", Path(directory) / "requirements"):
                server.persist_message(message)
            content = (raw / "2026-07-11-teacher001.md").read_text(encoding="utf-8")
            self.assertIn("sender: 蔡老师", content)
            self.assertIn("message_date: 2026-07-10", content)
            self.assertIn("message_type: 附件", content)
            self.assertIn("teacher_subject: 语文", content)

    def test_teacher_profiles_cover_all_three_subjects(self) -> None:
        self.assertEqual(server.teacher_profile("西瓜瓜西"), ("蔡老师", "语文"))
        self.assertEqual(server.teacher_profile("易歆"), ("刘老师", "数学"))
        self.assertEqual(server.teacher_profile("Elaine"), ("卢老师", "英语"))
        self.assertEqual(server.teacher_profile("数学-刘老师"), ("刘老师", "数学"))
        self.assertEqual(server.teacher_profile("科学-程"), ("程老师", "科学"))

    def test_teacher_knowledge_graph_uses_message_language(self) -> None:
        nodes, graph = server.build_teacher_knowledge_graph([
            {"sender": "卢老师", "content": "请家长提醒孩子完成英语阅读并提交打卡", "category": "老师要求", "message_type": "文字", "message_date": "2026-07-10"},
        ])
        profile = next(item for item in graph["profiles"] if item["teacher"] == "卢老师")
        self.assertEqual(profile["subject"], "英语")
        self.assertIn("家长协作", [item["name"] for item in profile["topics"]])
        self.assertEqual(profile["sources"], {"微信": 1})
        self.assertTrue(any(node["label"] == "卢老师" for node in nodes))

    def test_reminder_text_is_short_and_speakable(self) -> None:
        text = server.reminder_text({
            "text": "请完成今天的数学练习并订正。[玫瑰][玫瑰] https://example.com", "teacher_subject": "数学", "sender": "易歆",
        })
        self.assertEqual(text, "六六，今天的数学作业，易歆老师是这样要求的：请完成今天的数学练习并订正。记得认真完成，做完自己检查一遍。")

    def test_teacher_requirement_with_homework_words_is_a_voice_reminder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(server, "VOICE_REMINDERS", Path(directory)), patch.object(server.subprocess, "run", return_value=None), patch.object(server.subprocess, "Popen", return_value=None):
                reminder = server.create_voice_reminder({
                    "id": "homework001", "message_date": "2026-07-11", "category": "老师要求", "message_type": "文字",
                    "text": "请完成今天的数学练习并订正。", "teacher_subject": "数学", "sender": "易歆",
                })
        self.assertIsNotNone(reminder)

    def test_database_is_preferred_when_local_export_is_ready(self) -> None:
        with patch.object(server, "wechat_cli_ready", return_value=False), patch.object(server, "database_export_ready", return_value=True), patch.object(
            server, "read_database_messages", return_value=[{"text": "作业提醒"}]
        ):
            source, messages = server.read_group_messages()
        self.assertEqual(source, "database")
        self.assertEqual(messages, [{"text": "作业提醒"}])

    def test_external_message_id_is_stable(self) -> None:
        self.assertEqual(
            server.message_id({"external_id": "server-message-42"}),
            server.message_id({"external_id": "server-message-42", "text": "changed"}),
        )

    def test_qq_rich_elements_preserve_text_and_attachments(self) -> None:
        text, message_type = server.qq_message_text([
            {"textElement": {"content": "请完成今天的练习。"}},
            {"fileElement": {"fileName": "数学练习.pdf"}},
        ])
        self.assertEqual(text, "请完成今天的练习。 数学练习.pdf")
        self.assertEqual(message_type, "附件")

    def test_qq_status_is_offline_when_qce_reports_offline(self) -> None:
        with patch.object(server, "qq_api_request", return_value={"online": False}):
            self.assertEqual(server.qq_connection_state(), "offline")
            self.assertFalse(server.qq_ready())

    def test_vocabulary_reentry_and_review_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vocabulary = Path(directory) / "vocabulary.json"
            with patch.object(server, "VOCABULARY", vocabulary):
                record, created = server.add_vocabulary_word({"word": "Because", "meaning": "因为", "error_type": "拼写", "source": "听写"})
                self.assertTrue(created)
                updated, created = server.add_vocabulary_word({"word": "because", "meaning": "因为", "error_type": "词义", "source": "作业"})
                self.assertFalse(created)
                self.assertEqual(record["id"], updated["id"])
                self.assertEqual(updated["mistake_count"], 2)
                reviewed = server.review_vocabulary_word(record["id"], "known")
                self.assertEqual(reviewed["mastery_level"], 1)
                self.assertGreater(reviewed["next_review"], server.today())

    def test_ket_memory_plan_marks_unmatched_words(self) -> None:
        with patch.object(server, "load_ket_vocabulary", return_value=[{"id": "ket001", "word": "because", "part_of_speech": "conj"}]), patch.object(server, "load_ket_details", return_value={"because": {"translation": "因为"}}):
            plan = server.ket_memory_plan(["because", "not-in-ket"])
        self.assertEqual(plan["groups"][0][0]["meaning"], "因为")
        self.assertEqual(plan["unmatched"], ["not-in-ket"])

    def test_dictation_example_is_a_daily_sentence_with_the_target_word(self) -> None:
        example = server.daily_example_for_word("because")
        self.assertIn("because", example["sentence"].lower())
        self.assertEqual(example["translation"], "因为下雨了，我带了雨伞。")

    def test_dictation_example_uses_a_varied_sentence_for_ket_words(self) -> None:
        with patch.object(server, "load_ket_vocabulary", return_value=[{"word": "airport", "part_of_speech": "n"}]):
            example = server.daily_example_for_word("airport")
        self.assertIn("airport", example["sentence"])
        self.assertNotIn("heard the word", example["sentence"])

    def test_practice_meaning_returns_the_dictionary_translation(self) -> None:
        with patch.object(server, "ket_word_detail", return_value={"translation": "因为"}):
            self.assertEqual(server.practice_meaning("because"), {"word": "because", "meaning": "因为"})

    def test_ket_test_words_samples_requested_number(self) -> None:
        words = [{"id": str(index), "word": f"word{index}"} for index in range(5)]
        with patch.object(server, "load_ket_vocabulary", return_value=words):
            test = server.ket_test_words(3)
        self.assertEqual(test["total"], 5)
        self.assertEqual(len(test["items"]), 3)
        self.assertEqual(len({item["id"] for item in test["items"]}), 3)

    def test_ket_aliases_match_british_american_and_abbreviation_forms(self) -> None:
        entry = {"id": "centimetre", "word": "centimetre/centimeter (cm)"}
        with patch.object(server, "load_ket_vocabulary", return_value=[entry]):
            self.assertEqual(server.find_ket_vocabulary_word("centimeter"), entry)
            self.assertEqual(server.find_ket_vocabulary_word("cm"), entry)

    def test_repeat_review_keeps_word_due_today_without_counting_a_new_mistake(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vocabulary = Path(directory) / "vocabulary.json"
            with patch.object(server, "VOCABULARY", vocabulary):
                record, _ = server.add_vocabulary_word({"word": "because"})
                repeated = server.review_vocabulary_word(record["id"], "repeat")
        self.assertEqual(repeated["next_review"], server.today())
        self.assertEqual(repeated["mistake_count"], 1)

    def test_listening_choice_options_have_four_words_and_a_target(self) -> None:
        words = [{"id": str(index), "word": f"word{index}"} for index in range(5)]
        with patch.object(server, "load_ket_vocabulary", return_value=words):
            result = server.listening_choice_options("word0")
        self.assertEqual(len(result["choices"]), 4)
        self.assertEqual(result["answer"], "word0")

    def test_ket_vocabulary_mistake_fills_a_missing_meaning(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(server, "VOCABULARY", Path(directory) / "vocabulary.json"), patch.object(server, "load_ket_vocabulary", return_value=[{"id": "ket-because", "word": "because"}]), patch.object(server, "ket_word_detail", return_value={"translation": "因为"}):
            record, _ = server.add_vocabulary_word({"word": "because", "ket_word_id": "ket-because"})
        self.assertEqual(record["meaning"], "因为")

    def test_delete_vocabulary_word_removes_only_the_selected_word(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vocabulary = Path(directory) / "vocabulary.json"
            with patch.object(server, "VOCABULARY", vocabulary):
                first, _ = server.add_vocabulary_word({"word": "bettle"})
                second, _ = server.add_vocabulary_word({"word": "beetle"})
                self.assertEqual(server.delete_vocabulary_word(first["id"]), "bettle")
                self.assertEqual([item["id"] for item in server.load_vocabulary()], [second["id"]])


if __name__ == "__main__":
    unittest.main()
