# CSI Token Wire Format

The CSI token is a fixed 18-byte structure appended after the Ethernet header,
identified by EtherType `0x88B5`. It is parsed by the P4 pipeline before the
network-layer payload.

## Header structure

```
header csi_token_t {
    bit<8>  ver_type;     // Version and token type
    bit<8>  flags;        // Policy and status flags
    bit<16> node_id;      // Logical node identifier
    bit<32> epoch;        // Timestamp / replay protection
    bit<64> fingerprint;  // CSI-derived PHY fingerprint (see below)
    bit<16> next_etype;   // Encapsulated protocol
}
```

Total: 2 + 2 + 4 + 8 + 2 = 18 bytes.

## Fingerprint field (64 bits)

The 64-bit fingerprint packs four 8-bit hardware-intrinsic feature bins in its
high 32 bits, with the low 32 bits reserved:

| Bits    | Field    | Feature                          |
|---------|----------|----------------------------------|
| [63:56] | cfo_bin  | Carrier frequency offset         |
| [55:48] | iq_bin   | IQ amplitude imbalance           |
| [47:40] | pnl_bin  | Residual phase non-linearity     |
| [39:32] | ant_bin  | Cross-antenna phase differential |
| [31:0]  | reserved | Zero-padded, future extension    |

4 x 8 bits + 32 reserved = 64 bits.

## Feature calibration ranges

Each feature is quantised into an 8-bit bin using fixed calibration ranges:

| Feature                     | Range              |
|-----------------------------|--------------------|
| Carrier frequency offset    | [-0.15, +0.15] rad/pkt |
| IQ amplitude imbalance      | [-2.0, +2.0] dB    |
| Residual phase non-linearity| [-pi, +pi] rad     |
| Cross-antenna phase         | [-pi, +pi] rad     |

## Notes

- `reserved` (24 -> 32 bits) is zero-padded and available for additional
  features in future revisions.
- Residual phase non-linearity is computed after removing the linear,
  channel-induced phase ramp, isolating the frontend's intrinsic phase
  distortion. It contributes cross-vendor discrimination; carrier frequency
  offset provides finer same-vendor separation.
