#!/bin/sh
set -eu

root='infra/live-usb/debian-live/config/includes.chroot'
required='docs/work-blocks/WB-HIVE-BOOT-0006-unattended-ota-v0-3.md
docs/adr/ADR-0026-cyberhive-unattended-single-usb-ab-ota.md
docs/runbooks/live-appliance-v0-3.md
docs/security/live-appliance-v0-3-safety.md
infra/live-usb/debian-live/build-unattended-disk-image.sh
infra/live-usb/debian-live/config/hooks/live/002-cyberhive-unattended-v03.hook.chroot
infra/live-usb/debian-live/config/includes.chroot/usr/local/lib/cyberhive-device.sh
infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-host-disk-guard
infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-persist-init
infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-firstboot
infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-management-firewall
infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-update
infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-update-check
infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-boot-commit
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-persist-init.service
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/NetworkManager.service.d/10-cyberhive-persist.conf
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/tailscaled.service.d/10-cyberhive-persist.conf
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-management-firewall.service
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/ssh.service.d/20-cyberhive-management-firewall.conf
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-boot-commit.service
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-update-check.service
infra/live-usb/debian-live/config/includes.chroot/etc/systemd/system/cyberhive-update-check.timer
infra/live-usb/debian-live/config/includes.chroot/etc/profile.d/20-cyberhive-firstboot.sh
infra/live-usb/debian-live/config/includes.chroot/etc/cyberhive/bootstrap/authorized_keys
infra/live-usb/debian-live/config/includes.chroot/etc/cyberhive/ota/allowed_signers
.github/workflows/live-appliance-v0-3.yml'

printf '%s\n' "$required" | while IFS= read -r f; do
  [ -n "$f" ] || continue
  [ -f "$f" ] || { echo "missing v0.3 path: $f" >&2; exit 1; }
done

for f in \
  infra/live-usb/debian-live/build-unattended-disk-image.sh \
  infra/live-usb/debian-live/config/hooks/live/002-cyberhive-unattended-v03.hook.chroot \
  "$root/usr/local/lib/cyberhive-device.sh" \
  "$root/usr/local/bin/cyberhive-host-disk-guard" \
  "$root/usr/local/sbin/cyberhive-persist-init" \
  "$root/usr/local/sbin/cyberhive-firstboot" \
  "$root/usr/local/sbin/cyberhive-management-firewall" \
  "$root/usr/local/sbin/cyberhive-update" \
  "$root/usr/local/sbin/cyberhive-update-check" \
  "$root/usr/local/sbin/cyberhive-boot-commit" \
  "$root/usr/local/sbin/cyberhive-onboarding-init"; do
  sh -n "$f"
done
python3 -c 'import ast,pathlib; ast.parse(pathlib.Path("infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-web").read_text())'

line_of() {
  file=$1
  text=$2
  grep -nF -- "$text" "$file" | head -n 1 | cut -d: -f1
}
assert_before() {
  file=$1; first=$2; second=$3
  first_line=$(line_of "$file" "$first")
  second_line=$(line_of "$file" "$second")
  [ -n "$first_line" ] && [ -n "$second_line" ] && [ "$first_line" -lt "$second_line" ] || {
    echo "ordering invariant failed in $file: $first before $second" >&2; exit 1;
  }
}

if grep -R -n -E 'BEGIN (OPENSSH|RSA|EC|PRIVATE) KEY' "$root/etc/cyberhive" infra/live-usb/debian-live/config/hooks/live/002-cyberhive-unattended-v03.hook.chroot docs/work-blocks/WB-HIVE-BOOT-0006-unattended-ota-v0-3.md; then
  echo 'private key material must not be committed' >&2; exit 1
fi

grep -qx 'CYBERHIVE_LIVE_VERSION="0.3.0-dev"' "$root/etc/cyberhive/live/config.env"
grep -qx 'CYBERHIVE_EFI_LABEL="CYBER_EFI"' "$root/etc/cyberhive/live/config.env"
grep -qx 'CYBERHIVE_SLOT_A_LABEL="CYBERHIVE_A"' "$root/etc/cyberhive/live/config.env"
grep -qx 'CYBERHIVE_SLOT_B_LABEL="CYBERHIVE_B"' "$root/etc/cyberhive/live/config.env"
grep -qx 'CYBERHIVE_STATE_LABEL="CYBERHIVE_STATE"' "$root/etc/cyberhive/live/config.env"
python3 - "$root/etc/cyberhive/live/config.env" <<'PY'
from pathlib import Path
import sys
for line in Path(sys.argv[1]).read_text().splitlines():
    if line.startswith('CYBERHIVE_EFI_LABEL='):
        label = line.split('=', 1)[1].strip().strip('"')
        assert 1 <= len(label.encode('ascii')) <= 11
        break
