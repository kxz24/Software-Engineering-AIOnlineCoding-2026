from django.contrib import admin

from .models import Problem, TestSample


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "type", "language", "difficulty", "created_by", "updated")
    list_filter = ("type", "language", "difficulty")
    search_fields = ("title", "description")


@admin.register(TestSample)
class TestSampleAdmin(admin.ModelAdmin):
    list_display = ("id", "problem", "name", "is_sample", "created")
    list_filter = ("is_sample",)
    search_fields = ("problem__title", "name")
