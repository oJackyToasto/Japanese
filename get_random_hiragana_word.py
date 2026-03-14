"""
Hiragana word flip card application.
Uses Japanese-Chinese thesaurus dataset. Download on first run if not present.
Front: hiragana | Back: romaji + Chinese meaning
"""

import json
import os
import random
import re
import sys
import tkinter as tk
from tkinter import font as tkfont
from pathlib import Path
from urllib.request import urlretrieve

DATASET_URL = "https://github.com/lxl66566/Japanese-Chinese-thesaurus/releases/download/v1.1/final.json"
SCRIPT_DIR = Path(__file__).parent.resolve()
DATASET_PATH = SCRIPT_DIR / "japanese_chinese_words.json"

# Hiragana/Katakana to Romaji mapping (longest first for correct substitution)
_KANA_ROMAJI = [
    ("きゃ", "kya"), ("きゅ", "kyu"), ("きょ", "kyo"),
    ("しゃ", "sha"), ("しゅ", "shu"), ("しょ", "sho"),
    ("ちゃ", "cha"), ("ちゅ", "chu"), ("ちょ", "cho"),
    ("にゃ", "nya"), ("にゅ", "nyu"), ("にょ", "nyo"),
    ("ひゃ", "hya"), ("ひゅ", "hyu"), ("ひょ", "hyo"),
    ("みゃ", "mya"), ("みゅ", "myu"), ("みょ", "myo"),
    ("りゃ", "rya"), ("りゅ", "ryu"), ("りょ", "ryo"),
    ("ぎゃ", "gya"), ("ぎゅ", "gyu"), ("ぎょ", "gyo"),
    ("じゃ", "ja"), ("じゅ", "ju"), ("じょ", "jo"),
    ("びゃ", "bya"), ("びゅ", "byu"), ("びょ", "byo"),
    ("ぴゃ", "pya"), ("ぴゅ", "pyu"), ("ぴょ", "pyo"),
    ("あ", "a"), ("い", "i"), ("う", "u"), ("え", "e"), ("お", "o"),
    ("か", "ka"), ("き", "ki"), ("く", "ku"), ("け", "ke"), ("こ", "ko"),
    ("さ", "sa"), ("し", "shi"), ("す", "su"), ("せ", "se"), ("そ", "so"),
    ("た", "ta"), ("ち", "chi"), ("つ", "tsu"), ("て", "te"), ("と", "to"),
    ("な", "na"), ("に", "ni"), ("ぬ", "nu"), ("ね", "ne"), ("の", "no"),
    ("は", "ha"), ("ひ", "hi"), ("ふ", "fu"), ("へ", "he"), ("ほ", "ho"),
    ("ま", "ma"), ("み", "mi"), ("む", "mu"), ("め", "me"), ("も", "mo"),
    ("や", "ya"), ("ゆ", "yu"), ("よ", "yo"),
    ("ら", "ra"), ("り", "ri"), ("る", "ru"), ("れ", "re"), ("ろ", "ro"),
    ("わ", "wa"), ("を", "wo"), ("ん", "n"),
    ("が", "ga"), ("ぎ", "gi"), ("ぐ", "gu"), ("げ", "ge"), ("ご", "go"),
    ("ざ", "za"), ("じ", "ji"), ("ず", "zu"), ("ぜ", "ze"), ("ぞ", "zo"),
    ("だ", "da"), ("ぢ", "ji"), ("づ", "zu"), ("で", "de"), ("ど", "do"),
    ("ば", "ba"), ("び", "bi"), ("ぶ", "bu"), ("べ", "be"), ("ぼ", "bo"),
    ("ぱ", "pa"), ("ぴ", "pi"), ("ぷ", "pu"), ("ぺ", "pe"), ("ぽ", "po"),
    ("っ", ""), ("ー", "-"), ("　", " "),
]
def _katakana_to_hiragana(c: str) -> str:
    """Convert single katakana char to hiragana. Offset 0x60."""
    o = ord(c)
    if 0x30A0 <= o <= 0x30FF:  # katakana
        return chr(o - 0x60)
    return c


def _kana_to_romaji(text: str) -> str:
    """Convert hiragana/katakana to romaji."""
    t = "".join(_katakana_to_hiragana(c) for c in text)
    for kana, roma in sorted(_KANA_ROMAJI, key=lambda x: -len(x[0])):
        t = t.replace(kana, roma)
    return t


def _has_hiragana(s: str) -> bool:
    return bool(re.search(r"[\u3040-\u309f]", s))