else:
    raise AssertionError('CYBERHIVE_EFI_LABEL missing')
PY

device="$root/usr/local/lib/cyberhive-device.sh"
grep -F 'cyberhive_live_medium_device()' "$device" >/dev/null
grep -F '/run/live/medium /lib/live/mount/medium' "$device" >/dev/null
grep -F 'cyberhive_partition_on_parent_by_label()' "$device" >/dev/null
grep -F 'cyberhive_require_usb_parent()' "$device" >/dev/null

persist_init="$root/usr/local/sbin/cyberhive-persist-init"
grep -F '. /usr/local/lib/cyberhive-device.sh' "$persist_init" >/dev/null
grep -F 'cyberhive_live_medium_device' "$persist_init" >/dev/null
grep -F 'cyberhive_verify_live_slot' "$persist_init" >/dev/null
grep -F 'cyberhive_partition_on_parent_by_label "$parent" "$CYBERHIVE_STATE_LABEL"' "$persist_init" >/dev/null
assert_before "$persist_init" 'cyberhive_partition_on_parent_by_label "$parent" "$CYBERHIVE_STATE_LABEL"' 'mount -o rw,nodev,nosuid "$state_dev" "$persist"'
if grep -F 'blkid -L' "$persist_init"; then echo 'persist-init must not resolve critical siblings by global label' >&2; exit 1; fi

firstboot="$root/usr/local/sbin/cyberhive-firstboot"
grep -F 'state/network' "$firstboot" >/dev/null
grep -F 'tailscale up --hostname=' "$firstboot" >/dev/null
grep -F 'nmcli --ask device wifi connect "$ssid"' "$firstboot" >/dev/null
if grep -F 'wifi_password' "$firstboot"; then echo 'firstboot must not place Wi-Fi secrets in variables or argv' >&2; exit 1; fi
if grep -F 'password "$wifi_password"' "$firstboot"; then echo 'firstboot must not pass Wi-Fi secrets in process arguments' >&2; exit 1; fi

onboarding="$root/usr/local/sbin/cyberhive-onboarding-init"
grep -F 'existing_persist_state=$(cat "$CYBERHIVE_STATE_DIR/persistence-state"' "$onboarding" >/dev/null
grep -F 'case "$existing_persist_state" in mounted:*) persist_state=$existing_persist_state ;; esac' "$onboarding" >/dev/null

update="$root/usr/local/sbin/cyberhive-update"
grep -F '. /usr/local/lib/cyberhive-device.sh' "$update" >/dev/null
grep -F 'cyberhive_live_medium_device' "$update" >/dev/null
grep -F 'unique STATE/EFI/inactive-slot siblings not found on booted USB parent' "$update" >/dev/null
if grep -F 'blkid -L' "$update"; then echo 'updater must not resolve critical siblings by global label' >&2; exit 1; fi
grep -F -- '-I cyberhive-dev-release' "$update" >/dev/null
grep -F -- '-n cyberhive-ota' "$update" >/dev/null
grep -F 'bundle SHA-256 mismatch' "$update" >/dev/null
grep -F 'refusing OTA replay/downgrade/quarantine' "$update" >/dev/null
grep -F 'refusing previously failed OTA release' "$update" >/dev/null
grep -F 'another CyberHIVE OTA operation is active' "$update" >/dev/null
grep -F 'refusing OTA restage: inactive slot already armed or pending' "$update" >/dev/null
grep -F 'refusing OTA restage: EFI grubenv already armed or pending' "$update" >/dev/null
grep -F 'grub-editenv "$envfile" list' "$update" >/dev/null
assert_before "$update" 'refusing OTA restage: inactive slot already armed or pending' 'mount -o rw,nodev,nosuid "$target_dev" "$slot_mount"'
assert_before "$update" 'refusing OTA restage: EFI grubenv already armed or pending' 'mount -o rw,nodev,nosuid "$target_dev" "$slot_mount"'
assert_before "$update" 'mount -o ro,nodev,nosuid,noexec "$efi_dev" "$efi_mount"' 'mount -o rw,nodev,nosuid "$target_dev" "$slot_mount"'
grep -F 'read_sequence_file()' "$update" >/dev/null
grep -F 'malformed persisted current-sequence; refusing OTA' "$update" >/dev/null
grep -F 'malformed persisted failed-sequence; refusing OTA' "$update" >/dev/null
assert_before "$update" 'atomic_text "$sequence" "$otadir/pending-sequence"' 'grub-editenv "$envfile" set'
if grep -n -E '(^|[[:space:]])(dd|mkfs|wipefs|parted|sgdisk)([[:space:]]|$)' "$update"; then echo 'runtime OTA must not perform raw disk or partition mutation' >&2; exit 1; fi

