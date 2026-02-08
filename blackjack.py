import sys
import os
import random
import platform
import subprocess
from time import sleep

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QDialog,
    QRadioButton,
    QButtonGroup,
    QSpinBox,
    QStackedWidget,
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import (
    Qt,
    QPropertyAnimation,
    QPoint,
    QEasingCurve,
    QTimer,
    QSequentialAnimationGroup,
    QAbstractAnimation,
    QRect,
    QUrl,
)
from PySide6.QtMultimedia import QSoundEffect


# ----------------------------------------------------------------------
# Utilities: sound playback with graceful fallback (QSoundEffect -> system)
# ----------------------------------------------------------------------
def play_wav_with_system(path):
    """Try platform-native playback for wav files if QSoundEffect isn't available."""
    if not os.path.exists(path):
        return
    plat = platform.system()
    try:
        if plat == "Windows":
            from pygame import mixer
            mixer.init()
            mixer.music.load(path)
            mixer.music.play()
            return
        if plat == "Darwin":
            # macOS
            subprocess.Popen(["afplay", path])
            return
        # Linux: try aplay or paplay
        for cmd in (["paplay", path], ["aplay", path]):
            try:
                subprocess.Popen(cmd)
                return
            except Exception:
                continue
    except Exception:
        pass


def try_create_qsound(path):
    """Return QSoundEffect instance if possible and file exists, else None."""
    if not os.path.exists(path):
        return None
    try:
        s = QSoundEffect()
        s.setSource(QUrl.fromLocalFile(path))
        s.setVolume(0.6)
        return s
    except Exception:
        return None


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
# Card widget with flip animation
# ----------------------------------------------------------------------
class CardWidget(QLabel):
    def __init__(self, card_data, is_hidden=False, parent=None):
        super().__init__(parent)
        self.card_data = card_data  # (num, suit_idx)
        self.is_hidden = is_hidden
        # Always set pixmap (back if hidden)
        self.setPixmap(get_card_pixmap_static(*card_data, is_back=is_hidden))
        self.setFixedSize(100, 150)
        self.show()

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
# Intro animation screen (plays before rules)
# ----------------------------------------------------------------------
class IntroScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #004000;")
        self.cards = []

    def start_animation(self, duration_out=2000, duration_in=2000, on_finished=None, play_shuffle=None):
        self.clear_cards()
        area_w = self.width() if self.width() > 0 else 800
        area_h = self.height() if self.height() > 0 else 400
        center_x = area_w // 2
        center_y = area_h // 2

        # create many face-down cards centered
        for _ in range(40):
            c = CardWidget((1, 1), is_hidden=True, parent=self)
            c.move(center_x - c.width() // 2, center_y - c.height() // 2)
            c.show()
            self.cards.append(c)

        if play_shuffle:
            play_shuffle()

        # animate them flying out in random directions over duration_out
        for c in self.cards:
            dx = random.randint(-area_w, area_w)
            dy = random.randint(-area_h, area_h)
            end_x = max(0, min(area_w - c.width(), center_x + dx))
            end_y = max(0, min(area_h - c.height(), center_y + dy))

            anim = QPropertyAnimation(c, b"pos", self)
            anim.setDuration(duration_out)
            anim.setStartValue(c.pos())
            anim.setEndValue(QPoint(end_x, end_y))
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start(QAbstractAnimation.DeleteWhenStopped)

        # after duration_out, animate them back to center
        def gather_back():
            for c in self.cards:
                anim = QPropertyAnimation(c, b"pos", self)
                anim.setDuration(duration_in)
                anim.setStartValue(c.pos())
                anim.setEndValue(QPoint(center_x - c.width() // 2, center_y - c.height() // 2))
                anim.setEasingCurve(QEasingCurve.InOutCubic)
                anim.start(QAbstractAnimation.DeleteWhenStopped)

            QTimer.singleShot(duration_in, lambda: on_finished() if on_finished else None)

        QTimer.singleShot(duration_out, gather_back)

    def clear_cards(self):
        for c in self.cards:
            c.deleteLater()
        self.cards = []


# ----------------------------------------------------------------------
# main blackjack GUI
# ----------------------------------------------------------------------
class BlackjackGUI(QMainWindow):
    MODE_AUTO_START = 0
    MODE_WITH_PLAYER = 1
    MODE_AUTO_END = 2

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Blackjack")
        self.setFixedSize(760, 760)
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

        self.dealer_mode = self.MODE_WITH_PLAYER
        self.dealer_stand_threshold = 16

        self.pile_widget = None
        self.shuffle_widgets = []

        # audio: prefer QSoundEffect for wav; fallback to system playback
        self.snd_draw = None
        self.snd_flip = None
        self.snd_shuffle = None
        self.init_audio_players()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.intro_screen = IntroScreen()
        self.rules_widget = QWidget()
        self.game_widget = QWidget()
        self.stack.addWidget(self.intro_screen)
        self.stack.addWidget(self.rules_widget)
        self.stack.addWidget(self.game_widget)

        self.init_rules_ui()
        self.init_game_ui()

        # start with intro animation screen
        QTimer.singleShot(100, self.play_intro_then_rules)

    # ------------------------------------------------------------------
    # audio initialization with graceful fallback
    # ------------------------------------------------------------------
    def init_audio_players(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        assets = os.path.join(base_dir, "bj_assets")

        # prefer WAV files for QSoundEffect
        self.snd_draw = try_create_qsound(os.path.join(assets, "card_drawn.wav"))
        self.snd_flip = try_create_qsound(os.path.join(assets, "card_flipped.wav"))
        self.snd_shuffle = try_create_qsound(os.path.join(assets, "card_shuffle.wav"))

        # if wav not present, keep paths for system fallback (mp3 or wav)
        self._draw_path = (
            os.path.join(assets, "card_drawn.wav")
            if os.path.exists(os.path.join(assets, "card_drawn.wav"))
            else os.path.join(assets, "card_drawn.mp3")
        )
        self._flip_path = (
            os.path.join(assets, "card_flipped.wav")
            if os.path.exists(os.path.join(assets, "card_flipped.wav"))
            else os.path.join(assets, "card_flipped.mp3")
        )
        self._shuffle_path = (
            os.path.join(assets, "card_shuffle.wav")
            if os.path.exists(os.path.join(assets, "card_shuffle.wav"))
            else os.path.join(assets, "card_shuffle.mp3")
        )

    def play_draw_sound(self):
        if isinstance(self.snd_draw, QSoundEffect):
            try:
                self.snd_draw.play()
                return
            except Exception:
                pass
        play_wav_with_system(self._draw_path)

    def play_flip_sound(self):
        if isinstance(self.snd_flip, QSoundEffect):
            try:
                self.snd_flip.play()
                return
            except Exception:
                pass
        play_wav_with_system(self._flip_path)

    def play_shuffle_sound(self):
        if isinstance(self.snd_shuffle, QSoundEffect):
            try:
                self.snd_shuffle.play()
                return
            except Exception:
                pass
        play_wav_with_system(self._shuffle_path)

    # ------------------------------------------------------------------
    # Intro -> Rules flow
    # ------------------------------------------------------------------
    def play_intro_then_rules(self):
        self.stack.setCurrentWidget(self.intro_screen)

        def on_intro_finished():
            self.show_rules()

        # start intro animation: 2s out, 2s back
        self.intro_screen.start_animation(
            duration_out=2000,
            duration_in=2000,
            on_finished=on_intro_finished,
            play_shuffle=self.play_shuffle_sound,
        )

    # ------------------------------------------------------------------
    # rules screen
    # ------------------------------------------------------------------
    def init_rules_ui(self):
        layout = QVBoxLayout(self.rules_widget)

        title = QLabel("Choose Rules")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        r1_label = QLabel("When the dealer plays:")
        r1_label.setStyleSheet("color: white; font-size: 18px;")
        layout.addWidget(r1_label)

        self.mode_group = QButtonGroup(self.rules_widget)

        rb_start = QRadioButton("auto-play at the start")
        rb_with = QRadioButton("play with the player")
        rb_end = QRadioButton("auto-play at the end")

        rb_with.setChecked(True)

        for rb in (rb_start, rb_with, rb_end):
            rb.setStyleSheet("color: white; font-size: 16px;")
            layout.addWidget(rb)

        self.mode_group.addButton(rb_start, self.MODE_AUTO_START)
        self.mode_group.addButton(rb_with, self.MODE_WITH_PLAYER)
        self.mode_group.addButton(rb_end, self.MODE_AUTO_END)

        r2_label = QLabel("Dealer must stand at or above:")
        r2_label.setStyleSheet("color: white; font-size: 18px;")
        layout.addWidget(r2_label)

        h = QHBoxLayout()
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(12, 21)
        self.threshold_spin.setValue(16)
        self.threshold_spin.setStyleSheet("font-size: 16px;")
        h.addWidget(self.threshold_spin)

        lbl_pts = QLabel("points")
        lbl_pts.setStyleSheet("color: white; font-size: 16px;")
        h.addWidget(lbl_pts)
        h.addStretch()
        layout.addLayout(h)

        layout.addStretch()

        start_btn = QPushButton("Start Game")
        start_btn.setStyleSheet("font-size: 18px;")
        start_btn.clicked.connect(self.apply_rules_and_start)
        layout.addWidget(start_btn)

    def apply_rules_and_start(self):
        self.dealer_mode = self.mode_group.checkedId()
        self.dealer_stand_threshold = self.threshold_spin.value()
        self.show_game()
        # create pile between dealer and player before dealing
        QTimer.singleShot(100, self.create_pile_and_start)

    def show_rules(self):
        self.stack.setCurrentWidget(self.rules_widget)

    def show_game(self):
        self.stack.setCurrentWidget(self.game_widget)

    # ------------------------------------------------------------------
    # game UI
    # ------------------------------------------------------------------
    def init_game_ui(self):
        self.game_layout = QVBoxLayout(self.game_widget)

        # Dealer row
        dealer_label = QLabel("Dealer's hand:")
        dealer_label.setStyleSheet("color: white; font-size: 18px;")
        self.game_layout.addWidget(dealer_label)

        self.dealer_container = QWidget()
        self.dealer_container.setMinimumHeight(160)
        self.dealer_container.setLayout(None)
        self.game_layout.addWidget(self.dealer_container)

        # deck / pile area (between dealer and player)
        self.deck_area = QWidget()
        self.deck_area.setMinimumHeight(140)
        self.deck_area.setLayout(None)
        self.game_layout.addWidget(self.deck_area)

        # Player row
        player_label = QLabel("Your hand:")
        player_label.setStyleSheet("color: white; font-size: 18px;")
        self.game_layout.addWidget(player_label)

        self.player_container = QWidget()
        self.player_container.setMinimumHeight(160)
        self.player_container.setLayout(None)
        self.game_layout.addWidget(self.player_container)

        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("color: yellow; font-weight: bold; font-size: 32px;")
        self.game_layout.addWidget(self.result_label)

        self.totals_label = QLabel("")
        self.totals_label.setAlignment(Qt.AlignCenter)
        self.totals_label.setStyleSheet("color: white; font-size: 22px;")
        self.game_layout.addWidget(self.totals_label)

        self.btn_layout = QHBoxLayout()
        self.hit_btn = QPushButton("Hit")
        self.stand_btn = QPushButton("Stand")
        self.hit_btn.clicked.connect(self.player_hit_logic)
        self.stand_btn.clicked.connect(self.dealer_turn_logic)
        self.btn_layout.addWidget(self.hit_btn)
        self.btn_layout.addWidget(self.stand_btn)
        self.game_layout.addLayout(self.btn_layout)

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
        return len(self.player_cards) == 2 and self.calculate_score(self.player_cards) == 21

    # ------------------------------------------------------------------
    # create pile widget (single back) centered in deck_area
    # ------------------------------------------------------------------
    def create_pile_and_start(self):
        if self.pile_widget is not None:
            self.pile_widget.deleteLater()
            self.pile_widget = None

        area = self.deck_area
        w = area.width() if area.width() > 0 else self.width()
        h = area.height() if area.height() > 0 else 140
        self.pile_widget = CardWidget((1, 1), is_hidden=True, parent=area)
        px = w // 2 - self.pile_widget.width() // 2
        py = h // 2 - self.pile_widget.height() // 2
        self.pile_widget.move(px, py)
        self.pile_widget.show()

        QTimer.singleShot(100, self.start_game)

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

        for w in self.dealer_widgets + self.player_widgets + self.shuffle_widgets:
            try:
                w.deleteLater()
            except Exception:
                pass
        self.dealer_widgets = []
        self.player_widgets = []
        self.shuffle_widgets = []

        self.hit_btn.setEnabled(False)
        self.stand_btn.setEnabled(False)

        # deal initial cards from pile (cards animate from pile)
        self.deal_initial_cards()

    # ------------------------------------------------------------------
    # initial dealing after pile exists
    # ------------------------------------------------------------------
    def deal_initial_cards(self):
        # create a fresh sequential group for the deal animations
        self.intro_group = QSequentialAnimationGroup(self)

        # dealer initial 2 cards: first up, second down (horizontal layout)
        for i in range(2):
            c = self.draw_card()
            self.dealer_cards.append(c)
            hidden = (i == 1)
            self.add_animated_card(c, self.dealer_container, self.dealer_widgets, 300, hidden, dealer=True)

        # player: 2 cards, both face up (horizontal)
        for _ in range(2):
            c = self.draw_card()
            self.player_cards.append(c)
            self.add_animated_card(c, self.player_container, self.player_widgets, 400, False, dealer=False)

        def after_deal():
            # If auto-start mode, dealer should draw remaining cards face-down from the pile (and widgets visible)
            if self.dealer_mode == self.MODE_AUTO_START:
                # animate extra dealer cards from pile as face-down widgets
                self.deal_extra_dealer_cards_auto_start()
            else:
                if self.player_has_blackjack():
                    QTimer.singleShot(0, self.dealer_turn_logic)
                else:
                    self.enable_controls()

        self.intro_group.finished.connect(after_deal)
        self.intro_group.start()

    def deal_extra_dealer_cards_auto_start(self):
        """Ensure extra dealer cards are created as visible face-down widgets and animated from the pile."""
        # create a new sequential group for these extra cards so animations run
        group = QSequentialAnimationGroup(self)
        self.intro_group = group

        while self.calculate_score(self.dealer_cards) < self.dealer_stand_threshold:
            c = self.draw_card()
            self.dealer_cards.append(c)
            # add widget and animation (face-down)
            # add_animated_card will append animation to self.intro_group
            self.add_animated_card(c, self.dealer_container, self.dealer_widgets, 220, True, dealer=True)

        def after_extra():
            if self.player_has_blackjack():
                QTimer.singleShot(0, self.dealer_turn_logic)
            else:
                self.enable_controls()

        # run the group and call after_extra when done
        if group.animationCount() == 0:
            after_extra()
        else:
            group.finished.connect(after_extra)
            group.start()

    # ------------------------------------------------------------------
    # card animation helper (cards fly from pile to target)
    # dealer=True => horizontal dealer row; dealer cards should appear to come from below the pile
    # dealer=False => player row; cards come from above the pile
    # ------------------------------------------------------------------
    def add_animated_card(self, data, container, widget_list, duration, hidden, dealer=False):
        card = CardWidget(data, is_hidden=hidden, parent=container)
        widget_list.append(card)

        # ensure container sizing
        if container.width() == 0:
            container.setFixedHeight(160)
            container.setFixedWidth(self.width() - 40)

        card_w = 100
        card_h = 150
        spacing = 10

        # compute horizontal target positions for both dealer and player (both horizontal)
        for idx, w in enumerate(widget_list):
            tx = idx * (card_w + spacing) + 10
            ty = 5
            w.move(tx, ty)

        new_index = len(widget_list) - 1
        target_pos = QPoint(new_index * (card_w + spacing) + 10, 5)

        # start position: pile center mapped into container coordinates
        if self.pile_widget is not None:
            pile_center_global = self.pile_widget.mapToGlobal(self.pile_widget.rect().center())
            start_center = container.mapFromGlobal(pile_center_global)
            # For dealer cards, start below the pile (so they appear to come from bottom)
            # For player cards, start above the pile (so they appear to come from top)
            if dealer:
                start_pos = QPoint(start_center.x() - card_w // 2, start_center.y() + 200)
            else:
                start_pos = QPoint(start_center.x() - card_w // 2, start_center.y() - 200)
        else:
            # fallback: off-screen above/below
            if dealer:
                start_pos = QPoint(container.width() // 2 - card_w // 2, container.height() + 50)
            else:
                start_pos = QPoint(container.width() // 2 - card_w // 2, -200)

        card.move(start_pos)
        card.hide()

        incoming_anim = QPropertyAnimation(card, b"pos", self)
        incoming_anim.setDuration(duration)
        incoming_anim.setStartValue(start_pos)
        incoming_anim.setEndValue(target_pos)
        incoming_anim.setEasingCurve(QEasingCurve.OutCubic)

        def _on_anim_state(new_state, _old_state):
            if new_state == QAbstractAnimation.Running:
                card.show()
                # play draw sound
                self.play_draw_sound()
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

        # place to the right of dealer row
        card_w = 100
        spacing = 10
        x = len(self.dealer_widgets) * (card_w + spacing) + 20
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
        self.add_animated_card(c, self.player_container, self.player_widgets, 400, False, dealer=False)

        def after_hit():
            p_score = self.calculate_score(self.player_cards)

            if p_score == 21:
                QTimer.singleShot(0, self.dealer_turn_logic)
                return

            if p_score > 21:
                QTimer.singleShot(0, self.dealer_turn_logic)
                return

            if self.dealer_mode == self.MODE_WITH_PLAYER:
                self.dealer_react_after_player_hit()
            else:
                self.enable_controls()

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

        if d_score < self.dealer_stand_threshold:
            c = self.draw_card()
            self.dealer_cards.append(c)

            self.intro_group = QSequentialAnimationGroup(self)
            # dealer hit during player phase: face-down widget drawn from pile, horizontal, coming from bottom
            self.add_animated_card(c, self.dealer_container, self.dealer_widgets, 350, True, dealer=True)

            def reenable():
                self.enable_controls()

            if self.intro_group.animationCount() == 0:
                reenable()
            else:
                self.intro_group.finished.connect(reenable)
                self.intro_group.start()
        else:
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

        # reveal all hidden dealer cards with flip animation, spaced 0.5s apart
        hidden_widgets = [w for w in self.dealer_widgets if getattr(w, "is_hidden", False)]

        def reveal_sequence(index=0):
            if index >= len(hidden_widgets):
                after_reveal()
                return
            w = hidden_widgets[index]
            self.play_flip_sound()
            w.reveal()
            QTimer.singleShot(500, lambda: reveal_sequence(index + 1))

        def after_reveal():
            if self.dealer_mode == self.MODE_AUTO_START:
                # dealer already auto-played at start; just end
                self.hide_dealer_stand_label()
                self.end_game()
                return

            if self.dealer_mode == self.MODE_WITH_PLAYER:
                if self.dealer_has_stood:
                    self.hide_dealer_stand_label()
                    self.end_game()
                else:
                    # dealer now auto-plays until threshold; new cards face-up and drawn from pile
                    self.dealer_auto_play_end_mode(show_stand=False)
            else:  # MODE_AUTO_END
                self.dealer_auto_play_end_mode(show_stand=False)

        if hidden_widgets:
            QTimer.singleShot(200, lambda: reveal_sequence(0))
        else:
            after_reveal()

    def dealer_auto_play_end_mode(self, show_stand=False):
        self.intro_group = QSequentialAnimationGroup(self)

        while self.calculate_score(self.dealer_cards) < self.dealer_stand_threshold:
            c = self.draw_card()
            self.dealer_cards.append(c)
            # during dealer's own turn, new cards are face up (horizontal)
            self.add_animated_card(c, self.dealer_container, self.dealer_widgets, 350, False, dealer=True)

        if show_stand:
            self.show_dealer_stand_label()
        else:
            self.hide_dealer_stand_label()

        if self.intro_group.animationCount() == 0:
            self.end_game()
        else:
            self.intro_group.finished.connect(self.end_game)
            self.intro_group.start()

    # ------------------------------------------------------------------
    # end game + replay / change rules
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
        layout.addWidget(QLabel("What would you like to do?"))
        btn_row = QHBoxLayout()

        yes_btn = QPushButton("Play again")
        change_btn = QPushButton("Change rules")
        no_btn = QPushButton("Quit")

        def do_play_again():
            dlg.done(1)

        def do_change_rules():
            dlg.done(2)

        def do_quit():
            dlg.done(0)

        yes_btn.clicked.connect(do_play_again)
        change_btn.clicked.connect(do_change_rules)
        no_btn.clicked.connect(do_quit)

        btn_row.addWidget(yes_btn)
        btn_row.addWidget(change_btn)
        btn_row.addWidget(no_btn)
        layout.addLayout(btn_row)

        result = dlg.exec()

        if result == 1:
            # keep same rules, start new game (pile already exists)
            self.start_game()
        elif result == 2:
            # go back to rules screen (intro will not replay)
            self.show_rules()
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