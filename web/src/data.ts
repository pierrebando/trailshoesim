// Load the three data files at start-up with relative URLs (works under any sub-path).

import { useEffect, useState } from "react";
import type { Catalog, Meta, ScoringConfig } from "./engine/types";

export interface AppData {
  catalog: Catalog;
  meta: Meta;
  config: ScoringConfig;
}

async function getJson<T>(name: string): Promise<T> {
  const response = await fetch(`${import.meta.env.BASE_URL}data/${name}`);
  if (!response.ok) throw new Error(`could not load ${name} (HTTP ${response.status})`);
  return (await response.json()) as T;
}

export function useAppData(): { data: AppData | null; error: string | null } {
  const [data, setData] = useState<AppData | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    Promise.all([getJson<Catalog>("shoes.json"), getJson<Meta>("meta.json"), getJson<ScoringConfig>("scoring_config.json")])
      .then(([catalog, meta, config]) => setData({ catalog, meta, config }))
      .catch((e: Error) => setError(e.message));
  }, []);
  return { data, error };
}
