from datetime import datetime, timedelta, timezone

from django.db import migrations

# 固定东八区偏移，避免依赖容器内 tzdata。
CST = timezone(timedelta(hours=8))

AUTUMN = "金秋城市定向挑战赛"
SUMMER = "仲夏夜城市定向赛"


def seed(apps, schema_editor):
    Activity = apps.get_model("domain", "Activity")
    Checkpoint = apps.get_model("domain", "Checkpoint")
    Team = apps.get_model("domain", "Team")
    Checkin = apps.get_model("domain", "Checkin")

    # 进行中的活动：用于演示顺序打卡、跳点/重复拒绝和实时榜单。
    autumn = Activity.objects.create(
        name=AUTUMN,
        description="沿江老城线，4 个打卡点，需按顺序完成，完成后生成总用时并进入实时排行榜。",
        starts_at=datetime(2026, 9, 1, 8, 0, tzinfo=CST),
        ends_at=datetime(2026, 12, 31, 22, 0, tzinfo=CST),
    )
    autumn_points = [
        ("起点·滨江公园北门", "在江风与汽笛声中出发，于北门石碑旁完成首次打卡。"),
        ("CP1·老码头钟楼", "钟楼东侧台阶设有打卡旗，整点钟声为证。"),
        ("CP2·梧桐书院", "书院天井的百年梧桐下藏有二维码，扫码即打卡。"),
        ("终点·云顶观景台", "登顶后在观景台栏杆处完成最后一次打卡，生成总用时。"),
    ]
    autumn_cps = [
        Checkpoint.objects.create(activity=autumn, seq=seq, name=name, clue=clue)
        for seq, (name, clue) in enumerate(autumn_points, start=1)
    ]
    autumn_teams = {
        name: Team.objects.create(activity=autumn, name=name)
        for name in ["疾风队", "山猫队", "繁星队", "慢游者小队"]
    }

    def punch(team, cp_seq, day, hour, minute):
        Checkin.objects.create(
            team=autumn_teams[team],
            checkpoint=autumn_cps[cp_seq - 1],
            checked_at=datetime(2026, 9, day, hour, minute, tzinfo=CST),
        )

    # 山猫队已完成全程：总用时 1 小时 10 分，登上榜单。
    punch("山猫队", 1, 12, 9, 5)
    punch("山猫队", 2, 12, 9, 20)
    punch("山猫队", 3, 12, 9, 50)
    punch("山猫队", 4, 12, 10, 15)
    # 疾风队完成前两点，下一个应打 CP2·梧桐书院。
    punch("疾风队", 1, 12, 9, 0)
    punch("疾风队", 2, 12, 9, 25)
    # 繁星队只打了起点。
    punch("繁星队", 1, 12, 9, 10)
    # 慢游者小队尚未出发，需从第一个点开始。

    # 已结束的活动：用于演示活动结束后打卡被拒绝，以及历史榜单。
    summer = Activity.objects.create(
        name=SUMMER,
        description="已结束的夜间定向体验赛，线路与成绩保留供复盘参考。",
        starts_at=datetime(2026, 6, 1, 18, 0, tzinfo=CST),
        ends_at=datetime(2026, 6, 1, 23, 0, tzinfo=CST),
    )
    summer_points = [
        ("起点·南岸音乐广场", "夜幕降临时在音乐广场主舞台侧集合出发。"),
        ("CP1·灯塔栈道", "沿江栈道尽头灯塔下的打卡点。"),
        ("终点·摩天轮广场", "摩天轮下完成冲刺打卡。"),
    ]
    summer_cps = [
        Checkpoint.objects.create(activity=summer, seq=seq, name=name, clue=clue)
        for seq, (name, clue) in enumerate(summer_points, start=1)
    ]
    summer_teams = {
        name: Team.objects.create(activity=summer, name=name)
        for name in ["追风少年", "夜行者"]
    }

    def punch_summer(team, cp_seq, hour, minute):
        Checkin.objects.create(
            team=summer_teams[team],
            checkpoint=summer_cps[cp_seq - 1],
            checked_at=datetime(2026, 6, 1, hour, minute, tzinfo=CST),
        )

    # 追风少年 55 分钟完赛，夜行者 75 分钟完赛。
    punch_summer("追风少年", 1, 18, 10)
    punch_summer("追风少年", 2, 18, 40)
    punch_summer("追风少年", 3, 19, 5)
    punch_summer("夜行者", 1, 18, 5)
    punch_summer("夜行者", 2, 18, 50)
    punch_summer("夜行者", 3, 19, 20)


def unseed(apps, schema_editor):
    Activity = apps.get_model("domain", "Activity")
    Activity.objects.filter(name__in=[AUTUMN, SUMMER]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("domain", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
