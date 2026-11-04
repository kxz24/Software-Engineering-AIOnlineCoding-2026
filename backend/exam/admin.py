from django.contrib import admin

from .models import Exam, ExamCandidate, ExamProblem, Submission

# Register your models here.


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "course", "status", "start_time", "end_time", "updated")
    list_filter = ("status",)
    search_fields = ("title", "course")


@admin.register(ExamProblem)
class ExamProblemAdmin(admin.ModelAdmin):
    list_display = ("id", "exam", "problem", "order", "score")


@admin.register(ExamCandidate)
class ExamCandidateAdmin(admin.ModelAdmin):
    list_display = ("id", "exam", "student", "added_at")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "exam", "problem", "student", "status", "created")
    list_filter = ("status",)
