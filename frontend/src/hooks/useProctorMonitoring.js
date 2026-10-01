import { useCallback, useEffect, useRef, useState } from "react";

import { calculateRoundTripMs } from "../utils/analysisTiming.js";
import { monitoringWebSocketUrl } from "../utils/connection.js";

const FRAME_INTERVAL_MS = 250;
const MAX_CAPTURE_WIDTH = 416;
const JPEG_QUALITY = 0.72;

function stopMediaStream(stream) {
  stream?.getTracks().forEach((track) => track.stop());
}

export function useProctorMonitoring() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const socketRef = useRef(null);
  const captureTimerRef = useRef(null);
  const capturePendingRef = useRef(false);
  const awaitingResponseRef = useRef(false);
  const inFlightFrameRef = useRef(null);
  const analyzedFrameUrlRef = useRef("");
  const stopRequestedRef = useRef(false);
  const audioContextRef = useRef(null);
  const mountedRef = useRef(true);

  const [status, setStatus] = useState("idle");
  const [sessionId, setSessionId] = useState("");
  const [activeIncidents, setActiveIncidents] = useState([]);
  const [recentEvents, setRecentEvents] = useState([]);
  const [incidentCount, setIncidentCount] = useState(0);
  const [inferenceMs, setInferenceMs] = useState(null);
  const [roundTripMs, setRoundTripMs] = useState(null);
  const [serverProcessingMs, setServerProcessingMs] = useState(null);
  const [runtime, setRuntime] = useState("CPU");
  const [modelName, setModelName] = useState("YOLO11s");
  const [visibleDeviceCount, setVisibleDeviceCount] = useState(0);
  const [detections, setDetections] = useState([]);
  const [analyzedFrameUrl, setAnalyzedFrameUrl] = useState("");
  const [detectionFrameSize, setDetectionFrameSize] = useState({
    width: 0,
    height: 0,
  });
  const [error, setError] = useState("");

  const clearCaptureTimer = useCallback(() => {
    if (captureTimerRef.current !== null) {
      window.clearInterval(captureTimerRef.current);
      captureTimerRef.current = null;
    }
    capturePendingRef.current = false;
    awaitingResponseRef.current = false;
    inFlightFrameRef.current = null;
  }, []);

  const clearAnalyzedFrame = useCallback(() => {
    if (analyzedFrameUrlRef.current) {
      URL.revokeObjectURL(analyzedFrameUrlRef.current);
      analyzedFrameUrlRef.current = "";
    }
    setAnalyzedFrameUrl("");
  }, []);

  const showAnalyzedFrame = useCallback((blob) => {
    const nextUrl = URL.createObjectURL(blob);
    if (analyzedFrameUrlRef.current) {
      URL.revokeObjectURL(analyzedFrameUrlRef.current);
    }
    analyzedFrameUrlRef.current = nextUrl;
    setAnalyzedFrameUrl(nextUrl);
  }, []);

  const releaseCamera = useCallback(() => {
    stopMediaStream(streamRef.current);
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  const playAlertTone = useCallback(() => {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;

    const context = audioContextRef.current || new AudioContextClass();
    audioContextRef.current = context;
    if (context.state === "suspended") {
      context.resume().catch(() => {});
    }

    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const startedAt = context.currentTime;
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(880, startedAt);
    gain.gain.setValueAtTime(0.0001, startedAt);
    gain.gain.exponentialRampToValueAtTime(0.24, startedAt + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, startedAt + 0.24);
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start(startedAt);
    oscillator.stop(startedAt + 0.25);
  }, []);

  const captureAndSend = useCallback(() => {
    const socket = socketRef.current;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (
      stopRequestedRef.current ||
      !socket ||
      socket.readyState !== WebSocket.OPEN ||
      !video ||
      !canvas ||
      video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA ||
      capturePendingRef.current ||
      awaitingResponseRef.current
    ) {
      return;
    }

    const sourceWidth = video.videoWidth;
    const sourceHeight = video.videoHeight;
    if (!sourceWidth || !sourceHeight) return;

    const scale = Math.min(1, MAX_CAPTURE_WIDTH / sourceWidth);
    canvas.width = Math.max(1, Math.round(sourceWidth * scale));
    canvas.height = Math.max(1, Math.round(sourceHeight * scale));
    const context = canvas.getContext("2d", { alpha: false });
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    capturePendingRef.current = true;
    canvas.toBlob(
      (blob) => {
        capturePendingRef.current = false;
        if (
          stopRequestedRef.current ||
          !blob ||
          socket.readyState !== WebSocket.OPEN
        ) {
          return;
        }
        try {
          awaitingResponseRef.current = true;
          inFlightFrameRef.current = {
            blob,
            sentAt: performance.now(),
          };
          socket.send(blob);
        } catch {
          awaitingResponseRef.current = false;
          inFlightFrameRef.current = null;
        }
      },
      "image/jpeg",
      JPEG_QUALITY,
    );
  }, []);

  const startCaptureTimer = useCallback(() => {
    clearCaptureTimer();
    captureAndSend();
    captureTimerRef.current = window.setInterval(
      captureAndSend,
      FRAME_INTERVAL_MS,
    );
  }, [captureAndSend, clearCaptureTimer]);

  const handleFrameResult = useCallback(
    (message) => {
      const receivedAt = performance.now();
      const analyzedFrame = inFlightFrameRef.current;
      inFlightFrameRef.current = null;
      awaitingResponseRef.current = false;
      const detection = message.detection ?? {};
      const monitoring = message.monitoring ?? {};
      const nextDetections = Array.isArray(detection.detections)
        ? detection.detections
        : [];
      const events = Array.isArray(monitoring.events) ? monitoring.events : [];
      const startedEvents = events.filter(
        (event) => event.event_type === "started",
      );

      setInferenceMs(detection.inference_ms ?? null);
      setRoundTripMs(
        analyzedFrame
          ? calculateRoundTripMs(analyzedFrame.sentAt, receivedAt)
          : null,
      );
      setServerProcessingMs(message.server_processing_ms ?? null);
      setRuntime(detection.runtime || "CPU");
      setModelName(detection.model_name || "YOLO11s");
      setVisibleDeviceCount(detection.device_count ?? 0);
      setDetections(nextDetections);
      setDetectionFrameSize({
        width: detection.image_width ?? 0,
        height: detection.image_height ?? 0,
      });
      if (nextDetections.length && analyzedFrame?.blob) {
        showAnalyzedFrame(analyzedFrame.blob);
      } else {
        clearAnalyzedFrame();
      }
      setActiveIncidents(monitoring.active_incidents ?? []);
      if (startedEvents.length) {
        setIncidentCount((count) => count + startedEvents.length);
      }
      if (events.length) {
        const receivedAt = new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
        setRecentEvents((current) => [
          ...events.map((event) => ({ ...event, receivedAt })),
          ...current,
        ].slice(0, 8));
      }
      if (monitoring.play_alert_sound) {
        playAlertTone();
      }
    },
    [clearAnalyzedFrame, playAlertTone, showAnalyzedFrame],
  );

  const finishLocally = useCallback(
    (nextStatus = "idle") => {
      clearCaptureTimer();
      releaseCamera();
      clearAnalyzedFrame();
      setActiveIncidents([]);
      setVisibleDeviceCount(0);
      setDetections([]);
      setDetectionFrameSize({ width: 0, height: 0 });
      setStatus(nextStatus);
    },
    [clearAnalyzedFrame, clearCaptureTimer, releaseCamera],
  );

  const startMonitoring = useCallback(async () => {
    if (!["idle", "error"].includes(status)) return;

    setError("");
    setSessionId("");
    setActiveIncidents([]);
    setRecentEvents([]);
    setIncidentCount(0);
    setInferenceMs(null);
    setRoundTripMs(null);
    setServerProcessingMs(null);
    setRuntime("CPU");
    setModelName("YOLO11s");
    setVisibleDeviceCount(0);
    setDetections([]);
    clearAnalyzedFrame();
    setDetectionFrameSize({ width: 0, height: 0 });
    stopRequestedRef.current = false;
    setStatus("requesting-camera");

    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass && !audioContextRef.current) {
        audioContextRef.current = new AudioContextClass();
      }

      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("This browser does not support webcam access.");
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: "user",
        },
        audio: false,
      });
      if (!mountedRef.current) {
        stopMediaStream(stream);
        return;
      }

      streamRef.current = stream;
      if (!videoRef.current) {
        throw new Error("The camera preview is not available.");
      }
      videoRef.current.srcObject = stream;
      await videoRef.current.play();

      setStatus("connecting");
      const socket = new WebSocket(monitoringWebSocketUrl());
      socket.binaryType = "arraybuffer";
      socketRef.current = socket;

      socket.onmessage = (event) => {
        if (!mountedRef.current) return;
        let message;
        try {
          message = JSON.parse(event.data);
        } catch {
          awaitingResponseRef.current = false;
          inFlightFrameRef.current = null;
          setError("The server returned an unreadable message.");
          return;
        }

        if (message.type === "session_started") {
          setSessionId(message.session_id);
          setStatus("monitoring");
          startCaptureTimer();
          return;
        }
        if (message.type === "frame_result") {
          handleFrameResult(message);
          return;
        }
        if (message.type === "session_finished") {
          setSessionId(message.session_id ?? "");
          finishLocally("idle");
          return;
        }
        if (message.type === "error") {
          awaitingResponseRef.current = false;
          inFlightFrameRef.current = null;
          setError(message.message || "Monitoring server error.");
          if (!message.recoverable) {
            finishLocally("error");
          }
        }
      };

      socket.onerror = () => {
        if (!mountedRef.current) return;
        setError("Could not connect to the monitoring server.");
      };

      socket.onclose = () => {
        socketRef.current = null;
        if (!mountedRef.current) return;
        if (stopRequestedRef.current) {
          finishLocally("idle");
        } else {
          setError("The monitoring connection closed unexpectedly.");
          finishLocally("error");
        }
      };
    } catch (startError) {
      releaseCamera();
      setError(
        startError instanceof Error
          ? startError.message
          : "Unable to start monitoring.",
      );
      setStatus("error");
    }
  }, [
    clearAnalyzedFrame,
    finishLocally,
    handleFrameResult,
    releaseCamera,
    startCaptureTimer,
    status,
  ]);

  const stopMonitoring = useCallback(() => {
    stopRequestedRef.current = true;
    setStatus("stopping");
    clearCaptureTimer();
    releaseCamera();
    clearAnalyzedFrame();

    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "stop" }));
      window.setTimeout(() => {
        if (socket.readyState === WebSocket.OPEN) socket.close(1000);
      }, 2000);
      return;
    }
    if (socket && socket.readyState === WebSocket.CONNECTING) {
      socket.close();
    }
    finishLocally("idle");
  }, [clearAnalyzedFrame, clearCaptureTimer, finishLocally, releaseCamera]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      clearCaptureTimer();
      releaseCamera();
      clearAnalyzedFrame();
      const socket = socketRef.current;
      if (socket?.readyState === WebSocket.OPEN) {
        socket.close(1000);
      }
      audioContextRef.current?.close().catch(() => {});
    };
  }, [clearAnalyzedFrame, clearCaptureTimer, releaseCamera]);

  return {
    videoRef,
    canvasRef,
    status,
    sessionId,
    activeIncidents,
    recentEvents,
    incidentCount,
    inferenceMs,
    roundTripMs,
    serverProcessingMs,
    runtime,
    modelName,
    visibleDeviceCount,
    detections,
    analyzedFrameUrl,
    detectionFrameSize,
    error,
    startMonitoring,
    stopMonitoring,
    isBlocking: activeIncidents.length > 0,
    isActive: [
      "requesting-camera",
      "connecting",
      "monitoring",
      "stopping",
    ].includes(status),
  };
}
