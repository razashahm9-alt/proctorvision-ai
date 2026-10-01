import { mirrorDetectionBox } from "../utils/detectionGeometry.js";

const DEVICE_COLORS = {
  "cell phone": "#42d7e8",
  laptop: "#ffc857",
  tv: "#ff6b85",
};

export default function DetectionOverlay({ detections, imageWidth, imageHeight }) {
  if (!detections.length || !imageWidth || !imageHeight) return null;

  const fontSize = Math.max(13, imageWidth * 0.022);
  const labelHeight = fontSize + 9;

  return (
    <svg
      className="detection-layer"
      viewBox={`0 0 ${imageWidth} ${imageHeight}`}
      preserveAspectRatio="xMidYMid slice"
      aria-label="Prohibited-device boxes on the analyzed frame"
      role="img"
    >
      <title>Prohibited-device boxes on the analyzed frame</title>
      {detections.map((detection, index) => {
        const box = mirrorDetectionBox(
          detection.box,
          imageWidth,
          imageHeight,
        );
        const color = DEVICE_COLORS[detection.class_name] || "#42d7e8";
        const confidence = Math.round((detection.confidence || 0) * 100);
        const label = `${detection.display_name} ${confidence}%`;
        const labelWidth = Math.min(
          imageWidth - box.x,
          Math.max(112, label.length * fontSize * 0.58 + 14),
        );
        const labelY = box.y >= labelHeight + 4
          ? box.y - labelHeight - 2
          : box.y + 2;

        return (
          <g key={`${detection.class_name}-${index}`}>
            <rect
              className="detection-box"
              x={box.x}
              y={box.y}
              width={box.width}
              height={box.height}
              stroke={color}
              vectorEffect="non-scaling-stroke"
            />
            <rect
              className="detection-label-background"
              x={box.x}
              y={labelY}
              width={labelWidth}
              height={labelHeight}
              rx={4}
              fill={color}
            />
            <text
              className="detection-label"
              x={box.x + 7}
              y={labelY + fontSize + 1}
              fontSize={fontSize}
            >
              {label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
