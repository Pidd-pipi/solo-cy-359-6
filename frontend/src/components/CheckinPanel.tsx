import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Select, Space, Tag, Typography } from "antd";
import { AimOutlined } from "@ant-design/icons";
import type { CheckpointItem, CheckinResponse, TeamProgress } from "../types";

interface CheckinPanelProps {
  checkpoints: CheckpointItem[];
  teams: TeamProgress[];
  selectedTeamId: number | null;
  submitting: boolean;
  feedback: CheckinResponse | null;
  onSelectTeam: (teamId: number) => void;
  onSubmit: (teamId: number, checkpointId: number) => void;
}

export function CheckinPanel({
  checkpoints,
  teams,
  selectedTeamId,
  submitting,
  feedback,
  onSelectTeam,
  onSubmit,
}: CheckinPanelProps) {
  const team = useMemo(
    () => teams.find((item) => item.id === selectedTeamId) ?? null,
    [teams, selectedTeamId]
  );
  const [checkpointId, setCheckpointId] = useState<number | null>(null);

  // 默认选中该队伍按顺序应打的下一个点；换队伍或进度刷新后同步。
  useEffect(() => {
    setCheckpointId(team?.nextCheckpointId ?? null);
  }, [team?.id, team?.nextCheckpointId]);

  const doneIds = useMemo(
    () => new Set((team?.checkins ?? []).map((item) => item.checkpointId)),
    [team]
  );

  return (
    <div className="checkin-panel">
      <Space wrap size="middle">
        <Select
          className="checkin-select"
          placeholder="选择队伍"
          value={selectedTeamId ?? undefined}
          onChange={(value) => onSelectTeam(value)}
          options={teams.map((item) => ({
            value: item.id,
            label: `${item.name}（${item.statusText} ${item.completedCount}/${item.totalCount}）`,
          }))}
        />
        <Select
          className="checkin-select"
          placeholder="选择打卡点"
          value={checkpointId ?? undefined}
          onChange={(value) => setCheckpointId(value)}
          options={checkpoints.map((cp) => ({
            value: cp.id,
            label: `第${cp.seq}点 · ${cp.name}${doneIds.has(cp.id) ? "（已打卡）" : ""}`,
          }))}
        />
        <Button
          type="primary"
          icon={<AimOutlined />}
          loading={submitting}
          disabled={team == null || checkpointId == null}
          onClick={() => team && checkpointId != null && onSubmit(team.id, checkpointId)}
        >
          提交打卡
        </Button>
      </Space>

      {team && (
        <Typography.Text type="secondary">
          {team.nextCheckpointId != null ? (
            <>
              按顺序应打卡：第{team.nextCheckpointSeq}点「{team.nextCheckpointName}」，
              跳点、重复提交与活动结束后打卡都会被拒绝。
            </>
          ) : (
            <>
              该队伍已完成全部打卡点
              {team.totalText ? (
                <Tag color="green" className="checkin-total-tag">
                  总用时 {team.totalText}
                </Tag>
              ) : null}
            </>
          )}
        </Typography.Text>
      )}

      {feedback &&
        (feedback.accepted ? (
          <Alert type="success" showIcon message="打卡成功" description={feedback.message} closable />
        ) : (
          <Alert
            type="error"
            showIcon
            message="打卡被拒绝"
            description={feedback.reason ?? "未知原因"}
            closable
          />
        ))}
    </div>
  );
}
