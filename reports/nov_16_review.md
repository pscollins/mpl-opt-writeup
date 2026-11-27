# Comprehensive Thesis Review (`nov_16_review.md`)

**Date:** November 16, 2026  
**Scope:** [`latex/chapters/`](../latex/chapters/) (`introduction.tex`, `background.tex`, `preflatten.tex`, `shallowflatten.tex`, `evaluation.tex`, `related_work.tex`, `conclusion.tex`, `acknowledge.tex`, `appendix_notes.tex`), plus cross-checks against [`latex/solution.tex`](../latex/solution.tex), [`latex/abstract.tex`](../latex/abstract.tex), [`latex/defs.tex`](../latex/defs.tex), [`latex/references.bib`](../latex/references.bib), `latex/solution.log`, and [`analysis/config.json`](../analysis/config.json).

---

## Executive Summary & Top Priorities

Overall, the core technical narrative of the thesis is strong, well-motivated, and honest about negative and nuanced experimental findings (especially the `Chunkify` boundary sensitivity for `PreFlatten` and the parallel GC interactions for `ShallowFlatten`). Chapters 2–4 do a particularly nice job building visual intuition with side-by-side IR/C figures and TikZ memory-layout diagrams before introducing formal rewrite rules.

If you are triaging edits before submission, the highest-impact items to address first are:

