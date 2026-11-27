# Soundness Investigation of `ShallowFlatten` (`shallowflatten.tex` TODO)

**Date:** November 27, 2026  
**Triggered by:** `\hl{TODO: are we actually sound here? perhaps not -- we don't detect the mlton.eq case}` in [`latex/chapters/shallowflatten.tex`](../latex/chapters/shallowflatten.tex#L1217)  
**Repositories audited:** `~/code/mlton`, `~/code/mpl`, `~/code/parallel-ml-bench`, `~/code/mpl-opt-writeup`

---

## Executive Summary

1. **Is `ShallowFlatten` sound with respect to `MLton_eq` and other primitives?**
   **No.** Moreover, the unsoundness is **more severe than the `MLton.eq`-on-tuples case alone**, and there is a sharp asymmetry between **SoA** and **AoS**:
   - **Pure Standard ML 97 violations (no `MLton.*` or MPL extensions required):**
     1. **SoA breaks Standard ML array equality (`=` on `'a array`)**, causing `a = a'` to return `false` for aliases of the same array and causing **silent data corruption in `ArraySlice.copy`** (and spurious `Span` exceptions in `ArraySlice.span`). This happens because `PolyEqual` runs *before* `ShallowFlatten`, lowering array `=` to `Prim.MLton_eq`; SoA rewrites the array type to a tuple of arrays `(t array * ... * t array)` without rewriting `MLton_eq`, so `MLton_eq` ends up comparing ephemeral wrapper tuples that `Flatten` and nested `ShallowFlatten` freely re-box. **AoS does not have this bug** (it preserves a single array object).
     2. **AoS has an unchecked length-multiplication overflow in `Array_alloc`**, which under `-default-type int64` (the flag used by `parallel-ml-bench`) wraps `n * tupleWidth` modulo $2^{64}$ to a tiny allocation instead of failing with OOM/Size, creating a **heap buffer overflow** in pure Standard ML.
     3. **Both AoS and SoA crash the compiler (`raised: Option`)** on 5 container primitives that `doesPolicyFlattenStatement` marks as flattenable (`Array_copyArray`, `Array_copyVector`, `Vector_vector`, `Array_array`, and MPL's `Array_cas`). Standard `Array.copy` / `ArraySlice.copy` with `len >= 5` and vector literals `#[(x, y), ...]` immediately crash compilation.
   - **MLton / MPL extension violations:**
     4. **`MLton.eq` on tuples round-tripped through arrays** changes from `true` to `false` under **both AoS and SoA** (confirming the `shallowflatten.tex` TODO).
     5. **`MLton.Weak` (and `MLton.Finalizable`) on flattened arrays breaks under SoA** (preserved under AoS): `Weak.new a` tracks the ephemeral wrapper tuple `(a_0, a_1)`, which GC can collect while the underlying component arrays are still live and actively mutated.
     6. **`MLton.size` changes output under SoA** (verified on MLton's own `regression/size.sml`: `104` $\to$ `152` bytes due to extra array headers and wrapper tuple).
     7. **Concurrent tuple tearing in MPL** occurs under both AoS and SoA for racy `Array.update`/`Array.sub` — **but stock MPL Baseline (`DeepFlatten`) already tears too**, so this does not weaken MPL's memory model (only `Array_cas` is atomic).
   - **Primitives that *are* preserved soundly:** `MLton_equal` on vectors (structural fallback after `MLton_eq` fast path), `MLton.hash` (`PolyHash`), FFI `CFunction` (elaborator forbids tuple arrays from crossing FFI), and `Array_uninit` / `Array_uninitIsNop`.

2. **Do any benchmarks in `parallel-ml-bench` (or MLton's suite) have their semantics changed?**
   **No (0 benchmarks affected).** We dumped and analyzed `.shallowFlatten.pre.ssa` and `.shallowFlatten.post.ssa` across:
   - All **34** benchmarks in `parallel-ml-bench/exp.json` (under `mpl-soa`, `mlton-soa` with `maxWidthSameType:3`, and even heterogeneous `maxWidth:3`): **11** benchmarks are transformed under `maxWidthSameType:3`, and **0** contain `MLton_eq`, `Array_cas`, `Weak_*`, `MLton_size`, `MLton_share`, or unsupported container prims on any flattened container type, datatype containing a flattened container, or flattened tuple element type.
   - All **89** compilable benchmarks in `parallel-ml-bench/mpl/bench/` (26 transformed under `maxWidthSameType:3`): **0** semantic or compiler-crash hits.
   - All **MLton suite benchmarks** (`.MLton0.batch.sml`): only `flat-array` is transformed; it contains **0** `MLton_eq` calls.
   - **32 MLton regression tests** (`array*`, `vector*`, `flat-array*`, `eq`, `poly-equal*`, `weak*`, `finalize*`, `size`, `mlton.share`): 31/32 match Baseline identically; only `size.sml` differs under SoA (`104` vs. `152` bytes).

3. **Do other MLton/MPL compiler passes actually preserve `MLton.eq`?**
   **Your suspicion is completely right — stock MLton/MPL passes do *not* preserve `MLton.eq` on immutable tuples, and MLton's own manual calls its semantics "murky."**
   - Stock **`Flatten`**, **`CommonSubexp`**, **`Useless`**, **`SimplifyTypes`**, and **`PreFlatten`** all break `MLton.eq` on immutable tuples (we experimentally reproduced `Flatten` turning `MLton.eq (p, id p)` from `true` to `false`, `CommonSubexp` turning `MLton.eq ((x, y), (x, y))` from `false` to `true`, and `Useless` turning `MLton.eq ((w, "hello"), (w, "world"))` from `false` to `true` even for *structurally unequal* tuples!).
   - By contrast, **all stock passes strictly preserve `MLton.eq` on mutable objects (`array`, `ref`, `weak`)**, because Standard ML's `=` on `array` and `ref` is lowered to `MLton_eq`. `DeepFlatten` (in SSA2) explicitly guards `MLton_eq`, `MLton_size`, `MLton_share`, `Array_cas`, `Ref_cas`, `Weak_new`, and `CFunction` with `Value.dontFlatten` — primarily for SSA2-to-RSSA representation soundness, which *incidentally* keeps `MLton.eq (p, Array.sub (arr, i))` returning `true` in stock MLton.

---

## 1. Detailed Soundness Analysis of `ShallowFlatten`

### 1.1 Pipeline Context

In both `mlton/ssa/simplify.fun` (`~/code/mlton/mlton/ssa/simplify.fun:78-108`, `~/code/mpl/mlton/ssa/simplify.fun:85-115`), the relevant SSA pass order is:

```
constantPropagation -> useless -> simplifyTypes -> polyEqual -> polyHash
  -> ... -> localRef -> shallowFlatten -> preFlatten -> flatten -> localFlatten3
  -> ... -> commonSubexp1 -> shareZeroVec -> ... -> [SSA2: deepFlatten -> refFlatten]
```

Two ordering facts drive almost all the soundness issues below:
1. **`PolyEqual` runs *before* `ShallowFlatten`.** Standard ML's polymorphic `=` on `'a array` has already been lowered to `Prim.MLton_eq['a array]` (`mlton/ssa/poly-equal.fun:405`) by the time `ShallowFlatten` sees the program.
2. **`Flatten` (and `PreFlatten`, `CommonSubexp`) run *after* `ShallowFlatten`.** Any wrapper tuple introduced by SoA (`int array * int array`) is treated by `Flatten` as an ordinary immutable SML tuple that can be unpacked and re-allocated freely.

---

### 1.2 Pure Standard ML 97 Soundness Bugs

#### Bug 1 (SoA only): Broken Standard ML Array Equality (`=`) and Silent `ArraySlice.copy` Corruption

**Root cause:**
In `shallow-flatten.fun:1150-1193`, `MLton_eq` is not in `isContainerPrim`, so `doesPolicyFlattenStatement` returns `false`. `deepFlattenStatementsForConfig` then runs `updateTypesInStatement`, rewriting:
```
prim MLton_eq[((word32, word32) tuple) array] (a, b)
  ==>
prim MLton_eq[((word32) array, (word32) array) tuple] (a, b)
```
Under `ssa2-to-rssa.fun:1679-1703`, `MLton_eq` on a tuple type compiles to raw `Objptr` word equality — comparing the heap addresses of the **wrapper tuples**, not the underlying arrays. Whenever any pass reconstructs a fresh wrapper tuple for the same underlying component arrays, `a = a'` returns `false`:
- **Via `Flatten` on a `datatype` constructor:** `datatype box = Box of (int * int) array` gets flattened by `Flatten` to `Box of int array * int array`, which allocates a fresh wrapper tuple on `case` extraction.
- **Via `ShallowFlatten` itself on nested arrays:** `((int * int) array) array` becomes `(int array * int array) array` and then (even with `-shallow-flatten-max-iters 1`, because `deepFlattenStatementsForConfig:1231-1239` calls `recursiveFlatten` both before and after `updateTypesInStatement`) `(int array array * int array array)`. `Array.sub` then packs a fresh wrapper tuple.
- **Via `Array_toArray`:** `buildArrayToArray` (`shallow-flatten.fun:620-640`) allocates a fresh wrapper tuple even though `Array_toArray` is an in-place header cast (`ssa2-to-rssa.fun:1513-1549`).

**Experimental reproducer 1 (`test_soundness.sml`, pure SML 97):**
```sml
datatype box = Box of (int * int) array | Empty
fun unbox (n, b) =
  if n <= 0 then (case b of Box a => a | Empty => Array.array (1, (0, 0)))
  else unbox (n - 1, b)

val a = Array.array (3, (n + 1, n + 2))
val r1b_box = (a = unbox (n, if n >= 0 then Box a else Empty))
val aa = Array.array (2, a)
val r1c_aa = (a = Array.sub (aa, 0))
```
Observed results (compiled with `maxWidthSameType:3`, `max-iters 1`):

| Check | Expected (SML '97) | MLton Baseline | MLton AoS | MLton SoA | MPL SoA |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `1b: a = unbox (Box a)` | `true` | `true` | `true` | **`false`** | **`false`** |
| `1c: a = Array.sub (aa, 0)` | `true` | `true` | `true` | **`false`** | **`false`** |

**Experimental reproducer 2 (`t4e_corrupt.sml`, silent `ArraySlice.copy` data corruption in pure SML 97):**
The Standard ML Basis Library (`basis-library/arrays-and-vectors/sequence0.sml:203, 229, 485`) implements `ArraySlice.copy` for `len < 5` (`smallCopyLimit`) using `fun overlap () = S.sameArray (dst, src) andalso si < di` where `sameArray = op =`. If `src` holds a slice of an unboxed alias of `dst`, `sameArray` falsely returns `false` under SoA, copying forward (`0 -> 1 -> 2 -> 3`) instead of backward (`3 -> 2 -> 1 -> 0`):
```sml
val a = Array.tabulate (5, fn i => (i + 1, (i + 1) * 10))
val a_alias = unbox (n, if n >= 0 then Box a else Empty)
val _ = ArraySlice.copy {src = ArraySlice.slice (a_alias, 0, SOME 4), dst = a, di = 1}
```
Observed output:
- **MLton Baseline:** `(1,10) (1,10) (2,20) (3,30) (4,40)` (correct)
- **MLton SoA:** `(1,10) (1,10) (1,10) (1,10) (1,10)` (**silent memory/data corruption!**)

The same `sameArray = op =` check is used in `ArraySlice.span` (`sequence0.sml:434-440`), which will spuriously raise `Span` on two slices of the same array under SoA.

**Why AoS is immune:** In AoS, `(t * t) array` becomes a single `t array`, so `MLton_eq[t array](a, b)` still compares the single canonical heap object pointer.

**Clean fix for SoA:** Rewrite `Prim.MLton_eq[(t1 * ... * tn) array](a, b)` into:
```
a0 = select(a, 0)
b0 = select(b, 0)
res = prim MLton_eq[t1 array](a0, b0)
```
Because component arrays are always allocated together by `buildArrayAlloc` and never re-paired across distinct source arrays, pointer identity of component `0` is a 1-to-1 invariant of the source array's identity (note `ShareZeroVec` only transforms arrays converted to vectors via `Array_toVector`, never mutable arrays tested with `=`).

---

#### Bug 2 (AoS only): Unchecked `Array_alloc` Length Overflow (Heap Buffer Overflow)

**Root cause:**
`buildArrayAlloc` in AoS (`shallow-flatten.fun:753-763, 891-902`) computes the flattened allocation length as:
```sml
prim = Prim.Word_mul (WordSize.seqIndex (), {signed = false})
```
with **no overflow check**. Under `-default-type int64` (the default in `parallel-ml-bench/mpl/Makefile:4`), `Array.maxLen = 2^63 - 1 = 9223372036854775807`. For a 3-tuple array with `n = 6148914691236517206` ($\approx 2^{64}/3 \le \texttt{Array.maxLen}$), the Basis bounds check `n <= Array.maxLen` passes, and then `n * 3` wraps modulo $2^{64}$ to **`2`**.

**Experimental reproducer (`t5_tab2.sml`, compiled with `-default-type int64`):**
```sml
val n : int = 6148914691236517206
val a : (int * int * int) array =
  Array.tabulate (n, fn i => if i = 1 then raise Fail "ALLOC_SUCCEEDED_WRAPPED" else (i, i, i))
```
Observed output:
- **MLton Baseline:** `Out of memory. Unable to allocate sequence with 5555555555555556 elements and elements of size 24 bytes.` (exit 1)
- **MLton AoS:** `Caught Fail: ALLOC_SUCCEEDED_WRAPPED` — it allocated a **2-element (16-byte)** `int64 array` and wrote **3 elements (24 bytes)** at index 0 before `i = 1` raised `Fail`! (Without the exception, the loop would overwrite the heap past the buffer.)

**Clean fix:** Check `n > maxSeqIndex div tupleWidth` (or use `Word_mulCheckP`) and raise `Size` (or jump to an OOM/Size handler) before calling `Array_alloc`.

---

#### Bug 3 (Both AoS and SoA): Unimplemented Container Primitives Crash Compilation (`raised: Option`)

`doesPolicyFlattenStatement` (`shallow-flatten.fun:1155-1170`) claims 15 container primitives are flattenable, while `maybeFlattenStatement` (SoA, lines 661-683) and `maybeFlattenStatementAoS` (AoS, lines 1019-1045) only handle 10 of them. Encountering any of the remaining 5 hits `Option.valOf NONE` at line 1203:

| Primitive | How triggered in SML / MPL | Tested Result (SoA & AoS) | Implementable? |
| :--- | :--- | :--- | :--- |
| `Prim.Array_copyArray` | `Array.copy` / `ArraySlice.copy` with `len >= 5` (`sequence0.sml:203`) | **Compiler crash (`raised: Option`)** | Yes (AoS: multiply `di, si, len` by `n`; SoA: copy each component array) |
| `Prim.Array_copyVector` | `Array.copyVec` / `ArraySlice.copyVec` with `len >= 5` | **Compiler crash (`raised: Option`)** | Yes (same as `Array_copyArray`) |
| `Prim.Vector_vector` | Vector literals `#[(x, y), ...]` (`-default-ann 'allowVectorExps true'`) | **Compiler crash (`raised: Option`)** | Yes (AoS: flatten element list; SoA: `n` `Vector_vector` prims + `Tuple`) |
| `Prim.Array_array` | Emitted by `ConstantPropagation` (`constant-propagation.fun:1001`) | Compiler crash (`raised: Option`) | Yes (same as `Vector_vector`) |
| `Prim.Array_cas _` (MPL) | `MLton.Parallel.arrayCompareAndSwap` on tuple array | **Compiler crash (`raised: Option`)** (Baseline works and prints `8`) | **No** (no portable single-instruction multi-word CAS for arbitrary widths / SoA) |

---

### 1.3 MLton and MPL Extension Primitives

#### Issue 4 (Both AoS and SoA): `MLton.eq` on Tuples Round-Tripped Through Arrays

This is the exact case noted in `shallowflatten.tex:1113-1217`. Because `ShallowFlatten` replaces `Array_sub` with a fresh `Tuple(...)` pack and never inspects `MLton_eq`:
```sml
val arr = Array.array (3, (0, 0))
val p = (n + 1, n + 2)
val _ = Array.update (arr, 1, p)
val p' = Array.sub (arr, 1)
val eq = MLton.eq (p, p')
```
Observed output (`test_mlton_eq.sml`):
- **MLton Baseline:** `true` (because `DeepFlatten` explicitly calls `Value.dontFlatten` on `MLton_eq` args and therefore declines to flatten `arr`!)
- **MLton AoS:** `false`
- **MLton SoA:** `false`

**Subtle `parallel-ml-bench` MLton-compat consequence:** In `parallel-ml-bench/mpl/lib/github.com/mpllang/mpllib/compat/mlton.sml:29-32`, sequential MLton emulates `Concurrency.casArray` as:
```sml
fun casArray (a, i) (x, y) =
  let val current = Array.sub (a, i)
  in if MLton.eq (x, current) then Array.update (a, i, y) else (); current end
```
If any MLton program called `Concurrency.casArray` on a flattened tuple array, unlike MPL (which crashes at compile time on `Array_cas`), MLton would silently compile it and `MLton.eq (x, current)` would spuriously return `false`!

#### Issue 5 (SoA only): `MLton.Weak` (and `MLton.Finalizable`) Premature Collection on Arrays

Under SoA, `MLton.Weak.new a` creates a weak pointer to the **wrapper tuple** `Tuple(a_0, a_1)`. Once `Flatten` or local optimization extracts `a_0` and `a_1`, the wrapper tuple has no remaining live references and is reclaimed on the next GC **while the array `a` is still live and in use**.

**Experimental reproducer (`test_weak.sml`):**
```sml
val a = Array.array (10, (n, n + 1))
val w = MLton.Weak.new a
val _ = MLton.GC.collect ()
val aliveBefore = isSome (MLton.Weak.get w)
val s = useArr (n, a)   (* mutates and reads `a` across GCs *)
```
Observed output:
- **MLton Baseline:** `sum=13 aliveBefore=true aliveAfterUse=false`
- **MLton AoS:** `sum=13 aliveBefore=true aliveAfterUse=false`
- **MLton SoA:** `sum=13 aliveBefore=false aliveAfterUse=false` (**weak ref cleared while `a` is live!**)

Because `MLton.Finalizable` is built on `MLton.Weak`, finalizers attached to SoA-flattened arrays will fire prematurely.

*(Similarly, `Weak.new` on a tuple stored only inside a flattened array breaks under both AoS and SoA, because the original tuple pointer is never stored in the array.)*

#### Issue 6 (`MLton.size` and `MLton.share`)

- **`MLton.size`:** Directly observes heap layout. Confirmed on MLton's own `regression/size.sml`:
  - Baseline: `"The size of an array of length 10 of 2-ples of ints is = 104 bytes."`
  - AoS: `104 bytes` (matches Baseline, where `DeepFlatten` inlines the 10 pairs into 1 array: $10 \times 8 + 24 = 104$).
  - **SoA:** **`152 bytes`** (two 10-element `int32` arrays of 64 bytes each + 24-byte 2-tuple wrapper).
- **`MLton.share`:** Operates on immutable heap graphs. Under SoA, the wrapper tuple is immutable, though its children are mutable arrays (so distinct arrays won't be merged, while two wrapper tuples for the same array could be). Under both AoS and SoA, tuples stored in arrays no longer exist as separate heap objects to share.

#### Issue 7 (MPL): Concurrent Tuple Tearing on Racy `Array.update` / `Array.sub`

Under true AoP (disabling `deepFlatten`), `Array.update (a, 0, (k, k))` is a single pointer-sized write, so a concurrent reader in `ForkJoin.par` never observes a torn pair `x <> y`. Under AoS and SoA, the write splits into multiple stores and tears.

**Experimental result (`test_tearing.sml`, 5M concurrent iterations, 2 procs):**

| Configuration | Torn Observations (`x <> y`) |
| :--- | ---: |
| MPL true AoP (`-disable-pass '(preFlatten.*\|shallowFlatten.*\|deepFlatten)'`) | **0** |
| **MPL Baseline (default, with stock `DeepFlatten`)** | **25,649** |
| MPL AoS | **16,447** |
| MPL SoA | **354,059** |

**Key takeaway:** Stock MPL's `DeepFlatten` **already** flattens non-escaping tuples inline into arrays and tears on racy updates! Thus `ShallowFlatten` does not break MPL's concurrency semantics for ordinary `Array.update`/`Array.sub` (MPL assumes race freedom except for `Array_cas`).

#### Safe / Unaffected Primitives (Verified in Compiler Source)

| Primitive / Feature | Why It Remains Sound |
| :--- | :--- |
| **`MLton_equal` on vectors (`v1 = v2`)** | `PolyEqual` (`poly-equal.fun:245`) emits `MLton_eq(v1, v2) orelse elementwise_loop(v1, v2)`. A spurious `false` from `MLton_eq` under SoA safely falls through to the elementwise loop. |
| **`MLton.hash` (`PolyHash`)** | `poly-hash.fun:525` hashes arrays with a type-only constant (`stateful ()`) and hashes vectors via `Vector_length`/`Vector_sub` loops, which `ShallowFlatten` transforms soundly. |
| **FFI (`Prim.CFunction` / `_import`)** | `mlton/elaborate/elaborate-core.fun:1118-1143` (`toCType`) only permits primitive scalars and 1-level `array`/`ref`/`vector` of valid `CType`s — tuples and arrays of tuples cannot cross FFI. |
| **`Array_uninitIsNop` / `Array_uninit`** | Returning `false` from `Array_uninitIsNop` (`shallow-flatten.fun:607, 977`) is conservative/sound; `ssa2-to-rssa.fun:1590` lowers `Array_uninit` to a no-op for non-pointer element types and writes `bogus` for pointers. |

---

## 2. Benchmark Suite Audit (`parallel-ml-bench` & MLton Suites)

To determine with certainty whether *any* benchmark's semantics could be affected (including compiler-generated `MLton_eq` from `PolyEqual`, basis library calls, or datatype-embedded containers), we compiled every benchmark with `-keep-pass shallowFlatten -stop-pass shallowFlatten` and parsed both `.shallowFlatten.pre.ssa` and `.shallowFlatten.post.ssa`.

### 2.1 `parallel-ml-bench` (`exp.json` — All 34 Evaluation Benchmarks)

Audited under `mpl-soa`, `mlton-soa` (`maxWidthSameType:3`, `max-iters 1`), and additionally under heterogeneous `maxWidth:3` (`mpl-soa-het`):

- **11 / 34 benchmarks** contain flattenable homogeneous tuple containers under `maxWidthSameType:3`:

| Benchmark | Flattened Element Tuple Types | `MLton_eq` Type Args in SSA | Any Overlap / `MLton_eq` Changed? | `Array_cas` Types | `Weak` / `size` / `share` |
| :--- | :--- | :--- | :---: | :--- | :---: |
| `delaunay` | `(real64, real64)`, `(word64, word64, word64)`, `(word8, word8, word8)` | `(word8) vector`, `intInf`, `thread` | **No** | `word64` | None |
| `linearrec` | `(real64, real64)` | `(word8) vector`, `intInf`, `thread` | **No** | None | None |
| `linefit-opt` | `(real64, real64)` | `(word8) vector`, `intInf`, `thread` | **No** | None | None |
| `nearest-nbrs` | `(real64, real64)`, `(word8, word8, word8)` | `(word8) vector`, `intInf`, `thread` | **No** | None | None |
| `ocaml-game-of-life` | `(word8, word8, word8)` | `(word8) vector`, `intInf`, `thread` | **No** | None | None |
| `ocaml-nbody-imm` | `(real64, real64, real64)` | `(word8) vector`, `intInf`, `thread` | **No** | None | None |
| `quickhull` | `(real64, real64)`, `(word64, word64)` | `(state_0) ref`, `(word8) vector`, `intInf`, `thread` | **No** | None | None |
| `raytracer` | `(word64, word64, word64)` | `(state_0) ref`, `(word8) vector`, `intInf`, `thread` | **No** | None | None |
| `seam-carve` | `(word8, word8, word8)` | `(word8) vector`, `intInf`, `thread` | **No** | None | None |
| `suffix-array` | `(word64, word64)` | `(word8) vector`, `intInf`, `t_15`, `thread` | **No** | None | None |
| `tinykaboom` | `(word8, word8, word8)` | `(state_0) ref`, `(word8) vector`, `intInf`, `thread` | **No** | None | None |

- The other **23 / 34** benchmarks in `exp.json` have **no** flattenable homogeneous tuple arrays/vectors at all.
- Even under **heterogeneous `maxWidth:3`** (`mpl-soa-het`), all 34 benchmarks compile cleanly through `shallowFlatten` and have **zero** `MLton_eq` calls on any flattened container, datatype containing a flattened container, or flattened tuple type.

### 2.2 All Remaining Benchmarks in `parallel-ml-bench/mpl/bench/` (92 total)

We also audited all 92 `.mlb` benchmarks in `parallel-ml-bench/mpl/bench/` under `mpl-soa`:
- **3** have pre-existing broken sources (`connectivity`, `spanner` missing `../ldd/LDD.sml`; `delaunay-mostly-pure` undefined `T.boundaryCircle`).
- All **89** compilable benchmarks pass `shallowFlatten` cleanly; **26** have flattenable homogeneous tuple containers.
- **0 / 89** have any `MLton_eq`, `Array_cas`, `Weak_*`, `MLton_size`, `MLton_share`, or unsupported container prim touching a flattened type.
- Source-level `MLton.eq` / `casArray` uses in `mpllib` and extra benchmarks (`MatCOO.sml:75` on `I.int`/`R.real` arrays; `Hashset.sml`, `Hashtable.sml`, `dedup-entangled`, `bfs-tree-entangled` on `'a option array`; `collect/HashTable.sml` on `word64`/`real64` arrays; `ParFuncArray.sml` on log datatypes) never involve flattened tuple arrays or their elements.

### 2.3 MLton Benchmark & Regression Suites

- **MLton benchmark suite (`~/code/mlton/benchmark/tests/*.MLton0.batch.sml`):** Only `flat-array` is transformed by `ShallowFlatten` under `maxWidthSameType:3`; its SSA contains **0** `MLton_eq` calls.
- **MLton regression suite (32 array/vector/eq/weak/finalize/size/share tests):** Under `maxWidthSameType:3`, **31 / 32** compile and produce identical stdout across Baseline, AoS, and SoA. Only **`regression/size.sml`** differs under SoA (`104` vs. `152` bytes for `(int * int) array`).

---

## 3. Do Other Compiler Passes Preserve `MLton_eq`?

**No — not for immutable tuples.** There is a clean, intentional split across MLton and MPL's existing passes:

- **Mutable object identity (`array`, `ref`, `weak`)** is part of Standard ML `=` and is **strictly preserved** by every stock pass.
- **Immutable value pointer identity (`tuple`, `vector`, immutable `datatype`)** is *not* part of Standard ML. MLton's own documentation (`~/code/mlton/doc/guide/src/MLtonStructure.adoc:106-111`) explicitly notes:
  > *"For arrays, datatypes, strings, tuples, and vectors, this is a simple pointer equality. **The semantics is a bit murky.**"*

### Pass-by-Pass Matrix (Verified in Source & Experimentally)

| Pass (File) | Preserves `MLton_eq` on `array`/`ref`? | Preserves `MLton_eq` on immutable tuples? | Mechanism & Experimental Evidence |
| :--- | :---: | :---: | :--- |
| **`Flatten`** (`ssa/flatten.fun`) | Yes | **NO** (`true` $\to$ `false`) | `doitStatement` (`lines 171-196`) ignores `PrimApp` (including `MLton_eq`). Flattens tuples across function args/returns and `datatype` constructors, allocating fresh `Tuple`s at entry (`lines 402-417`). **Confirmed:** `MLton.eq (p, idTup p)` and `MLton.eq (q, unboxT (TBox q))` return **`false`** in stock MLton, `true` with `-disable-pass flatten`. |
| **`CommonSubexp`** (`ssa/common-subexp.fun`) | Yes | **NO** (`false` $\to$ `true`) | Hash-conses `Tuple` and `ConApp` (`lines 98, 165`), merging distinct allocations of equal fields. **Confirmed:** `val t1 = (n+5,n+6); val t2 = (n+5,n+6); MLton.eq (t1, t2)` returns **`true`** in stock MLton. |
| **`Useless`** (`ssa/useless.fun`) | Yes | **NO** (`false` $\to$ `true`, even for *unequal* tuples!) | `MLton_eq` calls `makeWanted` (`lines 627-642, 726-730`), keeping only components useful elsewhere. Unread slots are dropped and 1-element tuples collapse to scalars. **Confirmed (`t_useless3.sml`):** for `u1 = (w+0w1, "hello")`, `u2 = (w+0w1, "world")` (only `#1` read), `MLton.eq (u1, u2)` returns **`true`** in stock MLton, `false` with `-disable-pass useless`! |
| **`SimplifyTypes`** (`ssa/simplify-types.fun`) | Yes | **NO** (`false` $\to$ `true`) | Erases unit/zero-width fields from tuples (`(x, ())` $\to$ `x`) and folds cardinality-1 `MLton_eq` to `true` (`lines 754-766`). |
| **`ShareZeroVec`** (`ssa/share-zero-vec.fun`) | Yes | N/A (`false` $\to$ `true` on empty vectors) | Shares empty arrays converted to vectors globally. |
| **`LocalFlatten`** (`ssa/local-flatten.fun`) | Yes | Yes (jump args) | `PrimApp {args, ...} => forces args` (`line 125`) keeps jump args passed to `MLton_eq` tupled. |
| **`PreFlatten`** (`ssa/pre-flatten.fun`) | Yes | **NO** (under `always` policy) | Inserts fresh `BindTuple` / `BindCon` reconstructions at call/block boundaries (`lines 178-198`). |
| **`DeepFlatten`** (`ssa/deep-flatten.fun`, SSA2) | Yes | **Yes** | Explicitly marks `MLton_eq`, `MLton_size`, `MLton_share`, `Array_cas`, `Ref_cas`, `Weak_new`, `CFunction`, `Spork_forkThreadAndSetData`, and `_` as `Value.dontFlatten` (`lines 852-926`). This is required for SSA2$\to$RSSA lowering (flattened tuples have no `Objptr` to pass to `MLton_eq`), and *incidentally* preserves `MLton.eq (p, Array.sub (arr, i))` in stock MLton. |
| **`RefFlatten`** (`ssa/ref-flatten.fun`, SSA2) | **Yes** | N/A | Marks any `ref` passed to any `PrimApp` (including `MLton_eq`) as `Unflattenable` (`lines 582-625`), and guards `Array_cas`, `Ref_cas`, `MLton_size`, `MLton_share`, `Weak_new`, `CFunction`. |

### Why This Feels Fragile (and How to Think About It)

Your intuition is right: trying to preserve `MLton.eq` on *immutable tuples* in `ShallowFlatten` is fighting a battle that MLton's own earlier passes (`Useless`, `SimplifyTypes`, `Flatten`, `CommonSubexp`) have **already conceded**. Even if `ShallowFlatten` guarded `MLton.eq` on tuples, passing that exact same tuple through an identity function or `datatype` constructor already breaks `MLton.eq` in `Flatten`, and allocating two tuples already merges them in `CommonSubexp`.

By contrast, **mutable container identity (`MLton_eq` on `'a array`, `Weak` on `'a array`) and `Array_cas` (MPL) ARE real soundness obligations** — the former is required by Standard ML 97 itself!

---

## 4. Recommendations for `shallowflatten.tex` (and Future Compiler Fixes)

### For `latex/chapters/shallowflatten.tex` (§ `Limitations`, lines 1105–1226)

1. **Resolve the `\hl{TODO}` at line 1217 accurately:**
   - State clearly that the current prototype **does not** detect `MLton_eq` (or `Weak_new`, `MLton_size`, `MLton_share`), so it is **not generally sound** in the presence of those constructs — and distinguish **three** levels of soundness issues rather than only tuple `MLton.eq`:
     1. **Tuple identity (`MLton.eq` on tuples):** Broken by both AoS and SoA on array round-trips. Crucially, point out that **stock MLton's existing SSA passes (`Flatten`, `CommonSubexp`, `Useless`, `SimplifyTypes`) already do not preserve `MLton.eq` on immutable tuples** (and MLton's manual documents its semantics as "murky"), so treating tuples as identity-less value types aligns with how MLton's SSA optimizer already behaves in practice. (Only `DeepFlatten` in SSA2 preserves it, as a side effect of needing an `Objptr` to lower `MLton_eq`.)
     2. **Container identity (`=` / `MLton_eq` and `MLton.Weak` on flattened *arrays* — SoA only):** Much more serious because `=` on `'a array` is **pure Standard ML 97** (used inside the Basis Library's own `ArraySlice.copy` and `ArraySlice.span`). Because `PolyEqual` lowers array `=` to `MLton_eq` *before* `ShallowFlatten`, SoA currently leaves `MLton_eq` comparing ephemeral wrapper tuples that `Flatten` can re-box. Note that AoS avoids this entirely, and SoA can fix array `=` soundly in a few lines by rewriting `MLton_eq` on a flattened array to compare component `0` (`MLton_eq(select(a, 0), select(b, 0))`). `Weak` on flattened arrays under SoA would still require opting out of SoA (or falling back to AoS/AoP) for arrays passed to `Weak_new`.
     3. **Unimplemented container primitives & AoS overflow:** Mention that the prototype crashes on `Array_copyArray`, `Array_copyVector`, `Vector_vector`, `Array_array`, and MPL's `Array_cas` (the first four are straightforward to add; `Array_cas` fundamentally requires opting out or wide CAS), and that AoS's `Array_alloc` needs an overflow-checked multiplication under 64-bit `Int` (`-default-type int64`).
   - Add the empirical finding: **an IR-level audit across all 34 `parallel-ml-bench` evaluation benchmarks (and all 89 compilable benchmarks in the repo, plus the MLton benchmark suite) confirms that zero benchmarks trigger any of these unsound cases.**

2. **Two small typos in the same section (`shallowflatten.tex`):**
   - Line 1128: `preserved by \texttt{PreFlatten}` $\to$ `preserved by \texttt{ShallowFlatten}`.
   - Line 1213: `Given that the value-to-ref rewrite is trivial and no examples of, this...` $\to$ incomplete sentence (e.g., `...and no examples of tuple pointer-equality appear in the evaluated benchmarks, this...`).

### If Hardening `shallow-flatten.fun` Later (Ranked by Value/Effort)

1. **Rewrite `MLton_eq` on SoA-flattened array types** to `MLton_eq(select(a, 0), select(b, 0))` (fixes pure SML array `=` and `ArraySlice.copy` corruption!).
2. **Add overflow check to AoS `Array_alloc`** (`n * tupleWidth`).
3. **Implement `Array_copyArray`, `Array_copyVector`, `Vector_vector`, `Array_array`** (eliminates compiler crashes on standard SML `Array.copy` and vector literals).
4. **Add a pre-pass escape/ban check** (type-level opt-out) disabling flattening for any container type used in `Array_cas` (AoS & SoA) or `Weak_new` (SoA), and optionally `MLton_size`/`MLton_share` (SoA).
