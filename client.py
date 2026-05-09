import sys
import configparser
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QPushButton,
    QLabel, QVBoxLayout, QHBoxLayout, QMessageBox, QStackedWidget,
    QSizePolicy, QFrame, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QSize, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

from pieces import initialize_board, King, Pawn, Queen
from network_client import NetworkClient


# ---------- Config ----------
def load_config():
    cfg = configparser.ConfigParser()
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
    if os.path.exists(cfg_path):
        cfg.read(cfg_path)
    ip = cfg.get("server", "ip", fallback="127.0.0.1")
    port = cfg.getint("server", "port", fallback=5002)
    return ip, port


# ---------- Signals bridge (thread-safe) ----------
class Signals(QObject):
    color_assigned = pyqtSignal(str)
    waiting = pyqtSignal()
    opponent_left = pyqtSignal()
    move_received = pyqtSignal(str)


# ---------- Start Screen ----------
class StartScreen(QWidget):
    play_clicked = pyqtSignal(str, int)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("♚ Satranç ♚")
        title.setFont(QFont("Arial", 42, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)

        subtitle = QLabel("Çevrimiçi İki Kişilik Satranç Oyunu")
        subtitle.setFont(QFont("Arial", 16))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # IP input
        ip_layout = QHBoxLayout()
        ip_label = QLabel("Sunucu IP:")
        ip_label.setFont(QFont("Arial", 13))
        self.ip_input = QLineEdit()
        default_ip, default_port = load_config()
        self.ip_input.setText(default_ip)
        self.ip_input.setFont(QFont("Arial", 13))
        self.ip_input.setFixedWidth(200)
        ip_layout.addStretch()
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_input)
        ip_layout.addStretch()
        layout.addLayout(ip_layout)

        # Port input
        port_layout = QHBoxLayout()
        port_label = QLabel("Port:")
        port_label.setFont(QFont("Arial", 13))
        self.port_input = QLineEdit()
        self.port_input.setText(str(default_port))
        self.port_input.setFont(QFont("Arial", 13))
        self.port_input.setFixedWidth(200)
        port_layout.addStretch()
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)
        port_layout.addStretch()
        layout.addLayout(port_layout)

        layout.addSpacing(10)

        play_btn = QPushButton("Oyna")
        play_btn.setFont(QFont("Arial", 18, QFont.Bold))
        play_btn.setFixedSize(220, 60)
        play_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        play_btn.clicked.connect(self._on_play)
        layout.addWidget(play_btn, alignment=Qt.AlignCenter)

        layout.addSpacing(30)
        info = QLabel("Fatih Sultan Mehmet Vakıf Üniversitesi\nBilgisayar Ağları Proje - 2026")
        info.setFont(QFont("Arial", 10))
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(info)

        self.setLayout(layout)

    def _on_play(self):
        ip = self.ip_input.text().strip()
        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            port = 5002
        self.play_clicked.emit(ip, port)


