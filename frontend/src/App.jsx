// App.jsx – Main Application Shell for VoxLead AI
import React, { useState } from "react";
import VoiceInterface from "./components/VoiceInterface";
import ChatWindow from "./components/ChatWindow";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import { api } from "./services/api";
import "./App.css";

export default function App() {
  const [currentView, setCurrentView] = useState("agent"); // 'agent' | 'dashboard'
  const [callId, setCallId] = useState(null);
  const [callActive, setCallActive] = useState(false);
  const [messages, setMessages] = useState([]);
  const [lead, setLead] = useState(null);
  const [appointment, setAppointment] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastAgentReply, setLastAgentReply] = useState("");
  const [currentLanguage, setCurrentLanguage] = useState("en-IN");
  const [statusMessage, setStatusMessage] = useState("");

  // Start Call Handler
  const handleStartCall = async () => {
    setIsProcessing(true);
    setStatusMessage("Starting conversation with NovaCRM...");
    try {
      const res = await api.startCall();
      setCallId(res.call_id);
      setCallActive(true);
      setMessages([
        {
          role: "assistant",
          text: res.reply,
          sentiment: "positive",
          sources: [],
        },
      ]);
      setLastAgentReply(res.reply);
      setLead(null);
      setAppointment(null);
      setStatusMessage("Call active");
    } catch (err) {
      console.error("Start call failed:", err);
      setStatusMessage(`Error starting call: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Turn Handler
  const handleSendTurn = async (userText) => {
    if (!callId || !userText.trim()) return;

    // 1. Optimistically append user message to chat
    setMessages((prev) => [
      ...prev,
      { role: "user", text: userText, sentiment: "neutral" },
    ]);

    setIsProcessing(true);
    setStatusMessage("Nova is processing...");

    try {
      // 2. Call backend /turn endpoint
      const turnResp = await api.sendTurn(callId, userText, currentLanguage);

      // 3. Update agent response in chat
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: turnResp.reply,
          sentiment: turnResp.sentiment,
          sources: turnResp.sources || [],
        },
      ]);

      // 4. Trigger browser TTS via lastAgentReply
      setLastAgentReply(turnResp.reply);

      // 5. Update live lead qualification & appointment
      if (turnResp.lead) {
        setLead(turnResp.lead);
      }
      if (turnResp.appointment) {
        setAppointment(turnResp.appointment);
      }
      setStatusMessage("Call active");
    } catch (err) {
      console.error("Turn failed:", err);
      const fallbackText =
        "I'm sorry, I encountered an issue. Could you repeat that?";
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: fallbackText,
          sentiment: "neutral",
          sources: [],
        },
      ]);
      setLastAgentReply(fallbackText);
      setStatusMessage("Connection error – using fallback response");
    } finally {
      setIsProcessing(false);
    }
  };

  // End Call Handler
  const handleEndCall = async () => {
    if (!callId) return;
    setIsProcessing(true);
    setStatusMessage("Generating call summary & insights...");
    try {
      const res = await api.endCall(callId);
      setCallActive(false);
      setStatusMessage(
        `Call ended. Summary: "${res.summary.substring(0, 80)}..."`
      );
    } catch (err) {
      console.error("End call failed:", err);
      setCallActive(false);
      setStatusMessage("Call ended.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="app-shell">
      {/* Top Navigation */}
      <header className="navbar">
        <div className="nav-brand">
          <span className="brand-logo">🎙️</span>
          <div>
            <h1 className="brand-title">VoxLead AI</h1>
            <span className="brand-subtitle">Autonomous Sales Voice Agent</span>
          </div>
        </div>

        <nav className="nav-links">
          <button
            className={`nav-tab ${currentView === "agent" ? "active" : ""}`}
            onClick={() => setCurrentView("agent")}
          >
            🎙️ Voice Agent {callActive && <span className="live-dot"></span>}
          </button>
          <button
            className={`nav-tab ${currentView === "dashboard" ? "active" : ""}`}
            onClick={() => setCurrentView("dashboard")}
          >
            📊 CRM Dashboard
          </button>
        </nav>
      </header>

      {/* Main Container */}
      <main className="main-content">
        {currentView === "agent" ? (
          <div className="agent-workspace">
            {statusMessage && (
              <div className="status-toast">{statusMessage}</div>
            )}

            <VoiceInterface
              callActive={callActive}
              onStartCall={handleStartCall}
              onEndCall={handleEndCall}
              onSendTurn={handleSendTurn}
              isProcessing={isProcessing}
              lastAgentReply={lastAgentReply}
              currentLanguage={currentLanguage}
              onChangeLanguage={setCurrentLanguage}
            />

            <div className="agent-panels">
              <div className="chat-panel">
                <ChatWindow
                  messages={messages}
                  isProcessing={isProcessing}
                />
              </div>
              <div className="sidebar-panel">
                <Sidebar lead={lead} appointment={appointment} />
              </div>
            </div>
          </div>
        ) : (
          <Dashboard />
        )}
      </main>

      <footer className="footer">
        <p>
          VoxLead AI • Built with Python, FastAPI, Google Gemini & React • Technical Interview MVP
        </p>
      </footer>
    </div>
  );
}
