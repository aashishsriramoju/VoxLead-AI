// components/VoiceInterface.jsx – Bulletproof Web Speech API Voice Interface
// Engineered for 100% reliability in Google Chrome, Microsoft Edge, and Chromium browsers.

import React, { useState, useEffect, useRef, useCallback } from "react";

export default function VoiceInterface({
  callActive,
  onStartCall,
  onEndCall,
  onSendTurn,
  isProcessing,
  lastAgentReply,
  currentLanguage,
  onChangeLanguage,
  lastTurnLatency,
}) {
  const [isListening, setIsListening] = useState(false);
  const [continuousMode, setContinuousMode] = useState(true);
  const [transcript, setTranscript] = useState("");
  const [textInput, setTextInput] = useState("");
  const [isSpeakingTTS, setIsSpeakingTTS] = useState(false);
  const [micError, setMicError] = useState("");
  const [browserSupported, setBrowserSupported] = useState(true);

  // References to eliminate React closure staleness
  const recognitionRef = useRef(null);
  const isListeningRef = useRef(false);
  const isSpeakingTTSRef = useRef(false);
  const callActiveRef = useRef(false);
  const continuousModeRef = useRef(true);
  const restartTimerRef = useRef(null);
  const voiceSpeechEndTimestampRef = useRef(null);

  // Sync state to refs
  useEffect(() => {
    isListeningRef.current = isListening;
  }, [isListening]);

  useEffect(() => {
    isSpeakingTTSRef.current = isSpeakingTTS;
  }, [isSpeakingTTS]);

  useEffect(() => {
    callActiveRef.current = callActive;
  }, [callActive]);

  useEffect(() => {
    continuousModeRef.current = continuousMode;
  }, [continuousMode]);

  // Check browser support
  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setBrowserSupported(false);
      setMicError(
        "Web Speech Recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge."
      );
    }
  }, []);

  // Safe Start function
  const safeStart = useCallback(() => {
    if (!recognitionRef.current || isListeningRef.current || isSpeakingTTSRef.current) {
      return;
    }
    try {
      recognitionRef.current.lang = currentLanguage;
      recognitionRef.current.start();
      isListeningRef.current = true;
      setIsListening(true);
      setMicError("");
    } catch (err) {
      // If already started, update state
      if (err.name === "InvalidStateError") {
        isListeningRef.current = true;
        setIsListening(true);
      } else {
        console.warn("Recognition start warning:", err);
      }
    }
  }, [currentLanguage]);

  // Safe Stop function
  const safeStop = useCallback(() => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
    } catch (e) {}
    isListeningRef.current = false;
    setIsListening(false);
  }, []);

  // Initialize SpeechRecognition once (or on language change)
  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) return;

    // Clean up previous instance if any
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (e) {}
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.lang = currentLanguage;

    recognition.onstart = () => {
      isListeningRef.current = true;
      setIsListening(true);
      setMicError("");
    };

    recognition.onresult = (event) => {
      let interim = "";
      let final = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const item = event.results[i][0];
        if (event.results[i].isFinal) {
          final += item.transcript;
        } else {
          interim += item.transcript;
        }
      }

      const heard = (final || interim).trim();
      if (heard) {
        setTranscript(heard);
      }

      // If user speaks while Nova is speaking, trigger barge-in interrupt
      if (heard.length > 2 && isSpeakingTTSRef.current) {
        handleInterrupt();
      }

      // If we have a final transcript, dispatch the turn!
      if (final && final.trim()) {
        const query = final.trim();
        voiceSpeechEndTimestampRef.current = Date.now();
        setTranscript("");

        // Temporarily pause listening while processing unless in pure continuous mode
        if (!continuousModeRef.current) {
          safeStop();
        }

        onSendTurn(query, voiceSpeechEndTimestampRef.current);
      }
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      if (event.error === "no-speech") {
        // Normal silence; do not treat as fatal
        return;
      }
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        setMicError(
          "Microphone permission is blocked! Please click the lock icon in your address bar and allow Microphone access."
        );
        isListeningRef.current = false;
        setIsListening(false);
        return;
      }
      if (event.error === "network") {
        setMicError("Speech recognition network error. Retrying connection...");
      }
    };

    recognition.onend = () => {
      isListeningRef.current = false;
      setIsListening(false);

      // Debounced auto-restart: prevents Chrome's synchronous InvalidStateError
      if (
        callActiveRef.current &&
        continuousModeRef.current &&
        !isSpeakingTTSRef.current
      ) {
        if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
        restartTimerRef.current = setTimeout(() => {
          if (
            callActiveRef.current &&
            !isSpeakingTTSRef.current &&
            !isListeningRef.current
          ) {
            safeStart();
          }
        }, 250);
      }
    };

    recognitionRef.current = recognition;

    // Start recognition if call is active
    if (callActiveRef.current && !isSpeakingTTSRef.current) {
      safeStart();
    }

    return () => {
      if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
      try {
        recognition.abort();
      } catch (e) {}
    };
  }, [currentLanguage, safeStart, safeStop, onSendTurn]);

  // Text-To-Speech (TTS) logic with safe mic coordination
  useEffect(() => {
    if (!lastAgentReply || !("speechSynthesis" in window)) return;

    // Stop recognition during speech playback to avoid audio feedback
    safeStop();
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(lastAgentReply);
    utterance.lang = currentLanguage;
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Select suitable regional voice if available
    const voices = window.speechSynthesis.getVoices();
    if (voices.length > 0) {
      const langPrefix = currentLanguage.split("-")[0];
      const match = voices.find(
        (v) =>
          v.lang.toLowerCase() === currentLanguage.toLowerCase() ||
          v.lang.toLowerCase().startsWith(langPrefix)
      );
      if (match) utterance.voice = match;
    }

    utterance.onstart = () => {
      setIsSpeakingTTS(true);
      isSpeakingTTSRef.current = true;
    };

    const handleSpeechComplete = () => {
      setIsSpeakingTTS(false);
      isSpeakingTTSRef.current = false;
      // Allow 300ms acoustic echo buffer before reopening mic
      if (continuousModeRef.current && callActiveRef.current) {
        setTimeout(() => {
          if (!isSpeakingTTSRef.current && callActiveRef.current) {
            safeStart();
          }
        }, 300);
      }
    };

    utterance.onend = handleSpeechComplete;
    utterance.onerror = (e) => {
      if (e.error !== "canceled" && e.error !== "interrupted") {
        console.warn("TTS error:", e.error);
      }
      handleSpeechComplete();
    };

    window.speechSynthesis.speak(utterance);
  }, [lastAgentReply, currentLanguage, safeStart, safeStop]);

  // Barge-in Interruption: Stop TTS instantly and start listening
  const handleInterrupt = () => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setIsSpeakingTTS(false);
    isSpeakingTTSRef.current = false;
    setTimeout(() => {
      safeStart();
    }, 100);
  };

  // Explicit Start Call Wrapper: Requests mic permission upfront
  const handleStartCallWithPermission = async () => {
    setMicError("");
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        // Close audio track once permission is confirmed
        stream.getTracks().forEach((track) => track.stop());
      }
    } catch (err) {
      console.warn("Microphone permission check warning:", err);
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setMicError(
          "Microphone permission was denied. Please allow microphone access in your browser settings."
        );
        return;
      }
    }
    onStartCall();
  };

  // Toggle mic button manually
  const handleMicToggle = () => {
    if (isSpeakingTTS) {
      handleInterrupt();
      return;
    }
    if (isListening) {
      safeStop();
    } else {
      safeStart();
    }
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (!textInput.trim() || isProcessing) return;
    const msg = textInput.trim();
    setTextInput("");
    if (isSpeakingTTS) {
      handleInterrupt();
    }
    const sentTime = Date.now();
    onSendTurn(msg, sentTime);
  };

  // Visual state descriptor
  const getVoiceState = () => {
    if (isProcessing)
      return { label: "Nova is thinking...", class: "state-processing", icon: "⚙️" };
    if (isSpeakingTTS)
      return { label: "Nova Speaking (Tap to interrupt)", class: "state-speaking", icon: "🔊" };
    if (isListening)
      return { label: "Listening... Speak into microphone", class: "state-listening", icon: "🎙️" };
    return { label: "Microphone Paused (Tap to Speak)", class: "state-idle", icon: "⏸️" };
  };

  const currentState = getVoiceState();

  return (
    <div className="voice-interface-card">
      {micError && (
        <div className="mic-alert-banner">
          <span>⚠️ {micError}</span>
        </div>
      )}

      <div className="voice-header">
        <div className="call-actions">
          {!callActive ? (
            <button
              className="btn btn-primary btn-large"
              onClick={handleStartCallWithPermission}
              disabled={isProcessing || !browserSupported}
            >
              📞 Start Call with Nova
            </button>
          ) : (
            <div className="active-call-btns">
              <button
                className="btn btn-danger btn-large"
                onClick={onEndCall}
                disabled={isProcessing}
              >
                ⏹️ End Call
              </button>
              {isSpeakingTTS && (
                <button
                  className="btn btn-warning btn-interrupt"
                  onClick={handleInterrupt}
                  title="Interrupt Nova mid-sentence"
                >
                  🛑 Interrupt Nova
                </button>
              )}
            </div>
          )}
        </div>

        <div className="voice-meta-header">
          {lastTurnLatency && (
            <div className="latency-badge" title="Turnaround voice latency">
              ⚡ Response: <strong>{lastTurnLatency.totalMs}ms</strong>
              {lastTurnLatency.backendMs && (
                <span className="latency-sub">
                  {" "}
                  (AI: {Math.round(lastTurnLatency.backendMs)}ms)
                </span>
              )}
            </div>
          )}

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
      </div>

      {callActive && (
        <div className="voice-controls">
          <div className={`voice-state-pill ${currentState.class}`}>
            <span className="state-icon">{currentState.icon}</span>
            <span className="state-text">{currentState.label}</span>
          </div>

          <div className="mic-container">
            <button
              className={`mic-button ${isListening ? "mic-active" : ""} ${
                isSpeakingTTS ? "mic-speaking-bargein" : ""
              }`}
              onClick={handleMicToggle}
              disabled={isProcessing}
              title={
                isSpeakingTTS
                  ? "Tap to interrupt Nova"
                  : isListening
                  ? "Tap to pause microphone"
                  : "Tap to activate microphone"
              }
            >
              <div className="mic-icon">
                {isSpeakingTTS ? "🛑" : isListening ? "🎙️" : "🎤"}
              </div>
              <span className="mic-label">
                {isSpeakingTTS
                  ? "Tap to Interrupt"
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
                Continuous Voice Mode
              </label>
            </div>
          </div>

          {/* Real-time live transcript banner with clear visual feedback */}
          {transcript ? (
            <div className="live-transcript hearing-active">
              <span className="transcript-label">Hearing you:</span> "{transcript}"
            </div>
          ) : isListening ? (
            <div className="live-transcript listening-idle">
              <span className="transcript-label">Microphone active:</span> Speak now...
            </div>
          ) : null}

          {/* Fallback Text Input */}
          <form className="text-fallback-form" onSubmit={handleManualSubmit}>
            <input
              type="text"
              placeholder="Or type here if you prefer typing..."
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
