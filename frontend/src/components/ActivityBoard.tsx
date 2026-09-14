import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Select, Tag, Typography } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import {
  fetchActivities,
  fetchLeaderboard,
  fetchProgress,
  fetchRouteDetail,
  postCheckin,
} from "../api/client";
import { BOARD_MESSAGES } from "../constants/messages";
import type {
  ActivitySummary,
  CheckinResponse,
  LeaderboardResponse,
  ProgressResponse,
  RouteDetailResponse,
} from "../types";
import { formatDateTime, formatTime } from "../utils/format";
import { CheckinPanel } from "./CheckinPanel";
import { LeaderboardTable } from "./LeaderboardTable";
import { RouteSteps } from "./RouteSteps";
import { TeamProgressTable } from "./TeamProgressTable";

const STATUS_COLORS: Record<string, string> = {
  ongoing: "processing",
  ended: "default",
  upcoming: "warning",
};

export function ActivityBoard() {
  const [activities, setActivities] = useState<ActivitySummary[]>([]);
  const [activityId, setActivityId] = useState<number | null>(null);
  const [detail, setDetail] = useState<RouteDetailResponse | null>(null);
  const [progress, setProgress] = useState<ProgressResponse | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardResponse | null>(null);
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<CheckinResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [lastSync, setLastSync] = useState<string | null>(null);

  useEffect(() => {
    fetchActivities()
      .then((list) => {
        setActivities(list);
        const active = list.find((item) => item.status === "ongoing") ?? list[0];
        if (active) {
          setActivityId(active.id);
        }
      })
      .catch(() => setLoadError(true));
  }, []);

  const refreshBoard = useCallback(async (id: number) => {
    const [nextProgress, nextLeaderboard] = await Promise.all([
      fetchProgress(id),
      fetchLeaderboard(id),
    ]);
    setProgress(nextProgress);
    setLeaderboard(nextLeaderboard);
    setLastSync(new Date().toISOString());
  }, []);

  useEffect(() => {
    if (activityId == null) {
      return;
    }
    setFeedback(null);
    setDetail(null);
    fetchRouteDetail(activityId).then(setDetail).catch(() => setLoadError(true));
    refreshBoard(activityId).catch(() => setLoadError(true));
  }, [activityId, refreshBoard]);

  // 实时榜单与进度：按固定间隔轮询后端，保证刷新后数据一致。
  useEffect(() => {
    if (activityId == null) {
      return;
    }
    const timer = window.setInterval(() => {
      refreshBoard(activityId).catch(() => undefined);
    }, BOARD_MESSAGES.pollingSeconds * 1000);
    return () => window.clearInterval(timer);
  }, [activityId, refreshBoard]);

  // 默认选中第一支未完赛的队伍。
  useEffect(() => {
    if (!progress) {
      return;
    }
    if (selectedTeamId != null && progress.teams.some((item) => item.id === selectedTeamId)) {
      return;
    }
    const candidate = progress.teams.find((item) => item.status !== "completed") ?? progress.teams[0];
    if (candidate) {
      setSelectedTeamId(candidate.id);
    }
  }, [progress, selectedTeamId]);

  const selectedTeam = useMemo(
    () => progress?.teams.find((item) => item.id === selectedTeamId) ?? null,
    [progress, selectedTeamId]
  );

  const handleSubmit = (teamId: number, checkpointId: number) => {
    if (activityId == null) {
      return;
    }
    setSubmitting(true);
    postCheckin(activityId, teamId, checkpointId)
      .then((result) => {
        setFeedback(result);
        return refreshBoard(activityId);
      })
      .catch(() => setFeedback({ accepted: false, reason: BOARD_MESSAGES.checkinFailed }))
      .finally(() => setSubmitting(false));
  };

  const activity = detail?.activity ?? null;

  return (
    <section className="work-panel board-panel" aria-label="活动打卡与实时排行榜">
      <div className="board-header">
        <Typography.Title level={3} className="board-title">
          活动打卡与实时排行榜
        </Typography.Title>
        <Select
          className="board-activity-select"
          placeholder="选择活动"
          value={activityId ?? undefined}
          onChange={(value) => {
            setActivityId(value);
            setSelectedTeamId(null);
          }}
          options={activities.map((item) => ({
            value: item.id,
            label: `${item.name}（${item.statusText}）`,
          }))}
        />
      </div>

      {loadError && (
        <Alert type="warning" showIcon message={BOARD_MESSAGES.loadFailed} className="board-alert" />
      )}

      {activity && (
        <div className="board-meta">
          <Tag color={STATUS_COLORS[activity.status] ?? "default"}>{activity.statusText}</Tag>
          <span>
            活动窗口：{formatDateTime(activity.startsAt)} ~ {formatDateTime(activity.endsAt)}
          </span>
          <span>{activity.description}</span>
        </div>
      )}

      <div className="board-grid">
        <div className="board-col">
          <Typography.Title level={4}>线路详情 · 按顺序打卡</Typography.Title>
          {detail && <RouteSteps checkpoints={detail.checkpoints} team={selectedTeam} />}
          {detail && progress && (
            <CheckinPanel
              checkpoints={detail.checkpoints}
              teams={progress.teams}
              selectedTeamId={selectedTeamId}
              submitting={submitting}
              feedback={feedback}
              onSelectTeam={(teamId) => {
                setSelectedTeamId(teamId);
                setFeedback(null);
              }}
              onSubmit={handleSubmit}
            />
          )}
        </div>

        <div className="board-col">
          <Typography.Title level={4}>
            <ReloadOutlined /> 实时排行榜
          </Typography.Title>
          <LeaderboardTable entries={leaderboard?.entries ?? []} loading={!leaderboard && !loadError} />
          <div className="board-sync">
            每 {BOARD_MESSAGES.pollingSeconds} 秒自动刷新，仅完赛队伍上榜，按总用时从短到长排序
            {lastSync ? ` · 上次同步 ${formatTime(lastSync)}` : ""}
          </div>
          <Typography.Title level={4}>队伍进度</Typography.Title>
          <TeamProgressTable teams={progress?.teams ?? []} />
        </div>
      </div>
    </section>
  );
}
