import { Progress, Table, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { TeamProgress } from "../types";

const STATUS_COLORS: Record<string, string> = {
  completed: "green",
  in_progress: "processing",
  not_started: "default",
};

const columns: ColumnsType<TeamProgress> = [
  { title: "队伍", dataIndex: "name", key: "name" },
  {
    title: "打卡进度",
    key: "progress",
    render: (_, record) => (
      <div className="team-progress-cell">
        <Progress
          percent={record.totalCount ? Math.round((record.completedCount / record.totalCount) * 100) : 0}
          size="small"
          format={() => `${record.completedCount}/${record.totalCount}`}
        />
      </div>
    ),
  },
  {
    title: "状态",
    dataIndex: "statusText",
    key: "statusText",
    render: (value: string, record) => (
      <Tag color={STATUS_COLORS[record.status] ?? "default"}>{value}</Tag>
    ),
  },
  {
    title: "下一个打卡点",
    dataIndex: "nextCheckpointName",
    key: "nextCheckpointName",
    render: (value: string | null, record) =>
      value ? `第${record.nextCheckpointSeq}点 · ${value}` : "—",
  },
  {
    title: "总用时",
    dataIndex: "totalText",
    key: "totalText",
    render: (value: string | null) => value ?? "—",
  },
];

interface TeamProgressTableProps {
  teams: TeamProgress[];
}

export function TeamProgressTable({ teams }: TeamProgressTableProps) {
  return <Table columns={columns} dataSource={teams} rowKey="id" pagination={false} />;
}
