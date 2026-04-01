import chess
import chess.engine
import pygame
import sys

# ===== CONFIG =====
# Use a raw string to avoid escaping Windows backslashes.
STOCKFISH_PATH = r"C:\Users\admin\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"
THINK_TIME = 0.4
SQUARE_SIZE = 80
PANEL_WIDTH = 80

# ===== PYGAME =====
pygame.init()
screen = pygame.display.set_mode((8 * SQUARE_SIZE + PANEL_WIDTH, 8 * SQUARE_SIZE))
pygame.display.set_caption("Chess AI")

font = pygame.font.SysFont(None, 36)
title_font = pygame.font.SysFont(None, 48)
piece_font = pygame.font.SysFont("Segoe UI Symbol", 56)
small_font = pygame.font.SysFont(None, 24)
clock = pygame.time.Clock()

PIECE_GLYPHS = {
    chess.PAWN: "♙",
    chess.KNIGHT: "♘",
    chess.BISHOP: "♗",
    chess.ROOK: "♖",
    chess.QUEEN: "♕",
    chess.KING: "♔",
}

def choose_side_screen():
    while True:
        screen.fill((30, 30, 30))

        title = title_font.render("Choose Your Side", True, (240, 240, 240))
        screen.blit(title, (120, 40))

        white_rect = pygame.Rect(140, 200, 160, 60)
        black_rect = pygame.Rect(340, 200, 160, 60)

        pygame.draw.rect(screen, (230, 230, 230), white_rect)
        pygame.draw.rect(screen, (50, 50, 50), black_rect)

        white_text = font.render("White", True, (0, 0, 0))
        black_text = font.render("Black", True, (255, 255, 255))
        screen.blit(white_text, (white_rect.x + 45, white_rect.y + 15))
        screen.blit(black_text, (black_rect.x + 45, black_rect.y + 15))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if white_rect.collidepoint(event.pos):
                    return True
                if black_rect.collidepoint(event.pos):
                    return False

# ===== INIT =====
player_is_white = choose_side_screen()
engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
player_color = chess.WHITE if player_is_white else chess.BLACK

board = chess.Board()

# If player is Black, engine plays White first
if not player_is_white:
    move = engine.play(board, chess.engine.Limit(time=THINK_TIME)).move
    board.push(move)

# ===== MOVE QUALITY =====
def classify_move(board):
    info = engine.analyse(board, chess.engine.Limit(time=THINK_TIME), multipv=2)
    best = info[0]["score"].white().score(mate_score=10000)
    second = info[1]["score"].white().score(mate_score=10000)

    diff = abs(best - second)

    if diff > 250:
        return "Brilliant"
    elif diff > 100:
        return "Great"
    else:
        return "Best"

