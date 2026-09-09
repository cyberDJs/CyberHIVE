#!/usr/bin/env python3
import shlex
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = ROOT / 'infra/live-usb/debian-live/config/includes.chroot/usr/local/sbin/cyberhive-boot-commit'
src = COMMIT.read_text()

def require(text):
    assert text in src, text

positive_start = src.index('positive_sequence() {')
positive_end = src.index('\n}\n\nclear_pending_state() {', positive_start) + 3
positive_sequence = src[positive_start:positive_end]

start = src.index("if [ \"$efi_current_slot_missing\" = 'true' ] && [ ! -f \"$transaction\" ]; then")
end = src.index("health_ok='false'")
boot_guard = src[start:end]

def q(value):
    return shlex.quote(str(value))

def run_guard_case(*, pending, state_slot, state_release, state_sequence, pending_release='release-1', current='A', efi_current_slot='', efi_current_slot_missing='true'):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        persist = tmp / 'persist'
        ota = tmp / 'ota'
        script = tmp / 'guard.sh'
        script.write_text(f'''#!/bin/sh
set -eu
persist={q(persist)}
otadir={q(ota)}
transaction="$otadir/commit-transaction.json"
current={q(current)}
efi_current_slot_missing={q(efi_current_slot_missing)}
efi_current_slot={q(efi_current_slot)}
pending={q(pending)}
pending_release={q(pending_release)}
previous=''
tries=''
state_pending_slot={q(state_slot)}
state_pending_release={q(state_release)}
state_pending_sequence={q(state_sequence)}
mkdir -p "$persist/state/evidence" "$otadir"
[ -z "$state_pending_slot" ] || printf '%s\n' "$state_pending_slot" >"$otadir/pending-slot"
[ -z "$state_pending_release" ] || printf '%s\n' "$state_pending_release" >"$otadir/pending-release-id"
[ -z "$state_pending_sequence" ] || printf '%s\n' "$state_pending_sequence" >"$otadir/pending-sequence"
{positive_sequence}
atomic_text() {{ printf '%s\\n' "$1" >"$2"; }}
clear_pending_state() {{ rm -f "$otadir"/pending-*; }}
quarantine_release() {{ printf '%s\\n' "$1:$2:$3" >{q(tmp / 'quarantine')}; }}
record_health() {{ mkdir -p "$persist/state/evidence"; printf 'status=%s\\nreason=%s\\n' "$1" "$2" >"$persist/state/evidence/last-boot-health"; }}
sync() {{ :; }}
rollback_candidate_reboot() {{ printf '%s\\n' "$1" >{q(tmp / 'rollback')}; exit 99; }}
normalize_previous_efi_or_fail() {{ printf '%s\\n' "$1" >{q(tmp / 'normalize')}; exit 98; }}
{boot_guard}
printf '%s\\n' ordinary-health-path >{q(tmp / 'ordinary')}
''', encoding='utf-8')
        proc = subprocess.run(['/bin/sh', str(script)], capture_output=True, text=True, check=False)
        evidence = persist / 'state/evidence/last-boot-health'
        return {
            'returncode': proc.returncode,
            'stdout': proc.stdout,
            'stderr': proc.stderr,
            'rollback': (tmp / 'rollback').read_text().strip() if (tmp / 'rollback').exists() else '',
            'normalize': (tmp / 'normalize').read_text().strip() if (tmp / 'normalize').exists() else '',
            'quarantine': (tmp / 'quarantine').read_text().strip() if (tmp / 'quarantine').exists() else '',
            'health': evidence.read_text() if evidence.exists() else '',
            'ordinary': (tmp / 'ordinary').exists(),
        }

