// Types
interface SynonymDictionary {
  [key: string]: string[];
}

// Dictionnaire de synonymes et variations pour les termes religieux et courants
const synonyms: SynonymDictionary = {
  // Chabbat et fêtes
  "chabbat": ["chabat", "shabbat", "shabat", "שבת", "chabath", "shabbath"],
  "pessah": ["pessach", "pesach", "פסח", "pessakh", "pessa'h", "pesah"],
  "souccot": ["succot", "sukkot", "סוכות", "souccoth", "soukkot", "soukot"],
  "pourim": ["purim", "פורים", "pourime"],
  "roch": ["rosh", "ראש"],
  "hachana": ["hashana", "השנה", "achana"],
  "kippour": ["kipour", "kipur", "כיפור", "kippur", "yom kippour"],
  
  // Nourriture et cacherout
  "viande": ["viandes", "basar", "bassar", "בשר", "fleisch", "meat"],
  "cacher": ["casher", "kasher", "cachère", "kashrout", "cacherout", "כשר", "kosher", "cacherisé"],
  "lait": ["halavi", "halav", "חלב", "dairy", "milchik", "milchig"],
  "parve": ["pareve", "parvé", "parêve", "פרווה", "pareve", "parev"],
  "pain": ["hamotzi", "המוציא", "lechem", "לחם"],
  "poisson": ["fish", "דג", "dag"],
  "vin": ["wine", "יין", "yayin"],
  
  // Prières et rituels
  "priere": ["prière", "tefila", "תפילה", "tfila", "davening"],
  "benediction": ["bénédiction", "berakha", "bracha", "ברכה", "brakha", "beracha"],
  "mezouza": ["mezuzah", "מזוזה", "mezouzah", "mezousa"],
  "tefilin": ["tefillin", "תפילין", "phylactères", "tfilin"],
  "talith": ["talit", "טלית", "taleth", "tales"],
  
  // Concepts et lois
  "mitsva": ["mitsvah", "mitzvah", "מצווה", "mitzva", "mitsvot", "mitzvot"],
  "halakha": ["halacha", "הלכה", "halakhah", "alacha", "halakhot"],
  "torah": ["tora", "תורה", "thora", "sefer torah"],
  "cacheroute": ["kashrout", "כשרות", "kashrut", "cacherout"],
  
  // Termes courants
  "synagogue": ["shul", "beit knesset", "בית כנסת", "temple", "schul"],
  "rabbin": ["rav", "rabbi", "רב", "rabin", "rebbe"],
  "beth": ["beit", "beis", "בית", "bet"],
  "din": ["dine", "דין", "dinim"],
  
  // Famille et vie quotidienne
  "mariage": ["marriage", "חתונה", "kiddoushin", "kidouchin"],
  "divorce": ["guet", "גט", "get"],
  "enfant": ["child", "ילד", "yeled", "yeladim"],
  "famille": ["family", "משפחה", "mishpacha"],
  
  // Temps et calendrier
  "temps": ["zman", "זמן", "zmanim", "horaire"],
  "matin": ["shacharit", "שחרית", "boker"],
  "soir": ["soir", "arvit", "ערבית", "maariv"],
  "semaine": ["shavua", "שבוע", "week"]
};

// Fonction pour obtenir toutes les variations d'un mot
function getWordVariations(word: string): string[] {
  // Normaliser le mot recherché
  const normalizedWord = word.toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

  // Chercher dans les clés et les valeurs
  for (const [key, variations] of Object.entries(synonyms)) {
    if (key === normalizedWord || variations.includes(normalizedWord)) {
      return [key, ...variations];
    }
  }

  return [normalizedWord];
}

// Export des fonctions et du dictionnaire
export { synonyms, getWordVariations, hasVariations };

// Fonction pour vérifier si un mot a des variations
function hasVariations(word: string): boolean {
  const normalizedWord = word.toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
  
  return Object.entries(synonyms).some(([key, variations]) => 
    key === normalizedWord || variations.includes(normalizedWord)
  );
}
