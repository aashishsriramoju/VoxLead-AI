// components/VoiceInterface.jsx – Advanced Voice Interface with Barge-in Interruption & Latency Tracking
// Features:
// 1. Barge-in Interruption: User can interrupt Nova mid-sentence (stops TTS instantly and listens)
// 2. Turnaround Latency Measurement: Calculates exact time between human speech end and system response
// 3. Audio State Machine: [Idle] -> [Listening] -> [Processing] -> [Speaking] -> [Listening]
// 4. Natural Voice Selection: Auto-selects natural regional voices from available OS/Browser voices
// 5. Automatic error recovery and fallback text input

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
  lastTurnLatency,
}) {
  const [isListening, setIsListening] = useState(false);
  const [continuousMode, setContinuousMode] = useState(true); // default to continuous for real conversational flow
  const [transcript, setTranscript] = useState("");
  const [textInput, setTextInput] = useState("");
  const [isSpeakingTTS, setIsSpeakingTTS] = useState(false);
  const [availableVoices, setAvailableVoices] = useState([]);

  const recognitionRef = useRef(null);
  const voiceSpeechEndTimestampRef = useRef(null);

  // Load browser voices
  useEffect(() => {
    if (!("speechSynthesis" in window)) return;
    const loadVoices = () => {
      const v = window.speechSynthesis.getVoices();
      setAvailableVoices(v);
    };
    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;
  }, []);

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

      // If user speaks while Nova is speaking, trigger immediate barge-in interruption!
      if (spoken.length > 2 && isSpeakingTTS) {
        handleInterrupt();
      }

      if (final && final.trim()) {
        const query = final.trim();
        // Record timestamp when human voice ends to measure roundtrip latency
        voiceSpeechEndTimestampRef.current = Date.now();

        setTranscript("");
        if (!continuousMode) {
          stopListening();
        }
        onSendTurn(query, voiceSpeechEndTimestampRef.current);
      }
    };

    recognition.onerror = (event) => {
      if (event.error === "no-speech") {
        // Natural silence between sentences – keep listening if in continuous mode
        return;
      }
      console.warn("Speech recognition notice:", event.error);
      if (event.error === "not-allowed") {
        setIsListening(false);
      }
    };

    recognition.onend = () => {
      // Auto-reconnect if continuous mode is enabled and call is still active
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

    if (callActive && !isSpeakingTTS) {
      startListening();
    }

    return () => {
      try {
        recognition.stop();
      } catch {}
    };
  }, [currentLanguage, continuousMode, callActive, isSpeakingTTS]);

  // Text-To-Speech (TTS) logic with natural voice selection & interruption handling
  useEffect(() => {
    if (!lastAgentReply || !("speechSynthesis" in window)) return;

    // Cancel any previous audio playback
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(lastAgentReply);
    utterance.lang = currentLanguage;
    utterance.rate = 1.05; // natural conversational pacing
    utterance.pitch = 1.0;

    // Pick best regional voice if available
    if (availableVoices.length > 0) {
      const langPrefix = currentLanguage.split("-")[0];
      const match = availableVoices.find(
        (v) =>
          v.lang.toLowerCase() === currentLanguage.toLowerCase() ||
          v.lang.toLowerCase().startsWith(langPrefix)
      );
      if (match) {
        utterance.voice = match;
      }
    }

    utterance.onstart = () => {
      setIsSpeakingTTS(true);
    };

    utterance.onend = () => {
      setIsSpeakingTTS(false);
      // Resume mic immediately after Nova finishes speaking
      if (continuousMode && callActive) {
        startListening();
      }
    };

    utterance.onerror = (e) => {
      if (e.error !== "canceled" && e.error !== "interrupted") {
        console.warn("TTS notice:", e.error);
      }
      setIsSpeakingTTS(false);
      if (continuousMode && callActive) {
        startListening();
      }
    };

    window.speechSynthesis.speak(utterance);
  }, [lastAgentReply]);

  // Barge-in Interruption handler: Instantly cancels Nova's speech and opens mic
  const handleInterrupt = () => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setIsSpeakingTTS(false);
    startListening();
  };

  const startListening = () => {
    if (!recognitionRef.current || isListening) return;
    try {
      recognitionRef.current.lang = currentLanguage;
      recognitionRef.current.start();
      setIsListening(true);
    } catch (e) {
      // Ignore if already active
    }
  };

  const stopListening = () => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
      setIsListening(false);
    } catch (e) {}
  };

  const handleMicButtonClick = () => {
    // If agent is speaking, clicking the mic immediately interrupts the agent!
    if (isSpeakingTTS) {
      handleInterrupt();
      return;
    }

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
    if (isSpeakingTTS) {
      handleInterrupt();
    }
    const sentTime = Date.now();
    onSendTurn(msg, sentTime);
  };

  // State machine status label
  const getVoiceState = () => {
    if (isProcessing) return { label: "Nova is thinking...", class: "state-processing", icon: "⚙️" };
    if (isSpeakingTTS) return { label: "Nova Speaking (Click to interrupt)", class: "state-speaking", icon: "🔊" };
    if (isListening) return { label: "Listening... Speak naturally", class: "state-listening", icon: "🎙️" };
    return { label: "Microphone Paused", class: "state-idle", icon: "⏸️" };
  };

  const currentState = getVoiceState();

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

        {/* Turnaround Latency & Audio State Indicators */}
        <div className="voice-meta-header">
          {lastTurnLatency && (
            <div className="latency-badge" title="Time from human voice input to system reply">
              ⚡ Response Time: <strong>{lastTurnLatency.totalMs}ms</strong>
              {lastTurnLatency.backendMs && (
                <span className="latency-sub"> (AI: {Math.round(lastTurnLatency.backendMs)}ms)</span>
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
          {/* Audio State Machine Status Pill */}
          <div className={`voice-state-pill ${currentState.class}`}>
            <span className="state-icon">{currentState.icon}</span>
            <span className="state-text">{currentState.label}</span>
          </div>

          <div className="mic-container">
            <button
              className={`mic-button ${isListening ? "mic-active" : ""} ${
                isSpeakingTTS ? "mic-speaking-bargein" : ""
              }`}
              onClick={handleMicButtonClick}
              disabled={isProcessing}
              title={
                isSpeakingTTS
                  ? "Click to interrupt Nova!"
                  : isListening
                  ? "Click to pause microphone"
                  : "Click to speak"
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
                Continuous Conversation (Auto-Barge-in Enabled)
              </label>
            </div>
          </div>

          {transcript && (
            <div className="live-transcript">
              <span className="transcript-label">Hearing:</span> "{transcript}"
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
