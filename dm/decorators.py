from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from trainings.models import TrainingAssignment


def dm_required(view_func):
    """Ensure user is a device manager with participant profile, training, and LGA."""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        user = request.user

        # Admins should use the admin interface
        if user.is_superuser or user.groups.filter(
            name__in=["UNICEF Admin", "National Admin", "State Admin"]
        ).exists():
            return redirect("dashboard")

        if not hasattr(user, "participant_profile") or user.participant_profile is None:
            return redirect("dashboard")

        dm_participant = user.participant_profile

        # Find their DM assignment (category with is_device_manager=True)
        dm_assignment = (
            TrainingAssignment.objects.filter(
                participant=dm_participant,
                training_category__is_device_manager=True,
            )
            .select_related("training", "training_category", "cluster")
            .first()
        )

        # Fallback: any assignment they have
        if not dm_assignment:
            dm_assignment = (
                TrainingAssignment.objects.filter(participant=dm_participant)
                .select_related("training", "training_category", "cluster")
                .first()
            )

        if not dm_assignment:
            return redirect("dashboard")

        request.dm_participant = dm_participant
        request.dm_training = dm_assignment.training
        request.dm_assignment = dm_assignment
        request.dm_lga = dm_participant.lga
        request.dm_cluster = dm_assignment.cluster

        return view_func(request, *args, **kwargs)

    return wrapper
