"""
五十音图 (Gojūon) flip card application.
Displays random Japanese syllabary characters; flip to reveal romaji.
"""

import argparse
import random
import tkinter as tk
from tkinter import font as tkfont

# 五十音図: (hiragana, katakana, romaji) - 46 basic characters
GOJUON = [
    # Vowels
    ("あ", "ア", "a"), ("い", "イ", "i"), ("う", "ウ", "u"), ("え", "エ", "e"), ("お", "オ", "o"),
    # K-row
    ("か", "カ", "ka"), ("き", "キ", "ki"), ("く", "ク", "ku"), ("け", "ケ", "ke"), ("こ", "コ", "ko"),
    # S-row
    ("さ", "サ", "sa"), ("し", "シ", "shi"), ("す", "ス", "su"), ("せ", "セ", "se"), ("そ", "ソ", "so"),
    # T-row
    ("た", "タ", "ta"), ("ち", "チ", "chi"), ("つ", "ツ", "tsu"), ("て", "テ", "te"), ("と", "ト", "to"),
    # N-row
    ("な", "ナ", "na"), ("に", "ニ", "ni"), ("ぬ", "ヌ", "nu"), ("ね", "ネ", "ne"), ("の", "ノ", "no"),
    # H-row
    ("は", "ハ", "ha"), ("ひ", "ヒ", "hi"), ("ふ", "フ", "fu"), ("へ", "ヘ", "he"), ("ほ", "ホ", "ho"),
    # M-row
    ("ま", "マ", "ma"), ("み", "ミ", "mi"), ("む", "ム", "mu"), ("め", "メ", "me"), ("も", "モ", "mo"),
    # Y-row
    ("や", "ヤ", "ya"), ("ゆ", "ユ", "yu"), ("よ", "ヨ", "yo"),
    # R-row
    ("ら", "ラ", "ra"), ("り", "リ", "ri"), ("る", "ル", "ru"), ("れ", "レ", "re"), ("ろ", "ロ", "ro"),
    # W-row
    ("わ", "ワ", "wa"), ("を", "ヲ", "wo"),
    # N
    ("ん", "ン", "n"),
]

# 浊音 (dakuten / voiced)
DAKUON = [
    ("が", "ガ", "ga"), ("ぎ", "ギ", "gi"), ("ぐ", "グ", "gu"), ("げ", "ゲ", "ge"), ("ご", "ゴ", "go"),
    ("ざ", "ザ", "za"), ("じ", "ジ", "ji"), ("ず", "ズ", "zu"), ("ぜ", "ゼ", "ze"), ("ぞ", "ゾ", "zo"),
    ("だ", "ダ", "da"), ("ぢ", "ヂ", "ji"), ("づ", "ヅ", "zu"), ("で", "デ", "de"), ("ど", "ド", "do"),
    ("ば", "バ", "ba"), ("び", "ビ", "bi"), ("ぶ", "ブ", "bu"), ("べ", "ベ", "be"), ("ぼ", "ボ", "bo"),
]

# 半浊音 (handakuten / half-voiced)
HANDAKUON = [
    ("ぱ", "パ", "pa"), ("ぴ", "ピ", "pi"), ("ぷ", "プ", "pu"), ("ぺ", "ペ", "pe"), ("ぽ", "ポ", "po"),
]

# 拗音 (yōon / contracted)
YOON = [
    ("きゃ", "キャ", "kya"), ("きゅ", "キュ", "kyu"), ("きょ", "キョ", "kyo"),
    ("しゃ", "シャ", "sha"), ("しゅ", "シュ", "shu"), ("しょ", "ショ", "sho"),
    ("ちゃ", "チャ", "cha"), ("ちゅ", "チュ", "chu"), ("ちょ", "チョ", "cho"),
    ("にゃ", "ニャ", "nya"), ("にゅ", "ニュ", "nyu"), ("にょ", "ニョ", "nyo"),
    ("ひゃ", "ヒャ", "hya"), ("ひゅ", "ヒュ", "hyu"), ("ひょ", "ヒョ", "hyo"),
    ("みゃ", "ミャ", "mya"), ("みゅ", "ミュ", "myu"), ("みょ", "ミョ", "myo"),
    ("りゃ", "リャ", "rya"), ("りゅ", "リュ", "ryu"), ("りょ", "リョ", "ryo"),
    ("ぎゃ", "ギャ", "gya"), ("ぎゅ", "ギュ", "gyu"), ("ぎょ", "ギョ", "gyo"),
    ("じゃ", "ジャ", "ja"), ("じゅ", "ジュ", "ju"), ("じょ", "ジョ", "jo"),
    ("びゃ", "ビャ", "bya"), ("びゅ", "ビュ", "byu"), ("びょ", "ビョ", "byo"),
    ("ぴゃ", "ピャ", "pya"), ("ぴゅ", "ピュ", "pyu"), ("ぴょ", "ピョ", "pyo"),
]


