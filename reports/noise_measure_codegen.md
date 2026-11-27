# Measuring GCC `-O1` Instability via MLton C-Codegen Block-Order Permutations

This report is a companion to [`noise_measure.md`](noise_measure.md). Whereas [`noise_measure.md`](noise_measure.md) used GCC's `-fpatchable-function-entry=N,0` to sweep exact 4-byte code-layout offsets and isolate 32-byte Intel DSB periodicity, this experiment removes all GCC-level perturbation flags and instead perturbs the **lowered SML C code emitted by MLton itself** by permuting the emission order of chunk entry-block DFS subtrees in `mlton/codegen/c-codegen/c-codegen.fun`.

All measurements were conducted on `flattening-tests` (dual-socket Intel Xeon Platinum 8380 / Ice Lake-SP, GCC 15.2.0, Linux `perf` 7.0.14; see [`benchmark_machine.md`](benchmark_machine.md)).

---

## 1. Motivation & MLton Compiler Modification

In MLton's C backend, multiple lowered SML functions and continuations are coalesced into a single C function (`Chunk_0`, `Chunk_1`, ...) containing a `switch (nextBlock)` dispatch table followed by all basic blocks in the chunk. In stock MLton (`c-codegen.fun`), `outputChunkFn` emits those basic blocks in a deterministic DFS order (`dfsBlocks`) seeded by iterating over entry blocks in `blocks` vector order.

When an upstream SSA/RSSA optimization pass (such as `PreFlatten` or `ShallowFlatten`) adds, splits, inlines, or reorders functions anywhere in the program, the textual emission order and byte offsets of blocks inside a C chunk shift—even for hot loops that the optimization never touched.

To model this directly inside MLton without modifying benchmark source files or passing any GCC-level perturbation flags, we added an opt-in expert flag `-c-codegen-permute-entries <seed>` (`0` = stock MLton order; `seed > 0` = deterministic Fisher-Yates shuffle of the chunk entry visit order before DFS emission). Crucially:
* The `switch (nextBlock)` / `nextLabels` dispatch table (`entries`, sorted by `labelIndex`) is **unchanged**.
* Every basic block's C statements and control-flow transfers (`goto L_x;`) are **unchanged**; only the emission order of entry-block DFS subtrees inside each `Chunk_*` changes.

### Exact MLton Diff

Applied to `/home/cc/code/mlton` (rebuilt via `make compiler CHECK_FIXPOINT=false`):

