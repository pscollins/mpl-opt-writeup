# Literature Review: Tuple Flattening, Unboxing, and Aggregate Layout Optimizations

This report surveys academic papers and compiler documentation covering **tuple flattening**, **arity raising**, **unboxing / representation analysis**, **call-pattern / constructor specialization**, **scalar replacement of aggregates (SROA)**, and **container layout transformations (AoS-to-SoA / deep flattening)**.

To make this directly useful for the thesis (`latex/chapters/related_work.tex` and `latex/references.bib`), entries are grouped by how they relate to your passes (`PreFlatten` for tuples and `ConApp`s, and `ShallowFlatten` / `DeepFlatten` for containers), with notes on which works are **new additions** versus **already cited in `references.bib`**, alongside **direct URLs to downloadable PDFs, author archives, DOIs, and compiler documentation**.

---

## 1. Tuple Flattening, Arity Raising, and Argument Promotion (First-Order & Higher-Order IRs)

These works directly address eliminating intermediate tuple allocations across function and basic-block boundaries by expanding tuple arguments/returns into multiple scalar parameters ("arity raising" / "tuple flattening").

### 1.1 Ziarek, Weeks, & Jagannathan (2008) — *Flattening Tuples in an SSA Intermediate Representation* *(Already in `references.bib` as `flat-paper`)*
- **Citation:** Lukasz Ziarek, Stephen Weeks, and Suresh Jagannathan. *Higher-Order and Symbolic Computation (HOSC)*, 21(3):333–358, September 2008.
- **What it does:** Formalizes MLton's SSA `Flatten` and `LocalFlatten` passes using an abstract coercion/flow framework over first-order SSA form after defunctionalization and monomorphisation. Uses a global unification/containment property to decide whether function/block formals and constructor args can be flattened without introducing excessive coercions (pack/unpack overhead).
- **Relevance to `PreFlatten`:** Your `tuple-PreFlatten` pass directly relaxes `Flatten`'s requirement that callers/callees unify to a single flat/non-flat representation by duplicating/specializing functions for mismatched call sites using a strictly local analysis.
- **Download / Source URLs:**
  - Purdue Author Archive (PDF): https://www.cs.purdue.edu/homes/suresh/papers/hosc08.pdf
  - Springer DOI: https://doi.org/10.1007/s10990-008-9030-x

