from django import forms

from .models import Training, TrainingAssignment

INPUT = "w-full px-3 py-2.5 rounded-lg border border-gray-300 text-sm text-[#1A1A1A] focus:border-[#1CABE2] focus:ring-1 focus:ring-[#1CABE2]/30 outline-none transition-colors"
SELECT = INPUT + " bg-white"
TEXTAREA = INPUT


class TrainingForm(forms.ModelForm):
    class Meta:
        model = Training
        exclude = ["created_by", "created_at", "updated_at"]
        widgets = {
            "title": forms.TextInput(attrs={"class": INPUT, "placeholder": "Training title"}),
            "description": forms.Textarea(attrs={"class": TEXTAREA, "rows": 3, "placeholder": "Optional description"}),
            "implementing_partner": forms.TextInput(attrs={"class": INPUT, "placeholder": "e.g. NPC HQ Abuja"}),
            "responsible_officer": forms.TextInput(attrs={"class": INPUT, "placeholder": "Responsible programme officer(s)"}),
            "channel": forms.Select(attrs={"class": SELECT}),
            "state": forms.Select(attrs={"class": SELECT}),
            "destination": forms.TextInput(attrs={"class": INPUT, "placeholder": "Training venue/location"}),
            "modality": forms.Select(attrs={"class": SELECT}),
            "training_days": forms.NumberInput(attrs={"class": INPUT, "min": "1"}),
            "start_date": forms.DateInput(attrs={"class": INPUT, "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": INPUT, "type": "date"}),
            "status": forms.Select(attrs={"class": SELECT}),
        }


class TrainingAssignmentForm(forms.ModelForm):
    class Meta:
        model = TrainingAssignment
        fields = ["training", "participant", "training_category", "cluster", "role"]
        widgets = {
            "training": forms.Select(attrs={"class": SELECT}),
            "participant": forms.Select(attrs={"class": SELECT}),
            "training_category": forms.Select(attrs={"class": SELECT}),
            "cluster": forms.Select(attrs={"class": SELECT}),
            "role": forms.Select(attrs={"class": SELECT}),
        }
