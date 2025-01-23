export const synonyms = {
  "chabbat": ["chabat", "shabbat", "shabat", "שבת"],
  "pessah": ["pessach", "pesach", "פסח"],
  "souccot": ["succot", "sukkot", "סוכות"],
  "pourim": ["purim", "פורים"],
  "viande": ["viandes", "basar", "bassar", "בשר"],
  "cacher": ["casher", "kasher", "cachère", "kashrout", "cacherout", "כשר"],
  "lait": ["halavi", "halav", "חלב"],
  "parve": ["pareve", "parvé", "parêve", "פרווה"],
  "priere": ["prière", "tefila", "תפילה"],
  "benediction": ["bénédiction", "berakha", "bracha", "ברכה"],
  "mezouza": ["mezuzah", "מזוזה"],
  "mitsva": ["mitsvah", "mitzvah", "מצווה"],
  "halakha": ["halacha", "הלכה"],
  "torah": ["tora", "תורה"]
}

export function getWordVariations(word: string): string[] {
  const normalizedWord = word.toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

  for (const [key, variations] of Object.entries(synonyms)) {
    if (key === normalizedWord || variations.includes(normalizedWord)) {
      return [key, ...variations];
    }
  }

  return [normalizedWord];
}
