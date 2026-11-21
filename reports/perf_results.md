# Performance Evaluation Summary & Coverage Report

This report summarizes the current state of the performance evaluation across [`latex/chapters/evaluation.tex`](../latex/chapters/evaluation.tex), [`latex/chapters/introduction.tex`](../latex/chapters/introduction.tex), and [`analysis/config.json`](../analysis/config.json) (with generated data in [`analysis/charts/`](../analysis/charts/)).

> **Metric Sign Convention (`evaluation.tex` §5.1):** All relative changes are reported as $\left(\frac{\text{test}}{\text{base}} - 1\right) \times 100\%$ over benchmarks where the compiled binary hash differs between `base` and `test`.
> - **`< 0%` (negative)** = **Improvement / Win** (faster runtime, faster compile, smaller binary).
> - **`> 0%` (positive)** = **Regression / Loss** (slower runtime, slower compile, larger binary).
> - In the tables below, **Best (Min $\Delta\%$)** is the largest speedup (most negative $\Delta\%$), and **Worst (Max $\Delta\%$)** is the largest slowdown (most positive $\Delta\%$).

---

## 1. Experimental Conditions Matrix (Measured vs. Missing)

The evaluation spans **4 optimizations** across **3 compiler/suite environments** and **5 control/ablation settings**:
- **Optimizations:**
  1. `PreFlatten (tuple)`: Late phase (after `Flatten`), tail calls only (`tail_only`), local resolve, consumer policy `always`, 10 recursive steps.
  2. `PreFlatten (con)` (`ConApp`): Early phase (before `Flatten`), all calls (`always`), local resolve, consumer policy `always`, 10 recursive steps.
  3. `ShallowFlatten (aos)`: Array-of-Structs container flattening (`maxWidthSameType:3` or `4`).
  4. `ShallowFlatten (soa)`: Struct-of-Arrays container flattening (`maxWidthSameType:3` or `4`).
- **Compiler / Suite Environments:**
  1. **MLton / `mlton` suite**: Single-core (1c), 45 total benchmarks (measures run time, compile time, binary size).
  2. **MLton / `parallel-ml-bench`**: Single-core (1c), 34 total benchmarks (measures run time, binary size).
  3. **MPL / `parallel-ml-bench`**: Multi-core (`procs` $\in \{1, 2, 4, 8, 16, 32, 64, 80, 128, 160\}$), 34 total benchmarks (measures run time across cores, binary size).

### Coverage Matrix

Legend:
- **In Text + Config**: Measured in [`analysis/config.json`](../analysis/config.json) and plotted/discussed in [`latex/chapters/evaluation.tex`](../latex/chapters/evaluation.tex).
- **Config Only (Not in Text)**: Measured in [`analysis/config.json`](../analysis/config.json) and charts generated in [`analysis/charts/`](../analysis/charts/), but **not plotted or discussed** in [`latex/chapters/evaluation.tex`](../latex/chapters/evaluation.tex).
- **MISSING**: No measurement in `config.json` or `analysis/data/`.

| Optimization | Compiler / Suite | Default (`coalesce`) | `-chunkify one` | `-chunkify func` | Baseline Fixup (`Simplify`) | Fixed Trials (`fixed_iters`) | Sync GC (`sync_gc`) | `perf stat` Top-Down |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`PreFlatten` (`tuple`)** | **MLton / `mlton`** (1c) | In Text + Config | *Config Only* | **MISSING** | **MISSING** | N/A | N/A | — |
| | **MLton / `parallel_bench`** (1c) | In Text + Config | *Config Only* | **MISSING** | **MISSING** | **MISSING** | N/A | — |
| | **MPL / `parallel_bench`** (1–160c) | In Text + Config | In Text + Config | *Config Only* | In Text + Config | **MISSING** | **MISSING** | `delaunay`, `bfs` (1c, 160c) |
| **`PreFlatten` (`con`)** | **MLton / `mlton`** (1c) | In Text + Config | In Text + Config | **MISSING** | **MISSING** | N/A | N/A | — |
| | **MLton / `parallel_bench`** (1c) | In Text + Config | In Text + Config | **MISSING** | **MISSING** | **MISSING** | N/A | — |
| | **MPL / `parallel_bench`** (1–160c) | In Text + Config | In Text + Config | *Config Only* | **MISSING** | **MISSING** | **MISSING** | — |
| **`ShallowFlatten` (`aos`)** | **MLton / `mlton`** (1c) | In Text + Config | **MISSING** | **MISSING** | N/A | N/A | N/A | — |
| | **MLton / `parallel_bench`** (1c) | In Text + Config | **MISSING** | **MISSING** | N/A | **MISSING** | N/A | `delaunay`, `linearrec` (1c) |
| | **MPL / `parallel_bench`** (1–160c) | In Text + Config | In Text + Config | *Config Only* | N/A | In Text + Config | In Text + Config | `quickhull`, `linearrec` (1c, 160c) |
| **`ShallowFlatten` (`soa`)** | **MLton / `mlton`** (1c) | In Text + Config | **MISSING** | **MISSING** | N/A | N/A | N/A | — |
| | **MLton / `parallel_bench`** (1c) | In Text + Config | **MISSING** | **MISSING** | N/A | **MISSING** | N/A | `delaunay`, `linearrec` (1c) |
| | **MPL / `parallel_bench`** (1–160c) | In Text + Config | *Config Only* | **MISSING** | N/A | *Config Only* | *Config Only* | — |