### 1.2 Weeks (2006) — *Whole-Program Compilation in MLton* *(Already in `references.bib` as `mlton-proj`)*
- **Citation:** Stephen Weeks. In *Proceedings of the 2006 ACM SIGPLAN Workshop on ML (ML '06)*, p. 1, Portland, OR, September 2006.
- **What it does:** Architectural overview of MLton's whole-program compilation pipeline (monomorphisation, defunctionalization to first-order SSA, and SSA optimization passes including `Flatten`, `LocalFlatten`, `DeepFlatten`, and `RefFlatten`).
- **Download / Source URLs:**
  - MLton Official Archive (PDF): http://mlton.org/References.attachments/060916-mlton.pdf
  - Slides (PDF): http://mlton.org/References.attachments/060916-mlton-slides.pdf

### 1.3 Hannan & Hicks (1998) — *Higher-Order Arity Raising* *(New Reference)*
- **Citation:** John Hannan and Patrick Hicks. In *Proceedings of the Third ACM SIGPLAN International Conference on Functional Programming (ICFP '98)*, pp. 27–38, Baltimore, MD, September 1998.
- **What it does:** Formalizes **arity raising** (replacing a single tuple parameter with its $n$ constituent components) as a type-directed program transformation in a higher-order functional language, together with soundness proofs and conditions preventing useless tuple reconstruction.
- **Relevance to `PreFlatten`:** One of the earliest formal treatments specifically dedicated to tuple-argument flattening ("arity raising"). Contrasting Hannan & Hicks (higher-order type system) and Bergstrom & Reppy (`manticore-arity-paper`, higher-order CPS + 0CFA) with your first-order SSA `PreFlatten` highlights how MLton/MaPLe's defunctionalized SSA turns a complex higher-order flow problem into a local first-order specialization problem.
- **Download / Source URLs:**
  - ACM Digital Library (Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/289423.289426
  - DOI Landing Page: https://doi.org/10.1145/289423.289426

### 1.4 Bergstrom & Reppy (2010) — *Arity Raising in Manticore* *(Already in `references.bib` as `manticore-arity-paper`)*
- **Citation:** Lars Bergstrom and John Reppy. In *Implementation and Application of Functional Languages (IFL 2009)*, LNCS vol. 6041, pp. 90–106, Springer, 2010.
- **What it does:** Implements arity raising (flattening tuple arguments and unboxing raw values into registers) on Manticore's higher-order CPS intermediate representation (`BOM`), driven by control-flow analysis and a strict "never introduce extra pack/unpack operations on any path" profitability constraint.
- **Download / Source URLs:**
  - University of Chicago / Manticore Project Archive (PDF): https://manticore.cs.uchicago.edu/papers/ifl09-arity.pdf
  - Springer DOI: https://doi.org/10.1007/978-3-642-16478-1_6

### 1.5 Tarditi (1996) — *Design and Implementation of Code Optimizations for a Type-Directed Compiler for Standard ML* (PhD Dissertation) & *TIL: A Type-Directed Optimizing Compiler for ML* *(New References)*
- **Citation (Paper):** David Tarditi, Greg Morrisett, Perry Cheng, Chris Stone, Robert Harper, and Peter Lee. In *Proceedings of the ACM SIGPLAN 1996 Conference on Programming Language Design and Implementation (PLDI '96)*, pp. 181–192, May 1996.
- **Citation (PhD Thesis):** David Tarditi. *Design and Implementation of Code Optimizations for a Type-Directed Compiler for Standard ML*. Doctoral Dissertation, Technical Report CMU-CS-97-108, Carnegie Mellon University, December 1996.
- **What it does:** The TIL compiler for SML includes dedicated passes for **argument flattening** (flattening tuple arguments to functions when all call sites are known) and **loop-closing / register promotion of tuples** across recursive functions. Tarditi's dissertation (Chapter 6) gives a detailed mechanical breakdown of TIL's argument-flattening pass and when wrapper functions are generated for escaping functions.
- **Relevance to `PreFlatten`:** TIL's wrapper generation for escaping vs. known callers is a direct intellectual ancestor to function cloning/specialization for flattened vs. unflattened tuple callers.
- **Download / Source URLs:**
  - PLDI '96 Paper (Harvard DASH Open Access PDF): https://nrs.harvard.edu/urn-3:HUL.InstRepos:2797452
  - PLDI '96 Paper (ACM Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/231379.231414
  - PhD Dissertation `CMU-CS-97-108` (CMU Technical Reports Archive): http://reports-archive.adm.cs.cmu.edu/anon/1997/CMU-CS-97-108.pdf

---

## 2. Unboxing, Worker/Wrapper, and Constructor / Call-Pattern Specialization (GHC & Lazy/Strict Functional Compilers)

In GHC (Glasgow Haskell Compiler), tuple and constructor flattening across function boundaries is accomplished through the combination of **Unboxed Tuples**, the **Worker/Wrapper Transformation**, and **`SpecConstr` (Call-Pattern Specialization)**.

### 2.1 Peyton Jones & Launchbury (1991) — *Unboxed Values as First-Class Citizens in a Non-Strict Functional Language* *(New Reference)*
- **Citation:** Simon L. Peyton Jones and John Launchbury. In *Functional Programming Languages and Computer Architecture (FPCA '91)*, LNCS vol. 523, pp. 636–666, Springer, August 1991.
- **What it does:** Introduces first-class unboxed types and the **worker/wrapper transformation** in GHC. When strictness/demand analysis determines that a function evaluates a tuple or constructor argument, the function $f$ is split into an inlineable **wrapper** (which unpacks the tuple/constructor) and a **worker** $f_{\text{worker}}$ (which takes the flattened fields as separate arguments).
- **Relevance to `PreFlatten`:** Worker/wrapper is the canonical functional-compiler mechanism for decoupling a function's external calling convention from its flattened internal representation. When the wrapper is inlined at a call site where a tuple was just constructed (`let t = (a, b) in f t`), the tuple constructor and unpack cancel out via known-constructor simplification.
- **Download / Source URLs:**
  - Microsoft Research / Author Archive (PDF): https://www.microsoft.com/en-us/research/wp-content/uploads/1991/01/unboxed-values.pdf
  - Springer DOI: https://doi.org/10.1007/3540543961_30

### 2.2 Peyton Jones (2007) — *Call-Pattern Specialisation for Haskell Programs (`SpecConstr`)* *(New Reference — Crucial for `ConApp` and `tuple` `PreFlatten`!)*
- **Citation:** Simon Peyton Jones. In *Proceedings of the 12th ACM SIGPLAN International Conference on Functional Programming (ICFP '07)*, pp. 327–337, Freiburg, Germany, October 2007.
- **What it does:** Introduces GHC's `SpecConstr` pass. Whereas strictness-based worker/wrapper only flattens arguments that a function is *strict* in on *every* control-flow path, many functions (especially recursive loops) are only conditionally strict or receive specific constructor shapes (`Just x`, `(a, b)`, etc.) at specific recursive call sites. `SpecConstr` inspects call sites where arguments are explicit constructor applications (`ConApp`s or tuples), synthesizes a specialized clone of the function taking the flattened payload arguments directly, and rewrites matching call sites to invoke the specialized clone while keeping the original function for non-matching callers.
- **Relevance to `PreFlatten`:** **This is arguably the closest paper in the literature to your `PreFlatten` pass (both `tuple-PreFlatten` and `ConApp-PreFlatten`).** Like `PreFlatten`, `SpecConstr` duplicates/specializes functions based on constructor/tuple patterns observed at call sites so that intermediate heap allocations (`ConApp` / `tuple`) cancel out across calls, even when callers cannot all be unified to a single representation!
- **Download / Source URLs:**
  - Microsoft Research Publication Page & PDF: https://www.microsoft.com/en-us/research/publication/call-pattern-specialisation-for-haskell-programs/
  - Direct PDF Link: https://www.microsoft.com/en-us/research/wp-content/uploads/2016/07/specconstr.pdf
  - ACM DOI: https://doi.org/10.1145/1291151.1291200

### 2.3 Gill & Hutton (2009) — *The Worker/Wrapper Transformation* *(New Reference)*
- **Citation:** Andy Gill and Graham Hutton. *Journal of Functional Programming*, 19(2):227–251, March 2009.
- **What it does:** Generalizes Peyton Jones & Launchbury's worker/wrapper transformation into a formal equational reasoning framework for changing the data type representation of recursive functions via coerce/absorb pairs (`wrap` and `unwrap`).
- **Download / Source URLs:**
  - University of Nottingham Author Archive (PDF): https://www.cs.nott.ac.uk/~pszgmh/wrapper.pdf
  - Cambridge Core DOI: https://doi.org/10.1017/S0956796809007175

### 2.4 Bolingbroke & Peyton Jones (2009) — *Types Are Calling Conventions* *(New Reference)*
- **Citation:** Maximilian C. Bolingbroke and Simon L. Peyton Jones. In *Proceedings of the 2nd ACM SIGPLAN Symposium on Haskell (Haskell '09)*, pp. 73–84, Edinburgh, Scotland, September 2009.
- **What it does:** Expresses multi-argument arity, unboxed tuples, and worker/wrapper calling conventions directly in the types of an intermediate language (`Strict Core`), separating tuple values from multi-argument/multi-return calling conventions.
- **Download / Source URLs:**
  - University of Cambridge Author Archive (PDF): https://www.cl.cam.ac.uk/~mb566/papers/tacc-hs09.pdf
  - Microsoft Research Page: https://www.microsoft.com/en-us/research/publication/types-are-calling-conventions/

### 2.5 Downen, Ariola, Peyton Jones, & Eisenberg (2020) — *Kinds Are Calling Conventions* *(New Reference)*
- **Citation:** Paul Downen, Zena M. Ariola, Simon Peyton Jones, and Richard A. Eisenberg. *Proceedings of the ACM on Programming Languages (PACMPL)*, Vol. 4, Issue ICFP, Article 104, August 2020.
- **What it does:** Extends the type/kind system so that every type's kind describes its runtime calling convention and layout: boxed lifted pointers, unboxed scalars of various widths, and **unboxed tuples** (`TupleRep [r1, r2, ...]`) that pass/return multiple flattened values in registers without heap allocation.
- **Relevance to `related_work.tex`:** Directly connects GHC's unboxed tuples and worker/wrapper calling conventions with Jane Street's layout polymorphism work in OCaml (`layout-poly-paper`).
- **Download / Source URLs:**
  - Paul Downen Author Archive (PDF): http://pauldownen.com/publications/kacc.pdf
  - ACM Open Access DOI: https://doi.org/10.1145/3408986

---

## 3. Type-Directed Representation Analysis & Coercion-Based Unboxing (SML/NJ, FLINT, OCaml)

While MLton relies on whole-program monomorphisation to flatten tuples globally, separately compiled polymorphic languages (SML/NJ, OCaml) must reconcile unboxed/flattened tuple layouts with parametric polymorphism.

### 3.1 Leroy (1992) — *Unboxed Objects and Polymorphic Typing* *(New Reference)*
- **Citation:** Xavier Leroy. In *Proceedings of the 19th ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages (POPL '92)*, pp. 177–188, Albuquerque, NM, January 1992.
- **What it does:** The foundational paper on **coercion-based representation analysis**. Shows how a compiler can keep multi-word tuples and floats unboxed/flattened in monomorphic code and automatically insert `wrap`/`unwrap` coercions at boundaries with polymorphic code. Also powers the `Gallium` / `Caml Light` / `OCaml` approach to unboxed floats and multi-argument curried/tupled calls.
- **Download / Source URLs:**
  - Xavier Leroy's Official Archive (PDF): https://xavierleroy.org/publi/unboxed-popl92.pdf
  - ACM DOI: https://doi.org/10.1145/143165.143205

### 3.2 Henglein & Jørgensen (1994) — *Formally Optimal Boxing* *(New Reference)*
- **Citation:** Fritz Henglein and Jesper Jørgensen. In *Proceedings of the 21st ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages (POPL '94)*, pp. 213–226, Portland, OR, January 1994.
- **What it does:** Formulates Leroy's coercion insertion as a rewrite system over a coercion calculus and defines an optimality criterion (minimizing runtime box/unbox coercions along execution paths), proving that optimal placement of tuple/scalar boxing coercions can be computed via constraint solving.
- **Relevance to `PreFlatten`:** Their formal treatment of avoiding redundant box/unbox pairs (`unbox(box(x)) -> x`) parallels how MLton/MaPLe relies on downstream local simplification (`Shrink`) to cancel out `tuple` construction followed by `#i` projection once functions are specialized.
- **Download / Source URLs:**
  - ACM Digital Library (Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/174675.177874
  - DIKU Technical Report / DOI: https://doi.org/10.1145/174675.177874

### 3.3 Shao & Appel (1994) — *Space-Efficient Closure Representations* & (1995) — *A Type-Based Compiler for Standard ML* *(New References)*
- **Citations:**
  1. Zhong Shao and Andrew W. Appel. *Space-Efficient Closure Representations*. In *Proceedings of the 1994 ACM Conference on LISP and Functional Programming (LFP '94)*, pp. 150–161, June 1994.
  2. Zhong Shao and Andrew W. Appel. *A Type-Based Compiler for Standard ML*. In *Proceedings of the ACM SIGPLAN 1995 Conference on Programming Language Design and Implementation (PLDI '95)*, pp. 116–129, June 1995.
- **What they do:** Describe how SML/NJ's FLINT middle-end performs **argument flattening** (transforming an $n$-tuple parameter into $n$ separate register arguments when fits within hardware register limits), **safely-linked / flat closure representations**, and **minimal-typing derivation unboxing**.
- **Relevance to `related_work.tex`:** Note that in `related_work.tex` you already cite Reppy, Shivers, & Zhong (2026) (`closure-sharing-paper`), which builds directly on Shao & Appel (1994). Citing Shao & Appel (1994, 1995) directly grounds both your discussion of SML/NJ's CPS/FLINT lineage and how SML/NJ flattens tuple arguments up to register limits.
- **Download / Source URLs:**
  - *Space-Efficient Closure Representations* (Yale FLINT PDF): https://flint.cs.yale.edu/flint/publications/closure.pdf
  - *A Type-Based Compiler for Standard ML* (Yale FLINT PDF): https://flint.cs.yale.edu/flint/publications/sml-pldi95.pdf

### 3.4 Shao (1997) — *Flexible Representation Analysis* *(New Reference)*
- **Citation:** Zhong Shao. In *Proceedings of the Second ACM SIGPLAN International Conference on Functional Programming (ICFP '97)*, pp. 85–98, Amsterdam, June 1997.
- **What it does:** Combines coercion-based unboxing (Leroy 1992) with type-passing (TIL) in SML/NJ's FLINT IR so that recursive datatypes, mutable references, and multi-field records/tuples can be flattened without exponential coercion blowup across module/functor boundaries.
- **Download / Source URLs:**
  - Yale FLINT Archive (PDF): https://flint.cs.yale.edu/flint/publications/flex.pdf
  - ACM Open Access PDF: https://dl.acm.org/doi/pdf/10.1145/258948.258958

### 3.5 Ohori & Takamizawa (1997) — *An Unboxed Operational Semantics for ML Polymorphism* *(New Reference)*
- **Citation:** Atsushi Ohori and Tomonobu Takamizawa. *LISP and Symbolic Computation*, 10(1):61–91, May 1997 (extended from FPCA '95: *A Polymorphic Record Calculus and its Compilation*).
- **What it does:** Develops an unboxed operational semantics and compilation strategy where records and tuples are represented as flat, contiguous vectors/frames without extra pointer indirections even in the presence of ML polymorphism.
- **Download / Source URLs:**
  - Springer DOI: https://doi.org/10.1023/A:1007721502144

---

## 4. Container Flattening, Nested Data Parallelism, and AoS-to-SoA Layout Transformations

These works relate directly to **`ShallowFlatten`** and **`DeepFlatten`** (flattening tuples inside arrays/vectors, choosing between Array-of-Structs (AoS / flat contiguous interleaved elements) and Struct-of-Arrays (SoA / parallel arrays)).

### 4.1 Blelloch & Sabot (1990) — *Compiling Collection-Oriented Languages onto Massively Parallel Computers* & Blelloch (1990) — *Vector Models for Data-Parallel Computing* *(New References)*
- **Citations:**
  1. Guy E. Blelloch and Gary W. Sabot. *Journal of Parallel and Distributed Computing*, 8(2):119–134, February 1990.
  2. Guy E. Blelloch. *Vector Models for Data-Parallel Computing*. MIT Press, 1990.
- **What they do:** Introduce the **flattening transformation** for nested data parallelism (NESL / Paralation Lisp), including the foundational representation rule that a parallel sequence/array of tuples `[(a1, b1), ..., (an, bn)]` is represented in memory as a **tuple of parallel sequences (SoA)**: `([a1, ..., an], [b1, ..., bn])`.
- **Relevance to `ShallowFlatten` / `DeepFlatten`:** This is the historical origin of the SoA container transformation in functional languages, later adapted by Data Parallel Haskell (Chakravarty et al. 2007), Manticore's Data-Only Flattening (`dataonly-paper`, Bergstrom et al. 2013), and Futhark (`futhark-flatten`, Henriksen et al. 2019).
- **Download / Source URLs:**
  - *Vector Models for Data-Parallel Computing* (Full Book PDF hosted by CMU): https://www.cs.cmu.edu/~guyb/papers/Ble90.pdf
  - *Compiling Collection-Oriented Languages...* (CMU Author Archive PDF): https://www.cs.cmu.edu/~guyb/papers/BS90.pdf

### 4.2 Chakravarty, Leshchinskiy, Peyton Jones, Keller, & Marlow (2007) — *Data Parallel Haskell: A Status Report* *(New Reference)*
- **Citation:** Manuel M. T. Chakravarty, Roman Leshchinskiy, Simon Peyton Jones, Gabriele Keller, and Simon Marlow. In *Proceedings of the ACM SIGPLAN Workshop on Declarative Aspects of Multicore Programming (DAMP '07)*, pp. 10–18, Nice, France, January 2007.
- **What it does:** Introduces **type-indexed parametric array representations (`[: a :]`)** via associated type families in GHC. Specifically, an array of pairs `[: (a, b) :]` is defined by type-directed representation transformation as a pair of unboxed arrays `(:*:)` (i.e., SoA layout), eliminating per-element tuple pointers and enabling loop fusion (`Stream` fusion) to eliminate intermediate tuple allocations.
- **Relevance to `ShallowFlatten`:** Demonstrates how GHC/DPH achieves SoA array flattening via type families + stream fusion, in contrast to MaPLe's whole-program SSA transformation in `ShallowFlatten`.
- **Download / Source URLs:**
  - Microsoft Research / CMU Archive (PDF): https://www.cs.cmu.edu/~crary/819-f09/Chakravarty07.pdf
  - Microsoft Research Publication Page: https://www.microsoft.com/en-us/research/publication/data-parallel-haskell-a-status-report/

### 4.3 Keller, Chakravarty, Leshchinskiy, Peyton Jones, & Lippmeier (2010) — *Regular, Shape-Polymorphic, Parallel Arrays in Haskell (Repa)* *(New Reference)*
- **Citation:** Gabriele Keller, Manuel M. T. Chakravarty, Roman Leshchinskiy, Simon Peyton Jones, and Ben Lippmeier. In *Proceedings of the 15th ACM SIGPLAN International Conference on Functional Programming (ICFP '10)*, pp. 261–272, Baltimore, MD, September 2010.
- **What it does:** Shows how delayed/manifest arrays combined with `Unbox` type classes (which represent arrays of tuples as tuples of unboxed vectors—SoA) and GHC's `SpecConstr` / worker-wrapper eliminate intermediate tuple allocations in parallel array pipelines.
- **Download / Source URLs:**
  - Microsoft Research Archive (PDF): https://www.microsoft.com/en-us/research/wp-content/uploads/2016/07/repa-icfp10.pdf
  - ACM DOI: https://doi.org/10.1145/1863543.1863582

### 4.4 Chilimbi, Davidson, & Larus (1999) — *Cache-Conscious Structure Definition* *(New Reference)*
- **Citation:** Trishul M. Chilimbi, Bob Davidson, and James R. Larus. In *Proceedings of the ACM SIGPLAN 1999 Conference on Programming Language Design and Implementation (PLDI '99)*, pp. 13–24, Atlanta, GA, May 1999.
- **What it does:** The classic systems/compiler paper on **structure splitting** (splitting structs/tuples into hot and cold sub-structures, an AoS-to-SoA variant) and **field reordering** to improve cache line utilization and reduce memory bandwidth pressure.
- **Relevance to `ShallowFlatten`:** Provides the classic microarchitectural motivation (cache utilization, spatial locality, working-set reduction) for why transforming array-of-pointers-to-tuples into flat AoS or split SoA yields large speedups on memory-bound workloads.
- **Download / Source URLs:**
  - Microsoft Research Publication Page: https://www.microsoft.com/en-us/research/publication/cache-conscious-structure-definition/
  - ACM Digital Library (Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/301618.301635
  - UW-Madison Related Technical Report / Thesis Archive: http://digital.library.wisc.edu/1793/60228

### 4.5 Koparkar, Rainey, Vollmer, Kulkarni, & Newton (2021) — *Efficient Tree-Traversals: Reconciling Parallelism and Dense Data Representations* *(New Reference)*
- **Citation:** Chaitanya Koparkar, Mike Rainey, Michael Vollmer, Milind Kulkarni, and Ryan R. Newton. *Proceedings of the ACM on Programming Languages (PACMPL)*, Vol. 5, Issue ICFP, Article 91, August 2021.
- **What it does:** Extends Gibbon/`LoCal` (`local-paper` in your `.bib`) with parallel task scheduling ( directly comparing against and integrating concepts from MaPLe/MPL!) to study how dense, pointer-free / flattened ADT representations interact with parallel task granularity and garbage collection.
- **Relevance to `related_work.tex` & `evaluation.tex`:** You already cite `local-paper` (Vollmer et al. 2019); this 2021 follow-up specifically evaluates parallel execution and compares against MaPLe!
- **Download / Source URLs:**
  - arXiv Open Access Preprint (PDF): https://arxiv.org/pdf/2107.00522.pdf
  - ACM Open Access DOI: https://doi.org/10.1145/3473596

---

## 5. Escape Analysis, Scalar Replacement of Aggregates (SROA), and Object Inlining in Imperative & JIT Compilers

In imperative, OO, and JIT compilers (LLVM, Rust, Java HotSpot, GraalVM), the analog of local tuple flattening is **Scalar Replacement of Aggregates (SROA)** (often preceded by **Escape Analysis** or **Object Inlining**), while the analog of interprocedural tuple flattening is **Argument Promotion**.

### 5.1 Stadler, Würthinger, & Mössenböck (2014) — *Partial Escape Analysis and Scalar Replacement for Java* *(New Reference)*
- **Citation:** Lukas Stadler, Thomas Würthinger, and Hanspeter Mössenböck. In *Proceedings of the 12th Annual IEEE/ACM International Symposium on Code Generation and Optimization (CGO '14)*, pp. 165–174, Orlando, FL, February 2014.
- **What it does:** Introduces **Partial Escape Analysis (PEA)** in the GraalVM compiler. Unlike traditional escape analysis—which aborts scalar replacement (flattening an object/tuple into registers) if the object escapes on *any* control-flow branch—PEA keeps the object flattened (unallocated, represented only by its scalar components) along all non-escaping control-flow paths and **materializes (packs/allocates) the heap object lazily only on the specific branches where it escapes**.
- **Relevance to `PreFlatten`:** This is the control-flow dual of `PreFlatten`: when some paths/callers need a boxed tuple/constructor and others can work with flattened scalars, PEA/SROA delays materialization to the boundary where boxing is required rather than conservatively boxing everywhere (as MLton's original `Flatten` did when unification failed).
- **Download / Source URLs:**
  - JKU Linz Official Archive (PDF): https://www.ssw.uni-linz.ac.at/Research/Papers/Stadler14/Stadler2014-CGO-PEA.pdf
  - ACM DOI: https://doi.org/10.1145/2544137.2544157

### 5.2 Dolby & Chien (1998, 2000) — *An Automatic Object Inlining Optimization and its Evaluation* *(New Reference)*
- **Citations:**
  1. Julian Dolby. *Automatic Inline Allocation of Objects*. In *Proceedings of the ACM SIGPLAN 1997 Conference on Programming Language Design and Implementation (PLDI '97)*, pp. 7–17, June 1997.
  2. Julian Dolby and Andrew A. Chien. *An Automatic Object Inlining Optimization and its Evaluation*. In *Proceedings of the ACM SIGPLAN 2000 Conference on Programming Language Design and Implementation (PLDI '00)*, pp. 345–357, June 2000.
- **What they do:** Whole-program interprocedural analysis and transformation (implemented in the Concert C++/ICC compiler) that flattens heap-allocated child objects directly into their parent containers/objects (eliminating pointer indirections) and clones/specializes methods when callers pass either inlined (flattened) or non-inlined representations.
- **Relevance to `PreFlatten` and `ShallowFlatten` / `DeepFlatten`:** Combines container field flattening (like `DeepFlatten`/`RefFlatten`) with interprocedural function specialization/cloning when call sites disagree on whether an object is flattened (just like `PreFlatten`!).
- **Download / Source URLs:**
  - PLDI '97 Paper (ACM Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/258915.258918
  - PLDI '00 Paper (ACM Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/349299.349344

### 5.3 Choi, Gupta, Serrano, Sreedhar, & Midkiff (1999) — *Escape Analysis for Java* *(New Reference)*
- **Citation:** Jong-Deok Choi, Manish Gupta, Mauricio Serrano, Vugranam C. Sreedhar, and Sam Midkiff. In *Proceedings of the 14th ACM SIGPLAN Conference on Object-Oriented Programming, Systems, Languages, and Applications (OOPSLA '99)*, pp. 1–19, November 1999.
- **What it does:** Connection-graph escape analysis for Java used to determine when heap-allocated objects/tuples are method-local or thread-local, enabling stack allocation and scalar replacement (flattening fields into local variables).
- **Download / Source URLs:**
  - ACM Digital Library (Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/320384.320386
  - DOI: https://doi.org/10.1145/320384.320386

---

## 6. Official Compiler Documentation & Pass Guides (How Production Compilers Handle Tuple Flattening Today)

Below are direct links to official compiler documentation and source code describing how other production compilers implement tuple/aggregate flattening:

### 6.1 MLton SSA Optimization Catalog (`Flatten`, `LocalFlatten`, `DeepFlatten`, `RefFlatten`, `Useless`)
- **Documentation URLs:**
  - MLton SSA Optimization Overview: http://mlton.org/SSA
  - `Flatten` Pass Documentation: http://mlton.org/Flatten
  - `LocalFlatten` Pass Documentation: http://mlton.org/LocalFlatten
  - `DeepFlatten` Pass Documentation: http://mlton.org/DeepFlatten
  - `RefFlatten` Pass Documentation: http://mlton.org/RefFlatten
  - `Useless` Pass Documentation (eliminates unused tuple components): http://mlton.org/Useless
- **How it works:**
  - `Flatten` flattens tuple arguments across SSA functions and basic blocks (up to bounded depth).
  - `LocalFlatten` flattens tuples constructed and projected purely within a single SSA function.
  - `DeepFlatten` flattens tuples nested inside arrays, vectors, or other heap objects.
  - `RefFlatten` flattens mutable `ref` cells directly into a containing tuple/constructor allocation when lifetime/aliasing permits.

### 6.2 GHC User's Guide & Commentary (Worker/Wrapper, `SpecConstr`, Unboxed Tuples, Strict Field Unboxing)
- **Documentation URLs:**
  - GHC User's Guide — Optimization Flags (`-fworker-wrapper`, `-fspec-constr`, `-funbox-strict-fields`, `-funbox-small-strict-fields`): https://downloads.haskell.org/ghc/latest/docs/users_guide/using-optimisation.html
  - GHC User's Guide — Unboxed Types and Unboxed Tuples (`(# a, b #)`): https://downloads.haskell.org/ghc/latest/docs/users_guide/exts/primitives.html#unboxed-tuples
  - GHC Developer Wiki — Worker/Wrapper & Demand Analysis: https://gitlab.haskell.org/ghc/ghc/-/wikis/commentary/compiler/demand
  - GHC Developer Wiki — `SpecConstr` (Call-pattern specialization): https://gitlab.haskell.org/ghc/ghc/-/wikis/spec-constr
- **How it works:**
  - **Return Flattening (`CPR` — Constructed Product Result analysis):** When a function returns a constructed tuple or single-constructor ADT, CPR analysis transforms the worker to return an unboxed tuple `(# a, b #)` in registers rather than allocating a heap box.
  - **Argument Flattening:** Strictness analysis + worker/wrapper unpacks strict product arguments into separate worker parameters; `-fspec-constr` specializes recursive functions on constructor/tuple argument patterns even when not strictly evaluated on all paths.
  - **Data Structure Flattening (`UNPACK` / `-funbox-small-strict-fields`):** Automatically flattens strict fields that are pointer-sized or smaller (or annotated with `{-# UNPACK #-}`) directly into the parent ADT constructor's heap payload.

### 6.3 LLVM (`SROA`, `ArgumentPromotion`, `DeadArgumentElimination`)
- **Documentation URLs:**
  - LLVM Passes Reference (`sroa`, `argpromotion`, `deadargelim`): https://llvm.org/docs/Passes.html
  - `SROA` Source & Algorithm Docs (`llvm/lib/Transforms/Scalar/SROA.cpp`): https://github.com/llvm/llvm-project/blob/main/llvm/lib/Transforms/Scalar/SROA.cpp
  - `ArgumentPromotion` Source (`llvm/lib/Transforms/IPO/ArgumentPromotion.cpp`): https://github.com/llvm/llvm-project/blob/main/llvm/lib/Transforms/IPO/ArgumentPromotion.cpp
- **How it works:**
  - **`sroa` (Scalar Replacement of Aggregates):** Partitions stack-allocated aggregates (`alloca` of structs/tuples/arrays) into independent scalar slices and promotes them to SSA virtual registers (`mem2reg`).
  - **`argpromotion` (Interprocedural Argument Promotion):** Inspects `internal`/`private` functions taking pointer-to-struct/tuple arguments by reference. If the callee only loads fields from the pointer safely, `argpromotion` clones/rewrites the function signature to pass the loaded scalar fields by value in registers.

### 6.4 Rust (`rustc` MIR SROA & `PassMode::Pair` / `ScalarPair` ABI Flattening)
- **Documentation URLs:**
  - Rust Compiler Development Guide — MIR Optimizations (including MIR SROA / `ScalarReplacementOfAggregates`): https://rustc-dev-guide.rust-lang.org/mir/optimizations.html
  - `rustc` MIR SROA Implementation (`compiler/rustc_mir_transform/src/sroa.rs`): https://github.com/rust-lang/rust/blob/master/compiler/rustc_mir_transform/src/sroa.rs
  - `rustc_target` ABI Specification (`PassMode::Pair` / `ScalarPair` for 2-element tuples/slices/fat pointers): https://doc.rust-lang.org/nightly/nightly-rustc/rustc_abi/enum.PassMode.html
- **How it works:**
  - At the MIR level, `sroa.rs` flattens non-escaping local tuples and structs into separate local variables before LLVM lowering.
  - During ABI lowering, `rustc`'s default Rust calling convention automatically flattens 2-scalar aggregates (such as `(u64, u64)`, `&[T]`, `Option<usize>`) into `PassMode::Pair(Scalar, Scalar)`, passing both components directly in registers without relying on LLVM IPO.

### 6.5 OCaml (Flambda Middle-End & OxCaml / Jane Street Unboxed Types & Tuples)
- **Documentation URLs:**
  - OCaml Manual — Flambda Optimizer (unboxing of closures, numbers, and blocks): https://ocaml.org/manual/latest/flambda.html
  - OxCaml (Jane Street OCaml Extensions) — Unboxed Types & Layouts (`#(a, b)` unboxed tuples and `value_or_null`): https://oxcaml.org/documentation/unboxed-types/
  - Jane Street Tech Talk (`layout-poly-paper` in your `.bib`): https://www.janestreet.com/tech-talks/unboxed-types-for-ocaml/
- **How it works:**
  - Standard OCaml's **Flambda / Flambda 2** optimizer tracks block/tuple allocations across inlined functions and unboxes local tuple allocations via dead-block elimination and worker/wrapper-style function specialization.
  - **OxCaml** introduces explicit unboxed products/tuples `#(a, b)` with layout kinds (`bits64 & bits64`, `value & float64`, etc.) that are flattened both in registers (across function calls) and inline inside records/arrays.

---

## 7. Quick-Reference Summary: Which Papers Best Fit Which Section of `related_work.tex`

| Thesis Section | Best Additional Papers to Cite | Why They Fit |
| :--- | :--- | :--- |
| **`\section{tuple Flattening}`** | **Hannan & Hicks (1998)** (*Higher-Order Arity Raising*); **Tarditi et al. (1996)** (*TIL*); **Shao & Appel (1995)** (*FLINT*); **Peyton Jones & Launchbury (1991)** (*Unboxed values / Worker-Wrapper*); **Stadler et al. (2014)** (*Partial Escape Analysis*) | Contrasts whole-program first-order SSA tuple flattening (`Flatten` / `PreFlatten`) against type-directed higher-order arity raising, GHC's strictness-driven worker/wrapper, and Graal's partial escape analysis. |
| **`\section{ConApp Flattening}`** | **Peyton Jones (2007)** (*Call-Pattern Specialisation for Haskell Programs / `SpecConstr`*); **Dolby & Chien (2000)** (*Object Inlining*) | **`SpecConstr` (2007) is a must-cite here:** it specializes functions based on constructor patterns (`ConApp`s and tuples) at call sites so constructor allocation and case-dispatch cancel out, just like `PreFlatten`! |
| **`\section{array, vector Flattening}`** | **Blelloch & Sabot (1990)** (*NESL Flattening*); **Chakravarty et al. (2007)** (*Data Parallel Haskell*); **Keller et al. (2010)** (*Repa*); **Chilimbi et al. (1999)** (*Cache-Conscious Structure Definition*); **Koparkar et al. (2021)** (*Efficient Tree-Traversals*) | Connects `ShallowFlatten`'s AoS/SoA container transformations to the classic NESL/DPH/Repa SoA array representations and Chilimbi's cache-conscious structure splitting. |

---

## 8. Ready-to-Paste BibTeX Entries for New References

```bibtex
@inproceedings{specconstr-paper,
  author    = {Peyton Jones, Simon},
  title     = {Call-pattern specialisation for {Haskell} programs},
  booktitle = {Proceedings of the 12th ACM SIGPLAN International Conference on Functional Programming (ICFP '07)},
  year      = {2007},
  pages     = {327--337},
  publisher = {ACM},
  doi       = {10.1145/1291151.1291200},
  url       = {https://www.microsoft.com/en-us/research/wp-content/uploads/2016/07/specconstr.pdf}
}

@inproceedings{unboxed-values-paper,
  author    = {Peyton Jones, Simon L. and Launchbury, John},
  title     = {Unboxed values as first-class citizens in a non-strict functional language},
  booktitle = {Functional Programming Languages and Computer Architecture (FPCA '91)},
  series    = {Lecture Notes in Computer Science},
  volume    = {523},
  pages     = {636--666},
  publisher = {Springer},
  year      = {1991},
  doi       = {10.1007/3540543961_30},
  url       = {https://www.microsoft.com/en-us/research/wp-content/uploads/1991/01/unboxed-values.pdf}
}

@inproceedings{ho-arity-raising,
  author    = {Hannan, John and Hicks, Patrick},
  title     = {Higher-order arity raising},
  booktitle = {Proceedings of the Third ACM SIGPLAN International Conference on Functional Programming (ICFP '98)},
  pages     = {27--38},
  year      = {1998},
  publisher = {ACM},
  doi       = {10.1145/289423.289426},
  url       = {https://dl.acm.org/doi/pdf/10.1145/289423.289426}
}

@inproceedings{til-paper,
  author    = {Tarditi, David and Morrisett, Greg and Cheng, Perry and Stone, Chris and Harper, Robert and Lee, Peter},
  title     = {{TIL}: A type-directed optimizing compiler for {ML}},
  booktitle = {Proceedings of the ACM SIGPLAN 1996 Conference on Programming Language Design and Implementation (PLDI '96)},
  pages     = {181--192},
  year      = {1996},
  publisher = {ACM},
  doi       = {10.1145/231379.231414},
  url       = {https://nrs.harvard.edu/urn-3:HUL.InstRepos:2797452}
}

@phdthesis{tarditi-thesis,
  author    = {Tarditi, David},
  title     = {Design and Implementation of Code Optimizations for a Type-Directed Compiler for {Standard ML}},
  school    = {Carnegie Mellon University},
  year      = {1996},
  month     = dec,
  note      = {CMU-CS-97-108},
  url       = {http://reports-archive.adm.cs.cmu.edu/anon/1997/CMU-CS-97-108.pdf}
}

@inproceedings{leroy-unboxed-1992,
  author    = {Leroy, Xavier},
  title     = {Unboxed objects and polymorphic typing},
  booktitle = {Proceedings of the 19th ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages (POPL '92)},
  pages     = {177--188},
  year      = {1992},
  publisher = {ACM},
  doi       = {10.1145/143165.143205},
  url       = {https://xavierleroy.org/publi/unboxed-popl92.pdf}
}

@inproceedings{henglein-optimal-boxing,
  author    = {Henglein, Fritz and J{\o}rgensen, Jesper},
  title     = {Formally optimal boxing},
  booktitle = {Proceedings of the 21st ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages (POPL '94)},
  pages     = {213--226},
  year      = {1994},
  publisher = {ACM},
  doi       = {10.1145/174675.177874},
  url       = {https://dl.acm.org/doi/pdf/10.1145/174675.177874}
}

@inproceedings{shao-appel-1995,
  author    = {Shao, Zhong and Appel, Andrew W.},
  title     = {A type-based compiler for {Standard ML}},
  booktitle = {Proceedings of the ACM SIGPLAN 1995 Conference on Programming Language Design and Implementation (PLDI '95)},
  pages     = {116--129},
  year      = {1995},
  publisher = {ACM},
  doi       = {10.1145/207110.207123},
  url       = {https://flint.cs.yale.edu/flint/publications/sml-pldi95.pdf}
}

@inproceedings{shao-flex-1997,
  author    = {Shao, Zhong},
  title     = {Flexible representation analysis},
  booktitle = {Proceedings of the Second ACM SIGPLAN International Conference on Functional Programming (ICFP '97)},
  pages     = {85--98},
  year      = {1997},
  publisher = {ACM},
  doi       = {10.1145/258948.258958},
  url       = {https://flint.cs.yale.edu/flint/publications/flex.pdf}
}

@article{kinds-calling-conventions,
  author    = {Downen, Paul and Ariola, Zena M. and Peyton Jones, Simon and Eisenberg, Richard A.},
  title     = {Kinds are calling conventions},
  journal   = {Proceedings of the ACM on Programming Languages},
  volume    = {4},
  number    = {ICFP},
  articleno = {104},
  pages     = {1--29},
  year      = {2020},
  publisher = {ACM},
  doi       = {10.1145/3408986},
  url       = {http://pauldownen.com/publications/kacc.pdf}
}

@article{blelloch-sabot-1990,
  author    = {Blelloch, Guy E. and Sabot, Gary W.},
  title     = {Compiling collection-oriented languages onto massively parallel computers},
  journal   = {Journal of Parallel and Distributed Computing},
  volume    = {8},
  number    = {2},
  pages     = {119--134},
  year      = {1990},
  url       = {https://www.cs.cmu.edu/~guyb/papers/BS90.pdf}
}

@inproceedings{dph-status-2007,
  author    = {Chakravarty, Manuel M. T. and Leshchinskiy, Roman and Peyton Jones, Simon and Keller, Gabriele and Marlow, Simon},
  title     = {{Data Parallel Haskell}: A status report},
  booktitle = {Proceedings of the ACM SIGPLAN Workshop on Declarative Aspects of Multicore Programming (DAMP '07)},
  pages     = {10--18},
  year      = {2007},
  publisher = {ACM},
  url       = {https://www.cs.cmu.edu/~crary/819-f09/Chakravarty07.pdf}
}

@inproceedings{chilimbi-structure-splitting,
  author    = {Chilimbi, Trishul M. and Davidson, Bob and Larus, James R.},
  title     = {Cache-conscious structure definition},
  booktitle = {Proceedings of the ACM SIGPLAN 1999 Conference on Programming Language Design and Implementation (PLDI '99)},
  pages     = {13--24},
  year      = {1999},
  publisher = {ACM},
  doi       = {10.1145/301618.301635},
  url       = {https://dl.acm.org/doi/pdf/10.1145/301618.301635}
}

@inproceedings{dolby-object-inlining,
  author    = {Dolby, Julian and Chien, Andrew A.},
  title     = {An automatic object inlining optimization and its evaluation},
  booktitle = {Proceedings of the ACM SIGPLAN 2000 Conference on Programming Language Design and Implementation (PLDI '00)},
  pages     = {345--357},
  year      = {2000},
  publisher = {ACM},
  doi       = {10.1145/349299.349344},
  url       = {https://dl.acm.org/doi/pdf/10.1145/349299.349344}
}

@inproceedings{stadler-pea-2014,
  author    = {Stadler, Lukas and W{\"u}rthinger, Thomas and M{\"o}ssenb{\"o}ck, Hanspeter},
  title     = {Partial escape analysis and scalar replacement for {Java}},
  booktitle = {Proceedings of the 12th Annual IEEE/ACM International Symposium on Code Generation and Optimization (CGO '14)},
  pages     = {165--174},
  year      = {2014},
  publisher = {ACM},
  doi       = {10.1145/2544137.2544157},
  url       = {https://www.ssw.uni-linz.ac.at/Research/Papers/Stadler14/Stadler2014-CGO-PEA.pdf}
}
```
