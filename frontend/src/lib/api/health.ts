import { apiRequest } from "./client";
import type { LivenessResponse, ReadinessResponse } from "./types";

export function getLiveness(): Promise<LivenessResponse> {
  return apiRequest<LivenessResponse>("/health/live", {
    cache: "no-store",
  });
}

export function getReadiness(): Promise<ReadinessResponse> {
  return apiRequest<ReadinessResponse>("/health/ready", {
    cache: "no-store",
  });
}