# ---------- End Screen ----------
class EndScreen(QWidget):
    replay_clicked = pyqtSignal()
    quit_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        self.result_label = QLabel("")
        self.result_label.setFont(QFont("Arial", 36, QFont.Bold))
        self.result_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.result_label)

        self.detail_label = QLabel("")
        self.detail_label.setFont(QFont("Arial", 16))
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(self.detail_label)

        layout.addSpacing(20)

        btn_layout = QHBoxLayout()
        replay_btn = QPushButton("Tekrar Oyna")
        replay_btn.setFont(QFont("Arial", 16, QFont.Bold))
        replay_btn.setFixedSize(200, 55)
        replay_btn.setStyleSheet("""
            QPushButton {
                background-color: #2980b9;
                color: white;
                border-radius: 10px;
            }
            QPushButton:hover { background-color: #3498db; }
        """)
        replay_btn.clicked.connect(self.replay_clicked)
        btn_layout.addWidget(replay_btn)

        quit_btn = QPushButton("Çıkış")
        quit_btn.setFont(QFont("Arial", 16, QFont.Bold))
        quit_btn.setFixedSize(200, 55)
        quit_btn.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                color: white;
                border-radius: 10px;
            }
            QPushButton:hover { background-color: #e74c3c; }
        """)
        quit_btn.clicked.connect(self.quit_clicked)
        btn_layout.addWidget(quit_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def set_result(self, title, detail):
        self.result_label.setText(title)
        self.detail_label.setText(detail)


# ---------- Chess Board Widget ----------
LIGHT = "#F0D9B5"
DARK = "#B58863"
HIGHLIGHT = "#7FC97F"
INVALID_HIGHLIGHT = "#E74C3C"
SELECTED = "#F6F669"


class ChessBoardWidget(QWidget):
    game_over = pyqtSignal(str, str)  # title, detail
    opponent_left = pyqtSignal()
    timeout = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.board = None
        self.squares = [[None] * 8 for _ in range(8)]
        self.selected = (-1, -1)
        self.is_white_turn = True
        self.is_my_turn = False
        self.i_am_white = True
        self.client = None
        self.signals = Signals()
        self.captured_white = []
        self.captured_black = []

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)

        # Top bar
        top_bar = QHBoxLayout()
        self.captured_black_label = QLabel("")
        self.captured_black_label.setFont(QFont("Arial Unicode MS", 18))
        top_bar.addWidget(self.captured_black_label)
        top_bar.addStretch()
        self.turn_label = QLabel("Bağlanıyor...")
        self.turn_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.turn_label.setAlignment(Qt.AlignCenter)
        top_bar.addWidget(self.turn_label)
        top_bar.addStretch()
        self.role_label = QLabel("")
        self.role_label.setFont(QFont("Arial", 13))
        top_bar.addWidget(self.role_label)
        main_layout.addLayout(top_bar)

        # Board grid
        self.grid = QGridLayout()
        self.grid.setSpacing(0)
        for r in range(8):
            for c in range(8):
                btn = QPushButton()
                btn.setFixedSize(75, 75)
                btn.setFont(QFont("Arial Unicode MS", 32))
                btn.setFlat(True)
                btn.setAutoFillBackground(True)
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setStyleSheet(self._square_style(r, c))
                btn.clicked.connect(lambda _, row=r, col=c: self._on_square_click(row, col))
                self.squares[r][c] = btn
                self.grid.addWidget(btn, r, c)
        main_layout.addLayout(self.grid)

        # Bottom bar
        bottom_bar = QHBoxLayout()
        self.captured_white_label = QLabel("")
        self.captured_white_label.setFont(QFont("Arial Unicode MS", 18))
        bottom_bar.addWidget(self.captured_white_label)
        bottom_bar.addStretch()
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Arial", 12))
        self.status_label.setStyleSheet("color: #7f8c8d;")
        bottom_bar.addWidget(self.status_label)
        main_layout.addLayout(bottom_bar)

        self.setLayout(main_layout)

    def _square_style(self, r, c, bg=None, text_color=None):
        color = bg if bg else (LIGHT if (r + c) % 2 == 0 else DARK)
        style = f"background-color: {color}; border: none; font-size: 32px;"
        if text_color:
            style += f" color: {text_color};"
        return style

    def _piece_color(self, r, c):
        piece = self.board[r][c]
        if piece:
            return "#FFFFFF" if piece.is_white else "#000000"
        return None

    def _connect_signals(self):
        self.signals.color_assigned.connect(self._handle_color_assigned)
        self.signals.waiting.connect(self._handle_waiting)
        self.signals.opponent_left.connect(self._handle_opponent_left)
        self.signals.move_received.connect(self._handle_move_received)

    # ---- Network listener interface ----
    def on_color_assigned(self, color):
        self.signals.color_assigned.emit(color)

    def on_waiting(self):
        self.signals.waiting.emit()

    def on_opponent_left(self):
        self.signals.opponent_left.emit()

    def on_move_received(self, move):
        self.signals.move_received.emit(move)

    # ---- Signal handlers (main thread) ----
    def _handle_color_assigned(self, color):
        if hasattr(self, 'waiting_timer') and self.waiting_timer.isActive():
            self.waiting_timer.stop()
        self.board = initialize_board()
        self.is_white_turn = True
        self.selected = (-1, -1)
        self.captured_white = []
        self.captured_black = []
        self.captured_white_label.setText("")
        self.captured_black_label.setText("")
        self.i_am_white = (color == "white")
        self.is_my_turn = self.i_am_white
        self.role_label.setText("Siz: " + ("Beyaz" if self.i_am_white else "Siyah"))
        self.turn_label.setText("Sıra: Beyaz")
        self.status_label.setText("Renginiz: " + ("Beyaz ♔" if self.i_am_white else "Siyah ♚"))
        self._refresh_board()
        self._enable_board(True)

    def _handle_waiting(self):
        self.turn_label.setText("Rakip bekleniyor...")
        self.status_label.setText("Bağlantı kuruldu, rakip aranıyor...")
        self._enable_board(False)
        if hasattr(self, 'waiting_timer') and self.waiting_timer.isActive():
            self.waiting_timer.stop()
        self.waiting_timer = QTimer()
        self.waiting_timer.setSingleShot(True)
        self.waiting_timer.timeout.connect(self._on_waiting_timeout)
        self.waiting_timer.start(10000)  # 10 saniye

    def _handle_opponent_left(self):
        QMessageBox.information(self, "Rakip Ayrıldı", "Rakibiniz sistemden düştü.\nTamam'a bastığınızda lobiye döneceksiniz.")
        self.opponent_left.emit()

    def _on_waiting_timeout(self):
        QMessageBox.information(self, "Rakip Bulunamadı", "10 saniye içinde rakip bulunamadı.\nTamam'a bastığınızda lobiye döneceksiniz.")
        self.timeout.emit()

    def _handle_move_received(self, move):
        self._receive_move(move)
        self.is_my_turn = True

    # ---- Game logic ----
    def start_game(self, server_ip, server_port):
        self.board = initialize_board()
        self.is_white_turn = True
        self.is_my_turn = False
        self.selected = (-1, -1)
        self.captured_white = []
        self.captured_black = []
        self.captured_white_label.setText("")
        self.captured_black_label.setText("")
        self.turn_label.setText("Bağlanıyor...")
        self.role_label.setText("")
        self.status_label.setText("")
        self._refresh_board()
        self._enable_board(False)

        try:
            self.client = NetworkClient(server_ip, server_port, self)
        except Exception as e:
            QMessageBox.critical(self, "Bağlantı Hatası",
                                 f"Sunucuya bağlanılamadı:\n{e}")

    def _refresh_board(self):
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                self.squares[r][c].setText(piece.symbol() if piece else "")
                self.squares[r][c].setStyleSheet(self._square_style(r, c, text_color=self._piece_color(r, c)))

    def _enable_board(self, enabled):
        for r in range(8):
            for c in range(8):
                self.squares[r][c].setEnabled(enabled)

    def _clear_highlights(self):
        for r in range(8):
            for c in range(8):
                self.squares[r][c].setStyleSheet(self._square_style(r, c, text_color=self._piece_color(r, c)))

    def _on_square_click(self, row, col):
        if not self.is_my_turn:
            return

        piece = self.board[row][col]
        sr, sc = self.selected

        # Kendi taşına tıklama -> seç ve olası hamleleri göster
        if piece and piece.is_white == self.is_white_turn and piece.is_white == self.i_am_white:
            self._clear_highlights()
            self.selected = (row, col)
            self.squares[row][col].setStyleSheet(self._square_style(row, col, SELECTED, text_color=self._piece_color(row, col)))

            for r in range(8):
                for c in range(8):
                    if piece.can_move(row, col, r, c, self.board):
                        orig = self.board[r][c]
                        self.board[r][c] = piece
                        self.board[row][col] = None
                        in_check = self._is_king_in_check(self.is_white_turn)
                        self.board[row][col] = piece
                        self.board[r][c] = orig
                        color = INVALID_HIGHLIGHT if in_check else HIGHLIGHT
                        self.squares[r][c].setStyleSheet(self._square_style(r, c, color, text_color=self._piece_color(r, c)))
            return

        # Hedef kareye tıklama -> hamle yap
        if sr != -1:
            sel_piece = self.board[sr][sc]
            if sel_piece and sel_piece.is_white == self.is_white_turn \
                    and sel_piece.can_move(sr, sc, row, col, self.board):
                orig_target = self.board[row][col]
                self.board[row][col] = sel_piece
                self.board[sr][sc] = None

                if self._is_king_in_check(self.is_white_turn):
                    self.board[sr][sc] = sel_piece
                    self.board[row][col] = orig_target
                    QMessageBox.warning(self, "Geçersiz Hamle",
                                        "Kendinizi şah altında bırakamazsınız!")
                else:
                    # Piyon terfisi
                    if isinstance(sel_piece, Pawn):
                        if (sel_piece.is_white and row == 0) or (not sel_piece.is_white and row == 7):
                            self.board[row][col] = Queen(sel_piece.is_white)

                    # Yenen taş
                    if orig_target:
                        if orig_target.is_white:
                            self.captured_white.append(orig_target.symbol())
                            self.captured_white_label.setText(" ".join(self.captured_white))
                        else:
                            self.captured_black.append(orig_target.symbol())
                            self.captured_black_label.setText(" ".join(self.captured_black))

                    move_str = f"{sr},{sc}->{row},{col}"
                    if self.client:
                        self.client.send_move(move_str)
                    self.is_my_turn = False

                    self.is_white_turn = not self.is_white_turn
                    self.turn_label.setText("Sıra: " + ("Beyaz" if self.is_white_turn else "Siyah"))
                    self._refresh_board()
                    self._check_game_state()

                self.selected = (-1, -1)
                self._clear_highlights()

    def _receive_move(self, move):
        try:
            parts = move.split("->")
            fr, fc = map(int, parts[0].split(","))
            tr, tc = map(int, parts[1].split(","))

            moving = self.board[fr][fc]
            captured = self.board[tr][tc]

            # Yenen taşı kaydet
            if captured:
                if captured.is_white:
                    self.captured_white.append(captured.symbol())
                    self.captured_white_label.setText(" ".join(self.captured_white))
                else:
                    self.captured_black.append(captured.symbol())
                    self.captured_black_label.setText(" ".join(self.captured_black))

            self.board[tr][tc] = moving
            self.board[fr][fc] = None

            # Piyon terfisi
            if isinstance(moving, Pawn):
                if (moving.is_white and tr == 0) or (not moving.is_white and tr == 7):
                    self.board[tr][tc] = Queen(moving.is_white)

            self.is_white_turn = not self.is_white_turn
            self.turn_label.setText("Sıra: " + ("Beyaz" if self.is_white_turn else "Siyah"))
            self._refresh_board()
            self._check_game_state()
        except Exception:
            pass

    def _is_king_in_check(self, white_king):
        kr, kc = -1, -1
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if isinstance(p, King) and p.is_white == white_king:
                    kr, kc = r, c
        if kr == -1:
            return True
        for r in range(8):
            for c in range(8):
                att = self.board[r][c]
                if att and att.is_white != white_king:
                    if att.can_move(r, c, kr, kc, self.board):
                        return True
        return False

    def _has_any_valid_move(self, is_white):
        for sr in range(8):
            for sc in range(8):
                p = self.board[sr][sc]
                if p and p.is_white == is_white:
                    for dr in range(8):
                        for dc in range(8):
                            if p.can_move(sr, sc, dr, dc, self.board):
                                orig = self.board[dr][dc]
                                self.board[dr][dc] = p
                                self.board[sr][sc] = None
                                in_check = self._is_king_in_check(is_white)
                                self.board[sr][sc] = p
                                self.board[dr][dc] = orig
                                if not in_check:
                                    return True
        return False

    def _check_game_state(self):
        if self._is_king_in_check(self.is_white_turn):
            self.turn_label.setText(
                "ŞAH! Sıra: " + ("Beyaz" if self.is_white_turn else "Siyah"))
            if not self._has_any_valid_move(self.is_white_turn):
                winner = "Siyah" if self.is_white_turn else "Beyaz"
                self.game_over.emit("ŞAH MAT!", f"Kazanan: {winner}")
        else:
            if not self._has_any_valid_move(self.is_white_turn):
                self.game_over.emit("PAT!", "Oyun berabere bitti.")


# ---------- Main Window ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Satranç - Bilgisayar Ağları Proje")
        self.setFixedSize(660, 740)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.start_screen = StartScreen()
        self.chess_widget = ChessBoardWidget()
        self.end_screen = EndScreen()

        self.stack.addWidget(self.start_screen)    # 0
        self.stack.addWidget(self.chess_widget)     # 1
        self.stack.addWidget(self.end_screen)       # 2

        self.start_screen.play_clicked.connect(self._on_play)
        self.chess_widget.game_over.connect(self._on_game_over)
        self.chess_widget.opponent_left.connect(self._on_opponent_left)
        self.chess_widget.timeout.connect(self._on_timeout)
        self.end_screen.replay_clicked.connect(self._on_replay)
        self.end_screen.quit_clicked.connect(self.close)

        self.stack.setCurrentIndex(0)

    def _on_play(self, ip, port):
        self.stack.setCurrentIndex(1)
        self.chess_widget.start_game(ip, port)

    def _on_game_over(self, title, detail):
        self.end_screen.set_result(title, detail)
        self.stack.setCurrentIndex(2)

    def _on_opponent_left(self):
        if self.chess_widget.client:
            self.chess_widget.client.close()
        self.stack.setCurrentIndex(0)

    def _on_timeout(self):
        if self.chess_widget.client:
            self.chess_widget.client.close()
        self.stack.setCurrentIndex(0)

    def _on_replay(self):
        if self.chess_widget.client:
            self.chess_widget.client.close()
        self.stack.setCurrentIndex(0)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
