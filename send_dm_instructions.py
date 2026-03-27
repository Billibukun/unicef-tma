import os
import django

os.environ["DJANGO_SETTINGS_MODULE"] = "tma.settings"
django.setup()

from django.core.mail import send_mail
from accounts.models import CustomUser

count = 0
for u in CustomUser.objects.filter(participant_profile__isnull=False, is_active=True):
    if not u.email:
        continue
    p = u.participant_profile
    lga_name = str(p.lga) if p.lga else "your area"

    body = (
        f"Dear {p.full_name},\n\n"
        f"You have been assigned as a Device Manager for the Birth Registration Training in Katsina State.\n\n"
        f"YOUR ACCESS:\n"
        f"  URL: https://tma.worksiapps.com\n"
        f"  Username: {u.username}\n"
        f"  (Use the password sent earlier, or click Forgot Password on the login page)\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Log in at https://tma.worksiapps.com\n"
        f"2. You will see participants in your LGA ({lga_name})\n"
        f"3. To scan devices: click Devices tab > Scan\n"
        f"4. Point your phone camera at each barcode:\n"
        f"   - First barcode = IMEI 1\n"
        f"   - Second barcode = IMEI 2\n"
        f"   - Third barcode = Serial Number\n"
        f"5. State and LGA are auto-filled for you\n"
        f"6. Set condition, accessories, then Save Device\n\n"
        f"TIPS:\n"
        f"- Hold phone steady and close to barcode\n"
        f"- Ensure good lighting\n"
        f"- If scan fails, tap Type Manually\n"
        f"- Change password anytime from sidebar\n\n"
        f"Contact your training coordinator if you have issues.\n\n"
        f"---\n"
        f"UNICEF Training Management Application\n"
        f"Developed by Ibukunoluwa Omonijo"
    )

    send_mail(
        "UNICEF TMA - Device Manager Instructions",
        body,
        None,
        [u.email],
        fail_silently=True,
    )
    count += 1
    print(f"Sent to {p.full_name} ({u.email})")

print(f"\nTotal: {count} emails sent")
