const GOJUON = [
  ["あ","ア","a"],["い","イ","i"],["う","ウ","u"],["え","エ","e"],["お","オ","o"],
  ["か","カ","ka"],["き","キ","ki"],["く","ク","ku"],["け","ケ","ke"],["こ","コ","ko"],
  ["さ","サ","sa"],["し","シ","shi"],["す","ス","su"],["せ","セ","se"],["そ","ソ","so"],
  ["た","タ","ta"],["ち","チ","chi"],["つ","ツ","tsu"],["て","テ","te"],["と","ト","to"],
  ["な","ナ","na"],["に","ニ","ni"],["ぬ","ヌ","nu"],["ね","ネ","ne"],["の","ノ","no"],
  ["は","ハ","ha"],["ひ","ヒ","hi"],["ふ","フ","fu"],["へ","ヘ","he"],["ほ","ホ","ho"],
  ["ま","マ","ma"],["み","ミ","mi"],["む","ム","mu"],["め","メ","me"],["も","モ","mo"],
  ["や","ヤ","ya"],["ゆ","ユ","yu"],["よ","ヨ","yo"],
  ["ら","ラ","ra"],["り","リ","ri"],["る","ル","ru"],["れ","レ","re"],["ろ","ロ","ro"],
  ["わ","ワ","wa"],["を","ヲ","wo"],["ん","ン","n"]
];

const DAKUON = [
  ["が","ガ","ga"],["ぎ","ギ","gi"],["ぐ","グ","gu"],["げ","ゲ","ge"],["ご","ゴ","go"],
  ["ざ","ザ","za"],["じ","ジ","ji"],["ず","ズ","zu"],["ぜ","ゼ","ze"],["ぞ","ゾ","zo"],
  ["だ","ダ","da"],["ぢ","ヂ","ji"],["づ","ヅ","zu"],["で","デ","de"],["ど","ド","do"],
  ["ば","バ","ba"],["び","ビ","bi"],["ぶ","ブ","bu"],["べ","ベ","be"],["ぼ","ボ","bo"]
];

const HANDAKUON = [
  ["ぱ","パ","pa"],["ぴ","ピ","pi"],["ぷ","プ","pu"],["ぺ","ペ","pe"],["ぽ","ポ","po"]
];

const YOON = [
  ["きゃ","キャ","kya"],["きゅ","キュ","kyu"],["きょ","キョ","kyo"],
  ["しゃ","シャ","sha"],["しゅ","シュ","shu"],["しょ","ショ","sho"],
  ["ちゃ","チャ","cha"],["ちゅ","チュ","chu"],["ちょ","チョ","cho"],
  ["にゃ","ニャ","nya"],["にゅ","ニュ","nyu"],["にょ","ニョ","nyo"],
  ["ひゃ","ヒャ","hya"],["ひゅ","ヒュ","hyu"],["ひょ","ヒョ","hyo"],
  ["みゃ","ミャ","mya"],["みゅ","ミュ","myu"],["みょ","ミョ","myo"],
  ["りゃ","リャ","rya"],["りゅ","リュ","ryu"],["りょ","リョ","ryo"],
  ["ぎゃ","ギャ","gya"],["ぎゅ","ギュ","gyu"],["ぎょ","ギョ","gyo"],
  ["じゃ","ジャ","ja"],["じゅ","ジュ","ju"],["じょ","ジョ","jo"],
  ["びゃ","ビャ","bya"],["びゅ","ビュ","byu"],["びょ","ビョ","byo"],
  ["ぴゃ","ピャ","pya"],["ぴゅ","ピュ","pyu"],["ぴょ","ピョ","pyo"]
];

function getRandomCharacter() {
  const mode = document.querySelector('input[name="mode"]:checked').value;
  const includeVoiced = document.querySelector('input[name="voiced"]').checked;
  const includeYoon = document.querySelector('input[name="yoon"]').checked;

  let pool = [...GOJUON];
  if (includeVoiced) pool = pool.concat(DAKUON, HANDAKUON);
  if (includeYoon) pool = pool.concat(YOON);

  const entry = pool[Math.floor(Math.random() * pool.length)];
  const [hiragana, katakana, romaji] = entry;
  const kana = mode === "hiro" ? hiragana : mode === "kata" ? katakana : [hiragana, katakana][Math.floor(Math.random() * 2)];
  return [kana, romaji];
}

let showingFront = true;
let currentKana = "";
let currentRomaji = "";

const card = document.getElementById("card");
const text = document.getElementById("text");

function updateDisplay() {
  text.textContent = showingFront ? currentKana : currentRomaji;
  text.className = showingFront ? "char" : "romaji";
}

function newCard() {
  [currentKana, currentRomaji] = getRandomCharacter();
  showingFront = true;
  updateDisplay();
}

function flip() {
  showingFront = !showingFront;
  updateDisplay();
}

card.addEventListener("click", flip);

document.getElementById("next-btn").addEventListener("click", newCard);

document.addEventListener("keydown", function(e) {
  if (e.code === "Space" || e.code === "Enter") {
    e.preventDefault();
    flip();
  } else if (e.key === "n" || e.key === "N") {
    newCard();
  }
});

document.querySelectorAll('input[name="mode"]').forEach(function(r) {
  r.addEventListener("change", newCard);
});
document.querySelector('input[name="voiced"]').addEventListener("change", newCard);
document.querySelector('input[name="yoon"]').addEventListener("change", newCard);

newCard();
