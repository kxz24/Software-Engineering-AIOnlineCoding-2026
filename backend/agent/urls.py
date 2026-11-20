from django.urls import path

from . import views

urlpatterns = [
    path("api/v1/agent/capabilities", views.AgentCapabilitiesView.as_view(),
         name="agent_capabilities"),
    path("api/v1/agent/sessions", views.AgentSessionView.as_view(),
         name="agent_sessions"),
    path("api/v1/agent/sessions/<int:session_id>/messages",
         views.AgentMessagesView.as_view(), name="agent_messages"),
    path("api/v1/agent/sessions/<int:session_id>/changes",
         views.AgentChangeListView.as_view(), name="agent_changes"),
    path("api/v1/agent/sessions/<int:session_id>/transcript",
         views.AgentSessionTranscriptView.as_view(), name="agent_transcript"),
    path("api/v1/agent/changes/<int:change_id>/revert",
         views.AgentChangeRevertView.as_view(), name="agent_change_revert"),
    path("api/v1/agent/workspace", views.AgentWorkspaceView.as_view(),
         name="agent_workspace"),
    path("api/v1/exams/<int:exam_id>/agent/sessions",
         views.AgentExamSessionsView.as_view(), name="agent_exam_sessions"),
    path("api/v1/exams/<int:exam_id>/agent/summary",
         views.AgentExamSummaryView.as_view(), name="agent_exam_summary"),
]
