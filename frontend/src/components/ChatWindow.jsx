// components/ChatWindow.jsx – Conversation message log with sentiment & citations
import React, { useEffect, useRef } from "react";

export default function ChatWindow({ messages, isProcessing }) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing]);

  const renderSentimentBadge = (sentiment) => {
    if (!sentiment) return null;
    const s = sentiment.toLowerCase();
    let badgeClass = "badge-neutral";
    let icon = "⚪";
    if (s === "positive") {
      badgeClass = "badge-positive";
      icon = "🟢";
    } else if (s === "negative") {
      badgeClass = "badge-negative";
      icon = "🔴";
    }

    return (
      <span className={`sentiment-badge ${badgeClass}`}>
        {icon} {s}
      </span>
    );
  };

  return (
    <div className="chat-window-card">
      <div className="chat-header">
        <h3>💬 Live Conversation Transcript</h3>
        <span className="turns-count">{messages.length} turns</span>
      </div>

      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-chat-state">
            <p>Click "Start Call with Nova" to begin the conversation.</p>
          </div>
        ) : (
          messages.map((m, idx) => (
            <div
              key={idx}
              className={`message-bubble ${
                m.role === "assistant" ? "msg-assistant" : "msg-user"
              }`}
            >
              <div className="message-meta">
                <span className="sender-name">
                  {m.role === "assistant" ? "🤖 Nova (Sales Rep)" : "👤 Customer"}
                </span>
                <div className="meta-right">
                  {m.latency && (
                    <span className="message-latency" title="Roundtrip voice turnaround time">
                      ⚡ {m.latency}ms
                    </span>
                  )}
                  {renderSentimentBadge(m.sentiment)}
                </div>
              </div>

              <div className="message-body">{m.text}</div>

              {/* RAG Knowledge Base Sources Citation */}
              {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                <div className="rag-sources">
                  <span className="sources-title">📚 Retrieved Sources:</span>
                  <ul>
                    {m.sources.map((src, sIdx) => (
                      <li key={sIdx}>
                        Source: <strong>{src.file}</strong> &gt; {src.section} (Match: {Math.round(src.score * 100)}%)
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))
        )}

        {isProcessing && (
          <div className="message-bubble msg-assistant message-typing">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span className="typing-text">Nova is thinking...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
