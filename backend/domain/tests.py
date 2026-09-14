import threading
from datetime import timedelta

from django.db import connection
from django.test import Client, TestCase, TransactionTestCase
from django.utils import timezone

from .models import Activity, Checkpoint, Checkin, Team


def make_activity(name, starts_delta, ends_delta):
    now = timezone.now()
    return Activity.objects.create(
        name=name,
        starts_at=now + starts_delta,
        ends_at=now + ends_delta,
    )


class CheckinFlowTests(TestCase):
    """打卡规则与实时排行榜：标识校验、顺序、重复、时间窗、总用时与榜单。"""

    def setUp(self):
        self.activity = make_activity("测试定向赛", timedelta(hours=-2), timedelta(hours=2))
        self.cps = [
            Checkpoint.objects.create(activity=self.activity, seq=seq, name=f"CP{seq}")
            for seq in (1, 2, 3)
        ]
        self.team = Team.objects.create(activity=self.activity, name="测试队")
        self.other_team = Team.objects.create(activity=self.activity, name="对手队")
        self.client = Client()
        self.url = f"/api/activities/{self.activity.id}/checkins"

    def post_checkin(self, team, checkpoint):
        return self.client.post(
            self.url,
            data={"teamId": team.id, "checkpointId": checkpoint.id},
            content_type="application/json",
        )

    def test_overview_entry_kept(self):
        response = self.client.get("/api/overview")
        self.assertEqual(response.status_code, 200, "原有总览入口必须保持可用")
        self.assertEqual(response.json()["appCode"], "lporienteering")

    def test_route_detail_lists_checkpoints_in_order(self):
        response = self.client.get(f"/api/activities/{self.activity.id}")
        self.assertEqual(response.status_code, 200)
        seqs = [item["seq"] for item in response.json()["checkpoints"]]
        self.assertEqual(seqs, [1, 2, 3], "线路详情必须按顺序返回打卡点")

    def test_team_must_start_from_first_checkpoint(self):
        before = Checkin.objects.count()
        response = self.post_checkin(self.team, self.cps[1])
        self.assertEqual(response.status_code, 409, "首个打卡点之前不允许跳点")
        self.assertIn("顺序", response.json()["reason"], "跳点拒绝时必须说明顺序原因")
        self.assertEqual(Checkin.objects.count(), before, "跳点被拒绝时不允许发生任何写入")

    def test_first_valid_checkin_accepted(self):
        response = self.post_checkin(self.team, self.cps[0])
        self.assertEqual(response.status_code, 201, "从第一个点开始的有效打卡必须成功")
        payload = response.json()
        self.assertTrue(payload["accepted"])
        self.assertEqual(payload["progress"]["nextCheckpointSeq"], 2)

    def test_duplicate_checkin_rejected(self):
        self.assertEqual(self.post_checkin(self.team, self.cps[0]).status_code, 201)
        before = Checkin.objects.count()
        response = self.post_checkin(self.team, self.cps[0])
        self.assertEqual(response.status_code, 409, "同一打卡点重复提交必须被拒绝")
        self.assertIn("重复", response.json()["reason"], "重复拒绝时必须说明原因")
        self.assertEqual(Checkin.objects.count(), before, "重复提交被拒绝时不允许发生任何写入")

    def test_skip_checkpoint_rejected(self):
        self.assertEqual(self.post_checkin(self.team, self.cps[0]).status_code, 201)
        before = Checkin.objects.count()
        response = self.post_checkin(self.team, self.cps[2])
        self.assertEqual(response.status_code, 409, "跳过中间点的打卡必须被拒绝")
        self.assertIn("顺序", response.json()["reason"], "跳点拒绝时必须说明顺序原因")
        self.assertEqual(Checkin.objects.count(), before, "跳点被拒绝时不允许发生任何写入")

    def test_completion_generates_total_time(self):
        base = timezone.now() - timedelta(minutes=30)
        for index, cp in enumerate(self.cps):
            Checkin.objects.create(
                team=self.team, checkpoint=cp, checked_at=base + timedelta(minutes=10 * index)
            )
        response = self.client.get(f"/api/activities/{self.activity.id}/progress")
        team = next(t for t in response.json()["teams"] if t["id"] == self.team.id)
        self.assertEqual(team["status"], "completed", "完成全部打卡点后状态必须为已完成")
        self.assertEqual(team["totalSeconds"], 20 * 60, "总用时必须等于末次打卡减首次打卡")
        self.assertEqual(team["totalText"], "20分00秒")

    def test_leaderboard_orders_by_total_time_and_skips_unfinished(self):
        base = timezone.now() - timedelta(hours=1)

        def finish(team, minutes):
            for index, cp in enumerate(self.cps):
                Checkin.objects.create(
                    team=team,
                    checkpoint=cp,
                    checked_at=base + timedelta(minutes=minutes * index / 2),
                )

        finish(self.other_team, 40)  # 总用时 40 分钟
        finish(self.team, 20)  # 总用时 20 分钟，应排第一
        Checkin.objects.create(
            team=Team.objects.create(activity=self.activity, name="未完赛队"),
            checkpoint=self.cps[0],
            checked_at=base,
        )

        response = self.client.get(f"/api/activities/{self.activity.id}/leaderboard")
        entries = response.json()["entries"]
        self.assertEqual(
            [e["teamName"] for e in entries],
            ["测试队", "对手队"],
            "榜单必须按总用时从短到长排序",
        )
        self.assertEqual([e["rank"] for e in entries], [1, 2])
        self.assertEqual(entries[0]["totalSeconds"], 20 * 60)
        self.assertEqual(entries[0]["statusText"], "已完成")
        self.assertNotIn("未完赛队", [e["teamName"] for e in entries], "未完成队伍不允许上榜")

    def test_checkin_after_activity_end_rejected(self):
        ended = make_activity("已结束活动", timedelta(days=-2), timedelta(days=-1))
        cp = Checkpoint.objects.create(activity=ended, seq=1, name="CP1")
        team = Team.objects.create(activity=ended, name="迟到队")
        before = Checkin.objects.count()
        response = self.client.post(
            f"/api/activities/{ended.id}/checkins",
            data={"teamId": team.id, "checkpointId": cp.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409, "活动结束后继续打卡必须被拒绝")
        self.assertIn("已结束", response.json()["reason"], "拒绝时必须说明活动已结束")
        self.assertEqual(Checkin.objects.count(), before, "活动结束后打卡不允许发生任何写入")

    def test_checkin_before_activity_start_rejected(self):
        upcoming = make_activity("未开始活动", timedelta(days=1), timedelta(days=2))
        cp = Checkpoint.objects.create(activity=upcoming, seq=1, name="CP1")
        team = Team.objects.create(activity=upcoming, name="抢先队")
        before = Checkin.objects.count()
        response = self.client.post(
            f"/api/activities/{upcoming.id}/checkins",
            data={"teamId": team.id, "checkpointId": cp.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409, "活动未开始时打卡必须被拒绝")
        self.assertIn("尚未开始", response.json()["reason"], "拒绝时必须说明活动尚未开始")
        self.assertEqual(Checkin.objects.count(), before, "活动未开始打卡不允许发生任何写入")

    def test_progress_consistent_after_reload(self):
        # 模拟刷新：打卡后重新拉取进度与榜单，状态应保持一致。
        self.assertEqual(self.post_checkin(self.team, self.cps[0]).status_code, 201)
        progress = self.client.get(f"/api/activities/{self.activity.id}/progress").json()
        team = next(t for t in progress["teams"] if t["id"] == self.team.id)
        self.assertEqual(team["completedCount"], 1, "刷新后打卡进度必须保持一致")
        self.assertEqual(team["nextCheckpointSeq"], 2)
        leaderboard = self.client.get(
            f"/api/activities/{self.activity.id}/leaderboard"
        ).json()
        self.assertEqual(leaderboard["entries"], [], "未完赛队伍不允许出现在榜单中")

    def test_malformed_ids_return_parameter_error(self):
        # 布尔、0、负数、字符串、浮点、缺失等畸形标识一律 400，不得命中已有记录。
        valid_team = self.team.id
        valid_cp = self.cps[0].id
        malformed_payloads = [
            {"teamId": True, "checkpointId": valid_cp},
            {"teamId": False, "checkpointId": valid_cp},
            {"teamId": valid_team, "checkpointId": True},
            {"teamId": 0, "checkpointId": valid_cp},
            {"teamId": valid_team, "checkpointId": 0},
            {"teamId": -1, "checkpointId": valid_cp},
            {"teamId": valid_team, "checkpointId": -2},
            {"teamId": str(valid_team), "checkpointId": valid_cp},
            {"teamId": valid_team, "checkpointId": str(valid_cp)},
            {"teamId": valid_team + 0.5, "checkpointId": valid_cp},
            {"teamId": None, "checkpointId": valid_cp},
            {"checkpointId": valid_cp},
            {"teamId": valid_team},
            {},
        ]
        before = Checkin.objects.count()
        for payload in malformed_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(self.url, data=payload, content_type="application/json")
                self.assertEqual(response.status_code, 400, "畸形标识必须返回 400 参数错误")
                self.assertIn("参数错误", response.json()["reason"], "必须返回明确的参数错误原因")
        self.assertEqual(Checkin.objects.count(), before, "畸形标识请求不允许发生任何写入")

    def test_boolean_true_does_not_alias_existing_team(self):
        # true 不得被当成 id=1 命中已有队伍与打卡点。
        before = Checkin.objects.count()
        response = self.client.post(
            self.url,
            data={"teamId": True, "checkpointId": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400, "布尔标识必须返回 400 参数错误")
        self.assertEqual(Checkin.objects.count(), before, "布尔标识不允许命中任何已有记录")


class ConcurrentCheckinTests(TransactionTestCase):
    """并发提交：数据库唯一约束兜底，最多只有合法顺序的一笔成功。

    使用 TransactionTestCase（提交后对其他连接可见）+ 文件型测试库，
    让多个线程真实并发地打到同一个数据库上。
    """

    def setUp(self):
        self.activity = make_activity("并发测试赛", timedelta(hours=-1), timedelta(hours=1))
        self.cps = [
            Checkpoint.objects.create(activity=self.activity, seq=seq, name=f"CP{seq}")
            for seq in (1, 2, 3)
        ]
        self.team = Team.objects.create(activity=self.activity, name="并发队")
        self.url = f"/api/activities/{self.activity.id}/checkins"

    def _post_concurrently(self, payloads):
        """用屏障让多个线程尽量同时提交，返回与 payloads 顺序对齐的响应列表。"""
        barrier = threading.Barrier(len(payloads))
        responses = [None] * len(payloads)
        errors = []

        def worker(index, payload):
            try:
                barrier.wait(timeout=10)
                responses[index] = Client().post(
                    self.url, data=payload, content_type="application/json"
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker, args=(i, p)) for i, p in enumerate(payloads)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertFalse(errors, f"并发请求出现异常: {errors!r}")
        self.assertTrue(all(r is not None for r in responses), "存在超时未完成的并发请求")
        return responses

    def test_concurrent_same_checkpoint_allows_single_success(self):
        payload = {"teamId": self.team.id, "checkpointId": self.cps[0].id}
        responses = self._post_concurrently([dict(payload) for _ in range(6)])
        statuses = [r.status_code for r in responses]
        self.assertEqual(statuses.count(201), 1, "并发提交同一打卡点必须恰好一笔成功")
        self.assertEqual(
            statuses.count(409), len(responses) - 1, "其余并发提交必须全部被拒绝"
        )
        self.assertEqual(
            Checkin.objects.filter(team=self.team).count(),
            1,
            "并发后同一打卡点只允许落库一笔",
        )

    def test_concurrent_mixed_checkpoints_keep_ordered_prefix(self):
        # 同一队伍对不同点位同时提交：无论时序如何交错，
        # 落库结果都必须是从第 1 点开始的连续序列（无跳点、无重复）。
        payloads = [
            {"teamId": self.team.id, "checkpointId": cp.id} for cp in self.cps for _ in (0, 1)
        ]
        responses = self._post_concurrently(payloads)
        succeeded = [r for r in responses if r.status_code == 201]
        self.assertTrue(succeeded, "并发提交中至少应有一笔合法打卡成功")
        seqs = sorted(
            Checkin.objects.filter(team=self.team).values_list("checkpoint__seq", flat=True)
        )
        self.assertEqual(
            seqs,
            list(range(1, len(seqs) + 1)),
            "并发落库结果必须是从第1点开始的连续序列，不允许跳点或重复写入",
        )
