import sys
import os
import random
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QDialog,
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QPoint, QEasingCurve,
    QTimer, QSequentialAnimationGroup, QAbstractAnimation, QRect,
)


# ----------------------------------------------------------------------
# card image loading (bj_assets)
# ----------------------------------------------------------------------
def get_card_pixmap_static(num=None, suit_idx=None, is_back=False):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    suits = {1: "clubs", 2: "diamonds", 3: "hearts", 4: "spades"}
    ranks = {1: "a", 11: "j", 12: "q", 13: "k"}

    if is_back:
        filename = "card_back.png"
    else:
        rank_str = ranks.get(num, f"{num:02d}")
        filename = f"card_{suits[suit_idx]}_{rank_str}.png"

    path = os.path.join(base_dir, "bj_assets", filename)
    if not os.path.exists(path):
        return QPixmap()

    return QPixmap(path).scaled(100, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)


# ----------------------------------------------------------------------
# card widget with flip animation for hidden → face-up
# ----------------------------------------------------------------------
class CardWidget(QLabel):
    def __init__(self, card_data, is_hidden=False, parent=None):
        super().__init__(parent)
        self.card_data = card_data  # (num, suit_idx)
        self.is_hidden = is_hidden
        self.setPixmap(get_card_pixmap_static(*card_data, is_back=is_hidden))
        self.setFixedSize(100, 150)

    def reveal(self):
        if not self.is_hidden:
            return

        self.is_hidden = False

        parent = self.parent()
        if parent is None:
            self.setPixmap(get_card_pixmap_static(*self.card_data))
            return

        original_rect = self.geometry()
        center = original_rect.center()

        narrow_rect = QRect(original_rect)
        narrow_rect.setWidth(10)
        narrow_rect.moveCenter(center)

        shrink_anim = QPropertyAnimation(self, b"geometry")
        shrink_anim.setDuration(150)
        shrink_anim.setStartValue(original_rect)
        shrink_anim.setEndValue(narrow_rect)
        shrink_anim.setEasingCurve(QEasingCurve.InCubic)

        expand_anim = QPropertyAnimation(self, b"geometry")
        expand_anim.setDuration(150)
        expand_anim.setStartValue(narrow_rect)
        expand_anim.setEndValue(original_rect)
        expand_anim.setEasingCurve(QEasingCurve.OutCubic)

        def swap_pixmap():
            self.setPixmap(get_card_pixmap_static(*self.card_data))

        shrink_anim.finished.connect(swap_pixmap)

        group = QSequentialAnimationGroup(self)
        group.addAnimation(shrink_anim)
        group.addAnimation(expand_anim)
        group.start(QAbstractAnimation.DeleteWhenStopped)


