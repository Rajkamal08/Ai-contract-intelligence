import React, { useState, useRef, useEffect } from "react";
import { queryDocuments, clearChatHistory, extractData } from "../api";

export default function ChatPanel({ selectedDocumentId }) {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleClear = async () => {
    if (!window.confirm("Clear chat history?")) return;
    try {
      await clearChatHistory();
      setMessages([]);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isTyping) return;

    const question = inputValue.trim();
    setInputValue("");
    
    // Add user message optimistically
    const userMsg = { id: Date.now().toString(), role: "user", content: question };
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    try {
      const response = await queryDocuments(question, { 
        document_id: selectedDocumentId,
        top_k: 5
      });
      
      const aiMsg = { 
        id: Date.now().toString() + "_ai", 
        role: "assistant", 
        content: response.answer,
        citations: response.citations,
        confidence: response.confidence_note
      };
      
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      const errorMsg = {
        id: Date.now().toString() + "_err",
        role: "assistant",
        content: "❌ Error: " + err.message,
        isError: true
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleExtract = async (promptType) => {
    if (isTyping) return;
    
    // Add user message optimistically
    const userMsg = { id: Date.now().toString(), role: "user", content: `Action: ${promptType}` };
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    try {
      const response = await extractData(promptType, { document_id: selectedDocumentId });
      
      const aiMsg = { 
        id: Date.now().toString() + "_ai", 
        role: "assistant", 
        isExtraction: true,
        title: response.title,
        data: response.data
      };
      
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      const errorMsg = {
        id: Date.now().toString() + "_err",
        role: "assistant",
        content: "❌ Error extracting data: " + err.message,
        isError: true
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Chat Header */}
      <div style={{ 
        padding: "16px 32px", 
        borderBottom: "1px solid var(--border)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        background: "var(--bg-secondary)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: "600" }}>Chat Interface</h2>
          {selectedDocumentId && (
            <span className="badge badge-info animate-fade-in">
              Filtered to specific document
            </span>
          )}
        </div>
        <button className="btn btn-ghost" onClick={handleClear} disabled={messages.length === 0}>
          🗑️ Clear History
        </button>
      </div>

      {/* Messages Area */}
      <div style={{ flex: 1, overflowY: "auto", padding: "32px", display: "flex", flexDirection: "column", gap: "24px" }}>
        {messages.length === 0 ? (
          <div style={{ margin: "auto", textAlign: "center", color: "var(--text-muted)" }}>
            <div style={{ fontSize: "3rem", marginBottom: "16px" }}>💬</div>
            <h3>Ask questions about your documents</h3>
            <p style={{ marginTop: "8px", maxWidth: "400px" }}>
              The AI will retrieve relevant context and provide answers based solely on the uploaded documents.
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div 
              key={msg.id} 
              className={`animate-fade-in-up`}
              style={{
                alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                maxWidth: "80%",
                display: "flex",
                flexDirection: "column",
                gap: "8px"
              }}
            >
              <div style={{
                background: msg.role === "user" ? "var(--accent-gradient)" : "var(--bg-glass)",
                border: msg.role === "user" ? "none" : "1px solid var(--border)",
                color: msg.isError ? "var(--error)" : (msg.role === "user" ? "#fff" : "var(--text-primary)"),
                padding: "16px 20px",
                borderRadius: "var(--radius-lg)",
                borderBottomRightRadius: msg.role === "user" ? "4px" : "var(--radius-lg)",
                borderBottomLeftRadius: msg.role === "assistant" ? "4px" : "var(--radius-lg)",
                boxShadow: msg.role === "user" ? "0 4px 12px rgba(99, 102, 241, 0.2)" : "none",
                lineHeight: "1.6",
                whiteSpace: "pre-wrap"
              }}>
                {msg.isExtraction ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    <h4 style={{ margin: 0, color: "var(--accent-primary)", borderBottom: "1px solid var(--border)", paddingBottom: "8px" }}>
                      📊 {msg.title}
                    </h4>
                    <pre style={{ 
                      margin: 0, 
                      padding: "16px", 
                      background: "rgba(0,0,0,0.2)", 
                      borderRadius: "8px",
                      overflowX: "auto",
                      fontSize: "0.85rem",
                      color: "var(--text-secondary)"
                    }}>
                      {JSON.stringify(msg.data, null, 2)}
                    </pre>
                  </div>
                ) : (
                  msg.content
                )}
              </div>
              
              {/* Citations & Confidence */}
              {msg.role === "assistant" && !msg.isExtraction && msg.citations && msg.citations.length > 0 && (
                <div style={{ alignSelf: "flex-start", display: "flex", flexDirection: "column", gap: "8px", width: "100%" }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "8px" }}>
                    <span className={`badge ${msg.confidence.includes("High") ? "badge-success" : msg.confidence.includes("Moderate") ? "badge-warning" : "badge-error"}`}>
                      {msg.confidence.split("—")[0].trim()}
                    </span>
                    <span>{msg.citations.length} sources retrieved</span>
                  </div>
                  
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                    {msg.citations.map((cit, idx) => (
                      <div key={idx} className="glass" style={{
                        padding: "10px",
                        borderRadius: "var(--radius-md)",
                        fontSize: "0.8rem",
                        color: "var(--text-secondary)",
                        flex: "1 1 300px"
                      }}>
                        <div style={{ fontWeight: "600", color: "var(--text-primary)", marginBottom: "4px" }}>
                          [Source {idx + 1}] {cit.source_file} (Page {cit.page_number})
                        </div>
                        <div style={{ fontStyle: "italic", borderLeft: "2px solid var(--accent-primary)", paddingLeft: "8px", margin: "8px 0" }}>
                          "{cit.relevant_text}"
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.7rem", color: "var(--text-muted)" }}>
                          <span>Similarity: {(cit.similarity_score * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
        
        {isTyping && (
          <div style={{ alignSelf: "flex-start", background: "var(--bg-glass)", padding: "16px 20px", borderRadius: "var(--radius-lg)", borderBottomLeftRadius: "4px" }}>
            <div style={{ display: "flex", gap: "4px", alignItems: "center", height: "20px" }}>
              <div style={{ width: "6px", height: "6px", background: "var(--text-muted)", borderRadius: "50%", animation: "typingDot 1.4s infinite ease-in-out both" }}></div>
              <div style={{ width: "6px", height: "6px", background: "var(--text-muted)", borderRadius: "50%", animation: "typingDot 1.4s infinite ease-in-out both", animationDelay: "0.2s" }}></div>
              <div style={{ width: "6px", height: "6px", background: "var(--text-muted)", borderRadius: "50%", animation: "typingDot 1.4s infinite ease-in-out both", animationDelay: "0.4s" }}></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div style={{ padding: "24px 32px", borderTop: "1px solid var(--border)", background: "var(--bg-secondary)" }}>
        
        {/* Action Prompts */}
        <div style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}>
          <button 
            onClick={() => handleExtract("Summarize Liabilities")}
            className="btn btn-ghost" 
            style={{ fontSize: "0.8rem", padding: "6px 12px", border: "1px solid var(--border)" }}
            disabled={isTyping}
          >
            ⚡ Summarize Liabilities
          </button>
          <button 
            onClick={() => handleExtract("Extract Clauses")}
            className="btn btn-ghost" 
            style={{ fontSize: "0.8rem", padding: "6px 12px", border: "1px solid var(--border)" }}
            disabled={isTyping}
          >
            ⚡ Extract Clauses
          </button>
          <button 
            onClick={() => handleExtract("Identify Non-Compete Terms")}
            className="btn btn-ghost" 
            style={{ fontSize: "0.8rem", padding: "6px 12px", border: "1px solid var(--border)" }}
            disabled={isTyping}
          >
            ⚡ Identify Non-Compete Terms
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", gap: "12px", position: "relative" }}>
          <input 
            type="text" 
            className="input" 
            placeholder="Ask a question about your documents..." 
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isTyping}
            style={{ paddingRight: "100px", fontSize: "1rem" }}
          />
          <button 
            type="submit" 
            className="btn btn-primary" 
            disabled={!inputValue.trim() || isTyping}
            style={{ position: "absolute", right: "6px", top: "6px", bottom: "6px", padding: "0 20px" }}
          >
            Send ↗
          </button>
        </form>
      </div>
    </div>
  );
}
