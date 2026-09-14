import { Table, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { LeaderboardEntry } from "../types";
import { formatDateTime } from "../utils/format";

const MEDALS = ["🥇", "🥈", "🥉"];

const columns: ColumnsType<LeaderboardEntry> = [
  {
    title: "排名",
    dataIndex: "rank",
    key: "rank",
    width: 76,
    render: (rank: number) => (
      <strong>
        {rank <= 3 ? `${MEDALS[rank - 1]} ` : ""}第{rank}名
      </strong>
    ),
  },
  { title: "队伍", dataIndex: "teamName", key: "teamName" },
  {
    title: "完成状态",
    dataIndex: "statusText",
    key: "statusText",
    render: (value: string) => <Tag color="green">{value}</Tag>,
  },
  {
    title: "成绩（总用时）",
    dataIndex: "totalText",
    key: "totalText",
    render: (value: string) => <strong>{value}</strong>,
  },
  {
    title: "完赛时间",
    dataIndex: "finishedAt",
    key: "finishedAt",
    render: (value: string) => formatDateTime(value),
  },
];

interface LeaderboardTableProps {
  entries: LeaderboardEntry[];
  loading: boolean;
}

export function LeaderboardTable({ entries, loading }: LeaderboardTableProps) {
  return (
    <Table
      columns={columns}
      dataSource={entries}
      rowKey="teamId"
      pagination={false}
      loading={loading}
      locale={{ emptyText: "暂无队伍完成全部打卡，榜单虚位以待" }}
    />
  );
}
