# WB-HIVE-BOOT-0004 Source Map

## Work block

```text
docs/work-blocks/WB-HIVE-BOOT-0004-real-image-build-gate.md
```

## Parent evidence

```text
docs/work-blocks/WB-HIVE-BOOT-0003-real-build-plan.md
infra/live-usb/debian-live/REAL-BUILD-PLAN.md
infra/live-usb/debian-live/real-build-manifest.md
```

## New gate files

```text
docs/runbooks/live-usb-real-image-build-gate.md
docs/security/live-usb-real-image-build-safety.md
docs/adr/ADR-0008-live-usb-real-image-build-gate.md
infra/live-usb/debian-live/REAL-IMAGE-BUILD-GATE.md
infra/live-usb/debian-live/build-real-image.sh
scripts/validate-live-usb-real-image-build-gate.sh
.github/workflows/live-usb-real-image-build-gate.yml
.github/workflows/live-usb-real-image-build-manual.yml
```

## Updated files

```text
infra/live-usb/build-plan.md
infra/live-usb/debian-live/REAL-BUILD-PLAN.md
```

## Authority notes

- GitHub repository is the canonical tracked project source.
- This work block is proposed until merged.
- ADR-0008 is proposed only and is not accepted by file existence.
- Ordinary PR validation is repository/gate validation only and does not run the real image build.
- The same-repository `approved:image-build-only` label path may run an image-only build for the exact PR head carried by the label event.
- A later push requires a fresh remove/re-apply cycle before claiming exact-current-head image evidence.
- Real image build evidence is not USB write evidence.
- Real image build evidence is not boot/runtime verification evidence.

## Stop line

```text
ISO build: NOT RUN BY PR VALIDATION
approved:image-build-only label run: IMAGE BUILD ONLY
USB write: NOT AUTHORIZED
hardware boot: NOT CLAIMED
runtime verification: NOT CLAIMED
deployment: NOT PERFORMED
ADR accepted: NO
```
