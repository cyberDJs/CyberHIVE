#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = ROOT / 'infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-boot-commit'
src = COMMIT.read_text()

def require(text):
    assert text in src, text

start = src.index("if [ \"$efi_current_slot_missing\" = 'true' ] && [ ! -f \"$transaction\" ]; then")
end = src.index('rollback_malformed_transaction() {')
guard = src[start:end]

require("empty_current_slot_reason='unrecoverable-pending-efi-current-slot'")
require('[ "$pending" = "$current" ]')
require('[ "$state_pending_slot" = "$current" ]')
require('[ -n "$state_pending_release" ]')
require('[ "$state_pending_release" = "$pending_release" ]')
require("[ \"$pending_recoverable\" = 'true' ]")
require('quarantine_release "$state_pending_release" "$state_pending_sequence" empty-current-slot-pending-candidate')
require('record_health fail empty-current-slot-pending-candidate')
require('rollback_candidate_reboot empty-current-slot-pending-candidate')
require(': # allowed only because the pending slot must flow into rollback-detected repair below')
require('[ "$efi_current_slot_missing" = \'true\' ]')
require('normalize_previous_efi_or_fail rollback-detected')
require('record_health pass rollback-detected')

assert guard.index("empty_current_slot_reason='unrecoverable-pending-efi-current-slot'") < src.index("health_ok='false'")
assert 'case "$pending" in' in guard
assert '*)\n      empty_current_slot_reason=\'unrecoverable-pending-efi-current-slot\'' in guard
assert 'empty-current-slot-pending-candidate' in guard
assert guard.index('empty-current-slot-pending-candidate') < src.index("candidate='false'")
rollback_start = src.index("if [ -n \"$state_pending_release\" ]; then")
rollback_end = src.index("candidate='false'")
rollback_guard = src[rollback_start:rollback_end]
assert '[ "$current" != "$state_pending_slot" ]' in rollback_guard
assert 'normalize_previous_efi_or_fail rollback-detected' in rollback_guard
print('CyberHIVE boot-commit empty current-slot guard validation passed')
