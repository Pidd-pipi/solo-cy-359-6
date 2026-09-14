import { API_BASE_URL } from "../constants/app";
import type {
  ActivitySummary,
  CheckinResponse,
  LeaderboardResponse,
  OverviewResponse,
  ProgressResponse,
  RouteDetailResponse,
} from "../types";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function fetchOverview(): Promise<OverviewResponse> {
  return getJson<OverviewResponse>("/overview");
}

export async function fetchActivities(): Promise<ActivitySummary[]> {
  const payload = await getJson<{ activities: ActivitySummary[] }>("/activities");
  return payload.activities;
}

export function fetchRouteDetail(activityId: number): Promise<RouteDetailResponse> {
  return getJson<RouteDetailResponse>(`/activities/${activityId}`);
}

export function fetchProgress(activityId: number): Promise<ProgressResponse> {
  return getJson<ProgressResponse>(`/activities/${activityId}/progress`);
}

export function fetchLeaderboard(activityId: number): Promise<LeaderboardResponse> {
  return getJson<LeaderboardResponse>(`/activities/${activityId}/leaderboard`);
}

export async function postCheckin(
  activityId: number,
  teamId: number,
  checkpointId: number
): Promise<CheckinResponse> {
  const response = await fetch(`${API_BASE_URL}/activities/${activityId}/checkins`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ teamId, checkpointId }),
  });

  const body = (await response.json().catch(() => null)) as CheckinResponse | null;
  if (!body) {
    throw new Error(`Checkin request failed: ${response.status}`);
  }
  // 业务拒绝（跳点/重复/活动结束等）以后端返回的 reason 为准，不当作异常抛出。
  return body;
}
