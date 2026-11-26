// App.jsx – VoxLead AI Application Shell
import React, { useState } from "react";
import VoiceInterface from "./components/VoiceInterface";
import ChatWindow from "./components/ChatWindow";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import { api } from "./services/api";
import "./App.css";

export default function App() {
  const [currentView, setCurrentView] = useState("agent");
  const [callId, setCallId] = useState(null);
  const [callActive, setCallActive] = useState(false);
  const [messages, setMessages] = useState([]);
  const [lead, setLead] = useState(null);
  const [appointment, setAppointment] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastAgentReply, setLastAgentReply] = useState("");
  const [currentLanguage, setCurrentLanguage] = useState("en-IN");
  const [statusMessage, setStatusMessage] = useState("");
  const [lastTurnLatency, setLastTurnLatency] = useState(null);

  const handleStartCall = async () => {
    setIsProcessing(true);
    setStatusMessage("Connecting to Nova...");
    setLastTurnLatency(null);
    try {
      const res = await api.startCall();
      setCallId(res.call_id);
      setCallActive(true);
      setMessages([{ role: "assistant", text: res.reply, sentiment: "positive", sources: [] }]);
      setLastAgentReply(res.reply);
      setLead(null);
      setAppointment(null);
      setStatusMessage("Call active — Nova is listening");
    } catch (err) {
      console.error("Start call failed:", err);
      setStatusMessage(`Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSendTurn = async (userText, clientTimestamp = null) => {
    if (!callId || !userText.trim()) return;
    setMessages((prev) => [...prev, { role: "user", text: userText, sentiment: "neutral" }]);
    setIsProcessing(true);
    setStatusMessage("Nova is thinking...");

    try {
      const turnResp = await api.sendTurn(callId, userText, currentLanguage);
      const roundtripMs = clientTimestamp ? Math.max(50, Date.now() - clientTimestamp) : null;
      if (roundtripMs) {
        setLastTurnLatency({ totalMs: roundtripMs, backendMs: turnResp.latency_ms || null });
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: turnResp.reply,
          sentiment: turnResp.sentiment,
          sources: turnResp.sources || [],
          latency: roundtripMs,
        },
      ]);

      setLastAgentReply(turnResp.reply);
      if (turnResp.lead) setLead(turnResp.lead);
      if (turnResp.appointment) setAppointment(turnResp.appointment);

      if (turnResp.call_ended) {
        setStatusMessage("✅ Call ended — Summary & insights saved");
        setTimeout(() => setCallActive(false), 4000);
      } else {
        setStatusMessage("Call active — Nova is listening");
      }
    } catch (err) {
      console.error("Turn failed:", err);
      const fallback = "I'm sorry, something went wrong. Could you repeat that?";
      setMessages((prev) => [...prev, { role: "assistant", text: fallback, sentiment: "neutral", sources: [] }]);
      setLastAgentReply(fallback);
      setStatusMessage("Connection issue — using fallback");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleEndCall = async () => {
    if (!callId) return;
    setIsProcessing(true);
    setStatusMessage("Saving summary & insights...");
    try {
      await api.endCall(callId);
      setCallActive(false);
      setStatusMessage("✅ Call complete — View insights in Dashboard");
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
      {/* ── Navbar ── */}
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
            🎙️ Voice Agent
            {callActive && <span className="live-dot" />}
          </button>
          <button
            className={`nav-tab ${currentView === "dashboard" ? "active" : ""}`}
            onClick={() => setCurrentView("dashboard")}
          >
            📊 CRM Dashboard
          </button>
        </nav>
      </header>

      {/* ── Main ── */}
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
              lastTurnLatency={lastTurnLatency}
            />

            <div className="agent-panels">
              <div className="chat-panel">
                <ChatWindow messages={messages} isProcessing={isProcessing} />
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

      {/* ── Footer ── */}
      <footer className="footer">
        VoxLead AI &nbsp;•&nbsp; Python · FastAPI · Google Gemini · React
        &nbsp;•&nbsp; NovaCRM Interview MVP
      </footer>
    </div>
  );
}
