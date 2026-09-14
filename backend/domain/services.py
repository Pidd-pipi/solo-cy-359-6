OVERVIEW = {
  "appName": "城市定向越野活动平台",
  "appCode": "lporienteering",
  "description": "面向户外运动爱好者，提供定向越野线路设计、团队报名和积分排名的活动平台。",
  "features": [
    {
      "id": 1,
      "title": "活动线路设计与发布",
      "description": "管理员在地图上标记起点、终点和打卡点（CP点），设置各点线索和任务，发布活动时注明难度（亲子/成人/专业）、时长和装备要求。",
      "status": "已上线",
      "metric": "88%"
    },
    {
      "id": 2,
      "title": "线索打卡点（GPS/二维码）",
      "description": "参与者到达打卡点附近（GPS定位）或扫描二维码完成打卡，系统记录到达时间，打卡点可设置答题或拍照任务增加趣味性。",
      "status": "排期中",
      "metric": "31 单"
    },
    {
      "id": 3,
      "title": "团队报名与排名",
      "description": "用户以个人或团队形式报名，活动开始后系统记录各团队完成所有打卡点的总用时，按用时排名生成实时 leaderboard。",
      "status": "巡检中",
      "metric": "10 项"
    },
    {
      "id": 4,
      "title": "积分兑换商城",
      "description": "参与活动获得积分，积分可在商城兑换户外装备、活动优惠券或虚拟勋章，激励用户持续参与。",
      "status": "优化中",
      "metric": "4 级"
    },
    {
      "id": 5,
      "title": "历史线路收藏",
      "description": "用户可收藏感兴趣的已结束活动线路，查看其他参与者的成绩和路线轨迹，为下次报名提供参考。",
      "status": "可导出",
      "metric": "28 条"
    }
  ],
  "kpis": [
    {
      "label": "今日处理",
      "value": "132",
      "trend": "+12%",
      "tone": "primary"
    },
    {
      "label": "预约/订单",
      "value": "82",
      "trend": "+8%",
      "tone": "warm"
    },
    {
      "label": "履约率",
      "value": "90%",
      "trend": "+3%",
      "tone": "cool"
    },
    {
      "label": "待处理",
      "value": "5",
      "trend": "需跟进",
      "tone": "neutral"
    }
  ],
  "records": [
    {
      "key": "lporienteering-1",
      "name": "活动线路设计与发布",
      "owner": "运营组",
      "status": "已上线",
      "metric": "88%",
      "priority": "高"
    },
    {
      "key": "lporienteering-2",
      "name": "线索打卡点（GPS/二维码）",
      "owner": "管理员",
      "status": "排期中",
      "metric": "31 单",
      "priority": "中"
    },
    {
      "key": "lporienteering-3",
      "name": "团队报名与排名",
      "owner": "服务台",
      "status": "巡检中",
      "metric": "10 项",
      "priority": "低"
    },
    {
      "key": "lporienteering-4",
      "name": "积分兑换商城",
      "owner": "财务组",
      "status": "优化中",
      "metric": "4 级",
      "priority": "高"
    },
    {
      "key": "lporienteering-5",
      "name": "历史线路收藏",
      "owner": "审核组",
      "status": "可导出",
      "metric": "28 条",
      "priority": "中"
    }
  ]
}

from django.db import IntegrityError, transaction
from django.utils import timezone

from .errors import ActivityNotFound, CheckinRejected, ERROR_MESSAGES
from .models import Activity, Checkin, Checkpoint, Team


def get_overview():
    return OVERVIEW


# ---------------------------------------------------------------------------
# 活动打卡与实时排行榜
# ---------------------------------------------------------------------------

def format_duration(total_seconds):
    """把秒数格式化为「1小时10分05秒」式的中文用时。"""
    total_seconds = max(0, int(total_seconds))
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}小时{minutes:02d}分{seconds:02d}秒"
    if minutes:
        return f"{minutes}分{seconds:02d}秒"
    return f"{seconds}秒"


def _fmt_dt(value):
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M")