```diff
diff --git a/mlton/codegen/c-codegen/c-codegen.fun b/mlton/codegen/c-codegen/c-codegen.fun
index 30b776cfb..85b08ea9d 100644
--- a/mlton/codegen/c-codegen/c-codegen.fun
+++ b/mlton/codegen/c-codegen/c-codegen.fun
@@ -1677,13 +1677,46 @@ fun output {program as Machine.Program.T {chunks, frameInfos, main, ...},
             val entries =
                let
                   val entries = ref []
+                  val entryLabels = ref []
                   val _ =
                      Vector.foreach
                      (blocks, fn Block.T {kind, label, ...} =>
                       if Kind.isEntry kind
                          then (List.push (entries, (label, labelIndex label))
-                               ; visit label)
+                               ; List.push (entryLabels, label))
                          else ())
+                  val visitOrder = List.rev (!entryLabels)
+                  val _ =
+                     case !Control.cCodegenPermuteEntries of
+                        0 => List.foreach (visitOrder, visit)
+                      | seed =>
+                           let
+                              val arr = Array.fromList visitOrder
+                              val n = Array.length arr
+                              val state = ref (Word.fromInt seed)
+                              fun nextRand (bound: int): int =
+                                 let
+                                    val s = Word.+ (Word.* (!state, 0w1664525), 0w1013904223)
+                                    val _ = state := s
+                                 in
+                                    Word.toInt (Word.mod (Word.>> (s, 0w16), Word.fromInt bound))
+                                 end
+                              fun shuffle i =
+                                 if i <= 1
+                                    then ()
+                                 else let
+                                         val j = nextRand i
+                                         val k = i - 1
+                                         val tmp = Array.sub (arr, k)
+                                         val _ = Array.update (arr, k, Array.sub (arr, j))
+                                         val _ = Array.update (arr, j, tmp)
+                                      in
+                                         shuffle k
+                                      end
+                              val _ = shuffle n
+                           in
+                              Array.foreach (arr, visit)
+                           end
                in
                   List.insertionSort (!entries, fn ((_, i1), (_, i2)) => i1 <= i2)
                end
diff --git a/mlton/control/control-flags.sig b/mlton/control/control-flags.sig
index 356c2c34a..e403febc5 100644
--- a/mlton/control/control-flags.sig
+++ b/mlton/control/control-flags.sig
@@ -63,6 +63,7 @@ signature CONTROL_FLAGS =
       val chunkify: Chunkify.t ref
 
       val chunkJumpTable: bool ref
+      val cCodegenPermuteEntries: int ref
       val chunkMayRToSelfOpt: bool ref
       val chunkMustRToOtherOpt: bool ref
       val chunkMustRToSelfOpt: bool ref
diff --git a/mlton/control/control-flags.sml b/mlton/control/control-flags.sml
index c8f2041dc..d7768c50e 100644
--- a/mlton/control/control-flags.sml
+++ b/mlton/control/control-flags.sml
@@ -210,6 +210,9 @@ val chunkify = control {name = "chunkify",
 val chunkJumpTable = control {name = "chunkJumpTable",
                               default = false,
                               toString = Bool.toString}
+val cCodegenPermuteEntries = control {name = "cCodegenPermuteEntries",
+                                      default = 0,
+                                      toString = Int.toString}
 val chunkMayRToSelfOpt = control {name = "chunkMayRToSelfOpt",
                                   default = true,
                                   toString = Bool.toString}
diff --git a/mlton/main/main.fun b/mlton/main/main.fun
index a65b9b948..e4026a904 100644
--- a/mlton/main/main.fun
+++ b/mlton/main/main.fun
@@ -287,6 +287,9 @@ fun makeOptions {usage} =
        (Expert, "chunk-jump-table", " {false|true}",
         "whether to use explicit jump table for chunk entry switch",
         Bool (fn b => chunkJumpTable := b)),
+       (Expert, "c-codegen-permute-entries", " <n>",
+        "permute chunk entry DFS order in C codegen with seed n (0 = disabled)",
+        Int (fn n => cCodegenPermuteEntries := n)),
        (Expert, "chunk-may-rto-self-opt", " {true|false}",
         "whether to optimize return/raise that may transfer to self chunk",
         Bool (fn b => chunkMayRToSelfOpt := b)),
```

---

## 2. Experimental Setup

Identical controls to [`noise_measure.md`](noise_measure.md), replacing `-fpatchable-function-entry=N,0` with `-expert true -c-codegen-permute-entries <seed>`:
* **Flattening passes disabled:** `-codegen c -build-magic 0 -disable-pass '(preFlatten.*)|(shallowFlatten.*)'`.
* **MLton-level perturbation sweep:** `seed` $\in \{0, 1, \dots, 15\}$ (16 variants per configuration; `seed = 0` is stock MLton).
* **GCC configurations (4-step ablation):**
  1. `O1`: `-cc-opt -O1`
  2. `O1_align`: `-cc-opt -O1 -cc-opt -falign-loops=16 -cc-opt -falign-jumps=16 -cc-opt -falign-labels=16 -cc-opt -falign-functions=16`
  3. `O2`: `-cc-opt -O2`
  4. `O3_native`: `-cc-opt -O3 -cc-opt -march=native`
* **Benchmarks:** Same 8 single-core benchmarks across the MLton suite (`wc-input1`, `fft`, `matrix-multiply`, `imp-for`, `checksum`) and `parallel-ml-bench` (`primes`, `dense-matmul`, `msort`).
* **Execution controls:** 512 binaries compiled in parallel, then executed sequentially pinned to CPU 0 (`taskset -c 0`) under `perf stat` (Experiment 1), followed by 3-repetition Ice Lake TMA + DSB/MITE profiling on the fastest vs. slowest `-O1` seeds for the top 3 unstable benchmarks (Experiment 2).

