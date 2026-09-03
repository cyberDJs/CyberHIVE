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
- Real image build evidence is not USB write evidence.
- Real image build evidence is not boot/runtime verification evidence.

## Stop line

```text
ISO build: NOT RUN BY PR
USB write: NOT AUTHORIZED
hardware boot: NOT CLAIMED
runtime verification: NOT CLAIMED
deployment: NOT PERFORMED
ADR accepted: NO
```