def get_random_character(mode="hiro", include_voiced=True, include_yoon=True):
    """Returns a random (kana_display, romaji) tuple.
    mode: "hiro" (hiragana), "kata" (katakana), or "all" (random choice).
    include_voiced: include 浊音 and 半浊音 (default True).
    include_yoon: include 拗音 (default True).
    """
    pool = GOJUON
    if include_voiced:
        pool = pool + DAKUON + HANDAKUON
    if include_yoon:
        pool = pool + YOON
    entry = random.choice(pool)
    hiragana, katakana, romaji = entry
    if mode == "hiro":
        kana_display = hiragana
    elif mode == "kata":
        kana_display = katakana
    else:  # all
        kana_display = random.choice([hiragana, katakana])
    return kana_display, romaji


class FlipCardApp(tk.Tk):
    def __init__(self, mode="hiro", include_voiced=True, include_yoon=True):
        super().__init__()
        self._mode = mode
        self._include_voiced = include_voiced
        self._include_yoon = include_yoon
        self.title("五十音图 — Flip Cards")
        self.geometry("420x340")
        self.resizable(True, True)
        self._showing_front = True
        self._current_kana = ""
        self._current_romaji = ""

        # Center window
        self.update_idletasks()
        w, h = 420, 340
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._build_ui()
        self._new_card()
        self._bind_keys()

    def _build_ui(self):
        # Japanese-inspired palette: washi paper, indigo accent, warm charcoal
        self.configure(bg="#2d2a2e")
        main_frame = tk.Frame(self, padx=24, pady=24, bg="#2d2a2e")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Shadow layer (simulates card elevation)
        shadow_frame = tk.Frame(main_frame, bg="#1a181b", padx=4, pady=4)
        shadow_frame.pack(fill=tk.BOTH, expand=True)

        # Card border
        border_frame = tk.Frame(shadow_frame, bg="#3d3a40", padx=1, pady=1)
        border_frame.pack(fill=tk.BOTH, expand=True)

        # Card (cream paper look)
        self.card_frame = tk.Frame(border_frame, bg="#faf8f5")
        self.card_frame.pack(fill=tk.BOTH, expand=True)
        self.card_frame.bind("<Button-1>", lambda e: self._flip())
        self.card_frame.focus_set()

        self.label = tk.Label(
            self.card_frame,
            text="",
            font=tkfont.Font(family="MS Gothic", size=80, weight="normal"),
            bg="#faf8f5",
            fg="#2d2a2e",
        )
        self.label.pack(expand=True, fill=tk.BOTH, padx=32, pady=48)
        self.label.bind("<Button-1>", lambda e: self._flip())
        self.card_frame.bind("<Configure>", lambda e: self.card_frame.focus_set())

        # Instructions
        inst = tk.Label(
            main_frame,
            text="Click or Space to flip  ·  N for next card",
            font=tkfont.Font(family="Segoe UI", size=11),
            bg="#2d2a2e",
            fg="#8a8890",
        )
        inst.pack(pady=(16, 0))

    def _bind_keys(self):
        self.bind("<space>", lambda e: self._flip())
        self.bind("<Return>", lambda e: self._flip())
        self.bind("n", lambda e: self._new_card())
        self.bind("N", lambda e: self._new_card())

    def _flip(self):
        self._showing_front = not self._showing_front
        self._update_display()

    def _update_display(self):
        if self._showing_front:
            self.label.config(text=self._current_kana, fg="#2d2a2e", font=tkfont.Font(family="MS Gothic", size=80, weight="normal"))
        else:
            self.label.config(text=self._current_romaji, fg="#5c5a5e", font=tkfont.Font(family="Segoe UI", size=36, weight="normal"))

    def _new_card(self):
        self._current_kana, self._current_romaji = get_random_character(
            self._mode, include_voiced=self._include_voiced, include_yoon=self._include_yoon
        )
        self._showing_front = True
        self._update_display()


def _parse_args():
    p = argparse.ArgumentParser(description="五十音图 flip cards")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--hiro", action="store_true", help="Hiragana only (default)")
    g.add_argument("--kata", action="store_true", help="Katakana only")
    g.add_argument("--all", action="store_true", dest="all_mode", help="Both (random Hiragana or Katakana)")
    p.add_argument("--no-voiced", action="store_true", help="Exclude 浊音 and 半浊音 (default: include them)")
    p.add_argument("--no-yoon", action="store_true", help="Exclude 拗音 (default: include them)")
    args = p.parse_args()
    if args.kata:
        mode = "kata"
    elif args.all_mode:
        mode = "all"
    else:
        mode = "hiro"
    return mode, not args.no_voiced, not args.no_yoon


if __name__ == "__main__":
    mode, include_voiced, include_yoon = _parse_args()
    app = FlipCardApp(mode=mode, include_voiced=include_voiced, include_yoon=include_yoon)
    app.mainloop()
