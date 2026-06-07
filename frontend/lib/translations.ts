import type { Language } from "@/types/evaluation";

export const TRANSLATIONS = {
  loggedInAs: {
    de: "Angemeldet als",
    en: "Logged in as",
  },
  informationTab: {
    de: "Informationen",
    en: "Information",
  },
  evaluationTab: {
    de: "Evaluation",
    en: "Evaluation",
  },
  certificateDownload: {
    de: "Bescheinigung herunterladen",
    en: "Download certificate",
  },
  certificatePendingTooltip: {
    de: "Bitte zuerst je eine Aufgabe pro Station auswerten und die Evaluation abschließen.",
    en: "Please evaluate one task per station and complete the questionnaire first.",
  },
  logout: {
    de: "Abmelden",
    en: "Logout",
  },
  selectVideoPlaceholder: {
    de: "Video auswählen",
    en: "Select a video",
  },
  startEvaluation: {
    de: "Auswertung starten",
    en: "Start evaluation",
  },
  videoLoading: {
    de: "Video wird geladen...",
    en: "Loading video...",
  },
  videoUnsupported: {
    de: "Ihr Browser unterstützt dieses Video nicht.",
    en: "Your browser does not support this video.",
  },
  browserNoAudio: {
    de: "Browser unterstützt keine Audioaufnahme.",
    en: "Browser does not support audio recording.",
  },
  noVideos: {
    de: "Keine Videos vorhanden.",
    en: "No videos available.",
  },
  readyStatus: {
    de: "Bereit",
    en: "Ready",
  },
  uploadingStatus: {
    de: "Upload läuft...",
    en: "Upload running...",
  },
  processingStatus: {
    de: "Auswertung läuft...",
    en: "Evaluation running...",
  },
  updatingLanguageStatus: {
    de: "Sprache wird aktualisiert...",
    en: "Updating language...",
  },
  showTranscript: {
    de: "Transcript anzeigen",
    en: "Show transcript",
  },
  hideTranscript: {
    de: "Transcript ausblenden",
    en: "Hide transcript",
  },
  evaluationHeader: {
    de: "Evaluation",
    en: "Evaluation",
  },
  thanks: {
    de: "Vielen Dank!",
    en: "Thank you!",
  },
  answersSaved: {
    de: "Ihre Antworten wurden gespeichert.",
    en: "Your responses have been saved.",
  },
  restart: {
    de: "Neu starten",
    en: "Start again",
  },
  next: {
    de: "Weiter",
    en: "Next",
  },
  back: {
    de: "Zurück",
    en: "Back",
  },
  submit: {
    de: "Absenden",
    en: "Submit",
  },
  notesPlaceholder: {
    de: "Ihre Anmerkungen...",
    en: "Your notes...",
  },
  evaluationIntro: {
    de: "Mit dieser Evaluation helfen Sie uns, das KI-generierte Meta-Feedback zu bewerten - also die automatische Rückmeldung auf Ihr mündliches Feedback. Bewertet wird weder Ihr Audio-Feedback selbst noch das gezeigte Video.",
    en: "With this questionnaire, you help us evaluate the AI-generated meta-feedback - the automatic response to your spoken feedback. Neither your audio feedback itself nor the video shown is being assessed.",
  },
  feedbackFocusTitle: {
    de: "Feedbackschwerpunkte",
    en: "Feedback focus areas",
  },
  microphoneDenied: {
    de: "Mikrofon-Zugriff verweigert.",
    en: "Microphone access denied.",
  },
  recordingTooShort: {
    de: "Aufnahme zu kurz. Bitte erneut aufnehmen.",
    en: "Recording too short. Please record again.",
  },
  startRecording: {
    de: "Aufnahme starten",
    en: "Start recording",
  },
  stopRecording: {
    de: "Stop",
    en: "Stop",
  },
  noRecording: {
    de: "Noch keine Aufnahme.",
    en: "No recording yet.",
  },
  recordingInProgress: {
    de: "Aufnahme läuft...",
    en: "Recording in progress...",
  },
  recordingPrivacyNotice: {
    de: "Ihre Audioaufnahme wird ausschließlich zur Verarbeitung verwendet und nicht gespeichert.",
    en: "Your audio recording is used only for processing and is not stored.",
  },
  recordingFailed: {
    de: "Aufnahme fehlgeschlagen. Bitte erneut versuchen.",
    en: "Recording failed. Please try again.",
  },
  errorDefault: {
    de: "Fehler bei der Auswertung.",
    en: "Evaluation failed.",
  },
  uploadFailed: {
    de: "Upload fehlgeschlagen.",
    en: "Upload failed.",
  },
  processingFailed: {
    de: "Verarbeitung fehlgeschlagen.",
    en: "Processing failed.",
  },
  statusLoadFailed: {
    de: "Status konnte nicht geladen werden.",
    en: "Status could not be loaded.",
  },
  videoLoadFailed: {
    de: "Videos konnten nicht geladen werden.",
    en: "Videos could not be loaded.",
  },
  videoUrlFailed: {
    de: "Video-URL konnte nicht geladen werden.",
    en: "Video URL could not be loaded.",
  },
  audioRequired: {
    de: "Bitte zuerst eine Audioaufnahme erstellen.",
    en: "Please create an audio recording first.",
  },
  videoRequired: {
    de: "Bitte ein Video auswählen.",
    en: "Please select a video.",
  },
  certificateNotice: {
    de: "Die Bescheinigung wird auf den Namen {name} ausgestellt.",
    en: "The certificate will be issued in the name of {name}.",
  },
  certificateTitle: {
    de: "Bescheinigung herunterladen",
    en: "Download certificate",
  },
  certificateCancel: {
    de: "Abbrechen",
    en: "Cancel",
  },
  certificateDownloadButton: {
    de: "Herunterladen",
    en: "Download",
  },
  infoWelcomeTitle: {
    de: "Willkommen zur Prüferschulung",
    en: "Welcome to examiner training",
  },
  infoIntro: {
    de: "Diese Schulung unterstützt Sie dabei, strukturiertes und qualitativ hochwertiges Feedback im Rahmen von OSCE-Prüfungen zu geben. Bitte lesen Sie die folgenden Hinweise sorgfältig durch, bevor Sie beginnen.",
    en: "This training helps you provide structured, high-quality feedback in OSCE exams. Please read the instructions below before you begin.",
  },
  infoTaskHeading: {
    de: "Ihre Aufgabe:",
    en: "Your task:",
  },
  infoTaskDescription: {
    de: "Bearbeiten Sie je ein Video aus den beiden Stationen: Kommunikationsstation und Blutentnahme. Für jedes Video nehmen Sie Ihr mündliches Feedback auf und starten die Auswertung. Erst wenn beide Stationen abgeschlossen und die Evaluation ausgefüllt sind, können Sie Ihre Teilnahmebescheinigung herunterladen.",
    en: "Work through one video from each station: communication and blood draw. For each video, record spoken feedback and start the evaluation. Only after both stations are complete and the questionnaire is finished can you download your certificate.",
  },
  infoStep1Title: {
    de: "Video auswählen und anschauen",
    en: "Select and watch a video",
  },
  infoStep1: {
    de: "Wählen Sie im linken Menü je ein Video pro Station aus und schauen Sie es vollständig an. Achten Sie besonders auf das gezeigte Verhalten und die Interaktion zwischen Prüfer und Kandidat.",
    en: "Choose one video per station from the left menu and watch it completely. Pay attention to the observed behavior and interaction between examiner and candidate.",
  },
  infoStep2Title: {
    de: "Mündliches Feedback aufnehmen",
    en: "Record spoken feedback",
  },
  infoStep2: {
    de: "Nehmen Sie Ihr Feedback auf, indem Sie auf ‚Aufnahme starten‘ klicken und frei sprechen. Orientieren Sie sich dabei an den Prinzipien für konstruktives Feedback.",
    en: "Record your feedback by clicking 'Start recording' and speak freely. Follow the principles of constructive feedback.",
  },
  infoStep2List1: {
    de: "Ich-Botschaften verwenden",
    en: "Use 'I' statements",
  },
  infoStep2List2: {
    de: "Konkrete Beobachtungen benennen",
    en: "Name concrete observations",
  },
  infoStep2List3: {
    de: "Beobachtung und Interpretation trennen",
    en: "Separate observation and interpretation",
  },
  infoStep2List4: {
    de: "Zukunftsorientierte Empfehlungen geben",
    en: "Give future-oriented recommendations",
  },
  infoStep3Title: {
    de: "Auswertung starten",
    en: "Start evaluation",
  },
  infoStep3: {
    de: "Klicken Sie auf ‚Auswertung starten‘, um Ihre Aufnahme zu verarbeiten. Das System analysiert Ihr Feedback anhand festgelegter Qualitätskriterien.",
    en: "Click 'Start evaluation' to process your recording. The system analyzes your feedback against defined quality criteria.",
  },
  infoPrivacyHeading: {
    de: "Datenschutzhinweis:",
    en: "Privacy notice:",
  },
  infoStep3Privacy: {
    de: "Ihre Audioaufnahmen werden ausschließlich auf lokalen Servern verarbeitet. Eine Weitergabe an Dritte findet nicht statt.",
    en: "Your audio recordings are processed only on local servers. No third-party transfer takes place.",
  },
  infoStep4Title: {
    de: "Evaluation ausfüllen",
    en: "Complete the questionnaire",
  },
  infoStep4: {
    de: "Wechseln Sie nach der Auswertung zum Bereich ‚Evaluation‘ und beantworten Sie bitte alle Fragen. Ihre Angaben werden anonym behandelt.",
    en: "After evaluation, switch to the questionnaire section and answer all questions. Your responses are treated anonymously.",
  },
  infoStep5Title: {
    de: "Bescheinigung herunterladen",
    en: "Download certificate",
  },
  infoStep5: {
    de: "Nach Abschluss der Schulung können Sie über ‚Bescheinigung herunterladen‘ eine Teilnahmebescheinigung ausstellen lassen.",
    en: "After completing the training, you can request a certificate of participation via 'Download certificate'.",
  },
  infoFooter: {
    de: "Bei technischen Problemen oder Fragen wenden Sie sich bitte an die Studienleitung.",
    en: "For technical issues or questions, please contact the study coordination.",
  },
  loginAccessCode: {
    de: "Zugangscode",
    en: "Access code",
  },
  loginYourName: {
    de: "Ihr Name",
    en: "Your name",
  },
  loginAccessCodePrompt: {
    de: "Bitte geben Sie Ihren persönlichen Zugangscode ein.",
    en: "Please enter your personal access code.",
  },
  loginNamePrompt: {
    de: "Bitte geben Sie Ihren Namen ein. Er erscheint auf der Teilnahmebescheinigung.",
    en: "Please enter your name. It will appear on your certificate.",
  },
  loginFirstName: {
    de: "Vorname",
    en: "First name",
  },
  loginLastName: {
    de: "Nachname",
    en: "Last name",
  },
  loginChecking: {
    de: "Prüfe...",
    en: "Checking...",
  },
  loginContinue: {
    de: "Weiter",
    en: "Continue",
  },
  loginSigningIn: {
    de: "Anmelden...",
    en: "Signing in...",
  },
  loginSignIn: {
    de: "Anmelden",
    en: "Sign in",
  },
  loginBack: {
    de: "Zurück",
    en: "Back",
  },
  loginInvalidCode: {
    de: "Ungültiger Zugangscode.",
    en: "Invalid access code.",
  },
  loginUnexpectedError: {
    de: "Unerwarteter Fehler.",
    en: "Unexpected error.",
  },
  loginUnexpectedLoginError: {
    de: "Unerwarteter Fehler beim Login.",
    en: "Unexpected error during sign in.",
  },
  loginFailed: {
    de: "Login fehlgeschlagen.",
    en: "Sign in failed.",
  },
  downloadCertificateTitle: {
    de: "Bescheinigung herunterladen",
    en: "Download certificate",
  },
  downloadCertificateTrainingTitle: {
    de: "Prüferschulung",
    en: "Examiner training",
  },
  downloadCertificateLabel: {
    de: "Teilnahmebescheinigung",
    en: "Certificate of participation",
  },
  downloadCertificateBody: {
    de: "Hiermit wird bestätigt, dass",
    en: "This certifies that",
  },
  downloadCertificateSuccess: {
    de: "erfolgreich an der Prüferschulung teilgenommen hat.",
    en: "has successfully participated in the examiner training.",
  },
  feedbackTotalScore: {
    de: "Gesamtscore",
    en: "Total score",
  },
  feedbackCriteriaMet: {
    de: "Kriterien erfüllt",
    en: "Criteria met",
  },
  feedbackDuration: {
    de: "Dauer",
    en: "Duration",
  },
  feedbackSummary: {
    de: "Zusammenfassung",
    en: "Summary",
  },
  feedbackCriteria: {
    de: "Kriterien",
    en: "Criteria",
  },
  feedbackKeySuggestion: {
    de: "Wichtigste Empfehlung",
    en: "Key recommendation",
  },
  feedbackExcerpt: {
    de: "Belegstelle",
    en: "Excerpt",
  },
  coachingChatTitle: {
    de: "Coaching-Chat",
    en: "Coaching chat",
  },
  coachingHelpText: {
    de: "Stellen Sie Rückfragen zur Bewertung oder lassen Sie sich eine stärkere Formulierung zeigen.",
    en: "Ask follow-up questions about the evaluation or request a stronger wording example.",
  },
  coachingUserLabel: {
    de: "Sie",
    en: "You",
  },
  coachingSourcesLabel: {
    de: "Quellen",
    en: "Sources",
  },
  coachingResponding: {
    de: "Coach antwortet...",
    en: "Coach is responding...",
  },
  coachingInputPlaceholder: {
    de: "Stellen Sie eine Rückfrage zur Bewertung...",
    en: "Ask a follow-up question about the evaluation...",
  },
  coachingSendMessage: {
    de: "Nachricht senden",
    en: "Send message",
  },
};

