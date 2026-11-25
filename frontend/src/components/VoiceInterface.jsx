// components/VoiceInterface.jsx – Browser Web Speech API Voice Interface
// Features:
// 1. SpeechRecognition for browser-side STT (en-IN, hi-IN, te-IN)
// 2. speechSynthesis for browser-side TTS
// 3. Audio safety loop prevention: Mic stops while assistant speaks
// 4. Manual text input fallback

import React, { useState, useEffect, useRef } from "react";

export default function VoiceInterface({
  callActive,
  onStartCall,
  onEndCall,
  onSendTurn,
  isProcessing,
  lastAgentReply,
  currentLanguage,
  onChangeLanguage,
}) {
  const [isListening, setIsListening] = useState(false);
  const [continuousMode, setContinuousMode] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [textInput, setTextInput] = useState("");
  const [isSpeakingTTS, setIsSpeakingTTS] = useState(false);

  const recognitionRef = useRef(null);

  // Initialize Web Speech API SpeechRecognition
  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn("Web SpeechRecognition is not supported in this browser.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = currentLanguage;

    recognition.onresult = (event) => {
      let interim = "";
      let final = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          final += event.results[i][0].transcript;
        } else {
          interim += event.results[i][0].transcript;
        }
      }

      const spoken = (final || interim).trim();
      setTranscript(spoken);

      if (final && final.trim()) {
        const query = final.trim();
        setTranscript("");
        // Stop listening temporarily during processing
        if (!continuousMode) {
          stopListening();
        }
        onSendTurn(query);
      }
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      if (event.error !== "no-speech") {
        setIsListening(false);
      }
    };

    recognition.onend = () => {
      // Auto-restart if in continuous mode, call is active, and not currently speaking TTS
      if (continuousMode && callActive && !isSpeakingTTS) {
        try {
          recognition.start();
          setIsListening(true);
        } catch {
          setIsListening(false);
        }
      } else {
        setIsListening(false);
      }
    };

    recognitionRef.current = recognition;

    return () => {
      try {
        recognition.stop();
      } catch {}
    };
  }, [currentLanguage, continuousMode, callActive, isSpeakingTTS]);

  // Text-To-Speech (TTS) logic: Speak last agent reply and prevent audio feedback
  useEffect(() => {
    if (!lastAgentReply || !("speechSynthesis" in window)) return;

    // Stop recognition so the mic doesn't pick up the speaker audio
    stopListening();
    window.speechSynthesis.cancel(); // cancel any ongoing speech

    const utterance = new SpeechSynthesisUtterance(lastAgentReply);
    utterance.lang = currentLanguage;
    utterance.rate = 1.0;

    utterance.onstart = () => {
      setIsSpeakingTTS(true);
    };

    utterance.onend = () => {
      setIsSpeakingTTS(false);
      // If continuous mode is enabled and call is still active, resume mic
      if (continuousMode && callActive) {
        startListening();
      }
    };

    utterance.onerror = () => {
      setIsSpeakingTTS(false);
    };

    window.speechSynthesis.speak(utterance);
  }, [lastAgentReply]);

  const startListening = () => {
    if (!recognitionRef.current || isListening || isSpeakingTTS) return;
    try {
      recognitionRef.current.lang = currentLanguage;
      recognitionRef.current.start();
      setIsListening(true);
    } catch (e) {
      console.warn("Could not start recognition:", e);
    }
  };

  const stopListening = () => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
      setIsListening(false);
    } catch (e) {}
  };

  const toggleMic = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (!textInput.trim() || isProcessing) return;
    const msg = textInput.trim();
    setTextInput("");
    onSendTurn(msg);
  };

  return (
    <div className="voice-interface-card">
      <div className="voice-header">
        <div className="call-actions">
          {!callActive ? (
            <button
              className="btn btn-primary btn-large"
              onClick={onStartCall}
              disabled={isProcessing}
            >
              📞 Start Call with Nova
            </button>
          ) : (
            <button
              className="btn btn-danger btn-large"
              onClick={onEndCall}
              disabled={isProcessing}
            >
              ⏹️ End Call
            </button>
          )}
        </div>

        <div className="language-selector">
          <label>Language:</label>
          <select
            value={currentLanguage}
            onChange={(e) => onChangeLanguage(e.target.value)}
            disabled={!callActive}
          >
            <option value="en-IN">English (India)</option>
            <option value="hi-IN">Hindi (हिंदी)</option>
            <option value="te-IN">Telugu (తెలుగు)</option>
          </select>
        </div>
      </div>

      {callActive && (
        <div className="voice-controls">
          <div className="mic-container">
            <button
              className={`mic-button ${isListening ? "mic-active" : ""} ${
                isSpeakingTTS ? "mic-disabled-tts" : ""
              }`}
              onClick={toggleMic}
              disabled={isProcessing || isSpeakingTTS}
              title={
                isSpeakingTTS
                  ? "Agent is speaking (mic paused)"
                  : isListening
                  ? "Click to mute"
                  : "Click to speak"
              }
            >
              <div className="mic-icon">
                {isSpeakingTTS ? "🔊" : isListening ? "🎙️" : "🎤"}
              </div>
              <span className="mic-label">
                {isSpeakingTTS
                  ? "Speaking..."
                  : isListening
                  ? "Listening..."
                  : "Tap to Speak"}
              </span>
            </button>

            <div className="mode-toggle">
              <label>
                <input
                  type="checkbox"
                  checked={continuousMode}
                  onChange={(e) => setContinuousMode(e.target.checked)}
                />
                Continuous Conversation Mode
              </label>
            </div>
          </div>

          {transcript && (
            <div className="live-transcript">
              <span className="transcript-label">Heard:</span> "{transcript}"
            </div>
          )}

          {/* Text Input Fallback */}
          <form className="text-fallback-form" onSubmit={handleManualSubmit}>
            <input
              type="text"
              placeholder="Or type here if mic is unavailable..."
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              disabled={isProcessing}
            />
            <button
              type="submit"
              className="btn btn-secondary"
              disabled={!textInput.trim() || isProcessing}
            >
              Send
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
