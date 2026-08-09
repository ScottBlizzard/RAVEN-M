#!/system/bin/sh
set -eu

prefs=/data/data/com.android.chrome/shared_prefs/com.android.chrome_preferences.xml
test -f "$prefs"
owner="$(stat -c %u:%g "$prefs")"

sed -i "/first_run_flow/d;/first_run_tos_accepted/d;/first_run_signin_complete/d;/Chrome.NotificationPermission.RequestCount/d;/Chrome.NotificationPermission.RationaleTimestamp/d" "$prefs"
sed -i 's#</map>#<boolean name="first_run_flow" value="true" /><boolean name="first_run_tos_accepted" value="true" /><boolean name="first_run_signin_complete" value="true" /><int name="Chrome.NotificationPermission.RequestCount" value="1" /><long name="Chrome.NotificationPermission.RationaleTimestamp" value="1786290000000" /></map>#' "$prefs"

chown "$owner" "$prefs"
chmod 660 "$prefs"
restorecon "$prefs"

grep -q '<boolean name="first_run_flow" value="true" />' "$prefs"
grep -q '<boolean name="first_run_tos_accepted" value="true" />' "$prefs"
grep -q '<boolean name="first_run_signin_complete" value="true" />' "$prefs"
grep -q 'name="Chrome.NotificationPermission.RequestCount" value="1"' "$prefs"
grep -q 'name="Chrome.NotificationPermission.RationaleTimestamp" value="1786290000000"' "$prefs"