def _activity_status(activity, now):
    if now < activity.starts_at:
        return "upcoming", "未开始"
    if now > activity.ends_at:
        return "ended", "已结束"
    return "ongoing", "进行中"


def _serialize_activity(activity, now=None):
    now = now or timezone.now()
    code, text = _activity_status(activity, now)
    return {
        "id": activity.id,
        "name": activity.name,
        "description": activity.description,
        "status": code,
        "statusText": text,
        "startsAt": activity.starts_at.isoformat(),
        "endsAt": activity.ends_at.isoformat(),
    }


def _serialize_checkpoint(checkpoint):
    return {
        "id": checkpoint.id,
        "seq": checkpoint.seq,
        "name": checkpoint.name,
        "clue": checkpoint.clue,
    }


def _load_activity(activity_id):
    try:
        return Activity.objects.get(id=activity_id)
    except (Activity.DoesNotExist, ValueError, TypeError):
        raise ActivityNotFound(ERROR_MESSAGES["activity_not_found"])


def _team_progress(team, checkpoints):
    """汇总单支队伍的打卡进度；完成全部打卡点时给出总用时。"""
    checkins = sorted(team.checkins.all(), key=lambda item: (item.checked_at, item.id))
    done_ids = {item.checkpoint_id for item in checkins}
    seq_by_id = {cp.id: cp.seq for cp in checkpoints}
    total = len(checkpoints)
    next_cp = next((cp for cp in checkpoints if cp.id not in done_ids), None)

    if total and len(done_ids) >= total:
        status, status_text = "completed", "已完成"
    elif done_ids:
        status, status_text = "in_progress", "进行中"
    else:
        status, status_text = "not_started", "未出发"

    progress = {
        "id": team.id,
        "name": team.name,
        "completedCount": len(done_ids),
        "totalCount": total,
        "status": status,
        "statusText": status_text,
        "nextCheckpointId": next_cp.id if next_cp else None,
        "nextCheckpointSeq": next_cp.seq if next_cp else None,
        "nextCheckpointName": next_cp.name if next_cp else None,
        "checkins": [
            {
                "checkpointId": item.checkpoint_id,
                "seq": seq_by_id.get(item.checkpoint_id),
                "checkedAt": item.checked_at.isoformat(),
            }
            for item in checkins
        ],
        "totalSeconds": None,
        "totalText": None,
        "finishedAt": None,
    }

    if status == "completed":
        # 总用时 = 最后一次有效打卡时间 - 第一次有效打卡时间。
        seconds = int((checkins[-1].checked_at - checkins[0].checked_at).total_seconds())
        progress["totalSeconds"] = seconds
        progress["totalText"] = format_duration(seconds)
        progress["finishedAt"] = checkins[-1].checked_at.isoformat()
    return progress


def list_activities():
    now = timezone.now()
    activities = Activity.objects.prefetch_related("checkpoints", "teams").all()
    return {
        "activities": [
            {
                **_serialize_activity(activity, now),
                "checkpointCount": len(activity.checkpoints.all()),
                "teamCount": len(activity.teams.all()),
            }
            for activity in activities
        ]
    }


def get_route_detail(activity_id):
    """线路详情：活动信息 + 按顺序排列的打卡点。"""
    activity = _load_activity(activity_id)
    checkpoints = list(activity.checkpoints.all())
    return {
        "activity": _serialize_activity(activity),
        "checkpoints": [_serialize_checkpoint(cp) for cp in checkpoints],
    }


def get_progress(activity_id):
    """各队伍打卡进度（含每队下一个应打卡点）。"""
    activity = _load_activity(activity_id)
    checkpoints = list(activity.checkpoints.all())
    teams = activity.teams.prefetch_related("checkins").all()
    return {
        "activity": _serialize_activity(activity),
        "checkpoints": [_serialize_checkpoint(cp) for cp in checkpoints],
        "teams": [_team_progress(team, checkpoints) for team in teams],
    }