---

## 2. Measured Run-Time Results (`test / base - 1`)

### 2A. Single-Core Benchmarks (MLton Compiler)

| Suite | Condition (`config.json` key) | Optimization & Setting | Impacted Benchmarks | Geomean $\Delta\%$ | Best Win (Min $\Delta\%$) | Worst Regression (Max $\Delta\%$) | Status in `evaluation.tex` |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **`mlton`** | `tuple` | `PreFlatten` (tuple, default) | 7 / 45 | **-0.45%** | **-4.45%** (`count-graphs`) | **+2.28%** (`hamlet`) | Fig. 5.2 (§5.2.1) |
| **`mlton`** | `tuple_chunkify_one` | `PreFlatten` (tuple, `-chunkify one`) | 7 / 45 | **+0.99%** | **-0.02%** (`simple`) | **+2.84%** (`model-elimination`) | *Not in text* (`config.json` only) |
| **`mlton`** | `con` | `PreFlatten` (`ConApp`, default) | 23 / 45 | **-0.98%** | **-22.29%** (`wc-input1`) | **+8.82%** (`logic`) | Fig. 5.8 (§5.3.1) |
| **`mlton`** | `con_chunkify_one` | `PreFlatten` (`ConApp`, `-chunkify one`) | 22 / 45 | **+0.33%** | **-3.28%** (`count-graphs`) | **+11.77%** (`logic`) | Fig. 5.9 (§5.4) |
| **`mlton`** | `aos` | `ShallowFlatten` (AoS, default) | 1 / 45 | **-0.27%** | **-0.27%** (`flat-array`) | **-0.27%** (`flat-array`) | Fig. 5.15 (§5.6.1) |
| **`mlton`** | `soa` | `ShallowFlatten` (SoA, default) | 1 / 45 | **-0.28%** | **-0.28%** (`flat-array`) | **-0.28%** (`flat-array`) | Fig. 5.25 (§5.7.1) |
| **`parallel_bench`** | `tuple` | `PreFlatten` (tuple, default) | 11 / 11* | **+4.23%** | **-1.64%** (`delaunay`) | **+18.21%** (`reverb`) | Fig. 5.3 (§5.2.2) |
| **`parallel_bench`** | `tuple_chunkify_one` | `PreFlatten` (tuple, `-chunkify one`) | 11 / 11* | **-0.77%** | **-3.84%** (`range-query`) | **+2.76%** (`msort-ints`) | *Not in text* (`config.json` only) |
| **`parallel_bench`** | `con` | `PreFlatten` (`ConApp`, default) | 34 / 34 | **-2.65%** | **-54.87%** (`linearrec`) | **+21.49%** (`linefit-opt`) | Fig. 5.10 (§5.5) |
| **`parallel_bench`** | `con_chunkify_one` | `PreFlatten` (`ConApp`, `-chunkify one`) | 34 / 34 | **-2.92%** | **-50.44%** (`linearrec`) | **+15.44%** (`mcss-opt`) | Fig. 5.11 (§5.5) |
| **`parallel_bench`** | `aos` | `ShallowFlatten` (AoS, default) | 11 / 11* | **-11.40%** | **-64.48%** (`linearrec`) | **+16.14%** (`linefit-opt`) | Fig. 5.16 (§5.6.2) |
| **`parallel_bench`** | `soa` | `ShallowFlatten` (SoA, default) | 11 / 11* | **-10.34%** | **-54.90%** (`linearrec`) | **+26.72%** (`delaunay`) | Fig. 5.26–5.27 (§5.7.2) |

