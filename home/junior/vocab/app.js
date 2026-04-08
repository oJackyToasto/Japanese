(function () {
  "use strict";

  const CLASS_IDS = ["class1", "class2", "class3", "class4", "class5", "quantity"];
  const PITCH_SYMBOLS = "⓪①②③④⑤";
  const CLASS_BASE = "../../../classes/vocabs";

  const classSelect = document.getElementById("class-select");
  const classTitleEl = document.getElementById("class-title");
  const cardEl = document.getElementById("card");
  const frontEl = document.getElementById("front");
  const backEl = document.getElementById("back");
  const nextBtn = document.getElementById("next-btn");
  const wordOnlyCheckbox = document.getElementById("word-only");

  let deck = [];
  let deckIndex = 0;
  let showingFront = true;
  let currentClassData = null;

  function pitchStr(pitch) {
    if (pitch == null || pitch < 0 || pitch > 5) return "";
    return PITCH_SYMBOLS[pitch];
  }

  function shuffleArray(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function buildDeck(words, opts) {
    opts = opts || {};
    const wordOnly = !!opts.wordOnly;
    const cards = [];
    for (const w of words) {
      const word = w.word || "";
      const spelling = w.spelling || "";
      const meaning = w.meaning || "";
      const pitchChar = pitchStr(w.pitch);

      if (word && spelling) {
        cards.push({
          frontMain: word,
          frontPitch: pitchChar,
          backMain: spelling,
          backSub: null,
          backMeaning: meaning,
          backPitch: pitchChar,
        });
        if (!wordOnly) {
          cards.push({
            frontMain: spelling,
            frontPitch: pitchChar,
            backMain: word,
            backSub: null,
            backMeaning: meaning,
            backPitch: pitchChar,
          });
        }
      } else {
        cards.push({
          frontMain: word || spelling,
          frontPitch: pitchChar,
          backMain: "",
          backSub: null,
          backMeaning: meaning,
          backPitch: pitchChar,
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
    if (card.frontPitch) {
      const fPitch = document.createElement("div");
      fPitch.className = "pitch";
      fPitch.textContent = card.frontPitch;
      frontEl.appendChild(fPitch);
    }

    if (card.backMain) {
      const bMain = document.createElement("div");
      bMain.className = "main-text";
      bMain.textContent = card.backMain;
      backEl.appendChild(bMain);
    }
    if (card.backMeaning) {
      const bMeaning = document.createElement("div");
      bMeaning.className = "meaning-text";
      bMeaning.textContent = card.backMeaning;
      backEl.appendChild(bMeaning);
    }
    if (card.backPitch) {
      const bPitch = document.createElement("div");
      bPitch.className = "pitch";
      bPitch.textContent = card.backPitch;
      backEl.appendChild(bPitch);
    }
  }

  function updateDisplay() {
    cardEl.classList.toggle("flipped", !showingFront);
    if (deck.length) setCardContent(deck[deckIndex]);
  }

  function rebuildDeck() {
    if (!currentClassData) return;
    deck = buildDeck(currentClassData.words || [], { wordOnly: wordOnlyCheckbox.checked });
    deckIndex = 0;
    showingFront = true;
    cardEl.classList.remove("flipped");
    nextBtn.disabled = deck.length === 0;
    if (deck.length) {
      updateDisplay();
    } else {
      frontEl.innerHTML = '<div class="loading">No words in this class.</div>';
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
        frontEl.innerHTML = '<div class="error">Could not load class JSON.</div>';
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
      opt.textContent = id === "quantity" ? "Quantity" : "Class " + id.replace("class", "");
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
  wordOnlyCheckbox.addEventListener("change", rebuildDeck);
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
