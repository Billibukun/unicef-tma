from django import forms

from banks.models import Bank, BankAccount
from common.models import Channel
from participants.models import Participant

INPUT = "w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:border-unicef focus:ring-1 focus:ring-unicef outline-none"
SELECT = "w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:border-unicef focus:ring-1 focus:ring-unicef outline-none bg-white"


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = [
            "first_name", "last_name", "email", "phone",
            "channel", "channel_role", "health_organization",
            "origin", "state", "lga", "ward",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": INPUT, "placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"class": INPUT, "placeholder": "Last name"}),
            "email": forms.EmailInput(attrs={"class": INPUT, "placeholder": "Email address"}),
            "phone": forms.TextInput(attrs={"class": INPUT, "placeholder": "+234..."}),
            "channel": forms.Select(attrs={"class": SELECT, "x-model": "channelCode", "@change": "updateChannel($event)"}),
            "channel_role": forms.TextInput(attrs={"class": INPUT, "placeholder": "e.g. State ICT Officer"}),
            "health_organization": forms.TextInput(attrs={"class": INPUT, "placeholder": "Health organization name"}),
            "origin": forms.TextInput(attrs={"class": INPUT, "placeholder": "Traveling from"}),
            "state": forms.Select(attrs={"class": SELECT}),
            "lga": forms.Select(attrs={"class": SELECT}),
            "ward": forms.TextInput(attrs={"class": INPUT, "placeholder": "Ward"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["channel"].queryset = Channel.objects.filter(is_active=True)
        from common.models import State, LGA
        self.fields["state"].queryset = State.objects.all()
        self.fields["state"].required = False
        self.fields["lga"].queryset = LGA.objects.all()
        self.fields["lga"].required = False
        self.fields["health_organization"].required = False
        self.fields["ward"].required = False


class SelfRegistrationForm(forms.ModelForm):
    bank = forms.ModelChoiceField(
        queryset=Bank.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={"class": SELECT}),
        label="Bank",
    )
    account_number = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT, "placeholder": "10-digit account number"}),
        label="Account Number",
    )

    class Meta:
        model = Participant
        fields = [
            "first_name", "last_name", "email", "phone",
            "channel", "channel_role", "health_organization",
            "origin", "state", "lga", "ward",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": INPUT, "placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"class": INPUT, "placeholder": "Last name"}),
            "email": forms.EmailInput(attrs={"class": INPUT, "placeholder": "Email address"}),
            "phone": forms.TextInput(attrs={"class": INPUT, "placeholder": "+234..."}),
            "channel": forms.Select(attrs={"class": SELECT, "x-model": "channelCode", "@change": "updateChannel($event)"}),
            "channel_role": forms.TextInput(attrs={"class": INPUT, "placeholder": "e.g. State ICT Officer"}),
            "health_organization": forms.TextInput(attrs={"class": INPUT, "placeholder": "Health organization name"}),
            "origin": forms.TextInput(attrs={"class": INPUT, "placeholder": "Traveling from"}),
            "state": forms.Select(attrs={"class": SELECT}),
            "lga": forms.Select(attrs={"class": SELECT}),
            "ward": forms.TextInput(attrs={"class": INPUT, "placeholder": "Ward"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["channel"].queryset = Channel.objects.filter(is_active=True)
        from common.models import State, LGA
        self.fields["state"].queryset = State.objects.all()
        self.fields["state"].required = False
        self.fields["lga"].queryset = LGA.objects.all()
        self.fields["lga"].required = False

    def clean(self):
        cleaned = super().clean()
        bank = cleaned.get("bank")
        account_number = cleaned.get("account_number")
        if bank and not account_number:
            self.add_error("account_number", "Account number is required when a bank is selected.")
        if account_number and not bank:
            self.add_error("bank", "Please select a bank.")
        if account_number and len(account_number) != 10:
            self.add_error("account_number", "Account number must be exactly 10 digits.")
        return cleaned

    def save(self, commit: bool = True) -> Participant:
        participant = super().save(commit=commit)
        bank = self.cleaned_data.get("bank")
        account_number = self.cleaned_data.get("account_number")
        if bank and account_number:
            BankAccount.objects.update_or_create(
                participant=participant,
                defaults={"bank": bank, "account_number": account_number},
            )
        return participant


class ParticipantImportForm(forms.Form):
    file = forms.FileField(
        label="CSV or Excel file",
        help_text="Upload a .csv or .xlsx file with participant data.",
        widget=forms.FileInput(attrs={"class": "file-input file-input-bordered w-full", "accept": ".csv,.xlsx,.xls"}),
    )
