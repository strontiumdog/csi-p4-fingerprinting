#!/usr/bin/env python3
"""
pico_pnl_extract.py  —  PicoScenes .csi parser + PNL extraction
================================================================
Direct parser for PicoScenes format version 0x315, validated against
AX200/AX210 injection captures at 5.25 GHz HE 20 MHz.

Confirmed CSI segment layout (bytes after 'CSI\\x00' + segver byte):
  @0  u16  reserved (0)
  @2  u8   packetFormat (32 = HE-SU)
  @3  u16  deviceType (0x4d=AX200 class, 0x51=AX210 class)
  @5  u16  CBW (20/40/80 MHz)
  @7  u64  carrierFreq (Hz)
  @15 u64  samplingRate (Hz)
  @23 u32  subcarrierBandwidth (Hz)
  @27 u16  numTones
  @29 u8   numTx
  @30 u8   numRx
  @31 u8   numESS
  @32 u16  numCSI
  then: subcarrier index list (numTones x int16), then
        complex CSI (numTones*numTx*numRx x [int16 real, int16 imag])

PNL = std of per-subcarrier phase AFTER linear de-trend (removes CFO
residual + STO + detection delay). PicoScenes provides STO-corrected
phase, so PNL here is cleaner than the FeitCSI estimate.

Usage:
    python pico_pnl_extract.py /folder/with/csi
Outputs:
    pico_pnl_summary.csv
    pico_pnl_by_device.png
    pico_pnl_feasibility.txt
"""

import struct
import numpy as np
import os
import sys
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def parse_frames(raw):
    frames, pos, n = [], 0, len(raw)
    while pos + 4 < n:
        flen = struct.unpack('<I', raw[pos:pos + 4])[0]
        if flen <= 0 or pos + 4 + flen > n:
            break
        frames.append(raw[pos + 4:pos + 4 + flen])
        pos += 4 + flen
    return frames


def parse_csi_segment(frame):
    idx = frame.find(b'CSI\x00')
    if idx < 0:
        return None
    p = idx + 5  # skip 'CSI\0' + segver byte
    try:
        pktfmt = frame[p + 2]
        devtype = struct.unpack('<H', frame[p + 3:p + 5])[0]
        cbw = struct.unpack('<H', frame[p + 5:p + 7])[0]
        p2 = p + 7
        cfreq = struct.unpack('<q', frame[p2:p2 + 8])[0]; p2 += 8
        srate = struct.unpack('<q', frame[p2:p2 + 8])[0]; p2 += 8
        subbw = struct.unpack('<I', frame[p2:p2 + 4])[0]; p2 += 4
        ntones = struct.unpack('<H', frame[p2:p2 + 2])[0]; p2 += 2
        ntx = frame[p2]; p2 += 1
        nrx = frame[p2]; p2 += 1
        ness = frame[p2]; p2 += 1
        ncsi = struct.unpack('<H', frame[p2:p2 + 2])[0]; p2 += 2

        if ntones <= 0 or ntones > 4096 or ntx == 0 or nrx == 0:
            return None

        # subcarrier index list: numTones x int16
        sc_idx = np.frombuffer(frame[p2:p2 + ntones * 2], dtype='<i2')
        p2 += ntones * 2

        # complex CSI: ntones*ntx*nrx pairs of int16 (real, imag)
        n_vals = ntones * ntx * nrx
        csi_raw = np.frombuffer(frame[p2:p2 + n_vals * 4], dtype='<i2').astype(np.float64)
        if len(csi_raw) < n_vals * 2:
            return None
        csi_c = csi_raw[0::2] + 1j * csi_raw[1::2]
        csi_c = csi_c.reshape(ntones, ntx * nrx)
        return dict(devtype=devtype, cbw=cbw, cfreq=cfreq, ntones=ntones,
                    ntx=ntx, nrx=nrx, sc_idx=sc_idx.astype(np.float64), csi=csi_c)
    except (struct.error, ValueError, IndexError):
        return None


