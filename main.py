from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty, NumericProperty, ListProperty, BooleanProperty
from kivy.lang import Builder
from kivy.core.audio import SoundLoader
import random
import os
import math


def _load_terms(filename):
    path = os.path.join("picsnlists", filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return []
    # Datei enthält eine durch Kommata getrennte Liste
    parts = [p.strip() for p in content.split(",")]
    return [p for p in parts if p]


KOCHSTIL_TERMS = _load_terms("Kochstil.txt")
GERICHTE_TERMS = _load_terms("Gerichte.txt")
ZUTATEN_TERMS = _load_terms("Zutaten.txt")


class MenuScreen(Screen):
    def on_pre_enter(self, *args):
        """Start menu music when entering menu."""
        app = App.get_running_app()
        if hasattr(app, 'play_menu_music'):
            app.play_menu_music()
        return super().on_pre_enter(*args)


class GameScreen(Screen):
    current_card_source = StringProperty("")
    card_sources = ListProperty()
    current_index = NumericProperty(0)

    round_number = NumericProperty(1)
    start_back_order = ListProperty()

    last_back_type = StringProperty("")  # "cooking", "dish", "ingredient"
    front_word_top = StringProperty("")
    front_word_mid = StringProperty("")
    front_word_bottom = StringProperty("")
    current_player_index = NumericProperty(0)  # 0,1,2
    player_turn_text = StringProperty("")
    player_color = ListProperty([1, 1, 1, 1])

    selected_index = NumericProperty(-1)  # -1 = nichts gewählt, 0/1/2 = Top/Mid/Bottom
    current_round_choices = ListProperty()
    previous_decisions_text = StringProperty("")  # Text showing previous decisions

    # Einfache Runden-Summary nach Runde 1 und 2 (wird über eigenen Screen angezeigt)
    show_summary = BooleanProperty(False)  # bleibt für Abwärtskompatibilität, wird hier nicht mehr genutzt
    summary_words = ListProperty()

    # Merker, ob die Session schon initialisiert wurde
    session_initialized = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._backs_fixed_order = [
            "picsnlists/backpic_chef_cooking style.png",
            "picsnlists/backpic_chef_dish.png",
            "picsnlists/backpic_chef_ingredient.png",
        ]
        self._used_kochstil = []
        self._used_gerichte = []
        self._used_zutaten = []
        self._player_for_back = {}
        self._round_summaries = []

    def on_pre_enter(self, *args):
        # Neue Session nur beim ersten Betreten starten
        if not self.session_initialized:
            backs = list(self._backs_fixed_order)
            self.start_back_order = random.sample(backs, k=len(backs))
            self.round_number = 1

            # Verwendete Begriffe für diese Session zurücksetzen
            self._used_kochstil = []
            self._used_gerichte = []
            self._used_zutaten = []
            self._build_round_card_sources()
            self.current_index = 0
            self.current_card_source = self.card_sources[0]
            self._update_last_back_type_from_source(self.current_card_source)
            self.session_initialized = True
        return super().on_pre_enter(*args)

    def _build_round_card_sources(self):
        # Bestimme, mit welcher Backkarte diese Runde startet
        if not self.start_back_order or self.round_number < 1 or self.round_number > 3:
            return

        first_back = self.start_back_order[self.round_number - 1]

        # Reihenfolge der drei Backs in dieser Runde: Rotation der Fix-Liste
        backs = self._backs_fixed_order
        try:
            start_index = backs.index(first_back)
        except ValueError:
            start_index = 0
        ordered_backs = backs[start_index:] + backs[:start_index]

        # Spieler-Zuordnung für diese Runde: 1. Back -> Player 1, 2. -> Player 2, 3. -> Player 3
        self._player_for_back = {back: idx for idx, back in enumerate(ordered_backs)}

        front = "picsnlists/fontpic-chef_cooking style.png"
        self.card_sources = [
            ordered_backs[0],
            front,
            ordered_backs[1],
            front,
            ordered_backs[2],
            front,
        ]

    def _update_last_back_type_from_source(self, source):
        if "cooking" in source:
            self.last_back_type = "cooking"
        elif "dish" in source:
            self.last_back_type = "dish"
        elif "ingredient" in source:
            self.last_back_type = "ingredient"

        # Spieler anhand der Position dieser Backkarte in der aktuellen Runde bestimmen
        self.current_player_index = self._player_for_back.get(source, 0)

        if self.last_back_type:
            player_number = self.current_player_index + 1
            self.player_turn_text = f"Now it's Player {player_number}'s turn"

        # Spielerfarbe je nach Index setzen: 0 -> rot, 1 -> blau, 2 -> gelb
        if self.current_player_index == 0:
            self.player_color = [1, 0.5, 0.5, 1]
        elif self.current_player_index == 1:
            self.player_color = [0.6, 0.8, 1, 1]
        else:
            self.player_color = [1, 1, 0.6, 1]

    def _choose_three_terms(self):
        if self.last_back_type == "cooking":
            pool = KOCHSTIL_TERMS
            used = self._used_kochstil
        elif self.last_back_type == "dish":
            pool = GERICHTE_TERMS
            used = self._used_gerichte
        elif self.last_back_type == "ingredient":
            pool = ZUTATEN_TERMS
            used = self._used_zutaten
        else:
            pool = []
            used = []

        # Begriffe, die in vorherigen Runden schon genutzt wurden, ausschließen
        available = [w for w in pool if w not in used]

        if not available:
            self.front_word_top = ""
            self.front_word_mid = ""
            self.front_word_bottom = ""
            return

        words = (
            random.sample(available, k=3)
            if len(available) >= 3
            else random.sample(available, k=len(available))
        )
        # Falls weniger als 3 verfügbar sind, fehlende zufällig aus bereits gewählten auffüllen
        while len(words) < 3:
            words.append(random.choice(words))

        self.front_word_top, self.front_word_mid, self.front_word_bottom = words

        # Verwendete Begriffe merken
        used.extend([w for w in words if w not in used])

    def next_card(self):
        if not self.card_sources:
            return
        next_index = self.current_index + 1

        # Rundenende erreicht?
        if next_index >= len(self.card_sources):
            # aktuelle Rundenwahl merken
            self._round_summaries.append(list(self.current_round_choices))
            words = list(self.current_round_choices)
            self.summary_words = words
            self.current_round_choices = []

            # Nach Runde 1 und 2: normale SummaryScreen-Ansicht wie bisher
            if self.round_number < 3:
                App.get_running_app().show_summary(self.round_number, words)
                return

            # Nach Runde 3: alle Begriffe aus 3 Runden sammeln und FinalSummaryScreen starten
            flat_words = []
            for round_words in self._round_summaries[:3]:
                flat_words.extend(round_words)
            App.get_running_app().show_final_summary(flat_words)
            return

        # Normales Weiterschalten innerhalb der Runde
        self.current_index = next_index
        self.current_card_source = self.card_sources[self.current_index]

        if "backpic" in self.current_card_source:
            self._update_last_back_type_from_source(self.current_card_source)
        elif "fontpic" in self.current_card_source:
            self._choose_three_terms()
            self.selected_index = -1
            
            # Update previous decisions text directly
            words = [self.front_word_top, self.front_word_mid, self.front_word_bottom]
            previous_words = []
            for choice in self.current_round_choices:
                if isinstance(choice, str):
                    # If it's already a word, add it directly
                    previous_words.append(choice)
                elif choice != -1 and choice < len(words) and words[choice]:
                    # If it's an index, get the word
                    previous_words.append(words[choice])
            self.previous_decisions_text = " | ".join(previous_words)

    def select_front_segment(self, index):
        """Front-Click auf eines der drei Drittel (0 = oben, 1 = Mitte, 2 = unten)."""
        if "fontpic" not in self.current_card_source:
            return
        # Index nur setzen, wenn es auch wirklich ein Wort an dieser Position gibt
        words = [self.front_word_top, self.front_word_mid, self.front_word_bottom]
        if 0 <= index < len(words) and words[index]:
            print("select_front_segment", index, words[index])
            self.selected_index = index

    def _get_selected_word(self):
        if self.selected_index == 0:
            return self.front_word_top
        if self.selected_index == 1:
            return self.front_word_mid
        if self.selected_index == 2:
            return self.front_word_bottom
        return ""

    def confirm_selection(self):
        """Grüner Haken: Auswahl übernehmen und zur nächsten Karte wechseln."""
        if "fontpic" not in self.current_card_source:
            return
        word = self._get_selected_word()
        if word:
            self.current_round_choices.append(word)
        self.selected_index = -1
        self.next_card()

    def cancel_selection(self):
        """Rotes X: Auswahl verwerfen, Karte bleibt, keine Speicherung."""
        if "fontpic" not in self.current_card_source:
            return
        self.selected_index = -1

    def on_touch_down(self, touch):
        """Eingehende Touches behandeln.

        - Erst normale Widgets (Buttons wie X, ✔/✖, Front-Hitboxen) verarbeiten.
        - Wenn nichts reagiert und eine Backkarte angezeigt wird, schalte zur nächsten Karte
          (aber nur, wenn innerhalb der Karte getippt wurde).
        """
        print("on_touch_down at", touch.pos, "current_card=", self.current_card_source)

        menu_x = self.ids.get("menu_x") if "menu_x" in self.ids else None

        # 1) Backkarte: jeder Tap (außer direkt auf das Menü-X) schaltet sofort weiter
        if "backpic" in self.current_card_source:
            if not (menu_x and menu_x.collide_point(*touch.pos)):
                print(" -> backpic tap anywhere (not on X), calling next_card() BEFORE children")
                self.next_card()
                return True

        # 2) Ansonsten normale Widgets (Buttons etc.) zuerst
        handled = super().on_touch_down(touch)
        if handled:
            print(" -> handled by child widget")
            return True

        # 3) Frontkarte: Winkelbasierte Auswahl direkt auf der Karte
        if "fontpic" in self.current_card_source:
            card = self.ids.get("card_image")
            if card and card.collide_point(*touch.pos):
                cx, cy = card.center
                dx = touch.x - cx
                dy = touch.y - cy
                angle_deg = math.degrees(math.atan2(dy, dx))
                if angle_deg < 0:
                    angle_deg += 360

                # Winkelbereiche:
                # 90 <= angle < 210  -> links/oben (mittleres Wort, Index 1)
                # 210 <= angle < 300 -> unten (unteres Wort, Index 2)
                # Rest im Kartenbereich -> rechts/oben (oberes Wort, Index 0)
                if 90 <= angle_deg < 210:
                    index = 1
                elif 210 <= angle_deg < 300:
                    index = 2
                else:
                    index = 0

                print(" -> frontpic angle", angle_deg, "-> index", index)
                self.select_front_segment(index)
                return True

        # 4) Nichts hat reagiert
        print(" -> no widget handled touch, returning False")
        return False
    
    def update_previous_decisions_text(self):
        """Update the text showing previous players' decisions."""
        words = [self.front_word_top, self.front_word_mid, self.front_word_bottom]
        previous_words = []
        for choice in self.current_round_choices:
            if isinstance(choice, str):
                # If it's already a word, add it directly
                previous_words.append(choice)
            elif choice != -1 and choice < len(words) and words[choice]:
                # If it's an index, get the word
                previous_words.append(words[choice])
        self.previous_decisions_text = " | ".join(previous_words)


class RootWidget(ScreenManager):
    pass


class SummaryScreen(Screen):
    round_number = NumericProperty(1)
    summary_words = ListProperty()


class FinalSummaryScreen(Screen):
    # Zeigt nach Runde 3 alle gewählten Begriffe aus 3 Runden
    all_words = ListProperty()
    current_player_index = NumericProperty(0)  # 0,1,2 -> Player 1..3
    selected_index = NumericProperty(-1)  # -1 = nichts gewählt, 0/1/2 = Bubble oben/rechts/links
    selections = ListProperty()  # pro Spieler gewählte Bubble, Länge 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # initial leer: noch keine Auswahl pro Spieler
        self.selections = [-1, -1, -1]

    def select_bubble(self, index):
        """Eine der drei Bubbles auswählen (0 = oben, 1 = rechts, 2 = links)."""
        if 0 <= index <= 2:
            self.selected_index = index

    def confirm_selection(self):
        """Auswahl für aktuellen Spieler übernehmen und zum nächsten Player/ins Menü gehen."""
        if self.selected_index == -1:
            return

        # Auswahl für aktuellen Spieler speichern
        if 0 <= self.current_player_index < 3:
            self.selections[self.current_player_index] = self.selected_index

        # Weiter im Flow (nächster Spieler oder Menü)
        App.get_running_app().advance_final_summary()

    def cancel_selection(self):
        """Auswahl verwerfen, auf diesem Screen bleiben."""
        self.selected_index = -1


class ResultScreen(Screen):
    # Zeigt nach der Abstimmung die Gewinner-Bubble
    all_words = ListProperty()
    winning_index = NumericProperty(-1)  # 0 = oben, 1 = rechts, 2 = links


class VetoScreen(Screen):
    # Wird verwendet, wenn es keinen Mehrheits-Gewinner gibt
    all_words = ListProperty()
    current_player_index = NumericProperty(0)
    selected_index = NumericProperty(-1)
    vetoes = ListProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.vetoes = [-1, -1, -1]

    def select_bubble(self, index):
        if 0 <= index <= 2:
            self.selected_index = index

    def confirm_veto(self):
        if self.selected_index == -1:
            return
        if 0 <= self.current_player_index < 3:
            self.vetoes[self.current_player_index] = self.selected_index
        App.get_running_app().advance_veto()

    def cancel_selection(self):
        self.selected_index = -1


class InstructionsScreen(Screen):
    pass


KV = """
#:import dp kivy.metrics.dp
#:import math math

RootWidget:
    MenuScreen:
    GameScreen:
    SummaryScreen:
    FinalSummaryScreen:
    ResultScreen:
    VetoScreen:
    InstructionsScreen:

<MenuScreen>:
    name: "menu"
    BoxLayout:
        orientation: "vertical"
        spacing: "20dp"
        padding: "40dp"

        Label:
            text: "Cards Against the Chef"
            font_size: "32sp"

        Button:
            text: "Start with 3 Players"
            size_hint_y: None
            height: "48dp"
            on_release: app.set_players_and_start(3)

        Button:
            text: "Instructions"
            size_hint_y: None
            height: "48dp"
            on_release: app.show_instructions()

        Button:
            text: "End Game"
            size_hint_y: None
            height: "48dp"
            on_release: app.stop()

<CardImage@Image>:
    allow_stretch: False
    keep_ratio: True
    size_hint_y: 0.9
    size_hint_x: None
    pos_hint: {"center_x": 0.5, "center_y": 0.5}
    border_visible: True
    on_texture:
        self.width = self.height * (self.texture.width / self.texture.height) if self.texture else 0

    canvas.after:
        Color:
            rgba: (0.9, 0.9, 0.9, 1) if self.border_visible else (0, 0, 0, 0)
        Line:
            width: 0.9
            rounded_rectangle: (self.x - dp(0.8), self.y - dp(0.8), self.width + dp(1.6), self.height + dp(1.6), 28, 28, 28, 28)

<GameScreen>:
    name: "game"
    BoxLayout:
        orientation: "vertical"
        padding: "0dp"
        spacing: "10dp"

        RelativeLayout:
            size_hint_y: 0.9 if not root.show_summary else 0

            CardImage:
                id: card_image
                source: root.current_card_source
                border_visible: "fontpic" not in root.current_card_source

            # Overlay für Frontkarte: drei Linien + drei Begriffe
            FloatLayout:
                size_hint: None, None
                size: card_image.size
                pos: card_image.pos
                opacity: 1 if "fontpic" in root.current_card_source else 0
                disabled: "fontpic" not in root.current_card_source

                canvas.after:
                    Color:
                        rgba: 1, 1, 1, 1
                    Line:
                        width: 1
                        # Linie 1: von der Mitte senkrecht nach oben bis zum oberen Rand der Karte
                        points: [card_image.center_x, card_image.center_y, card_image.center_x, card_image.top]
                    Line:
                        width: 1
                        # Linie 2: von der Mitte schräg nach unten rechts bis zum Kartenrand
                        points: [card_image.center_x, card_image.center_y, card_image.right, card_image.y]
                    Line:
                        width: 1
                        # Linie 3: von der Mitte schräg nach unten links bis zum Kartenrand
                        points: [card_image.center_x, card_image.center_y, card_image.x, card_image.y]

                Label:
                    text: root.front_word_top
                    bold: True
                    color: (0.5, 1, 0.5, 1) if root.selected_index == 0 else (1, 1, 1, 1)
                    font_size: "22sp"
                    halign: "center"
                    valign: "middle"
                    size_hint: None, None
                    size: card_image.width * 0.4, card_image.height * 0.15
                    text_size: self.size
                    # Punkt 1 auf Kreis um Kartenmittelpunkt bei 60°
                    center_x: card_image.center_x + card_image.height * 0.28 * math.cos(math.radians(60))
                    center_y: card_image.center_y + card_image.height * 0.28 * math.sin(math.radians(60))

                Label:
                    text: root.front_word_mid
                    bold: True
                    color: (0.5, 1, 0.5, 1) if root.selected_index == 1 else (1, 1, 1, 1)
                    font_size: "20sp"
                    halign: "center"
                    valign: "middle"
                    size_hint: None, None
                    size: card_image.width * 0.4, card_image.height * 0.15
                    text_size: self.size
                    # Punkt 2 auf Kreis bei 120°
                    center_x: card_image.center_x + card_image.height * 0.28 * math.cos(math.radians(120))
                    center_y: card_image.center_y + card_image.height * 0.28 * math.sin(math.radians(120))

                Label:
                    text: root.front_word_bottom
                    bold: True
                    color: (0.5, 1, 0.5, 1) if root.selected_index == 2 else (1, 1, 1, 1)
                    font_size: "20sp"
                    halign: "center"
                    valign: "middle"
                    size_hint: None, None
                    size: card_image.width * 0.4, card_image.height * 0.15
                    text_size: self.size
                    # Punkt 3 auf Kreis bei 270°
                    center_x: card_image.center_x + card_image.height * 0.28 * math.cos(math.radians(270))
                    center_y: card_image.center_y + card_image.height * 0.28 * math.sin(math.radians(270))

            # Menü-X oben links über der Karte
            Button:
                id: menu_x
                text: "X"
                size_hint: None, None
                size: dp(32), dp(32)
                pos: card_image.x + dp(4), card_image.top - dp(36)
                background_normal: ""
                background_down: ""
                background_color: 0, 0, 0, 0
                color: 1, 1, 1, 1
                on_release: app.switch_to_menu()

            # Bestätigen / Verwerfen unten auf der Frontkarte
            BoxLayout:
                size_hint: None, None
                size: card_image.width * 0.7, dp(60)
                center_x: card_image.center_x
                y: card_image.y + dp(4)
                spacing: dp(12)
                opacity: 1 if "fontpic" in root.current_card_source and root.selected_index != -1 else 0

                Button:
                    text: "continue"
                    font_size: "20sp"
                    size_hint_x: 0.5
                    disabled: "fontpic" not in root.current_card_source or root.selected_index == -1
                    background_normal: ""
                    color: 0.5, 1, 0.5, 1
                    on_release: root.confirm_selection()

                Button:
                    text: "Back"
                    font_size: "20sp"
                    size_hint_x: 0.5
                    disabled: "fontpic" not in root.current_card_source or root.selected_index == -1
                    background_normal: ""
                    color: 1, 0.3, 0.3, 1
                    on_release: root.cancel_selection()

        # Spieleranzeige unterhalb der Karte
        Label:
            text: root.player_turn_text if "backpic" in root.current_card_source else ""
            font_size: "20sp"
            bold: True
            halign: "center"
            valign: "middle"
            text_size: self.size
            size_hint_y: None
            height: "40dp"
            color: root.player_color

        # Previous decisions display
        Label:
            text: root.previous_decisions_text
            font_size: "16sp"
            color: (0.8, 0.8, 0.8, 1)
            size_hint_y: None
            height: "25dp"
            opacity: 1 if "fontpic" in root.current_card_source else 0
            halign: "center"
            valign: "middle"
            text_size: self.size


<SummaryScreen>:
    name: "summary"
    BoxLayout:
        orientation: "vertical"
        padding: "0dp"
        spacing: "10dp"

        Label:
            text: "Round " + str(root.round_number)
            font_size: "24sp"
            size_hint_y: None
            height: "40dp"

        RelativeLayout:
            size_hint_y: 0.9

            # Vollbild-Button, um per Tap zur nächsten Runde zu gehen
            Button:
                background_normal: ""
                background_down: ""
                background_color: 0, 0, 0, 0
                size_hint: 1, 1
                on_release: app.start_next_round_from_summary()

            BoxLayout:
                orientation: "horizontal"
                size_hint: 0.9, 0.9
                pos_hint: {"center_x": 0.5, "center_y": 0.5}
                spacing: dp(10)

                BoxLayout:
                    orientation: "vertical"
                    size_hint_x: 0.3
                    padding: dp(8)
                    canvas.before:
                        Color:
                            rgba: 0.15, 0.15, 0.15, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [dp(18), dp(18), dp(18), dp(18)]

                    Label:
                        text: root.summary_words[0] if len(root.summary_words) > 0 else ""
                        halign: "center"
                        valign: "middle"
                        text_size: self.size

                BoxLayout:
                    orientation: "vertical"
                    size_hint_x: 0.3
                    padding: dp(8)
                    canvas.before:
                        Color:
                            rgba: 0.15, 0.15, 0.15, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [dp(18), dp(18), dp(18), dp(18)]

                    Label:
                        text: root.summary_words[1] if len(root.summary_words) > 1 else ""
                        halign: "center"
                        valign: "middle"
                        text_size: self.size

                BoxLayout:
                    orientation: "vertical"
                    size_hint_x: 0.3
                    padding: dp(8)
                    canvas.before:
                        Color:
                            rgba: 0.15, 0.15, 0.15, 1
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [dp(18), dp(18), dp(18), dp(18)]

                    Label:
                        text: root.summary_words[2] if len(root.summary_words) > 2 else ""
                        halign: "center"
                        valign: "middle"
                        text_size: self.size


<FinalSummaryScreen>:
    name: "final_summary"
    BoxLayout:
        orientation: "vertical"
        padding: "0dp"
        spacing: "10dp"

        Label:
            text: "Choose the dish you want to cook - Player " + str(root.current_player_index + 1)
            font_size: "24sp"
            size_hint_y: None
            height: "40dp"

        RelativeLayout:
            size_hint_y: 0.9

            # Obere Bubble (Runde 1)
            BoxLayout:
                id: bubble_top
                orientation: "vertical"
                size_hint: 0.4, 0.35
                pos_hint: {"center_x": 0.5, "center_y": 0.75}
                padding: dp(8)
                spacing: dp(4)
                canvas.before:
                    Color:
                        rgba: 0, 0, 0, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(24), dp(24), dp(24), dp(24)]
                canvas.after:
                    Color:
                        rgba: 1, 1, 1, 1
                    Line:
                        width: 1.2
                        rounded_rectangle: (self.x, self.y, self.width, self.height, dp(24), dp(24), dp(24), dp(24))

                Label:
                    text: root.all_words[0] if len(root.all_words) > 0 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (0.5, 1, 0.5, 1) if root.selected_index == 0 else (1, 1, 1, 1)
                Label:
                    text: root.all_words[1] if len(root.all_words) > 1 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (0.5, 1, 0.5, 1) if root.selected_index == 0 else (1, 1, 1, 1)
                Label:
                    text: root.all_words[2] if len(root.all_words) > 2 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (0.5, 1, 0.5, 1) if root.selected_index == 0 else (1, 1, 1, 1)

            # Klickbare Fläche für obere Bubble
            Button:
                background_normal: ""
                background_down: ""
                background_color: 0, 0, 0, 0
                size_hint: 0.4, 0.35
                pos_hint: {"center_x": 0.5, "center_y": 0.75}
                on_release: root.select_bubble(0)

            # Rechte Bubble (Runde 2)
            BoxLayout:
                id: bubble_right
                orientation: "vertical"
                size_hint: 0.4, 0.35
                pos_hint: {"center_x": 0.78, "center_y": 0.35}
                padding: dp(8)
                spacing: dp(4)
                canvas.before:
                    Color:
                        rgba: 0, 0, 0, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(24), dp(24), dp(24), dp(24)]
                canvas.after:
                    Color:
                        rgba: 1, 1, 1, 1
                    Line:
                        width: 1.2
                        rounded_rectangle: (self.x, self.y, self.width, self.height, dp(24), dp(24), dp(24), dp(24))

                Label:
                    text: root.all_words[3] if len(root.all_words) > 3 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (0.5, 1, 0.5, 1) if root.selected_index == 1 else (1, 1, 1, 1)
                Label:
                    text: root.all_words[4] if len(root.all_words) > 4 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (0.5, 1, 0.5, 1) if root.selected_index == 1 else (1, 1, 1, 1)
                Label:
                    text: root.all_words[5] if len(root.all_words) > 5 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (0.5, 1, 0.5, 1) if root.selected_index == 1 else (1, 1, 1, 1)

            Button:
                background_normal: ""
                background_down: ""
                background_color: 0, 0, 0, 0
                size_hint: 0.4, 0.35
                pos_hint: {"center_x": 0.78, "center_y": 0.35}
                on_release: root.select_bubble(1)

            # Linke Bubble (Runde 3)
            BoxLayout:
                id: bubble_left
                orientation: "vertical"
                size_hint: 0.4, 0.35
                pos_hint: {"center_x": 0.22, "center_y": 0.35}
                padding: dp(8)
                spacing: dp(4)
                canvas.before:
                    Color:
                        rgba: 0, 0, 0, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(24), dp(24), dp(24), dp(24)]
                canvas.after:
                    Color:
                        rgba: 1, 1, 1, 1
                    Line:
                        width: 1.2
                        rounded_rectangle: (self.x, self.y, self.width, self.height, dp(24), dp(24), dp(24), dp(24))

                Label:
                    text: root.all_words[6] if len(root.all_words) > 6 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (0.5, 1, 0.5, 1) if root.selected_index == 2 else (1, 1, 1, 1)
                Label:
                    text: root.all_words[7] if len(root.all_words) > 7 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (0.5, 1, 0.5, 1) if root.selected_index == 2 else (1, 1, 1, 1)
                Label:
                    text: root.all_words[8] if len(root.all_words) > 8 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (0.5, 1, 0.5, 1) if root.selected_index == 2 else (1, 1, 1, 1)

            Button:
                background_normal: ""
                background_down: ""
                background_color: 0, 0, 0, 0
                size_hint: 0.4, 0.35
                pos_hint: {"center_x": 0.22, "center_y": 0.35}
                on_release: root.select_bubble(2)

            # Bestätigen / Verwerfen am unteren Rand
            BoxLayout:
                size_hint: None, None
                size: dp(220), dp(60)
                pos_hint: {"center_x": 0.5}
                y: dp(20)
                spacing: dp(12)
                opacity: 1 if root.selected_index != -1 else 0

                Button:
                    text: "continue"
                    font_size: "20sp"
                    size_hint_x: 0.5
                    background_normal: ""
                    color: 0.5, 1, 0.5, 1
                    on_release: root.confirm_selection()

                Button:
                    text: "Back"
                    font_size: "20sp"
                    size_hint_x: 0.5
                    background_normal: ""
                    color: 1, 0.3, 0.3, 1
                    on_release: root.cancel_selection()


<ResultScreen>:
    name: "result"
    BoxLayout:
        orientation: "vertical"
        padding: "0dp"
        spacing: "10dp"

        Label:
            text: "Interesting pick, Chef! Time to cook."
            font_size: "24sp"
            size_hint_y: None
            height: "40dp"

        RelativeLayout:
            size_hint_y: 0.8

            # Einzelne Gewinner-Bubble in der Mitte
            BoxLayout:
                orientation: "vertical"
                size_hint: 0.6, 0.5
                pos_hint: {"center_x": 0.5, "center_y": 0.55}
                padding: dp(8)
                spacing: dp(4)
                canvas.before:
                    Color:
                        rgba: 0, 0, 0, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(24), dp(24), dp(24), dp(24)]
                canvas.after:
                    Color:
                        rgba: 1, 1, 1, 1
                    Line:
                        width: 1.2
                        rounded_rectangle: (self.x, self.y, self.width, self.height, dp(24), dp(24), dp(24), dp(24))

                # Drei Zeilen je nach Gewinner-Index
                Label:
                    text: (root.all_words[0] if len(root.all_words) > 0 else "") if root.winning_index == 0 else \
                          (root.all_words[3] if len(root.all_words) > 3 else "") if root.winning_index == 1 else \
                          (root.all_words[6] if len(root.all_words) > 6 else "") if root.winning_index == 2 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                Label:
                    text: (root.all_words[1] if len(root.all_words) > 1 else "") if root.winning_index == 0 else \
                          (root.all_words[4] if len(root.all_words) > 4 else "") if root.winning_index == 1 else \
                          (root.all_words[7] if len(root.all_words) > 7 else "") if root.winning_index == 2 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                Label:
                    text: (root.all_words[2] if len(root.all_words) > 2 else "") if root.winning_index == 0 else \
                          (root.all_words[5] if len(root.all_words) > 5 else "") if root.winning_index == 1 else \
                          (root.all_words[8] if len(root.all_words) > 8 else "") if root.winning_index == 2 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size

        BoxLayout:
            size_hint_y: None
            height: dp(60)
            padding: [0, dp(10), 0, dp(10)]
            spacing: dp(10)
            orientation: "vertical"

            Button:
                text: "Back to Menu"
                size_hint: 0.4, 1
                pos_hint: {"center_x": 0.5}
                background_normal: ""
                background_color: 0.4, 0.4, 0.4, 1
                on_release: app.switch_to_menu()


<VetoScreen>:
    name: "veto"
    BoxLayout:
        orientation: "vertical"
        padding: "0dp"
        spacing: "10dp"

        Label:
            text: "Choose what you don't want to cook - Player " + str(root.current_player_index + 1)
            font_size: "24sp"
            size_hint_y: None
            height: "40dp"

        RelativeLayout:
            size_hint_y: 0.9

            # Obere Bubble (Runde 1)
            BoxLayout:
                orientation: "vertical"
                size_hint: 0.4, 0.35
                pos_hint: {"center_x": 0.5, "center_y": 0.75}
                padding: dp(8)
                spacing: dp(4)
                canvas.before:
                    Color:
                        rgba: 0, 0, 0, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(24), dp(24), dp(24), dp(24)]
                canvas.after:
                    Color:
                        rgba: 1, 1, 1, 1
                    Line:
                        width: 1.2
                        rounded_rectangle: (self.x, self.y, self.width, self.height, dp(24), dp(24), dp(24), dp(24))

                Label:
                    text: root.all_words[0] if len(root.all_words) > 0 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (1, 0.4, 0.4, 1) if root.selected_index == 0 else (1, 1, 1, 1)
                Label:
                    text: root.all_words[1] if len(root.all_words) > 1 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (1, 0.4, 0.4, 1) if root.selected_index == 0 else (1, 1, 1, 1)
                Label:
                    text: root.all_words[2] if len(root.all_words) > 2 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (1, 0.4, 0.4, 1) if root.selected_index == 0 else (1, 1, 1, 1)

            Button:
                background_normal: ""
                background_down: ""
                background_color: 0, 0, 0, 0
                size_hint: 0.4, 0.35
                pos_hint: {"center_x": 0.5, "center_y": 0.75}
                on_release: root.select_bubble(0)

            # Rechte Bubble (Runde 2)
            BoxLayout:
                orientation: "vertical"
                size_hint: 0.4, 0.35
                pos_hint: {"center_x": 0.78, "center_y": 0.35}
                padding: dp(8)
                spacing: dp(4)
                canvas.before:
                    Color:
                        rgba: 0, 0, 0, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(24), dp(24), dp(24), dp(24)]
                canvas.after:
                    Color:
                        rgba: 1, 1, 1, 1
                    Line:
                        width: 1.2
                        rounded_rectangle: (self.x, self.y, self.width, self.height, dp(24), dp(24), dp(24), dp(24))

                Label:
                    text: root.all_words[3] if len(root.all_words) > 3 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (1, 0.4, 0.4, 1) if root.selected_index == 1 else (1, 1, 1, 1)
                Label:
                    text: root.all_words[4] if len(root.all_words) > 4 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (1, 0.4, 0.4, 1) if root.selected_index == 1 else (1, 1, 1, 1)
                Label:
                    text: root.all_words[5] if len(root.all_words) > 5 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (1, 0.4, 0.4, 1) if root.selected_index == 1 else (1, 1, 1, 1)

            Button:
                background_normal: ""
                background_down: ""
                background_color: 0, 0, 0, 0
                size_hint: 0.4, 0.35
                pos_hint: {"center_x": 0.78, "center_y": 0.35}
                on_release: root.select_bubble(1)

            # Linke Bubble (Runde 3)
            BoxLayout:
                orientation: "vertical"
                size_hint: 0.4, 0.35
                pos_hint: {"center_x": 0.22, "center_y": 0.35}
                padding: dp(8)
                spacing: dp(4)
                canvas.before:
                    Color:
                        rgba: 0, 0, 0, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(24), dp(24), dp(24), dp(24)]
                canvas.after:
                    Color:
                        rgba: 1, 1, 1, 1
                    Line:
                        width: 1.2
                        rounded_rectangle: (self.x, self.y, self.width, self.height, dp(24), dp(24), dp(24), dp(24))

                Label:
                    text: root.all_words[6] if len(root.all_words) > 6 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (1, 0.4, 0.4, 1) if root.selected_index == 2 else (1, 1, 1, 1)
                Label:
                    text: root.all_words[7] if len(root.all_words) > 7 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (1, 0.4, 0.4, 1) if root.selected_index == 2 else (1, 1, 1, 1)
                Label:
                    text: root.all_words[8] if len(root.all_words) > 8 else ""
                    halign: "center"
                    valign: "middle"
                    text_size: self.size
                    color: (1, 0.4, 0.4, 1) if root.selected_index == 2 else (1, 1, 1, 1)

            Button:
                background_normal: ""
                background_down: ""
                background_color: 0, 0, 0, 0
                size_hint: 0.4, 0.35
                pos_hint: {"center_x": 0.22, "center_y": 0.35}
                on_release: root.select_bubble(2)

            # Veto / Verwerfen am unteren Rand
            BoxLayout:
                size_hint: None, None
                size: dp(260), dp(60)
                pos_hint: {"center_x": 0.5}
                y: dp(20)
                spacing: dp(12)
                opacity: 1 if root.selected_index != -1 else 0

                Button:
                    text: "VETO"
                    font_size: "18sp"
                    size_hint_x: 0.6
                    background_normal: ""
                    background_color: 0.8, 0.3, 0.3, 1
                    on_release: root.confirm_veto()

                Button:
                    text: "Back"
                    font_size: "20sp"
                    size_hint_x: 0.4
                    background_normal: ""
                    color: 1, 0.3, 0.3, 1
                    on_release: root.cancel_selection()

        # Immer sichtbarer Continue-Button unterhalb der Bubbles
        BoxLayout:
            size_hint_y: None
            height: dp(60)
            padding: [0, dp(10), 0, dp(10)]
            spacing: dp(10)
            orientation: "vertical"

            Button:
                text: "Continue"
                size_hint: 0.4, 1
                pos_hint: {"center_x": 0.5}
                background_normal: ""
                background_color: 0.4, 0.4, 0.4, 1
                on_release: app.advance_veto()


<InstructionsScreen>:
    name: "instructions"
    BoxLayout:
        orientation: "vertical"
        padding: "1dp"
        spacing: "1dp"
        
        ScrollView:
            size_hint_y: 0.97
            
            Image:
                source: "../Instructions.png"
                allow_stretch: True
                keep_ratio: True
                size_hint_y: None
                height: self.texture_size[1] * 0.6  # Even smaller to show only core content
                mipmap: True
            
        Button:
            text: "Back to Menu"
            size_hint_y: None
            height: "30dp"
            on_release: app.switch_to_menu()


"""


class CardsAgainstTheChefApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.player_count = 1
        self.menu_music = None

    def build(self):
        self.title = "Cards Against the Chef"
        return Builder.load_string(KV)
    
    def on_start(self):
        """Load and start menu music when app starts."""
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self.load_menu_music(), 0.5)
        Clock.schedule_once(lambda dt: self.play_menu_music(), 1.0)
    
    def load_menu_music(self):
        """Load the Gyros im Rösti music."""
        music_path = "../Gyros_im_Rosti.mp3"
        try:
            self.menu_music = SoundLoader.load(music_path)
            if self.menu_music:
                self.menu_music.loop = True
                self.menu_music.volume = 0.3  # 30% volume
                print("Menu music loaded successfully")
            else:
                print("Could not load menu music")
        except Exception as e:
            print(f"Error loading menu music: {e}")
    
    def play_menu_music(self):
        """Play the menu music."""
        if self.menu_music:
            self.menu_music.play()
    
    def stop_menu_music(self):
        """Stop the menu music."""
        if self.menu_music:
            self.menu_music.stop()

    def set_players_and_start(self, count):
        self.player_count = count
        self.switch_to_game()

    def show_instructions(self):
        """Show the instructions screen."""
        self.root.current = "instructions"

    def switch_to_game(self):
        """Switch to game screen and stop menu music."""
        self.stop_menu_music()
        self.root.current = "game"

    def switch_to_menu(self):
        # Game-Session zurücksetzen, damit ein neuer Start wirklich frisch beginnt
        sm = self.root
        if sm.has_screen("game"):
            game = sm.get_screen("game")
            game.session_initialized = False
            game.current_index = 0
            game.current_card_source = ""
            game.current_round_choices = []
            game.selected_index = -1
            game.player_turn_text = ""
            game.player_color = [1, 1, 1, 1]
        sm.current = "menu"

    def show_summary(self, round_number, words):
        """SummaryScreen mit den gewählten Wörtern für diese Runde anzeigen."""
        sm = self.root
        summary = sm.get_screen("summary")
        summary.round_number = round_number
        summary.summary_words = list(words)
        sm.current = "summary"

    def show_final_summary(self, all_words):
        """FinalSummaryScreen nach Runde 3 mit allen gewählten Begriffen anzeigen."""
        sm = self.root
        final = sm.get_screen("final_summary")
        final.all_words = list(all_words)
        final.current_player_index = 0
        final.selected_index = -1
        sm.current = "final_summary"

    def show_result(self, all_words, winning_index):
        """ResultScreen mit der Gewinner-Bubble anzeigen."""
        sm = self.root
        result = sm.get_screen("result")
        result.all_words = list(all_words)
        result.winning_index = winning_index
        sm.current = "result"

    def show_veto(self, all_words):
        """VetoScreen anzeigen, wenn es keinen Mehrheits-Gewinner gibt."""
        sm = self.root
        veto = sm.get_screen("veto")
        veto.all_words = list(all_words)
        veto.current_player_index = 0
        veto.selected_index = -1
        veto.vetoes = [-1, -1, -1]
        sm.current = "veto"

    def start_next_round_from_summary(self):
        """Vom SummaryScreen zurück ins Spiel und nächste Runde starten."""
        sm = self.root
        game = sm.get_screen("game")

        # Nächste Runde vorbereiten
        game.round_number += 1
        game._build_round_card_sources()
        if not game.card_sources:
            self.switch_to_menu()
            return
        game.current_index = 0
        game.current_card_source = game.card_sources[0]
        if "backpic" in game.current_card_source:
            game._update_last_back_type_from_source(game.current_card_source)

        sm.current = "game"

    def advance_final_summary(self):
        """FinalSummaryScreen: durch die drei Spieler blättern, danach ins Menü."""
        sm = self.root
        final = sm.get_screen("final_summary")
        # aktuelle Auswahl zurücksetzen, bevor wir weiter schalten
        final.selected_index = -1

        # Noch nicht alle Spieler gewählt -> zum nächsten Spieler wechseln
        if final.current_player_index < 2:
            final.current_player_index += 1
            return

        # Alle drei Spieler haben gewählt -> Stimmen auszählen
        votes = {0: 0, 1: 0, 2: 0}
        for sel in final.selections:
            if sel in votes:
                votes[sel] += 1

        # Gewinner mit mindestens 2 Stimmen suchen
        winning_index = -1
        for idx, count in votes.items():
            if count >= 2:
                winning_index = idx
                break

        if winning_index != -1:
            # Gewinner-Bubble anzeigen
            self.show_result(final.all_words, winning_index)
        else:
            # Kein Mehrheits-Gewinner -> Veto-Runde starten
            self.show_veto(final.all_words)

    def advance_veto(self):
        """VetoScreen: durch die drei Spieler blättern, danach Ergebnis aus Votes - Vetos bestimmen."""
        sm = self.root
        veto = sm.get_screen("veto")

        # aktuelle Auswahl zurücksetzen
        veto.selected_index = -1

        if veto.current_player_index < 2:
            veto.current_player_index += 1
            return

        # Nach dem dritten Spieler: Votes und Vetos kombinieren und Gewinner bestimmen
        final = sm.get_screen("final_summary")

        votes = {0: 0, 1: 0, 2: 0}
        for sel in getattr(final, "selections", []):
            if sel in votes:
                votes[sel] += 1

        veto_counts = {0: 0, 1: 0, 2: 0}
        for v in veto.vetoes:
            if v in veto_counts:
                veto_counts[v] += 1

        # Score aus Stimmen minus Vetos berechnen
        best_index = 0
        best_score = votes[0] - veto_counts[0]
        for idx in (1, 2):
            score = votes[idx] - veto_counts[idx]
            if score > best_score:
                best_score = score
                best_index = idx

        # Gewinner mit bestem Score im ResultScreen anzeigen
        self.show_result(veto.all_words, best_index)


if __name__ == "__main__":
    CardsAgainstTheChefApp().run()
