#!/usr/bin/env python3
"""
pnl_extract.py  —  Residual Phase Non-Linearity (PNL) from FeitCSI .dat
=======================================================================
FeitCSI .dat extractor. Complements pico_pnl_extract.py (PicoScenes).

IMPORTANT — interpretation note (validated Aug 2026):
  FeitCSI lacks the STO-correction field that PicoScenes provides, so
  absolute PNL magnitudes here are INFLATED by residual sampling-time
  offset. Use FeitCSI PNL for CROSS-VENDOR separation only (Intel high,
  Broadcom low). For clean same-vendor / absolute values use the
  PicoScenes path — it showed AX200 vs AX210 do NOT separate on PNL
  (0.26x), confirming PNL is a complementary cross-vendor feature, with
  CFO remaining the within-family discriminator.

Header layout (confirmed from byte probe):
  @0x00 u32  record payload size
  @0x04 u32  field1 (=4)
  @0x34 u32  subcarrier count (242 / 484 / 996)
  payload    int16 (I,Q) pairs, 8 bytes/subcarrier
  -32768     invalid/guard sentinel

BANDWIDTH WARNING: PNL is measured across subcarriers, so 242 / 484 / 996
captures are NOT comparable. Script groups by (device, bandwidth) and never
mixes. Repeat-capture regime should fix bandwidth per session.

Usage:  python pnl_extract.py /folder/with/dat
"""

import struct
import numpy as np
import os
import sys
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SENTINEL = -32768


def device_class(fname):
    """
    Device map — complete across both FeitCSI .dat batches.
    Grouped by silicon vendor (PNL separates cross-vendor on FeitCSI):

      Intel family (high PNL on FeitCSI):
        AX201_win        win_s4..s7          Intel AX201
        Intel8265_tosh   Toshiba_Ubuntu_*    Intel 8265
        AX210            ax210pi5_*          Intel AX210
        HP_win           HP_Windows_*        Intel (HP laptop, Windows)
        HP_ubu           HP_Ubuntu_*         Intel (HP laptop, Ubuntu)

      Broadcom family (low PNL on FeitCSI):
        BCM4345          rp15_BCM4345_*      Broadcom BCM4345 (RPi5)
        BCM43xx_Pi3      Pi3Bcom_*           Broadcom (RPi3)

      Unlabelled test devices (verify silicon before thesis use):
        devA             devA_*              behaves Broadcom-like (low PNL)
        devB             devB_*              behaves Intel-like (high PNL)
    """
    f = fname.lower()
    # Intel family
    if f.startswith('win_'):           return 'AX201_win'
    if 'toshiba' in f:                 return 'Intel8265_tosh'
    if 'ax210' in f:                   return 'AX210'
    if 'hp_windows' in f:              return 'HP_win'
    if 'hp_ubuntu' in f:               return 'HP_ubu'
    # Broadcom family
    if 'bcm4345' in f or 'rp15' in f:  return 'BCM4345'
    if 'pi3bcom' in f:                 return 'BCM43xx_Pi3'
    # unlabelled test devices
    if 'deva' in f:                    return 'devA'
    if 'devb' in f:                    return 'devB'
    return 'unknown'


def read_dat(filepath):
    with open(filepath, 'rb') as fh:
        raw = fh.read()
    rec_sz = struct.unpack('<I', raw[0:4])[0]
    n_sub = struct.unpack('<I', raw[0x34:0x38])[0]
    if n_sub not in (242, 484, 996):
        return n_sub, []
    expected = n_sub * 8
    frames = []
    pos = 0x60
    while pos + expected <= len(raw):
        block = raw[pos:pos + expected]
        ints = np.frombuffer(block, dtype='<i2').astype(np.float64).reshape(-1, 4)
        I, Q = ints[:, 0], ints[:, 1]
        valid = (I != SENTINEL) & (Q != SENTINEL)
        csi = np.where(valid, I + 1j * Q, np.nan)
        if np.isfinite(csi).sum() > n_sub * 0.5:
            frames.append(csi)
        pos += max(rec_sz, expected)
    return n_sub, frames


def extract_pnl(frames, n_sub):
    sc_idx = np.arange(n_sub)
    out = []
    for csi in frames:
        valid = np.isfinite(csi)
        if valid.sum() < n_sub * 0.5:
            continue
        ph = np.unwrap(np.where(valid, np.angle(csi), 0.0))
        x, y = sc_idx[valid], ph[valid]
        A = np.vstack([x, np.ones_like(x)]).T
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        out.append(np.std(y - A @ coef))
    return np.array(out)


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else '.'
    files = sorted(f for f in os.listdir(folder) if f.endswith('.dat'))
    rows = []
    by_class_bw = {}
    for fname in files:
        n_sub, frames = read_dat(os.path.join(folder, fname))
        cls = device_class(fname)
        if not frames:
            rows.append((fname, cls, n_sub, 0, np.nan, np.nan))
            continue
        pnl = extract_pnl(frames, n_sub)
        if len(pnl) == 0:
            rows.append((fname, cls, n_sub, 0, np.nan, np.nan))
            continue
        by_class_bw.setdefault((cls, n_sub), []).extend(pnl.tolist())
        rows.append((fname, cls, n_sub, len(pnl),
                     float(np.mean(pnl)), float(np.std(pnl))))

    with open(os.path.join(folder, 'pnl_summary.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['file', 'class', 'n_subcarriers', 'n_frames',
                    'pnl_mean_rad', 'pnl_std_rad'])
        w.writerows(rows)

    lines = ["PNL FEASIBILITY — grouped by bandwidth (never mix subcarrier counts)\n"]
    for bw in (242, 484, 996):
        keys = [k for k in by_class_bw if k[1] == bw]
        if not keys:
            continue
        lines.append(f"\n=== {bw} subcarriers ===")
        means = {}
        for (cls, _bw) in sorted(keys):
            vals = np.array(by_class_bw[(cls, bw)])
            means[cls] = np.mean(vals)
            lines.append(f"  {cls:<16} n={len(vals):<5} "
                         f"PNL mean={np.mean(vals):.4f} rad  std={np.std(vals):.4f}")
        if len(means) >= 2:
            spread = max(means.values()) - min(means.values())
            within = np.mean([np.std(np.array(by_class_bw[(c, bw)])) for c in means])
            ratio = spread / within if within > 0 else float('inf')
            lines.append(f"  --> inter-class spread {spread:.4f} / "
                         f"intra {within:.4f} = {ratio:.2f}x")
            lines.append("  --> " + ("CLEAN cross-vendor" if ratio > 1.5 else "MARGINAL"))
    open(os.path.join(folder, 'pnl_feasibility.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))

    bws = sorted({k[1] for k in by_class_bw})
    if bws:
        fig, axes = plt.subplots(1, len(bws), figsize=(5 * len(bws), 3.2), squeeze=False)
        for ax, bw in zip(axes[0], bws):
            keys = sorted(k for k in by_class_bw if k[1] == bw)
            ax.boxplot([by_class_bw[k] for k in keys],
                       tick_labels=[k[0] for k in keys], showfliers=False)
            ax.set_title(f'{bw} subcarriers')
            ax.set_ylabel('PNL (rad)')
            ax.tick_params(axis='x', rotation=45, labelsize=7)
        plt.tight_layout()
        plt.savefig(os.path.join(folder, 'pnl_by_class.png'), dpi=150)


if __name__ == '__main__':
    main()
