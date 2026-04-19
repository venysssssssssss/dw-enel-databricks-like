export type DatasetVersion = {
  hash: string;
  sources: string[];
  generated_at: string;
};

export type AggregationResponse<T = Record<string, unknown>> = {
  view_id: string;
  dataset_hash: string;
  filters: Record<string, unknown>;
  data: T[];
};

const etags = new Map<string, string>();

export function encodeFilters(filters: Record<string, unknown>): string {
  const json = JSON.stringify(filters);
  return btoa(json).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

export async function fetchDatasetVersion(): Promise<DatasetVersion> {
  return requestJson<DatasetVersion>("/v1/dataset/version");
}

export async function fetchAggregation<T>(
  viewId: string,
  filters: Record<string, unknown>,
  datasetHash: string
): Promise<AggregationResponse<T>> {
  const query = Object.keys(filters).length > 0 ? `?filters=${encodeFilters(filters)}` : "";
  const url = `/v1/aggregations/${viewId}${query}`;
  return requestJson<AggregationResponse<T>>(url, { cacheKey: `${url}:${datasetHash}` });
}

export async function sendRagFeedback(
  questionHash: string,
  rating: "up" | "down",
  comment = ""
): Promise<void> {
  const response = await fetch("/v1/rag/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_hash: questionHash, rating, comment })
  });
  if (!response.ok) {
    throw new Error(`Falha ao registrar feedback (${response.status})`);
  }
}

async function requestJson<T>(url: string, options: { cacheKey?: string } = {}): Promise<T> {
  const headers: HeadersInit = {};
  const cacheKey = options.cacheKey ?? url;
  const etag = etags.get(cacheKey);
  if (etag) {
    headers["If-None-Match"] = etag;
  }
  const response = await fetch(url, { headers });
  if (response.status === 304) {
    const cached = sessionStorage.getItem(cacheKey);
    if (cached) {
      return JSON.parse(cached) as T;
    }
  }
  if (!response.ok) {
    throw new Error(`Falha na API (${response.status})`);
  }
  const payload = (await response.json()) as T;
  const nextEtag = response.headers.get("ETag");
  if (nextEtag) {
    etags.set(cacheKey, nextEtag);
    sessionStorage.setItem(cacheKey, JSON.stringify(payload));
  }
  return payload;
}