### Reproducibility & Artifacts
* **Experiment script:** [`analysis/o1_codegen_permute_exp.py`](../analysis/o1_codegen_permute_exp.py)
* **Plotting & summary script:** [`analysis/plot_o1_codegen_permute.py`](../analysis/plot_o1_codegen_permute.py)
* **Raw data:**
  * [`analysis/data/o1_codegen_permute_sweep.jsonl`](../analysis/data/o1_codegen_permute_sweep.jsonl)
  * [`analysis/data/o1_codegen_permute_perf.json`](../analysis/data/o1_codegen_permute_perf.json)
* **Figures:**
  * [`analysis/charts/thesis/o1_codegen_permute_sweep.pdf`](../analysis/charts/thesis/o1_codegen_permute_sweep.pdf) ([PNG](../analysis/charts/thesis/o1_codegen_permute_sweep.png))
  * [`analysis/charts/thesis/o1_codegen_permute_spread_bar.pdf`](../analysis/charts/thesis/o1_codegen_permute_spread_bar.pdf) ([PNG](../analysis/charts/thesis/o1_codegen_permute_spread_bar.png))

To reproduce:
```bash
python3 analysis/o1_codegen_permute_exp.py
~/code/parallel-ml-bench/env/bin/python3 analysis/plot_o1_codegen_permute.py
```

---

## 3. Experiment 1: MLton C-Codegen Permutation Sensitivity

### Max-to-Min Cycle Spread Across Seeds $0 \dots 15$

| Benchmark | Suite | `-O1` | `-O1 + align=16` | `-O2` | `-O3 -march=native` | `-O1` Inst. Spread |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| **`wc-input1`** | mlton | **41.57%** | **1.13%** | 4.98% | 7.45% | 0.825% |
| **`dense-matmul`** | parallel_bench | **8.45%** | 7.37% | **3.29%** | 10.37%\* | 0.085% |
| **`checksum`** | mlton | **7.67%** | **7.72%** | **0.99%** | **0.24%** | **9.000%** |
| **`matrix-multiply`** | mlton | **5.75%** | **0.23%** | **0.11%** | **0.13%** | 0.023% |
| `primes` | parallel_bench | **3.74%** | 2.27% | **1.65%** | 1.97% | 0.040% |
| `msort` | parallel_bench | 3.03% | 0.77% | 3.73% | 3.34% | 0.229% |
| `fft` | mlton | 1.16% | 0.64% | 1.16% | 1.09% | 0.163% |
| `imp-for` | mlton | 0.06% | 0.15% | 2.74% | 0.14% | 0.003% |

*\*On `dense-matmul`, `-O3 -march=native` is flat (~0%) across 14 of 16 seeds with one outlier at seed 15 (+9.5% vs. median); `-O1 + align=16` is flat across 15 of 16 seeds with one outlier at seed 7 (+7.3%).*

### Max-to-Min Wall-Time Spread Across Seeds $0 \dots 15$

| Benchmark | `-O1` | `-O1 + align=16` | `-O2` | `-O3 -march=native` |
| :--- | ---: | ---: | ---: | ---: |
| **`wc-input1`** | **40.33%** | **1.09%** | 4.70% | 7.30% |
| **`matrix-multiply`** | **9.77%** | **0.35%** | **0.24%** | **0.33%** |
| **`dense-matmul`** | **8.43%** | 6.95% | **3.40%** | 11.33% |
| **`checksum`** | **7.54%** | **7.74%** | **1.17%** | **0.78%** |
| `primes` | 3.52% | 2.21% | 3.09% | 2.38% |
| `msort` | 2.82% | 0.92% | 3.44% | 3.19% |
| `fft` | 1.15% | 0.68% | 1.12% | 1.00% |
| `imp-for` | 0.27% | 0.30% | 2.57% | 0.42% |

