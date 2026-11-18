# Benchmark Machine Specifications

This document describes the hardware, topology, and software configuration of the benchmark host (`flattening-tests`) used for the MLton and MaPLe (MPL) performance evaluation.

---

## 1. Summary Table (For Paper / Evaluation Section)

| Component | Specification |
| :--- | :--- |
| **Processor** | 2 $\times$ Intel Xeon Platinum 8380 (3rd Gen Xeon Scalable, "Ice Lake-SP") |
| **Cores / Threads** | 80 physical cores (40 per socket) / 160 hardware threads (2-way SMT / Hyper-Threading enabled) |
| **Clock Frequency** | 2.30 GHz base, up to 3.40 GHz Turbo Boost (min 800 MHz; governor: `schedutil`, Turbo enabled) |
| **L1 Cache (per core)** | 48 KiB L1d (12-way, 64 B line) + 32 KiB L1i (8-way, 64 B line) — 3.8 MiB L1d / 2.5 MiB L1i total |
| **L2 Cache (per core)** | 1.25 MiB (1280 KiB) unified (20-way, 64 B line) — 100 MiB total across 80 cores |
| **L3 Cache (per socket)** | 60 MiB (61,440 KiB) unified (12-way, 64 B line) — 120 MiB total across 2 sockets |
| **Main Memory** | 251 GiB (~257 GB) RAM across 2 NUMA nodes (~128 GiB per socket), 0 B swap |
| **Operating System** | Ubuntu 26.04 LTS (Resolute Raccoon), Linux kernel `7.0.0-29-generic` (`x86_64`) |
| **C Backend Compiler** | GCC 15.2.0 (`Ubuntu 15.2.0-16ubuntu1`), flags `-O2 -march=native` |
| **Storage** | 447.1 GiB Micron 5300 PRO SATA SSD (`MTFDDAK480TDS`) |

---

## 2. Processor & Microarchitecture Details

- **Model**: Intel(R) Xeon(R) Platinum 8380 CPU @ 2.30GHz
- **Microarchitecture**: Ice Lake-SP (10nm, Family `6`, Model `106`, Stepping `6`)
- **Topology**:
  - **Sockets**: 2
  - **Physical Cores per Socket**: 40 (80 physical cores total)
  - **Threads per Core**: 2 (160 logical CPUs total, numbered `0–159`)
- **Address Sizes**: 46 bits physical, 57 bits virtual (5-level paging / `la57` supported)
- **Key ISA Extensions**:
  - Vector / SIMD: `sse4_1`, `sse4_2`, `avx`, `avx2`, `fma`, `f16c`
  - AVX-512: `avx512f`, `avx512dq`, `avx512ifma`, `avx512cd`, `avx512bw`, `avx512vl`, `avx512vbmi`, `avx512_vbmi2`, `avx512_vnni`, `avx512_bitalg`, `avx512_vpopcntdq`
  - Bit Manipulation & Crypto: `bmi1`, `bmi2`, `adx`, `abm`, `popcnt`, `aes`, `vaes`, `pclmulqdq`, `vpclmulqdq`, `sha_ni`, `gfni`

---

## 3. Cache Hierarchy & Memory / NUMA Topology

### Cache Hierarchy
| Level | Type | Size per Instance | Associativity | Line Size | Sharing Scope | Total Capacity (System) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **L1d** | Data | 48 KiB | 12-way | 64 B | Per physical core (2 SMT threads, e.g. CPUs `0,80`) | 3.8 MiB (80 instances) |
| **L1i** | Instruction | 32 KiB | 8-way | 64 B | Per physical core (2 SMT threads, e.g. CPUs `0,80`) | 2.5 MiB (80 instances) |
| **L2** | Unified | 1,280 KiB (1.25 MiB) | 20-way | 64 B | Per physical core (2 SMT threads, e.g. CPUs `0,80`) | 100 MiB (80 instances) |
| **L3 (LLC)** | Unified (non-inclusive) | 61,440 KiB (60 MiB) | 12-way | 64 B | Per socket (40 physical cores / 80 logical CPUs) | 120 MiB (2 instances) |

