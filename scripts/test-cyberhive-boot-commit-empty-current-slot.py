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
require('record_health fail "$empty_current_slot_reason"')
require('exit 2')

assert guard.index("empty_current_slot_reason='unrecoverable-pending-efi-current-slot'") < src.index("health_ok='false'")
assert "case \"$pending\" in" in guard
assert "*)\n      empty_current_slot_reason='unrecoverable-pending-efi-current-slot'" in guard
print('CyberHIVE boot-commit empty current-slot guard validation passed')
