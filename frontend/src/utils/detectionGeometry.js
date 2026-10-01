function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

export function mirrorDetectionBox(box, imageWidth, imageHeight) {
  const x1 = clamp(Number(box?.x1) || 0, 0, imageWidth);
  const y1 = clamp(Number(box?.y1) || 0, 0, imageHeight);
  const x2 = clamp(Number(box?.x2) || 0, x1, imageWidth);
  const y2 = clamp(Number(box?.y2) || 0, y1, imageHeight);

  return {
    x: imageWidth - x2,
    y: y1,
    width: x2 - x1,
    height: y2 - y1,
  };
}