def _extract_kana_and_chinese(key: str, value: str) -> tuple[str | None, str]:
    """Extract (hiragana_display, chinese_meaning)."""
    value = str(value).strip()
    chinese = value

    # Try (kana) or （kana） at start - supports fullwidth （） and ASCII ()
    m = re.match(r"[（(]([^)）]+)[）)]\s*(.*)", value)
    if m:
        kana_part, rest = m.group(1).strip(), m.group(2).strip()
        if _has_hiragana(kana_part) or re.search(r"[\u30a0-\u30ff]", kana_part):
            kana = "".join(_katakana_to_hiragana(c) for c in kana_part)
            chinese = re.sub(r"^[a-zA-Z\s\d\[\]【】]+", "", rest).strip() or rest
            return kana, chinese
        chinese = rest

    # Key might be hiragana - e.g. ありがとう
    if _has_hiragana(key):
        chinese = re.sub(r"^[a-zA-Z\s\d\[\]【】\(\)]+", "", value).strip() or value
        return key, chinese

    # Try first token as kana if it looks like kana - e.g. "かんしゃ 感谢"
    parts = value.split()
    if parts and (_has_hiragana(parts[0]) or re.search(r"[\u30a0-\u30ff]", parts[0])):
        kana = "".join(_katakana_to_hiragana(c) for c in parts[0])
        chinese = " ".join(parts[1:]) if len(parts) > 1 else value
        chinese = re.sub(r"^[a-zA-Z\s\d\[\]【】]+", "", chinese).strip() or chinese
        return kana, chinese

    chinese = re.sub(r"^[a-zA-Z\s\d\[\]\(\)【】]+", "", value).strip() or value
    return None, chinese


def _download_dataset() -> bool:
    """Download dataset to local file. Returns True on success."""
    try:
        urlretrieve(DATASET_URL, DATASET_PATH)
        return True
    except Exception:
        return False


def _load_words() -> list[tuple[str, str, str, str]]:
    """Load (full_word, hiragana, romaji, chinese) entries. Download dataset if needed."""
    if not DATASET_PATH.exists():
        print("Downloading Japanese-Chinese vocabulary dataset...")
        if not _download_dataset():
            print("Download failed. Please download manually from:")
            print(DATASET_URL)
            print(f"Save as: {DATASET_PATH}")
            sys.exit(1)

    with open(DATASET_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    entries = []
    for key, value in raw.items():
        kana, chinese = _extract_kana_and_chinese(key, value)
        if kana and chinese and len(kana) <= 20:
            romaji = _kana_to_romaji(kana)
            if romaji:
                full_word = key  # kanji/hiragana as in JSON key
                entries.append((full_word, kana, romaji, chinese))

    if not entries:
        print("No suitable entries found in dataset.")
        sys.exit(1)
    return entries


def get_random_word(words: list[tuple[str, str, str, str]]) -> tuple[str, str, str, str]:
    """Return random (full_word, hiragana, romaji, chinese) tuple."""
    return random.choice(words)


def _parse_args() -> bool:
    """Parse --full / --hira. Returns True to show full word, False for hiragana (default)."""
    args = [a for a in sys.argv[1:] if a.startswith("--")]
    if "--full" in args:
        return True
    return False  # --hira or default


class FlipCardApp(tk.Tk):
    def __init__(self, words: list[tuple[str, str, str, str]], show_full_word: bool = False):
        super().__init__()
        self._words = words
        self._show_full_word = show_full_word
        self.title("単語 — Full Word" if show_full_word else "単語 — Hiragana Word Cards")
        self.geometry("500x380")
        self.resizable(True, True)
        self._showing_front = True
        self._current_full = ""
        self._current_hiragana = ""
        self._current_romaji = ""
        self._current_chinese = ""

        self.update_idletasks()
        w, h = 500, 380
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._build_ui()
        self._new_card()
        self._bind_keys()

    def _build_ui(self):
        self.configure(bg="#2d2a2e")
        main_frame = tk.Frame(self, padx=24, pady=24, bg="#2d2a2e")
        main_frame.pack(fill=tk.BOTH, expand=True)

        shadow_frame = tk.Frame(main_frame, bg="#1a181b", padx=4, pady=4)
        shadow_frame.pack(fill=tk.BOTH, expand=True)

        border_frame = tk.Frame(shadow_frame, bg="#3d3a40", padx=1, pady=1)
        border_frame.pack(fill=tk.BOTH, expand=True)

        self.card_frame = tk.Frame(border_frame, bg="#faf8f5")
        self.card_frame.pack(fill=tk.BOTH, expand=True)
        self.card_frame.bind("<Button-1>", lambda e: self._flip())
        self.card_frame.focus_set()

        self.label = tk.Label(
            self.card_frame,
            text="",
            font=tkfont.Font(family="MS Gothic", size=32, weight="normal"),
            bg="#faf8f5",
            fg="#2d2a2e",
            wraplength=420,
            justify=tk.CENTER,
        )
        self.label.pack(expand=True, fill=tk.BOTH, padx=24, pady=32)
        self.label.bind("<Button-1>", lambda e: self._flip())
        self.card_frame.bind("<Configure>", lambda e: self.card_frame.focus_set())

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
            front_text = self._current_full if self._show_full_word else self._current_hiragana
            self.label.config(text=front_text, font=tkfont.Font(family="MS Gothic", size=32, weight="normal"), fg="#2d2a2e")
        else:
            back_text = f"{self._current_romaji}\n\n{self._current_chinese}"
            self.label.config(text=back_text, font=tkfont.Font(family="Segoe UI", size=16, weight="normal"), fg="#5c5a5e")

    def _new_card(self):
        self._current_full, self._current_hiragana, self._current_romaji, self._current_chinese = get_random_word(self._words)
        self._showing_front = True
        self._update_display()


if __name__ == "__main__":
    show_full = _parse_args()
    words = _load_words()
    print(f"Loaded {len(words)} vocabulary entries.")
    print("Mode: full word" if show_full else "Mode: hiragana (default)")
    app = FlipCardApp(words, show_full_word=show_full)
    app.mainloop()
