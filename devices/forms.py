from django import forms

from common.models import LGA, State
from .models import Device

INPUT = "w-full px-3 py-2.5 rounded-lg border border-gray-300 text-sm text-[#1A1A1A] focus:border-[#1CABE2] focus:ring-1 focus:ring-[#1CABE2]/30 outline-none"
SELECT = INPUT + " bg-white"


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        exclude = ["uploaded_by", "created_at", "updated_at"]
        widgets = {
            "serial_number": forms.TextInput(attrs={"class": INPUT}),
            "imei_1": forms.TextInput(attrs={"class": INPUT, "placeholder": "15-digit IMEI"}),
            "imei_2": forms.TextInput(attrs={"class": INPUT, "placeholder": "15-digit IMEI"}),
            "device_type": forms.Select(attrs={"class": SELECT}),
            "brand": forms.TextInput(attrs={"class": INPUT}),
            "model_name": forms.TextInput(attrs={"class": INPUT}),
            "assigned_to": forms.Select(attrs={"class": SELECT}),
            "training": forms.Select(attrs={"class": SELECT}),
            "state": forms.Select(attrs={"class": SELECT}),
            "lga": forms.Select(attrs={"class": SELECT}),
            "status": forms.Select(attrs={"class": SELECT}),
            "condition": forms.Select(attrs={"class": SELECT}),
        }

    def __init__(self, *args, training=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["state"].queryset = State.objects.all()
        self.fields["lga"].queryset = LGA.objects.all()
        self.fields["state"].required = False
        self.fields["lga"].required = False
        self.fields["assigned_to"].required = False
        self.fields["training"].required = False

        # If linked to a training, lock state to training state
        if training:
            self.fields["training"].initial = training.pk
            self.fields["training"].widget = forms.HiddenInput()
            self.fields["state"].initial = training.state_id
            self.fields["state"].widget = forms.HiddenInput()
            if training.state:
                self.fields["lga"].queryset = LGA.objects.filter(state=training.state)


class DeviceBulkUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Expected columns: serial_number, imei_1, imei_2, device_type, brand, model_name",
        widget=forms.ClearableFileInput(attrs={"class": INPUT, "accept": ".csv"}),
    )

    def clean_csv_file(self):
        f = self.cleaned_data["csv_file"]
        if not f.name.endswith(".csv"):
            raise forms.ValidationError("Only CSV files are accepted.")
        return f


class DeviceAssignForm(forms.Form):
    participant = forms.IntegerField(widget=forms.HiddenInput())
    training = forms.IntegerField(widget=forms.HiddenInput(), required=False)
