# CSI-P4 Fingerprinting

Hardware-intrinsic Channel State Information (CSI) fingerprinting with
enforcement in a P4 programmable data plane.

This repository accompanies the paper *"Embedding Physical Layer Fingerprints
into P4 Networks"* (ICECER 2026) and provides the P4 program, token
specification, and CSI feature-extraction scripts needed to reproduce the
token-construction and enforcement stages described in the paper.

## Overview

The system extracts hardware-intrinsic CSI features (carrier frequency offset,
IQ imbalance, residual phase non-linearity, and cross-antenna phase
differential) from commodity 802.11ax NICs, quantises them into a compact
64-bit fingerprint carried in a custom EtherType token, and enforces device
authentication at line rate within a P4 pipeline running on BMv2/Mininet.

## Repository layout

```
csi-p4-fingerprinting/
├── p4/                     P4 program and control-plane config
│   ├── csi_fingerprint.p4  Main P4 pipeline (parser, tables, registers)
│   └── runtime/            P4Runtime table entries and switch config
├── tools/
│   ├── extraction/         CSI feature extraction from capture files
│   │   ├── pnl_extract.py       FeitCSI .dat  -> PNL features
│   │   └── pico_pnl_extract.py  PicoScenes .csi (v0x315) -> PNL features
│   └── analysis/           Classification and figure generation
│       └── figure_export.py     Result figures (CFO, confusion matrix)
├── docs/
│   ├── token_spec.md       CSI token wire format (18-byte structure)
│   └── capture_protocol.md Capture procedure and session conventions
├── data/
│   └── README_data/        Notes on data availability (captures not committed)
├── LICENSE
└── README.md
```

## Token format

The CSI token is an 18-byte structure appended after the Ethernet header using
EtherType `0x88B5`. Full field-by-field specification in
[`docs/token_spec.md`](docs/token_spec.md).

## Quick start

### Requirements
- Python 3.10+ with `numpy`, `matplotlib`
- P4 toolchain: `p4c`, `bmv2` (`simple_switch_grpc`), `mininet`
- For CSI capture: FeitCSI or PicoScenes with a supported 802.11ax NIC

### Extract features from a capture
```bash
# FeitCSI .dat captures
python tools/extraction/pnl_extract.py /path/to/dat/folder

# PicoScenes .csi captures (format version 0x315)
python tools/extraction/pico_pnl_extract.py /path/to/csi/folder
```

### Run the P4 pipeline
```bash
# compile
p4c --target bmv2 --arch v1model p4/csi_fingerprint.p4

# see p4/runtime/ for Mininet topology and P4Runtime table setup
```

## Reproducing the paper results

The paper reports preliminary 3-class classification (88.9% k-NN LOO) on
PicoScenes injection-mode captures. The extraction and analysis scripts here
regenerate the feature statistics and result figures from capture files. Raw
captures are not committed to the repository owing to size; see
[`data/README_data/`](data/README_data/) for availability.

## Citation

```bibtex
@inproceedings{edge2026csip4,
  author    = {Edge, Peter and Zhang, Zhongwei and Askarinejad, Hossein},
  title     = {Embedding Physical Layer Fingerprints into {P4} Networks},
  booktitle = {Proc. International Conference on ... (ICECER)},
  year      = {2026}
}
```

## License

Released under the MIT License. See [LICENSE](LICENSE).
