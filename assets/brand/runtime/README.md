# CyberHIVE Runtime Brand Assets

Repository-safe runtime branding assets for the CyberHIVE Live USB.

## Current candidate

`cyberdjs-cyberhive-boot.svg` is the reviewable source for the Live Appliance v0.2 boot treatment.

The source is intentionally vector/text based so it can be code-reviewed. The real-image build converts it to the raster format required by Debian live-build inside the temporary build workspace.

This candidate is implementation material on `WB-HIVE-BOOT-0005`; merge remains the visual acceptance boundary.

## Intended assets

- boot splash source/export
- role selector visual assets
- dashboard icon set
- topology node icons
- USB badge/icon
- wallpaper/backgrounds
- color and typography tokens

## Rules

- no third-party logos
- no embedded secrets or private infrastructure data
- assets must be reviewable or have tracked source/export provenance
- generated or new visual assets remain candidates until reviewed
- runtime UI must remain usable without images
- generated raster build output is not the canonical visual source