def get_leaderboard(activity_id):
    """实时排行榜：仅完赛队伍上榜，按总用时从短到长排序。"""
    activity = _load_activity(activity_id)
    checkpoints = list(activity.checkpoints.all())
    teams = activity.teams.prefetch_related("checkins").all()

    entries = []
    for team in teams:
        progress = _team_progress(team, checkpoints)
        if progress["status"] != "completed":
            continue
        entries.append(
            {
                "teamId": team.id,
                "teamName": team.name,
                "status": "completed",
                "statusText": "已完成",
                "totalSeconds": progress["totalSeconds"],
                "totalText": progress["totalText"],
                "finishedAt": progress["finishedAt"],
            }
        )
    entries.sort(key=lambda item: (item["totalSeconds"], item["finishedAt"], item["teamId"]))
    for rank, entry in enumerate(entries, start=1):
        entry["rank"] = rank

    return {
        "activity": _serialize_activity(activity),
        "generatedAt": timezone.now().isoformat(),
        "entries": entries,
    }


def submit_checkin(activity_id, team_id, checkpoint_id):
    """提交一次打卡。

    规则：活动窗口外拒绝；同一打卡点只认第一次有效打卡；必须按线路顺序
    从第一个点开始依次打卡，跳点拒绝。所有拒绝都返回中文原因。
    """
    activity = _load_activity(activity_id)
    now = timezone.now()

    if now < activity.starts_at:
        raise CheckinRejected(f"活动尚未开始，打卡通道将于 {_fmt_dt(activity.starts_at)} 开启")
    if now > activity.ends_at:
        raise CheckinRejected(f"活动已结束（结束时间 {_fmt_dt(activity.ends_at)}），打卡无效")

    team = Team.objects.filter(id=team_id, activity=activity).first()
    if team is None:
        raise CheckinRejected("队伍不存在或未报名该活动")
    checkpoint = Checkpoint.objects.filter(id=checkpoint_id, activity=activity).first()
    if checkpoint is None:
        raise CheckinRejected("打卡点不属于该活动线路")

    if Checkin.objects.filter(team=team, checkpoint=checkpoint).exists():
        raise CheckinRejected(
            f"第{checkpoint.seq}点「{checkpoint.name}」已有首次有效打卡，"
            "同一打卡点只认第一次有效打卡，重复提交无效"
        )

    checkpoints = list(activity.checkpoints.all())
    done_ids = set(
        Checkin.objects.filter(team=team, checkpoint__activity=activity).values_list(
            "checkpoint_id", flat=True
        )
    )
    next_cp = next((cp for cp in checkpoints if cp.id not in done_ids), None)
    if next_cp is None:
        raise CheckinRejected("该队伍已完成全部打卡点，无需再次打卡")
    if checkpoint.id != next_cp.id:
        raise CheckinRejected(
            f"请按线路顺序打卡：需先完成第{next_cp.seq}点「{next_cp.name}」，"
            f"暂不能打卡第{checkpoint.seq}点「{checkpoint.name}」"
        )

    try:
        with transaction.atomic():
            checkin = Checkin.objects.create(team=team, checkpoint=checkpoint, checked_at=now)
    except IntegrityError:
        # 并发下唯一约束兜底：同一打卡点仍只认第一次有效打卡。
        raise CheckinRejected(
            f"第{checkpoint.seq}点「{checkpoint.name}」已有首次有效打卡，重复提交无效"
        )

    fresh_team = Team.objects.prefetch_related("checkins").get(id=team.id)
    progress = _team_progress(fresh_team, checkpoints)
    completed = progress["status"] == "completed"

    message = f"打卡成功：第{checkpoint.seq}点「{checkpoint.name}」"
    if completed:
        message += f"，全部打卡点已完成，总用时 {progress['totalText']}"

    return {
        "accepted": True,
        "message": message,
        "checkin": {
            "checkpointId": checkpoint.id,
            "seq": checkpoint.seq,
            "checkedAt": checkin.checked_at.isoformat(),
        },
        "progress": progress,
        "result": {
            "completed": completed,
            "totalSeconds": progress["totalSeconds"],
            "totalText": progress["totalText"],
        },
    }