def draw_board():
    colors = [(240, 217, 181), (181, 136, 99)]
    for r in range(8):
        for c in range(8):
            pygame.draw.rect(
                screen,
                colors[(r + c) % 2],
                pygame.Rect(c*SQUARE_SIZE, r*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            )
    # File labels (a-h) and rank labels (1-8)
    for c in range(8):
        label = chr(ord("a") + c)
        text = small_font.render(label, True, (80, 80, 80))
        screen.blit(text, (c*SQUARE_SIZE + 6, 8*SQUARE_SIZE - 22))
    for r in range(8):
        label = str(8 - r)
        text = small_font.render(label, True, (80, 80, 80))
        screen.blit(text, (4, r*SQUARE_SIZE + 4))
    pygame.draw.rect(
        screen,
        (30, 30, 30),
        pygame.Rect(8*SQUARE_SIZE, 0, PANEL_WIDTH, 8*SQUARE_SIZE)
    )

def draw_pieces():
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            is_white = piece.color == chess.WHITE
            fg = (245, 245, 245) if is_white else (20, 20, 20)
            shadow = (30, 30, 30) if is_white else (220, 220, 220)
            glyph = PIECE_GLYPHS.get(piece.piece_type, piece.symbol())
            text = piece_font.render(glyph, True, fg)
            shadow_text = piece_font.render(glyph, True, shadow)
            r = 7 - chess.square_rank(square)
            c = chess.square_file(square)
            center = (c*SQUARE_SIZE + SQUARE_SIZE//2, r*SQUARE_SIZE + SQUARE_SIZE//2)
            shadow_rect = shadow_text.get_rect(center=(center[0] + 2, center[1] + 2))
            text_rect = text.get_rect(center=center)
            screen.blit(shadow_text, shadow_rect)
            screen.blit(text, text_rect)

selected_square = None
dragging_square = None
eval_history = []
last_eval_cp = 0
player_move_stats = {"Brilliant": 0, "Great": 0, "Best": 0, "Good": 0, "Inaccurate": 0, "Mistake": 0, "Blunder": 0}
player_move_drops = []
last_move = None

def get_legal_targets(from_square):
    if from_square is None:
        return []
    return [m.to_square for m in board.legal_moves if m.from_square == from_square]

def draw_highlights():
    if selected_square is not None:
        r = 7 - chess.square_rank(selected_square)
        c = chess.square_file(selected_square)
        pygame.draw.rect(
            screen,
            (120, 180, 120),
            pygame.Rect(c*SQUARE_SIZE, r*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE),
            4
        )
        for target in get_legal_targets(selected_square):
            tr = 7 - chess.square_rank(target)
            tc = chess.square_file(target)
            center = (tc*SQUARE_SIZE + SQUARE_SIZE//2, tr*SQUARE_SIZE + SQUARE_SIZE//2)
            pygame.draw.circle(screen, (50, 120, 200), center, 10)

def draw_last_move_arrow():
    if last_move is None:
        return
    from_sq, to_sq = last_move
    fr = 7 - chess.square_rank(from_sq)
    fc = chess.square_file(from_sq)
    tr = 7 - chess.square_rank(to_sq)
    tc = chess.square_file(to_sq)
    start = (fc*SQUARE_SIZE + SQUARE_SIZE//2, fr*SQUARE_SIZE + SQUARE_SIZE//2)
    end = (tc*SQUARE_SIZE + SQUARE_SIZE//2, tr*SQUARE_SIZE + SQUARE_SIZE//2)

    pygame.draw.line(screen, (200, 60, 60), start, end, 6)

    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = max((dx*dx + dy*dy) ** 0.5, 1)
    ux, uy = dx / length, dy / length
    left = (end[0] - 16*ux + 6*uy, end[1] - 16*uy - 6*ux)
    right = (end[0] - 16*ux - 6*uy, end[1] - 16*uy + 6*ux)
    pygame.draw.polygon(screen, (200, 60, 60), [end, left, right])

def evaluate_board_cp():
    info = engine.analyse(board, chess.engine.Limit(time=THINK_TIME))
    return info["score"].white().score(mate_score=10000)

def classify_drop(drop_cp):
    if drop_cp <= 0:
        return "Brilliant"
    if drop_cp <= 50:
        return "Great"
    if drop_cp <= 150:
        return "Best"
    if drop_cp <= 250:
        return "Good"
    if drop_cp <= 400:
        return "Inaccurate"
    if drop_cp <= 800:
        return "Mistake"
    return "Blunder"

def update_eval_bar():
    global last_eval_cp
    last_eval_cp = evaluate_board_cp()
    eval_history.append(last_eval_cp)

def draw_eval_bar():
    # Clamp for display
    cp = max(-1000, min(1000, last_eval_cp))
    height = 8 * SQUARE_SIZE
    x = 8 * SQUARE_SIZE
    y = 0
    mid = y + height // 2
    offset = int((cp / 1000.0) * (height // 2))
    # White top, Black bottom
    pygame.draw.rect(screen, (245, 245, 245), pygame.Rect(x, y, PANEL_WIDTH, mid - offset))
    pygame.draw.rect(screen, (20, 20, 20), pygame.Rect(x, mid - offset, PANEL_WIDTH, height - (mid - offset)))
    pygame.draw.line(screen, (120, 120, 120), (x, mid), (x + PANEL_WIDTH, mid), 2)
    eval_text = f"{last_eval_cp/100:.2f}"
    text_surf = small_font.render(eval_text, True, (220, 220, 220))
    screen.blit(text_surf, (x + 10, 10))

def show_game_over_screen():
    result = board.result()
    outcome = board.outcome()
    if outcome and outcome.winner is not None:
        winner = "White" if outcome.winner == chess.WHITE else "Black"
    else:
        winner = "Draw"

    total_moves = board.fullmove_number - (0 if board.turn == chess.WHITE else 1)
    avg_drop = sum(player_move_drops) / len(player_move_drops) if player_move_drops else 0

    lines = [
        "Game Over",
        f"Result: {result}",
        f"Winner: {winner}",
        f"Total moves: {total_moves}",
        f"Avg drop: {avg_drop:.1f} cp",
        "Player move quality:",
        f"Brilliant: {player_move_stats['Brilliant']}",
        f"Great: {player_move_stats['Great']}",
        f"Best: {player_move_stats['Best']}",
        f"Good: {player_move_stats['Good']}",
        f"Inaccurate: {player_move_stats['Inaccurate']}",
        f"Mistake: {player_move_stats['Mistake']}",
        f"Blunder: {player_move_stats['Blunder']}",
        "Close the window to exit."
    ]

    while True:
        screen.fill((20, 20, 20))
        y = 40
        for line in lines:
            surf = font.render(line, True, (230, 230, 230))
            screen.blit(surf, (40, y))
            y += 36
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                engine.quit()
                pygame.quit()
                sys.exit()

def try_make_move(from_square, to_square):
    if from_square is None or to_square is None:
        return False

    if board.turn != player_color:
        return False

    eval_before = evaluate_board_cp()
    move = chess.Move(from_square, to_square)

    # Auto-queen promotion if needed
    piece = board.piece_at(from_square)
    if piece and piece.piece_type == chess.PAWN:
        to_rank = chess.square_rank(to_square)
        if (piece.color == chess.WHITE and to_rank == 7) or (piece.color == chess.BLACK and to_rank == 0):
            move = chess.Move(from_square, to_square, promotion=chess.QUEEN)

    if move in board.legal_moves:
        board.push(move)
        global last_move
        last_move = (from_square, to_square)

        eval_after = evaluate_board_cp()
        drop = (eval_before - eval_after) if player_color == chess.WHITE else (eval_after - eval_before)
        quality = classify_drop(drop)
        player_move_stats[quality] += 1
        player_move_drops.append(drop)
        update_eval_bar()

        if board.is_game_over():
            show_game_over_screen()
            return True

        bot_move = engine.play(board, chess.engine.Limit(time=THINK_TIME)).move
        board.push(bot_move)
        last_move = (bot_move.from_square, bot_move.to_square)
        update_eval_bar()

        if board.is_game_over():
            show_game_over_screen()
            return True

        print(f"Bot move: {bot_move.uci()} {quality}")
        return True

    return False

# ===== MAIN LOOP =====
while True:
    draw_board()
    draw_last_move_arrow()
    draw_highlights()
    draw_pieces()
    draw_eval_bar()
    pygame.display.flip()
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            engine.quit()
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            col = x // SQUARE_SIZE
            row = 7 - (y // SQUARE_SIZE)
            square = chess.square(col, row)

            if selected_square is None:
                selected_square = square
                dragging_square = square
            else:
                moved = try_make_move(selected_square, square)
                selected_square = None
                dragging_square = None

        if event.type == pygame.MOUSEBUTTONUP and dragging_square is not None:
            x, y = event.pos
            col = x // SQUARE_SIZE
            row = 7 - (y // SQUARE_SIZE)
            square = chess.square(col, row)
            try_make_move(dragging_square, square)
            selected_square = None
            dragging_square = None
