import socket
import threading
import random

PORT = 5002
sessions = []
session_counter = 0
lock = threading.Lock()


class SClient:
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr
        self.color = None
        self.session = None
        self.has_relay = False

    def send(self, msg):
        try:
            self.conn.sendall((msg + "\n").encode("utf-8"))
        except Exception:
            pass


class GameSession:
    def __init__(self, sid, player1):
        self.sid = sid
        self.player1 = player1
        self.player2 = None
        self.status = "waiting"

    def is_full(self):
        return self.player1 is not None and self.player2 is not None

    def add_player2(self, p2):
        self.player2 = p2
        self.status = "in_game"

    def other(self, client):
        if client is self.player1:
            return self.player2
        if client is self.player2:
            return self.player1
        return None


def client_reader(client):
    """Her istemci icin tek bir okuyucu thread. Hamleleri dinamik olarak
    mevcut oturumdaki rakibe iletir."""
    global session_counter
    try:
        buf = b""
        while True:
            data = client.conn.recv(4096)
            if not data:
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                msg = line.decode("utf-8").strip()
                if msg:
                    session = client.session
                    if session and session.status == "in_game":
                        target = session.other(client)
                        if target:
                            target.send(msg)
    except Exception:
        pass
    finally:
        print(f"Oyuncu ayrildi: {client.addr}")
        client.has_relay = False

        with lock:
            session = client.session
            if not session:
                return

            session.status = "finished"
            if session in sessions:
                sessions.remove(session)

            remaining = session.other(client)
            if remaining is None:
                return
            remaining.send("OPPONENT_LEFT")
            remaining.color = None
            remaining.session = None

            new_session = None
            for s in sessions:
                if not s.is_full() and s.status == "waiting":
                    new_session = s
                    break

            if new_session is None:
                new_session = GameSession(session_counter, remaining)
                session_counter += 1
                sessions.append(new_session)
                remaining.session = new_session
                remaining.send("WAITING_FOR_OPPONENT")
            else:
                new_session.add_player2(remaining)
                remaining.session = new_session
                start_game(new_session)


def start_game(session):
    white_first = random.random() < 0.5
    p1 = session.player1
    p2 = session.player2
    p1.color = "white" if white_first else "black"
    p2.color = "black" if white_first else "white"
    p1.send(f"MATCHED:{p1.color}")
    p2.send(f"MATCHED:{p2.color}")
    if not p1.has_relay:
        p1.has_relay = True
        threading.Thread(target=client_reader, args=(p1,), daemon=True).start()
    if not p2.has_relay:
        p2.has_relay = True
        threading.Thread(target=client_reader, args=(p2,), daemon=True).start()


def main():
    global session_counter
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("0.0.0.0", PORT))
    server_sock.listen()
    print(f"Sunucu baslatildi, port {PORT} dinleniyor...")

    while True:
        conn, addr = server_sock.accept()
        print(f"Yeni oyuncu baglandi: {addr}")
        client = SClient(conn, addr)

        with lock:
            session = None
            for s in sessions:
                if not s.is_full() and s.status == "waiting":
                    session = s
                    break

            if session is None:
                session = GameSession(session_counter, client)
                session_counter += 1
                sessions.append(session)
                client.session = session
                client.send("WAITING_FOR_OPPONENT")
                if not client.has_relay:
                    client.has_relay = True
                    threading.Thread(target=client_reader, args=(client,), daemon=True).start()
            else:
                session.add_player2(client)
                client.session = session
                start_game(session)


if __name__ == "__main__":
    main()
