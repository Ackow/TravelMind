import { apiRequest } from "@/lib/api/client";
import type { components } from "@/lib/api/generated";

export type Pace = components["schemas"]["Pace"];
export type TransportMode = components["schemas"]["TransportMode"];
export type DietaryPreference = components["schemas"]["DietaryPreference"];
export type Money = components["schemas"]["Money"];
type CompletePreferences = Required<components["schemas"]["TripPreferences"]>;
type CompleteConstraints = Required<components["schemas"]["TripConstraints"]>;
type GeneratedTripCreateRequest = components["schemas"]["TripCreateRequest"];
type GeneratedTripResponse = components["schemas"]["TripResponse"];

export type TripCreateRequest = Omit<
  GeneratedTripCreateRequest,
  "preferences" | "constraints"
> & {
  preferences: CompletePreferences;
  constraints: CompleteConstraints;
};

export type TripResponse = Omit<
  GeneratedTripResponse,
  "preferences" | "constraints"
> & {
  preferences: CompletePreferences;
  constraints: CompleteConstraints;
};

export function createTrip(payload: TripCreateRequest): Promise<TripResponse> {
  return apiRequest<TripResponse>("/api/v1/trips", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getTrip(tripId: string): Promise<TripResponse> {
  return apiRequest<TripResponse>("/api/v1/trips/" + tripId);
}

export function listTrips(limit = 50): Promise<TripResponse[]> {
  return apiRequest<TripResponse[]>(`/api/v1/trips?limit=${limit}`);
}

export type PlanningRunResponse =
  components["schemas"]["PlanningRunResponse"];

export async function startPlanning(
  tripId: string,
): Promise<PlanningRunResponse> {
  const body = await apiRequest<{
    planning_run: PlanningRunResponse;
  }>("/api/v1/trips/" + tripId + "/planning-runs", {
    method: "POST",
  });
  return body.planning_run;
}

type GeneratedActivity = components["schemas"]["Activity"];
export type PlanActivity = Omit<GeneratedActivity, "notes"> & {
  notes: NonNullable<GeneratedActivity["notes"]>;
};
export type PlanRouteLeg = components["schemas"]["RouteLeg"];
type GeneratedDay = components["schemas"]["DayPlan"];
export type PlanDay = Omit<
  GeneratedDay,
  "activities" | "route_legs" | "warnings"
> & {
  activities: PlanActivity[];
  route_legs: PlanRouteLeg[];
  warnings: string[];
};
type GeneratedItinerary = components["schemas"]["Itinerary"];
type GeneratedBudget = components["schemas"]["BudgetSummary"];
type GeneratedPlan = components["schemas"]["CurrentPlanResponse"];
export type PlanVersionResponse = Omit<GeneratedPlan, "itinerary"> & {
  itinerary: Omit<GeneratedItinerary, "days" | "budget" | "general_notes"> & {
    days: PlanDay[];
    budget: Required<GeneratedBudget>;
    general_notes: string[];
  };
};

export function getCurrentPlan(tripId: string): Promise<PlanVersionResponse> {
  return apiRequest<PlanVersionResponse>(
    "/api/v1/trips/" + tripId + "/plans/current",
  );
}

export function getPlanVersion(
  tripId: string,
  version: number,
): Promise<PlanVersionResponse> {
  return apiRequest<PlanVersionResponse>(
    `/api/v1/trips/${tripId}/plans/${version}`,
  );
}

export type PlanListResponse = components["schemas"]["PlanListResponse"];
export type PlanVersionSummary = components["schemas"]["PlanVersionSummary"];

export function listPlanVersions(tripId: string): Promise<PlanListResponse> {
  return apiRequest<PlanListResponse>(`/api/v1/trips/${tripId}/plans`);
}

export type FeedbackResponse = components["schemas"]["FeedbackResponse"];

export function submitWalkingFeedback(
  tripId: string,
  basePlanVersion: number,
  metersPerDay: number,
  message: string,
): Promise<FeedbackResponse> {
  return apiRequest<FeedbackResponse>(`/api/v1/trips/${tripId}/feedback`, {
    method: "POST",
    body: JSON.stringify({
      base_plan_version: basePlanVersion,
      message,
      client_operations: [
        {
          op: "set_max_walking",
          meters_per_day: metersPerDay,
          reason: "用户希望减少每日步行距离",
        },
      ],
      auto_start_replanning: true,
    }),
  });
}

export function acceptPlanVersion(
  tripId: string,
  version: number,
): Promise<PlanVersionResponse> {
  return apiRequest<PlanVersionResponse>(
    `/api/v1/trips/${tripId}/plans/${version}/accept`,
    {
      method: "POST",
    },
  );
}

export function checkoutPlanVersion(
  tripId: string,
  version: number,
): Promise<TripResponse> {
  return apiRequest<TripResponse>(
    `/api/v1/trips/${tripId}/plans/${version}/checkout`,
    {
      method: "POST",
    },
  );
}

export type PlanningEventItem = {
  id: string;
  sequence: number;
  type: string;
  step?: string | null;
  message: string;
  payload?: Record<string, unknown>;
  created_at: string;
};

export function listPlanningEvents(
  tripId: string,
  runId: string,
): Promise<{ items: PlanningEventItem[] }> {
  return apiRequest<{ items: PlanningEventItem[] }>(
    `/api/v1/trips/${tripId}/planning-runs/${runId}/events`,
  );
}

export function createFeedback(
  tripId: string,
  payload: {
    base_plan_version: number;
    message: string;
    client_operations?: Array<Record<string, unknown>>;
    auto_start_replanning?: boolean;
  },
): Promise<FeedbackResponse> {
  return apiRequest<FeedbackResponse>(`/api/v1/trips/${tripId}/feedback`, {
    method: "POST",
    body: JSON.stringify({
      base_plan_version: payload.base_plan_version,
      message: payload.message,
      client_operations: payload.client_operations || [],
      auto_start_replanning: payload.auto_start_replanning ?? true,
    }),
  });
}

export type ManualActivityEdit = components["schemas"]["ManualActivityEdit"];
export type ManualDayEdit = components["schemas"]["ManualDayEdit"];

export function submitManualPlanEdits(
  tripId: string,
  basePlanVersion: number,
  days: ManualDayEdit[],
): Promise<{
  plan: PlanVersionResponse;
  planning_run: PlanningRunResponse;
}> {
  return apiRequest(`/api/v1/trips/${tripId}/manual-edits`, {
    method: "POST",
    body: JSON.stringify({
      base_plan_version: basePlanVersion,
      days,
    }),
  });
}

