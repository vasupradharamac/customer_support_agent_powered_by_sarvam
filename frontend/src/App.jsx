import { useState, useRef, useEffect } from "react";
import axios from "axios";
import { Mic, Volume2, Loader2, Globe } from "lucide-react";

// When served from the backend (production) the API is the same origin.
// In local dev override with VITE_API_URL.
const API_URL = (import.meta.env.VITE_API_URL || window.location.origin).replace(/\/$/, "");

// Session ID: prefer one injected by widget.js (via URL param), else generate new.
const urlParams = new URLSearchParams(window.location.search);
const SESSION_ID = urlParams.get("session") || "session_" + Date.now();
const IS_EMBEDDED = urlParams.get("embedded") === "1";

const LANGUAGES = [
  { code: "en-IN", label: "English",  welcome: "Hi! I'm your KV Iyengars support agent. How can I help you?" },
  { code: "ta-IN", label: "தமிழ்",   welcome: "வணக்கம்! நான் KV Iyengars support agent. எப்படி உதவட்டும்?" },
  { code: "hi-IN", label: "हिंदी",    welcome: "नमस्ते! मैं KV Iyengars का support agent हूँ। आज कैसे मदद करूँ?" },
  { code: "te-IN", label: "తెలుగు",  welcome: "నమస్కారం! నేను KV Iyengars support agent ని. ఎలా సహాయం చేయగలను?" },
  { code: "kn-IN", label: "ಕನ್ನಡ",   welcome: "ನಮಸ್ಕಾರ! ನಾನು KV Iyengars support agent. ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?" },
];

export default function App() {
  const [selectedLang, setSelectedLang] = useState(LANGUAGES[0]);
  const [showLangDropdown, setShowLangDropdown] = useState(false);
  const [messages, setMessages] = useState([
    { role: "agent", text: LANGUAGES[0].welcome, lang: "en-IN" },
  ]);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState("");
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });

  // Clean up session when widget/tab is closed
  useEffect(() => {
    const cleanup = () => {
      navigator.sendBeacon(`${API_URL}/session/${SESSION_ID}`, "{}");
    };
    window.addEventListener("beforeunload", cleanup);
    return () => window.removeEventListener("beforeunload", cleanup);
  }, []);

  const handleLanguageChange = (lang) => {
    setSelectedLang(lang);
    setShowLangDropdown(false);
    setMessages([{ role: "agent", text: lang.welcome, lang: lang.code }]);
  };

  const toggleRecording = async () => {
    if (isRecording) {
      setIsRecording(false);
      setIsProcessing(true);
      setProcessingStep("🎙️ Transcribing...");
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach((t) => t.stop());

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        const formData = new FormData();
        formData.append("audio", audioBlob, "recording.wav");

        try {
          setProcessingStep("🎙️ Transcribing...");
          const res = await axios.post(
            `${API_URL}/voice-chat/${SESSION_ID}`,
            formData,
            { headers: { "Content-Type": "multipart/form-data" } }
          );
          setProcessingStep("🔊 Generating voice...");

          const { transcript, agent_response, language, audio_base64 } = res.data;

          setMessages((prev) => [
            ...prev,
            { role: "user", text: transcript, lang: language },
            { role: "agent", text: agent_response, lang: language },
          ]);

          const audioBytes = Uint8Array.from(atob(audio_base64), (c) => c.charCodeAt(0));
          const audioBuffer = new Blob([audioBytes], { type: "audio/wav" });
          new Audio(URL.createObjectURL(audioBuffer)).play();

          setTimeout(scrollToBottom, 100);
        } catch (err) {
          console.error(err);
          setMessages((prev) => [
            ...prev,
            { role: "agent", text: "Sorry, something went wrong. Please try again.", lang: "en-IN" },
          ]);
        } finally {
          setIsProcessing(false);
          setProcessingStep("");
        }
      };
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];
        mediaRecorder.ondataavailable = (e) => audioChunksRef.current.push(e.data);
        mediaRecorder.start();
        setIsRecording(true);
      } catch (err) {
        alert("Microphone access denied. Please allow mic access and try again.");
        console.error(err);
      }
    }
  };

  // When embedded in an iframe, strip the outer full-page wrapper so it fills the panel
  const outerClass = IS_EMBEDDED
    ? "w-full h-screen bg-gray-900 flex flex-col"
    : "min-h-screen bg-gray-950 flex items-center justify-center p-4";
  const innerClass = IS_EMBEDDED
    ? "w-full h-full flex flex-col"
    : "w-full max-w-md bg-gray-900 rounded-2xl shadow-2xl flex flex-col h-[600px]";

  return (
    <div className={outerClass}>
      <div className={innerClass}>

        {/* Header */}
        <div className="p-4 border-b border-gray-700 flex items-center gap-3 shrink-0">
          <div className="w-10 h-10 bg-indigo-600 rounded-full flex items-center justify-center">
            <Volume2 className="text-white w-5 h-5" />
          </div>
          <div>
            <h1 className="text-white font-semibold text-sm">KV Iyengars Support</h1>
            <p className="text-gray-400 text-xs">Speak in your language</p>
          </div>

          {/* Language Dropdown */}
          <div className="ml-auto relative">
            <button
              onClick={() => setShowLangDropdown(!showLangDropdown)}
              className="flex items-center gap-1.5 bg-gray-700 hover:bg-gray-600 text-gray-200 text-xs px-3 py-1.5 rounded-full transition-colors"
            >
              <Globe className="w-3 h-3" />
              {selectedLang.label}
            </button>

            {showLangDropdown && (
              <div className="absolute right-0 top-8 bg-gray-800 border border-gray-700 rounded-xl shadow-xl z-10 overflow-hidden w-36">
                {LANGUAGES.map((lang) => (
                  <button
                    key={lang.code}
                    onClick={() => handleLanguageChange(lang)}
                    className={`w-full text-left px-4 py-2.5 text-sm transition-colors
                      ${selectedLang.code === lang.code
                        ? "bg-indigo-600 text-white"
                        : "text-gray-300 hover:bg-gray-700"
                      }`}
                  >
                    {lang.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[80%] px-4 py-2 rounded-2xl text-sm leading-relaxed
                ${msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-br-sm"
                  : "bg-gray-700 text-gray-100 rounded-bl-sm"
                }`}>
                {msg.text}
              </div>
            </div>
          ))}

          {isProcessing && (
            <div className="flex justify-start">
              <div className="bg-gray-700 px-4 py-3 rounded-2xl rounded-bl-sm flex items-center gap-2">
                <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
                <span className="text-gray-400 text-sm">{processingStep || "Thinking..."}</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Mic Button */}
        <div className="p-5 border-t border-gray-700 flex flex-col items-center gap-2 shrink-0">
          <button
            onClick={toggleRecording}
            disabled={isProcessing}
            className={`w-14 h-14 rounded-full flex items-center justify-center transition-all duration-200 shadow-lg
              ${isRecording
                ? "bg-red-500 scale-110 shadow-red-500/50 animate-pulse"
                : isProcessing
                  ? "bg-gray-600 cursor-not-allowed"
                  : "bg-indigo-600 hover:bg-indigo-500 hover:scale-105"
              }`}
          >
            <Mic className="text-white w-6 h-6" />
          </button>
          <p className="text-gray-500 text-xs">
            {isRecording
              ? "🔴 Recording... click again to send"
              : isProcessing
                ? processingStep
                : "🎙️ Click to speak"}
          </p>
        </div>

      </div>
    </div>
  );
}