*\*Note: For `parallel-ml-bench`, the processed `.jsonl` files pre-filter or only run the subset of benchmarks impacted by the pass (11 for `tuple`/`aos`/`soa` on MLton, 21 for `tuple` on MPL, 34 for `con`, 11 for `aos`/`soa` on MPL).*

---

### 2B. Multi-Core Benchmarks (MPL Compiler on `parallel-ml-bench`)

All MPL configurations are measured across 10 core counts: `procs` $\in \{1, 2, 4, 8, 16, 32, 64, 80, 128, 160\}$.

| Condition (`config.json` key) | Optimization & Setting | Impacted Benches | 1-Core Geomean (Best / Worst) | 160-Core Geomean (Best / Worst) | Geomean Range Across All Cores | Overall Best Win (Min $\Delta\%$ Across All Cores) | Overall Worst Loss (Max $\Delta\%$ Across All Cores) | Status in `evaluation.tex` |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **`tuple`** | `PreFlatten` (tuple, default) | 21 | **+0.33%**<br>(-4.73% `bfs` / +9.77% `delaunay`) | **-0.85%**<br>(-16.54% `tokens` / +9.03% `nearest-nbrs`) | **-0.85%** (160c) to **+0.89%** (64c) | **-16.54%**<br>(`tokens` @ 160c) | **+11.58%**<br>(`msort-strings` @ 64c) | Fig. 5.5 (§5.2.3) |
| **`tuple_vs_fixup`** | `PreFlatten` (tuple, baseline fixup) | 21 | **+0.46%**<br>(-3.80% `bfs` / +8.27% `delaunay`) | **-0.18%**<br>(-6.72% `bfs` / +15.91% `tokens`) | **-1.46%** (128c) to **+0.62%** (8c) | **-12.10%**<br>(`tokens` @ 128c) | **+15.91%**<br>(`tokens` @ 160c) | Fig. 5.6–5.7 (§5.2.6) |
| **`tuple_chunkify_func`** | `PreFlatten` (tuple, `-chunkify func`) | 21 | **+1.03%**<br>(-2.03% `centrality` / +22.52% `seam-carve`) | **-1.37%**<br>(-10.84% `tokens` / +2.86% `nearest-nbrs`) | **-1.65%** (128c) to **+1.03%** (1c) | **-18.20%**<br>(`tokens` @ 128c) | **+22.52%**<br>(`seam-carve` @ 1c) | *Not in text* (`config.json` only) |
| **`tuple_chunkify_one`** | `PreFlatten` (tuple, `-chunkify one`) | 21 | **-0.54%**<br>(-6.89% `ocaml-lu-decomp` / +1.76% `low-d-decomp`) | **-0.69%**<br>(-16.99% `tokens` / +10.59% `ocaml-lu-decomp`) | **-1.00%** (2c) to **+0.14%** (80c) | **-16.99%**<br>(`tokens` @ 160c) | **+10.59%**<br>(`ocaml-lu-decomp` @ 160c) | Fig. 5.6–5.8 (§5.2.6) |
| **`con`** | `PreFlatten` (`ConApp`, default) | 34 | **+2.22%**<br>(-2.57% `nqueens` / +48.22% `suffix-array`) | **+0.42%**<br>(-15.02% `tokens` / +45.72% `suffix-array`) | **+0.42%** (160c) to **+2.42%** (80c) | **-15.02%**<br>(`tokens` @ 160c) | **+48.22%**<br>(`suffix-array` @ 1c) | Fig. 5.12 (§5.5.1) |
| **`con_chunkify_func`** | `PreFlatten` (`ConApp`, `-chunkify func`) | 34 | **-0.47%**<br>(-11.46% `integrate-opt` / +3.44% `tinykaboom`) | **+0.10%**<br>(-15.89% `linearrec` / +7.22% `seam-carve`) | **-1.32%** (128c) to **+0.14%** (32c) | **-18.75%**<br>(`msort-strings` @ 128c) | **+11.74%**<br>(`dedup` @ 128c) | *Not in text* (`config.json` only) |
| **`con_chunkify_one`** | `PreFlatten` (`ConApp`, `-chunkify one`) | 34 | **-0.25%**<br>(-6.10% `ocaml-binarytrees5` / +5.13% `ocaml-lu-decomp`) | **-0.91%**<br>(-21.32% `linearrec` / +5.00% `triangle-count`) | **-0.98%** (2c) to **+0.87%** (128c) | **-21.32%**<br>(`linearrec` @ 160c) | **+59.21%**<br>(`linearrec` @ 128c) | Fig. 5.13–5.15 (§5.5.1) |
| **`aos`** | `ShallowFlatten` (AoS, default) | 11 | **-12.50%**<br>(-54.09% `linearrec` / +11.96% `ocaml-game-of-life`) | **-4.06%**<br>(-46.28% `quickhull` / +23.55% `linearrec`) | **-12.50%** (1c) to **-3.50%** (32c) | **-54.09%**<br>(`linearrec` @ 1c) | **+23.55%**<br>(`linearrec` @ 160c) | Fig. 5.17 (§5.6.3) |
| **`aos_chunkify_func`** | `ShallowFlatten` (AoS, `-chunkify func`) | 11 | **-14.09%**<br>(-46.35% `linearrec` / +3.27% `seam-carve`) | **-5.45%**<br>(-46.26% `quickhull` / +6.91% `ocaml-nbody-imm`) | **-14.09%** (1c) to **-4.97%** (80c) | **-46.35%**<br>(`linearrec` @ 1c) | **+18.85%**<br>(`linearrec` @ 80c) | *Not in text* (`config.json` only) |
| **`aos_chunkify_one`** | `ShallowFlatten` (AoS, `-chunkify one`) | 11 | **-13.50%**<br>(-50.65% `linearrec` / +4.17% `seam-carve`) | **-6.13%**<br>(-46.69% `quickhull` / +10.07% `linearrec`) | **-13.50%** (1c) to **-3.59%** (64c) | **-50.65%**<br>(`linearrec` @ 1c) | **+23.86%**<br>(`linearrec` @ 64c) | Fig. 5.23–5.24 (§5.6.6) |
| **`aos_fixed_iters`** | `ShallowFlatten` (AoS, fixed trial count) | 11 | **-16.44%**<br>(-51.28% `linearrec` / +4.40% `seam-carve`) | **-6.06%**<br>(-33.61% `quickhull` / +48.08% `linearrec`) | **-16.44%** (1c) to **-6.06%** (160c) | **-51.28%**<br>(`linearrec` @ 1c) | **+48.08%**<br>(`linearrec` @ 160c) | Fig. 5.19–5.20 (§5.6.6) |
| **`aos_sync_gc`** | `ShallowFlatten` (AoS, synchronous GC) | 11 | **-10.24%**<br>(-40.04% `linearrec` / +13.27% `ocaml-game-of-life`) | **-49.27%**<br>(-96.94% `quickhull` / +3.13% `ocaml-game-of-life`) | **-49.27%** (160c) to **-10.24%** (1c) | **-96.95%** (~33$\times$)<br>(`quickhull` @ 128c) | **+13.27%**<br>(`ocaml-game-of-life` @ 1c) | Fig. 5.21–5.22 (§5.6.6) |
| **`soa`** | `ShallowFlatten` (SoA, default) | 11 | **-9.98%**<br>(-51.64% `linearrec` / +12.58% `ocaml-game-of-life`) | **-3.10%**<br>(-40.37% `quickhull` / +20.12% `linearrec`) | **-9.98%** (1c) to **-2.26%** (80c) | **-51.64%**<br>(`linearrec` @ 1c) | **+20.12%**<br>(`linearrec` @ 160c) | Fig. 5.28–5.29 (§5.7.3) |
| **`soa_chunkify_one`** | `ShallowFlatten` (SoA, `-chunkify one`) | 11 | **-12.83%**<br>(-53.78% `linearrec` / +3.66% `seam-carve`) | **+0.08%**<br>(-41.97% `quickhull` / +55.52% `linearrec`) | **-12.83%** (1c) to **+0.08%** (160c) | **-53.78%**<br>(`linearrec` @ 1c) | **+55.52%**<br>(`linearrec` @ 160c) | *Not in text* (`config.json` only) |
| **`soa_fixed_iters`** | `ShallowFlatten` (SoA, fixed trial count) | 11 | **-14.64%**<br>(-52.26% `linearrec` / +2.74% `seam-carve`) | **-3.78%**<br>(-35.32% `suffix-array` / +27.58% `linearrec`) | **-14.64%** (1c) to **-3.78%** (160c) | **-52.26%**<br>(`linearrec` @ 1c) | **+52.45%**<br>(`linearrec` @ 128c) | *Not in text* (`config.json` only) |
| **`soa_sync_gc`** | `ShallowFlatten` (SoA, synchronous GC) | 11 | **-8.27%**<br>(-41.07% `linearrec` / +12.70% `ocaml-game-of-life`) | **-48.08%**<br>(-96.67% `quickhull` / +2.01% `ocaml-nbody-imm`) | **-48.39%** (128c) to **-8.27%** (1c) | **-96.67%** (~30$\times$)<br>(`quickhull` @ 160c) | **+21.41%**<br>(`ocaml-game-of-life` @ 2c) | *Not in text* (`config.json` only) |

