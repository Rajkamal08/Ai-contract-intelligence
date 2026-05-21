/**
 * API Client — Communicates with FastAPI backend.
 * All API calls in one place for maintainability.
 */

// Use VITE_API_URL from environment variables (set in Vercel), or fallback to local backend
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

/**
 * Upload a PDF file for ingestion.
 * @param {File} file - PDF file object
 * @param {string} documentType - E.g., 'NDA', 'Employment Contract'
 * @param {function} onProgress - Optional progress callback
 * @returns {Promise<object>} DocumentUploadResponse
 */
export async function uploadDocument(file, documentType = "General", onProgress) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("document_type", documentType);

  const response = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Upload failed");
  }

  return response.json();
}

/**
 * Get list of all ingested documents.
 * @returns {Promise<object>} DocumentListResponse
 */
export async function getDocuments() {
  const response = await fetch(`${API_BASE}/documents`);

  if (!response.ok) {
    throw new Error("Failed to fetch documents");
  }

  return response.json();
}

/**
 * Delete a document and all its vectors.
 * @param {string} documentId
 * @returns {Promise<object>}
 */
export async function deleteDocument(documentId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Delete failed");
  }

  return response.json();
}

/**
 * Send a query to the RAG pipeline.
 * @param {string} question
 * @param {object} options - { top_k, document_id, document_type }
 * @returns {Promise<object>} QueryResponse
 */
export async function queryDocuments(question, options = {}) {
  const body = {
    question,
    ...(options.top_k && { top_k: options.top_k }),
    ...(options.document_id && { document_id: options.document_id }),
    ...(options.document_type && { document_type: options.document_type }),
  };

  const response = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Query failed");
  }

  return response.json();
}

/**
 * Extract structured data from RAG pipeline.
 * @param {string} promptType - The extraction type
 * @param {object} options - { document_id, document_type }
 * @returns {Promise<object>} ExtractionResponse
 */
export async function extractData(promptType, options = {}) {
  const body = {
    prompt_type: promptType,
    ...(options.document_id && { document_id: options.document_id }),
    ...(options.document_type && { document_type: options.document_type }),
  };

  const response = await fetch(`${API_BASE}/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Extraction failed");
  }

  return response.json();
}

/**
 * Get chat history.
 * @returns {Promise<object>} ChatHistoryResponse
 */
export async function getChatHistory() {
  const response = await fetch(`${API_BASE}/history`);

  if (!response.ok) {
    throw new Error("Failed to fetch chat history");
  }

  return response.json();
}

/**
 * Clear chat history.
 * @returns {Promise<object>}
 */
export async function clearChatHistory() {
  const response = await fetch(`${API_BASE}/history`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Failed to clear chat history");
  }

  return response.json();
}

/**
 * Health check.
 * @returns {Promise<object>}
 */
export async function healthCheck() {
  const response = await fetch(`${API_BASE}/health`);
  return response.json();
}
