import { useCallback, useEffect, useRef, useState } from "react";

import {
  buildApiEndpoint,
  DEFAULT_API_BASE_URL,
  normalizeApiBaseUrl,
} from "../utils/sessionHistory.js";


const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env?.VITE_API_URL || DEFAULT_API_BASE_URL,
);


async function fetchJson(url, signal) {
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
    signal,
  });
  if (!response.ok) {
    let detail = "The session archive could not be loaded.";
    try {
      const payload = await response.json();
      if (payload?.detail) detail = payload.detail;
    } catch {
      // Preserve the readable fallback when the server response is not JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}


export function useSessionHistory() {
  const mountedRef = useRef(true);
  const listAbortRef = useRef(null);
  const detailAbortRef = useRef(null);
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");

  const loadSession = useCallback(async (sessionId) => {
    if (!sessionId) {
      setSelectedSession(null);
      setSelectedSessionId("");
      return;
    }

    detailAbortRef.current?.abort();
    const controller = new AbortController();
    detailAbortRef.current = controller;
    setSelectedSessionId(sessionId);
    setDetailLoading(true);
    setError("");
    try {
      const detail = await fetchJson(
        buildApiEndpoint(`history/sessions/${encodeURIComponent(sessionId)}`, API_BASE_URL),
        controller.signal,
      );
      if (mountedRef.current) setSelectedSession(detail);
    } catch (requestError) {
      if (requestError.name !== "AbortError" && mountedRef.current) {
        setError(requestError.message);
      }
    } finally {
      if (mountedRef.current && !controller.signal.aborted) {
        setDetailLoading(false);
      }
    }
  }, []);

  const loadSessions = useCallback(async () => {
    listAbortRef.current?.abort();
    const controller = new AbortController();
    listAbortRef.current = controller;
    setLoading(true);
    setError("");
    try {
      const payload = await fetchJson(
        buildApiEndpoint("history/sessions?limit=100", API_BASE_URL),
        controller.signal,
      );
      if (!mountedRef.current) return;
      const items = Array.isArray(payload.items) ? payload.items : [];
      setSessions(items);
      const preferredId = items.some((item) => item.id === selectedSessionId)
        ? selectedSessionId
        : items[0]?.id || "";
      if (preferredId) {
        await loadSession(preferredId);
      } else {
        setSelectedSession(null);
        setSelectedSessionId("");
      }
    } catch (requestError) {
      if (requestError.name !== "AbortError" && mountedRef.current) {
        setError(requestError.message);
      }
    } finally {
      if (mountedRef.current && !controller.signal.aborted) setLoading(false);
    }
  }, [loadSession, selectedSessionId]);

  useEffect(() => {
    mountedRef.current = true;
    loadSessions();
    return () => {
      mountedRef.current = false;
      listAbortRef.current?.abort();
      detailAbortRef.current?.abort();
    };
  }, []); // The initial archive load intentionally runs once per mounted view.

  return {
    apiBaseUrl: API_BASE_URL,
    sessions,
    selectedSession,
    selectedSessionId,
    loading,
    detailLoading,
    error,
    loadSession,
    refresh: loadSessions,
  };
}
