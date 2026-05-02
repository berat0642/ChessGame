import socket
import threading


class NetworkClient:
    def __init__(self, server_ip, server_port, listener):
        self.listener = listener
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((server_ip, server_port))
        self._running = True
        self._thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._thread.start()

    def _receive_loop(self):
        buf = b""
        try:
            while self._running:
                data = self.sock.recv(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    msg = line.decode("utf-8").strip()
                    if not msg:
                        continue
                    if msg.startswith("MATCHED:"):
                        color = msg.split(":")[1]
                        self.listener.on_color_assigned(color)
                    elif msg == "WAITING_FOR_OPPONENT":
                        self.listener.on_waiting()
                    elif msg == "OPPONENT_LEFT":
                        self.listener.on_opponent_left()
                    else:
                        self.listener.on_move_received(msg)
        except Exception:
            pass
        finally:
            if self._running:
                self.listener.on_opponent_left()

    def send_move(self, move):
        try:
            self.sock.sendall((move + "\n").encode("utf-8"))
        except Exception:
            pass

    def close(self):
        self._running = False
        try:
            self.sock.close()
        except Exception:
            pass
