// frontend/src/suggestionsApi.js
import api from "./api";

// LIST suggestions (with optional filters)
export const fetchSuggestions = (courseId, params = {}) =>
  api.get(`/courses/${courseId}/suggestions`, { params }).then((r) => r.data);

// Create suggestion (QEC manual add)
export const createSuggestion = (courseId, payload) =>
  api.post(`/courses/${courseId}/suggestions`, payload).then((r) => r.data);

// Detail (with action timeline)
export const fetchSuggestionDetail = (suggestionId) =>
  api.get(`/suggestions/${suggestionId}`).then((r) => r.data);

// Update suggestion (status/priority/text)
export const updateSuggestion = (suggestionId, payload) =>
  api.put(`/suggestions/${suggestionId}`, payload).then((r) => r.data);

// Add action (comment / evidence / status_change)
export const addSuggestionAction = (suggestionId, payload) =>
  api.post(`/suggestions/${suggestionId}/actions`, payload).then((r) => r.data);

// Stats (QEC dashboard)
export const fetchSuggestionStats = (params = {}) =>
  api.get(`/suggestions/stats`, { params }).then((r) => r.data);
