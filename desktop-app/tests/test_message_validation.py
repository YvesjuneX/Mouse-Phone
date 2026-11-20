import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mouse_phone.security.message_validation import MAX_DELTA, MessageValidationError, validate_message


class MessageValidationTests(unittest.TestCase):
    def test_all_supported_control_messages_are_accepted(self):
        for message in ({"type": "move", "dx": 1.5, "dy": -2}, {"type": "move_end"}, {"type": "click", "button": "left"}, {"type": "scroll", "amount": 20}, {"type": "media", "action": "play_pause"}):
            self.assertEqual(validate_message(message), message)

    def test_rejects_unknown_actions_invalid_types_and_unexpected_fields(self):
        invalid = ({"type": "shell", "command": "calc"}, {"type": "move", "dx": float("inf"), "dy": 0}, {"type": "move", "dx": MAX_DELTA + 1, "dy": 0}, {"type": "scroll", "amount": 1.5}, {"type": "click", "button": "right"}, {"type": "media", "action": "space"}, {"type": "move_end", "extra": True})
        for message in invalid:
            with self.subTest(message=message):
                with self.assertRaises(MessageValidationError): validate_message(message)

    def test_rejects_invalid_encrypted_envelopes_and_replayed_counter_values(self):
        for message in ({"type": "secure", "counter": 0, "nonce": "short", "data": "x"}, {"type": "secure", "counter": True, "nonce": "a" * 16, "data": "x"}, {"type": "secure", "counter": 1, "nonce": "a" * 16, "data": "x", "extra": 1}):
            with self.subTest(message=message):
                with self.assertRaises(MessageValidationError): validate_message(message)
