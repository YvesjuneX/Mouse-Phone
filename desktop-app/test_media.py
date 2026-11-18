import asyncio
import json
import unittest
from unittest.mock import patch
import server


class Connection:
    remote_address = ('test', 0)

    def __init__(self, action):
        self.messages = iter([json.dumps({'type': 'media', 'action': action})] * 2)

    async def send(self, message):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.messages)
        except StopIteration:
            raise StopAsyncIteration


class MediaTests(unittest.TestCase):
    def test_two_taps_send_two_complete_presses_in_each_mode(self):
        for action, key in [('play_pause', 'playpause'), ('play_pause_video', 'space'), ('play_pause_youtube', 'k')]:
            with self.subTest(action=action), patch.object(server.pyautogui, 'keyDown') as down, patch.object(server.pyautogui, 'keyUp') as up:
                asyncio.run(server.handle_client(Connection(action)))
                self.assertEqual(down.call_count, 2)
                self.assertEqual(up.call_count, 2)
                down.assert_called_with(key, _pause=False)
                up.assert_called_with(key, _pause=False)


if __name__ == '__main__':
    unittest.main()