---

### 2C. Compile Time & Binary Size Summary

*(Note: `parallel-ml-bench` records binary size (`binary_bytes`) but does not measure compilation time; `mlton` benchmark suite records both `compileTime` and `binarySize`.)*

| Suite / Compiler | Condition | Compile Time Geomean (Min / Max) | Binary Size Geomean (Min / Max) |
| :--- | :--- | :--- | :--- |
| **MLton / `mlton`** | `tuple` | **+1.97%** (-1.00% `model-elimination` / +4.33% `tensor`) | **+1.73%** (+0.07% `simple` / +4.87% `model-elimination`) |
| | `tuple_chunkify_one` | **+2.67%** (+0.51% `DLXSimulator` / +3.55% `model-elimination`) | **+2.00%** (+0.17% `simple` / +5.42% `model-elimination`) |
| | `con` | **+7.53%** (-1.07% `vliw` / +192.67% `logic`) | **+9.24%** (-1.77% `boyer` / +565.24% `logic`) |
| | `con_chunkify_one` | **+7.92%** (-7.78% `mlyacc` / +244.04% `logic`) | **+10.17%** (-1.42% `boyer` / +676.23% `logic`) |
| | `aos` | **+1.73%** (+1.73% `flat-array`, $n=1$) | **+0.00%** (+0.00% `flat-array`, $n=1$) |
| | `soa` | **+3.29%** (+3.29% `flat-array`, $n=1$) | **+0.18%** (+0.18% `flat-array`, $n=1$) |
| **MLton / `parallel_bench`** | `tuple` | *Not measured* | **+1.71%** (+0.00% `nqueens` / +4.94% `msort`) |
| | `tuple_chunkify_one` | *Not measured* | **+2.07%** (+0.00% `reverb` / +5.43% `nearest-nbrs`) |
| | `con` | *Not measured* | **+0.40%** (-1.67% `ocaml-lu-decomp` / +3.76% `bfs`) |
| | `con_chunkify_one` | *Not measured* | **+0.60%** (-1.70% `ocaml-binarytrees5` / +5.02% `max-indep-set`) |
| | `aos` | *Not measured* | **-0.02%** (-1.27% `tinykaboom` / +1.04% `delaunay`) |
| | `soa` | *Not measured* | **+0.45%** (+0.00% `linearrec` / +2.54% `nearest-nbrs`) |
| **MPL / `parallel_bench`** | `tuple` (all 4 variants) | *Not measured* | **+2.14% to +2.19%** (-1.41% `dense-matmul` / +7.36% `delaunay`) |
| | `con` (all 3 variants) | *Not measured* | **+8.54% to +8.81%** (-0.51% `integrate-opt` / +36.73% `tinykaboom`) |
| | `aos` (all 5 variants) | *Not measured* | **-0.13% to -0.03%** (-1.45% `delaunay` / +0.99% `suffix-array`) |
| | `soa` (all 4 variants) | *Not measured* | **+0.09% to +0.20%** (-0.90% `quickhull` / +1.02% `tinykaboom`) |

