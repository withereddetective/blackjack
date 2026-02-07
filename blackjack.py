import sys
import os
import random
from time import sleep
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QDialog)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QPropertyAnimation, QPoint, QEasingCurve, QTimer, QSequentialAnimationGroup, QParallelAnimationGroup, QAbstractAnimation

def get_card_pixmap_static(num=None, suit_idx=None, is_back=False):
    # strings and paths in all lowercase
    base_dir = os.path.dirname(os.path.abspath(__file__))
    suits = {1: "clubs", 2: "diamonds", 3: "hearts", 4: "spades"}
    ranks = {1: "a", 11: "j", 12: "q", 13: "k"}
    filename = "card_back.png" if is_back else f"card_{suits[suit_idx]}_{ranks.get(num, f'{num:02d}')}.png"
    path = os.path.join(base_dir, "bj_assets", filename)
    if not os.path.exists(path): return QPixmap() 
    return QPixmap(path).scaled(100, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)

class CardWidget(QLabel):
    def __init__(self, card_data, is_hidden=False, parent=None):
        super().__init__(parent)
        self.card_data = card_data
        self.is_hidden = is_hidden
        self.setPixmap(get_card_pixmap_static(*card_data, is_back=is_hidden))
        self.setFixedSize(100, 150)

    def reveal(self):
        self.is_hidden = False
        self.setPixmap(get_card_pixmap_static(*self.card_data))

class BlackjackGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("pyside6 blackjack")
        # 3. window is now shorter
        self.setFixedSize(600, 550) 
        self.setStyleSheet("background-color: #006400;")
        self.used_cards = set()
        self.player_cards = []
        self.dealer_cards = []
        self.dealer_widgets = []
        self.player_widgets = []
        self.init_ui()
        self.start_game()

    def init_ui(self):
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.main_layout = QVBoxLayout(self.central)
        
        # dealer row
        self.main_layout.addWidget(QLabel("dealer's hand:"))
        self.dealer_container = QWidget()
        self.dealer_container.setMinimumHeight(160)
        self.main_layout.addWidget(self.dealer_container)

        # player row
        self.main_layout.addWidget(QLabel("your hand:"))
        self.player_container = QWidget()
        self.player_container.setMinimumHeight(160)
        self.main_layout.addWidget(self.player_container)

        self.dealer_container.setLayout(None)
        self.player_container.setLayout(None)

        # 4. bigger text for win/loss
        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("color: yellow; font-weight: bold; font-size: 32px;")
        self.main_layout.addWidget(self.result_label)

        self.totals_label = QLabel("")
        self.totals_label.setAlignment(Qt.AlignCenter)
        self.totals_label.setStyleSheet("color: white; font-size: 22px;")
        self.main_layout.addWidget(self.totals_label)

        self.btn_layout = QHBoxLayout()
        self.hit_btn = QPushButton("hit")
        self.stand_btn = QPushButton("stand")
        self.hit_btn.clicked.connect(self.player_hit_logic)
        self.stand_btn.clicked.connect(self.dealer_turn_logic)
        self.btn_layout.addWidget(self.hit_btn)
        self.btn_layout.addWidget(self.stand_btn)
        self.main_layout.addLayout(self.btn_layout)

        for lbl in self.findChildren(QLabel):
            lbl.setStyleSheet(lbl.styleSheet() + "color: white;")

    def draw_card(self):
        while True:
            card = (random.randint(1, 13), random.randint(1, 4))
            if card not in self.used_cards:
                self.used_cards.add(card)
                return card

    def calculate_score(self, cards):
        if not cards:
            return 0
        ranks = [c[0] for c in cards]
        total = sum(min(r, 10) for r in ranks)
        ace_count = ranks.count(1)
        while ace_count > 0 and total + 10 <= 21:
            total += 10
            ace_count -= 1
        return total

    def start_game(self):
        self.used_cards.clear()
        self.player_cards = []
        self.dealer_cards = []
        self.result_label.setText("")
        self.totals_label.setText("")
        
        for w in self.dealer_widgets + self.player_widgets:
            w.deleteLater()
        self.dealer_widgets = []
        self.player_widgets = []
        
        self.hit_btn.setEnabled(False)
        self.stand_btn.setEnabled(False)
        self._dealer_playing = False

        self.intro_group = QSequentialAnimationGroup(self)
        
        # initial cards (dealer fast, player slow)
        for i in range(2):
            c = self.draw_card()
            self.dealer_cards.append(c)
            self.add_animated_card(c, self.dealer_container, self.dealer_widgets, 200, len(self.dealer_cards)==2)
            
        while self.calculate_score(self.dealer_cards) < 16:
            c = self.draw_card()
            self.dealer_cards.append(c)
            self.add_animated_card(c, self.dealer_container, self.dealer_widgets, 200, True)

        for i in range(2):
            c = self.draw_card()
            self.player_cards.append(c)
            self.add_animated_card(c, self.player_container, self.player_widgets, 600, False)
        
        self.intro_group.finished.connect(self.enable_controls)
        self.intro_group.start()

    def add_animated_card(self, data, container, widget_list, duration, hidden):
        # Create card widget with container as parent
        card = CardWidget(data, is_hidden=hidden, parent=container)
        widget_list.append(card)

        # Ensure container has a usable size for positioning
        if container.width() == 0:
            container.setFixedHeight(160)
            container.setFixedWidth(self.width() - 40)

        # layout constants
        card_width = 100
        spacing = 10
        y_pos = 5
        shift = card_width + spacing

        # compute final positions for all cards and place existing cards immediately
        for idx, w in enumerate(widget_list):
            target_x = idx * shift + 10
            target_pos = QPoint(target_x, y_pos)
            if w is card:
                # incoming card start position (off top center)
                start_pos = QPoint(container.width() // 2 - card_width // 2, -150)
                # place the incoming card at the start position (but keep it hidden until animation starts)
                card.move(start_pos)
                card.hide()
            else:
                # place existing card directly at its final slot (no animation)
                w.move(target_pos)

        # Create animation only for the incoming card
        new_index = len(widget_list) - 1
        new_target = QPoint(new_index * shift + 10, y_pos)
        incoming_anim = QPropertyAnimation(card, b"pos", self)
        incoming_anim.setDuration(duration)
        incoming_anim.setStartValue(card.pos())
        incoming_anim.setEndValue(new_target)
        incoming_anim.setEasingCurve(QEasingCurve.OutCubic)

        # show the card when the animation actually starts
        def _on_anim_state(new_state, old_state):
            if new_state == QAbstractAnimation.Running:
                card.show()
                try:
                    incoming_anim.stateChanged.disconnect(_on_anim_state)
                except Exception:
                    pass
        incoming_anim.stateChanged.connect(_on_anim_state)

        # Ensure intro_group exists and is owned by self
        if not hasattr(self, "intro_group") or self.intro_group is None:
            self.intro_group = QSequentialAnimationGroup(self)

        # Add only the incoming animation to the sequence
        self.intro_group.addAnimation(incoming_anim)

    def enable_controls(self):
        if self.calculate_score(self.player_cards) < 21:
            self.hit_btn.setEnabled(True)
            self.stand_btn.setEnabled(True)

    def player_hit_logic(self):
        # disable controls while animating
        self.hit_btn.setEnabled(False)
        self.stand_btn.setEnabled(False)

        c = self.draw_card()
        self.player_cards.append(c)

        # create a fresh animation group for this single card and keep it on self
        self.intro_group = QSequentialAnimationGroup(self)
        self.add_animated_card(c, self.player_container, self.player_widgets, 600, False)

        def after_hit():
            p_score = self.calculate_score(self.player_cards)
            if p_score >= 21:
                # if player reached or exceeded 21, proceed to dealer turn
                # use QTimer.singleShot(0, ...) to ensure we return to the event loop
                QTimer.singleShot(0, self.dealer_turn_logic)
            else:
                self.enable_controls()

        # if there are animations, wait for them; otherwise call immediately
        if self.intro_group.animationCount() == 0:
            after_hit()
        else:
            self.intro_group.finished.connect(after_hit)
            self.intro_group.start()

    def dealer_turn_logic(self):
        if getattr(self, "_dealer_playing", False):
            return
        self._dealer_playing = True

        self.hit_btn.setEnabled(False)
        self.stand_btn.setEnabled(False)

        for w in self.dealer_widgets: 
            try:
                if getattr(w, "is_hidden", False):
                    w.reveal()
            except Exception:
                pass
                
        QTimer.singleShot(200, self.end_game)

    def end_game(self):
        p_score = self.calculate_score(self.player_cards)
        d_score = self.calculate_score(self.dealer_cards)
        
        # 4. win/loss logic (draw if both bust)
        if p_score > 21 and d_score > 21: msg = "it's a draw! (both bust)"
        elif p_score > 21: msg = "you lose! (bust)"
        elif d_score > 21: msg = "you win! (dealer bust)"
        elif p_score > d_score: msg = "you win!"
        elif d_score > p_score: msg = "you lose!"
        else: msg = "it's a tie!"
        
        self.result_label.setText(msg.lower())
        self.totals_label.setText(f"your: {p_score} | dealer: {d_score}")
        # 6. delayed play again
        QTimer.singleShot(2000, self.ask_play_again)

    def ask_play_again(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("play again?")
        l = QVBoxLayout(dlg)
        l.addWidget(QLabel("would you like to play again?"))
        hb = QHBoxLayout()
        y, n = QPushButton("yes"), QPushButton("no")
        y.clicked.connect(dlg.accept); n.clicked.connect(dlg.reject)
        hb.addWidget(y); hb.addWidget(n)
        l.addLayout(hb)
        if dlg.exec(): self.start_game()
        else: self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = BlackjackGUI(); win.show()
    sys.exit(app.exec())