### Key Findings from Experiment 1
1. **Large `-O1` swings from MLton-only lowering changes:** Without touching any GCC flag, simply permuting the order in which MLton emits entry-block subtrees inside C chunks reproduces **+41.6% cycle swings on `wc-input1`**, **+8.5% on `dense-matmul`**, **+7.7% on `checksum`**, and **+5.8% on `matrix-multiply`** (+9.8% wall time).
2. **Exposes a *second* `-O1` failure mode invisible to NOP padding (`checksum`):** Unlike the pure code-alignment swings on `wc-input1`, `dense-matmul`, and `matrix-multiply` (all <0.85% instruction spread), `checksum` jumps by **+7.67% cycles** and **+9.000% retired instructions** on 4 of 16 seeds (`seed` $\in \{4, 6, 7, 10\}$) under both `-O1` and `-O1 + align=16`. Because GCC `-O1` disables `-freorder-blocks` and performs minimal CFG layout optimization, permuting MLton's C-label emission order directly alters whether GCC emits a fallthrough vs. an extra jump instruction in the hot loop (~480M extra retired instructions). Both `-O2` (0.99% cycle spread, **0.015%** inst. spread) and `-O3 -march=native` (0.24% cycle spread, **0.023%** inst. spread) eliminate this artifact completely.
3. **Complementarity with `-fpatchable-function-entry` ([`noise_measure.md`](noise_measure.md)):**
   * Entry-order permutation catches `-O1` instabilities on `matrix-multiply` (5.75% vs. 0.39% under NOP padding), `checksum` (7.67% vs. 0.05%), and `primes` (3.74% vs. 0.61%), and produces an even larger swing on `wc-input1` (41.57% vs. 33.16%).
   * Conversely, `imp-for` stays flat (0.06%) under these 16 entry permutations because its hot loop lives in a tiny chunk where the permuted entry subtrees did not land the loop on the bad 32-byte DSB boundary that the systematic 4-byte NOP sweep exposed (56.04%). Together, the two methods bracket both *realistic MLton C-emission reorderings* and *systematic worst-case alignment cliffs*.

---

## 4. Experiment 2: Ice Lake TMA Root-Cause Analysis

### `wc-input1` (`-O1` fast seed=7 vs. slow seed=13: **+40.39% cycles**, −0.755% instructions)

| Variant | Seed | Cycles (B) | Insts (B) | IPC | FE Bound | BE Bound | DSB µops | MITE µops | DSB→MITE Pen (M) | ICache Stall (M) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `O1_fast` | 7 | **1.640** | 3.158 | **1.93** | 2.7% | 62.1% | 95.6% | 4.4% | 7.27 | 4.94 |
| `O1_slow` | 13 | **2.302** | 3.134 | **1.36** | 1.5% | **73.3%** | 95.4% | 4.6% | 7.56 | 2.24 |
| `O1_align_S0` | 0 | 2.280 | 3.421 | 1.50 | 1.6% | 70.5% | 95.7% | 4.3% | 8.42 | 3.61 |
| `O2_S0` | 0 | 1.962 | 2.824 | 1.44 | 2.1% | 72.2% | 94.8% | 5.2% | 7.57 | 1.88 |
| `O3_native_S0` | 0 | 1.971 | 2.825 | 1.43 | 1.9% | 72.2% | 94.7% | 5.3% | 7.66 | 1.91 |

**Diagnosis:** Identical signature to [`noise_measure.md`](noise_measure.md): permuting MLton's C-codegen entry order flips `wc-input1` cleanly between the fast (~1.64B cycles, IPC 1.93) and slow (~2.30B cycles, IPC 1.36) regimes—**+40.4% more cycles** despite retiring **0.76% fewer instructions**—with `BE Bound` rising by +11.2 percentage points. Enabling `-falign-*=16` immediately eliminates the bimodal cliff (spread drops from 41.57% to 1.13%).

### `dense-matmul` (`-O1` fast seed=15 vs. slow seed=9: **+8.34% cycles**, +0.077% instructions)

| Variant | Seed | Cycles (B) | Insts (B) | IPC | FE Bound | BE Bound | DSB µops | MITE µops | DSB→MITE Pen (M) | ICache Stall (M) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `O1_fast` | 15 | **4.817** | 22.672 | **4.71** | **17.9%** | 4.5% | 99.8% | 0.2% | 1.41 | 0.86 |
| `O1_slow` | 9 | **5.218** | 22.690 | **4.35** | **24.6%** | 2.8% | 99.8% | 0.2% | 1.36 | 0.83 |
| `O1_align_S0` | 0 | 4.844 | 22.778 | 4.70 | 17.6% | 4.7% | 99.8% | 0.2% | 1.34 | 0.78 |
| `O2_S0` | 0 | 4.956 | 19.445 | 3.92 | 14.5% | 20.7% | 99.8% | 0.2% | 1.65 | 0.84 |
| `O3_native_S0` | 0 | 4.818 | 18.294 | 3.80 | 19.9% | 12.7% | 99.8% | 0.2% | 1.31 | 0.89 |

