(function () {
  "use strict";

  const FILES = {
    vocabs: ["class1", "class2", "class3", "class4", "class5", "quantity"],
    verbs: ["intro", "class5"],
  };

  const BASE = {
    vocabs: "../../classes/vocabs/",
    verbs: "../../classes/verbs/",
  };

  const typeSelect = document.getElementById("type-select");
  const fileSelect = document.getElementById("file-select");
  const classTitleEl = document.getElementById("class-title");
  const wrap = document.getElementById("dictionary-wrap");

  function humanName(type, id) {
    if (type === "vocabs") {
      if (id === "quantity") return "Quantity";
      if (id.startsWith("class")) return "Class " + id.replace("class", "");
    }
    if (type === "verbs") {
      if (id === "intro") return "Intro";
      if (id.startsWith("class")) return "Class " + id.replace("class", "");
    }
    return id;
  }

  function populateFileSelect() {
    const type = typeSelect.value;
    const items = FILES[type] || [];
    const previous = fileSelect.value;
    fileSelect.innerHTML = "";

    items.forEach(function (id) {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = humanName(type, id);
      fileSelect.appendChild(opt);
    });

    if (items.includes(previous)) fileSelect.value = previous;
  }

  function renderVocabs(data) {
    const words = Array.isArray(data.words) ? data.words : [];
    const table = document.createElement("table");
    table.className = "dict-table";
    table.innerHTML =
      "<thead><tr><th>#</th><th>Word</th><th>Reading</th><th>Pitch</th><th>Meaning</th></tr></thead>";

    const body = document.createElement("tbody");
    words.forEach(function (w, i) {
      const tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" + (i + 1) + "</td>" +
        "<td>" + (w.word || "") + "</td>" +
        "<td>" + (w.spelling || "") + "</td>" +
        "<td>" + (w.pitch ?? "") + "</td>" +
        "<td>" + (w.meaning || "") + "</td>";
      body.appendChild(tr);
    });
    table.appendChild(body);
    return table;
  }

  function renderVerbs(data) {
    const verbs = Array.isArray(data.verbs) ? data.verbs : [];
    const table = document.createElement("table");
    table.className = "dict-table";
    table.innerHTML =
      "<thead><tr><th>#</th><th>Lemma</th><th>Reading</th><th>Type</th><th>Meaning</th><th>Notes</th></tr></thead>";

    const body = document.createElement("tbody");
    verbs.forEach(function (v, i) {
      const tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" + (i + 1) + "</td>" +
        "<td>" + (v.lemma || "") + "</td>" +
        "<td>" + (v.reading || "") + "</td>" +
        "<td>" + (v.verb_type ?? "") + "</td>" +
        "<td>" + (v.meaning || "") + "</td>" +
        "<td>" + (v.notes || "") + "</td>";
      body.appendChild(tr);
    });
    table.appendChild(body);
    return table;
  }

  function loadDictionary() {
    const type = typeSelect.value;
    const id = fileSelect.value;
    const url = BASE[type] + id + ".json";

    wrap.innerHTML = '<div class="loading">Loading...</div>';

    fetch(url)
      .then(function (res) {
        if (!res.ok) throw new Error("Load failed");
        return res.json();
      })
      .then(function (data) {
        classTitleEl.textContent = data.title || humanName(type, id);
        wrap.innerHTML = "";
        wrap.appendChild(type === "vocabs" ? renderVocabs(data) : renderVerbs(data));
      })
      .catch(function () {
        classTitleEl.textContent = "";
        wrap.innerHTML = '<div class="error">Could not load dictionary JSON.</div>';
      });
  }

  typeSelect.addEventListener("change", function () {
    populateFileSelect();
    loadDictionary();
  });
  fileSelect.addEventListener("change", loadDictionary);

  populateFileSelect();
  loadDictionary();
})();