---

## 3. Detailed Breakdown of Missing Conditions & Document Discrepancies

### 3A. Missing Experimental Conditions (Not Measured at All)

1. **`ShallowFlatten (soa)` Missing `-chunkify func` on MPL (and Chunkify Controls on MLton):**
   - `ShallowFlatten (aos)` has both `aos_chunkify_one` and `aos_chunkify_func` measured on `mpl/parallel_bench` as a methodological sanity check (§5.6.6).
   - `ShallowFlatten (soa)` now has `soa_chunkify_one` on `mpl/parallel_bench`, but still has **no `-chunkify func` run** on `mpl/parallel_bench` (and neither `aos` nor `soa` has chunkify controls on MLton).

2. **`PreFlatten (con)` Missing Baseline Fixup Control (`con_vs_fixup`):**
   - For `tuple` on MPL, `tuple_vs_fixup` runs post-pass `Simplify` on the baseline to prove that the extra `Simplify` pass is not responsible for the performance difference (§5.2.6).
   - No analogous `con_vs_fixup` control exists for `ConApp` flattening (nor for MLton on either `tuple` or `con`).

3. **`PreFlatten` (`tuple` and `con`) Missing `fixed_iters` and `sync_gc` Controls on MPL:**
   - Only `aos` and `soa` have `fixed_iters` and `sync_gc` runs on `mpl/parallel_bench`.
   - Even though `evaluation.tex` (§5.2.4, line 337) hypothesizes that `bfs`'s vanishing speedup at high core counts under `tuple` is due to GC pauses, and `con_chunkify_one` exhibits a massive +59.21% spike at 128c vs. -21.32% win at 160c on `linearrec`, neither `tuple` nor `con` has `fixed_iters` or `sync_gc` measurements.

