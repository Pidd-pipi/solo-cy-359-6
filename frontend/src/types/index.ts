export interface FeatureItem {
  id: number;
  title: string;
  description: string;
  status: string;
  metric: string;
}

export interface KpiItem {
  label: string;
  value: string;
  trend: string;
  tone: string;
}

export interface OperationRecord {
  key: string;
  name: string;
  owner: string;
  status: string;
  metric: string;
  priority: string;
}

export interface OverviewResponse {
  appName: string;
  appCode: string;
  description: string;
  features: FeatureItem[];
  kpis: KpiItem[];
  records: OperationRecord[];
}

export interface ActivitySummary {
  id: number;
  name: string;
  description: string;
  status: string;
  statusText: string;
  startsAt: string;
  endsAt: string;
  checkpointCount: number;
  teamCount: number;
}

export interface ActivityInfo {
  id: number;
  name: string;
  description: string;
  status: string;
  statusText: string;
  startsAt: string;
  endsAt: string;
}

export interface CheckpointItem {
  id: number;
  seq: number;
  name: string;
  clue: string;
}

export interface RouteDetailResponse {
  activity: ActivityInfo;
  checkpoints: CheckpointItem[];
}

export interface TeamCheckinItem {
  checkpointId: number;
  seq: number;
  checkedAt: string;
}

export interface TeamProgress {
  id: number;
  name: string;
  completedCount: number;
  totalCount: number;
  status: string;
  statusText: string;
  nextCheckpointId: number | null;
  nextCheckpointSeq: number | null;
  nextCheckpointName: string | null;
  checkins: TeamCheckinItem[];
  totalSeconds: number | null;
  totalText: string | null;
  finishedAt: string | null;
}

export interface ProgressResponse {
  activity: ActivityInfo;
  checkpoints: CheckpointItem[];
  teams: TeamProgress[];
}

export interface LeaderboardEntry {
  rank: number;
  teamId: number;
  teamName: string;
  status: string;
  statusText: string;
  totalSeconds: number;
  totalText: string;
  finishedAt: string;
}

export interface LeaderboardResponse {
  activity: ActivityInfo;
  generatedAt: string;
  entries: LeaderboardEntry[];
}

export interface CheckinResponse {
  accepted: boolean;
  message?: string;
  reason?: string;
  checkin?: TeamCheckinItem;
  progress?: TeamProgress;
  result?: {
    completed: boolean;
    totalSeconds: number | null;
    totalText: string | null;
  };
}
