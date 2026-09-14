class AppError(Exception):
    pass


class ActivityNotFound(AppError):
    """活动不存在。"""


class CheckinRejected(AppError):
    """打卡被业务规则拒绝，message 即拒绝原因。"""


ERROR_MESSAGES = {
    "overview_unavailable": "Overview data is unavailable",
    "activity_not_found": "活动不存在",
}
