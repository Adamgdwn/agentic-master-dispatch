import socket
import unittest
from contextlib import closing

from governed_agent_lab.desktop import build_app_url, find_available_port


class DesktopTests(unittest.TestCase):
    def test_build_app_url(self) -> None:
        self.assertEqual(build_app_url("127.0.0.1", 8123), "http://127.0.0.1:8123")

    def test_find_available_port_returns_different_port_when_preferred_is_busy(self) -> None:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            busy_port = int(sock.getsockname()[1])
            available_port = find_available_port("127.0.0.1", busy_port)
        self.assertNotEqual(available_port, busy_port)
        self.assertGreater(available_port, 0)


if __name__ == "__main__":
    unittest.main()
