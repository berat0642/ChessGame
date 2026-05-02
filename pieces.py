from abc import ABC, abstractmethod


class Piece(ABC):
    def __init__(self, is_white: bool):
        self.is_white = is_white

    @abstractmethod
    def can_move(self, start_r, start_c, end_r, end_c, board) -> bool:
        pass

    @abstractmethod
    def symbol(self) -> str:
        pass

    def __repr__(self):
        return self.symbol()


class Pawn(Piece):
    def can_move(self, sr, sc, er, ec, board):
        direction = -1 if self.is_white else 1
        # Bir kare ileri
        if sr + direction == er and sc == ec and board[er][ec] is None:
            return True
        # İlk hamle 2 kare
        start_row = 6 if self.is_white else 1
        if sr == start_row and sr + 2 * direction == er and sc == ec \
                and board[er][ec] is None and board[sr + direction][ec] is None:
            return True
        # Çapraz yeme
        if sr + direction == er and abs(sc - ec) == 1 \
                and board[er][ec] is not None and board[er][ec].is_white != self.is_white:
            return True
        return False

    def symbol(self):
        return "♙" if self.is_white else "♟"


class Rook(Piece):
    def can_move(self, sr, sc, er, ec, board):
        if sr != er and sc != ec:
            return False
        dx = 0 if er == sr else (1 if er > sr else -1)
        dy = 0 if ec == sc else (1 if ec > sc else -1)
        x, y = sr + dx, sc + dy
        while x != er or y != ec:
            if board[x][y] is not None:
                return False
            x += dx
            y += dy
        return board[er][ec] is None or board[er][ec].is_white != self.is_white

    def symbol(self):
        return "♖" if self.is_white else "♜"


class Knight(Piece):
    def can_move(self, sr, sc, er, ec, board):
        dx = abs(er - sr)
        dy = abs(ec - sc)
        if (dx == 2 and dy == 1) or (dx == 1 and dy == 2):
            return board[er][ec] is None or board[er][ec].is_white != self.is_white
        return False

    def symbol(self):
        return "♘" if self.is_white else "♞"


class Bishop(Piece):
    def can_move(self, sr, sc, er, ec, board):
        dx = abs(er - sr)
        dy = abs(ec - sc)
        if dx != dy or dx == 0:
            return False
        xd = 1 if er > sr else -1
        yd = 1 if ec > sc else -1
        x, y = sr + xd, sc + yd
        while x != er and y != ec:
            if board[x][y] is not None:
                return False
            x += xd
            y += yd
        return board[er][ec] is None or board[er][ec].is_white != self.is_white

    def symbol(self):
        return "♗" if self.is_white else "♝"


class Queen(Piece):
    def can_move(self, sr, sc, er, ec, board):
        dx = abs(er - sr)
        dy = abs(ec - sc)
        if sr == er or sc == ec:
            # Kale hareketi
            xd = 0 if er == sr else (1 if er > sr else -1)
            yd = 0 if ec == sc else (1 if ec > sc else -1)
            x, y = sr + xd, sc + yd
            while x != er or y != ec:
                if board[x][y] is not None:
                    return False
                x += xd
                y += yd
        elif dx == dy:
            # Fil hareketi
            xd = 1 if er > sr else -1
            yd = 1 if ec > sc else -1
            x, y = sr + xd, sc + yd
            while x != er and y != ec:
                if board[x][y] is not None:
                    return False
                x += xd
                y += yd
        else:
            return False
        return board[er][ec] is None or board[er][ec].is_white != self.is_white

    def symbol(self):
        return "♕" if self.is_white else "♛"


class King(Piece):
    def can_move(self, sr, sc, er, ec, board):
        dx = abs(er - sr)
        dy = abs(ec - sc)
        if dx <= 1 and dy <= 1 and (dx + dy) > 0:
            return board[er][ec] is None or board[er][ec].is_white != self.is_white
        return False

    def symbol(self):
        return "♔" if self.is_white else "♚"


def initialize_board():
    board = [[None] * 8 for _ in range(8)]
    # Beyaz taşlar (alt)
    board[7] = [Rook(True), Knight(True), Bishop(True), Queen(True),
                King(True), Bishop(True), Knight(True), Rook(True)]
    board[6] = [Pawn(True) for _ in range(8)]
    # Siyah taşlar (üst)
    board[0] = [Rook(False), Knight(False), Bishop(False), Queen(False),
                King(False), Bishop(False), Knight(False), Rook(False)]
    board[1] = [Pawn(False) for _ in range(8)]
    return board
