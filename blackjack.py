"""
Blackjack Game Implementation using Pygame.

This module implements a fully functional Blackjack card game with multiple dealer modes,
animated card dealing and flipping, sound effects, and a complete game flow including
intro animation, rules selection, gameplay, and end-game results.

Features:
- Configurable dealer behavior (draw at start, with player, or at end)
- Smooth animations for card movements and flips with scaling effects
- Sound effects for card draws, flips, and shuffling
- Sequential dealing and dealer actions to match reference implementations
- Professional UI with buttons and text inputs

Classes:
    Button: Interactive button with hover and selection states
    TextInput: Numeric input field with up/down buttons
    Card: Represents a playing card with animation capabilities
    Game: Main game controller managing state and logic

Author: Kyle Haynes
Date Last Updated: March 7th, 2026
"""

import pygame
import sys
import os
import random

pygame.init()
pygame.mixer.init()

# ensure mixer volume defaults
pygame.mixer.set_num_channels(8)

# Constants
FPS = 60
ASPECT_RATIO = 4 / 3  # 4:3 aspect ratio

# Reference dimensions for scaling calculations (base 4:3 aspect ratio)
REFERENCE_WIDTH = 1200
REFERENCE_HEIGHT = 900

# Detect screen size and initialize window size
def get_initial_window_size():
    """Calculate initial window size based on screen resolution, maintaining 4:3 aspect ratio."""
    # Get display info
    display_info = pygame.display.Info()
    screen_width = display_info.current_w
    screen_height = display_info.current_h
    
    # Calculate max usable space (leave some margin for taskbar, etc)
    max_width = int(screen_width * 0.95)
    max_height = int(screen_height * 0.90)
    
    # Calculate size maintaining 4:3 ratio
    if max_width / max_height > ASPECT_RATIO:
        # Width is relatively larger, constrain by height
        win_height = max_height
        win_width = int(win_height * ASPECT_RATIO)
    else:
        # Height is relatively larger, constrain by width
        win_width = max_width
        win_height = int(win_width / ASPECT_RATIO)
    
    return (win_width, win_height)

def enforce_aspect_ratio(width, height):
    """Adjust dimensions to maintain 4:3 aspect ratio."""
    current_ratio = width / height
    if current_ratio > ASPECT_RATIO:
        # Too wide, reduce width
        width = int(height * ASPECT_RATIO)
    else:
        # Too tall, reduce height
        height = int(width / ASPECT_RATIO)
    return (width, height)

# Get initial size
_initial_size = get_initial_window_size()
DEFAULT_WIDTH = _initial_size[0]
DEFAULT_HEIGHT = _initial_size[1]
WIDTH = DEFAULT_WIDTH
HEIGHT = DEFAULT_HEIGHT

# Scaling functions - scale relative to reference screen size
def get_scaled_value(base_value, dimension='width'):
    """Scale a value based on current screen dimensions relative to reference."""
    if dimension == 'width':
        return int(base_value * WIDTH / REFERENCE_WIDTH)
    elif dimension == 'height':
        return int(base_value * HEIGHT / REFERENCE_HEIGHT)
    elif dimension == 'dialog':
        return int(base_value * min(WIDTH / REFERENCE_WIDTH, HEIGHT / REFERENCE_HEIGHT))
    return base_value

def get_font_size(base_size):
    """Scale font size based on screen dimensions."""
    scale = min(WIDTH / REFERENCE_WIDTH, HEIGHT / REFERENCE_HEIGHT)
    return max(12, int(base_size * scale))

# Colors
GREEN = (0, 100, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)

def get_card_dimensions():
    """Get scaled card dimensions based on current screen size relative to reference."""
    # Base card size at reference resolution
    base_card_width = 100
    base_card_height = 150
    
    # Scale factor based on current vs reference size
    scale_factor = min(WIDTH / REFERENCE_WIDTH, HEIGHT / REFERENCE_HEIGHT)
    
    card_width = int(base_card_width * scale_factor)
    card_height = int(base_card_height * scale_factor)
    return (card_width, card_height)

# Load assets
base_dir = os.path.dirname(os.path.abspath(__file__))
assets = os.path.join(base_dir, "bj_assets")

# Card images: Dictionary mapping (suit, rank) to loaded images
card_images = {}
suits = ['clubs', 'diamonds', 'hearts', 'spades']
ranks = ['a'] + [f"{i:02d}" for i in range(2, 11)] + ['j', 'q', 'k']

# Store original images at 1:1 scale for dynamic resizing
card_images_original = {}
for suit in suits:
    for rank in ranks:
        path = os.path.join(assets, f"card_{suit}_{rank}.png")
        if os.path.exists(path):
            img = pygame.image.load(path)
            card_images_original[(suit, rank)] = img

card_back_red_original = pygame.image.load(os.path.join(assets, "card_back_red.png"))
card_back_blue_original = pygame.image.load(os.path.join(assets, "card_back_blue.png"))