### NUMA Topology
The system has **2 NUMA nodes** (one per socket) with interleaved even/odd logical CPU numbering:
- **NUMA Node 0 (Socket 0)**:
  - **Logical CPUs**: Even IDs `0, 2, 4, ..., 158` (physical cores `0, 2, ..., 78` and their SMT siblings `80, 82, ..., 158`)
  - **Local Memory**: 128,260 MB (~125.3 GiB)
- **NUMA Node 1 (Socket 1)**:
  - **Logical CPUs**: Odd IDs `1, 3, 5, ..., 159` (physical cores `1, 3, ..., 79` and their SMT siblings `81, 83, ..., 159`)
  - **Local Memory**: 128,940 MB (~125.9 GiB)
- **NUMA Distance Matrix**:
  - Local access (`0 -> 0`, `1 -> 1`): `10`
  - Cross-socket UPI access (`0 -> 1`, `1 -> 0`): `20`
- **Virtual Memory Settings**:
  - Swap: Disabled (`0 B`)
  - Transparent Huge Pages (THP): `madvise` (`always [madvise] never`)

> **Note for Multi-Core Scaling (`parallel-ml-bench`)**: Because the machine has 80 physical cores across 2 sockets (and 160 logical CPUs with 2-way SMT), MPL scaling sweeps across `procs` $\in \{1, 2, 4, 8, 16, 32, 64, 80, 128, 160\}$ transition from physical core scaling (up to 80 cores across 2 NUMA nodes) into Simultaneous Multithreading (SMT) between `80` and `160` processors.

---

## 4. Software, Power Management & Security Mitigations

- **Operating System**: Ubuntu 26.04 LTS (`Resolute Raccoon`)
- **Linux Kernel**: `7.0.0-29-generic #29-Ubuntu SMP PREEMPT_DYNAMIC`
- **Performance Counter Tooling**: Linux `perf` version `7.0.14` (supports Ice Lake hardware Top-Down Microarchitecture Analysis / TMA metrics)
- **C Compiler (Backend)**: `gcc (Ubuntu 15.2.0-16ubuntu1) 15.2.0`
- **Power / Frequency Management**:
  - Driver: `intel_pstate` (`no_turbo = 0`, Turbo Boost enabled)
  - Scaling Governor: `schedutil` (800 MHz min – 3400 MHz max)
- **Active Hardware Vulnerability Mitigations**:
  - **Spectre v1**: Mitigation (`usercopy/swapgs` barriers and `__user` pointer sanitization)
  - **Spectre v2**: Mitigation (Enhanced / Automatic IBRS; IBPB conditional; PBRSB-eIBRS SW sequence; BHI SW loop)
  - **Indirect Target Selection**: Mitigation (Aligned branch/return thunks)
  - **Speculative Store Bypass**: Mitigation (disabled via `prctl`)
  - **MMIO Stale Data**: Mitigation (Clear CPU buffers; SMT vulnerable)
  - **Gather Data Sampling (GDS)**: Vulnerable (no microcode mitigation applied)
  - *Not affected*: Meltdown, L1TF, MDS, Retbleed, SRBDS, TSX Async Abort

---

## 5. Draft LaTeX Paragraph for `evaluation.tex` (§5.1 Methodology)

If you want to include a concise hardware description directly in [`latex/chapters/evaluation.tex`](../latex/chapters/evaluation.tex), you can drop in the following paragraph:

```latex
All experiments were conducted on a dual-socket server equipped with two
Intel Xeon Platinum 8380 (Ice Lake-SP) processors running at a 2.30\,GHz
base clock (up to 3.40\,GHz Turbo Boost), providing 40 physical cores (80
hardware threads via 2-way SMT) per socket for a total of 80 physical cores
and 160 hardware threads across two NUMA nodes. Each physical core has
48\,KiB of L1 data cache, 32\,KiB of L1 instruction cache, and a private
1.25\,MiB L2 unified cache, while each socket shares a 60\,MiB L3 last-level
cache (120\,MiB L3 total). The machine is equipped with 251\,GiB of main
memory (approximately 126\,GiB per NUMA node) with swap disabled, and runs
Ubuntu 26.04 LTS (Linux kernel 7.0.0) with GCC 15.2.0 as the C backend
compiler.
```
