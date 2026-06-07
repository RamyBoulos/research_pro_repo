"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { Language } from "@/types/evaluation";
import { DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, translate } from "@/lib/translations";
import type { TranslationKey } from "@/lib/translations";

interface LanguageContextValue {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);
const STORAGE_KEY = "osce_language";

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>(DEFAULT_LANGUAGE);

  useEffect(() => {
    const storageValue = window.localStorage.getItem(STORAGE_KEY);
    if (storageValue && SUPPORTED_LANGUAGES.includes(storageValue as Language)) {
      setLanguageState(storageValue as Language);
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = language;
    window.localStorage.setItem(STORAGE_KEY, language);
  }, [language]);

  const setLanguage = (lang: Language) => {
    if (!SUPPORTED_LANGUAGES.includes(lang)) {
      return;
    }
    setLanguageState(lang);
  };

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      t: (key: TranslationKey) => translate(key, language),
    }),
    [language]
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
