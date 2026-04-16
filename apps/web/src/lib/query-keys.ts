export const queryKeys = {
  dataset: ["dataset-version"] as const,
  aggregation: (viewId: string, filters: Record<string, unknown>, datasetHash: string) =>
    ["aggregation", viewId, filters, datasetHash] as const,
  ragCards: (datasetHash: string) => ["rag-cards", datasetHash] as const
};