def load_scaled_cards():
    """Load and scale card images to current screen dimensions."""
    global card_images, card_back_red, card_back_blue
    dims = get_card_dimensions()
    card_images = {}
    for (suit, rank), img in card_images_original.items():
        card_images[(suit, rank)] = pygame.transform.scale(img, dims)
    card_back_red = pygame.transform.scale(card_back_red_original, dims)
    card_back_blue = pygame.transform.scale(card_back_blue_original, dims)

# Load initial scaled cards
load_scaled_cards()

# Sounds: Prefer WAV but fallback to MP3 if available
wav = lambda name: os.path.join(assets, name + ".wav")
mp3 = lambda name: os.path.join(assets, name + ".mp3")

def load_sound(name):
    """
    Load a sound file, preferring WAV over MP3.

    Args:
        name (str): Base name of the sound file (without extension).

    Returns:
        pygame.mixer.Sound or None: Loaded sound object or None if not found.
    """
    # try wav first then mp3
    path = wav(name) if os.path.exists(wav(name)) else (mp3(name) if os.path.exists(mp3(name)) else None)
    if path:
        try:
            return pygame.mixer.Sound(path)
        except Exception:
            return None
    return None


def play_sound(snd, label):
    """
    Play a sound effect if available.

    Args:
        snd (pygame.mixer.Sound or None): Sound to play.
        label (str): Label for debugging output.
    """
    if snd:
        try:
            snd.play()
            print(f"played sound: {label}")
        except Exception as e:
            print(f"error playing sound {label}: {e}")


draw_sound = load_sound("card_drawn")
flip_sound = load_sound("card_flipped")
shuffle_sound = load_sound("card_shuffle")

# set reasonable volumes
if draw_sound:
    draw_sound.set_volume(0.6)
if flip_sound:
    flip_sound.set_volume(0.6)
if shuffle_sound:
    shuffle_sound.set_volume(0.6)

# debug print load results
print("sounds loaded:",
      "draw=" + str(bool(draw_sound)),
      "flip=" + str(bool(flip_sound)),
      "shuffle=" + str(bool(shuffle_sound)))

