import os
import secrets
import django

os.environ["DJANGO_SETTINGS_MODULE"] = "tma.settings"
django.setup()

from django.core.mail import send_mail
from accounts.models import CustomUser
from trainings.models import TrainingCategory

# Get registration links
lga_trainee_link = ""
try:
    lga_cat = TrainingCategory.objects.filter(name__icontains="LGA Trainee").first()
    if lga_cat:
        lga_trainee_link = lga_cat.registration_url
except Exception:
    pass

# Also get Health Registrar link if it exists
health_reg_link = ""
try:
    hr_cat = TrainingCategory.objects.filter(name__icontains="Health Registrar").first()
    if not hr_cat:
        hr_cat = TrainingCategory.objects.filter(name__icontains="LGA Trainee").first()
    if hr_cat:
        health_reg_link = hr_cat.registration_url
except Exception:
    pass

count = 0
for u in CustomUser.objects.filter(participant_profile__isnull=False, is_active=True):
    if not u.email:
        continue
    p = u.participant_profile
    lga_name = str(p.lga) if p.lga else "your area"
    channel_name = str(p.channel) if p.channel else ""

    # Reset password
    new_pw = secrets.token_urlsafe(8)
    u.set_password(new_pw)
    u.save()

    # Pick the right registration link based on their channel
    reg_link = lga_trainee_link or health_reg_link

    body = f"""Dear {p.full_name},

You have been assigned as a Device Manager for the Birth Registration Training in Katsina State.
Your LGA: {lga_name}
Your Channel: {channel_name}

========================================
YOUR LOGIN DETAILS
========================================
Website: https://tma.worksiapps.com
Username: {u.username}
Password: {new_pw}

Save these details. You can change your password after logging in.

========================================
REGISTRATION LINK FOR LGA PARTICIPANTS
========================================
Share this link with the training participants in your LGA.
They will use it to register their details and bank account.

Registration Link: {reg_link}

How to use:
1. Send this link to each participant in your LGA via WhatsApp or SMS
2. They open the link on their phone
3. They fill in their name, phone, email, LGA, organization
4. They select their bank and enter their 10-digit account number
5. They tap "Validate" to verify the account
6. They tap "Register for Training"
7. Their details are saved automatically

IMPORTANT: Make sure they select the correct LGA when registering.

========================================
HOW TO SCAN A DEVICE (Step by Step)
========================================

STEP 1: Log in
- Open https://tma.worksiapps.com on your phone (use Chrome)
- Enter your username and password
- You will see the training page

STEP 2: Go to Devices tab
- Tap "Devices" tab
- Tap "Scan" button

STEP 3: Allow Camera
- Tap ALLOW when asked for camera permission
- Camera opens automatically

STEP 4: Scan the 3 Barcodes
Look at the back of the OUKITEL RT7 TITAN tablet.
There are 3 barcodes on the right side, stacked vertically.

- Hold phone CLOSE (about 10cm) to the FIRST barcode
- Keep STEADY until "IMEI 1" turns green (you feel a vibration)
- Move to SECOND barcode — wait for "IMEI 2" to turn green
- Move to THIRD barcode — wait for "S/N" to turn green

If scanning fails:
- Try better lighting (use daylight)
- Hold phone very steady
- Tap "Type Manually" and enter the numbers by hand
  (the numbers are printed next to each barcode)

STEP 5: Save Device
- Device Type: Tablet
- Condition: Working (or Faulty/Not Working)
- Brand: OUKITEL (already filled)
- Model: RT7 TITAN (already filled)
- Accessories: Complete or Incomplete
- Your LGA is auto-selected
- Tap "Save Device"

STEP 6: Scan Next Device
- Tap "Clear & Next"
- Repeat for all devices

========================================
HOW TO ASSIGN A DEVICE TO A PARTICIPANT
========================================

1. Go to Devices tab
2. Tap the serial number of the device
3. In "Assign Device" section, type the participant name
4. Select the person from the list
5. Tap "Update Assignment"

Done! The device is now linked to that participant.

========================================
NEED HELP?
========================================
- Camera not working? Switch camera using the dropdown at top of scanner
- Forgot password? Tap "Forgot Password" on login page
- Other issues? Contact your training coordinator

---
UNICEF Training Management Application
Developed by Ibukunoluwa Omonijo
"""

    try:
        send_mail(
            "UNICEF TMA - Device Manager Guide, Login & Registration Link",
            body,
            None,
            [u.email],
            fail_silently=False,
        )
        count += 1
        print(f"OK: {p.full_name} ({u.email}) pw={new_pw}")
    except Exception as e:
        print(f"FAIL: {p.full_name} ({u.email}): {e}")

print(f"\nTotal: {count} emails sent")