4. **Missing `perf stat` Top-Down Profiles for `ConApp` and Multi-Core `SoA`:**
   - `evaluation.tex` includes `perf stat` tables for `tuple` (MPL 1c & 160c on `delaunay`, `bfs`), `aos` (MPL 1c & 160c on `quickhull`, `linearrec`), and single-core MLton `aos` vs. `soa` (1c on `delaunay`, `linearrec`).
   - There are no `perf stat` tables for `con` (`ConApp` flattening) or for 160-core `soa` on MPL.

---

### 3B. Measured in `config.json` / `analysis/charts/` but Missing from `evaluation.tex`

1. **`PreFlatten (tuple)` `-chunkify one` on MLton (`mlton` and `parallel-ml-bench`):**
   - Both `mlton_benchmarks_mlton_vs_mlton.tuple_chunkify_one` and `parallel_bench_benchmarks_mlton_vs_mlton.tuple_chunkify_one` (along with `compare_bar_charts` entries `mlton_tuple_chunkify_one_mlton_bench` and `mlton_tuple_chunkify_one_parallel_bench`) are now configured in [`analysis/config.json`](../analysis/config.json).
   - On `mlton/parallel_bench`, `-chunkify one` flips the default **+4.23%** geomean regression (`reverb` at +18.21%) into a **-0.77%** geomean improvement (`range-query` -3.84%, `msort-strings` -3.37%, `reverb` -3.29%, `msort-ints` +2.76%), confirming that the default slowdown was chunkification noise. On `mlton/mlton`, it shifts the **-0.45%** default geomean to **+0.99%** (`simple` -0.02% / `model-elimination` +2.84%).
   - Neither dataset is plotted or discussed in [`latex/chapters/evaluation.tex`](../latex/chapters/evaluation.tex) yet.

