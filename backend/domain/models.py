from django.db import models


class Activity(models.Model):
    """一场定向越野活动，打卡只在活动时间窗内有效。"""

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-starts_at", "id"]

    def __str__(self):
        return self.name


class Checkpoint(models.Model):
    """线路上的打卡点，seq 决定必须按序打卡。"""

    activity = models.ForeignKey(Activity, related_name="checkpoints", on_delete=models.CASCADE)
    seq = models.PositiveIntegerField()
    name = models.CharField(max_length=120)
    clue = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["seq", "id"]
        constraints = [
            models.UniqueConstraint(fields=["activity", "seq"], name="uniq_checkpoint_seq_per_activity"),
        ]

    def __str__(self):
        return f"{self.activity.name} #{self.seq} {self.name}"


class Team(models.Model):
    """报名某场活动的队伍。"""

    activity = models.ForeignKey(Activity, related_name="teams", on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["activity", "name"], name="uniq_team_name_per_activity"),
        ]

    def __str__(self):
        return self.name


class Checkin(models.Model):
    """一次有效打卡。同一队伍同一打卡点只保留第一次有效记录。"""

    team = models.ForeignKey(Team, related_name="checkins", on_delete=models.CASCADE)
    checkpoint = models.ForeignKey(Checkpoint, related_name="checkins", on_delete=models.CASCADE)
    checked_at = models.DateTimeField()

    class Meta:
        ordering = ["checked_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["team", "checkpoint"], name="uniq_checkin_per_team_checkpoint"),
        ]

    def __str__(self):
        return f"{self.team.name} @ {self.checkpoint.name}"
