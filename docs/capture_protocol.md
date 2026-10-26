# Capture Protocol

Conventions for CSI capture sessions used in this work.

## Session naming

Files are named `<device>_<mode>_s<N>` where:
- `<device>` identifies the NIC (e.g. `ax200`, `ax210`, `bcm4345`)
- `<mode>` is `inject` (injection) or `passive`
- `s<N>` is the session number

## Capture modes

- **Injection mode** (PicoScenes): the transmitter is controlled directly,
  isolating the frontend contribution. Preferred for phase-based features.
- **Passive mode**: standard packet reception. Amplitude features remain
  usable; phase features are less clean without STO correction.

## Bandwidth consistency (IMPORTANT)

Residual phase non-linearity is measured across subcarriers, so captures at
different bandwidths (20 / 40 / 80 MHz -> 242 / 484 / 996 subcarriers) are
NOT directly comparable. **Fix the bandwidth per session** across the whole
device set. Mixed-bandwidth datasets require per-bandwidth normalisation.

## Tooling caveats

- **FeitCSI .dat**: lacks sampling-time-offset (STO) correction. Absolute
  phase-based feature magnitudes are inflated; usable for cross-vendor
  separation, not for clean absolute values.
- **PicoScenes .csi**: provides STO-corrected, phase-coherent CSI. Preferred
  for residual phase non-linearity extraction. Parser targets format
  version 0x315.
