import unittest
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app import parse_whatsapp_txt, _match_line, _parse_dt

class TestParser(unittest.TestCase):
    def test_line_matching_formats(self):
        # Android English 24h
        match1 = _match_line("28/07/2026, 14:30 - Alice: Hello")
        self.assertIsNotNone(match1)
        self.assertEqual(match1, ("28/07/2026", "14:30", "Alice", "Hello"))

        # iOS English 12h
        match2 = _match_line("[28/07/26, 2:30:15 PM] Bob: Hi there")
        self.assertIsNotNone(match2)
        self.assertEqual(match2, ("28/07/26", "2:30:15 PM", "Bob", "Hi there"))

        # Android Spanish
        match3 = _match_line("28-07-26 14:30 - Carlos: Hola")
        self.assertIsNotNone(match3)
        self.assertEqual(match3, ("28-07-26", "14:30", "Carlos", "Hola"))

        # iOS French
        match4 = _match_line("[28.07.2026 14:30:00] Danielle: Bonjour")
        self.assertIsNotNone(match4)
        self.assertEqual(match4, ("28.07.2026", "14:30:00", "Danielle", "Bonjour"))

    def test_parse_datetime(self):
        dt1 = _parse_dt("28/07/2026", "14:30")
        self.assertEqual(dt1.year, 2026)
        self.assertEqual(dt1.month, 7)
        self.assertEqual(dt1.day, 28)
        self.assertEqual(dt1.hour, 14)
        self.assertEqual(dt1.minute, 30)

        dt2 = _parse_dt("28/07/26", "2:30:15 PM")
        self.assertEqual(dt2.hour, 14)
        self.assertEqual(dt2.minute, 30)
        self.assertEqual(dt2.second, 15)

        # Malformed or out of range components
        with self.assertRaises((ValueError, IndexError)):
            _parse_dt("invalid", "14:30")

    def test_parser_logical_stitching(self):
        chat_txt = (
            "28/07/2026, 14:30 - Alice: Line 1\n"
            "Line 2 of multi-line\n"
            "28/07/2026, 14:31 - Bob: reacted with ❤️\n"
            "28/07/2026, 14:32 - Bob: Line 3\n"
        )
        msgs = parse_whatsapp_txt(chat_txt, "TestChat")
        
        # Should result in 2 messages (reaction stitched to Alice)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["content"], "Line 1\nLine 2 of multi-line")
        self.assertEqual(msgs[0]["sender"], "Alice")
        
        # Check reaction stitched to Alice (since Bob reacted immediately after)
        self.assertIn("reactions", msgs[0])
        self.assertEqual(msgs[0]["reactions"][0]["sender"], "Bob")
        self.assertEqual(msgs[0]["reactions"][0]["emoji"], "❤️")
        
        self.assertEqual(msgs[1]["content"], "Line 3")
        self.assertEqual(msgs[1]["sender"], "Bob")

    def test_i18n_attachment_parsing(self):
        # Multiple locales for (file attached)
        attachments = [
            ("photo.jpg (file attached)", "photo.jpg", "image"),
            ("video.mp4 (archivo adjunto)", "video.mp4", "video"),
            ("audio.opus (Datei angehängt)", "audio.opus", "audio"),
            ("document.pdf (fichier joint)", "document.pdf", "file"),
            ("record.wav (arquivo anexado)", "record.wav", "audio"),
            ("image.png (file allegato)", "image.png", "image"),
        ]
        
        for raw, fname, mtype in attachments:
            chat = f"28/07/2026, 14:30 - Alice: {raw}"
            msgs = parse_whatsapp_txt(chat, "TestChat")
            self.assertEqual(len(msgs), 1)
            msg = msgs[0]
            self.assertEqual(msg["type"], mtype)
            if mtype == "audio":
                self.assertIn(fname, msg["audio_file"])
            elif mtype == "file":
                self.assertEqual(msg["filename"], fname)
            else:
                self.assertIn(fname, msg["media_file"])

    def test_caption_extraction(self):
        chat = (
            "28/07/2026, 14:30 - Alice: photo.jpg (file attached)\n"
            "This is a cool image caption!"
        )
        msgs = parse_whatsapp_txt(chat, "TestChat")
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["type"], "image")
        self.assertEqual(msgs[0]["caption"], "This is a cool image caption!")

    def test_unparseable_lines_skip(self):
        chat = (
            "28/07/2026, 14:30 - Alice: Hi\n"
            "28/00/2026, 14:30 - Malformed Date: Skip me\n"
            "28/07/2026, 14:31 - Alice: Bye\n"
        )
        msgs = parse_whatsapp_txt(chat, "TestChat")
        # Should successfully skip the malformed line and parse Alice's messages
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["content"], "Hi")
        self.assertEqual(msgs[1]["content"], "Bye")

    def test_xss_payload_parsing(self):
        # Deliberately malicious payloads targeting breaking out of scripts/html tags
        xss_sender = "</script><script>alert('xss')</script>"
        xss_content = "<img src=x onerror=alert(1)>"
        xss_caption = "caption </script><script>"
        
        chat = (
            f"28/07/2026, 14:30 - {xss_sender}: photo.jpg (file attached)\n"
            f"{xss_caption}\n"
            f"28/07/2026, 14:31 - Bob: {xss_content}\n"
            f"28/07/2026, 14:32 - Bob: reacted with ❤️\n"
        )
        
        msgs = parse_whatsapp_txt(chat, "TestChat")
        self.assertEqual(len(msgs), 2)
        
        self.assertEqual(msgs[0]["sender"], xss_sender)
        self.assertEqual(msgs[0]["caption"], xss_caption)
        self.assertEqual(msgs[1]["content"], xss_content)

    def test_i18n_skip_content_heuristics(self):
        # Spanish/German/French omitted & deleted templates
        skipped_scenarios = [
            "<Media omitted>",
            "<Multimedia omitido>",
            "<Medien ausgeschlossen>",
            "This message was deleted",
            "Este mensaje fue eliminado",
            "Diese Nachricht wurde gelöscht",
            "Ce message a été supprimé"
        ]
        for content in skipped_scenarios:
            chat = f"28/07/2026, 14:30 - Alice: {content}"
            msgs = parse_whatsapp_txt(chat, "TestChat")
            self.assertEqual(len(msgs), 0)

if __name__ == "__main__":
    unittest.main()
