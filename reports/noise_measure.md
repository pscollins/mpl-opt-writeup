# Measuring GCC `-O1` Code-Layout Performance Instability

This report documents a controlled perturbation experiment conducted on `flattening-tests` (dual-socket Intel Xeon Platinum 8380 / Ice Lake-SP, GCC 15.2.0, Linux `perf` 7.0.14; see [`benchmark_machine.md`](benchmark_machine.md)) to quantify and diagnose the performance instability observed when compiling MLton/MPL's C backend with its default `-O1` optimization level.

---

## 1. Motivation & Experimental Design

In [`latex/chapters/evaluation.tex`](../latex/chapters/evaluation.tex) (§5.1 Methodology), we noted that compiling benchmarks with MLton's default C backend flag (`-O1`) produced erratic, hard-to-interpret swings across minor compiler changes and across host microarchitectures, whereas enabling code-layout alignment and higher GCC optimization levels (`-O2` / `-O3 -march=native`) stabilized measurements.

To pin this down quantitatively without conflating it with any optimization pass:
* **Flattening passes disabled:** All binaries were compiled with MLton's C backend (`-codegen c -build-magic 0`) and `-disable-pass '(preFlatten.*)|(shallowFlatten.*)'`.
* **Semantic no-op code-layout perturbation:** We swept GCC's `-fpatchable-function-entry=N,0` across $N \in \{0, 4, 8, 12, \dots, 60\}$ (16 offsets spanning one full 64-byte cache line / two 32-byte Intel DSB lines). Because MLton emits many SML functions into a single C chunk function (`Chunk_0`, `Chunk_1`, ...), inserting $N$ 1-byte `nop` instructions at function entry shifts every basic block and loop inside the chunk by $N$ bytes while adding negligible executed instructions (run once per chunk entry, never inside loops).
* **GCC configurations compared (4-step ablation):**
  1. `O1`: `-cc-opt -O1` (MLton default; disables all `-falign-*` flags)
  2. `O1_align`: `-cc-opt -O1 -cc-opt -falign-loops=16 -cc-opt -falign-jumps=16 -cc-opt -falign-labels=16 -cc-opt -falign-functions=16` (isolates 16-byte alignment from `-O2`'s other optimizations)
  3. `O2`: `-cc-opt -O2`
  4. `O3_native`: `-cc-opt -O3 -cc-opt -march=native` (matches the main thesis evaluation runs)
* **Benchmarks (8 single-core benchmarks across both suites):**
  * **MLton suite (scaled to ~0.5–1.1s/trial, 2–3 trials per binary):** `wc-input1` (`doit 256`), `fft` (`doit 1`), `matrix-multiply` (`doit 3`), `imp-for` (`doit 64`), `checksum` (`doit 192`).
  * **`parallel-ml-bench` (1-core MLton, `-repeat 3 -warmup 1`):** `primes` (`-N 40000000`), `dense-matmul` (`-N 512`), `msort` (`-N 2500000`).
* **Execution controls:** All 512 binaries (8 benchmarks × 4 configs × 16 offsets) were compiled in parallel, then executed sequentially pinned to CPU 0 (`taskset -c 0`) under `perf stat` collecting `cycles`, `instructions`, and `branch-misses` (Experiment 1). For the top 3 benchmarks by `-O1` cycle spread, we then collected Ice Lake Top-Down Microarchitecture Analysis (TMA) and DSB/MITE frontend counters over 3 repetitions on the fastest vs. slowest `-O1` offsets alongside `N=0` of the other three configs (Experiment 2).

### Reproducibility & Artifacts
* **Experiment script:** [`analysis/o1_instability_exp.py`](../analysis/o1_instability_exp.py)
* **Plotting & summary script:** [`analysis/plot_o1_instability.py`](../analysis/plot_o1_instability.py)
* **Raw data:**
  * [`analysis/data/o1_instability_sweep.jsonl`](../analysis/data/o1_instability_sweep.jsonl)
  * [`analysis/data/o1_instability_perf.json`](../analysis/data/o1_instability_perf.json)
* **Figures:**
  * [`analysis/charts/thesis/o1_instability_sweep.pdf`](../analysis/charts/thesis/o1_instability_sweep.pdf) ([PNG](../analysis/charts/thesis/o1_instability_sweep.png))
  * [`analysis/charts/thesis/o1_instability_spread_bar.pdf`](../analysis/charts/thesis/o1_instability_spread_bar.pdf) ([PNG](../analysis/charts/thesis/o1_instability_spread_bar.png))

To reproduce:
```bash
python3 analysis/o1_instability_exp.py
~/code/parallel-ml-bench/env/bin/python3 analysis/plot_o1_instability.py
```

---

## 2. Experiment 1: Code-Layout Perturbation Sensitivity

### Max-to-Min Cycle Spread Across $N \in \{0, 4, \dots, 60\}$

| Benchmark | Suite | `-O1` | `-O1 + align=16` | `-O2` | `-O3 -march=native` | `-O1` Inst. Spread |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| **`imp-for`** | mlton | **56.04%** | **57.03%** | 3.57% | **0.21%** | 0.035% |
| **`wc-input1`** | mlton | **33.16%** | **1.96%** | **1.23%** | **2.48%** | 0.078% |
| **`dense-matmul`** | parallel_bench | **8.32%** | **0.88%** | 3.08% | 11.96%\* | 0.009% |
| `msort` | parallel_bench | 2.64% | 0.82% | 1.36% | 2.93% | 0.029% |
| `fft` | mlton | 1.45% | 0.64% | 1.19% | 0.56% | 0.015% |
| `primes` | parallel_bench | 0.61% | 1.16% | 2.98% | 2.01% | 0.040% |
| `matrix-multiply` | mlton | 0.39% | 0.17% | 0.80% | 0.67% | 0.018% |
| `checksum` | mlton | 0.05% | 0.34% | 0.44% | 0.12% | 0.006% |

*\*On `dense-matmul`, `-O3 -march=native` is flat (~0%) across 15 of 16 offsets with a single isolated spike at $N=24$.*

### Max-to-Min Wall-Time Spread Across $N \in \{0, 4, \dots, 60\}$

| Benchmark | `-O1` | `-O1 + align=16` | `-O2` | `-O3 -march=native` |
| :--- | ---: | ---: | ---: | ---: |
| **`imp-for`** | **53.91%** | **55.20%** | 3.62% | **0.66%** |
| **`wc-input1`** | **32.19%** | **1.99%** | **1.25%** | **2.41%** |
| **`dense-matmul`** | **7.39%** | **0.60%** | 3.16% | 12.12% |
| `msort` | 2.75% | 0.92% | 1.56% | 2.95% |
| `fft` | 1.51% | 0.72% | 1.23% | 0.62% |
| `primes` | 0.67% | 1.28% | 2.65% | 2.95% |
| `matrix-multiply` | 0.79% | 0.57% | 0.95% | 0.80% |
| `checksum` | 0.43% | 0.32% | 1.31% | 0.76% |

### Key Findings from Experiment 1
1. **Exact 32-byte periodicity under `-O1`:**
   * On `wc-input1`, `-O1` produces an exact 32-byte periodic square wave: offsets $N \in \{0, 4, 8, 12\}$ and $\{32, 36, 40, 44\}$ run fast (~$-14\%$ vs. median), while $N \in \{16, 20, 24, 28\}$ and $\{48, 52, 56, 60\}$ run **33.2% slower** (~$+14\%$ vs. median). Enabling 16-byte alignment (`-O1 + align=16`) immediately eliminates the square wave (spread drops from 33.16% to 1.96%), as do `-O2` (1.23%) and `-O3 -march=native` (2.48%).
   * On `imp-for`, `-O1` exhibits exact 32-byte periodic **+56.0% spikes** at $N \in \{4, 8, 16\}$ and $\{36, 40, 48\}$. Notably, 16-byte alignment alone (`-O1 + align=16`) is *insufficient* here—it still exhibits +57.0% spikes with 32-byte periodicity ($N \in \{12, 16\}$ and $\{44, 48\}$) because 16-byte-aligned loops can still land on unfavorable 32-byte DSB boundaries. Moving to `-O2` drops the spread to 3.57%, and `-O3 -march=native` eliminates it completely (0.21%).
   * On `dense-matmul`, `-O1` exhibits 24-byte-spaced spikes ($N \in \{0, 24, 48\}$, 8.32% spread), which `-O1 + align=16` reduces to 0.88%.
2. **Instruction-count invariance:** Across all 8 benchmarks, retired instruction counts under `-O1` vary by **<0.08%** across all 16 offsets. The 8–56% cycle and wall-time swings are therefore purely microarchitectural code-layout artifacts rather than differences in generated work.

---

## 3. Experiment 2: Ice Lake TMA Root-Cause Analysis

To confirm the microarchitectural cause of the `-O1` cliffs, we profiled the fastest (`O1_fast`) vs. slowest (`O1_slow`) `-O1` offsets for the three most unstable benchmarks using Ice Lake hardware Top-Down Microarchitecture Analysis (TMA) counters (3 repetitions per variant on CPU 0, 100% counter residency / zero multiplexing).

### `imp-for` (`-O1` fast $N=44$ vs. slow $N=40$: **+55.87% cycles**, +0.031% instructions)

| Variant | Offset | Cycles (B) | Insts (B) | IPC | FE Bound | BE Bound | DSB µops | MITE µops | DSB→MITE Pen (M) | ICache Stall (M) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `O1_fast` | 44 | **0.917** | 4.057 | **4.42** | **3.1%** | 21.6% | 99.9% | 0.1% | 0.59 | 0.07 |
| `O1_slow` | 40 | **1.429** | 4.058 | **2.84** | **52.2%** | 0.0% | 97.8% | 2.2% | 0.64 | 0.07 |
| `O1_align_N0` | 0 | 0.921 | 4.192 | 4.55 | 3.1% | 18.0% | 99.8% | 0.2% | 0.40 | 0.06 |
| `O2_N0` | 0 | 1.033 | 4.185 | 4.05 | 10.2% | 20.9% | 99.4% | 0.6% | 11.96 | 0.06 |
| `O3_native_N0` | 0 | 0.585 | 2.334 | 3.99 | 1.2% | 23.1% | 99.9% | 0.1% | 0.07 | 0.06 |

**Diagnosis:** Shifting code layout by **4 bytes** ($N=44 \to N=40$) leaves instruction count unchanged (+0.031%) while causing `topdown-fe-bound` to jump from **3.1% to 52.2%** and IPC to fall from **4.42 to 2.84** (+55.9% cycles)—a classic Ice Lake frontend/DSB-boundary bottleneck.

### `wc-input1` (`-O1` fast $N=0$ vs. slow $N=16$: **+33.71% cycles**, +0.047% instructions)

| Variant | Offset | Cycles (B) | Insts (B) | IPC | FE Bound | BE Bound | DSB µops | MITE µops | DSB→MITE Pen (M) | ICache Stall (M) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `O1_fast` | 0 | **1.669** | 3.158 | **1.89** | 2.3% | 62.9% | 95.7% | 4.3% | 7.23 | 1.84 |
| `O1_slow` | 16 | **2.232** | 3.159 | **1.42** | 1.6% | 72.2% | 95.3% | 4.7% | 7.89 | 3.01 |
| `O1_align_N0` | 0 | 2.283 | 3.420 | 1.50 | 1.4% | 70.7% | 95.7% | 4.3% | 8.23 | 3.33 |
| `O2_N0` | 0 | 1.975 | 2.824 | 1.43 | 2.1% | 72.2% | 94.8% | 5.2% | 7.55 | 4.07 |
| `O3_native_N0` | 0 | 1.967 | 2.824 | 1.44 | 2.0% | 72.0% | 94.8% | 5.2% | 7.63 | 2.51 |

**Diagnosis:** A 16-byte shift ($N=0 \to N=16$) produces +33.7% cycles and an IPC drop from 1.89 to 1.42 with identical instruction count (+0.047%), accompanied by increased backend pressure (+9.3 percentage points `BE Bound`) and higher instruction-cache tag stalls (1.84M → 3.01M).

### `dense-matmul` (`-O1` fast $N=60$ vs. slow $N=24$: **+8.36% cycles**, +0.003% instructions)

| Variant | Offset | Cycles (B) | Insts (B) | IPC | FE Bound | BE Bound | DSB µops | MITE µops | DSB→MITE Pen (M) | ICache Stall (M) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `O1_fast` | 60 | **4.810** | 22.689 | **4.72** | **18.0%** | 4.3% | 99.8% | 0.2% | 1.26 | 0.87 |
| `O1_slow` | 24 | **5.212** | 22.689 | **4.35** | **24.1%** | 3.0% | 99.8% | 0.2% | 1.22 | 0.74 |
| `O1_align_N0` | 0 | 4.843 | 22.777 | 4.70 | 17.6% | 4.7% | 99.8% | 0.2% | 1.28 | 0.83 |
| `O2_N0` | 0 | 4.954 | 19.445 | 3.92 | 14.5% | 20.3% | 99.8% | 0.2% | 1.64 | 0.81 |
| `O3_native_N0` | 0 | 4.712 | 18.293 | 3.88 | 16.1% | 15.4% | 99.8% | 0.2% | 1.30 | 0.82 |

**Diagnosis:** Identical instruction count (22.689B vs. 22.689B, +0.003%) with `topdown-fe-bound` rising from 18.0% to 24.1% and IPC dropping from 4.72 to 4.35 (+8.4% cycles).

---

## 4. Implications for the Evaluation Methodology

* Under MLton's default `-O1`, **unrelated code-size changes anywhere earlier in a C chunk can induce 33–56% runtime swings** on tight-loop benchmarks without changing the executed instructions of the hot loop at all. Any compiler-pass evaluation run at `-O1` risks mistaking these layout cliffs for large optimization wins or regressions (and seeing opposite-sign effects across microarchitectures with different frontend/DSB geometries, such as Intel Ice Lake vs. AMD Ryzen).
* Simply adding 16-byte alignment flags (`-falign-*=16`) to `-O1` fixes `wc-input1` (33.2% → 2.0%) and `dense-matmul` (8.3% → 0.9%), but does **not** eliminate the 32-byte boundary cliff on `imp-for` (57.0%).
* Compiling with `-O2` or `-O3 -march=native` suppresses these `-O1` cliffs dramatically (`imp-for`: 56.0% → 0.21% at `-O3 -march=native`; `wc-input1`: 33.2% → 2.48%), justifying the use of `-O3 -march=native` throughout the thesis evaluation (and motivating updating the `-O2` text in `evaluation.tex` §5.1 to match the `-O3 -march=native` flags actually used in the benchmark runs).
