import json

from django.http import JsonResponse

from . import services
from .errors import ActivityNotFound, CheckinRejected


def health(_request):
    return JsonResponse({"status": "ok"})


def overview(_request):
    return JsonResponse(services.get_overview())


def _method_not_allowed():
    return JsonResponse({"accepted": False, "reason": "请求方法不支持"}, status=405)


def _not_found(exc):
    return JsonResponse({"accepted": False, "reason": str(exc)}, status=404)


def _is_positive_int(value):
    # bool 是 int 的子类，必须显式排除，否则 true/false 会被当成 1/0 命中已有记录。
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def activities_collection(request):
    if request.method != "GET":
        return _method_not_allowed()
    return JsonResponse(services.list_activities())


def activity_detail(request, activity_id):
    if request.method != "GET":
        return _method_not_allowed()
    try:
        return JsonResponse(services.get_route_detail(activity_id))
    except ActivityNotFound as exc:
        return _not_found(exc)


def activity_progress(request, activity_id):
    if request.method != "GET":
        return _method_not_allowed()
    try:
        return JsonResponse(services.get_progress(activity_id))
    except ActivityNotFound as exc:
        return _not_found(exc)


def activity_leaderboard(request, activity_id):
    if request.method != "GET":
        return _method_not_allowed()
    try:
        return JsonResponse(services.get_leaderboard(activity_id))
    except ActivityNotFound as exc:
        return _not_found(exc)


def activity_checkins(request, activity_id):
    if request.method != "POST":
        return _method_not_allowed()

    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"accepted": False, "reason": "请求体不是有效的 JSON"}, status=400)

    team_id = body.get("teamId")
    checkpoint_id = body.get("checkpointId")
    if not (_is_positive_int(team_id) and _is_positive_int(checkpoint_id)):
        return JsonResponse(
            {"accepted": False, "reason": "参数错误：teamId 与 checkpointId 必须为正整数"},
            status=400,
        )

    try:
        payload = services.submit_checkin(activity_id, team_id, checkpoint_id)
    except ActivityNotFound as exc:
        return _not_found(exc)
    except CheckinRejected as exc:
        return JsonResponse({"accepted": False, "reason": str(exc)}, status=409)
    return JsonResponse(payload, status=201)
