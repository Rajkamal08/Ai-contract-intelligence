import React, { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import UploadPanel from "./components/UploadPanel";
import ChatPanel from "./components/ChatPanel";
import { getDocuments } from "./api";

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchDocuments = async () => {
    try {
      const data = await getDocuments();
      setDocuments(data.documents);
    } catch (err) {
      console.error("Failed to fetch documents:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  return (
    <div style={{ display: "flex", height: "100vh", width: "100vw", overflow: "hidden", background: "var(--bg-primary)" }}>
      {/* Sidebar for Document Management */}
      <Sidebar 
        documents={documents} 
        onSelectDocument={setSelectedDocumentId} 
        selectedDocumentId={selectedDocumentId}
        refreshDocuments={fetchDocuments}
      />

      {/* Main Content Area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <UploadPanel onUploadSuccess={fetchDocuments} />
        <ChatPanel selectedDocumentId={selectedDocumentId} />
      </div>
    </div>
  );
}
