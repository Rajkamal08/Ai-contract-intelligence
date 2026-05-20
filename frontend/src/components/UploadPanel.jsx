import React, { useState, useRef } from "react";
import { uploadDocument } from "../api";

export default function UploadPanel({ onUploadSuccess }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [documentType, setDocumentType] = useState("General");
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const processFile = async (file) => {
    if (!file) return;
    if (file.type !== "application/pdf") {
      setError("Only PDF files are supported.");
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setError("File is too large. Maximum size is 50MB.");
      return;
    }

    setError(null);
    setIsUploading(true);

    try {
      await uploadDocument(file, documentType);
      onUploadSuccess(); // Refresh document list
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
      // Reset input
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    processFile(file);
  };

  const handleChange = (e) => {
    const file = e.target.files[0];
    processFile(file);
  };

  return (
    <div style={{ padding: "32px", borderBottom: "1px solid var(--border)", display: "flex", gap: "24px", alignItems: "flex-start" }}>
      
      {/* Settings Side */}
      <div style={{ flex: "0 0 250px", display: "flex", flexDirection: "column", gap: "16px" }}>
        <h3 style={{ fontSize: "1.1rem", fontWeight: "600", color: "var(--text-primary)" }}>Document Details</h3>
        <div>
          <label style={{ display: "block", marginBottom: "8px", fontSize: "0.9rem", color: "var(--text-secondary)" }}>
            Document Type
          </label>
          <select 
            className="input" 
            value={documentType}
            onChange={(e) => setDocumentType(e.target.value)}
            disabled={isUploading}
            style={{ width: "100%", padding: "10px", appearance: "auto" }}
          >
            <option value="General">General Document</option>
            <option value="NDA">Non-Disclosure Agreement (NDA)</option>
            <option value="Employment Contract">Employment Contract</option>
            <option value="Vendor Agreement">Vendor Agreement</option>
          </select>
        </div>
      </div>

      {/* Upload Zone */}
      <div 
        className={`glass ${isDragging ? "dragging" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        style={{
          flex: 1,
          border: `2px dashed ${isDragging ? "var(--accent-primary)" : "var(--border)"}`,
          borderRadius: "var(--radius-lg)",
          padding: "40px",
          textAlign: "center",
          cursor: isUploading ? "wait" : "pointer",
          transition: "all var(--transition-base)",
          background: isDragging ? "var(--bg-glass-hover)" : "var(--bg-glass)"
        }}
      >
        <input 
          type="file" 
          accept=".pdf" 
          ref={fileInputRef} 
          onChange={handleChange} 
          style={{ display: "none" }} 
        />
        
        {isUploading ? (
          <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "16px" }}>
            <div style={{
              width: "40px",
              height: "40px",
              border: "4px solid rgba(129, 140, 248, 0.2)",
              borderTopColor: "var(--accent-primary)",
              borderRadius: "50%",
              animation: "spin 1s linear infinite"
            }} />
            <div>
              <h3 style={{ color: "var(--text-primary)", fontWeight: "500" }}>Processing Document...</h3>
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "4px" }}>
                Extracting text, chunking, and generating embeddings
              </p>
            </div>
          </div>
        ) : (
          <div className="animate-fade-in">
            <div style={{ fontSize: "3rem", marginBottom: "16px", filter: "drop-shadow(0 4px 8px rgba(0,0,0,0.2))" }}>
              📄
            </div>
            <h3 style={{ color: "var(--text-primary)", fontSize: "1.2rem", marginBottom: "8px" }}>
              Upload a new document
            </h3>
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "20px" }}>
              Drag & drop a PDF here, or click to browse
            </p>
            <button className="btn btn-primary" style={{ pointerEvents: "none" }}>
              Select File
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="animate-fade-in-up" style={{ 
          marginTop: "16px", 
          padding: "12px 16px", 
          background: "var(--error-bg)", 
          border: "1px solid rgba(248, 113, 113, 0.2)", 
          borderRadius: "var(--radius-md)",
          color: "var(--error)",
          fontSize: "0.9rem",
          display: "flex",
          alignItems: "center",
          gap: "8px"
        }}>
          <span>⚠️</span>
          {error}
        </div>
      )}
    </div>
  );
}