class Button:
    """
    Represents an interactive button with hover, selection, and enabled states.

    Attributes:
        rect (pygame.Rect): The button's rectangular area.
        text (str): The text displayed on the button.
        font (pygame.font.Font): Font used for rendering text.
        color (tuple): Default color of the button.
        hover_color (tuple): Color when mouse hovers over the button.
        selected_color (tuple): Color when the button is selected.
        hovered (bool): Whether the mouse is currently hovering.
        selected (bool): Whether the button is selected.
        enabled (bool): Whether the button is interactive.
    """

    def __init__(self, x, y, w, h, text, font, color=WHITE, hover_color=YELLOW, selected_color=(150,150,150)):
        """
        Initialize a Button instance.

        Args:
            x (int): X-coordinate of the top-left corner.
            y (int): Y-coordinate of the top-left corner.
            w (int): Width of the button.
            h (int): Height of the button.
            text (str): Text to display on the button.
            font (pygame.font.Font): Font for the text.
            color (tuple): Default color (RGB).
            hover_color (tuple): Hover color (RGB).
            selected_color (tuple): Selected color (RGB).
        """
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.selected_color = selected_color
        self.hovered = False
        self.selected = False
        self.enabled = True  # new flag to disable interaction

    def draw(self, screen):
        """
        Draw the button on the screen.

        Args:
            screen (pygame.Surface): The surface to draw on.
        """
        if not self.enabled:
            color = (200, 200, 200)
        elif self.selected:
            color = self.selected_color
        elif self.hovered:
            color = self.hover_color
        else:
            color = self.color
        pygame.draw.rect(screen, color, self.rect)
        text_surf = self.font.render(self.text, True, BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def update(self, mouse_pos):
        """
        Update the button's hover state based on mouse position.

        Args:
            mouse_pos (tuple): Current mouse position (x, y).
        """
        if self.enabled:
            self.hovered = self.rect.collidepoint(mouse_pos)
        else:
            self.hovered = False

    def click(self, pos):
        """
        Check if the button was clicked at the given position.

        Args:
            pos (tuple): Position to check (x, y).

        Returns:
            bool: True if clicked and enabled, False otherwise.
        """
        return self.enabled and self.rect.collidepoint(pos)


class TextInput:
    """
    Represents a numeric text input field with up/down arrow buttons.

    Attributes:
        rect (pygame.Rect): The input field's rectangular area.
        font (pygame.font.Font): Font used for rendering text.
        text (str): Current text in the input.
        active (bool): Whether the input is currently active for editing.
        min_val (int): Minimum allowed value.
        max_val (int): Maximum allowed value.
        up_btn (Button): Button to increase the value.
        down_btn (Button): Button to decrease the value.
    """

    def __init__(self, x, y, w, h, font, initial="16", min_val=4, max_val=21):
        """
        Initialize a TextInput instance.

        Args:
            x (int): X-coordinate of the top-left corner.
            y (int): Y-coordinate of the top-left corner.
            w (int): Width of the input field.
            h (int): Height of the input field.
            font (pygame.font.Font): Font for the text.
            initial (str): Initial text value.
            min_val (int): Minimum value constraint.
            max_val (int): Maximum value constraint.
        """
        self.rect = pygame.Rect(x, y, w, h)
        self.font = font
        self.text = initial
        self.active = False
        self.min_val = min_val
        self.max_val = max_val
        self.up_btn = Button(x + w + 10, y, 30, h // 2, "+", font, WHITE, YELLOW)
        self.down_btn = Button(x + w + 10, y + h // 2, 30, h // 2, "-", font, WHITE, YELLOW)

    def draw(self, screen):
        """
        Draw the text input and buttons on the screen.

        Args:
            screen (pygame.Surface): The surface to draw on.
        """
        color = WHITE if self.active else (200, 200, 200)
        pygame.draw.rect(screen, color, self.rect)
        text_surf = self.font.render(self.text, True, BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)
        self.up_btn.draw(screen)
        self.down_btn.draw(screen)

    def update(self, mouse_pos):
        """
        Update the buttons' hover states.

        Args:
            mouse_pos (tuple): Current mouse position (x, y).
        """
        self.up_btn.update(mouse_pos)
        self.down_btn.update(mouse_pos)

    def handle_event(self, event):
        """
        Handle input events for the text input.

        Args:
            event (pygame.event.Event): The event to handle.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
            else:
                self.active = False
            if self.up_btn.click(event.pos):
                val = int(self.text) + 1
                self.text = str(min(val, self.max_val))
            elif self.down_btn.click(event.pos):
                val = int(self.text) - 1
                self.text = str(max(val, self.min_val))
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
            try:
                val = int(self.text)
                val = max(self.min_val, min(val, self.max_val))
                self.text = str(val)
            except ValueError:
                self.text = "16"

    def get_value(self):
        """
        Get the current numeric value of the input.

        Returns:
            int: The parsed integer value, or 16 if invalid.
        """
        try:
            return int(self.text)
        except ValueError:
            return 16

class Card:
    """
    Represents a playing card with animation capabilities for movement and flipping.

    Attributes:
        num (int): Card rank (1-13, where 1=Ace, 11=Jack, etc.).
        suit_idx (int): Suit index (1-4: clubs, diamonds, hearts, spades).
        hidden (bool): Whether the card is face-down.
        flipping (bool): Whether the card is currently flipping.
        flip_progress (float): Progress of the flip animation (0.0 to 1.0).
        pos (list): Current position [x, y].
        target_pos (list): Target position for animation [x, y].
        animating (bool): Whether the card is currently animating movement.
        anim_progress (float): Progress of the movement animation (0.0 to 1.0).
        start_pos (list): Starting position for animation [x, y].
        duration (float): Duration of the current animation in seconds.
        easing (str or None): Easing function for animation ('in_cubic', 'out_cubic', etc.).
        on_finish (callable or None): Callback function to call when animation finishes.
        image (pygame.Surface): Current image of the card.
        rect (pygame.Rect): Rectangular area for drawing.
    """

    def __init__(self, num, suit_idx, hidden=False):
        """
        Initialize a Card instance.

        Args:
            num (int): Card rank (1-13).
            suit_idx (int): Suit index (1-4).
            hidden (bool): Whether to start face-down.
        """
        self.num = num
        self.suit_idx = suit_idx
        self.hidden = hidden
        self.flipping = False
        self.flip_progress = 0.0
        self.pos = [0, 0]
        self.target_pos = [0, 0]
        self.animating = False
        self.anim_progress = 0.0
        self.start_pos = [0, 0]
        self.duration = 0.0
        self.easing = None
        self.image = self.get_image()
        self.rect = self.image.get_rect()

    def get_image(self):
        """
        Get the appropriate image for the card based on hidden state.

        Returns:
            pygame.Surface: The card's image.
        """
        if self.hidden:
            return card_back_red if self.suit_idx in [2, 3] else card_back_blue
        suit = suits[self.suit_idx - 1]
        rank = ranks[self.num - 1]
        return card_images.get((suit, rank), pygame.Surface((100, 150)))

    def draw(self, screen):
        """
        Draw the card on the screen, handling flip animation with scaling.

        Args:
            screen (pygame.Surface): The surface to draw on.
        """
        if self.flipping:
            base_width, base_height = self.image.get_size()
            scale_x = abs(self.flip_progress - 0.5) * 2
            # Growth factor for flip effect, scaled to base size
            grow = 1 + (0.5 - abs(self.flip_progress - 0.5)) * 0.5
            width = int(base_width * scale_x * grow)
            height = int(base_height * grow)
            if width > 0 and height > 0:
                img = pygame.transform.scale(self.image, (width, height))
                rect = img.get_rect(center=self.rect.center)
                screen.blit(img, rect)
            if self.flip_progress > 0.5 and self.hidden:
                self.hidden = False
                self.image = self.get_image()
        else:
            screen.blit(self.image, self.rect)

    def update(self, dt):
        """
        Update the card's animation state.

        Args:
            dt (float): Time delta since last update in seconds.
        """
        if self.animating:
            self.anim_progress += dt / self.duration
            if self.anim_progress >= 1.0:
                self.anim_progress = 1.0
                self.animating = False
                self.pos = self.target_pos[:]
                if self.on_finish:
                    self.on_finish()
            else:
                eased_progress = self.anim_progress
                if self.easing == 'in_cubic':
                    eased_progress = self.anim_progress ** 3
                for i in range(2):
                    self.pos[i] = self.start_pos[i] + (self.target_pos[i] - self.start_pos[i]) * eased_progress
            self.rect.center = self.pos
        if self.flipping:
            self.flip_progress += dt / 0.5
            if self.flip_progress >= 1.0:
                self.flipping = False
                self.flip_progress = 0.0
                self.hidden = False
                self.image = self.get_image()
                if self.on_finish:
                    self.on_finish()

    def move_to(self, pos, duration=0.5, easing=None, on_finish=None):
        """
        Animate the card to a new position.

        Args:
            pos (tuple or list): Target position (x, y).
            duration (float): Animation duration in seconds.
            easing (str or None): Easing type.
            on_finish (callable or None): Callback when animation completes.
        """
        self.start_pos = self.pos[:]
        self.target_pos = list(pos)
        self.anim_progress = 0.0
        self.duration = duration
        self.easing = easing
        self.on_finish = on_finish
        self.animating = True

    def flip(self, on_finish=None):
        """
        Start the flip animation to reveal the card.

        Args:
            on_finish (callable or None): Callback when flip completes.
        """
        if not self.hidden:
            if on_finish:
                on_finish()
            return
        self.flipping = True
        self.flip_progress = 0.0
        self.on_finish = on_finish
        play_sound(flip_sound, "flip")

class Game:
    """
    Main game controller for the Blackjack application.

    Manages the overall game state, UI elements, animations, and game logic.
    Handles different game phases: intro animation, rules selection, gameplay, and end screen.

    Attributes:
        screen (pygame.Surface): The main display surface.
        clock (pygame.time.Clock): Clock for managing frame rate.
        state (str): Current game state ('intro', 'rules', 'game', 'end').
        Various UI elements: buttons, fonts, cards, etc.
        dealer_mode (int): Dealer behavior mode (0=At Start, 1=With Player, 2=At End).
        dealer_threshold (int): Score threshold for dealer to stop hitting.
        And many more for managing animations, timers, and game data.
    """

    def __init__(self):
        """
        Initialize the Game instance, setting up display, fonts, UI elements, and initial state.
        """
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Blackjack")
        self.clock = pygame.time.Clock()
        self.state = 'intro'
        self.intro_phase = 0
        self.intro_timer = 0.0
        self.dealer_mode = 1
        self.dealer_threshold = 16
        # clear any pending timers so menu transition won't fire after start
        self.reset_timers()
        self.used_cards = set()
        self.player_cards = []
        self.dealer_cards = []
        self.deck_pos = (WIDTH // 2, HEIGHT // 2)
        self.intro_cards = []
        self.intro_phase = 0      # 0=fly out,1=gather back
        self.result_text = ""
        self.totals_text = ""
        self.timer_event = 0
        self.dealing = False
        self.deal_index = 0
        self.deal_cards = []
        self.flipping = False
        self.flip_index = 0
        self.flip_cards = []
        self.player_stood = False
        self._dealer_playing = False
        self.pending_dealer_turn = False
        self.dealer_stood = False  # tracks when dealer decides to stand during "with player" mode
        # durations for intro animation will be computed when starting
        self.intro_out = 2.0
        self.intro_back = 2.0
        
        # Initialize layout and fonts (creates all UI elements with proper scaling)
        self.update_layout()
    
    def update_fonts(self):
        """Update font sizes based on current screen dimensions."""
        self.font_large = pygame.font.SysFont(None, get_font_size(48))
        self.font_medium = pygame.font.SysFont(None, get_font_size(36))
        self.font_small = pygame.font.SysFont(None, get_font_size(24))
    
    def update_layout(self):
        """Recreate UI elements with scaled positions and sizes."""
        self.update_fonts()
        load_scaled_cards()
        
        # Game buttons (hit/stand)
        button_width = get_scaled_value(100, 'dialog')
        spacing = get_scaled_value(50, 'dialog')
        total_width = button_width * 2 + spacing
        start_x = WIDTH // 2 - total_width // 2
        self.hit_btn = Button(start_x, HEIGHT - get_scaled_value(60, 'height'), button_width, get_scaled_value(40, 'height'), "Hit", self.font_medium)
        self.stand_btn = Button(start_x + button_width + spacing, HEIGHT - get_scaled_value(60, 'height'), button_width, get_scaled_value(40, 'height'), "Stand", self.font_medium)
        
        # Rules menu buttons (start/quit)
        button_width = get_scaled_value(100, 'dialog')
        spacing = get_scaled_value(50, 'dialog')
        total_width = button_width * 2 + spacing
        start_x = WIDTH // 2 - total_width // 2
        self.start_btn = Button(start_x, HEIGHT - get_scaled_value(50, 'height'), button_width, get_scaled_value(40, 'height'), "Start", self.font_medium)
        self.quit_btn = Button(start_x + button_width + spacing, HEIGHT - get_scaled_value(50, 'height'), button_width, get_scaled_value(40, 'height'), "Quit", self.font_medium)
        
        # Mode selection buttons
        button_width = get_scaled_value(150, 'dialog')
        spacing = get_scaled_value(25, 'dialog')
        total_width = button_width * 3 + spacing * 2
        start_x = WIDTH // 2 - total_width // 2
        self.mode_btns = [
            Button(start_x, get_scaled_value(200, 'height'), button_width, get_scaled_value(40, 'height'), "At Start", self.font_small),
            Button(start_x + button_width + spacing, get_scaled_value(200, 'height'), button_width, get_scaled_value(40, 'height'), "With Player", self.font_small),
            Button(start_x + 2 * (button_width + spacing), get_scaled_value(200, 'height'), button_width, get_scaled_value(40, 'height'), "At End", self.font_small)
        ]
        # mark initial selection
        for j, b in enumerate(self.mode_btns):
            b.selected = (j == self.dealer_mode)
        
        # Threshold input
        input_width = get_scaled_value(100, 'dialog')
        input_height = get_scaled_value(40, 'height')
        self.threshold_input = TextInput(WIDTH // 2 - input_width // 2, get_scaled_value(300, 'height'), input_width, input_height, self.font_small)
        
        # Play again buttons
        button_width = get_scaled_value(120, 'dialog')
        spacing = get_scaled_value(20, 'dialog')
        total_width = button_width * 2 + spacing
        start_x = WIDTH // 2 - total_width // 2
        y = HEIGHT // 2 + get_scaled_value(80, 'height')
        self.play_again_btns = [
            Button(start_x, y, button_width, get_scaled_value(40, 'height'), "Play Again", self.font_small),
            Button(start_x + button_width + spacing, y, button_width, get_scaled_value(40, 'height'), "Menu", self.font_small)
        ]
    
    def get_dealer_card_pos(self, card_index):
        """Get scaled position for dealer card."""
        card_width, card_height = get_card_dimensions()
        # Base positioning at reference resolution
        base_x = 100
        base_spacing = 60
        base_y = 80
        
        x = get_scaled_value(base_x, 'width') + card_index * (card_width + get_scaled_value(base_spacing, 'width'))
        y = get_scaled_value(base_y, 'height') + card_height // 2
        return (x, y)
    
    def get_player_card_pos(self, card_index):
        """Get scaled position for player card."""
        card_width, card_height = get_card_dimensions()
        # Base positioning at reference resolution
        base_x = 100
        base_spacing = 60
        base_y_offset = 270
        
        x = get_scaled_value(base_x, 'width') + card_index * (card_width + get_scaled_value(base_spacing, 'width'))
        y = HEIGHT - get_scaled_value(base_y_offset, 'height') + card_height // 2
        return (x, y)

    def draw_card(self):
        while True:
            card = (random.randint(1, 13), random.randint(1, 4))
            if card not in self.used_cards:
                self.used_cards.add(card)
                return card

    def calculate_score(self, cards):
        """
        Calculate the Blackjack score for a list of cards, handling Aces optimally.

        Args:
            cards (list[Card]): List of cards to score.

        Returns:
            int: The calculated score.
        """
        if not cards:
            return 0
        nums = [c.num for c in cards]
        total = sum(min(n, 10) for n in nums)
        aces = nums.count(1)
        while aces > 0 and total + 10 <= 21:
            total += 10
            aces -= 1
        return total

    def reset_timers(self):
        """
        Clear all pending timers to prevent unwanted state transitions.
        """
        # disable all user timers and clear state
        for i in range(1, 5):
            pygame.time.set_timer(pygame.USEREVENT + i, 0)
        self.timer_event = 0

    def run(self):
        """
        Main game loop. Handles events, updates state, and renders the screen.
        """
        running = True
        while running:
            try:
                dt = self.clock.tick(FPS) / 1000.0
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.VIDEORESIZE:
                        global WIDTH, HEIGHT
                        # Enforce 4:3 aspect ratio
                        new_width, new_height = enforce_aspect_ratio(event.size[0], event.size[1])
                        WIDTH, HEIGHT = new_width, new_height
                        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                        self.update_layout()
                    elif event.type == pygame.USEREVENT + self.timer_event:
                        self.handle_timer()
                    else:
                        self.handle_event(event)
                self.update(dt)
                self.draw()
                pygame.display.flip()
            except Exception as e:
                print("Exception in main loop:", e)
                import traceback
                traceback.print_exc()
                running = False
        pygame.quit()

    def handle_event(self, event):
        """
        Handle user input events based on current game state.

        Args:
            event (pygame.event.Event): The event to handle.
        """
        mouse_pos = pygame.mouse.get_pos()
        if self.state == 'rules':
            self.threshold_input.handle_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, btn in enumerate(self.mode_btns):
                    if btn.click(event.pos):
                        self.dealer_mode = i
                if self.start_btn.click(event.pos):
                    self.dealer_threshold = self.threshold_input.get_value()
                    self.state = 'game'
                    self.start_game()
                elif self.quit_btn.click(event.pos):
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif self.state == 'game':
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.hit_btn.enabled and self.hit_btn.click(event.pos) and not self.player_stood and not self._dealer_playing:
                    self.player_hit()
                elif self.stand_btn.enabled and self.stand_btn.click(event.pos) and not self.player_stood and not self._dealer_playing:
                    self.player_stood = True
                    self.dealer_turn()
        elif self.state == 'end':
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.play_again_btns[0].click(event.pos):
                    self.start_game()
                elif self.play_again_btns[1].click(event.pos):
                    self.state = 'rules'

    def update(self, dt):
        """
        Update game state and animations.

        Args:
            dt (float): Time delta since last update.
        """
        mouse_pos = pygame.mouse.get_pos()
        if self.state == 'intro':
            # manage timing for intro phases
            self.intro_timer += dt
            if self.intro_phase == 0 and self.intro_timer >= self.intro_out:
                # start gathering back
                for card in self.intro_cards:
                    card.move_to(self.deck_pos, self.intro_back, 'in_out_cubic')
                self.intro_phase = 1
                self.intro_timer = 0.0
            elif self.intro_phase == 1 and self.intro_timer >= self.intro_back:
                self.state = 'rules'
        elif self.state == 'rules':
            self.threshold_input.update(mouse_pos)
            for btn in self.mode_btns:
                btn.update(mouse_pos)
            self.start_btn.update(mouse_pos)
            self.quit_btn.update(mouse_pos)
        elif self.state == 'game':
            self.hit_btn.update(mouse_pos)
            self.stand_btn.update(mouse_pos)
            for card in self.player_cards + self.dealer_cards:
                card.update(dt)
        elif self.state == 'end':
            for btn in self.play_again_btns:
                btn.update(mouse_pos)
        for card in self.intro_cards:
            card.update(dt)

        # if dealer turn was queued while animations were running, trigger now
        if self.pending_dealer_turn:
            animating = any(c.animating for c in self.player_cards + self.dealer_cards)
            if not animating:
                self.pending_dealer_turn = False
                self.dealer_turn()

    def draw(self):
        """
        Render the current game state to the screen.
        """
        self.screen.fill(GREEN)
        if self.state == 'intro':
            for card in self.intro_cards:
                card.draw(self.screen)
        elif self.state == 'rules':
            self.draw_rules()
        elif self.state == 'game' or self.state == 'end':
            self.draw_game()
            if self.state == 'end':
                for btn in self.play_again_btns:
                    btn.draw(self.screen)

    def draw_rules(self):
        title = self.font_large.render("BLACKJACK", True, WHITE)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, get_scaled_value(50, 'height')))
        dealer_text = self.font_medium.render("The Dealer should play:", True, WHITE)
        self.screen.blit(dealer_text, (WIDTH // 2 - dealer_text.get_width() // 2, get_scaled_value(120, 'height')))
        # update selection state
        for j, btn in enumerate(self.mode_btns):
            btn.selected = (j == self.dealer_mode)
            btn.draw(self.screen)
        threshold_text = self.font_medium.render("The Dealer has to draw on:", True, WHITE)
        self.screen.blit(threshold_text, (WIDTH // 2 - threshold_text.get_width() // 2, get_scaled_value(260, 'height')))
        self.threshold_input.draw(self.screen)
        self.start_btn.draw(self.screen)
        self.quit_btn.draw(self.screen)

    def draw_game(self):
        dealer_label_x = get_scaled_value(50, 'width')
        dealer_label_y = get_scaled_value(50, 'height')
        dealer_text = self.font_medium.render("Dealer's hand:", True, WHITE)
        self.screen.blit(dealer_text, (dealer_label_x, dealer_label_y))
        for card in self.dealer_cards:
            card.draw(self.screen)
        # Show STAND! text when dealer stands during "with player" mode
        if self.dealer_mode == 1 and self.dealer_stood and not self.player_stood:
            stand_text = self.font_medium.render("STAND!", True, YELLOW)
            # Position to the right of the dealer's last card
            if self.dealer_cards:
                last_card_x = self.dealer_cards[-1].rect.right + get_scaled_value(20, 'width')
                self.screen.blit(stand_text, (last_card_x, get_scaled_value(80, 'height')))
        
        player_label_x = get_scaled_value(50, 'width')
        player_label_y = HEIGHT - get_scaled_value(300, 'height')
        player_text = self.font_medium.render("Your hand:", True, WHITE)
        self.screen.blit(player_text, (player_label_x, player_label_y))
        for card in self.player_cards:
            card.draw(self.screen)
        # Deck
        deck_img = card_back_red  # or any back
        deck_rect = deck_img.get_rect(center=self.deck_pos)
        self.screen.blit(deck_img, deck_rect)
        # Buttons
        if self.state == 'game':
            self.hit_btn.draw(self.screen)
            self.stand_btn.draw(self.screen)
        # Result
        if self.result_text:
            result_surf = self.font_large.render(self.result_text, True, YELLOW)
            self.screen.blit(result_surf, (WIDTH // 2 - result_surf.get_width() // 2, HEIGHT // 2 - get_scaled_value(50, 'height')))
        if self.totals_text:
            totals_surf = self.font_medium.render(self.totals_text, True, WHITE)
            self.screen.blit(totals_surf, (WIDTH // 2 - totals_surf.get_width() // 2, HEIGHT // 2))

    def start_intro(self):
        # compute shuffle length, fall back to 2s; split into two halves so total animation
        # matches the sound duration. we'll apply easing on the return phase to create a bell curve.
        length = shuffle_sound.get_length() if shuffle_sound else 2.0
        half = length / 2.0
        self.intro_out = half
        self.intro_back = half
        self.intro_cards = []
        self.intro_phase = 0
        self.intro_timer = 0.0
        red_count = 0
        blue_count = 0
        for _ in range(40):
            suit = random.randint(1, 4)
            if suit in [2, 3]:
                if red_count < 20:
                    red_count += 1
                else:
                    suit = random.choice([1, 4])
                    blue_count += 1
            else:
                if blue_count < 20:
                    blue_count += 1
                else:
                    suit = random.choice([2, 3])
                    red_count += 1
            card = Card(1, suit, hidden=True)
            card.pos = list(self.deck_pos)
            self.intro_cards.append(card)
        # Animate out using shuffle length
        for card in self.intro_cards:
            dx = random.randint(-WIDTH // 2, WIDTH // 2)
            dy = random.randint(-HEIGHT // 2, HEIGHT // 2)
            end_pos = (self.deck_pos[0] + dx, self.deck_pos[1] + dy)
            card.move_to(end_pos, self.intro_out, 'out_cubic')
        play_sound(shuffle_sound, "shuffle")

    def handle_timer(self):
        # clear pending timer to avoid unwanted transitions
        print("handle_timer event", self.timer_event)
        current = self.timer_event
        self.reset_timers()
        if current == 1:
            # Gather back (reserved but not normally used anymore)
            for card in self.intro_cards:
                card.move_to(self.deck_pos, self.intro_back, 'in_out_cubic')
            self.timer_event = 2
            pygame.time.set_timer(pygame.USEREVENT + 2, int(self.intro_back * 1000))
        elif current == 2:
            self.state = 'rules'
        elif current == 3:
            self.state = 'end'
        elif current == 4:
            self.on_reveal_done()
        elif current == 5:
            self.flip_next()

    def start_game(self):
        """
        Reset game state for a new round and begin dealing initial cards.
        """
        # prepare for new round
        self.state = 'game'                    # <--- ensure state switches back
        self.reset_timers()
        self.used_cards.clear()
        self.player_cards = []
        self.dealer_cards = []
        self.result_text = ""
        self.totals_text = ""
        self.player_stood = False
        self.dealer_stood = False
        # initially controls disabled until cards dealt
        self.hit_btn.enabled = False
        self.stand_btn.enabled = False
        self.deal_initial()

    def deal_initial(self):
        self.deal_cards = []
        # Dealer 2
        for i in range(2):
            card_data = self.draw_card()
            card = Card(card_data[0], card_data[1], hidden=(i == 1))
            self.dealer_cards.append(card)
            card.pos = list(self.deck_pos)
            card.rect.center = card.pos
            target_pos = self.get_dealer_card_pos(i)
            self.deal_cards.append((card, target_pos, 0.5))
        # Player 2
        for i in range(2):
            card_data = self.draw_card()
            card = Card(card_data[0], card_data[1], hidden=False)
            self.player_cards.append(card)
            card.pos = list(self.deck_pos)
            card.rect.center = card.pos
            target_pos = self.get_player_card_pos(i)
            self.deal_cards.append((card, target_pos, 0.5))
        self.deal_index = 0
        self.dealing = True
        self.deal_next()

    def deal_next(self):
        if self.deal_index < len(self.deal_cards):
            card, pos, duration = self.deal_cards[self.deal_index]
            card.move_to(pos, duration, on_finish=self.on_deal_finish)
            play_sound(draw_sound, "draw")
            self.deal_index += 1
        else:
            self.dealing = False
            # Check blackjack or auto-start dealer draw
            if self.calculate_score(self.player_cards) == 21:
                self.dealer_turn()
            elif self.dealer_mode == 0:
                # draw extra dealer cards then enable controls afterwards
                self.deal_extra_dealer(on_complete=self.enable_controls)
            else:
                self.enable_controls()

    def on_deal_finish(self):
        self.deal_next()

    def deal_extra_dealer(self, on_complete=None):
        # sequentially deal face-down cards from pile until threshold met
        def cond():
            return self.calculate_score(self.dealer_cards) < self.dealer_threshold
        self.queue_dealer_draws(hidden=True, condition_fn=cond, callback=on_complete or (lambda: None))

    def player_hit(self):
        card_data = self.draw_card()
        card = Card(card_data[0], card_data[1], hidden=False)
        self.player_cards.append(card)
        card.pos = list(self.deck_pos)
        card.rect.center = card.pos
        target_pos = self.get_player_card_pos(len(self.player_cards) - 1)

        # Disable buttons during animation
        self.hit_btn.enabled = False
        self.stand_btn.enabled = False

        def after_draw():
            score = self.calculate_score(self.player_cards)
            if score >= 21:
                # queue dealer turn until all animations complete
                self.pending_dealer_turn = True
            elif self.dealer_mode == 1:
                self.dealer_react()
            self.enable_controls()

        card.move_to(target_pos, 0.5, on_finish=after_draw)
        play_sound(draw_sound, "draw")

    def dealer_react(self):
        if self.calculate_score(self.dealer_cards) < self.dealer_threshold:
            card_data = self.draw_card()
            card = Card(card_data[0], card_data[1], hidden=True)
            self.dealer_cards.append(card)
            card.pos = list(self.deck_pos)
            card.rect.center = card.pos
            target_pos = self.get_dealer_card_pos(len(self.dealer_cards) - 1)
            # Disable buttons during animation
            self.hit_btn.enabled = False
            self.stand_btn.enabled = False
            card.move_to(target_pos, 0.5, on_finish=self.enable_controls)
            play_sound(draw_sound, "draw")
        else:
            # dealer stands (score >= threshold) during "with player" mode
            self.dealer_stood = True
            self.enable_controls()

    def enable_controls(self):
        # only allow buttons when player hasn't stood and hasn't busted or hit 21
        if not self.player_stood and self.calculate_score(self.player_cards) < 21:
            self.hit_btn.enabled = True
            self.stand_btn.enabled = True
        else:
            self.hit_btn.enabled = False
            self.stand_btn.enabled = False

    def dealer_turn(self):
        """
        Handle the dealer's turn: reveal hidden cards and play according to mode.
        """
        # disable player controls while dealer is revealing
        self.hit_btn.enabled = False
        self.stand_btn.enabled = False
        self._dealer_playing = True
        hidden_cards = [c for c in self.dealer_cards if c.hidden]
        if hidden_cards:
            self.flip_cards = hidden_cards
            self.flip_index = 0
            self.flipping = True
            self.flip_next()
        else:
            self.on_reveal_done()

    # ------------------------------------------------------------------
    # helper to queue sequential dealer draws (used by auto-play and extra-dealer)
    def queue_dealer_draws(self, hidden, condition_fn, callback):
        self.dealer_queue = []
        # build list of cards to draw
        while condition_fn():
            card_data = self.draw_card()
            card = Card(card_data[0], card_data[1], hidden=hidden)
            self.dealer_cards.append(card)
            card.pos = list(self.deck_pos)
            card.rect.center = card.pos
            # Position is based on the card's index in dealer_cards
            target_pos = self.get_dealer_card_pos(len(self.dealer_cards) - 1)
            self.dealer_queue.append((card, target_pos, 0.5))
        self.dealer_draw_index = 0
        self.dealer_draw_callback = callback
        if self.dealer_queue:
            self.dealer_draw_next()
        else:
            # nothing to draw, just call callback immediately
            callback()

    def dealer_draw_next(self):
        if self.dealer_draw_index < len(self.dealer_queue):
            card, pos, duration = self.dealer_queue[self.dealer_draw_index]
            self.dealer_draw_index += 1
            card.move_to(pos, duration, on_finish=self.dealer_draw_next)
            play_sound(draw_sound, "draw")
        else:
            # done
            cb = getattr(self, 'dealer_draw_callback', None)
            if cb:
                self.dealer_draw_callback()
                self.dealer_draw_callback = None

    def flip_next(self):
        if self.flip_index < len(self.flip_cards):
            self.flip_cards[self.flip_index].flip(on_finish=self.on_flip_finish)
            self.flip_index += 1
        else:
            self.flipping = False
            self.on_reveal_done()

    def on_flip_finish(self):
        # wait then trigger next flip via timer_event 5
        self.timer_event = 5
        pygame.time.set_timer(pygame.USEREVENT + 5, 500)

    def on_reveal_done(self):
        if self.dealer_mode == 0:
            self.end_game()
        elif self.dealer_mode == 1:
            if self.calculate_score(self.dealer_cards) >= self.dealer_threshold:
                self.end_game()
            else:
                self.dealer_auto_play()
        else:
            self.dealer_auto_play()

    def dealer_auto_play(self):
        # sequentially draw until threshold reached, then end game
        def cond():
            return self.calculate_score(self.dealer_cards) < self.dealer_threshold
        self.queue_dealer_draws(hidden=False, condition_fn=cond, callback=self.end_game)

    def end_game(self):
        """
        Determine game outcome and transition to end state.
        """
        # dealer finished revealing, allow any UI cleanup
        self._dealer_playing = False
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
        self.result_text = msg
        self.totals_text = f"Your: {p_score} | Dealer: {d_score}"
        self.timer_event = 3
        pygame.time.set_timer(pygame.USEREVENT + 3, 2000)

if __name__ == "__main__":
    game = Game()
    game.start_intro()
    game.run()