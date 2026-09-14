from django.urls import include, path

from domain.views import (
    activities_collection,
    activity_checkins,
    activity_detail,
    activity_leaderboard,
    activity_progress,
    health,
    overview,
)

# 活动打卡相关接口。
activity_patterns = [
    path("activities", activities_collection),
    path("activities/<int:activity_id>", activity_detail),
    path("activities/<int:activity_id>/progress", activity_progress),
    path("activities/<int:activity_id>/leaderboard", activity_leaderboard),
    path("activities/<int:activity_id>/checkins", activity_checkins),
]

# 同时注册带 /api 前缀与不带前缀的路径：
# 前端经 Nginx / Vite 代理访问 /api/...，代理会剥掉前缀后转发到后端。
urlpatterns = [
    path("health", health),
    path("api/health", health),
    path("overview", overview),
    path("api/overview", overview),
    path("", include(activity_patterns)),
    path("api/", include(activity_patterns)),
]
