import React from "react";
import { deleteDocument } from "../api";

export default function Sidebar({ documents, onSelectDocument, selectedDocumentId, refreshDocuments }) {
  const handleDelete = async (e, docId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this document and all its data?")) return;
    
    try {
      await deleteDocument(docId);
      refreshDocuments();
      if (selectedDocumentId === docId) {
        onSelectDocument(null);
      }
    } catch (err) {
      alert("Error deleting document: " + err.message);
    }
  };

  return (
    <div className="sidebar" style={{
      width: "var(--sidebar-width)",
      borderRight: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      background: "var(--bg-secondary)"
    }}>
      <div style={{ padding: "20px", borderBottom: "1px solid var(--border)" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: "600", color: "var(--text-primary)" }}>
          ⚖️ Contract Intelligence
        </h2>
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "4px" }}>
          Enterprise Compliance Platform
        </p>
      </div>

      <div style={{ padding: "20px", flex: 1, overflowY: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h3 style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "var(--text-secondary)", letterSpacing: "1px" }}>
            My Documents
          </h3>
          <span className="badge badge-info">{documents.length}</span>
        </div>

        {documents.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--text-muted)" }}>
            <div style={{ fontSize: "2rem", marginBottom: "8px" }}>📄</div>
            <p style={{ fontSize: "0.9rem" }}>No documents yet</p>
          </div>
        ) : (
          <ul style={{ listStyle: "none" }}>
            <li 
              onClick={() => onSelectDocument(null)}
              className="glass"
              style={{
                padding: "12px",
                borderRadius: "var(--radius-md)",
                marginBottom: "8px",
                cursor: "pointer",
                transition: "all var(--transition-fast)",
                background: selectedDocumentId === null ? "var(--bg-glass-hover)" : "transparent",
                borderColor: selectedDocumentId === null ? "var(--accent-primary)" : "transparent"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span>🌐</span>
                <span style={{ fontSize: "0.9rem", fontWeight: selectedDocumentId === null ? "600" : "400" }}>All Documents</span>
              </div>
            </li>
            
            {documents.map((doc) => (
              <li 
                key={doc.document_id}
                onClick={() => onSelectDocument(doc.document_id)}
                className="glass"
                style={{
                  padding: "12px",
                  borderRadius: "var(--radius-md)",
                  marginBottom: "8px",
                  cursor: "pointer",
                  transition: "all var(--transition-fast)",
                  background: selectedDocumentId === doc.document_id ? "var(--bg-glass-hover)" : "var(--bg-card)",
                  borderColor: selectedDocumentId === doc.document_id ? "var(--accent-primary)" : "var(--border)"
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ overflow: "hidden" }}>
                    <div style={{ 
                      fontSize: "0.9rem", 
                      fontWeight: selectedDocumentId === doc.document_id ? "600" : "500",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      color: selectedDocumentId === doc.document_id ? "var(--accent-primary)" : "var(--text-primary)"
                    }}>
                      {doc.filename}
                    </div>
                    
                    {/* Tags and Risk Score */}
                    <div style={{ display: "flex", gap: "6px", marginTop: "8px", flexWrap: "wrap" }}>
                      <span className="badge badge-info" style={{ fontSize: "0.65rem", padding: "2px 6px" }}>
                        {doc.document_type || "General"}
                      </span>
                      {doc.risk_score !== null && doc.risk_score !== undefined && (
                        <span className={`badge ${doc.risk_score > 60 ? 'badge-error' : doc.risk_score > 30 ? 'badge-warning' : 'badge-success'}`} style={{ fontSize: "0.65rem", padding: "2px 6px" }}>
                          Risk: {doc.risk_score}/100
                        </span>
                      )}
                    </div>
                    
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "6px" }}>
                      {doc.total_pages} pages • {doc.total_chunks} chunks
                    </div>
                  </div>
                  <button 
                    onClick={(e) => handleDelete(e, doc.document_id)}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                      padding: "4px",
                      borderRadius: "4px"
                    }}
                    onMouseOver={(e) => e.currentTarget.style.color = "var(--error)"}
                    onMouseOut={(e) => e.currentTarget.style.color = "var(--text-muted)"}
                    title="Delete document"
                  >
                    🗑️
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div style={{ padding: "20px", borderTop: "1px solid var(--border)", fontSize: "0.75rem", color: "var(--text-muted)", textAlign: "center" }}>
        Powered by Groq & ChromaDB
      </div>
    </div>
  );
}