1. **Critical Factual / Pass-Name Swaps & Stale Numbers (Part 1):**
   - ~~[`introduction.tex:32`](../latex/chapters/introduction.tex#L32) says `ShallowFlatten` where it means `PreFlatten`.~~
   - ~~[`shallowflatten.tex:1128`](../latex/chapters/shallowflatten.tex#L1128) says `PreFlatten` where it means `ShallowFlatten`, and [`shallowflatten.tex:1213`](../latex/chapters/shallowflatten.tex#L1213) has a truncated sentence (*"and no examples of, this..."*).~~
   - ~~[`related_work.tex:191-199`](../latex/chapters/related_work.tex#L191-L199) says `AoS` three times for NESL and Data Parallel Haskell, both of which use **SoA**; [`related_work.tex:143`](../latex/chapters/related_work.tex#L143) says `SoA` for Jane Street's unboxed product arrays, which are **AoS**.~~
   - ~~[`evaluation.tex:114`](../latex/chapters/evaluation.tex#L114) says `PreFlatten` only transforms *non-tail-recursive* functions (inverted: it only transforms `tail` calls)~~, alongside several stale numbers/claims left over from earlier benchmark runs (§5.1, §5.2.2, §5.3.1, §5.5, §5.7.2).
2. **`perf stat -dd` Multiplexing Artifact in `Topdown L1` Metrics (Part 1.4):**
   - Every `perf` table in Chapter 5 reports `80%–97.3%` `Bad Speculation` and `0.9%–9.6%` `Retiring`—even on 1-core `linearrec` where `Branch Miss Rate = 0.0%` and `IPC = 3.20` (physically impossible on a 5-wide Ice Lake pipeline, where `3.3%` retiring caps IPC at $\le 0.17$). Raw files in `analysis/perf_data/*.txt` show that `-dd` multiplexed ~18 counters at mismatched duty cycles (`14%–57%`), corrupting Ice Lake's `PERF_METRICS` Topdown L1 registers. This directly explains your open `\hl{TODO}` questions at [`evaluation.tex:1070`](../latex/chapters/evaluation.tex#L1070) and [`evaluation.tex:1092`](../latex/chapters/evaluation.tex#L1092).
3. **Formalism & Code-Snippet Bugs (Part 2):**
   - ~~Concrete bugs in the lowered C code for `fib` in Chapter 2 (which actually computes factorial, jumps to `bb2` instead of `bb3`, and has invalid C pointer assignments),~~ ~~a type-superscript collision (`x^{\tau}`) and untransformed specialization bodies in `PreFlatten`'s Fig. 3.8,~~ ~~and a homogeneous-tuple contradiction (`w_t`) against `ShallowFlatten`'s Fig. 4.6 (`((a * b) * c) array`).~~
4. **Structural & Build Defects in Chapter 5 & Bibliography (Part 3 & Part 5):**
   - Two `\section` commands in `ConApp Flattening` ([`evaluation.tex:707, 725`](../latex/chapters/evaluation.tex#L707)) that should be `\subsection`s; a duplicate `\label{tab:perf_comparison_aos_linearrec_1core}` collision ([`evaluation.tex:1163, 1588`](../latex/chapters/evaluation.tex#L1163)); stray numbered list text floating between tables ([`evaluation.tex:1098-1188`](../latex/chapters/evaluation.tex#L1098)); a figure overflowing the page by 2.2 inches ([`evaluation.tex:776`](../latex/chapters/evaluation.tex#L776)); `. en.` printed in ~25 bibliography entries; and missing author/venue/article metadata in 4 BibTeX entries.
5. **Missing Sections & Unincorporated Data (Part 4):**
   - Placeholder [`abstract.tex`](../latex/abstract.tex) and [`conclusion.tex`](../latex/chapters/conclusion.tex), ~~missing hardware specs (`compute_icelake_r750`),~~ 44 `\hl{...}` markers, and the new Nov 16 `-chunkify one` runs (`commit 3dd0c2c`, whose charts have not yet been generated in `analysis/charts/`) plus `soa_sync_gc` / `soa_fixed_iters`.

---

## Part 1: Factual, Technical, & Cross-Chapter Consistency Issues

### 1.1 Wrong Pass or Layout Named in Prose

1. ~~**`ShallowFlatten` written instead of `PreFlatten` ([`introduction.tex:30-35`](../latex/chapters/introduction.tex#L30-L35)):**~~
   - **Current:** *"After controlling for the effect of the `\texttt{Chunkify}` heuristic (by forcing all generated code into a single chunk), the `\texttt{ShallowFlatten}` optimizations are neutral-to-positive, generally demonstrating a geomean win on the order of 1-2% across all impacted benchmarks."*
   - **Issue:** That paragraph is about `PreFlatten` (and the next paragraph begins *"On the other hand, both `\texttt{ShallowFlatten}` transformations are overwhelmingly positive..."*). Replace `\texttt{ShallowFlatten}` with `\texttt{PreFlatten}` on line 32.

2. ~~**`PreFlatten` written instead of `ShallowFlatten` ([`shallowflatten.tex:1126-1128`](../latex/chapters/shallowflatten.tex#L1126-L1128)):**~~
   - **Current:** *"...wrap the element type in `\texttt{ref}`, as depicted in `\cref{fig:push_pop_ref}` -- in which case we are guaranteed that `\texttt{element = element'}`, which is preserved by `\texttt{PreFlatten}`."*
   - **Fix:** Replace `\texttt{PreFlatten}` with `\texttt{ShallowFlatten}` (since `(int * int) ref array` has $w_t(\texttt{(int * int) ref}) = 0$, `ShallowFlatten` leaves the outer array as an array of `ref` pointers).
   - ~~**Related note ([`shallowflatten.tex:911`](../latex/chapters/shallowflatten.tex#L911)):** Your `\hl{TODO}` says *"mention the homogeneous tuple restriction in limitaitons -- say that we could skip it for AoS but it's easier to keep it"*. Note that it is **SoA** ($\Phi_{\texttt{SoA}}$) where the uniform-element restriction can be skipped without changing `SSA` (as [`shallowflatten.tex:1219`](../latex/chapters/shallowflatten.tex#L1219) correctly explains), whereas AoS requires uniform types in `SSA`.~~

3. **`AoS` vs. `SoA` inverted in `related_work.tex` ([`related_work.tex:142-144`](../latex/chapters/related_work.tex#L142-L144), [`related_work.tex:191-199`](../latex/chapters/related_work.tex#L191-L199)):**
   - ~~**Lines 191–199:** Currently writes `AoS` three times (*"AoS container layouts have a long history..."*, *"in `\citet{nesl-book}` ... in which AoS is the canonical layout for container-of-tuple types"*, and *"The Data Parallel Haskell project of `\citet{data-parallel-haskell}`, likewise, commits exclusively to AoS layouts"*). Both NESL and Data Parallel Haskell canonically flatten arrays of tuples into **tuples of parallel arrays (SoA)** (`[(a, b)]` $\mapsto$ `([a], [b])`), **not** AoS. Change all three occurrences of `AoS` in that paragraph to `SoA`.~~
   - ~~**Lines 142–144:** States Jane Street's unboxed types in OCaml aim to materialize *"the same wins that we demonstrate here through the SoA transformation"*. Unboxed product arrays in OxCaml (`#(a, b) array`) inline fields contiguously per element (**AoS**, or say *"through `\texttt{ShallowFlatten}`'s AoS and SoA transformations"*).~~
   - **Lines 161–163 (`\citet{realtime-sml-paper}`):** Clarify that restricting to uniform element types is only needed by the **AoS** flavor of `ShallowFlatten` because `SSA` lacks heterogeneous inline struct-array types, whereas `DeepFlatten` operated on `SSA2`.
   - **Lines 78–83 (`\citet{local-paper}` and `\citet{adt4hpc-paper}`):** Currently describes both as *"concerned with manual control over the format of serialized data on disk"*. In fact, LoCal/Gibbon (`local-paper`) operates on dense packed/serialized tree buffers (inferring locations largely automatically), whereas Baudon's thesis (`adt4hpc-paper`) focuses on **in-memory** ADT bit-stealing (`Ribbit`) and **in-memory** AoS/SoA container layouts via layout annotations rather than disk serialization.

### 1.2 Tail Calls vs. Non-Tail Calls vs. Tail-Recursive Functions

1. ~~**Direct inversion in [`evaluation.tex:114`](../latex/chapters/evaluation.tex#L114):**~~
   - **Current:** `"\item \texttt{PreFlatten} only transforms non-tail-recursive functions"`
   - **Actual (`preflatten.tex:784`, Fig. 3.8a line 888, and `-pre-flatten-transfer-policy tail_only`):** `tuple`-`PreFlatten` **only transforms tail calls** ($L = \mathtt{tail}$), *excluding* non-tail calls.

2. **Conflation of "tail call" (callsite property) and "tail-recursive function" (function property) across Chapters 2, 3, and 5:**
   - ~~[`background.tex:172-175`](../latex/chapters/background.tex#L172-L175): *"Tail-recursive functions are distinguished in `\texttt{SSA}` by the lack of a `\texttt{return\_label}`; in the textual representation they use the placeholder label `\texttt{tail}`."* $\to$ In MLton's `SSA`, `tail` is a property of an individual **`call` transfer** (any tail call `call tail g(...)`, whether self-recursive, mutually recursive, or non-recursive), not only self-tail-recursive functions.~~
   - Same imprecise phrasing appears in ~~[`background.tex:355`](../latex/chapters/background.tex#L355) (*"non-tail-recursive function calls"* $\to$ *"non-tail function calls"*)~~, ~~[`preflatten.tex:784`](../latex/chapters/preflatten.tex#L784) (*"only flatten tail-recursive function calls"*, whereas line 794 and Fig. 3.8a line 888 correctly say *"Tail calls"* / $L = \mathtt{tail}$)~~, and [`evaluation.tex:640`](../latex/chapters/evaluation.tex#L640) (*"transforms all functions (both tail-recurisve and not)"* $\to$ *"transforms all calls (both tail and non-tail)"*).

### 1.3 Evaluation Prose vs. Plotted Data & Experimental Configurations

1. ~~**Metric definition mismatch ([`evaluation.tex:23-26`](../latex/chapters/evaluation.tex#L23-L26) vs. all figures, and [`introduction.tex:38-44`](../latex/chapters/introduction.tex#L38-L44)):**~~
   - `evaluation.tex:23-26` states that all results are reported as raw ratios `\texttt{test / base}` where `<1.0` is good and `>1.0` is bad (also missing a closing `''` after `test side` on line 25). However, **every chart and caption in Chapter 5** plots relative percentage change $(\text{test}/\text{base} - 1) \times 100\%$, where `<0%` is an improvement and `>0%` is a regression.
   - In [`introduction.tex:38-44`](../latex/chapters/introduction.tex#L38-L44) and [`abstract.tex:6`](../latex/abstract.tex#L6), speedup multipliers (*"by as much as 2x"*, *"as large as 10x"*) are mixed with percentage runtime reductions (*"geomean wins on the order of 10%"*, *"a 50% geomean win"*, *"wins of up to 50%"*). Note that a 50% runtime reduction *is* a $2\times$ speedup (and under `sync_gc`, `quickhull` achieves `-96.94%` runtime change $\approx 33\times$ speedup at 128–160c). Defining the percentage metric once in Ch. 1 and §5.1 will avoid ambiguity.

2. **Compiler flags stated in `evaluation.tex` vs. actual `config.json` runs:**
   - **C optimization level ([`evaluation.tex:34`](../latex/chapters/evaluation.tex#L34)):** Text says benchmarks were compiled under `\texttt{-O2}`, whereas the datasets in `analysis/config.json` pass `-cc-opt -O3 -cc-opt -march=native`—**except** `mlton_benchmarks_mlton_vs_mlton.con_chunkify_one` (`mlton_only_chunkify_one`), which used `-cc-opt -O2`. (Comparing an `-O3` default `con` series against an `-O2` `con_chunkify_one` series in Fig. 5.9 mixes C optimization levels, though both compare `-O2` vs. `-O2` / `-O3` vs. `-O3` internally.)
   - ~~**Tuple width cutoff $W$ ([`evaluation.tex:857-860, 1427-1428`](../latex/chapters/evaluation.tex#L857-L860)):** Text says $\le 3$ elements (`maxWidthSameType:3`), which matches `parallel-ml-bench`, whereas the MLton-suite runs (`test_aos_flatten_test_o3`, `test_soa_flatten_test_o3`) passed `maxWidthSameType:4`.~~ the only impacted benchmark has a tuple of size < 4 so there's no need to rerun
   - ~~**`ShallowFlatten` iteration limit:** All benchmarked AoS/SoA runs pass `-shallow-flatten-max-iters 1`, whereas [`shallowflatten.tex:956`](../latex/chapters/shallowflatten.tex#L956) formalizes the pass as iterating to a fixed point $\sembrack{P}_\Phi^*$. Worth adding a one-sentence note in §5.6 that $1$ outer iteration already reaches the fixed point on all benchmarks in both suites because none contain nested flattenable containers.~~ gemini is wrong, the iterations don't matter because we eliminate all flattenable types
   - **Pre-Oct-13 `tuple` runs on `parallel-ml-bench`:** `mlton_benchmarks_mlton_vs_mlton.tuple` was updated on Oct 13 (`tuple_test_o3_fixed_downgrade`), whereas `parallel_bench` default `tuple` runs (`260825-*`) predated that commit (though today's Nov 16 `mlton_tuple_vs_tuple_chunkify_one` uses the latest binary).

3. **Stale benchmark numbers and reversed claims in `evaluation.tex`:**
   - **§5.2.2 ([`evaluation.tex:174-182`](../latex/chapters/evaluation.tex#L174-L182)):** Calls `tuple` on MLton `parallel-ml-bench` *"broadly neutral"* apart from `reverb`, whereas Fig. 5.3 shows a **`+4.23%` geomean regression** across the 11 impacted benchmarks (`msort-strings` `+9.95%`, `tokens` `+9.62%`, `reverb` `+18.21%`). Incorporating your new Nov 16 `tuple_chunkify_one` run (`-0.77%` geomean—see Part 4.2 below!) resolves this cleanly by showing that the `+4.23%` slowdown disappears under `-chunkify one`.
   - **§5.3.1–5.4 ([`evaluation.tex:673-715`](../latex/chapters/evaluation.tex#L673-L715)):** Flagged by `\hl{TODO: THIS IS NOW A WIN}`: lines 675–677 and 698 still describe an *"overall geomean loss"* and *"the large loss to `wc-input1`"*, contradicting line 712 (*"the majr wins on `wc-input1` and `wc-scanStream` disappear"*). In Fig. 5.8, default `con` is a **`-0.98%` geomean win** (`wc-input1` `-22.29%`), which turns into a **`+0.33%` geomean** once `-chunkify one` removes the accidental chunk-layout win.
   - **§5.5 ([`evaluation.tex:746-747`](../latex/chapters/evaluation.tex#L746-L747)):** Claims *"a strong geomean win of $4.1\%$"* for `con` on MLton `parallel-ml-bench`; Fig. 5.10 shows **`-2.65%`** (`-2.7%` default, `-2.92%` with `-chunkify one`).
   - **§5.2.5 ([`evaluation.tex:491-495`](../latex/chapters/evaluation.tex#L491-L495)):** Immediately after 160-core `bfs` (Table 5.4), the text says *"While we still have instruction bloat, the increase to IPC / retiring pipeline slots was large enough to improve performance overall"*. That describes **1-core `bfs`** (Table 5.3: `+2.03%` instructions, `+8.06%` IPC), whereas in **160-core `bfs`** (Table 5.4) instructions *decreased* (`-2.14%`), IPC *decreased* (`-1.64%`), and Retiring *decreased* (`-0.3 pp`).
   - **§5.7.2 ([`evaluation.tex:1502-1508`](../latex/chapters/evaluation.tex#L1502-L1508)):** Says *"with AoS at a higher instruction count but a lower IPC, and SoA at a lower instruction count at a higher IPC"*. Comparing Table 5.10 (AoS: **150.59B** instructions, `1.92` IPC) and Table 5.11 (SoA: **166.83B** instructions, `2.23` IPC), **AoS has the lower instruction count and SoA has the higher instruction count**—which agrees with your explanation in the very next sentence that SoA executes extra tuple pack/unpack/select instructions!

4. **Warmup duration vs. test trial counts in `parallel-ml-bench` ([`evaluation.tex:28-30, 1241-1273`](../latex/chapters/evaluation.tex#L1241-L1273)):**
   - Lines 1241–1246 state that in the default configuration *"the benchmarks run for a fixed time, the faster AOS-transformed version runes for many more trials than the baseline."*
   - Checking the raw `.processed.jsonl` files and [`analysis/build_charts_lib.py:920-968`](../analysis/build_charts_lib.py#L920-L968), `-repeat 20 -warmup 5` actually runs **a fixed 5.0-second warmup** (`warmup_n = 118` on `mpl-aos` vs. `64` on `mpl-baseline` for 160-core `quickhull`) followed by **an identical 20 timed `test` trials** (`test_n = 20`) on both sides! Fig. 5.18 overlays warmup (`x`) and test (`o`) points starting at x-index `0`, making `mpl-aos` extend further along the x-axis due to its warmup runs.
   - Clarifying this actually *strengthens* your GC diagnosis in §5.6.6: running 5 seconds of warmup causes the faster AoS binary to execute nearly twice as many warmup iterations before trial 0, leaving the heap and hierarchical memory manager in a different GC phase entering the 20 timed trials; switching to `-repeat 15 -warmup 2` (`fixed_iters`, 2 warmup + 15 test iterations on both sides) equalizes the pre-test warmup work, while `sync_gc` eliminates mid-trial GC pause-placement variance altogether.

### 1.4 `perf stat -dd` Multiplexing Artifact in `Topdown L1` Metrics (Resolves §5.2.5 & §5.6.5 TODOs)

Across **all** `perf` tables in Chapter 5 (Tables 5.1–5.4 and 5.6–5.12), the `Topdown L1 Metrics` rows show `81.5%–97.3%` `Bad Speculation` on 1 core and `0.9%–9.6%` `Retiring`—leading [`evaluation.tex:427-428`](../latex/chapters/evaluation.tex#L427-L428) to conclude *"a shocking 97% of utilization lost to bad speculation"* and prompting your puzzled `\hl{TODO}`s at [`evaluation.tex:1070`](../latex/chapters/evaluation.tex#L1070) (*"WHY BAD SPEC? LOWER MISS RATE SHOUHD SHOW UP AS LESS BACKEND BOUND"*) and [`evaluation.tex:1092`](../latex/chapters/evaluation.tex#L1092).

- **Why the `Topdown L1` rows are corrupted:** Look at MPL 1-core `linearrec` ([`evaluation.tex:1170-1182`](../latex/chapters/evaluation.tex#L1170-L1182), raw file [`analysis/perf_data/linearrec_1_aos_base.txt`](../analysis/perf_data/linearrec_1_aos_base.txt)):
  - Measured `IPC = 3.20` instructions/cycle and `Branch Miss Rate = 0.0%` (`50M` misses / `144.5B` branches $= 0.035\%$).
  - Yet `Retiring = 3.3%` and `Bad Speculation = 94.6%`. On a 5-wide Ice Lake core (`5` pipeline slots/cycle), `3.3%` retiring pipeline slots physically limits retirement to at most $0.033 \times 5 = 0.165$ uops/cycle—**nearly $20\times$ lower than the measured `3.20` IPC**! (The same contradiction holds in every other 1-core table: e.g., `quickhull` has `IPC = 1.61` with `Retiring = 5.3%`; MLton `linearrec` SoA has `IPC = 2.23` with `Retiring = 7.9%`.)
  - In `analysis/perf_data/*.txt`, `perf stat -dd -D $DELAY` enabled ~18 hardware counters at once on an 8-PMC CPU, causing heavy PMU time-multiplexing with **mismatched active-time fractions** (`LLC-loads` `14%`, `branch-misses` `21%`, `cpu-cycles` `35%`, `instructions` `42%`, `tma_frontend_bound` `49%`, `TopdownL1` `50%`, `tma_retiring` `57%`). On Intel Ice Lake, `PERF_METRICS` Topdown L1 counters require atomic scheduling with Fixed Counter 3 (`slots`) via `perf stat --topdown` (without `-dd` splitting/multiplexing them); otherwise `tma_bad_speculation` absorbs the ungrouped scaling residual.
- **What remains completely valid:** All standard hardware counters in those tables (`Task Clock`, `Instructions`, `IPC`, `Branch Miss Rate`, `L1 D-Cache Miss Rate`, `LLC Load Miss Rate`, `dTLB Load Miss Rate`) as well as Table 5.5 (`bfs_1_tuple_base_badspec.txt`, which ran at `100.00%` duty cycle with zero multiplexing) are sound and already tell your microarchitectural story cleanly!
- **Recommended fix:** Either (a) drop the 4 `Topdown L1 Metrics` rows from the `perf` tables and base §5.2.5 / §5.6.5 / §5.7.2 on `Instructions`, `IPC`, and cache/TLB/branch miss rates (the quickest zero-rerun fix), or (b) re-collect `Topdown L1` alone using `perf stat --topdown -D $DELAY` (without `-dd`, verifying `100.00%` active time).

---

## Part 2: Formalism, IR Grammar, & Code-Snippet Bugs

### 2.1 Chapter 2 (`background.tex`): C Lowering & `SSA` Grammar

1. ~~**`fib` computes factorial rather than Fibonacci ([`background.tex:105-133, 297-315`](../latex/chapters/background.tex#L105-L133)):**~~
   - `fun fib(n) = if n = 0 then 1 else n * fib(n - 1)` computes $n!$ (`fact`), not Fibonacci (`fib`), and prints `fib 4` ($= 24$). Since Chapter 3 (`preflatten.tex:504`) introduces an actual Fibonacci function `fibPair`, renaming `fib` to `fact` in Figs. 2.2 & 2.4–2.8 (or changing the recurrence) avoids an immediate reader double-take.

2. ~~**Concrete C bugs in Figs. 2.5–2.9 ([`background.tex:380-540`](../latex/chapters/background.tex#L380-L540)):**~~
   - **Label case & enum mismatch:** `fig:chunk_func` (`line 339`) jumps to `L_bb0`, `L_bb1`, and blocks declare `L_bb0:`, `L_bb1:`, `L_bb2:`, `L_bb3:`. However, `fig:c_pseudo_small_bb0` (`lines 387, 389`) writes lowercase `goto l_bb1;` / `goto l_bb2;`, and `fig:c_pseudo_small_bb2` (`line 463`) writes `goto bb0;` (jumping to an enum constant instead of `L_bb0`).
   - **Wrong continuation label & stack offset in `bb2` ([`background.tex:455`](../latex/chapters/background.tex#L455)):** `call bb3 fib (callArg)` returns to `bb3`, but line 455 writes `*(Label*)(*stackTopPtr + sizeof(Label)) = bb2;` (which would loop infinitely back into `bb2`!). Moreover, `bb1` (`line 419`) and `bb3` (`line 503`) read the return label from `*stackTopPtr - sizeof(Label)` *before* subtracting `kFibStackSize`, which corresponds to caller offset `*stackTopPtr + kFibStackSize - sizeof(Label)` rather than `+ sizeof(Label)`.
   - **Invalid C expressions in `bb3` ([`background.tex:501, 503`](../latex/chapters/background.tex#L501-L503)):** Line 501 `(*stackTopPtr + 0) = funcResult;` assigns an `int` to an rvalue `char*` (missing `*(int*)` dereference, cf. line 416), and line 503 writes `*stackTop` instead of `*stackTopPtr`. Also standardize `uint32` (`bb0`, `bb1`) vs. `int` (`bb2`, `bb3`).
   - **Invalid C `typedef` in `fig:mlton_trampoline` ([`background.tex:527`](../latex/chapters/background.tex#L527)):** `typedef ChunkFn = ...;` mixes C `typedef` with C++11 `using` (`typedef Label (*ChunkFn)(char**, Label);`).
   - **Trailing semicolon in SSA snippet ([`background.tex:405`](../latex/chapters/background.tex#L405)):** `return 1;` has a C semicolon in the Python/SSA column.

3. **Other Chapter 2 code/grammar mismatches:**
   - ~~**Misplaced apostrophe & polymorphism in SSA ([`background.tex:191-193`](../latex/chapters/background.tex#L191-L193)):** Writes `\texttt{a' array}` and `\texttt{a' vector}` (in SML type variables are `'a`, not `a'`, and `SSA` is monomorphic—writing $\tau\;\texttt{array}$ and $\tau\;\texttt{vector}$ matches `fig:ssa_grammar` line 224 and the note in `appendix_notes.tex:142`).~~
   - ~~**0-based array comment ([`background.tex:1019-1020`](../latex/chapters/background.tex#L1019-L1020)):** `// Positive offset accesses element 16` above `15 * sizeof(int)` (index 15; right above on line 1016 you use 0-based `elements[0]`).~~
   - ~~**SML vs. SSA literal mismatch ([`background.tex:2419-2454, 2486-2514`](../latex/chapters/background.tex#L2419-L2454)):** Left-hand SML calls `doOp (2, 2, ...)`, while right-hand SSA calls `doOp(1, 2, env)`.~~
   - **`SSA` pseudocode syntax drift across Chapters 2–4 vs. `fig:ssa_grammar` ([`background.tex:200-225`](../latex/chapters/background.tex#L200-L225)):**
     - ~~`fig:ssa_grammar` defines function headers as `def f(...): tau =`, used in Figs. 2.2, 2.4, 2.15–2.19, and 3.9, whereas Figs. 2.24–2.25 (`background.tex:2431-2511`), Figs. 3.1–3.7 (`preflatten.tex:53-759`), and Fig. 4.1 (`shallowflatten.tex:76`) switch to Pythonic `def f(...) -> tau:`.~~
     - ~~`fig:true_flat_undirected_after` (`background.tex:1735-1737`) uses multi-value return `def g(...): int, int =` and `return a, b`, whereas `fig:ssa_grammar` only permits a single return type $\tau$ and single operand `return v`.~~
     - ~~`fig:hofo_no_polyvar_ssa` (`background.tex:2447`) writes bare `env: lambda1 = xEnv_add` without `con`, whereas `fig:ssa_grammar` line 217 requires `con C(...)`.~~

### 2.2 Chapter 3 (`preflatten.tex`): Formalism & IR Snippets

1. ~~**Duplicate parameter names when tuple fields share a type ([`preflatten.tex:897, 910, 927`](../latex/chapters/preflatten.tex#L910)):**~~
   - In Fig. 3.8b–c, $\pi(x{:}\tau_1 * \cdots * \tau_k, \texttt{Flatten}) = x^{\tau_1}{:}\tau_1, \dots, x^{\tau_k}{:}\tau_k$ names fresh parameters by superscripting their *type* $\tau_j$. Whenever a tuple has two fields of the same type (such as `int * int`), this produces colliding formal parameter names $x^{\mathtt{int}}{:}\mathtt{int}, x^{\mathtt{int}}{:}\mathtt{int}$.
   - **Fix:** Superscript by field index $1 \dots k$ (e.g., $x^{(1)}{:}\tau_1, \dots, x^{(k)}{:}\tau_k$ in both $\pi$ and $\beta$).

2. ~~**Untransformed basic blocks inside newly emitted specializations ([`preflatten.tex:906-908, 967-975`](../latex/chapters/preflatten.tex#L906-L908)):**~~
   - In Fig. 3.8b, $\flatsem{F_j}^{\texttt{Preserve}^n}$ transforms its blocks ($\flatsem{B_0} \cdots \flatsem{B_k}$), **but** $\flatsem{F_j}^{\vec{d}}$ ($\vec{d} \neq \texttt{Preserve}^n$, line 907) emits $\mathtt{bbBind}_{\vec{d}}\ B_0 \cdots B_k$ with *untransformed* $B_0 \cdots B_k$. And in Fig. 3.8e (line 971), when $\sigma' = \sigma$ or the iteration limit is reached, $\flatsem{P}$ returns $\mathcal{N}$ directly without applying $\sembrack{\mathcal{N}}_{\sigma'}$.
   - **Consequence:** If the iteration limit is $1$, or if a specialized function $f_{j,\vec{d}}$ calls another specialized function $h_{\vec{d}'}$ whose decision was already in $\sigma$ (so $\sigma' = \sigma$ if no new call labels appear), calls inside $f_{j,\vec{d}}$ are never rewritten! Furthermore, for $\Sigma(\mathcal{N})$ in line 966 to distinguish calls inside $\mathcal{N}$ from calls in $P$, duplicated call sites need fresh `callN` labels.
   - **Fix:** Change line 907 to $\mathtt{bbBind}_{\vec{d}}\ \flatsem{B_0} \cdots \flatsem{B_k}$ (and note in the caption of Fig. 3.8b/e that emitting $\flatsem{F_j}^{\vec{d}}$ assigns fresh block/variable/call-site names so $\Sigma(\mathcal{N})$ analyzes the newly created call sites).

3. ~~**Nullary `datatype` constructors in $\texttt{Flatten}_C$ ([`preflatten.tex:911-912, 929, 948-949`](../latex/chapters/preflatten.tex#L911-L912)):**~~
   - Fig. 3.8 assumes every constructor has the form $C \mathbin{\mathtt{of}} \tau$ carrying a payload argument. However, closure conversion routinely emits nullary constructors for capture-free functions (e.g., `xEnv_add | xEnv_sub` in `background.tex` Fig. 2.24!). Either add the nullary case ($\pi(x{:}T, \texttt{Flatten}_C) = \epsilon$, $\beta = (x{:}T \syneq \mathtt{con}\ C())$, $\alpha = \epsilon$) or note that nullary constructors are treated as carrying `unit`.

4. ~~**Missing payload binding in `ConApp` `case` arms ([`preflatten.tex:264, 287, 384`](../latex/chapters/preflatten.tex#L384)):**~~
   - In Fig. 3.3 (`lines 264, 287`) and Fig. 3.5a (`line 384`), `Env1` is declared as `Env1 of a * b` and `bb1` expects `block bb1(t: a * b):`, yet the `case` arm is written `Env1 => goto bb1` instead of `Env1(t) => goto bb1(t)` (passing 0 arguments to a 1-parameter block).

5. ~~**Abrupt transition opening §3.3 ([`preflatten.tex:987-990`](../latex/chapters/preflatten.tex#L987-L990)):**~~
   - `\section{Comparison with \texttt{Flatten}}` begins *"By contrast, the analysis of `\texttt{PreFlatten}` simply reasons about callsites..."* even though the immediately preceding section (§3.2) was already about `PreFlatten`! Add a one-sentence recap of `Flatten`'s global constraint-graph propagation at the start of §3.3 so *"By contrast"* has its referent.

### 2.3 Chapter 4 (`shallowflatten.tex`): Formalism & Motivating Example

1. ~~**Contradiction between homogeneous `w_t(t)` and Fig. 4.6 ([`shallowflatten.tex:621, 648-713, 917-921, 1219`](../latex/chapters/shallowflatten.tex#L648-L713)):**~~
   - Lines 917–921 define $w_t(t) = n$ **only** when $t = \tau * \cdots * \tau$ (all $n$ components share the *exact same* type $\tau$), and both $\Phi_{\texttt{SoA}}$ and $\Phi_{\texttt{AoS}}$ in Fig. 4.8 (`lines 1027-1030`) require $(\tau * \cdots * \tau)\;\kappa$.
   - However, Fig. 4.6 (`fig:shallow_needs_repeated`) illustrates multi-iteration convergence on `arr: ((a * b) * c) array`. Under your definition of $w_t$, **even if $a = b = c = \mathtt{int}$**, the outer element type is $(\mathtt{int} * \mathtt{int}) * \mathtt{int}$, whose two fields have *different* types ($\mathtt{int} * \mathtt{int} \neq \mathtt{int}$), so $w_t((\mathtt{int} * \mathtt{int}) * \mathtt{int}) = 0$ and $\sembrack{\tau}_\Phi$ never transforms it at all!
   - Furthermore, [`shallowflatten.tex:1219-1220`](../latex/chapters/shallowflatten.tex#L1219-L1220) states *"An additional limitation that is specific to the AoS flavor, as described above, is the restriction to tuples of uniform types"*, contradicting lines 917–921 and 1027 where $\Phi_{\texttt{SoA}}$ is also restricted to uniform types.
   - **Fix:**
     - If your implementation (`maxWidthSameType`) restricts *both* AoS and SoA to uniform tuples for convenience, change Fig. 4.6's example to balanced `((int * int) * (int * int)) array` (where $w_t((\mathtt{int} * \mathtt{int}) * (\mathtt{int} * \mathtt{int})) = 2$), and reword line 1219 to note that while the current prototype applies the uniform-type policy to both flavors, the restriction is *inherent* only to AoS in `SSA` (and incidental for SoA).
     - Conversely, if $\Phi_{\texttt{SoA}}$ in your compiler already supports heterogeneous tuples $\tau_1 * \cdots * \tau_n$, generalize $w_t$ and $\Phi_{\texttt{SoA}}$ in §4.2 to $\tau_1 * \cdots * \tau_n$ and apply the uniform-type guard only to $\Phi_{\texttt{AoS}}$.

2. ~~**Subscript case typo ([`shallowflatten.tex:956`](../latex/chapters/shallowflatten.tex#L956)):**~~
   - Writes $\sembrack{P}_\phi^*$ (lowercase $\phi$) instead of $\sembrack{P}_\Phi^*$ (uppercase $\Phi$, matching line 907 and Fig. 4.7 line 966).

3. ~~**Incomplete sentence in §4.3 ([`shallowflatten.tex:1213-1215`](../latex/chapters/shallowflatten.tex#L1213-L1215)):**~~
   - **Current:** *"Given that the value-to-ref rewrite is trivial and no examples of, this seems to impose minimal programmer burden and win substanial flexibility for the compiler."*
   - **Fix:** Supply the missing clause after *"no examples of"* (e.g., *"...and no examples of tuple pointer-equality or tuple-array CAS operations appear in our benchmark suites, this seems..."*) and fix `substanial` $\to$ `substantial` (lines 1214 and 1222).

### 2.4 Chapter 5 (`evaluation.tex`): Pseudocode Bugs

1. **`parfor` / `parfor_flat` snippet ([`evaluation.tex:256-283`](../latex/chapters/evaluation.tex#L256-L283)):**
   - Line 268: `par (left, right)` is indented *inside* `def right():` instead of inside `def parfor(...)`.
   - Line 271: `def parfor_flat(f: 'a -> b, ...): ...` is missing the tick on `'b` and has a stray `...` after `:`.
   - Lines 277–278: Defines `lohi = (lo, mid)` (no underscore) and calls `parfor (f, lo_hi, grain)` (with underscore).
2. **`quickhull` snippet ([`evaluation.tex:961-981`](../latex/chapters/evaluation.tex#L961-L981)):**
   - Lines 970–972 compute `lefts` and `right`, ignore both variables, and recompute `(filter(is_left, indices), filter(is_right, indices))`; also `partition` takes `int list`, is annotated `-> (int array) * (int array)`, returns filtered lists, and is called with `indices: int array` on line 977.
3. **`linearrec` snippet & prose ([`evaluation.tex:989-1003, 1038-1040`](../latex/chapters/evaluation.tex#L989-L1003)):**
   - Line 989 names the parameter `points`, but line 1001 calls `prefix_scan(pairs, combine)` (`pairs` is undefined).
   - Lines 1039–1040 call the primitive `\texttt{parallel\_scan}` (instead of `\texttt{prefix\_scan}`) and say it operates over *"a flat `\texttt{float * float}` array"* (should be *"a flat `\texttt{float}` array"*).

---

## Part 3: Structural, Cross-Reference, & LaTeX Layout Defects

1. **Broken section hierarchy in `ConApp Flattening` ([`evaluation.tex:707, 725, 770`](../latex/chapters/evaluation.tex#L707-L770)):**
   - Under `\section{\texttt{ConApp} Flattening}` (§5.3), two subsections were accidentally written as top-level `\section`s:
     - Line 707: `\section{\texttt{wc-input1}: controlling for \texttt{Chunkify}}` (becomes **§5.4** instead of **§5.3.3**!)
     - Line 725: `\section{\texttt{parallel-ml-bench}: MLton vs MLton}` (becomes **§5.5** instead of **§5.3.4**, which also nests line 770 `\subsection{\texttt{parallel-ml-bench}: MPL vs MPL}` as **§5.5.1** *inside* `MLton vs MLton`!)
   - Changing lines 707 and 725 to `\subsection` aligns `ConApp Flattening` with `Tuple Flattening`, `AoS Flattening`, and `SoA Flattening`.

2. **Multiply-defined label `\label{tab:perf_comparison_aos_linearrec_1core}` ([`evaluation.tex:1163, 1588`](../latex/chapters/evaluation.tex#L1163)):**
   - Defined on both the **MPL** 1-core `linearrec` AoS table (line 1163) and the **MLton** 1-core `linearrec` AoS table (line 1588). As a result, `\cref{tab:perf_comparison_aos_linearrec_1core}` in the MPL discussion ([`evaluation.tex:1080`](../latex/chapters/evaluation.tex#L1080)) points to the MLton table! Rename line 1588 (e.g., `tab:perf_comparison_mlton_aos_linearrec_1core`) and update line 1502, and include the compiler (`MPL` vs. `MLton`) and pass name in all `perf` table captions (which currently repeat `"on 1 core (..., 1 core)"` without naming the compiler).

3. **Orphan numbered list lines between floating tables ([`evaluation.tex:1098, 1128, 1158, 1188`](../latex/chapters/evaluation.tex#L1098)):**
   - Plain text lines `1. Quickhull on 1 Core`, `2. Quickhull on 160 Cores`, `3. Linearrec on 1 Core`, `4. Linearrec on 160 Cores` appear outside `\begin{table}[htbp]...\end{table}`, so when LaTeX floats the tables, those four lines concatenate into a stray paragraph in the body text. Delete them.

4. **Figure overflowing page by 159pt / 2.2 inches ([`evaluation.tex:772-797`](../latex/chapters/evaluation.tex#L772-L797)):**
   - `LaTeX Warning: Float too large for page by 159.05794pt on input line 797.` Because `ConApp` impacts all 34 benchmarks in `parallel-ml-bench`, `con_parallel_bench_run_mpl_vs_mpl_trellis.pdf` is much taller than the 11- or 21-benchmark trellis plots. Add `height=0.82\textheight,keepaspectratio` (as you did on line 848) or split the trellis into its own full-page figure.

5. **Overfull `\hbox` and `hyperref` warnings from `solution.log`:**
   - ~~**TikZ diagram overflow (`66.7pt` too wide):** [`background.tex:1207-1279`](../latex/chapters/background.tex#L1207-L1279) (`fig:layout_nested_array`) overflows its `0.50\textwidth` minipage by nearly an inch; wrap the `tikzpicture` in `\resizebox{\linewidth}{!}{...}` or tighten cell `minimum width`s.~~
   - **Display math overflow (`21.4pt` too wide):** [`preflatten.tex:906-908`](../latex/chapters/preflatten.tex#L906-L908) (`fig:preflatten_emit_new`) exceeds `\textwidth`; move $(\vec{d} \neq \texttt{Preserve}^n)$ onto a second aligned line or reduce `\qquad` to `\quad`.
   - **Dataflow TikZ Row 3 (`8.5pt` too wide):** [`preflatten.tex:1443-1543`](../latex/chapters/preflatten.tex#L1443-L1543).
   - **Unstyled `minted` blocks in `evaluation.tex`:** Unlike Chapters 2–4 (which style all `minted` blocks inside framed `figure`s with `fontsize=\scriptsize` or `\footnotesize`), `evaluation.tex` has 9 inline `minted` blocks at default `12pt` font (`lines 241, 256, 323, 355, 683, 959, 986, 1006, 1018`), causing horizontal overflows at lines 271 (`13.9pt`) and 990 (`1.4pt`) and clashing visually with earlier chapters (see also `appendix_notes.tex:98`).
   - **List of Figures overflows (8 warnings up to `70.3pt` too wide):** Multi-sentence captions with long `\texttt{...}` identifiers don't hyphenate in `\listoffigures`. Pass concise short titles `\caption[Short title for LOF]{Full detailed caption.}` on the longest captions (e.g., Figs. 2.11, 2.20, 3.2, 3.4, 3.6, 3.7, ~~4.5, 4.9~~) or add `\usepackage{microtype}`.
   - ~~**PDF bookmark Unicode warnings (6 warnings):** `\subsection{SML $\Rightarrow$ \texttt{SSA}}` and `\subsection{\texttt{SSA} $\Rightarrow$ C}` ([`background.tex:82, 268`](../latex/chapters/background.tex#L82)) emit `Token not allowed in a PDF string`; replace `$\Rightarrow$` with `\texorpdfstring{$\Rightarrow$}{->}`.~~

---

## Part 4: Missing Information, Unincorporated Data, & Open `\hl{TODO}`s

### 4.1 Missing Sections & Architectural Context

1. **Abstract ([`latex/abstract.tex`](../latex/abstract.tex)) & Conclusion ([`latex/chapters/conclusion.tex`](../latex/chapters/conclusion.tex)):**
   - ~~`abstract.tex` is currently `\hl{TODO: FILL IN}` plus one sentence, and `conclusion.tex` is `\hl{TODO}`.~~
   - A crisp 1–2 page **Conclusion** can synthesize: (a) the central design thesis—that simple, local pack/unpack-inserting IR passes (`PreFlatten` and `ShallowFlatten`) composed with existing SSA cleanup passes (`Simplify`, `KnownCase`, `Flatten`) avoid the fragility of global all-or-nothing lattice analyses (`Flatten`, `DeepFlatten`); (b) why `ShallowFlatten` delivers large single-core wins (~10–12% geomean, up to $>2\times$) while exposing parallel GC pause sensitivity in MPL (up to ~49% geomean reduction under `sync_gc`); (c) why `PreFlatten` is largely neutralized or destabilized by `Chunkify` boundary perturbations; and (d) concrete **Future Work** (chunk-aware cost modeling or evaluating MLton's native x86_64/LLVM backends where `Chunkify` trampolines do not apply; MPL parallel GC heuristic co-design; heterogeneous AoS in `SSA2`; SIMD vectorization over `ShallowFlatten` buffers; and static `MLton.eq`/CAS fallback or value-type semantics).

2. **Introduction Roadmap & Explicit Contributions ([`latex/chapters/introduction.tex`](../latex/chapters/introduction.tex)):**
   - ~~At 45 lines, Chapter 1 jumps straight from a two-paragraph motivation to benchmark numbers without an explicit **contributions list** (noted in `appendix_notes.tex:133`) or a **chapter-by-chapter outline** linking `\cref{ch:background}`–`\cref{ch:conclusion}`.~~

3. ~~**Hardware & Benchmark Suite Description ([`evaluation.tex:101-103`](../latex/chapters/evaluation.tex#L101-L103), `\hl{TODO: DESCRIBE HW}`):**~~
   - From [`analysis/reserve_machine.sh`](../analysis/reserve_machine.sh) and `analysis/perf_data/*.txt`, fill in the Chameleon Cloud hardware details: `compute_icelake_r750` (Dell PowerEdge R750, dual-socket Intel Xeon Platinum 8380 Ice Lake at ~3.0 GHz, $2 \times 40 = 80$ physical cores / $160$ hardware threads with SMT, Ubuntu Linux, GCC 15.2.0).
   - **Important insight to mention:** Calling out that the machine has **80 physical cores and 160 SMT threads across 2 sockets** immediately explains why `procs` spans $\{1, 2, 4, 8, 16, 32, 64, 80, 128, 160\}$—up to `80` scales across physical cores, while `128` and `160` cross into hyperthreading!
   - Also state the total benchmark counts in §5.1 (**45** in the MLton suite, **34** in `parallel-ml-bench`) and how many benchmarks each pass modifies (e.g., AoS/SoA modify only `flat-array` ($1/45$) in MLton's suite vs. $11/34$ in `parallel-ml-bench`).

4. **Small Missing Definitions / Explanations in Chapters 2–5:**
   - ~~**Define `ConApp` on first use:** `fig:ssa_grammar` (`background.tex:217`) writes constructor application as `con C(...)`, and `ConApp` appears abruptly at [`background.tex:1618`](../latex/chapters/background.tex#L1618) and [`preflatten.tex:231`](../latex/chapters/preflatten.tex#L231) without explanation (noted in commented-out `preflatten.tex:694`). Add one sentence in §2.1.2 noting that MLton internally calls constructor application (`con C(...)`) `ConApp`.~~
   - ~~**Concrete example of why `DeepFlatten` fails ([`background.tex:2258-2263`](../latex/chapters/background.tex#L2258-L2263)):** Briefly note *why* `DeepFlatten`'s lattice marks arrays unflattened in benchmarks like `quickhull` and `linearrec`—namely, whenever an element read `t = Array_sub(arr, i)` is passed to a helper function, captured in a closure, or bound across blocks rather than projected immediately in-place in `SSA2` (cf. `appendix_notes.tex:129`).~~
   - **Explain `"10 recursive steps"` ([`evaluation.tex:116, 642`](../latex/chapters/evaluation.tex#L116)):** Replace both `\hl{TODO: EXPLAIN? REMOVE?}` notes with a cross-reference to the iteration limit in [`preflatten.tex:848`](../latex/chapters/preflatten.tex#L848) and `\cref{fig:preflatten_recurse}` (`-pre-flatten-recursive-steps 10`, capping mutual/self-recursive specialization depth at 10 rounds).
   - **Submission cleanup ([`solution.tex:161, 260-262`](../latex/solution.tex#L260-L262)):**
     - Comment out `\appendix \chapter{Working Notes} \input{chapters/appendix_notes}` before final build (currently pages 97–99 of `solution.pdf` contain personal meeting notes).
     - ~~Check NYU Courant MS title-page wording on [`solution.tex:161`](../latex/solution.tex#L161): *"A **dissertation** submitted in partial fulfillment... Master of Science"* $\to$ NYU MS templates typically use *"A **thesis** submitted..."* (*dissertation* is reserved for PhD).~~

### 4.2 Unincorporated Experimental Datasets in `analysis/`

1. **Today's Nov 16 `-chunkify one` runs (`commit 3dd0c2c`)—not yet built into `analysis/charts/` or discussed in `evaluation.tex`:**
   - **Reminder:** Run `build_charts.py` / `make` in `analysis/` first—the four new PDFs (`mlton_tuple_chunkify_one_parallel_bench.pdf`, `mlton_tuple_chunkify_one_mlton_bench.pdf`, `soa_chunkify_one_geomean.pdf`, `soa_chunkify_one_parallel_bench_run_mpl_vs_mpl_trellis.pdf`) do not exist in `analysis/charts/` yet!
   - **What the new runs show (and where to add them):**
     - **`mlton_tuple_vs_tuple_chunkify_one` (§5.2.2, MLton `parallel-ml-bench`):** Eliminates the `+4.23%` default regression completely, yielding a **`-0.77%` geomean win** across the 11 impacted benchmarks (`range-tree` `-3.84%`, `msort-strings` `-3.37%`, `reverb` `-3.29%`; worst is `msort` `+2.76%`). This makes §5.2.2's narrative much stronger and consistent with §5.2.6!
     - **`tuple_chunkify_one` (§5.2.1, MLton suite):** 7/45 impacted, **`+0.99%` geomean** (`-0.02%` `simple` to `+2.84%` `model-elimination`), confirming `tuple` on the MLton suite remains near-neutral (`<3%` everywhere) with or without `Chunkify`.
     - **`mpl_soa_vs_soa_chunkify_one` (§5.7.3, MPL `parallel-ml-bench`):** `-12.83%` geomean at 1c to `+0.08%` at 160c (`quickhull` `-41.97%`, `linearrec` `+55.52%` GC spike at 160c), matching AoS's insensitivity to `-chunkify one`.

2. **Existing `soa_sync_gc` and `soa_fixed_iters` charts (`analysis/charts/`) missing from §5.7.3 ([`evaluation.tex:1642-1683`](../latex/chapters/evaluation.tex#L1642-L1683)):**
   - Currently §5.7.3 is only one 4-line paragraph, even though `soa_sync_gc` (`-48.08%` geomean at 160c, `-48.39%` at 128c, `quickhull` `-96.67%`) and `soa_fixed_iters` (`-14.64%` at 1c to `-3.78%` at 160c) are already measured and plotted in `analysis/charts/`. Including them (or adding `soa_sync_gc_geomean` / `soa_fixed_iters_geomean` in `config.json`) makes §5.7 symmetric with §5.6 and backs up the Introduction's claim that *both* `ShallowFlatten` flavors achieve ~50% geomean wins under synchronous GC.
   - Similarly, `-chunkify func` datasets exist in `config.json` for `tuple`, `con`, and `aos`; even a 1–2 sentence footnote or remark in §5.2.6 noting that `-chunkify func` behaves similarly would put that data to work.

### 4.3 Complete Inventory of `\hl{...}` Markers (44 Total)

- **Already Resolved / Safe to Unwrap or Delete Immediately (7):**
  - ~~[`background.tex:154`](../latex/chapters/background.tex#L154) `\hl{TODO: grammar needs to mention globals}` — `fig:ssa_grammar` line 208 (`P ::= D* s* F*`) and line 158 already include globals!~~
  - ~~[`background.tex:277`](../latex/chapters/background.tex#L277) & [`287`](../latex/chapters/background.tex#L287) `\hl{TODO: where to note that the match isn't exact?}` / `\hl{its semantics}` — lines 285–287 already state this cleanly; just unwrap `\hl{its semantics}`.~~
  - ~~[`background.tex:2326`](../latex/chapters/background.tex#L2326) `\hl{translation}` — unwrap `\hl{translation}`.~~
  - [`related_work.tex:214`](../latex/chapters/related_work.tex#L214) `\hl{TODO: OpenJDK Project Valhalla in shallowflatten.tex}` — already added in `shallowflatten.tex:1210`!
  - ~~[`shallowflatten.tex:13, 23`](../latex/chapters/shallowflatten.tex#L13) `\hl{disasterous}` + `\hl{ALREADY SAID ``DISASTEROUS''}` — replace `\hl{disasterous}` with e.g. `pathological` or `poor` and delete line 23.~~
- **Quick Inline Polish / Cross-Refs (16):**
  - ~~`background.tex`: [`1288`](../latex/chapters/background.tex#L1288) (allocation side—optional 1 sentence on bump-pointer frontier), [`1597`](../latex/chapters/background.tex#L1597) (stale PreFlatten note—already moved to Ch. 3, just smooth first sentence *"Specifically..."*), [`2107`](../latex/chapters/background.tex#L2107) (`\hl{REPHRASE}` *"perfect efficiency"* $\to$ *"100% cache-line utilization"*), [`2387`](../latex/chapters/background.tex#L2387) (`datatype` values vs. objects), [`2588`](../latex/chapters/background.tex#L2588), [`2618`](../latex/chapters/background.tex#L2618).~~
  - `preflatten.tex`: [`24`](../latex/chapters/preflatten.tex#L24) (decide whether to keep name `PreFlatten` or rename), [`304`](../latex/chapters/preflatten.tex#L304) (add *"after which dead-code elimination removes the unused `tuple` allocation"*), [`478`](../latex/chapters/preflatten.tex#L478) (add `\cref{fig:tuple_mlton_size_mlton_vs_mlton,fig:con_parallel_bench_size_mpl_vs_mpl}` and note `logic` outlier in `con`), [`850`](../latex/chapters/preflatten.tex#L850) (link back to `\cref{fig:good_flat_rec_func_ssa}`).
  - ~~`shallowflatten.tex`: [`332`](../latex/chapters/shallowflatten.tex#L332), [`636`](../latex/chapters/shallowflatten.tex#L636), [`911`](../latex/chapters/shallowflatten.tex#L911), [`1217`](../latex/chapters/shallowflatten.tex#L1217) (clarify that `MLton_equal` / `MLton_eq` is polymorphic or check if it's in $\mathcal{P}_{\text{flat}}$'s error list).~~
  - `related_work.tex`: [`99, 109, 112, 126`](../latex/chapters/related_work.tex#L99-L126) — cite `\citep{amd64-abi}` (already in `references.bib`!) for ABI signature constraints and contrast intraprocedural PEA (delays `pack` onto escaping branches) with interprocedural `PreFlatten` (clones/specializes the callee so the tuple never escapes across the call)—see `reports/related_work_recommendations.md` Item B.1 for drop-in prose.
- **Substantive Missing Prose / Evaluation Rewrites (21):**
  - [`abstract.tex:3`](../latex/abstract.tex#L3), [`introduction.tex:46`](../latex/chapters/introduction.tex#L46), [`conclusion.tex:2`](../latex/chapters/conclusion.tex#L2), and [`evaluation.tex`](../latex/chapters/evaluation.tex) lines ~~`101, 103`,~~ `116, 122, 431, 496, 642, 673, 704, 799, 857, 1057, 1070, 1092, 1094, 1096, 1239, 1527` (all covered in Parts 1.3, 1.4, and 4.1 above).

---

## Part 5: Style, Terminology, Bibliography, & Complete Typo List

### 5.1 Prose Style & Terminology Consistency

1. **Remove hyphens after `-ly` adverbs and `more` / `most` comparatives (~40 instances across all chapters):**
   - Standard academic style does not hyphenate `more`/`most` comparatives or `-ly` adverbs:
     - Comparatives/superlatives: `more-aggressive` $\to$ `more aggressive`, `more-expensive` $\to$ `more expensive`, `more-similar` $\to$ `more similar`, `more-faithfully` $\to$ `more faithfully`, `more-unlucky` $\to$ `more unlucky`, `most-conservative` $\to$ `most conservative`, `most-profitable` $\to$ `most profitable`, `most-closely` $\to$ `most closely`, `no-more-expensive` $\to$ `no more expensive`, `no-flatter-than` $\to$ `no flatter than`.
     - `-ly` adverbs: `strictly-local` $\to$ `strictly local`, `purely-local` $\to$ `purely local`, `statically-known` $\to$ `statically known`, `newly-emitted` $\to$ `newly emitted`, `modestly-sized` $\to$ `modestly sized`, `sufficiently-large` $\to$ `sufficiently large`, `individually-meaningful` $\to$ `individually meaningful`, `roughly-fixed` $\to$ `roughly fixed`, `previously-observed` $\to$ `previously observed`, `directionally-different` $\to$ `directionally different`, `dynamically-typed` $\to$ `dynamically typed`, `potentially-unboxed` $\to$ `potentially unboxed`, `individually-allocated` $\to$ `individually allocated`, `potentially-unnecessary` $\to$ `potentially unnecessary`, `potentially-unpleasant` $\to$ `potentially unpleasant`, `insufficiently-expressive` $\to$ `insufficiently expressive`.
     - Verbs: `flatten-away` (`related_work.tex:166`) $\to$ `flatten away`; ~~`better-leverage` (`shallowflatten.tex:1221`) $\to$ `better leverage`~~.

2. **Standardize project/technical terms across chapters:**
   - ~~**`MaPLe` (7×) vs. `MPL` (38×):** Introduce `"MaPLe (MPL)"` once in [`introduction.tex:17`](../latex/chapters/introduction.tex#L17) (and [`background.tex:6`](../latex/chapters/background.tex#L6)), then use one consistently (`MPL` dominates 38 to 7).~~
   - ~~**`\texttt{parallel-ml-bench}` (25×) vs. variants:** Replace `\texttt{parallel\_bench}` (`evaluation.tex:49, 917, 1483, 1672`), `\texttt{parallel\_ml\_bench}` (`evaluation.tex:956`), and unformatted `parallel ML bench` (`evaluation.tex:53, 175`) with `\texttt{parallel-ml-bench}`.~~
   - ~~**`AoS` (64×) vs. `AOS` (9×):** Replace all-caps `AOS` in `evaluation.tex` (`lines 916, 949, 1055, 1068, 1086, 1242, 1252, 1269`) with `AoS`.~~
   - ~~**`unflattenable` (13×) vs. `un-flattenable` (3×) vs. `non-flattenable` (2×):** Standardize on `unflattenable`.~~
   - ~~**`Standard ML` (12×) vs. `StandardML` (`shallowflatten.tex:1122`):** Add space.~~
   - **Pass naming in Chapter 6:** `\section{\texttt{array}, \texttt{vector} Flattening}` ([`related_work.tex:130`](../latex/chapters/related_work.tex#L130)) never mentions the name `\texttt{ShallowFlatten}` until line 187 (`\texttt{SoA}-\texttt{ShallowFlatten}`); name `\texttt{ShallowFlatten}` in the opening paragraph of §6.2 to mirror §6.1.
   - ~~**Dashes:** [`related_work.tex:145, 151`](../latex/chapters/related_work.tex#L145) use spaced Unicode en-dashes ` – ` whereas the rest of the thesis uses `--` (or unspaced em-dashes `---`). Pick one convention thesis-wide.~~

3. ~~**Citation & Cross-Reference Grammar (`\citet` vs. `\citep`, `\cref`):**~~
   - ~~**Plural `\citet` subjects with singular verbs in [`related_work.tex`](../latex/chapters/related_work.tex):**~~ Because `\citet{...}` expands to the author list, 11 sentences read ungrammatically in the PDF (e.g., *"Hannan and Hicks [15] introduces"*, *"Bergstrom and Reppy [16] solves"*, *"Peyton Jones and Launchbury [19] introduces"*, *"Melançon, Feeley, and Serrano [24] applies"*, *"Stadler, Würthinger, and Mössenböck [27] introduces"*, *"Bergstrom et al. [28] applies"*, *"Henriksen et al. [30] also discusses"*, *"Li et al. [32] also investigates"*, *"Ureche et al. [34] proposes"*, *"Dolby and Chien [35] addresses"*, *"Budimlić, Joyner, and Kennedy [36] extends"*). Either pluralize the verbs (`introduce`, `solve`, `apply`, ...) or write *"The work of \citet{...} introduces..."*.
   - ~~**`in \citet{...}` $\to$ `by \citet{...}` or `\citep{...}`:**~~ Fix phrases like *"first introduced in `\citet{flat-paper}`"* (`introduction.tex:16, 17`), *"as described in `\citet{mpl-orig}`"* (`evaluation.tex:1226`), *"as defined in the language specification `\citet{sml-def}`"* (`shallowflatten.tex:1123, 1194`), *"coined in `\citet{intel-simd-journal}`"* (`related_work.tex:203`), *"The recent work `\citet{closure-sharing-paper}` examines"* (`related_work.tex:35` $\to$ *"Recent work by `\citet{closure-sharing-paper}`"*), and replace the 3 raw `\cite{...}` calls (`introduction.tex:15`, `background.tex:16, 1315`) with `\citep{...}`.
   - ~~**`\cref` glitches:**~~
     - [`background.tex:356`](../latex/chapters/background.tex#L356): `Figures \cref{fig:pseudo_small_bb0}...` renders as `"Figures fig. 2.5..."` $\to$ use `\Cref{fig:pseudo_small_bb0,fig:pseudo_small_bb1,fig:pseudo_small_bb2,fig:pseudo_small_bb3}`.
     - [`background.tex:17`](../latex/chapters/background.tex#L17): `Figure~\ref{fig:mlton-ir-pipeline}` (the only `\ref` in the thesis) $\to$ `\cref{fig:mlton-ir-pipeline}`. Consider loading `\usepackage[capitalise,noabbrev]{cleveref}` in [`defs.tex:160`](../latex/defs.tex#L160) so mid-sentence `\cref` renders `"Figure 2.1"` / `"Section 3.3"` instead of `"fig. 2.1"` / `"section 3.3"`.
     - [`background.tex:1554`](../latex/chapters/background.tex#L1554): `translation of the \cref{fig:nested_tuple_flattened}` $\to$ drop `the`.
     - [`evaluation.tex:746`](../latex/chapters/evaluation.tex#L746): `On \cref{fig:con_parallel_bench}` $\to$ `In \cref{fig:con_parallel_bench}`.

### 5.2 Bibliography (`references.bib` & `solution.tex`) Fixes

1. ~~**Suppress `. en.` printed across \~25 bibliography entries:**~~
   - ~~`references.bib` sets `language = "en"`, which `biblatex` prints literally as `. en.` after titles on pages 100–102 (e.g., *`Guy E Blelloch. Vector models for data-parallel computing. en. Artificial Intelligence...`*). Add `\AtEveryBibitem{\clearlist{language}\clearfield{month}}` after `\usepackage[...]{biblatex}` in [`solution.tex:128`](../latex/solution.tex#L128) (which also silences Biber's two warnings on `month = {September}` / `{August}` in `mlton-proj` and `mpl-orig`).~~
2. ~~**Fix 4 incomplete/misattributed entries in [`latex/references.bib`](../latex/references.bib):**~~
   - ~~**`layout-poly-paper` (`lines 363-371`):** Has no `author` and no `year`, so `\citet{layout-poly-paper}` renders inline on p. 94 as *"in e.g. Unboxed types for OCaml :: Jane Street [29]"*! Add `author = {Eisenberg, Richard A.}` and `year = {2023}` (or cite Eisenberg's ML '23 paper / Lorenzen et al. ICFP '24).~~
   - ~~**`data-parallel-haskell` (`lines 830-844`):** Currently `@MISC` with no `year` and no `booktitle`, and writes `Jones, Simon Peyton` (parsing surname as `Jones` rather than `Peyton Jones` as in `[19, 20]`). Change to `@inproceedings`, `author = {Chakravarty, Manuel M. T. and Leshchinskiy, Roman and Peyton Jones, Simon and Keller, Gabriele and Marlow, Simon}`, `booktitle = {Proceedings of the ACM SIGPLAN Workshop on Declarative Aspects of Multicore Programming (DAMP '07)}`, `pages = {10--18}`, `year = {2007}`.~~
   - ~~**`intel-simd-journal` (`lines 846-853`):** Currently attributes the journal issue title `"Intel Technology Journal {Q2}, 1999"` to managing editor `Chao, Lin`. The actual article coining AoS/SoA in that issue is: `author = {Abel, James and Balasubramanian, Kumar and Bargeron, Mike and Craver, Tom and Phlipot, Mike}`, `title = {Applications tuning for {Streaming SIMD Extensions}}`, `journal = {Intel Technology Journal}`, `volume = {3}`, `number = {Q2}`, `year = {1999}`.~~
   - ~~**`adt4hpc-paper` (`lines 407-413`):** `@PHDTHESIS` missing `school = {Universit{\'e} de Lyon}` (ENS de Lyon).~~
3. ~~**Minor BibTeX polish:**~~
   - ~~Protect capitalization in `virgil-paper` (`{Virgil III}`), `sml-def` (`{Standard ML}`, and note 1997 is *The Definition of {Standard ML} (Revised)*; drop redundant `series = "The MIT Press"`), `realtime-sml-paper` (`an {SML} compiler`), and `java-scicomp` (`{Java}`).~~
   - ~~In [`solution.tex:270`](../latex/solution.tex#L270), remove `\nocite{*}` before adding any exploratory BibTeX entries so uncited references are not silently appended to the bibliography.~~
   - ~~Optional cleanup in [`defs.tex:48-150`](../latex/defs.tex#L48-L150): duplicate `\usepackage{soul}` on lines 48 and 52, plus \~90 lines of unused math/calculus macros (`\Hessian`, `\curl`, `\Laplace`, `\contradiction`, `\pder`, etc.).~~

### 5.3 Exhaustive Line-by-Line Typo & Grammar Table

> **Note:** `MLton` is pronounced "milton", so `"a MLton ..."` (e.g., `a MLton stack operation`, `a \texttt{MLton.eq}`) is correct; do not change `"a MLton"` to `"an MLton"`.

| File & Line | Current Text | Suggested Fix |
| :--- | :--- | :--- |
| [`introduction.tex:8`](../latex/chapters/introduction.tex#L8) | ~~`disasterous`~~ | `disastrous` |
| [`introduction.tex:27`](../latex/chapters/introduction.tex#L27) | ~~`optimizations interact poorly ... and so fails`~~ | `...and so fail` (subject-verb agreement) |
| [`introduction.tex:39`](../latex/chapters/introduction.tex#L39) | ~~`materialzing`~~ | `materializing` |
| [`introduction.tex:40`](../latex/chapters/introduction.tex#L40) | ~~`on the order of as 10\%`~~ | `on the order of 10\%` |
| [`background.tex:10`](../latex/chapters/background.tex#L10) | ~~`MLton and MPL broadly interchangeable`~~ | `MLton and MPL are broadly interchangeable` |
| [`background.tex:64`](../latex/chapters/background.tex#L64) | ~~`guarntees`~~ | `guarantees` |
| [`background.tex:70-71`](../latex/chapters/background.tex#L70-L71) | ~~`codgen backends ... consider only on the C backend`~~ | `codegen backends ... consider only the C backend` |
| [`background.tex:179`](../latex/chapters/background.tex#L179) | ~~`implemeting`~~ | `implementing` |
| [`background.tex:187`](../latex/chapters/background.tex#L187) | ~~`introduces new sum type`~~ | `introduces a new sum type` |
| [`background.tex:561, 563`](../latex/chapters/background.tex#L561) | ~~`correspondance` (×2)~~ | `correspondence` |
| [`background.tex:916`](../latex/chapters/background.tex#L916) | ~~`Type types are mapped to C \texttt{struct} types`~~ | `Tuple types are mapped to C \texttt{struct} types` |
| [`background.tex:919-920`](../latex/chapters/background.tex#L919-L920) | ~~`a MLton stack operation`~~ ~~`... medatadata`~~ | ~~`an MLton stack operation`~~ `... metadata` |
| [`background.tex:1288`](../latex/chapters/background.tex#L1288) | ~~`hte` (in TODO)~~ | `the` |
| [`background.tex:1505`](../latex/chapters/background.tex#L1505) | ~~`pathogical`~~ | `pathological` |
| [`background.tex:1985`](../latex/chapters/background.tex#L1985) | ~~`disasterous`~~ | `disastrous` |
| [`background.tex:2100, 2198`](../latex/chapters/background.tex#L2100) | ~~`while executing (a)` (missing period)~~ | `while executing (a).` |
| [`background.tex:2110`](../latex/chapters/background.tex#L2110) | ~~`travsered`~~ | `traversed` |
| [`background.tex:2135`](../latex/chapters/background.tex#L2135) | ~~`from the the program`~~ | `from the program` |
| [`preflatten.tex:5`](../latex/chapters/preflatten.tex#L5) | ~~`agressive`~~ | `aggressive` |
| [`preflatten.tex:108`](../latex/chapters/preflatten.tex#L108) | ~~`defintion`~~ | `definition` |
| [`preflatten.tex:233`](../latex/chapters/preflatten.tex#L233) | ~~`of a a \texttt{datatype}`~~ | `of a \texttt{datatype}` |
| [`preflatten.tex:311, 314`](../latex/chapters/preflatten.tex#L311) | ~~`\texttt{PreFlateen}` / missing period on line 314~~ | `\texttt{PreFlatten}` / add trailing period |
| [`preflatten.tex:709`](../latex/chapters/preflatten.tex#L709) | ~~`Unflattenable arguments are is marked`~~ | `Unflattenable arguments are marked` |
| [`preflatten.tex:792`](../latex/chapters/preflatten.tex#L792) | ~~`arguments to a non-tail corresponds`~~ | `arguments to a non-tail call corresponds` |
| [`shallowflatten.tex:3`](../latex/chapters/shallowflatten.tex#L3) | ~~`agressive`~~ | `aggressive` |
| [`shallowflatten.tex:424-425`](../latex/chapters/shallowflatten.tex#L424-L425) | ~~`an length-$n$ \texttt{(int * int)}`~~ | `a length-$n$ \texttt{(int * int) array}` |
| [`shallowflatten.tex:427`](../latex/chapters/shallowflatten.tex#L427) | ~~`homogoneous`~~ | `homogeneous` |
| [`shallowflatten.tex:467`](../latex/chapters/shallowflatten.tex#L467) | ~~`# Consuming still code uses 'p'`~~ | `# Consuming code still uses 'p'` |
| [`shallowflatten.tex:557, 613`](../latex/chapters/shallowflatten.tex#L557) | ~~Captions missing final period~~ | Add trailing `.` |
| [`shallowflatten.tex:562`](../latex/chapters/shallowflatten.tex#L562) | ~~`inserting pack/unpack operations allow us`~~ | `inserting pack/unpack operations allows us` |
| [`shallowflatten.tex:931`](../latex/chapters/shallowflatten.tex#L931) | ~~`of \texttt{ShallowFlatten} We say`~~ | `of \texttt{ShallowFlatten}, we say` |
| [`shallowflatten.tex:1197-1198`](../latex/chapters/shallowflatten.tex#L1197-L1198) | ~~`would to be disable ...`~~ ~~`a \texttt{MLton.eq}`~~ | `would be to disable ...` ~~`an \texttt{MLton.eq}`~~ |
| [`shallowflatten.tex:1214, 1222`](../latex/chapters/shallowflatten.tex#L1214) | ~~`substanial` (×2)~~ | `substantial` |
| [`evaluation.tex:3`](../latex/chapters/evaluation.tex#L3) | ~~`evalutation`~~ | `evaluation` |
| [`evaluation.tex:25`](../latex/chapters/evaluation.tex#L25) | ``` ``bigger number on the test side ``` | ``` ``bigger number on the test side'' ``` |
| [`evaluation.tex:62, 72`](../latex/chapters/evaluation.tex#L62) | `\texttt{delunay}` (×3) | `\texttt{delaunay}` |
| [`evaluation.tex:90`](../latex/chapters/evaluation.tex#L90) | ~~`formed from hash of`~~ | `formed from a hash of` |
| [`evaluation.tex:150`](../latex/chapters/evaluation.tex#L150) | `flattning` | `flattening` |
| [`evaluation.tex:182`](../latex/chapters/evaluation.tex#L182) | `optimzation` | `optimization` |
| [`evaluation.tex:305`](../latex/chapters/evaluation.tex#L305) | `spwaning` | `spawning` |
| [`evaluation.tex:321`](../latex/chapters/evaluation.tex#L321) | `paralllel` | `parallel` |
| [`evaluation.tex:350-352`](../latex/chapters/evaluation.tex#L350-L352) | `code bloat that caused ... backend bound? ... conflusions` | `...frontend-bound? ... conclusions` (note line 350 repeats `backend-bound` for code bloat!) |
| [`evaluation.tex:507`](../latex/chapters/evaluation.tex#L507) | `examinining` | `examining` |
| [`evaluation.tex:576`](../latex/chapters/evaluation.tex#L576) | `benhcmark` | `benchmark` |
| [`evaluation.tex:640, 642`](../latex/chapters/evaluation.tex#L640) | `recurisve` (×2) | `recursive` |
| [`evaluation.tex:676`](../latex/chapters/evaluation.tex#L676) | `investiage` | `investigate` |
| [`evaluation.tex:702`](../latex/chapters/evaluation.tex#L702) | `functons` | `functions` |
| [`evaluation.tex:712`](../latex/chapters/evaluation.tex#L712) | `inded purpose ... majr wins` | `intended purpose ... major wins` |
| [`evaluation.tex:916`](../latex/chapters/evaluation.tex#L916) | `poisitive` | `positive` |
| [`evaluation.tex:952`](../latex/chapters/evaluation.tex#L952) | `(a win at low core counts ... high core counts.` | Missing closing `)` |
| [`evaluation.tex:1013`](../latex/chapters/evaluation.tex#L1013) | `paralell` | `parallel` |
| [`evaluation.tex:1035`](../latex/chapters/evaluation.tex#L1035) | `allowing the 2D geometry calculation operate` | `allowing the 2D geometry calculation to operate` |
| [`evaluation.tex:1038`](../latex/chapters/evaluation.tex#L1038) | `unchaned` | `unchanged` |
| [`evaluation.tex:1067-1068`](../latex/chapters/evaluation.tex#L1067-L1068) | `additon ... matching out expectations` | `addition ... matching our expectations` |
| [`evaluation.tex:1074`](../latex/chapters/evaluation.tex#L1074) | `trend for \texttt{quickhull}` | `the trend for \texttt{quickhull}` |
| [`evaluation.tex:1084-1088`](../latex/chapters/evaluation.tex#L1084-L1088) | `verison ... poiners ... hierachy` | `version ... pointers ... hierarchy` |
| [`evaluation.tex:1226`](../latex/chapters/evaluation.tex#L1226) | `hte` | `the` |
| [`evaluation.tex:1239`](../latex/chapters/evaluation.tex#L1239) | `spawing` | `spawning` |
| [`evaluation.tex:1241-1242`](../latex/chapters/evaluation.tex#L1241-L1242) | `Noting from ... note that ... runes` | `Noting from ... that ... runs` |
| [`evaluation.tex:1265`](../latex/chapters/evaluation.tex#L1265) | `conunt` | `count` |
| [`evaluation.tex:1288`](../latex/chapters/evaluation.tex#L1288) | `completley` | `completely` |
| [`evaluation.tex:1502`](../latex/chapters/evaluation.tex#L1502) | `exhbit` | `exhibit` |
| [`evaluation.tex:1515`](../latex/chapters/evaluation.tex#L1515) | `algorith ... addreses` | `algorithm ... addresses` |
| [`evaluation.tex:1525`](../latex/chapters/evaluation.tex#L1525) | `indcrease` | `increase` |
| [`related_work.tex:57`](../latex/chapters/related_work.tex#L57) | `analyis` | `analysis` |
| [`related_work.tex:102`](../latex/chapters/related_work.tex#L102) | ``` ``scalar replacement of aggregates,'' (SROA) ``` | ``` ``scalar replacement of aggregates'' (SROA), ``` |
| [`related_work.tex:173-174`](../latex/chapters/related_work.tex#L173-L174) | `allow programmers to regions of code ... arays` | `allow programmers to annotate regions of code ... arrays` |