2. **`soa_chunkify_one`, `soa_sync_gc`, and `soa_fixed_iters` (MPL `parallel-ml-bench`):**
   - All three datasets are configured in [`analysis/config.json`](../analysis/config.json#L39-L41) (with `compare_series.soa_chunkify_one_geomean` added for `soa_chunkify_one`).
   - `soa_chunkify_one` reaches **-12.83%** geomean at 1c (`linearrec` -53.78%) and **+0.08%** at 160c (`quickhull` -41.97%, `linearrec` +55.52%).
   - `soa_sync_gc` and `soa_fixed_iters` show the exact same dramatic GC effect as AoS (`soa_sync_gc` reaches **-48.39% geomean** at 128c and **-48.08%** at 160c, with `quickhull` at **-96.67%**).
   - However, §5.7.3 of [`latex/chapters/evaluation.tex`](../latex/chapters/evaluation.tex) only includes the default `soa` plot and `soa_vs_aos_geomean.pdf`, never mentioning or plotting `soa_chunkify_one`, `soa_sync_gc`, or `soa_fixed_iters` (and `config.json` still lacks `compare_series` entries for `soa_sync_gc_geomean` and `soa_fixed_iters_geomean`).

3. **`-chunkify func` Runs (`tuple_chunkify_func`, `con_chunkify_func`, `aos_chunkify_func`):**
   - All three are present in [`analysis/config.json`](../analysis/config.json#L28-L34) (and `aos_exp_geomean` in `config.json` even plots `aos_chunkify_func`), with `.pdf` and `.csv` files generated in `analysis/charts/`.
   - None of the `-chunkify func` results are mentioned or included in [`latex/chapters/evaluation.tex`](../latex/chapters/evaluation.tex).

---

### 3C. Stale Prose / Config Mismatches in `evaluation.tex` Found During Audit

1. **Stale `PreFlatten (tuple)` Configuration on `mlton/parallel_bench` & `mpl/parallel_bench`:**
   - On Oct 13, `mlton_benchmarks_mlton_vs_mlton.tuple` was updated in `config.json` to `tuple_test_o3_fixed_downgrade` (`-pre-flatten-consumer-policy always -pre-flatten-resolve-policy local`, per the note in [`latex/chapters/preflatten.tex`](../latex/chapters/preflatten.tex#L781)).
   - However, `parallel_bench_benchmarks_mlton_vs_mlton.tuple` (`mlton_tuple_mlton_parallel_o3`, Aug 25) and `parallel_bench_benchmarks_mpl_vs_mpl.tuple` (`mpl_tuple_mpl_parallel_o3_morecores`, Aug 26) still point to runs from late August before that Oct 13 downgrade fix.
2. **Stale Numbers / Descriptions in `evaluation.tex` Text:**
   - **§5.2 (`evaluation.tex` line 114):** States `PreFlatten` *"only transforms non-tail-recursive functions"*, whereas `preflatten.tex` (line 784) and the actual compiler flag (`-pre-flatten-transfer-policy tail_only`) transform **only tail-recursive calls**.
   - **§5.2.2 (`evaluation.tex` line 174):** Describes `tuple` on MLton `parallel-ml-bench` as *"broadly neutral"* except for `reverb`, whereas the plotted data (`tuple_parallel_bench_run_mlton_vs_mlton.csv`) has a **+4.23% geomean regression** across 11 benchmarks.
   - **§5.3.1 (`evaluation.tex` line 675):** Text says the MLton suite under `ConApp` *"shows modest $\approx 5\%$ regressions on a number of benchmarks, for an overall geomean loss. We'll investigate the large loss to `wc-input1`"*, with a `\hl{TODO: THIS IS NOW A WIN}` above it. In the current data, `con` is a **-0.98% geomean win** and `wc-input1` is a **-22.29% win** (which disappears under `-chunkify one`, turning into a **+0.33% geomean loss**).
   - **§5.5 (`evaluation.tex` line 747):** Text cites a *"strong geomean win of 4.1%"* for `con` on MLton `parallel-ml-bench`; the current chart (`con_parallel_bench_run_mlton_vs_mlton.pdf`) reports **-2.65%** (`-2.7%` on chart) default and **-2.92%** (`-2.9%` on chart) under `-chunkify one`.
   - **§5.1 (`evaluation.tex` line 34) & §5.6/5.7 (`evaluation.tex` line 857):** §5.1 says benchmarks were compiled with `-O2`, whereas the actual data files in `config.json` use `-cc-opt -O3` (except `mlton_only_chunkify_one`, which used `-cc-opt -O2`). Similarly, §5.6/5.7 say containers-of-tuples of $\le 3$ elements were flattened, whereas the `-O3` data files in `mlton_benchmarks_mlton_vs_mlton` passed `maxWidthSameType:4`.
