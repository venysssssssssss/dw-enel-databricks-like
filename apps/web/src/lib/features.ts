type ViteImportMeta = ImportMeta & {
  env?: Record<string, string | undefined>;
};

function flagEnabled(name: string, defaultValue = true): boolean {
  const value = (import.meta as ViteImportMeta).env?.[name];
  if (value === undefined || value === "") return defaultValue;
  return !["0", "false", "off", "no"].includes(value.toLowerCase());
}

export const features = {
  severidadeV1: flagEnabled("VITE_FEATURE_SEVERIDADE_V1")
} as const;
