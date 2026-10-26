/*
 * csi_fingerprint.p4
 * ------------------
 * PLACEHOLDER — replace with your working P4 program.
 *
 * Main pipeline for CSI token parsing and five-stage ingress enforcement:
 *   1. Parse Ethernet + EtherType 0x88B5, check token present
 *   2. Node policy exact match (t_node_policy)
 *   3. Fingerprint ternary match with tolerance mask (t_fingerprint)
 *   4. Epoch freshness via per-node register (r_last_epoch)
 *   5. Accept: write epoch, increment cnt_accept, forward
 *
 * Counters: cnt_drop_missing, cnt_drop_unknown, cnt_drop_fp_mismatch,
 *           cnt_drop_stale, cnt_accept
 *
 * Target: BMv2 v1model.
 */

/* Drop your actual csi_fingerprint.p4 source here. */