commit="$root/usr/local/sbin/cyberhive-boot-commit"
grep -F '. /usr/local/lib/cyberhive-device.sh' "$commit" >/dev/null
grep -F 'cyberhive_live_medium_device' "$commit" >/dev/null
grep -F 'unique EFI sibling not found on booted USB parent' "$commit" >/dev/null
if grep -F 'blkid -L' "$commit"; then echo 'boot commit must not resolve critical siblings by global label' >&2; exit 1; fi
grep -F 'env_state=$(grub-editenv "$envfile" list) ||' "$commit" >/dev/null
grep -F 'grubenv unreadable' "$commit" >/dev/null
grep -F "pending=\$(printf '%s\\n' \"\$env_state\"" "$commit" >/dev/null
if grep -F 'grub-editenv "$envfile" list | sed' "$commit"; then echo 'boot commit must not mask grubenv read failure through a pipeline' >&2; exit 1; fi
grep -F 'candidate persistence unavailable; rebooting for automatic rollback' "$commit" >/dev/null
grep -F 'commit-transaction.json' "$commit" >/dev/null
grep -F 'invalid commit transaction schema' "$commit" >/dev/null
grep -F 'rollback_candidate_reboot()' "$commit" >/dev/null
grep -F 'commit_candidate_efi_or_reboot()' "$commit" >/dev/null
grep -F 'failed to write rollback grubenv' "$commit" >/dev/null
grep -F 'EFI remount rw failed during' "$commit" >/dev/null
grep -F 'final EFI commit write failed; rebooting for recovery' "$commit" >/dev/null
grep -F 'final EFI remount rw failed; rebooting for recovery' "$commit" >/dev/null
grep -F 'record_health fail final-efi-commit' "$commit" >/dev/null
grep -F 'rollback_malformed_transaction()' "$commit" >/dev/null
grep -F 'malformed-commit-transaction' "$commit" >/dev/null
grep -F 'incomplete-commit-rollback' "$commit" >/dev/null
grep -F 'rollback-detected' "$commit" >/dev/null
grep -F 'quarantine_release "$state_pending_release" "$state_pending_sequence" health-gate' "$commit" >/dev/null
grep -F 'rollback_candidate_reboot health-gate' "$commit" >/dev/null
grep -F 'rollback_candidate_reboot malformed-current-sequence' "$commit" >/dev/null
grep -F 'rollback_candidate_reboot incomplete-pending-metadata' "$commit" >/dev/null
grep -F 'clearing incomplete pre-arm pending STATE journal' "$commit" >/dev/null
grep -F 'recovered-pre-arm-journal' "$commit" >/dev/null
assert_before "$commit" 'clearing incomplete pre-arm pending STATE journal' 'if [ -n "$state_pending_release" ] && [ "$pending" != "$state_pending_slot" ]; then'
grep -F 'read_sequence_file()' "$commit" >/dev/null
grep -F 'malformed persisted current-sequence; rolling back candidate' "$commit" >/dev/null
grep -F 'quarantine_release "$state_pending_release" "$state_pending_sequence" malformed-current-sequence' "$commit" >/dev/null
grep -F 'cyberhive-host-disk-guard >/dev/null 2>&1' "$commit" >/dev/null

