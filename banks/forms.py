from django import forms

from banks.models import Bank, BankAccount


TW_SELECT = "w-full px-3 py-2 rounded-lg border border-gray-300 text-sm bg-white focus:border-[#1CABE2] outline-none"
TW_INPUT = "w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:border-[#1CABE2] outline-none"


class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ["participant", "bank", "account_number", "is_proxy", "proxy_name"]
        widgets = {
            "participant": forms.Select(attrs={"class": TW_SELECT}),
            "bank": forms.Select(attrs={"class": TW_SELECT, "id": "id_bank"}),
            "account_number": forms.TextInput(attrs={
                "class": TW_INPUT + " font-mono",
                "placeholder": "10-digit account number",
                "maxlength": "10",
                "id": "id_account_number",
            }),
            "is_proxy": forms.CheckboxInput(attrs={
                "class": "w-4 h-4 rounded border-gray-300 text-[#1CABE2] focus:ring-[#1CABE2]",
            }),
            "proxy_name": forms.TextInput(attrs={
                "class": TW_INPUT,
                "placeholder": "Name of account owner",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["bank"].queryset = Bank.objects.filter(is_active=True)
        self.fields["is_proxy"].required = False
        self.fields["proxy_name"].required = False

    def clean_account_number(self) -> str:
        account_number = self.cleaned_data["account_number"]
        if len(account_number) != 10 or not account_number.isdigit():
            raise forms.ValidationError("Account number must be exactly 10 digits.")
        return account_number
