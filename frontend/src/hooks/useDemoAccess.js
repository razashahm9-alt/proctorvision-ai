import { useCallback, useEffect, useState } from "react";

import {
  buildApiEndpoint,
  DEFAULT_API_BASE_URL,
  normalizeApiBaseUrl,
} from "../utils/sessionHistory.js";


const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env?.VITE_API_URL || DEFAULT_API_BASE_URL,
);


async function readAccessResponse(response) {
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    // A readable fallback is supplied below for non-JSON proxy errors.
  }
  if (!response.ok) {
    throw new Error(payload?.detail || "Access could not be verified.");
  }
  return payload;
}


export function useDemoAccess() {
  const [state, setState] = useState("checking");
  const [required, setRequired] = useState(false);
  const [error, setError] = useState("");

  const check = useCallback(async () => {
    setState("checking");
    setError("");
    try {
      const response = await fetch(buildApiEndpoint("auth/status", API_BASE_URL), {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      const payload = await readAccessResponse(response);
      setRequired(Boolean(payload?.required));
      setState(payload?.authenticated ? "unlocked" : "locked");
    } catch (requestError) {
      setError(requestError.message || "The ProctorVision server is unavailable.");
      setState("error");
    }
  }, []);

  const login = useCallback(async (accessToken) => {
    setState("checking");
    setError("");
    try {
      const response = await fetch(buildApiEndpoint("auth/login", API_BASE_URL), {
        method: "POST",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ access_token: accessToken }),
      });
      const payload = await readAccessResponse(response);
      setRequired(Boolean(payload?.required));
      setState("unlocked");
      return true;
    } catch (requestError) {
      setError(requestError.message || "The access token was not accepted.");
      setState("locked");
      return false;
    }
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  return { state, required, error, check, login };
}
