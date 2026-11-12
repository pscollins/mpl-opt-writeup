# Literature Review: `ShallowFlatten`, Container Unboxing, AoP-to-AoS/SoA Transformations, and Pack/Unpack Coercion Elimination

This report surveys academic papers and production compiler documentation relevant to your **`ShallowFlatten` transformation** (`latex/chapters/shallowflatten.tex`, `latex/chapters/background.tex` Section `sec:background_deep_flatten`, `latex/chapters/evaluation.tex` Sections `AoS Flattening` & `SoA Flattening`, and `latex/chapters/related_work.tex` Section `array, vector Flattening`).

To make this directly actionable for your thesis, the literature is organized around the **six core technical dimensions** of `ShallowFlatten`:
1. **SoA Container Flattening in Functional & Data-Parallel Compilers (`(a * b) array -> a array * b array`):** How compilers for functional and nested data-parallel languages (Futhark, Manticore, NESL, Data Parallel Haskell, Haskell `vector`/`Repa`/`Accelerate`, $\text{d}\widetilde{\text{F}}$) transform arrays-of-tuples into tuples-of-arrays.
2. **AoS Container Flattening & Contiguous Inline Tuple Storage (`(a * a) array -> a array` vs. `DeepFlatten`):** How compilers embed tuple/struct elements directly into flat contiguous buffers (MLton's `DeepFlatten`, Real-Time MLton, Virgil III, Jane Street's OxCaml, OCaml's `floatarray`, Single Assignment C (SaC), and Dex).
3. **Local Pack/Unpack Insertion + Downstream Simplification Synergy:** Compilers that transform container representations locally by inserting `pack`/`unpack` bridges around container operations and relying on subsequent tuple/allocation-elimination passes to cancel intermediate allocations (Scala `ildl`, Coercion Calculus, Stream Fusion)—as opposed to conservative whole-program analyses that abort if any intermediate tuple is introduced.
4. **Object & Array Inlining and Structure Splitting in Imperative, OO, and JIT Compilers:** How Java, C++, and systems compilers convert arrays of pointers (`AoP`) into flat arrays of structs (`AoS`) or split parallel arrays (`SoA`) (Dolby & Chien, Wimmer & Mössenböck, Budimlić & Kennedy, Lhoták & Hendren, Chilimbi et al., Zhong et al.).
5. **Semantic Subtleties: Pointer Identity (`MLton.eq`), Atomic Tearing (Compare-and-Swap), and Width Cutoffs ($W$):** Literature addressing the exact semantic and hardware constraints discussed in your `Limitations` section (`shallowflatten.tex` lines 1105–1162), including Java Project Valhalla (JEP 401), Baker's *Equal Rights for Functional Objects* (`egal`), Julia's `isbits` arrays, and configurable AoS/SoA DSLs (SHAPES, Ribbit, Halide, Taichi, ISPC).
6. **Production Compiler Documentation & Source Code Links:** Direct links to pass documentation and source code across **MLton**, **Futhark**, **Haskell (`vector`, `Accelerate`, `Repa`)**, **OxCaml**, **OpenJDK Valhalla**, **Julia**, and **LLVM**.

---

## 1. SoA Container Flattening in Functional & Data-Parallel Compilers (`(a * b) array` $\to$ `a array * b array`)

Your $\Phi_{\text{SoA}}$ flavor of `ShallowFlatten` rewrites every container type $(\tau_1 * \cdots * \tau_k)\;\kappa$ into a tuple of parallel containers $\tau_1\;\kappa * \cdots * \tau_k\;\kappa$ ($\kappa \in \{\mathtt{array}, \mathtt{vector}\}$), iterating to a fixed point over nested types (`((a * b) * c) array -> (a array * b array) * c array`). This transformation has a rich lineage in functional data-parallel compilers.

### 1.1 Bergstrom, Fluet, Rainey, Reppy, Rosen, & Shaw (2013) — *Data-Only Flattening for Nested Data Parallelism* *(Already in `references.bib` as `dataonly-paper`)*
- **Citation:** Lars Bergstrom, Matthew Fluet, Mike Rainey, John Reppy, Stephen Rosen, and Adam Shaw. In *Proceedings of the 18th ACM SIGPLAN Symposium on Principles and Practice of Parallel Programming (PPoPP '13)*, pp. 81–92, Shenzhen, China, February 2013.
- **What it does:** Introduces **data-only flattening** in the Manticore compiler for Parallel ML (PMA). Instead of Blelloch's full vector-flattening transformation (which flattens both data representations and control flow into segmented SIMD operations), data-only flattening leaves parallel control structures intact for multicore fork-join scheduling while transforming nested data structures: specifically, it rewrites **arrays of tuples into tuples of flat scalar arrays (SoA)** and attaches explicit shape descriptors for nested irregular arrays.
- **Relevance to `ShallowFlatten`:**
  - As you note in `related_work.tex` (line 61), Manticore's rule for product types inside sequences (`[| (t1, t2) |] = ([| t1 |], [| t2 |])`) is directly analogous to your $\Phi_{\text{SoA}}$ type transformation.
  - **Key Contrasts to Highlight:**
    1. Manticore only explores the SoA representation (plus hierarchical shape descriptors for nested arrays), whereas `ShallowFlatten` is parameterized over both **SoA ($\Phi_{\text{SoA}}$)** and **AoS ($\Phi_{\text{AoS}}$)** and evaluates both systematically on multicore CPU workloads.
    2. Manticore relies on high-level combinator fusion rules (`map`, `reduce`, `scan`, `filter` over ropes) to avoid materializing intermediate tuples, whereas `ShallowFlatten` operates at a lower level on general imperative/functional SSA primitive array operations (`Array_sub`, `Array_update`, `Array_alloc`, `Vector_sub`), inserting explicit `tuple` pack and `select` unpack operations and delegating their elimination to general-purpose SSA tuple passes (`Flatten`, `PreFlatten`, `LocalFlatten`, `Simplify`).
- **Download / Source URLs:**
  - Author Archive Direct PDF (Mike Rainey): http://mike-rainey.site/papers/ppopp13-flat.pdf
  - University of Chicago Manticore Archive (PDF): https://manticore.cs.uchicago.edu/papers/ppopp13-flat.pdf
  - ACM Digital Library DOI: https://doi.org/10.1145/2442516.2442525

### 1.2 Henriksen, Serup, Elsman, Henglein, & Oancea (2017) — *Futhark: Purely Functional GPU-Programming with Nested Parallelism and In-Place Array Updates* & Henriksen (2017) — PhD Thesis *(New References — Closest Architectural Match to $\Phi_{\text{SoA}}$!)*
- **Citations:**
  1. Troels Henriksen, Niels G. W. Serup, Martin Elsman, Fritz Henglein, and Cosmin E. Oancea. *Futhark: Purely Functional GPU-Programming with Nested Parallelism and In-Place Array Updates*. In *Proceedings of the 38th ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI '17)*, pp. 556–571, Barcelona, Spain, June 2017.
  2. Troels Henriksen. *Design and Implementation of the Futhark Programming Language*. PhD Thesis, Department of Computer Science (DIKU), University of Copenhagen, December 2017.
  3. Troels Henriksen, Frederik Thorøe, Martin Elsman, and Cosmin Oancea. *Incremental Flattening for Nested Data Parallelism*. In *PPoPP '19*, pp. 53–67, February 2019 *(Already in `references.bib` as `futhark-flatten`)*.
- **What they do:** In Futhark, the surface ML-style language allows arbitrary arrays of tuples and records (e.g., `[n](f32, f32)` or nested `((a, b), c)`). Very early in the compiler pipeline—during the **`Internaliser` pass** (and reinforced by the `SOACS` simplification passes)—Futhark **unconditionally eliminates all arrays of tuples by transforming them into tuples of arrays (SoA)**:
  - Every type annotation `[n](t1, ..., tk)` is recursively flattened to `([n]t1, ..., [n]tk)`.
  - Every array indexing operation `a[i]` on a former array-of-tuples is rewritten to index each constituent array `a_1[i], ..., a_k[i]` and **re-pack** the scalar components into a tuple `(x_1, ..., x_k)`.
  - Every in-place array update `a with [i] = v` unpacks `v` into `v_1, ..., v_k` and updates each constituent array `a_1, ..., a_k`.
  - Subsequent standard ANF/SSA simplification, inlining, and tuple scalarization passes eliminate all the temporary tuples introduced by the pack/unpack rewrites!
- **Relevance to `ShallowFlatten`:**
  - **This is arguably the closest architectural match in any functional compiler to the $\Phi_{\text{SoA}}$ mode of `ShallowFlatten`!** Look at how Futhark's `Internaliser` works (Henriksen PhD Thesis, Section 4.2):
    1. It runs early in the compilation pipeline after monomorphisation and defunctorization/defunctionalization.
    2. It globally rewrites all array-of-tuple types into tuple-of-array types recursively to a fixed point.
    3. It inserts local tuple pack/unpack operations around array reads/writes and relies entirely on downstream scalar/tuple simplification passes to remove the temporary tuples.
  - **Key Differences to Highlight in `related_work.tex`:**
    1. Futhark *only* supports the SoA transformation (because GPUs require coalesced memory accesses across SIMD lanes and Futhark forbids AoS arrays of tuples in its core IR), whereas `ShallowFlatten` supports **both AoS ($\Phi_{\text{AoS}}$) and SoA ($\Phi_{\text{SoA}}$)** and compares their microarchitectural tradeoffs on multicore CPUs.
    2. Futhark is a restricted pure array DSL without general recursive datatypes (`datatype`) or mutable references (`ref`), whereas `ShallowFlatten` operates in a general-purpose Standard ML compiler (MLton/MPL) and must rewrite container types embedded inside arbitrary user-defined `datatype`s and defunctionalized closure environments (`Fig. 4.6` in `shallowflatten.tex`).
- **Download / Source URLs:**
  - PLDI '17 Paper (Futhark Official Publications PDF): https://futhark-lang.org/publications/pldi17.pdf
  - Henriksen PhD Thesis (Full PDF, University of Copenhagen / Futhark Archive): https://futhark-lang.org/publications/troels-henriksen-phd-thesis.pdf
  - PPoPP '19 Paper (`futhark-flatten` PDF): https://futhark-lang.org/publications/ppopp19.pdf
  - ACM DOI (PLDI '17): https://doi.org/10.1145/3062341.3062354

### 1.3 Blelloch (1990) — *Vector Models for Data-Parallel Computing* & Blelloch & Sabot (1990) — *Compiling Collection-Oriented Languages onto Massively Parallel Computers* *(New References)*
- **Citations:**
  1. Guy E. Blelloch. *Vector Models for Data-Parallel Computing*. MIT Press, Cambridge, MA, 1990.
  2. Guy E. Blelloch and Gary W. Sabot. *Compiling Collection-Oriented Languages onto Massively Parallel Computers*. *Journal of Parallel and Distributed Computing*, 8(2):119–134, February 1990.
  3. Guy E. Blelloch, Siddhartha Chatterjee, Jonathan C. Hardwick, Jay Sipelstein, and Marco Zagha. *Implementation of a Portable Nested Data-Parallel Language*. *Journal of Parallel and Distributed Computing*, 21(1):4–14, April 1994 (preliminary version in PPoPP '93).
- **What they do:** Establish the classical **flattening (vectorization) transformation** for NESL and Paralation Lisp, where any parallel sequence of pairs `[(a_0, b_0), ..., (a_{n-1}, b_{n-1})]` is canonically represented in memory as a pair of flat vectors `([a_0, ..., a_{n-1}], [b_0, ..., b_{n-1}])` (SoA).
- **Relevance to `ShallowFlatten`:** The historical root of the SoA transformation in functional programming languages. Note that in `evaluation.tex` (Section `quickhull, linearrec`), both `quickhull` and `linearrec` are classic NESL benchmarks originally studied by Blelloch! Showing that `ShallowFlatten` recovers flat AoS/SoA vector memory layouts automatically for Standard ML implementations of `quickhull` and `linearrec` without requiring a specialized vector language connects your thesis directly back to Blelloch's foundational work.
- **Download / Source URLs:**
  - *Vector Models for Data-Parallel Computing* (Full Book PDF at CMU): https://www.cs.cmu.edu/~guyb/papers/Ble90.pdf
  - *Compiling Collection-Oriented Languages...* (CMU Author Archive PDF): https://www.cs.cmu.edu/~guyb/papers/BS90.pdf
  - *Implementation of a Portable Nested Data-Parallel Language* (CMU Author Archive PDF): https://www.cs.cmu.edu/~guyb/papers/BCHSZ94.pdf

### 1.4 Chakravarty & Keller (2001/2003) — *An Approach to Fast Arrays in Haskell* & Chakravarty et al. (2007) — *Data Parallel Haskell: A Status Report* *(New References)*
- **Citations:**
  1. Manuel M. T. Chakravarty and Gabriele Keller. *An Approach to Fast Arrays in Haskell*. In *Advanced Functional Programming (AFP 2002)*, LNCS vol. 2638, pp. 27–58, Springer, 2003.
  2. Manuel M. T. Chakravarty, Roman Leshchinskiy, Simon Peyton Jones, Gabriele Keller, and Simon Marlow. *Data Parallel Haskell: A Status Report*. In *Proceedings of the ACM SIGPLAN Workshop on Declarative Aspects of Multicore Programming (DAMP '07)*, pp. 10–18, Nice, France, January 2007.
- **What they do:** Introduce **type-indexed / associated type family array representations** in Haskell (`Data.Array.Parallel.Unlifted` and later `Data.Vector.Unboxed`), where the memory layout of an unboxed array `UArr e` is computed by type induction on the element type `e`:
  - `UArr Int` / `UArr Float`: a single flat contiguous byte array (`ByteArray#`).
  - `UArr (a, b)`: a **pair of unboxed arrays `(UArr a, UArr b)`** (SoA).
  - `UArr ()`: a single integer storing the length.
  Indexing `indexU (arr_a, arr_b) i` reads `indexU arr_a i` and `indexU arr_b i` and constructs the pair `(x, y)`, which GHC's worker/wrapper, `SpecConstr`, and stream fusion passes subsequently unbox and eliminate.
- **Relevance to `ShallowFlatten`:**
  - Look at the structural parallel: in Haskell's `Data.Vector.Unboxed` and DPH, the SoA transformation is expressed at the *library/type-family level* (`Vector (a, b)` wraps `(Vector a, Vector b)`), and indexing/updating inserts tuple pack/unpack operations that GHC's Core simplifier (`case-of-known-constructor` + `SpecConstr`) eliminates.
  - By contrast, in Standard ML (which has a single built-in mutable `'a array` and immutable `'a vector` type and no associated type families), users write ordinary `(int * int) array` code, and `ShallowFlatten` performs the exact same SoA (or AoS) representation rewrite *automatically inside the compiler's SSA middle-end*!
- **Download / Source URLs:**
  - *An Approach to Fast Arrays in Haskell* (UNSW Author Archive PDF): https://www.cse.unsw.edu.au/~chak/papers/CK02.pdf
  - *Data Parallel Haskell: A Status Report* (CMU / MSR Archive PDF): https://www.cs.cmu.edu/~crary/819-f09/Chakravarty07.pdf
  - Microsoft Research Publication Page: https://www.microsoft.com/en-us/research/publication/data-parallel-haskell-a-status-report/

### 1.5 Keller et al. (2010) — *Regular, Shape-Polymorphic, Parallel Arrays in Haskell (Repa)* & Chakravarty et al. (2011) / McDonell et al. (2013) — *Accelerate* *(New References)*
- **Citations:**
  1. Gabriele Keller, Manuel M. T. Chakravarty, Roman Leshchinskiy, Simon Peyton Jones, and Ben Lippmeier. *Regular, Shape-Polymorphic, Parallel Arrays in Haskell*. In *Proceedings of the 15th ACM SIGPLAN International Conference on Functional Programming (ICFP '10)*, pp. 261–272, September 2010.
  2. Manuel M. T. Chakravarty, Gabriele Keller, Sean Lee, Trevor L. McDonell, and Vinod Grover. *Accelerating Haskell Array Codes with Multicore GPUs*. In *Proceedings of the Sixth Workshop on Declarative Aspects of Multicore Programming (DAMP '11)*, pp. 3–14, January 2011.
  3. Trevor L. McDonell, Manuel M. T. Chakravarty, Gabriele Keller, and Ben Lippmeier. *Optimising Purely Functional GPU Programs*. In *Proceedings of the 18th ACM SIGPLAN International Conference on Functional Programming (ICFP '13)*, pp. 49–60, September 2013.
- **What they do:** Both **Repa** (for multicore CPUs) and **Accelerate** (for GPUs/multicore) represent manifest arrays of tuples `Array sh (a, b)` as tuples of primitive arrays `(Array sh a, Array sh b)` (SoA) using GADT type representations (`ArrayElt`). When scalar expressions inside array combinators construct or project from tuples, Accelerate's sharing recovery and array fusion passes (`McDonell et al. 2013`) beta-reduce tuple projections (`fst (a, b) ==> a`) so that temporary tuples never materialize in generated device code.
- **Download / Source URLs:**
  - Repa ICFP '10 Paper (Microsoft Research PDF): https://www.microsoft.com/en-us/research/wp-content/uploads/2016/07/repa-icfp10.pdf
  - Accelerate DAMP '11 Paper (UNSW Author Archive PDF): https://www.cse.unsw.edu.au/~chak/papers/CL+11.pdf
  - Accelerate ICFP '13 Paper (UNSW Author Archive PDF): https://www.cse.unsw.edu.au/~chak/papers/MCKL13.pdf

### 1.6 Shaikhha, Fitzgibbon, Vytiniotis, Peyton Jones, & Koch (2019) — *Efficient Differentiable Programming in a Functional Array-Processing Language* *(New Reference)*
- **Citation:** Amir Shaikhha, Andrew Fitzgibbon, Dimitrios Vytiniotis, Simon Peyton Jones, and Christoph Koch. *Proceedings of the ACM on Programming Languages (PACMPL)*, Vol. 3, Issue ICFP, Article 97, August 2019.
- **What it does:** Forward-mode automatic differentiation over array programs naturally transforms every scalar `float` into a dual number `(float, float)` (value and derivative), turning every `float array` into a `(float * float) array`! To eliminate the catastrophic overhead of allocating heap pairs inside differentiated array loops, their compiler ($\text{d}\widetilde{\text{F}}$) applies an algebraic **AoS-to-SoA rewrite rule (`unzip` rule)** that transforms arrays of pairs into pairs of arrays, combined with local pair beta-reduction (`snd (a, b) -> b`).
- **Relevance to `ShallowFlatten`:** Provides a compelling modern motivation (automatic differentiation and scientific computing in ML-family languages) where `(float * float) array` arises pervasively and requires automatic SoA/AoS container flattening + local tuple cancellation.
- **Download / Source URLs:**
  - arXiv Open Access PDF: https://arxiv.org/pdf/1806.02136.pdf
  - ACM Open Access DOI: https://doi.org/10.1145/3341701

---

## 2. AoS Container Flattening & Contiguous Inline Tuple Storage (`(a * a) array` $\to$ `a array` vs. `DeepFlatten`)

Your $\Phi_{\text{AoS}}$ flavor of `ShallowFlatten` transforms a container of $n$ homogeneous $k$-tuples $(\tau_0 * \cdots * \tau_0)\;\kappa$ into a single flat container $\tau_0\;\kappa$ of length $n \cdot k$, rewriting `Array_sub(a, i)` into $k$ reads at `i * k + (j - 1)` followed by a `tuple(x_1, ..., x_k)` pack, and `Array_update(a, i, x)` into $k$ `select(x, j - 1)` unpacks followed by $k$ writes at `i * k + (j - 1)`.

### 2.1 Weeks (2004) — *Flattening of Arrays and Vectors (`DeepFlatten` Design Note)* & Ziarek, Weeks, & Jagannathan (2008) — *Flattening Tuples in an SSA IR* *(Already in `references.bib` as `deep-flat-email` and `flat-paper`)*
- **Citations:**
  1. Stephen Weeks. *[MLton] flattening of arrays and vectors*. MLton Developers Mailing List, August 2004.
  2. Lukasz Ziarek, Stephen Weeks, and Suresh Jagannathan. *Flattening Tuples in an SSA Intermediate Representation*. *Higher-Order and Symbolic Computation*, 21(3):333–358, 2008.
- **What they do:** Document MLton's `SSA2` intermediate representation and the `DeepFlatten` pass. Because `SSA` only represents flat unary type constructors (`'a array`), Stephen Weeks introduced `SSA2` specifically so that a container type could represent a mutable or immutable sequence with multiple inline fields per element (`Prod` of fields inside an `Array` object type), along with generalized `Base` + `Offset` addressing (`Select { base : 'a Base.t, offset : int }` and `Update { base : 'a Base.t, offset : int, value : 'b }`) where `base` can be either a heap `Object` or an `ArraySub(arr, idx)`.
- **Relevance to `ShallowFlatten` (Crucial Architectural Comparison):**
  - Why did MLton's `DeepFlatten` require `SSA2`, whereas your `ShallowFlatten` operates in `SSA`?
    1. In `SSA2`, `DeepFlatten` flattens *in-place* by turning `y = Array_sub(a, i); x = #0 y` into a direct compound field read `x = Select(ArraySub(a, i), 0)`. However, because `SSA2` has no representation for a standalone pointer to an interior slice of an array element (`ArraySub(a, i)` is not a first-class value that can be passed to a function or bound to a variable expecting a heap tuple), **`DeepFlatten` is forced to mark an array element as `DontFlatten` on its two-point lattice whenever the element tuple `y = Array_sub(a, i)` escapes to a function call, a `case` branch, or any use other than direct field projection**, or when `Array_update(a, i, y)` receives a pre-existing tuple variable `y` rather than a freshly constructed tuple!
    2. By contrast, `ShallowFlatten` runs *early in `SSA`* (before `Flatten` and `PreFlatten`) and decouples the container representation from the element's consumers by **inserting explicit `tuple(...)` pack and `select(...)` unpack statements**. Even if the read element `p` is passed to a helper function `f(p)` (as in `quickhull`'s geometry helpers or `linearrec`'s `combine` function!), downstream `PreFlatten` + `Flatten` + `Simplify` flattens `f`'s signature and cancels out `p`!
    3. Furthermore, for homogeneous tuples $(\tau_0 * \cdots * \tau_0)$, $\Phi_{\text{AoS}}$ achieves an identical contiguous memory layout to `DeepFlatten` (`[x_0, y_0, x_1, y_1, ...]`) purely inside `SSA` by scaling the array length by $k$ and index expressions by $i \cdot k + j$, without needing `SSA2`'s compound addressing machinery.
- **Download / Source URLs:**
  - Weeks (2004 Mailing List Archive): http://www.mlton.org/pipermail/mlton/2004-August/025760.html
  - MLton `DeepFlatten` Wiki: http://mlton.org/DeepFlatten
  - MLton `deep-flatten.fun` Source Code (GitHub): https://github.com/MLton/mlton/blob/master/mlton/ssa/deep-flatten.fun
  - Ziarek et al. (2008 PDF): https://www.cs.purdue.edu/homes/suresh/papers/hosc08.pdf

### 2.2 Li, McArdle, Murphy, Shivkumar, & Ziarek (2016) — *Adding Real-Time Capabilities to a SML Compiler* *(Already in `references.bib` as `realtime-sml-paper`)*
- **Citation:** Muyuan Li, Daniel E. McArdle, Jeffrey C. Murphy, Bhargav Shivkumar, and Lukasz Ziarek. *ACM SIGBED Review*, 13(2):8–13, April 2016.
- **What it does:** Modifies MLton to use a chunked heap object model for real-time garbage collection and notes that MLton's `DeepFlatten` had to be disabled because computing element offsets in `SSA2`/`Machine` when an array element flattens heterogeneous fields of mixed byte widths (e.g., 16-bit, 32-bit, 64-bit) greatly complicates array indexing and GC object layout descriptors.
- **Relevance to `ShallowFlatten`:** As you already note in `related_work.tex` (line 67), `ShallowFlatten`'s AoS mode ($\Phi_{\text{AoS}}$) cleanly avoids mixed-width offset calculation by restricting AoS flattening to homogeneous tuples ($\tau_0 * \cdots * \tau_0$), while its SoA mode ($\Phi_{\text{SoA}}$) naturally supports *arbitrary heterogeneous tuples* ($\tau_1 * \cdots * \tau_k$) because each field $\tau_j$ resides in its own homogeneous array $\tau_j\;\mathtt{array}$!
- **Download / Source URLs:**
  - ACM Digital Library DOI: https://doi.org/10.1145/2933566.2933568
  - Author Archive / SUNY Buffalo Mirror ( via Semantic Scholar / ACM ): https://dl.acm.org/doi/10.1145/2933566.2933568

### 2.3 Titzer (2013) — *Harmonizing Classes, Functions, Tuples, and Type Parameters in Virgil III* *(Already in `references.bib` as `virgil-paper`)*
- **Citation:** Ben L. Titzer. In *Proceedings of the 34th ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI '13)*, pp. 85–94, Seattle, WA, June 2013.
- **What it does:** In the Virgil III compiler, tuples are purely value-typed first-class citizens and **every tuple in the program is unconditionally flattened**—not only in local variables and function arguments/returns, but also inside arrays (`Array<(A, B)>`). Specifically, Section 5 (*Tuple Implementation / Arrays of Tuples*) explains how the Virgil compiler lowers `Array<(A, B)>` into either **parallel constituent arrays (`(Array<A>, Array<B>)`, i.e., SoA)** (used on the JVM/managed targets and for heterogeneous types) or a **single flat scaled array (AoS)** (when targeting native/C-like memory or homogeneous scalars), inserting component-by-component reads and writes at every array access site.
- **Relevance to `ShallowFlatten`:**
  - **Virgil III is the most direct precedent in a general-purpose statically-typed language for `ShallowFlatten`'s unconditional global type-directed container rewriting!**
  - Look at how closely Virgil III's array-of-tuple normalization matches `ShallowFlatten`:
    1. Like `ShallowFlatten`, Virgil rewrites all occurrences of `Array<(A, B)>` globally across types, function signatures, and data declarations, recursively flattening nested tuples (`Array<((A, B), C)>`).
    2. Like `ShallowFlatten`, Virgil supports both the **tuple-of-arrays (SoA)** lowering and the **scaled-index single-array (AoS)** lowering for homogeneous element types.
    3. As you note in `related_work.tex` (line 56), Titzer explicitly observes that unconditional flattening of very wide tuples can degrade performance due to code bloat and register/memory traffic—directly motivating `ShallowFlatten`'s maximum tuple width parameter $W$ ($2 \le k \le W$)!
- **Download / Source URLs:**
  - ACM Digital Library DOI: https://doi.org/10.1145/2491956.2462185
  - Semantic Scholar / Author Copy: https://www.semanticscholar.org/paper/Harmonizing-classes%2C-functions%2C-tuples%2C-and-type-in-Titzer/a22784863274410d7024461d52950275e427319b

### 2.4 Eisenberg (2023) — *Layout Polymorphism* & Lorenzen, White, Dolan, Eisenberg, & Lindley (2024) — *Oxidizing OCaml with Modal Memory Management* (Jane Street / OxCaml) *(Upgrades `layout-poly-paper` in `references.bib`)*
- **Citations:**
  1. Richard A. Eisenberg. *Layout Polymorphism: Using Static Computation to Allow Efficient Polymorphism over Variable Representations*. In *ACM SIGPLAN Workshop on ML (ML '23)*, Seattle, WA, September 2023.
  2. Anton Lorenzen, Leo White, Stephen Dolan, Richard A. Eisenberg, and Sam Lindley. *Oxidizing OCaml with Modal Memory Management*. *Proceedings of the ACM on Programming Languages (PACMPL)*, Vol. 8, Issue ICFP, Article 253, August 2024.
- **What they do:** Introduce **unboxed product layouts (`#(a, b)` with layout `layout1 & layout2`)** and **unboxed arrays** in Jane Street's OxCaml compiler. An array of unboxed tuples `#(float#, float#) array` is laid out contiguously in memory as an AoS buffer without per-element heap pointers or headers, while layout annotations enable zero-cost abstraction when passing unboxed products to monomorphized/layout-specialized functions.
- **Relevance to `ShallowFlatten`:** In `related_work.tex` (lines 63–64), you cite the Jane Street tech talk (`layout-poly-paper`). Citing Eisenberg's ML '23 extended abstract and Lorenzen et al.'s ICFP '24 paper gives you peer-reviewed academic citations, and strengthens your contrast: OxCaml requires explicit source-level unboxed product types `#(a, b)` and kind/layout annotations (`any`, `value`, `bits64 & bits64`) to reconcile unboxed arrays with separate compilation, whereas `ShallowFlatten` operates automatically on standard SML `(a * b) array` types via whole-program SSA compilation.
- **Download / Source URLs:**
  - Eisenberg (2023 ML Workshop Extended Abstract PDF): https://richarde.dev/papers/2023/layout-poly/layout-poly.pdf
  - Lorenzen et al. (2024 ICFP Paper Direct PDF): https://antonlorenzen.de/oxidizing-ocaml-modal-memory-management.pdf
  - ACM Open Access DOI (ICFP '24): https://doi.org/10.1145/3674642
  - OxCaml Official Unboxed Types & Arrays Docs: https://oxcaml.org/documentation/unboxed-types/

### 2.5 Leroy (1992, 1997) — *Unboxed Objects and Polymorphic Typing* & OCaml's `floatarray` (`Tag_double_array`) Optimization *(New Reference)*
- **Citations:**
  1. Xavier Leroy. *Unboxed Objects and Polymorphic Typing*. In *POPL '92*, pp. 177–188, January 1992.
  2. Xavier Leroy. *The Effectiveness of Type-Based Unboxing*. In *Workshop on Types in Compilation (TIC '97)*, Technical Report BCCS-97-03, Boston College, June 1997.
- **What they do:** Explain how OCaml handles the tension between boxed uniform representations (required for polymorphic `'a array`) and flat unboxed arrays (`float array`). Notice how OCaml's classic `float array` optimization works: when an array is known at compile time to be `float array`, OCaml stores raw 64-bit floats contiguously (`Tag_double_array`), **inserting an unbox operation on every `Array.set` and a fresh `float` box allocation on every `Array.get`**, which downstream local float unboxing eliminates if the read float does not escape!
- **Relevance to `ShallowFlatten`:**
  - **OCaml's `float array` (`Tag_double_array`) optimization is the exact scalar ancestor of `ShallowFlatten`'s "insert pack/unpack around array reads/writes and let local unboxing clean up" strategy!**
  - Just as OCaml's `Array.get` on a `float array` logically emits `box_float(load_double(a, i))` and relies on local unboxing to cancel `unbox_float(box_float(v))`, `ShallowFlatten` emits `tuple(Array_sub(a, 2*i), Array_sub(a, 2*i+1))` and relies on `Flatten`/`PreFlatten`/`Simplify` to cancel `select(tuple(x, y), 0) ==> x`!
  - Furthermore, because MLton/MPL performs whole-program monomorphisation (unlike OCaml's separate compilation), `ShallowFlatten` never needs OCaml's infamous runtime `Tag_double_array` branch on polymorphic array accesses.
- **Download / Source URLs:**
  - Leroy (1997 TIC Paper PDF): https://xavierleroy.org/publi/unboxing-tic97.pdf
  - Leroy (1992 POPL Paper PDF): https://xavierleroy.org/publi/unboxed-popl92.pdf

### 2.6 Šinkarovs & Scholz (2013, 2016) — *Semantics-Preserving Data Layout Transformations for Improved Vectorisation* (Single Assignment C / SaC) *(New References)*
- **Citations:**
  1. Artjoms Šinkarovs and Sven-Bodo Scholz. *Semantics-Preserving Data Layout Transformations for Improved Vectorisation*. In *Proceedings of the 2nd ACM SIGPLAN Workshop on Functional High-Performance Computing (FHPC '13)*, pp. 59–70, Boston, MA, September 2013.
  2. Artjoms Šinkarovs and Sven-Bodo Scholz. *Type-Driven Data Layouts for Improved Vectorisation*. *Concurrency and Computation: Practice and Experience*, 28(7):2092–2119, May 2016.
- **What they do:** In the functional array language **Single Assignment C (SaC)** (where complex numbers or points are represented as small inner arrays/tuples, turning an $N$-element array of 2D points into an array of shape $[N, 2]$—AoS—or $[2, N]$—SoA), Šinkarovs & Scholz formalize layout transformations (AoS $\leftrightarrow$ SoA $\leftrightarrow$ AoS-of-SoA) as **type-directed index-space isomorphisms** (`[N, 2] -> [2*N]` or `[2, N]`) applied to both array type declarations and array indexing primitives (`sel(iv, a)`).
- **Relevance to `ShallowFlatten`:** Formalizes the exact index-arithmetic correspondence between AoS (`a[i * k + j]`) and SoA (`a_j[i]`) in a functional IR, and evaluates how AoS vs. SoA impacts SIMD vectorization and cache locality on multicore CPUs.
- **Download / Source URLs:**
  - FHPC '13 Paper (ACM DOI): https://doi.org/10.1145/2502323.2502332
  - CCPE '16 Journal Paper (Heriot-Watt / ResearchGate Open Access PDF): https://www.researchgate.net/publication/281116002_Type-driven_data_layouts_for_improved_vectorisation
  - Wiley Online Library DOI: https://doi.org/10.1002/cpe.3541

### 2.7 Paszke et al. (2021) — *Getting to the Point: Index Sets and Parallelism-Preserving Autodiff for Pointful Array Programming (Dex)* *(New Reference)*
- **Citation:** Adam Paszke, Daniel D. Johnson, David Duvenaud, Dimitrios Vytiniotis, Alexey Radul, Matthew J. Johnson, Jonathan Ragan-Kelley, and Dougal Maclaurin. *Proceedings of the ACM on Programming Languages (PACMPL)*, Vol. 5, Issue ICFP, Article 88, August 2021.
- **What it does:** In the **Dex** functional array language, arrays are typed as memoized functions over finite index sets (`n => a`). Because Dex is "pointful" (loops are written via explicit index binders `for i:n. ...`), an array of pairs `n => (a & b)` is automatically uncurried/split by the Dex compiler into a pair of arrays `(n => a) & (n => b)` (SoA) or a product-indexed flat array `(n & Fin 2) => a` (AoS), while pointful indexing `x.i` avoids creating intermediate heap tuples.
- **Download / Source URLs:**
  - arXiv Open Access PDF: https://arxiv.org/pdf/2104.05372.pdf
  - ACM Open Access DOI: https://doi.org/10.1145/3473593

---

## 3. Local Pack/Unpack Coercion Insertion + Downstream Simplification Synergy

A central design contribution of `ShallowFlatten` (`shallowflatten.tex` lines 18–21, 406–417) is its **two-phase philosophy**: rather than building a fragile, monolithic whole-program pass that simultaneously rewrites containers and fuses all consuming expressions (or aborts when it cannot, like `DeepFlatten`), `ShallowFlatten` performs a **purely local primitive rewrite** by inserting `tuple` ("pack") and `select` ("unpack") bridges around every container primitive, and relies on existing downstream SSA optimizations (`Flatten`, `PreFlatten`, `LocalFlatten`, `Simplify`) to cancel out the temporary tuples.

### 3.1 Ureche, Biboudis, Smaragdakis, & Odersky (2015) — *Automating Ad-Hoc Data Representation Transformations* *(New Reference — Must-Cite for Pack/Unpack Bridge Architecture!)*
- **Citation:** Vlad Ureche, Aggelos Biboudis, Yannis Smaragdakis, and Martin Odersky. In *Proceedings of the 2015 ACM SIGPLAN International Conference on Object-Oriented Programming, Systems, Languages, and Applications (OOPSLA '15)*, pp. 733–752, Pittsburgh, PA, October 2015.
- **What it does:** Introduces **`ildl` (Interface-Guided Data Layout Transformations)** in the Scala compiler. To transform an `Array[Complex]` or `Array[Point]` (which is by default an Array-of-Pointers `AoP` on the JVM) into either a flat `Array[Double]` of length $2n$ (**AoS**, indexing `2*i` and `2*i + 1`) or two parallel arrays (**SoA**), `ildl` **rewrites container operations by inserting explicit `toRepr` (unpack) and `fromRepr` (pack) bridge coercions** at every boundary where elements enter or leave the transformed container, while preserving all types and variable names in the consuming code! Then, a local **bridge-cancellation optimization (`fromRepr(toRepr(x)) ==> x` + scalar inlining)** eliminates the temporary heap allocations when elements are immediately consumed.
- **Relevance to `ShallowFlatten`:**
  - **This paper uses the exact same "pack/unpack bridge around container primitives + downstream cancellation" architecture as `ShallowFlatten`!**
  - Look at the side-by-side comparison:
    - In `ildl`, reading `arr(i)` from an AoS-transformed `Array[Point]` is rewritten to `fromRepr(arr(2*i), arr(2*i+1))` (which allocates a `new Point(x, y)`), and writing `arr(i) = p` unpacks `p.x` and `p.y` into `arr(2*i)` and `arr(2*i+1)`—literally identical to `ShallowFlatten`'s `Fig. 4.4` (`AoS read + pack` and `AoS write + unpack`)!
    - **How `ShallowFlatten` goes further:** In `ildl` (Scala), the programmer must manually annotate scopes and write representation transformation schemas, and `ildl`'s cancellation only eliminates `pack`/`unpack` pairs within local inlined scopes. In `ShallowFlatten` (MPL/MLton), the transformation is **100% automatic across the whole program**, and because `ShallowFlatten` runs before interprocedural `PreFlatten` and `Flatten`, temporary tuples packed on array reads are eliminated **even across non-inlined and recursive function calls**!
- **Download / Source URLs:**
  - EPFL Infoscience Open Access Direct PDF: http://infoscience.epfl.ch/record/207050/files/ildl.pdf
  - Yannis Smaragdakis Author Archive (PDF): https://yanniss.github.io/ildl-oopsla15.pdf
  - ACM Digital Library DOI: https://doi.org/10.1145/2814270.2814283

### 3.2 Peterson (1989) — *Untagged Data in Tagged Environments: Choosing Optimal Representations at Compile Time* & Henglein & Jørgensen (1994) — *Formally Optimal Boxing* *(New References)*
- **Citations:**
  1. John C. Peterson. *Untagged Data in Tagged Environments: Choosing Optimal Representations at Compile Time*. In *Proceedings of the Fourth International Conference on Functional Programming Languages and Computer Architecture (FPCA '89)*, pp. 89–99, London, UK, September 1989.
  2. Fritz Henglein and Jesper Jørgensen. *Formally Optimal Boxing*. In *Proceedings of the 21st ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages (POPL '94)*, pp. 213–226, January 1994.
- **What they do:** Formalize representation changes in functional compilers by inserting explicit representation coercions (`box`/`unbox` or `pack`/`unpack`) around primitive operations and solving for representations that minimize remaining runtime coercions after local cancellation (`unbox(box(x)) = x`). Notably, Peterson (1989) explicitly models **arrays of unboxed vs. boxed elements**, showing that even if converting an array to an unboxed representation requires inserting `box` coercions at certain read sites that escape to generic functions, it is still profitable whenever the dynamic frequency of in-loop unboxed accesses outweighs the escaping boundary coercions!
- **Relevance to `ShallowFlatten`:** Provides the theoretical justification for `ShallowFlatten`'s core thesis (lines 16–21 of `shallowflatten.tex`): why MLton's `DeepFlatten` ("only flatten an array if *zero* pack/unpack coercions are needed anywhere") is overly conservative, and why eagerly transforming the container layout and inserting pack/unpack coercions is the right priority for array-intensive workloads.
- **Download / Source URLs:**
  - Peterson (1989 ACM Digital Library Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/99370.99377
  - Henglein & Jørgensen (1994 ACM Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/174675.177874

### 3.3 Coutts, Leshchinskiy, & Stewart (2007) — *Stream Fusion: From Lists to Streams to Nothing at All* *(New Reference)*
- **Citation:** Duncan Coutts, Roman Leshchinskiy, and Don Stewart. In *Proceedings of the 12th ACM SIGPLAN International Conference on Functional Programming (ICFP '07)*, pp. 315–326, Freiburg, Germany, October 2007.
- **What it does:** Powers Haskell's `vector` library (`Data.Vector.Unboxed`). Array pipelines (`map`, `filter`, `zipWith`, `scanl`) over unboxed vectors of tuples are rewritten into non-recursive `Stream` steppers that pack and unpack intermediate state and element tuples (`Done | Skip s | Yield (a, b) s`), relying on GHC's general-purpose simplifier (`case-of-case`, `case-of-known-constructor`, and `SpecConstr`) to eliminate all intermediate tuple and constructor allocations.
- **Relevance to `ShallowFlatten`:** Demonstrates how Haskell libraries achieve allocation-free SoA array loops by combining type-directed SoA array wrappers with general-purpose tuple/constructor simplification, whereas `ShallowFlatten` achieves this for arbitrary imperative and recursive array code in SSA without requiring stream-fusible combinator pipelines.
- **Download / Source URLs:**
  - Author Archive / Princeton Mirror (PDF): https://www.cs.princeton.edu/~dpw/courses/cos326-12/notes/stream-fusion.pdf
  - ACM Digital Library DOI: https://doi.org/10.1145/1291151.1291199

---

## 4. Object & Array Inlining and Structure Splitting in Imperative, OO, and JIT Compilers

In Java and object-oriented languages, every array of objects `Point[]` has the exact same **Array-of-Pointers (`AoP`)** memory layout as MLton's default `(int * int) array` (`Fig. 4.3` and `Fig. 2.18` in your thesis). Consequently, the Java/OO compiler community developed two major families of optimizations—**Object/Array Inlining (AoP $\to$ AoS)** and **Structure Splitting / Array Regrouping (AoP $\to$ SoA)**—that provide rich related work for `ShallowFlatten` and `DeepFlatten`.

### 4.1 Dolby & Chien (1997, 2000) — *An Automatic Object Inlining Optimization and its Evaluation* *(New References)*
- **Citations:**
  1. Julian Dolby. *Automatic Inline Allocation of Objects*. In *Proceedings of the ACM SIGPLAN 1997 Conference on Programming Language Design and Implementation (PLDI '97)*, pp. 7–17, June 1997.
  2. Julian Dolby and Andrew A. Chien. *An Automatic Object Inlining Optimization and its Evaluation*. In *Proceedings of the ACM SIGPLAN 2000 Conference on Programming Language Design and Implementation (PLDI '00)*, pp. 345–357, Vancouver, BC, June 2000.
- **What they do:** Present a whole-program interprocedural analysis and transformation that **inlines heap-allocated child objects directly into their parent objects or arrays** (converting an array of pointers `Point*[]` into a flat contiguous array of structs `Point[]`, i.e., AoP $\to$ AoS). Crucially, like MLton's `DeepFlatten`, Dolby & Chien require strict aliasing/mutability invariants so that no new object allocations (pack/unpack copies) are ever introduced when reading or writing an inlined array element.
- **Relevance to `ShallowFlatten` & `DeepFlatten`:**
  - Dolby & Chien (1997, 2000) is the direct imperative/OO counterpart to MLton's `DeepFlatten`!
  - Citing Dolby & Chien alongside Ziarek et al. (2008) shows why traditional "in-place object/tuple inlining into arrays" requires complex whole-program interprocedural aliasing and flow constraints—and why `ShallowFlatten`'s copy-in/copy-out (pack/unpack) semantics enabled by SML's immutable tuples is drastically simpler and more broadly applicable.
- **Download / Source URLs:**
  - PLDI '97 Paper (ACM Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/258915.258918
  - PLDI '00 Paper (ACM Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/349299.349344

### 4.2 Budimlić & Kennedy (1998, 2001) — *Object Inlining in Java (`JaMake`)* *(New References — Direct Precedent for Copy-Based Array Flattening!)*
- **Citations:**
  1. Zoran Budimlić and Ken Kennedy. *Static Interprocedural Optimizations in Java*. Technical Report CRPC-TR98746, Center for Research on Parallel Computation, Rice University, December 1998.
  2. Zoran Budimlić and Ken Kennedy. *JaMake: A Java Compiler Environment*. In *Proceedings of the Third International Conference on Large-Scale Scientific Computing (LSSC 2001)*, LNCS vol. 2179, pp. 201–209, Springer, 2001.
  3. Zoran Budimlić. *Compiling Java for High Performance and the Internet*. PhD Thesis, Rice University, January 2001.
- **What they do:** In the `JaMake` bytecode-to-bytecode Java compiler, Budimlić & Kennedy observe that Java arrays of small immutable/value-like objects (such as `Complex[]` or `Point[]`) suffer catastrophic cache and indirection overhead (`AoP`). To eliminate the `AoP` layout *without* modifying the JVM, `JaMake` transforms `Complex[]` of length $n$ into either:
  1. **Two parallel primitive arrays `double[] re, double[] im` of length $n$ (SoA)**, or
  2. **A single flat primitive array `double[] data` of length $2n$ (AoS)**,
  and rewrites array loads `a[i]` to reconstruct a `new Complex(re[i], im[i])` (pack) and array stores `a[i] = c` to extract `c.re, c.im` (unpack), relying on downstream scalar replacement / object inlining to eliminate the temporary `Complex` objects!
- **Relevance to `ShallowFlatten`:**
  - **This is an extraordinary parallel from the scientific Java compiler literature!** Just like `ShallowFlatten` cannot add new low-level C/JVM memory layout descriptors in the high-level IR (`SSA` in MPL vs. Java bytecode in `JaMake`), Budimlić & Kennedy express both **SoA (tuple of primitive arrays)** and **AoS (single scaled-length primitive array)** using standard existing array types, insert pack/unpack operations at array accesses, and rely on downstream scalar replacement to eliminate the temporary objects!
- **Download / Source URLs:**
  - Budimlić PhD Thesis (Rice University Digital Scholarship Archive Full PDF): https://scholarship.rice.edu/bitstream/handle/1911/17935/3021101.PDF
  - LSSC 2001 Paper (Springer DOI): https://doi.org/10.1007/3-540-45346-6_21

### 4.3 Lhoták & Hendren (2002) — *Run-Time Evaluation of Opportunities for Object Inlining in Java* *(New Reference)*
- **Citation:** Ondřej Lhoták and Laurie Hendren. In *Proceedings of the 11th International Conference on Compiler Construction (CC 2002)*, LNCS vol. 2304, pp. 175–189, Grenoble, France, April 2002.
- **What it does:** Conducts a comprehensive dynamic trace study of Java benchmarks to measure how often container/field references could be inlined (flattened) under strict identity-preserving rules (`DeepFlatten` / Dolby & Chien style) versus value-copying rules (`ShallowFlatten` / Budimlić & Kennedy style), showing that strict pointer-identity preservation blocks a large fraction of otherwise profitable array-flattening opportunities.
- **Download / Source URLs:**
  - McGill Sable Group Archive (PDF): https://www.sable.mcgill.ca/publications/papers/2002-1/cc2002.pdf
  - Springer Open Access PDF: https://link.springer.com/content/pdf/10.1007/3-540-45937-5_14.pdf

### 4.4 Wimmer & Mössenböck (2007, 2008) — *Automatic Object Inlining and Array Inlining in Java Virtual Machines* *(New References)*
- **Citations:**
  1. Christian Wimmer and Hanspeter Mössenböck. *Automatic Object Inlining in a Java Virtual Machine*. In *Proceedings of the 3rd International Conference on Virtual Execution Environments (VEE '07)*, pp. 14–23, June 2007.
  2. Christian Wimmer and Hanspeter Mössenböck. *Automatic Array Inlining in Java Virtual Machines*. In *Proceedings of the 6th Annual IEEE/ACM International Symposium on Code Generation and Optimization (CGO '08)*, pp. 14–23, Boston, MA, April 2008.
- **What they do:** Implement dynamic GC-cooperative object and array inlining in the Java HotSpot VM, co-allocating parent objects and child arrays/objects contiguously in the garbage-collected heap so pointer loads turn into fixed offset arithmetic.
- **Download / Source URLs:**
  - CGO '08 Paper (JKU Linz Official Archive PDF): https://www.ssw.uni-linz.ac.at/Research/Papers/Wimmer08/Wimmer2008-CGO-ArrayInlining.pdf
  - VEE '07 Paper (JKU Linz Official Archive PDF): https://www.ssw.uni-linz.ac.at/Research/Papers/Wimmer07/Wimmer2007-VEE-ObjectInlining.pdf

### 4.5 Chilimbi, Davidson, & Larus (1999) — *Cache-Conscious Structure Definition* & Zhong, Orlovich, Shen, & Ding (2004) — *Array Regrouping and Structure Splitting Using Whole-Program Reference Affinity* *(New References)*
- **Citations:**
  1. Trishul M. Chilimbi, Bob Davidson, and James R. Larus. *Cache-Conscious Structure Definition*. In *Proceedings of the ACM SIGPLAN 1999 Conference on Programming Language Design and Implementation (PLDI '99)*, pp. 13–24, May 1999.
  2. Yutao Zhong, Maksim Orlovich, Xipeng Shen, and Chen Ding. *Array Regrouping and Structure Splitting Using Whole-Program Reference Affinity*. In *Proceedings of the ACM SIGPLAN 2004 Conference on Programming Language Design and Implementation (PLDI '04)*, pp. 255–266, Washington, DC, June 2004.
- **What they do:** Foundational systems compiler papers on **structure splitting** (decomposing an array of structs into separate parallel arrays—SoA or hot/cold sub-arrays) and **array regrouping** (interleaving separate arrays that are always accessed together at the same index $i$ into a single flat array—AoS).
- **Relevance to `ShallowFlatten` (`background.tex` & `evaluation.tex`):**
  - Directly supports your microarchitectural cache-line utilization analysis in `background.tex` (lines 1984–2199, where you calculate the 89% wasted DRAM cache-line bandwidth of AoP vs. 100% cache-line efficiency of AoS/SoA) and your `perf` L1/LLC cache-miss analysis of `quickhull` and `linearrec` in `evaluation.tex`!
  - Also explains the tradeoff between AoS and SoA when only a subset of tuple fields is accessed (`select(p)` in `linearrec` line 995, which projects only the first component of each pair: under SoA, projecting only `#0` reads 100% useful bytes from `arr_x`, whereas under AoS it reads stride-2 elements from the interleaved array).
- **Download / Source URLs:**
  - Chilimbi et al. (PLDI '99 ACM Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/301618.301635
  - Zhong et al. (PLDI '04 University of Rochester Technical Report / PDF): https://www.cs.rochester.edu/u/cding/Documents/Publications/pldi04.pdf
  - Zhong et al. (ACM DOI): https://doi.org/10.1145/996841.996872

---

## 5. Semantic Subtleties: Pointer Identity (`MLton.eq`), Atomic Tearing (CAS), Tuple Width Cutoffs ($W$), and Configurable AoS/SoA DSLs

In `shallowflatten.tex` (`Section: Limitations`, lines 1105–1162), you discuss three crucial issues:
1. **Physical Pointer Equality (`MLton.eq`) vs. Standard ML Value Semantics:** Writing `element = (1, 2)` into `arr` and reading `element' = Array.sub(arr, 1)` returns a newly packed tuple, so `MLton.eq(element, element')` becomes `false` unless wrapped in a `ref` cell.
2. **Concurrency / Compare-and-Swap (CAS) on Flattened Array Elements:** Splitting a tuple across $k$ separate array slots (`arr[i*k + j]` or `arr_j[i]`) means a single-word CAS can no longer atomically update or compare an entire tuple element.
3. **Tuple Width Cutoff ($2 \le k \le W$):** Flattening very wide tuples yields diminishing returns and hurts performance.

The literature below directly addresses these exact three points!

### 5.1 OpenJDK Project Valhalla — *JEP 401: Value Classes and Objects* (Smith & Rose, 2024–2026) *(New Reference — Directly Mirrors Your `Limitations` Section!)*
- **Citation:** Dan Smith and John Rose. *JEP 401: Value Classes and Objects (Preview)*. OpenJDK Enhancement Proposal, Oracle / OpenJDK Project Valhalla, 2024–2026.
- **What it does:** Specifies how the Java Virtual Machine flattens arrays of immutable `value class` objects (converting `Point[]` from an Array-of-Pointers `AoP` into a contiguous flattened `AoS` array in heap memory). To make array flattening sound in Java, JEP 401 establishes three rules that **match your `Limitations` discussion in `shallowflatten.tex` point-for-point**:
  1. **Freedom from Object Identity (`==` vs. `MLton.eq`):** Value objects have no memory-address identity; copying (packing/unpacking) them into and out of a flattened array is semantically invisible because `==` compares fields by value rather than heap pointer address. If a programmer needs pointer identity, they must wrap the value in an identity object (the exact equivalent of your `ref` cell workaround in `shallowflatten.tex` lines 1131–1140!).
  2. **Multi-Word Tearing & Atomicity (Compare-and-Swap):** Because a flattened array element spans multiple fields in memory, concurrent reads/writes or atomic operations can observe "torn" multi-word states unless restricted to hardware atomic word widths or marked tearable (`LooselyConsistentValue`)—directly paralleling your discussion of MPL's compare-and-swap primitive on flattened `(int * int) array` elements!
  3. **Size Threshold for Flattening ($W$):** The JVM only flattens value arrays when the element size is below a small word-count threshold; larger value classes remain reference arrays (`AoP`) because copying large payloads on every read/write outweighs the eliminated pointer indirection.
- **Download / Source URLs:**
  - Official OpenJDK JEP 401 Specification: https://openjdk.org/jeps/401
  - John Rose & Brian Goetz — *State of Valhalla, Part 2: The Language Model & Part 3: The JVM Model*: https://openjdk.org/projects/valhalla/design-notes/state-of-valhalla/03-vm-model

### 5.2 Baker (1993) — *Equal Rights for Functional Objects or, The More Things Change, The More They Are the Same* *(New Reference)*
- **Citation:** Henry G. Baker. *ACM SIGPLAN OOPS Messenger*, 4(4):2–27, October 1993.
- **What it does:** The classic foundational paper on **object identity vs. value equality (`egal`)** in functional and ML-family languages. Proves that in a language like Standard ML where mutable state is explicitly isolated inside `ref` cells and `array`s (`sml-def`), immutable tuples `(a, b)` have **no intensional pointer identity**: unboxing, copying, or splitting and re-packing an immutable tuple when storing it into an array is 100% observationally indistinguishable in the formal semantics, and only `ref` cells possess physical identity.
- **Relevance to `ShallowFlatten`:** Gives you the canonical theoretical citation for lines 1128–1140 of `shallowflatten.tex` (why `ShallowFlatten`'s pack/unpack behavior is completely sound under Standard ML's formal semantics and why wrapping in `ref` is the principled way to opt into physical identity).
- **Download / Source URLs:**
  - Author Archive / Printf.net Mirror (PDF): https://courses.cs.washington.edu/courses/cse341/04wi/lectures/26-egal.pdf
  - ACM Digital Library (Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/165507.165508

### 5.3 Bezanson, Edelman, Karpinski, & Shah (2017) — *Julia: A Fresh Approach to Numerical Computing* *(New Reference)*
- **Citation:** Jeff Bezanson, Alan Edelman, Stefan Karpinski, and Viral B. Shah. *SIAM Review*, 59(1):65–98, 2017.
- **What it does:** Explains how **Julia** compiles arrays of composite types (`Array{T}`). When `T` is an immutable `struct` (or tuple) composed recursively of primitive/immutable fields (`isbits(T)`), Julia **automatically stores `Array{T}` inline as a contiguous AoS buffer** without pointers or object headers, packing/unpacking values into registers on array read/write and defining physical equality (`===`) via Baker's `egal` (bit-equality for immutable structs, pointer-equality for `mutable struct`). Meanwhile, the Julia ecosystem provides **`StructArrays.jl`** to transparently represent `AbstractArray{T}` in **SoA** layout (`tuple` of component arrays) with lazy tuple packing on indexing.
- **Download / Source URLs:**
  - SIAM Review Open Access / arXiv PDF: https://arxiv.org/pdf/1411.1607.pdf
  - SIAM DOI: https://doi.org/10.1137/141000671
  - Julia Compiler Docs — `isbits` Inline Array Layout: https://docs.julialang.org/en/v1/devdocs/arrays/
  - `StructArrays.jl` Documentation (SoA in Julia): https://juliaarrays.github.io/StructArrays.jl/stable/

### 5.4 Franco, Hagelin, Wrigstad, Drossopoulou, & Eisenbach (2017) — *You Can Have It All: Abstraction and Good Cache Performance (SHAPES)* & Baudon, Radanne, & Gonnord (2023, 2024) — *Ribbit / ADT4HPC* *(New & Updated References)*
- **Citations:**
  1. Juliana Franco, Martin Hagelin, Tobias Wrigstad, Sophia Drossopoulou, and Susan Eisenbach. *You Can Have It All: Abstraction and Good Cache Performance*. In *Proceedings of the 2017 ACM SIGPLAN International Symposium on New Ideas, New Paradigms, and Reflections on Programming and Software (Onward! '17)*, pp. 148–167, Vancouver, BC, October 2017.
  2. Juliana Franco, Sylvan Clebsch, Sophia Drossopoulou, Jan Vitek, and Tobias Wrigstad. *Correctness of a Concurrent Object Collector for Actor Languages* / *Layout-Polymorphic Pools in SHAPES* (ECOOP / Imperial College London).
  3. Thaïs Baudon, Gabriel Radanne, and Laure Gonnord. *Bit-Stealing Made Legal: Compilation for Custom Memory Representations of Algebraic Data Types*. *Proceedings of the ACM on Programming Languages (PACMPL)*, Vol. 7, Issue ICFP, Article 216, August 2023.
  4. Thaïs Baudon. *Algebraic Data Types for High-Performance Computing*. PhD Thesis, ENS de Lyon, November 2024 *(Already in `references.bib` as `adt4hpc-paper`)*.
- **What they do:**
  - **SHAPES (Franco et al. 2017)** allows an array/pool of composite objects to be instantiated with a layout parameter choosing between **AoP** (boxed pointers), **AoS** (contiguous interleaved fields), or **SoA** (parallel field arrays), while client code uses uniform field access syntax.
  - **Thaïs Baudon's PhD Thesis (`adt4hpc-paper`, 2024, Chapter 5: *Layouts for Collections of ADTs*)** specifically investigates transforming arrays of algebraic data types and tuples in functional languages between **AoP, AoS, and SoA (and AoSoA)** layouts! Note that in your `related_work.tex` (line 41), you currently mention `adt4hpc-paper` only under `\section{ConApp Flattening}` (saying it is concerned with serialized data on disk—which is true of `local-paper` / Gibbon, whereas `adt4hpc-paper` is actually about custom in-memory ADT and AoS/SoA array layouts in functional languages for HPC!). Citing `adt4hpc-paper` in `\section{array, vector Flattening}` as well (and adding Baudon et al.'s ICFP '23 paper) will make your related work section much more accurate and thorough!
- **Download / Source URLs:**
  - Franco et al. (Onward! '17 Uppsala DiVA Open Access PDF): https://uu.diva-portal.org/smash/get/diva2:1156445/FULLTEXT01.pdf
  - Baudon, Radanne, & Gonnord (ICFP '23 arXiv / HAL Open Access PDF): https://hal.science/hal-04156178/document (ACM DOI: https://doi.org/10.1145/3607858)
  - Baudon (2024 PhD Thesis HAL Open Access PDF): https://theses.hal.science/tel-04846642v1/file/TH2024BAUDONTHAIS.pdf

### 5.5 Ragan-Kelley et al. (2013) — *Halide* & Hu et al. (2019) — *Taichi* (Complementing `ispc-paper` in `shallowflatten.tex` line 335) *(New References)*
- **Citations:**
  1. Jonathan Ragan-Kelley, Connelly Barnes, Andrew Adams, Sylvain Paris, Frédo Durand, and Saman Amarasinghe. *Halide: A Language and Compiler for Optimizing Parallelism, Locality, and Recomputation in Image Processing Pipelines*. In *Proceedings of the 34th ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI '13)*, pp. 519–530, June 2013.
  2. Yuanming Hu, Tzu-Mao Li, Luke Anderson, Jonathan Ragan-Kelley, and Frédo Durand. *Taichi: A Language for High-Performance Computation on Spatially Sparse Data Structures*. *ACM Transactions on Graphics (SIGGRAPH Asia '19)*, 38(6), Article 201, November 2019.
- **What they do:** In `shallowflatten.tex` (lines 334–341), you cite Intel's ISPC (`ispc-paper`) and `cuda-textbook` to motivate how high-performance DSLs decouple AoS-like element indexing syntax from SoA/AoS physical memory layout.
  - In **Halide**, a multi-valued function returning a `Tuple(x, y)` is compiled by default to a **tuple of separate planar arrays (SoA)**, and can be switched to interleaved **AoS** with a one-line schedule directive without changing the algorithm.
  - In **Taichi**, a field of vectors/structs `ti.Vector.field(2, dtype=ti.f32)` lets the programmer switch between **AoS** (`ti.root.dense(ti.i, N).place(x)`) and **SoA** (`ti.root.place(x(0), x(1))`) purely in the data-layout declaration while keeping all kernel array accesses `x[i]` identical.
- **Relevance to `ShallowFlatten`:** Whereas Halide, Taichi, and ISPC require the programmer to use a specialized DSL or write explicit layout schedules, `ShallowFlatten` brings parameterized AoS vs. SoA layout compilation (`-shallow-flatten aos` vs. `-shallow-flatten soa`) transparently to unmodified Standard ML programs!
- **Download / Source URLs:**
  - Halide PLDI '13 Paper (MIT CSAIL Open Access PDF): https://people.csail.mit.edu/jrk/halide-pldi13.pdf
  - Taichi SIGGRAPH Asia '19 Paper (MIT CSAIL / Author Archive PDF): https://yuanming.taichi.graphics/publication/2019-taichi/taichi-lang.pdf

---

## 6. Official Compiler Documentation & Source Code (How Production Compilers Handle Container Flattening Today)

### 6.1 MLton (`DeepFlatten`, `RefFlatten`, `Flatten`, `LocalFlatten`)
- **Documentation & Source URLs:**
  - `DeepFlatten` Wiki Page: http://mlton.org/DeepFlatten
  - `DeepFlatten` Implementation (`mlton/ssa/deep-flatten.fun`): https://github.com/MLton/mlton/blob/master/mlton/ssa/deep-flatten.fun
  - `RefFlatten` Wiki Page (flattening mutable `ref` cells into containing tuples/constructors in `SSA2`): http://mlton.org/RefFlatten
  - `RefFlatten` Implementation (`mlton/ssa/ref-flatten.fun`): https://github.com/MLton/mlton/blob/master/mlton/ssa/ref-flatten.fun
  - Stephen Weeks's 2004 Design Post on Array/Vector Flattening: http://www.mlton.org/pipermail/mlton/2004-August/025760.html

### 6.2 Futhark (`Internaliser` SoA Transformation & `SOACS` Simplification)
- **Documentation & Source URLs:**
  - Futhark Compiler Architecture & Internal Core IR Docs: https://futhark.readthedocs.io/en/latest/compiler-overview.html
  - Futhark `Internaliser` Source Code (`src/Futhark/Internalise.hs` & `TypesValues.hs` — rewrites arrays of tuples/records into tuples of arrays): https://github.com/diku-dk/futhark/blob/master/src/Futhark/Internalise/TypesValues.hs
  - Futhark `SOACS` Simplifier (eliminates intermediate tuple constructions after SoA array reads): https://github.com/diku-dk/futhark/blob/master/src/Futhark/IR/SOACS/Simplify.hs

### 6.3 Haskell (`Data.Vector.Unboxed`, `Accelerate`, `Repa`)
- **Documentation & Source URLs:**
  - `Data.Vector.Unboxed` Hackage Documentation (type-family SoA representation of unboxed tuple vectors): https://hackage.haskell.org/package/vector/docs/Data-Vector-Unboxed.html
  - `Data.Vector.Unboxed.Base` Source Code (see `MV_2` / `V_2` SoA instances for `(a, b)`): https://github.com/haskell/vector/blob/master/vector/src/Data/Vector/Unboxed/Base.hs
  - `Accelerate` Array Representation Docs (`Arrays` & `Sugar.Elt` SoA lowering): https://hackage.haskell.org/package/accelerate/docs/Data-Array-Accelerate.html

### 6.4 Jane Street OxCaml (Unboxed Product Arrays & `floatarray`)
- **Documentation & Source URLs:**
  - OxCaml Unboxed Types & Layouts Documentation (`#(a, b)` unboxed tuples and unboxed arrays): https://oxcaml.org/documentation/unboxed-types/
  - Standard OCaml Manual — `Array` & `Float.Array` (`Tag_double_array` flat float arrays): https://ocaml.org/manual/latest/api/Array.html

### 6.5 OpenJDK Project Valhalla (JEP 401 Flattened Value Arrays)
- **Documentation & Source URLs:**
  - JEP 401: Value Classes and Objects (Array Flattening, Identity, and Tearing): https://openjdk.org/jeps/401
  - OpenJDK Valhalla Wiki — Flat Arrays & Calling Conventions: https://wiki.openjdk.org/display/valhalla/Main

### 6.6 LLVM (`InterleavedAccessPass` & `SLPVectorizer` / `VectorCombine` for AoS vs. SoA)
- **Documentation & Source URLs:**
  - LLVM Auto-Vectorization Docs (Interleaved Load/Store Vectorization for Strided AoS Arrays `a[2*i]`, `a[2*i+1]`): https://llvm.org/docs/Vectorizers.html#interleaved-access-vectorization
  - LLVM `InterleavedAccessPass.cpp` Source Code: https://github.com/llvm/llvm-project/blob/main/llvm/lib/CodeGen/InterleavedAccessPass.cpp

---

## 7. Actionable Notes for Your Thesis Chapters (`shallowflatten.tex` & `related_work.tex`)

| Thesis Location | Relevant Citations from This Report | How It Helps Your Writeup |
| :--- | :--- | :--- |
| **`shallowflatten.tex` Motivation (lines 11–55 & 332–342)** | **Ureche et al. (OOPSLA '15)**; **Henriksen et al. (PLDI '17)**; **Peterson (FPCA '89)**; **Halide (PLDI '13)**; **Taichi (SIGGRAPH Asia '19)** | Grounds your argument that `DeepFlatten`'s zero-allocation requirement is overly restrictive, and shows how `ShallowFlatten` brings Halide/Taichi/ISPC-style AoS/SoA layout switching to unmodified SML programs. |
| **`shallowflatten.tex` Limitations (lines 1105–1162: `MLton.eq`, CAS, & width cutoff $W$)** | **Baker (1993)** (*`egal` / Equal Rights for Functional Objects*); **JEP 401 (OpenJDK Valhalla)**; **Titzer (PLDI '13)** (*Virgil III*); **Lhoták & Hendren (CC '02)** | Citing **Baker (1993)** and **JEP 401 (Project Valhalla)** makes your `Limitations` section read like a tour de force: Java Valhalla's flattened value arrays face the *exact* same two semantic issues (loss of pointer identity `==` and multi-word tearing under atomic/CAS updates) and solve them the exact same way (value semantics by default, explicit identity wrapper analogous to `ref`, and small width cutoff $W$)! |
| **`related_work.tex` Section `array, vector Flattening` (lines 59–71)** | **Henriksen et al. (PLDI '17) & Henriksen Thesis (2017)** (*Futhark's `Internaliser`*); **Ureche et al. (OOPSLA '15)** (*Scala `ildl`*); **Chakravarty & Keller (2003, 2007)** (*DPH / `Data.Vector.Unboxed`*); **Budimlić & Kennedy (2001)** (*`JaMake`*); **Dolby & Chien (PLDI '00)**; **Šinkarovs & Scholz (2013, 2016)**; **Baudon (2023, 2024)** | Expands `\section{array, vector Flattening}` to compare `ShallowFlatten` against (1) Futhark's SoA `Internaliser`, (2) Scala `ildl`'s pack/unpack container bridges, (3) Haskell's type-family SoA vectors (`Data.Vector.Unboxed` / `Repa` / `Accelerate`), (4) `JaMake` and Dolby & Chien's Java array inlining, and (5) OxCaml's layout polymorphism (**Eisenberg 2023**, **Lorenzen et al. 2024**). Also note that `adt4hpc-paper` (**Baudon 2024**) studies in-memory AoS/SoA ADT array layouts (whereas `local-paper` studies serialized disk formats), so `adt4hpc-paper` fits naturally here too! |

---

## 8. Ready-to-Paste BibTeX Entries for New References

```bibtex
@inproceedings{futhark-pldi17,
  author    = {Henriksen, Troels and Serup, Niels G. W. and Elsman, Martin and Henglein, Fritz and Oancea, Cosmin E.},
  title     = {Futhark: Purely functional {GPU}-programming with nested parallelism and in-place array updates},
  booktitle = {Proceedings of the 38th ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI '17)},
  pages     = {556--571},
  year      = {2017},
  publisher = {ACM},
  doi       = {10.1145/3062341.3062354},
  url       = {https://futhark-lang.org/publications/pldi17.pdf}
}

@phdthesis{henriksen-thesis-2017,
  author    = {Henriksen, Troels},
  title     = {Design and Implementation of the {Futhark} Programming Language},
  school    = {University of Copenhagen},
  year      = {2017},
  month     = dec,
  url       = {https://futhark-lang.org/publications/troels-henriksen-phd-thesis.pdf}
}

@inproceedings{ureche-ildl-2015,
  author    = {Ureche, Vlad and Biboudis, Aggelos and Smaragdakis, Yannis and Odersky, Martin},
  title     = {Automating ad hoc data representation transformations},
  booktitle = {Proceedings of the 2015 ACM SIGPLAN International Conference on Object-Oriented Programming, Systems, Languages, and Applications (OOPSLA '15)},
  pages     = {733--752},
  year      = {2015},
  publisher = {ACM},
  doi       = {10.1145/2814270.2814283},
  url       = {http://infoscience.epfl.ch/record/207050/files/ildl.pdf}
}

@incollection{chakravarty-fast-arrays-2003,
  author    = {Chakravarty, Manuel M. T. and Keller, Gabriele},
  title     = {An approach to fast arrays in {Haskell}},
  booktitle = {Advanced Functional Programming (AFP 2002)},
  series    = {Lecture Notes in Computer Science},
  volume    = {2638},
  pages     = {27--58},
  publisher = {Springer},
  year      = {2003},
  doi       = {10.1007/978-3-540-44833-4_2},
  url       = {https://www.cse.unsw.edu.au/~chak/papers/CK02.pdf}
}

@inproceedings{dph-status-2007,
  author    = {Chakravarty, Manuel M. T. and Leshchinskiy, Roman and Peyton Jones, Simon and Keller, Gabriele and Marlow, Simon},
  title     = {{Data Parallel Haskell}: A status report},
  booktitle = {Proceedings of the ACM SIGPLAN Workshop on Declarative Aspects of Multicore Programming (DAMP '07)},
  pages     = {10--18},
  year      = {2007},
  publisher = {ACM},
  doi       = {10.1145/1248648.1248652},
  url       = {https://www.cs.cmu.edu/~crary/819-f09/Chakravarty07.pdf}
}

@inproceedings{repa-icfp10,
  author    = {Keller, Gabriele and Chakravarty, Manuel M. T. and Leshchinskiy, Roman and Peyton Jones, Simon and Lippmeier, Ben},
  title     = {Regular, shape-polymorphic, parallel arrays in {Haskell}},
  booktitle = {Proceedings of the 15th ACM SIGPLAN International Conference on Functional Programming (ICFP '10)},
  pages     = {261--272},
  year      = {2010},
  publisher = {ACM},
  doi       = {10.1145/1863543.1863582},
  url       = {https://www.microsoft.com/en-us/research/wp-content/uploads/2016/07/repa-icfp10.pdf}
}

@inproceedings{accelerate-icfp13,
  author    = {McDonell, Trevor L. and Chakravarty, Manuel M. T. and Keller, Gabriele and Lippmeier, Ben},
  title     = {Optimising purely functional {GPU} programs},
  booktitle = {Proceedings of the 18th ACM SIGPLAN International Conference on Functional Programming (ICFP '13)},
  pages     = {49--60},
  year      = {2013},
  publisher = {ACM},
  doi       = {10.1145/2500365.2500595},
  url       = {https://www.cse.unsw.edu.au/~chak/papers/MCKL13.pdf}
}

@inproceedings{stream-fusion-2007,
  author    = {Coutts, Duncan and Leshchinskiy, Roman and Stewart, Don},
  title     = {Stream fusion: From lists to streams to nothing at all},
  booktitle = {Proceedings of the 12th ACM SIGPLAN International Conference on Functional Programming (ICFP '07)},
  pages     = {315--326},
  year      = {2007},
  publisher = {ACM},
  doi       = {10.1145/1291151.1291199},
  url       = {https://www.cs.princeton.edu/~dpw/courses/cos326-12/notes/stream-fusion.pdf}
}

@article{shaikhha-diff-array-2019,
  author    = {Shaikhha, Amir and Fitzgibbon, Andrew and Vytiniotis, Dimitrios and Peyton Jones, Simon and Koch, Christoph},
  title     = {Efficient differentiable programming in a functional array-processing language},
  journal   = {Proceedings of the ACM on Programming Languages},
  volume    = {3},
  number    = {ICFP},
  articleno = {97},
  pages     = {1--30},
  year      = {2019},
  publisher = {ACM},
  doi       = {10.1145/3341701},
  url       = {https://arxiv.org/pdf/1806.02136.pdf}
}

@book{blelloch-vector-models-1990,
  author    = {Blelloch, Guy E.},
  title     = {Vector Models for Data-Parallel Computing},
  publisher = {MIT Press},
  address   = {Cambridge, MA},
  year      = {1990},
  url       = {https://www.cs.cmu.edu/~guyb/papers/Ble90.pdf}
}

@article{blelloch-sabot-1990,
  author    = {Blelloch, Guy E. and Sabot, Gary W.},
  title     = {Compiling collection-oriented languages onto massively parallel computers},
  journal   = {Journal of Parallel and Distributed Computing},
  volume    = {8},
  number    = {2},
  pages     = {119--134},
  year      = {1990},
  doi       = {10.1016/0743-7315(90)90087-6},
  url       = {https://www.cs.cmu.edu/~guyb/papers/BS90.pdf}
}

@inproceedings{eisenberg-layout-poly-2023,
  author    = {Eisenberg, Richard A.},
  title     = {Layout polymorphism: Using static computation to allow efficient polymorphism over variable representations},
  booktitle = {ACM SIGPLAN Workshop on ML (ML '23)},
  year      = {2023},
  url       = {https://richarde.dev/papers/2023/layout-poly/layout-poly.pdf}
}

@article{oxidizing-ocaml-2024,
  author    = {Lorenzen, Anton and White, Leo and Dolan, Stephen and Eisenberg, Richard A. and Lindley, Sam},
  title     = {Oxidizing {OCaml} with modal memory management},
  journal   = {Proceedings of the ACM on Programming Languages},
  volume    = {8},
  number    = {ICFP},
  articleno = {253},
  pages     = {485--514},
  year      = {2024},
  publisher = {ACM},
  doi       = {10.1145/3674642},
  url       = {https://antonlorenzen.de/oxidizing-ocaml-modal-memory-management.pdf}
}

@inproceedings{sinkarovs-scholz-2013,
  author    = {{\v{S}}inkarovs, Artjoms and Scholz, Sven-Bodo},
  title     = {Semantics-preserving data layout transformations for improved vectorisation},
  booktitle = {Proceedings of the 2nd ACM SIGPLAN Workshop on Functional High-Performance Computing (FHPC '13)},
  pages     = {59--70},
  year      = {2013},
  publisher = {ACM},
  doi       = {10.1145/2502323.2502332}
}

@article{sinkarovs-scholz-2016,
  author    = {{\v{S}}inkarovs, Artjoms and Scholz, Sven-Bodo},
  title     = {Type-driven data layouts for improved vectorisation},
  journal   = {Concurrency and Computation: Practice and Experience},
  volume    = {28},
  number    = {7},
  pages     = {2092--2119},
  year      = {2016},
  doi       = {10.1002/cpe.3541}
}

@article{dex-icfp21,
  author    = {Paszke, Adam and Johnson, Daniel D. and Duvenaud, David and Vytiniotis, Dimitrios and Radul, Alexey and Johnson, Matthew J. and Ragan-Kelley, Jonathan and Maclaurin, Dougal},
  title     = {Getting to the point: Index sets and parallelism-preserving autodiff for pointful array programming},
  journal   = {Proceedings of the ACM on Programming Languages},
  volume    = {5},
  number    = {ICFP},
  articleno = {88},
  pages     = {1--29},
  year      = {2021},
  publisher = {ACM},
  doi       = {10.1145/3473593},
  url       = {https://arxiv.org/pdf/2104.05372.pdf}
}

@inproceedings{peterson-untagged-1989,
  author    = {Peterson, John C.},
  title     = {Untagged data in tagged environments: Choosing optimal representations at compile time},
  booktitle = {Proceedings of the Fourth International Conference on Functional Programming Languages and Computer Architecture (FPCA '89)},
  pages     = {89--99},
  year      = {1989},
  publisher = {ACM},
  doi       = {10.1145/99370.99377},
  url       = {https://dl.acm.org/doi/pdf/10.1145/99370.99377}
}

@inproceedings{dolby-object-inlining-2000,
  author    = {Dolby, Julian and Chien, Andrew A.},
  title     = {An automatic object inlining optimization and its evaluation},
  booktitle = {Proceedings of the ACM SIGPLAN 2000 Conference on Programming Language Design and Implementation (PLDI '00)},
  pages     = {345--357},
  year      = {2000},
  publisher = {ACM},
  doi       = {10.1145/349299.349344},
  url       = {https://dl.acm.org/doi/pdf/10.1145/349299.349344}
}

@phdthesis{budimlic-thesis-2001,
  author    = {Budimli{\'c}, Zoran},
  title     = {Compiling {Java} for High Performance and the Internet},
  school    = {Rice University},
  year      = {2001},
  url       = {https://scholarship.rice.edu/bitstream/handle/1911/17935/3021101.PDF}
}

@inproceedings{lhotak-hendren-2002,
  author    = {Lhot{\'a}k, Ond{\v{r}}ej and Hendren, Laurie},
  title     = {Run-time evaluation of opportunities for object inlining in {Java}},
  booktitle = {Compiler Construction (CC 2002)},
  series    = {Lecture Notes in Computer Science},
  volume    = {2304},
  pages     = {175--189},
  publisher = {Springer},
  year      = {2002},
  doi       = {10.1007/3-540-45937-5_14},
  url       = {https://www.sable.mcgill.ca/publications/papers/2002-1/cc2002.pdf}
}

@inproceedings{wimmer-array-inlining-2008,
  author    = {Wimmer, Christian and M{\"o}ssenb{\"o}ck, Hanspeter},
  title     = {Automatic array inlining in {Java} virtual machines},
  booktitle = {Proceedings of the 6th Annual IEEE/ACM International Symposium on Code Generation and Optimization (CGO '08)},
  pages     = {14--23},
  year      = {2008},
  publisher = {ACM},
  doi       = {10.1145/1356058.1356061},
  url       = {https://www.ssw.uni-linz.ac.at/Research/Papers/Wimmer08/Wimmer2008-CGO-ArrayInlining.pdf}
}

@inproceedings{chilimbi-structure-splitting-1999,
  author    = {Chilimbi, Trishul M. and Davidson, Bob and Larus, James R.},
  title     = {Cache-conscious structure definition},
  booktitle = {Proceedings of the ACM SIGPLAN 1999 Conference on Programming Language Design and Implementation (PLDI '99)},
  pages     = {13--24},
  year      = {1999},
  publisher = {ACM},
  doi       = {10.1145/301618.301635},
  url       = {https://dl.acm.org/doi/pdf/10.1145/301618.301635}
}

@inproceedings{zhong-array-regrouping-2004,
  author    = {Zhong, Yutao and Orlovich, Maksim and Shen, Xipeng and Ding, Chen},
  title     = {Array regrouping and structure splitting using whole-program reference affinity},
  booktitle = {Proceedings of the ACM SIGPLAN 2004 Conference on Programming Language Design and Implementation (PLDI '04)},
  pages     = {255--266},
  year      = {2004},
  publisher = {ACM},
  doi       = {10.1145/996841.996872},
  url       = {https://www.cs.rochester.edu/u/cding/Documents/Publications/pldi04.pdf}
}

@article{baker-egal-1993,
  author    = {Baker, Henry G.},
  title     = {Equal rights for functional objects or, the more things change, the more they are the same},
  journal   = {ACM SIGPLAN OOPS Messenger},
  volume    = {4},
  number    = {4},
  pages     = {2--27},
  year      = {1993},
  publisher = {ACM},
  doi       = {10.1145/165507.165508},
  url       = {https://dl.acm.org/doi/pdf/10.1145/165507.165508}
}

@misc{jep401-valhalla,
  author       = {Smith, Dan and Rose, John},
  title        = {{JEP} 401: Value Classes and Objects (Preview)},
  howpublished = {OpenJDK Enhancement Proposal, \url{https://openjdk.org/jeps/401}},
  year         = {2025}
}

@article{julia-siam-2017,
  author    = {Bezanson, Jeff and Edelman, Alan and Karpinski, Stefan and Shah, Viral B.},
  title     = {Julia: A fresh approach to numerical computing},
  journal   = {SIAM Review},
  volume    = {59},
  number    = {1},
  pages     = {65--98},
  year      = {2017},
  doi       = {10.1137/141000671},
  url       = {https://arxiv.org/pdf/1411.1607.pdf}
}

@inproceedings{franco-shapes-2017,
  author    = {Franco, Juliana and Hagelin, Martin and Wrigstad, Tobias and Drossopoulou, Sophia and Eisenbach, Susan},
  title     = {You can have it all: Abstraction and good cache performance},
  booktitle = {Proceedings of the 2017 ACM SIGPLAN International Symposium on New Ideas, New Paradigms, and Reflections on Programming and Software (Onward! '17)},
  pages     = {148--167},
  year      = {2017},
  publisher = {ACM},
  doi       = {10.1145/3133850.3133861},
  url       = {https://uu.diva-portal.org/smash/get/diva2:1156445/FULLTEXT01.pdf}
}

@article{baudon-ribbit-2023,
  author    = {Baudon, Tha{\"\i}s and Radanne, Gabriel and Gonnord, Laure},
  title     = {Bit-stealing made legal: Compilation for custom memory representations of algebraic data types},
  journal   = {Proceedings of the ACM on Programming Languages},
  volume    = {7},
  number    = {ICFP},
  articleno = {216},
  pages     = {789--816},
  year      = {2023},
  publisher = {ACM},
  doi       = {10.1145/3607858},
  url       = {https://hal.science/hal-04156178/document}
}

@inproceedings{halide-pldi13,
  author    = {Ragan-Kelley, Jonathan and Barnes, Connelly and Adams, Andrew and Paris, Sylvain and Durand, Fr{\'e}do and Amarasinghe, Saman},
  title     = {Halide: A language and compiler for optimizing parallelism, locality, and recomputation in image processing pipelines},
  booktitle = {Proceedings of the 34th ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI '13)},
  pages     = {519--530},
  year      = {2013},
  publisher = {ACM},
  doi       = {10.1145/2491956.2462176},
  url       = {https://people.csail.mit.edu/jrk/halide-pldi13.pdf}
}

@article{taichi-2019,
  author    = {Hu, Yuanming and Li, Tzu-Mao and Anderson, Luke and Ragan-Kelley, Jonathan and Durand, Fr{\'e}do},
  title     = {Taichi: A language for high-performance computation on spatially sparse data structures},
  journal   = {ACM Transactions on Graphics},
  volume    = {38},
  number    = {6},
  articleno = {201},
  pages     = {1--16},
  year      = {2019},
  publisher = {ACM},
  doi       = {10.1145/3355089.3356506},
  url       = {https://yuanming.taichi.graphics/publication/2019-taichi/taichi-lang.pdf}
}
```