export type TranslationKey = keyof typeof TRANSLATIONS;

export function translate(key: TranslationKey, language: Language) {
  return TRANSLATIONS[key][language] ?? TRANSLATIONS[key].de;
}

export const EVALUATION_QUESTIONS: Record<Language, Array<
  | { type: "likert"; text: string; low: string; high: string }
  | { type: "text"; text: string }
>> = {
  de: [
    { type: "likert", text: "Ich bin mit dem Feedback zufrieden.", low: "trifft nicht zu", high: "trifft zu" },
    { type: "likert", text: "Ich empfinde das Feedback als fair.", low: "trifft nicht zu", high: "trifft zu" },
    { type: "likert", text: "Ich halte das Feedback für gerechtfertigt.", low: "trifft nicht zu", high: "trifft zu" },
    { type: "likert", text: "Ich empfinde das Feedback als nützlich.", low: "trifft nicht zu", high: "trifft zu" },
    { type: "likert", text: "Ich empfinde das Feedback als hilfreich.", low: "trifft nicht zu", high: "trifft zu" },
    { type: "likert", text: "Das Feedback unterstützt mich stark.", low: "trifft nicht zu", high: "trifft zu" },
    { type: "likert", text: "Ich akzeptiere das Feedback.", low: "trifft nicht zu", high: "trifft zu" },
    { type: "likert", text: "Ich zweifle das Feedback an.", low: "trifft nicht zu", high: "trifft zu" },
    { type: "likert", text: "Ich weise das Feedback zurück.", low: "trifft nicht zu", high: "trifft zu" },
    { type: "likert", text: "Ich bin bereit, meine Leistung zu verbessern.", low: "trifft nicht zu", high: "trifft zu" },
    { type: "likert", text: "Wenn ich dieses Feedback erhalte, fühle ich mich … zufrieden.", low: "Gar nicht", high: "Sehr" },
    { type: "likert", text: "Wenn ich dieses Feedback erhalte, fühle ich mich … selbstsicher.", low: "Gar nicht", high: "Sehr" },
    { type: "likert", text: "Wenn ich dieses Feedback erhalte, fühle ich mich … erfolgreich.", low: "Gar nicht", high: "Sehr" },
    { type: "likert", text: "Wenn ich dieses Feedback erhalte, fühle ich mich … beleidigt.", low: "Gar nicht", high: "Sehr" },
    { type: "likert", text: "Wenn ich dieses Feedback erhalte, fühle ich mich … verärgert.", low: "Gar nicht", high: "Sehr" },
    { type: "likert", text: "Wenn ich dieses Feedback erhalte, fühle ich mich … frustriert.", low: "Gar nicht", high: "Sehr" },
    { type: "text", text: "Haben Sie weitere Anmerkungen?" },
  ],
  en: [
    { type: "likert", text: "I am satisfied with the feedback.", low: "does not apply", high: "applies" },
    { type: "likert", text: "I perceive the feedback as fair.", low: "does not apply", high: "applies" },
    { type: "likert", text: "I consider the feedback justified.", low: "does not apply", high: "applies" },
    { type: "likert", text: "I perceive the feedback as useful.", low: "does not apply", high: "applies" },
    { type: "likert", text: "I perceive the feedback as helpful.", low: "does not apply", high: "applies" },
    { type: "likert", text: "The feedback strongly supports me.", low: "does not apply", high: "applies" },
    { type: "likert", text: "I accept the feedback.", low: "does not apply", high: "applies" },
    { type: "likert", text: "I have doubts about the feedback.", low: "does not apply", high: "applies" },
    { type: "likert", text: "I reject the feedback.", low: "does not apply", high: "applies" },
    { type: "likert", text: "I am willing to improve my performance.", low: "does not apply", high: "applies" },
    { type: "likert", text: "When I receive this feedback, I feel ... satisfied.", low: "Not at all", high: "Very much" },
    { type: "likert", text: "When I receive this feedback, I feel ... confident.", low: "Not at all", high: "Very much" },
    { type: "likert", text: "When I receive this feedback, I feel ... successful.", low: "Not at all", high: "Very much" },
    { type: "likert", text: "When I receive this feedback, I feel ... offended.", low: "Not at all", high: "Very much" },
    { type: "likert", text: "When I receive this feedback, I feel ... annoyed.", low: "Not at all", high: "Very much" },
    { type: "likert", text: "When I receive this feedback, I feel ... frustrated.", low: "Not at all", high: "Very much" },
    { type: "text", text: "Do you have any additional comments?" },
  ],
};

export const DEFAULT_LANGUAGE: Language = "de";

export const SUPPORTED_LANGUAGES: Language[] = ["de", "en"];

export function isSupportedLanguage(value: unknown): value is Language {
  return value === "de" || value === "en";
}
