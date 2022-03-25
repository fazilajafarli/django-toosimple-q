from django.contrib import admin
from django.contrib.messages.constants import SUCCESS
from django.template.defaultfilters import truncatechars
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

from .models import ScheduleExec, TaskExec
from .task import tasks_registry


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


@admin.register(TaskExec)
class TaskExecAdmin(ReadOnlyAdmin):
    list_display = [
        "icon",
        "task_name",
        "arguments_",
        "queue",
        "priority",
        "due_",
        "created_",
        "started_",
        "finished_",
        "replaced_by_",
        "result_",
    ]
    list_display_links = ["task_name"]
    list_filter = ["task_name", "queue", "state"]
    actions = ["action_requeue"]
    ordering = ["-created"]
    readonly_fields = ["result"]

    def arguments_(self, obj):
        return format_html(
            "{}<br/>{}",
            truncatechars(str(obj.args), 32),
            truncatechars(str(obj.kwargs), 32),
        )

    def result_(self, obj):
        return truncatechars(str(obj.result), 32)

    def due_(self, obj):
        return short_naturaltime(obj.due)

    def created_(self, obj):
        return short_naturaltime(obj.created)

    def started_(self, obj):
        return short_naturaltime(obj.started)

    def finished_(self, obj):
        return short_naturaltime(obj.finished)

    def replaced_by_(self, obj):
        if obj.replaced_by:
            return f"{obj.replaced_by.icon} [{obj.replaced_by.pk}]"

    def action_requeue(self, request, queryset):
        for task in queryset:
            tasks_registry[task.task_name].enqueue(*task.args, **task.kwargs)
        self.message_user(
            request, f"{queryset.count()} tasks successfully requeued...", level=SUCCESS
        )

    action_requeue.short_description = "Requeue task"


@admin.register(ScheduleExec)
class ScheduleExecAdmin(ReadOnlyAdmin):
    list_display = ["icon", "name", "last_check", "last_run_", "cron"]
    list_display_links = ["name"]
    ordering = ["last_check"]

    def last_run_(self, obj):
        if obj.last_run:
            app, model = obj.last_run._meta.app_label, obj.last_run._meta.model_name
            edit_link = reverse(f"admin:{app}_{model}_change", args=(obj.last_run_id,))
            return format_html('<a href="{}">{}</a>', edit_link, obj.last_run.icon)
        return "-"


def short_naturaltime(datetime):

    if datetime is None:
        return None

    delta = timezone.now() - datetime
    disps = [
        (60, "s"),
        (60 * 60, "m"),
        (60 * 60 * 24, "h"),
        (60 * 60 * 24 * 7, "D"),
        (60 * 60 * 24 * 30, "W"),
        (60 * 60 * 24 * 365, "M"),
        (float("inf"), "Y"),
    ]

    last_v = 1
    for threshold, abbr in disps:
        if abs(delta.seconds) < threshold:
            text = f"{delta.seconds // last_v}{abbr}"
            break
        last_v = threshold

    shorttime = f"in&nbsp;{text}" if delta.seconds < 0 else f"{text}&nbsp;ago"

    return mark_safe(f'<span title="{escape(datetime)}">{shorttime}</span>')
