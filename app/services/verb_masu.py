"""ます形 from 原形 using 一类/二类/三类 (verb_type 1/2/3)."""


def masu_form(lemma: str, verb_type: int) -> str:
    if verb_type == 3:
        if lemma == "来る" or lemma == "くる":
            return "きます"
        if lemma == "する":
            return "します"
        if lemma.endswith("する"):
            return lemma[: -len("する")] + "します"
        raise ValueError(f"Unsupported type-3 verb: {lemma}")
    if verb_type == 2:
        if not lemma.endswith("る"):
            raise ValueError(f"Type-2 verb should end with る: {lemma}")
        return lemma[:-1] + "ます"
    if verb_type == 1:
        if lemma in ("行く", "いく"):
            return "いきます"
        if len(lemma) < 2:
            raise ValueError(f"Lemma too short: {lemma}")
        stem, last = lemma[:-1], lemma[-1]
        mp = {
            "う": "い",
            "く": "き",
            "ぐ": "ぎ",
            "す": "し",
            "つ": "ち",
            "ぬ": "に",
            "ぶ": "び",
            "む": "み",
            "る": "り",
        }
        if last not in mp:
            raise ValueError(f"Unknown type-1 ending for: {lemma}")
        return stem + mp[last] + "ます"
    raise ValueError(f"verb_type must be 1, 2, or 3, got {verb_type}")
