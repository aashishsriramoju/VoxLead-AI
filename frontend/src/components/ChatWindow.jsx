// components/ChatWindow.jsx – Modern conversation transcript UI
import React, { useEffect, useRef } from "react";

function SentimentBadge({ sentiment }) {
  if (!sentiment) return null;
  const s = sentiment.toLowerCase();
  const map = {
    positive: { cls: "badge-positive", icon: "●" },
    negative: { cls: "badge-negative", icon: "●" },
    neutral:  { cls: "badge-neutral",  icon: "●" },
  };
  const { cls, icon } = map[s] || map.neutral;
  return <span className={`sentiment-badge ${cls}`}>{icon} {s}</span>;
}

export default function ChatWindow({ messages, isProcessing }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing]);

  return (
    <div className="chat-window-card">
      <div className="chat-header">
        <h3>💬 Conversation</h3>
        <span className="turns-count">{messages.length} turns</span>
      </div>

      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-chat-state">
            <p>Start a call to begin chatting with Nova</p>
          </div>
        ) : (
          messages.map((m, idx) => (
            <div
              key={idx}
              className={`message-bubble ${m.role === "assistant" ? "msg-assistant" : "msg-user"}`}
            >
              <div className="message-meta">
                <span className="sender-name">
                  {m.role === "assistant" ? "🤖 Nova" : "👤 You"}
                </span>
                <div className="meta-right">
                  {m.latency && (
                    <span className="message-latency" title="Round-trip voice latency">
                      ⚡ {m.latency}ms
                    </span>
                  )}
                  <SentimentBadge sentiment={m.sentiment} />
                </div>
              </div>

              <div className="message-body">{m.text}</div>

              {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                <div className="rag-sources">
                  <span className="sources-title">📚 Sources</span>
                  <ul>
                    {m.sources.map((src, i) => (
                      <li key={i}>
                        {src.file} › {src.section} &nbsp;
                        <strong style={{ color: "var(--cyan)" }}>
                          {Math.round(src.score * 100)}%
                        </strong>
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
            <div className="message-meta">
              <span className="sender-name">🤖 Nova</span>
            </div>
            <div className="typing-indicator">
              <span /><span /><span />
            </div>
            <span className="typing-text">thinking...</span>
          </div>
        )}

        <div ref={endRef} />
      </div>
    </div>
  );
}