host_guard="$root/usr/local/bin/cyberhive-host-disk-guard"
grep -F '. /usr/local/lib/cyberhive-device.sh' "$host_guard" >/dev/null
grep -F 'cyberhive_live_medium_device' "$host_guard" >/dev/null
grep -F 'cyberhive_require_usb_parent "$candidate"' "$host_guard" >/dev/null
if grep -F 'NAME,TYPE,RM' "$host_guard"; then echo 'host-disk guard must not classify CyberHIVE by RM alone' >&2; exit 1; fi

builder='infra/live-usb/debian-live/build-unattended-disk-image.sh'
grep -F '. "$script_dir/config/includes.chroot/etc/cyberhive/live/config.env"' "$builder" >/dev/null
grep -F 'mkfs.vfat -F 32 -n "$CYBERHIVE_EFI_LABEL"' "$builder" >/dev/null
grep -F 'regexp --set=1:boot_disk' "$builder" >/dev/null
grep -F 'set efi="$boot_disk,gpt1"' "$builder" >/dev/null
grep -F 'set slotdev="$boot_disk,gpt2"' "$builder" >/dev/null
grep -F 'set slotdev="$boot_disk,gpt3"' "$builder" >/dev/null
grep -F 'cannot prove boot EFI parent' "$builder" >/dev/null
grep -F 'set missing_slot="$boot_slot"' "$builder" >/dev/null
grep -F 'if [ -n "$pending_slot" -a "$missing_slot" = "$pending_slot" ]; then' "$builder" >/dev/null
grep -F 'save_env -f "$envfile" current_slot pending_slot previous_slot tries pending_release_id' "$builder" >/dev/null
grep -F 'selected_slot="($slotdev)"' "$builder" >/dev/null
grep -F 'probe --fs-uuid --set=slot_uuid "$selected_slot"' "$builder" >/dev/null
grep -F 'cannot prove selected slot filesystem UUID' "$builder" >/dev/null
grep -F 'live-media=/dev/disk/by-uuid/$slot_uuid' "$builder" >/dev/null
grep -F 'cyberhive.slot_uuid=$slot_uuid' "$builder" >/dev/null
grep -F 'slot_uuid_duplicate' "$builder" >/dev/null
grep -F 'for candidate in (*); do' "$builder" >/dev/null
grep -F 'duplicate selected slot filesystem UUID' "$builder" >/dev/null
grep -F 'selected slot filesystem UUID resolved ambiguously' "$builder" >/dev/null
assert_before "$builder" 'duplicate selected slot filesystem UUID' 'linux "$slotroot/vmlinuz"'
assert_before "$builder" 'selected slot filesystem UUID resolved ambiguously' 'linux "$slotroot/vmlinuz"'
if grep -F 'hd15,gpt3' "$builder"; then echo 'GRUB duplicate UUID check must not be limited to a hard-coded disk list' >&2; exit 1; fi
if grep -F 'search --no-floppy --label' "$builder"; then echo 'GRUB slot selection must not use globally non-unique labels' >&2; exit 1; fi
grep -F '"usb_written": false' "$builder" >/dev/null
if grep -F '/dev/sd' "$builder"; then echo 'image builder must not name a physical disk target' >&2; exit 1; fi

firewall="$root/usr/local/sbin/cyberhive-management-firewall"
grep -F 'required command missing' "$firewall" >/dev/null
if grep -F 'command -v "$bin"' "$firewall" | grep -F 'return 0'; then echo 'firewall must fail closed when filtering binaries are missing' >&2; exit 1; fi
grep -F -- '--dport 22 -j DROP' "$firewall" >/dev/null
grep -F -- '--dport 80 -j DROP' "$firewall" >/dev/null
assert_before "$firewall" '--dport 80 -j DROP' 'for net in 127.0.0.0/8'

web="$root/usr/local/bin/cyberhive-web"
grep -F 'CSRF_TOKEN = secrets.token_urlsafe' "$web" >/dev/null
grep -F 'def require_mutation_auth' "$web" >/dev/null
grep -F 'def trusted_management_host' "$web" >/dev/null
grep -F 'def trusted_management_request' "$web" >/dev/null
grep -F 'import threading' "$web" >/dev/null
grep -F 'ATTEMPTS_LOCK = threading.Lock()' "$web" >/dev/null
grep -F 'with ATTEMPTS_LOCK:' "$web" >/dev/null
grep -F 'TRUSTED_TAILSCALE_NAMES' "$web" >/dev/null
grep -F "host.startswith(f'{name}.') and host.endswith('.ts.net')" "$web" >/dev/null
grep -F "headers.get('Host'" "$web" >/dev/null
grep -F "headers.get('Origin'" "$web" >/dev/null
grep -F 'trusted management Host/Origin required' "$web" >/dev/null
grep -F "self.headers.get('X-CyberHIVE-CSRF'" "$web" >/dev/null
grep -F "'X-CyberHIVE-CSRF':csrf" "$web" >/dev/null
python3 - "$web" <<'PY'
from pathlib import Path
import sys
src = Path(sys.argv[1]).read_text()
assert "return host in TRUSTED_HOST_NAMES or host.endswith('.ts.net')" not in src
for route in ("def do_GET(self):", "def do_POST(self):"):
    block = src[src.index(route):src.index("if self.path ==", src.index(route))]
    assert 'require_management_request' in block
