from django.contrib import admin

from trainings.models import Training, TrainingAssignment, TrainingCategory, TrainingCluster


class ClusterInline(admin.TabularInline):
    model = TrainingCluster
    extra = 1


class CategoryInline(admin.TabularInline):
    model = TrainingCategory
    extra = 1


class AssignmentInline(admin.TabularInline):
    model = TrainingAssignment
    extra = 1
    autocomplete_fields = ["participant"]


@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = ["title", "channel", "state", "destination", "modality", "training_days", "start_date", "end_date", "status"]
    list_filter = ["channel", "modality", "status", "state"]
    search_fields = ["title", "destination"]
    inlines = [CategoryInline, ClusterInline, AssignmentInline]


@admin.register(TrainingCategory)
class TrainingCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "training", "dsa_rate", "travel_mode"]
    list_filter = ["training"]


@admin.register(TrainingCluster)
class TrainingClusterAdmin(admin.ModelAdmin):
    list_display = ["name", "training"]
    list_filter = ["training"]


@admin.register(TrainingAssignment)
class TrainingAssignmentAdmin(admin.ModelAdmin):
    list_display = ["training", "participant", "role", "training_category", "cluster", "outbound_mode", "return_mode", "assigned_at"]
    list_filter = ["role", "training__channel", "training_category"]
