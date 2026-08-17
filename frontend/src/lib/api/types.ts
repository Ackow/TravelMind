export interface LivenessResponse {
  status: "ok";
  service: string;
  version: string;
}

export interface ReadinessResponse {
  status: "ready" | "not_ready";
  checks: Record<string, "ok" | "error">;
}
