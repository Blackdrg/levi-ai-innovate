/**
 * documentService.js
 * Ingestion and management of documents (PDF/DOCX/TXT).
 */
import { apiClient } from "./apiClient";

export const documentService = {
  upload: async (file, onProgress) => {
    const formData = new FormData();
    formData.append("file", file);
    
    const response = await apiClient.post("/v1/upload/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percentCompleted);
        }
      }
    });
    return response.data;
  },
  
  // Placeholder for future multi-doc management
  getDocuments: async () => {
    const response = await apiClient.get("/v1/upload/my-docs");
    return response.data;
  }
};
