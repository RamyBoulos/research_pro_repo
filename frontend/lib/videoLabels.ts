import type { Language } from "@/types/evaluation";

const VIDEO_TITLES: Record<string, Record<Language, string>> = {
  "osce-1": {
    de: "Anamnese und Untersuchung 1",
    en: "History Taking and Physical Examination 1",
  },
  "osce-3": {
    de: "Anamnese und Untersuchung 2",
    en: "History Taking and Physical Examination 2",
  },
  "osce-4": {
    de: "Blutentnahme 1",
    en: "Blood Draw 1",
  },
  "osce-5": {
    de: "Blutentnahme 2",
    en: "Blood Draw 2",
  },
  "osce-6": {
    de: "Blutentnahme 3",
    en: "Blood Draw 3",
  },
};

const VIDEO_CATEGORIES: Record<string, Record<Language, string>> = {
  Kommunikationsstation: {
    de: "Anamnese und Untersuchung",
    en: "History Taking and Physical Examination",
  },
  "Anamnese und Untersuchung": {
    de: "Anamnese und Untersuchung",
    en: "History Taking and Physical Examination",
  },
  Blutentnahme: {
    de: "Blutentnahme",
    en: "Blood Draw",
  },
};

export function localizeVideoTitle(video: { id: string; title: string }, language: Language) {
  return VIDEO_TITLES[video.id]?.[language] ?? video.title;
}

export function localizeVideoCategory(category: string, language: Language) {
  return VIDEO_CATEGORIES[category]?.[language] ?? category;
}