for route, end in [("if self.path == '/api/role':", "if self.path == '/api/support':"), ("if self.path == '/api/support':", "self.send_json(HTTPStatus.NOT_FOUND")]:
    block = src[src.index(route):src.index(end, src.index(route)+1)]
    assert 'require_mutation_auth' in block
session = src[src.index("if self.path == '/api/session':"):src.index("if self.path == '/api/support-download':")]
assert 'require_management_request' in session
assert "payload['csrf'] = CSRF_TOKEN" in session
for route, end in [("if self.path == '/api/health':", "if self.path == '/api/inventory':"), ("if self.path == '/api/inventory':", "if self.path == '/api/session':")]:
    block = src[src.index(route):src.index(end, src.index(route)+1)]
    assert 'require_pairing' in block
PY
python3 - "$web" <<'PY'
import importlib.machinery
import importlib.util
import os
import sys
import unittest.mock

os.environ['CYBERHIVE_TAILSCALE_HOSTNAME'] = 'cyberhive-dev-01'
loader = importlib.machinery.SourceFileLoader('cyberhive_web_under_test', sys.argv[1])
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
with unittest.mock.patch('pathlib.Path.mkdir'), \
     unittest.mock.patch('pathlib.Path.write_text'), \
     unittest.mock.patch('os.chmod'):
    loader.exec_module(module)

class Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)

assert module.trusted_management_host('cyberhive-dev-01.tailnet.ts.net')
assert not module.trusted_management_host('evil.tailnet.ts.net')
assert module.trusted_management_request(Headers(Host='100.64.0.10'))
assert module.trusted_management_request(Headers(Host='cyberhive.local', Origin='http://cyberhive.local'))
assert not module.trusted_management_request(Headers(Host='attacker.example'))
assert not module.trusted_management_request(Headers(Host='100.64.0.10', Origin='http://attacker.example'))
PY

web_unit="$root/etc/systemd/system/cyberhive-web.service"
ssh_dropin="$root/etc/systemd/system/ssh.service.d/20-cyberhive-management-firewall.conf"
grep -F 'Requires=cyberhive-management-firewall.service' "$web_unit" >/dev/null
grep -F 'After=cyberhive-onboarding-init.service network-online.target cyberhive-management-firewall.service' "$web_unit" >/dev/null
grep -F 'EnvironmentFile=/etc/cyberhive/live/config.env' "$web_unit" >/dev/null
grep -F 'Requires=cyberhive-management-firewall.service' "$ssh_dropin" >/dev/null
grep -F 'After=cyberhive-management-firewall.service' "$ssh_dropin" >/dev/null
grep -qx 'iptables' infra/live-usb/debian-live/config/package-lists/cyberhive-live.list.chroot

grep -F 'PasswordAuthentication no' "$root/usr/local/sbin/cyberhive-onboarding-init" >/dev/null
grep -F 'state/ssh/host_keys' "$root/usr/local/sbin/cyberhive-onboarding-init" >/dev/null
grep -F 'RuntimeWatchdogSec=90s' "$root/etc/systemd/system.conf.d/30-cyberhive-watchdog.conf" >/dev/null
grep -F 'OnUnitActiveSec=30min' "$root/etc/systemd/system/cyberhive-update-check.timer" >/dev/null
grep -F 'pre-unattended-disk-usage.txt' .github/workflows/live-usb-real-image-build-gate.yml >/dev/null
grep -F 'unattended-console.txt' .github/workflows/live-usb-real-image-build-gate.yml >/dev/null

echo 'CyberHIVE Live Appliance v0.3 validation passed'
