from django import forms

from banks.models import Bank, BankAccount


class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ["participant", "bank", "account_number"]
        widgets = {
            "participant": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "bank": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "account_number": forms.TextInput(attrs={
                "class": "input input-bordered w-full",
                "placeholder": "10-digit account number",
                "maxlength": "10",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["bank"].queryset = Bank.objects.filter(is_active=True)

    def clean_account_number(self) -> str:
        account_number = self.cleaned_data["account_number"]
        if len(account_number) != 10 or not account_number.isdigit():
            raise forms.ValidationError("Account number must be exactly 10 digits.")
        return account_number
