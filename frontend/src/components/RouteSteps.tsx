import { Steps, Tag } from "antd";
import type { StepsProps } from "antd";
import type { CheckpointItem, TeamProgress } from "../types";
import { formatDateTime } from "../utils/format";

interface RouteStepsProps {
  checkpoints: CheckpointItem[];
  team: TeamProgress | null;
}

export function RouteSteps({ checkpoints, team }: RouteStepsProps) {
  const doneMap = new Map((team?.checkins ?? []).map((item) => [item.checkpointId, item]));

  const items: StepsProps["items"] = checkpoints.map((cp) => {
    const done = doneMap.get(cp.id);
    const isNext = team != null && team.nextCheckpointId === cp.id;
    return {
      title: `第${cp.seq}点 · ${cp.name}`,
      status: done ? "finish" : isNext ? "process" : "wait",
      description: (
        <div className="route-step-desc">
          <span>{cp.clue}</span>
          {done && <Tag color="green">已打卡 {formatDateTime(done.checkedAt)}</Tag>}
          {!done && isNext && <Tag color="processing">下一个打卡点</Tag>}
        </div>
      ),
    };
  });

  return <Steps direction="vertical" items={items} />;
}