require('positive_sequence()')
require('positive_sequence "$state_pending_sequence"')
require('rollback_candidate_reboot empty-current-slot-pending-candidate')
require('rollback_candidate_reboot unrecoverable-pending-efi-current-slot')
require('rollback_candidate_reboot incomplete-pending-metadata')
require('positive_sequence "$state_pending_sequence" || state_pending_sequence=')
require(': # allowed only because the pending slot must flow into rollback-detected repair below')
require('[ "$efi_current_slot_missing" = \'true\' ]')
require('normalize_previous_efi_or_fail rollback-detected')
require('record_health pass rollback-detected')
require('pending_state_mismatch=')
require('if [ -n "$state_pending_release" ] && [ "$pending" != "$state_pending_slot" ]; then')
require('record_health fail "$empty_current_slot_reason"')
require('exit 2')

candidate_guard_index = src.index("candidate='false'")
rollback_detected_index = src.index("pending_state_mismatch='false'")
assert candidate_guard_index < rollback_detected_index
assert boot_guard.index('rollback_candidate_reboot empty-current-slot-pending-candidate') < src.index("health_ok='false'")
assert boot_guard.index('rollback_candidate_reboot unrecoverable-pending-efi-current-slot') < src.index("health_ok='false'")
assert boot_guard.index('rollback_candidate_reboot incomplete-pending-metadata') < rollback_detected_index
assert 'case "$pending" in' in boot_guard
assert "*)\n      empty_current_slot_reason='unrecoverable-pending-efi-current-slot'" in boot_guard

valid_candidate = run_guard_case(pending='A', state_slot='A', state_release='release-1', state_sequence='7')
assert valid_candidate['returncode'] == 99, valid_candidate
assert valid_candidate['rollback'] == 'empty-current-slot-pending-candidate', valid_candidate
assert 'reason=empty-current-slot-pending-candidate' in valid_candidate['health'], valid_candidate
assert not valid_candidate['ordinary'], valid_candidate

zero_candidate = run_guard_case(pending='A', state_slot='A', state_release='release-1', state_sequence='0')
assert zero_candidate['returncode'] == 99, zero_candidate
assert zero_candidate['rollback'] == 'unrecoverable-pending-efi-current-slot', zero_candidate
assert 'reason=unrecoverable-pending-efi-current-slot' in zero_candidate['health'], zero_candidate
assert not zero_candidate['ordinary'], zero_candidate

missing_metadata = run_guard_case(pending='A', state_slot='', state_release='', state_sequence='')
assert missing_metadata['returncode'] == 99, missing_metadata
assert missing_metadata['rollback'] == 'unrecoverable-pending-efi-current-slot', missing_metadata
assert not missing_metadata['ordinary'], missing_metadata

valid_current_slot_mismatch = run_guard_case(
    pending='A',
    state_slot='B',
    state_release='release-1',
    state_sequence='7',
    efi_current_slot='A',
    efi_current_slot_missing='false',
)
assert valid_current_slot_mismatch['returncode'] == 99, valid_current_slot_mismatch
assert valid_current_slot_mismatch['rollback'] == 'incomplete-pending-metadata', valid_current_slot_mismatch
assert 'reason=incomplete-pending-metadata' in valid_current_slot_mismatch['health'], valid_current_slot_mismatch
assert not valid_current_slot_mismatch['ordinary'], valid_current_slot_mismatch

other_slot_repair = run_guard_case(pending='B', state_slot='B', state_release='release-1', state_sequence='7')
assert other_slot_repair['returncode'] == 98, other_slot_repair
assert other_slot_repair['normalize'] == 'rollback-detected', other_slot_repair
assert not other_slot_repair['ordinary'], other_slot_repair

malformed_other_slot = run_guard_case(pending='B', state_slot='B', state_release='release-1', state_sequence='0')
assert malformed_other_slot['returncode'] == 2, malformed_other_slot
assert 'reason=unrecoverable-pending-efi-current-slot' in malformed_other_slot['health'], malformed_other_slot
assert not malformed_other_slot['ordinary'], malformed_other_slot

print('CyberHIVE boot-commit empty current-slot behavior validation passed')
