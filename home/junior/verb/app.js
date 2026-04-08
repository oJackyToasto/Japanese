(function () {
  "use strict";

  const CLASS_IDS = ["intro", "class5"];
  const CLASS_BASE = "../../../classes/verbs";

  const classSelect = document.getElementById("class-select");
  const classTitleEl = document.getElementById("class-title");
  const includeDictionaryEl = document.getElementById("include-dictionary");
  const includeMasuEl = document.getElementById("include-masu");
  const cardEl = document.getElementById("card");
  const frontEl = document.getElementById("front");
  const backEl = document.getElementById("back");
  const nextBtn = document.getElementById("next-btn");

  let deck = [];
  let deckIndex = 0;
  let showingFront = true;
  let currentClassData = null;

  function toMasuForm(lemma, verbType) {
    if (!lemma) throw new Error("Empty lemma");
    if (verbType === 3) {
      if (lemma === "来る" || lemma === "くる") return "きます";
      if (lemma === "する") return "します";
      if (lemma.endsWith("する")) return lemma.slice(0, -2) + "します";
      throw new Error("Unsupported type-3 verb: " + lemma);
    }
    if (verbType === 2) {
      if (!lemma.endsWith("る")) throw new Error("Type-2 verb should end with る: " + lemma);
      return lemma.slice(0, -1) + "ます";
    }
    if (verbType === 1) {
      if (lemma === "行く" || lemma === "いく") return "いきます";
      if (lemma.length < 2) throw new Error("Lemma too short: " + lemma);
      const stem = lemma.slice(0, -1);
      const last = lemma.slice(-1);
      const mp = {
        "う": "い",
        "く": "き",
        "ぐ": "ぎ",
        "す": "し",
        "つ": "ち",
        "ぬ": "に",
        "ぶ": "び",
        "む": "み",
        "る": "り",
      };
      if (!mp[last]) throw new Error("Unknown type-1 ending for: " + lemma);
      return stem + mp[last] + "ます";
    }
    throw new Error("verb_type must be 1, 2, or 3");
  }

  function shuffleArray(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function buildDeck(verbs, opts) {
    const includeDictionary = !!opts.includeDictionary;
    const includeMasu = !!opts.includeMasu;
    const cards = [];

    for (const v of verbs) {
      const lemma = v.lemma || "";
      const reading = v.reading || "";
      const meaning = v.meaning || "";
      const verbType = Number(v.verb_type);
      if (!lemma || !verbType) continue;

      let masu = "";
      let readingMasu = "";
      try {
        masu = toMasuForm(lemma, verbType);
        readingMasu = reading ? toMasuForm(reading, verbType) : "";
      } catch (_err) {
        masu = "";
        readingMasu = "";
      }

      if (includeDictionary && masu) {
        cards.push({
          frontMain: lemma,
          frontSub: reading || "",
          backMain: masu,
          backSub: readingMasu || "",
          backMeaning: meaning,
          backType: "dict -> masu",
        });
      }
      if (includeMasu && masu) {
        cards.push({
          frontMain: masu,
          frontSub: readingMasu || "",
          backMain: lemma,
          backSub: reading || "",
          backMeaning: meaning,
          backType: "masu -> dict",
        });
      }
    }

    return shuffleArray(cards);
  }

  function setCardContent(card) {
    frontEl.innerHTML = "";
    backEl.innerHTML = "";

    const fMain = document.createElement("div");
    fMain.className = "main-text";
    fMain.textContent = card.frontMain;
    frontEl.appendChild(fMain);
    if (card.frontSub) {
      const fSub = document.createElement("div");
      fSub.className = "sub-text";
      fSub.textContent = card.frontSub;
      frontEl.appendChild(fSub);
    }

    const bMain = document.createElement("div");
    bMain.className = "main-text";
    bMain.textContent = card.backMain;
    backEl.appendChild(bMain);

    if (card.backSub) {
      const bSub = document.createElement("div");
      bSub.className = "sub-text";
      bSub.textContent = card.backSub;
      backEl.appendChild(bSub);
    }

    if (card.backMeaning) {
      const bMeaning = document.createElement("div");
      bMeaning.className = "meaning-text";
      bMeaning.textContent = card.backMeaning;
      backEl.appendChild(bMeaning);
    }

    const bType = document.createElement("div");
    bType.className = "pitch";
    bType.textContent = card.backType;
    backEl.appendChild(bType);
  }

  function updateDisplay() {
    cardEl.classList.toggle("flipped", !showingFront);
    if (deck.length) setCardContent(deck[deckIndex]);
  }

  function rebuildDeck() {
    if (!currentClassData) return;
    deck = buildDeck(currentClassData.verbs || [], {
      includeDictionary: includeDictionaryEl.checked,
      includeMasu: includeMasuEl.checked,
    });
    deckIndex = 0;
    showingFront = true;
    cardEl.classList.remove("flipped");
    nextBtn.disabled = deck.length === 0;
    if (deck.length) {
      updateDisplay();
    } else {
      frontEl.innerHTML = '<div class="loading">No cards with current checkbox options.</div>';
      backEl.innerHTML = "";
    }
  }

  function loadClass(classId) {
    const url = CLASS_BASE + "/" + classId + ".json";
    cardEl.classList.remove("flipped");
    frontEl.innerHTML = '<div class="loading">Loading...</div>';
    backEl.innerHTML = "";
    fetch(url)
      .then(function (res) {
        if (!res.ok) throw new Error("Failed to load " + classId);
        return res.json();
      })
      .then(function (data) {
        currentClassData = data;
        classTitleEl.textContent = data.title || classId;
        rebuildDeck();
      })
      .catch(function () {
        frontEl.innerHTML = '<div class="error">Could not load verb class JSON.</div>';
        backEl.innerHTML = "";
        deck = [];
        nextBtn.disabled = true;
      });
  }

  function populateClassSelect() {
    classSelect.innerHTML = "";
    CLASS_IDS.forEach(function (id) {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = id === "intro" ? "Intro" : "Class " + id.replace("class", "");
      classSelect.appendChild(opt);
    });
  }

  function flip() {
    if (!deck.length) return;
    showingFront = !showingFront;
    cardEl.classList.toggle("flipped", !showingFront);
  }

  function nextCard() {
    if (!deck.length) return;
    deckIndex = (deckIndex + 1) % deck.length;
    showingFront = true;
    cardEl.classList.remove("flipped");
    updateDisplay();
  }

  populateClassSelect();
  loadClass(classSelect.value);

  classSelect.addEventListener("change", function () { loadClass(classSelect.value); });
  includeDictionaryEl.addEventListener("change", rebuildDeck);
  includeMasuEl.addEventListener("change", rebuildDeck);
  cardEl.addEventListener("click", flip);
  nextBtn.addEventListener("click", nextCard);
  document.addEventListener("keydown", function (e) {
    if (e.code === "Space" || e.code === "Enter") {
      e.preventDefault();
      flip();
    } else if (e.key === "n" || e.key === "N") {
      nextCard();
    }
  });
})();
