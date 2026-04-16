import { onCLS, onINP, onLCP, type Metric } from "web-vitals";

function sendMetric(metric: Metric): void {
  const body = JSON.stringify({
    name: metric.name,
    value: metric.value,
    rating: metric.rating,
    id: metric.id
  });
  if (navigator.sendBeacon) {
    navigator.sendBeacon("/v1/telemetry/web-vitals", body);
    return;
  }
  void fetch("/v1/telemetry/web-vitals", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true
  });
}

export function reportWebVitals(): void {
  onCLS(sendMetric);
  onINP(sendMetric);
  onLCP(sendMetric);
}