# ----------------------------------------------------------------------
# main blackjack GUI
# ----------------------------------------------------------------------
class BlackjackGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Blackjack")
        self.setFixedSize(600, 550)
        self.setStyleSheet("background-color: #006400;")

        self.used_cards = set()
        self.player_cards = []
        self.dealer_cards = []
        self.player_widgets = []
        self.dealer_widgets = []

        self.dealer_has_stood = False
        self.dealer_stand_label = None
        self._dealer_playing = False
        self.intro_group = None

        self.init_ui()
        self.start_game()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------
    def init_ui(self):
        self.central = QWidget()
        self.setCentralWidget(self.central)

        self.main_layout = QVBoxLayout(self.central)

        dealer_label = QLabel("Dealer's hand:")
        dealer_label.setStyleSheet("color: white; font-size: 18px;")
        self.main_layout.addWidget(dealer_label)

        self.dealer_container = QWidget()
        self.dealer_container.setMinimumHeight(160)
        self.dealer_container.setLayout(None)
        self.main_layout.addWidget(self.dealer_container)

        player_label = QLabel("Your hand:")
        player_label.setStyleSheet("color: white; font-size: 18px;")
        self.main_layout.addWidget(player_label)

        self.player_container = QWidget()
        self.player_container.setMinimumHeight(160)
        self.player_container.setLayout(None)
        self.main_layout.addWidget(self.player_container)

        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("color: yellow; font-weight: bold; font-size: 32px;")
        self.main_layout.addWidget(self.result_label)

        self.totals_label = QLabel("")
        self.totals_label.setAlignment(Qt.AlignCenter)
        self.totals_label.setStyleSheet("color: white; font-size: 22px;")
        self.main_layout.addWidget(self.totals_label)

        self.btn_layout = QHBoxLayout()
        self.hit_btn = QPushButton("Hit")
        self.stand_btn = QPushButton("Stand")
        self.hit_btn.clicked.connect(self.player_hit_logic)
        self.stand_btn.clicked.connect(self.dealer_turn_logic)
        self.btn_layout.addWidget(self.hit_btn)
        self.btn_layout.addWidget(self.stand_btn)
        self.main_layout.addLayout(self.btn_layout)

    # ------------------------------------------------------------------
    # core game helpers
    # ------------------------------------------------------------------
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

    def player_has_blackjack(self):
        return (
            len(self.player_cards) == 2 and
            self.calculate_score(self.player_cards) == 21
        )

    # ------------------------------------------------------------------
    # game start / reset
    # ------------------------------------------------------------------
    def start_game(self):
        self.used_cards.clear()
        self.player_cards = []
        self.dealer_cards = []
        self.result_label.setText("")
        self.totals_label.setText("")
        self.dealer_has_stood = False
        self._dealer_playing = False

        if self.dealer_stand_label is not None:
            self.dealer_stand_label.hide()

        for w in self.dealer_widgets + self.player_widgets:
            w.deleteLater()
        self.dealer_widgets = []
        self.player_widgets = []

        self.hit_btn.setEnabled(False)
        self.stand_btn.setEnabled(False)

        self.intro_group = QSequentialAnimationGroup(self)

        # dealer: exactly 2 cards, first up, second down (hidden), no pre-play auto-hitting
        for i in range(2):
            c = self.draw_card()
            self.dealer_cards.append(c)
            hidden = (i == 1)
            self.add_animated_card(c, self.dealer_container, self.dealer_widgets, 200, hidden)

        # player: 2 cards, both face up
        for _ in range(2):
            c = self.draw_card()
            self.player_cards.append(c)
            self.add_animated_card(c, self.player_container, self.player_widgets, 600, False)

        def after_deal():
            if self.player_has_blackjack():
                # natural blackjack → auto-stand
                self.dealer_turn_logic()
            else:
                self.enable_controls()

        self.intro_group.finished.connect(after_deal)
        self.intro_group.start()

    # ------------------------------------------------------------------
    # card animation helper
    # ------------------------------------------------------------------
    def add_animated_card(self, data, container, widget_list, duration, hidden):
        card = CardWidget(data, is_hidden=hidden, parent=container)
        widget_list.append(card)

        if container.width() == 0:
            container.setFixedHeight(160)
            container.setFixedWidth(self.width() - 40)

        card_width = 100
        spacing = 10
        y_pos = 5
        shift = card_width + spacing

        for idx, w in enumerate(widget_list):
            target_x = idx * shift + 10
            target_pos = QPoint(target_x, y_pos)
            if w is card:
                start_pos = QPoint(container.width() // 2 - card_width // 2, -150)
                card.move(start_pos)
                card.hide()
            else:
                w.move(target_pos)

        new_index = len(widget_list) - 1
        new_target = QPoint(new_index * shift + 10, y_pos)

        incoming_anim = QPropertyAnimation(card, b"pos", self)
        incoming_anim.setDuration(duration)
        incoming_anim.setStartValue(card.pos())
        incoming_anim.setEndValue(new_target)
        incoming_anim.setEasingCurve(QEasingCurve.OutCubic)

        def _on_anim_state(new_state, _old_state):
            if new_state == QAbstractAnimation.Running:
                card.show()
                try:
                    incoming_anim.stateChanged.disconnect(_on_anim_state)
                except Exception:
                    pass

        incoming_anim.stateChanged.connect(_on_anim_state)

        if self.intro_group is None:
            self.intro_group = QSequentialAnimationGroup(self)

        self.intro_group.addAnimation(incoming_anim)

    # ------------------------------------------------------------------
    # dealer STAND! label
    # ------------------------------------------------------------------
    def show_dealer_stand_label(self):
        if self.dealer_stand_label is None:
            self.dealer_stand_label = QLabel("STAND!", self.dealer_container)
            self.dealer_stand_label.setStyleSheet(
                "color: white; font-weight: bold; font-size: 24px;"
            )

        card_width = 100
        spacing = 10
        x = len(self.dealer_widgets) * (card_width + spacing) + 20
        y = 40
        self.dealer_stand_label.move(x, y)
        self.dealer_stand_label.show()

    def hide_dealer_stand_label(self):
        if self.dealer_stand_label is not None:
            self.dealer_stand_label.hide()

    # ------------------------------------------------------------------
    # controls enabling
    # ------------------------------------------------------------------
    def enable_controls(self):
        if self.calculate_score(self.player_cards) < 21:
            self.hit_btn.setEnabled(True)
            self.stand_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # player hit + dealer reaction
    # ------------------------------------------------------------------
    def player_hit_logic(self):
        if self._dealer_playing:
            return

        self.hit_btn.setEnabled(False)
        self.stand_btn.setEnabled(False)

        c = self.draw_card()
        self.player_cards.append(c)

        self.intro_group = QSequentialAnimationGroup(self)
        self.add_animated_card(c, self.player_container, self.player_widgets, 600, False)

        def after_hit():
            p_score = self.calculate_score(self.player_cards)

            # If player hits into exactly 21, treat it as stand
            if p_score == 21:
                QTimer.singleShot(0, self.dealer_turn_logic)
                return

            # If player busts, dealer_turn_logic will handle reveal + end
            if p_score > 21:
                QTimer.singleShot(0, self.dealer_turn_logic)
                return

            # Otherwise dealer reacts normally
            self.dealer_react_after_player_hit()

        if self.intro_group.animationCount() == 0:
            after_hit()
        else:
            self.intro_group.finished.connect(after_hit)
            self.intro_group.start()

    def dealer_react_after_player_hit(self):
        if self.dealer_has_stood:
            self.enable_controls()
            return

        d_score = self.calculate_score(self.dealer_cards)

        if d_score < 17:
            # dealer hits once, card is face down
            c = self.draw_card()
            self.dealer_cards.append(c)

            self.intro_group = QSequentialAnimationGroup(self)
            self.add_animated_card(c, self.dealer_container, self.dealer_widgets, 400, True)

            def reenable():
                self.enable_controls()

            if self.intro_group.animationCount() == 0:
                reenable()
            else:
                self.intro_group.finished.connect(reenable)
                self.intro_group.start()
        else:
            # dealer stands (no more hits during player actions)
            self.dealer_has_stood = True
            self.show_dealer_stand_label()
            self.enable_controls()

    # ------------------------------------------------------------------
    # player stand → dealer's turn
    # ------------------------------------------------------------------
    def dealer_turn_logic(self):
        if self._dealer_playing:
            return

        self._dealer_playing = True
        self.hit_btn.setEnabled(False)
        self.stand_btn.setEnabled(False)

        # reveal all hidden dealer cards with flip animation
        hidden_widgets = [w for w in self.dealer_widgets if getattr(w, "is_hidden", False)]
        for w in hidden_widgets:
            w.reveal()

        def after_reveal():
            if self.dealer_has_stood:
                # dealer already stood earlier → remove STAND! and finish
                self.hide_dealer_stand_label()
                self.end_game()
                return

            # dealer has NOT stood yet → dealer plays normally (no STAND! text)
            self.dealer_auto_play()

        if hidden_widgets:
            QTimer.singleShot(350, after_reveal)
        else:
            after_reveal()

    def dealer_auto_play(self):
        self.intro_group = QSequentialAnimationGroup(self)

        while self.calculate_score(self.dealer_cards) < 17:
            c = self.draw_card()
            self.dealer_cards.append(c)
            # during dealer's own turn, new cards are face up
            self.add_animated_card(c, self.dealer_container, self.dealer_widgets, 400, False)

        if self.intro_group.animationCount() == 0:
            self.end_game()
        else:
            self.intro_group.finished.connect(self.end_game)
            self.intro_group.start()

    # ------------------------------------------------------------------
    # end game + replay
    # ------------------------------------------------------------------
    def end_game(self):
        p_score = self.calculate_score(self.player_cards)
        d_score = self.calculate_score(self.dealer_cards)

        if p_score > 21 and d_score > 21:
            msg = "It's a draw! (both bust)"
        elif p_score > 21:
            msg = "You lose! (bust)"
        elif d_score > 21:
            msg = "You win! (dealer bust)"
        elif p_score > d_score:
            msg = "You win!"
        elif d_score > p_score:
            msg = "You lose!"
        else:
            msg = "It's a tie!"

        self.result_label.setText(msg)
        self.totals_label.setText(f"Your: {p_score} | Dealer: {d_score}")

        QTimer.singleShot(2000, self.ask_play_again)

    def ask_play_again(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Play again?")
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Would you like to play again?"))
        btn_row = QHBoxLayout()
        yes_btn = QPushButton("Yes")
        no_btn = QPushButton("No")
        yes_btn.clicked.connect(dlg.accept)
        no_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(yes_btn)
        btn_row.addWidget(no_btn)
        layout.addLayout(btn_row)

        if dlg.exec():
            self.start_game()
        else:
            self.close()


# ----------------------------------------------------------------------
# main entry
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = BlackjackGUI()
    win.show()
    sys.exit(app.exec())