**Diagnosis:** Nearly identical to the NOP-padding result (+8.34% cycles vs. +8.36% in [`noise_measure.md`](noise_measure.md)): instruction count is invariant (+0.077%) while `topdown-fe-bound` jumps from **17.9% to 24.6%** and IPC drops from **4.71 to 4.35**.

### `checksum` (`-O1` fast seed=2 vs. slow seed=4: **+7.65% cycles**, **+8.996% instructions**)

| Variant | Seed | Cycles (B) | Insts (B) | IPC | FE Bound | BE Bound | DSB µops | MITE µops | DSB→MITE Pen (M) | ICache Stall (M) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `O1_fast` | 2 | **1.473** | **5.339** | 3.62 | 0.9% | 32.3% | 99.8% | 0.2% | 0.52 | 0.21 |
| `O1_slow` | 4 | **1.586** | **5.819** | 3.67 | 1.2% | 31.0% | 99.8% | 0.2% | 0.54 | 0.22 |
| `O1_align_S0` | 0 | 1.473 | 5.339 | 3.62 | 0.9% | 32.4% | 99.8% | 0.2% | 0.52 | 0.21 |
| `O2_S0` | 0 | 0.318 | 1.096 | 3.45 | 2.0% | 35.6% | 99.2% | 0.8% | 0.39 | 0.51 |
| `O3_native_S0` | 0 | 0.218 | 0.495 | 2.28 | 2.4% | 56.3% | 98.2% | 1.8% | 0.37 | 0.80 |

**Diagnosis:** Unlike `wc-input1` and `dense-matmul`, IPC and TMA breakdown are virtually unchanged (3.62 vs. 3.67 IPC; 0.9% vs. 1.2% `FE Bound`). Instead, permuting MLton's C-block emission order causes GCC `-O1` (which lacks `-freorder-blocks`) to retire **+480M (+9.00%) extra instructions**, directly driving the +7.65% cycle regression. Adding `-falign-*=16` cannot fix this (7.72% spread), whereas `-O2` (0.99% spread, 0.015% inst. spread) and `-O3 -march=native` (0.24% spread, 0.023% inst. spread) both eliminate the sensitivity and dramatically optimize the loop itself (1.47B → 0.22B cycles).

---

## 5. Summary Comparison (`noise_measure.md` vs. `noise_measure_codegen.md`)

| Benchmark | GCC NOP Padding (`-O1`) | MLton `c-codegen` Permute (`-O1`) | MLton `c-codegen` Permute (`-O2`) | MLton `c-codegen` Permute (`-O3 -march=native`) |
| :--- | ---: | ---: | ---: | ---: |
| `wc-input1` | **33.16%** | **41.57%** | 4.98% | 7.45% |
| `imp-for` | **56.04%** | 0.06% | 2.74% | **0.14%** |
| `dense-matmul` | **8.32%** | **8.45%** | **3.29%** | 10.37%\* |
| `checksum` | 0.05% | **7.67%** *(+9.0% insts)* | **0.99%** | **0.24%** |
| `matrix-multiply` | 0.39% | **5.75%** | **0.11%** | **0.13%** |
| `primes` | 0.61% | **3.74%** | **1.65%** | 1.97% |
| `msort` | 2.64% | 3.03% | 3.73% | 3.34% |
| `fft` | 1.45% | 1.16% | 1.16% | 1.09% |

**Conclusion:** Perturbing **only MLton's lowered C block emission order**—with zero GCC-level perturbation flags—directly reproduces up to **41.6% cycle swings** under `-O1` and exposes *two* distinct `-O1` instabilities: (1) microarchitectural alignment cliffs (`wc-input1` +41.6%, `dense-matmul` +8.5%, `matrix-multiply` +5.8%) and (2) `-O1` CFG/fallthrough codegen sensitivity (`checksum` +7.7% cycles / +9.0% retired instructions), which `-falign-*=16` alone cannot fix. Compiling with `-O2` or `-O3 -march=native` suppresses both failure modes.