def frame_pnl(seg):
    """Per-frame PNL: std of residual phase after linear de-trend, averaged over Rx."""
    csi = seg['csi']
    x = seg['sc_idx']
    ntones = seg['ntones']
    if len(x) != ntones:
        x = np.arange(ntones, dtype=np.float64)
    pnls = []
    for col in range(csi.shape[1]):
        c = csi[:, col]
        mag = np.abs(c)
        valid = mag > 0
        if valid.sum() < ntones * 0.5:
            continue
        ph = np.unwrap(np.angle(c[valid]))
        xv = x[valid]
        A = np.vstack([xv, np.ones_like(xv)]).T
        coef, *_ = np.linalg.lstsq(A, ph, rcond=None)
        residual = ph - A @ coef
        pnls.append(np.std(residual))
    return np.mean(pnls) if pnls else np.nan


def device_from_name(f):
    f = f.lower()
    tag = 'AX210' if 'ax210' in f else 'AX200' if 'ax200' in f else 'unknown'
    if 'true_inject' in f or ('inject' in f and 'true' in f):
        mode = 'inject'
    elif 'inject' in f:
        mode = 'inject'
    elif 'passive' in f:
        mode = 'passive'
    else:
        mode = 'other'
    return tag, mode


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else '.'
    files = sorted(f for f in os.listdir(folder) if f.endswith('.csi'))
    rows = []
    groups = {}  # (device, mode) -> [pnl per frame]

    for fname in files:
        raw = open(os.path.join(folder, fname), 'rb').read()
        frames = parse_frames(raw)
        pnls = []
        dt = None
        for fr in frames:
            seg = parse_csi_segment(fr)
            if seg is None:
                continue
            dt = seg['devtype']
            v = frame_pnl(seg)
            if np.isfinite(v):
                pnls.append(v)
        dev, mode = device_from_name(fname)
        if pnls:
            arr = np.array(pnls)
            groups.setdefault((dev, mode), []).extend(arr.tolist())
            rows.append((fname, dev, mode, hex(dt) if dt else '?', len(arr),
                         float(np.mean(arr)), float(np.std(arr))))
        else:
            rows.append((fname, dev, mode, '?', 0, np.nan, np.nan))

    with open(os.path.join(folder, 'pico_pnl_summary.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['file', 'device', 'mode', 'devtype_hex', 'n_frames',
                    'pnl_mean_rad', 'pnl_std_rad'])
        w.writerows(rows)

    lines = ["PicoScenes PNL (STO-corrected) — by device and capture mode\n"]
    for (dev, mode) in sorted(groups):
        a = np.array(groups[(dev, mode)])
        lines.append(f"  {dev:<7} {mode:<8} n={len(a):<6} "
                     f"PNL mean={np.mean(a):.4f} rad  std={np.std(a):.4f}")
    # injection-mode class separation (the paper's Option B story)
    inj = {d: np.array(groups[(d, m)]) for (d, m) in groups if m == 'inject'}
    if len(inj) >= 2:
        means = {d: np.mean(v) for d, v in inj.items()}
        spread = max(means.values()) - min(means.values())
        within = np.mean([np.std(v) for v in inj.values()])
        ratio = spread / within if within > 0 else float('inf')
        lines.append(f"\n  Injection-mode AX200 vs AX210 separation: {ratio:.2f}x "
                     f"(spread {spread:.4f} / intra {within:.4f})")
        lines.append("  verdict: " + ("CLEAN" if ratio > 1.5 else "MARGINAL (same-vendor, expected)"))
    open(os.path.join(folder, 'pico_pnl_feasibility.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))

    # plot injection vs passive per device
    if groups:
        keys = sorted(groups)
        fig, ax = plt.subplots(figsize=(1.6 * len(keys) + 2, 3.4))
        ax.boxplot([groups[k] for k in keys],
                   tick_labels=[f'{d}\n{m}' for d, m in keys], showfliers=False)
        ax.set_ylabel('PNL (rad)')
        ax.set_title('PicoScenes PNL — STO-corrected phase')
        ax.tick_params(axis='x', labelsize=7)
        plt.tight_layout()
        plt.savefig(os.path.join(folder, 'pico_pnl_by_device.png'), dpi=150)
        print("\nWrote pico_pnl_summary.csv, pico_pnl_feasibility.txt, pico_pnl_by_device.png")


if __name__ == '__main__':
    main()
