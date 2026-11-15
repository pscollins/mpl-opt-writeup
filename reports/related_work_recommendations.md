# Recommendations for Substantive Edits & New Citations in `related_work.tex`

This document contains:
1. **Substantive Content & Structural Refinements** for existing paragraphs in `latex/chapters/related_work.tex` (left untouched in `related_work.tex` so only mechanical/typo/citation fixes were applied directly).
2. **Prioritized New Citations** from `reports/` (`argon_tuple_lit_search.md`, `argon_conapp_lit_search.md`, and `argon_shallowflat_lit_search.md`), ranked by value, along with suggested LaTeX prose and BibTeX entries.

---

## Part A: Substantive Refinements to Existing Content in `related_work.tex`

1. **Section 1 Organization (`\section{Flattening Function Arguments}`):**
   - Currently, Section 1 alternates back and forth between `tuple` flattening and `ConApp` flattening (Lines 3–9: `tuple`, Lines 10–19: `ConApp`, Lines 21–33: `tuple`, Lines 35–40: `ConApp`, Lines 42–61: `tuple`, Lines 63–95: `ConApp`, Lines 99–124: `tuple`/SROA).
   - **Recommendation:** Split Section 1 into two subsections—`\subsection{Tuple Argument Flattening and SROA}` and `\subsection{Constructor (\texttt{ConApp}) Specialization and ADT Representations}`—and group the `tuple` paragraphs together followed by the `ConApp` paragraphs.

2. **Line 24 (`\citet{higher-order-flattening}` comparison target):**
   - Currently reads: *"solving the SML-NJ-lineage (CPS IR) equivalent of MLton's `\citet{mlton-closure-paper}`."*
   - **Recommendation:** Since `higher-order-flattening` (Hannan & Hicks 1998) is about higher-order arity raising (tuple flattening) rather than closure conversion, comparing it to MLton's `\citet{flat-paper}` (or both `\citet{flat-paper}` and `\citet{mlton-closure-paper}`) is more precise.

3. **Lines 42–50 (`\citet{compiling-with-types}` — Morrisett 1995, Section 5.2.4 & 8.5.4):**
   - **Verified accurate in `related_work.tex`:** Morrisett's thesis (*Compiling with Types*, CMU-CS-95-226, Section 5.2.4 pp. 78–87 and Section 8.5.4 p. 184) explicitly presents the 3-case translation of functions and applications (known tuple with $\le k$ elements, known non-tuple / tuple with $> k$ elements, and unknown type variable $t$ handled via `Vararg`/`vararg`/`onearg` using `typecase` at runtime).
   - **Optional complementary citation:** If desired, you can also cite **Shao & Appel (PLDI '95)** (`shao-appel-1995`) alongside `\citet{compiling-with-types}` (which Morrisett himself cites on p. 70 and p. 184 as the coercion-based SML/NJ counterpart to his `vararg`/`onearg` dynamic type dispatch approach), or keep the paragraph as-is since its description of `\citet{compiling-with-types}` is completely spot-on.

4. ~~**Lines 52–61 (`\citet{haskell-fc-unbox}` — Peyton Jones & Launchbury 1991):**~~
   - Currently describes the `worker` as *"a re-pack sequence followed by the original function body."*
   - **Recommendation:** Clarify that the worker/wrapper split is driven by **strictness analysis** (requiring the callee to be strict in the tuple on *all* control-flow paths), and that the inlineable `wrapper` unpacks the tuple and calls the `worker` with flattened scalar arguments, while inside the `worker` the temporary re-pack cancels with projections in the function body via known-constructor simplification.

5. **Lines 76–87 (`\citet{local-paper}` and `\citet{adt4hpc-paper}`):**
   - Currently groups `\citet{local-paper}` (Vollmer et al. 2019, LoCal/Gibbon) and `\citet{adt4hpc-paper}` (Baudon 2024) together as both being *"concerned with manual control over the format of serialized data on disk."*
   - **Recommendation:** Separate them! `\citet{local-paper}` (LoCal/Gibbon) operates on dense, serialized/packed tree buffers (and infers buffer locations automatically or semi-automatically). By contrast, `\citet{adt4hpc-paper}` (Baudon's 2024 PhD thesis and her ICFP '23 `Ribbit` paper, `baudon-ribbit-2023`) is about **in-memory** bit-stealing (`Ribbit`, closely related to `\citet{double-steal-paper}`) and **in-memory AoS/SoA layout transformations for arrays of ADTs**.

6. **Lines 128–144 (`\section{\texttt{array}, \texttt{vector} Flattening}`):**
   - **Explicitly name `\texttt{ShallowFlatten}` ($\Phi_{\text{AoS}}$ and $\Phi_{\text{SoA}}$):** Currently the section text never uses the name `\texttt{ShallowFlatten}`.
   - **Lines 132–138 (`\citet{layout-poly-paper}`):** Jane Street's unboxed product arrays (`#(a, b) array`) lay out elements contiguously inline (**AoS**, not SoA). Recommend saying *"through `\texttt{ShallowFlatten}`'s AoS and SoA transformations."*
   - **Line 142 (`\citet{realtime-sml-paper}`):** Currently says *"We avoid this issue by simply restricting ourselves to tuples with uniform element types..."* Recommend clarifying that **only the AoS variant ($\Phi_{\text{AoS}}$) of `\texttt{ShallowFlatten}`** restricts to uniform element types, whereas the **SoA variant ($\Phi_{\text{SoA}}$)** naturally supports heterogeneous tuples `(t1 * ... * tk) array` because each component type resides in its own homogeneous array.

---

## Part B: Prioritized New References from `reports/` to Include Next

### Tier 1: Immediate High-Value Additions (Resolves Open `\hl{TODO}`s & Closest Architectural Analogs)

#### 1. Resolving the SROA, ABI/Procedure Cloning, and Partial Escape Analysis `\hl{TODO}`s (`related_work.tex` lines 97–125)
- **References to Cite:**
  1. **System V AMD64 ABI (`amd64-abi`)** — *Already in `references.bib`*
  2. **Cooper, Hall, & Kennedy (1993)** — *A Methodology for Procedure Cloning* (`procedure-cloning-1993`)
  3. **Stadler, Würthinger, & Mössenböck (CGO 2014)** — *Partial Escape Analysis and Scalar Replacement for Java* (`partial-escape-analysis`, now in `references.bib`)
- **Why this is top priority:**
  - Directly resolves all three `\hl{TODO}` markers in `related_work.tex` (`\hl{TODO: CHECK}`, `\hl{TODO: NEED REFERENCE FOR THE SECOND PART}`, and `\hl{TODO: how to summarize difference?}`).
  - Explains that external C/C++ functions must obey platform calling conventions (`amd64-abi`, which passes aggregates larger than two eightbytes in memory), and that interprocedural signature changes require **procedure cloning** (`procedure-cloning-1993`) or LLVM's `ArgumentPromotion` restricted to internal-linkage functions whose pointer arguments do not escape.
  - Sharpens the contrast with **Partial Escape Analysis (PEA)** (`partial-escape-analysis`): PEA is an *intraprocedural* control-flow transformation that keeps an object scalarized along non-escaping branches and delays heap allocation ("pack") onto only those branches where the object escapes (such as a non-inlined call), whereas `PreFlatten` is an *interprocedural* call-graph transformation that specializes the callee's signature so the object does not escape across the call boundary in the first place.
- **Suggested Replacement LaTeX for `related_work.tex` (Lines 97–125):**
```latex
The equivalent intraprocedural transformation in C/C++ compilers like \texttt{clang} or
\texttt{gcc} is referred to as ``scalar replacement of aggregates'' (SROA), as
described in \citet{munchick-compiler-design}. Since these languages natively
support ``unboxed'' \texttt{struct} value types, the goal in this context is to
promote stack-allocated aggregates into SSA registers and enable subsequent optimizations like constant or copy propagation, rather than
to eliminate heap allocations. In order for the transformation to be sound, the
compiler must prove that no address references to the aggregate escape the current
function, since (like our tuple flattening) the transformation cannot preserve
the memory address of the original aggregate. Due to separate compilation and fixed platform ABI
constraints (such as \citet{amd64-abi}, which requires aggregates exceeding two 64-bit eightbytes to be passed in memory), \texttt{clang} and \texttt{gcc} cannot alter externally visible function signatures, and can only apply interprocedural procedure cloning \citep{procedure-cloning-1993} or argument promotion to internal-linkage functions whose pointer arguments do not escape.

SROA is also a common optimization technique in higher-level, JIT-compiled
languages, such as Java. \citet{partial-escape-thesis} provides a detailed
introduction to the general optimization for Java, and additionally introduces a
``partial escape analysis'' that solves a related problem to our
mixed-caller \texttt{PreFlatten} transformation. In the Java case, the benefits
of SROA are more similar to the MLton case than the \texttt{clang} case -- Java
aggregate objects are heap allocated, and hence replacement with scalars
eliminates an allocation. The soundness analysis in the Java case is identical
to the C/C++ case -- the compiler must prove that references to the flattenable
object do not escape the current scope. \citet{partial-escape-analysis}
introduces a novel technique to enable SROA when an object escapes on some (but
not all) control-flow paths: their solution is an intraprocedural transformation that delays the ``pack'' (allocation) operation
onto only those control-flow branches where the object escapes (e.g., into a non-inlined call), whereas our \texttt{PreFlatten} is an interprocedural transformation that clones and specializes the callee signature so that the tuple does not escape across the call at all.
```

---

#### 2. Ureche, Biboudis, Smaragdakis, & Odersky (OOPSLA 2015) — *Automating Ad-Hoc Data Representation Transformations (`ildl`)*
- **Where it fits:** `\section{\texttt{array}, \texttt{vector} Flattening}` in `related_work.tex` (and optionally `shallowflatten.tex` Motivation).
- **Why it is high-value:**
  - **Closest match in the literature to `ShallowFlatten`'s local pack/unpack bridge architecture.**
  - Scala's `ildl` framework transforms object arrays (`AoP`) into either flat scaled-index primitive arrays (`AoS`, indexing `2*i` and `2*i+1`) or parallel arrays (`SoA`) by inserting explicit `fromRepr` (**pack**) and `toRepr` (**unpack**) bridge coercions around container operations, relying on a downstream local simplification pass to cancel `fromRepr(toRepr(x)) ==> x`.
  - **Key contrast that highlights your contribution:** `ildl` requires manual programmer annotations per scope and only cancels pack/unpack pairs within local inlined expressions, whereas `ShallowFlatten` is completely automatic across the whole program and composes with interprocedural `PreFlatten` and `Flatten` to eliminate pack/unpack overhead even across non-inlined and recursive function calls.
- **Suggested LaTeX Paragraph for `related_work.tex`:**
```latex
\citet{ureche-ildl-2015} introduces the \texttt{ildl} framework for Scala, which shares \texttt{ShallowFlatten}'s two-step design philosophy: rather than fusing container layout changes with consumer optimizations in a single monolithic pass, \texttt{ildl} rewrites container accesses by inserting explicit ``pack'' (\texttt{fromRepr}) and ``unpack'' (\texttt{toRepr}) bridge coercions around AoS or SoA array primitives and relies on a subsequent simplification pass to cancel adjacent bridges. Our \texttt{ShallowFlatten} pass differs in two key respects: first, \texttt{ildl} requires explicit programmer annotations on data types and lexical scopes whereas \texttt{ShallowFlatten} is applied automatically across the whole program; second, because \texttt{ShallowFlatten} runs prior to interprocedural \texttt{PreFlatten} and \texttt{Flatten}, our pipeline cancels pack/unpack pairs across non-inlined and recursive function calls rather than only within locally inlined scopes.
```

---

#### 3. Henriksen et al. (PLDI 2017) & Henriksen PhD Thesis (2017) — *Futhark's `Internaliser` SoA Transformation*
- **Where it fits:** `\section{\texttt{array}, \texttt{vector} Flattening}` in `related_work.tex` (alongside existing `\citet{futhark-flatten}`).
- **Why it is high-value:**
  - Currently `related_work.tex` cites `futhark-flatten` (PPoPP '19, which is about nested GPU parallelism threshold tuning), but does not cite the Futhark compiler's actual array-of-tuples flattening pass (`Internaliser`), documented in **Henriksen et al. (PLDI '17)** and **Henriksen's PhD Thesis (2017, Section 4.2)**.
  - Futhark's `Internaliser` is the closest architectural match in a functional compiler to the $\Phi_{\text{SoA}}$ mode of `ShallowFlatten`: it unconditionally rewrites every array-of-tuples type `[n](t1, ..., tk)` to a tuple of arrays `([n]t1, ..., [n]tk)` recursively to a fixed point, inserts tuple pack/unpack operations around array indexing, and relies on downstream SSA simplification to eliminate the temporary tuples.
  - **Key contrast:** Futhark is a pure array DSL without general recursive `datatype`s or `ref` cells and *only* supports SoA (as required for GPU coalescing), whereas `ShallowFlatten` supports both AoS ($\Phi_{\text{AoS}}$) and SoA ($\Phi_{\text{SoA}}$) on multicore CPUs and rewrites containers nested inside arbitrary SML `datatype`s and closure environments.
- **Suggested LaTeX Addition for `related_work.tex` (expanding the `futhark-flatten` paragraph):**
```latex
In the Futhark compiler \citep{futhark-pldi17, henriksen-thesis-2017}, the early \texttt{Internaliser} pass unconditionally transforms all arrays of tuples into tuples of arrays in a manner directly analogous to our SoA variant ($\Phi_{\text{SoA}}$) of \texttt{ShallowFlatten}: array indexing and updates are rewritten to pack and unpack intermediate tuples, which downstream SSA simplification passes subsequently eliminate. Unlike Futhark -- which targets a pure array DSL without general algebraic datatypes and exclusively commits to SoA layouts for GPU memory coalescing (alongside nested parallelism flattening in \citet{futhark-flatten}) -- \texttt{ShallowFlatten} supports both AoS and SoA container layouts in a general-purpose ML compiler, rewriting container types embedded inside arbitrary recursive \texttt{datatype}s and defunctionalized closures while relying on MPL's runtime scheduler \citep{mpl-sched-paper} to manage parallel load balance.
```

---

#### 4. Wright & Jagannathan (TOPLAS 1998) — *Polymorphic Splitting* & Fluet & Weeks (ICFP 2001) — *Contification Using Dominators*
- **Where it fits:** After the `\citet{mlton-closure-paper}` paragraph in `related_work.tex` (and `background.tex` Section `sec:background_polyvar`).
- **Why it is high-value:**
  - **Wright & Jagannathan (1998)** is the theoretical foundation of MLton's `Polyvariance` pass (co-authored by Suresh Jagannathan, who also co-authored MLton's `ClosureConvert` and `Flatten` papers). Citing it lets you explain *how* MLton attempts to avoid multi-variant closure datatypes prior to `SSA` (by duplicating small higher-order functions per call site in `SXML`), and why `ConApp`-`PreFlatten` is more targeted: `ConApp`-`PreFlatten` runs *after* defunctionalization in `SSA` and emits at most one specialized clone per distinct constructor tag $\texttt{Flatten}_C$, sharing the specialization across all callers that pass the same closure variant.
  - **Fluet & Weeks (2001)** formalizes MLton's `Contify` pass, explaining when MLton can inline/contify functions into basic blocks (allowing intraprocedural `KnownCase` to fold constructor tags) and why non-contifiable functions need `ConApp`-`PreFlatten` to push `ConApp`s across call boundaries.
- **Suggested LaTeX Addition for `related_work.tex` (right after the `mlton-closure-paper` paragraph):**
```latex
To improve the precision of monovariant 0CFA during defunctionalization, MLton applies a pre-closure-conversion \texttt{Polyvariance} pass based on polymorphic splitting \citep{polymorphic-splitting-1998} as well as an SSA \texttt{Contify} pass \citep{contify-paper} that turns single-continuation functions into local basic blocks where intraprocedural \texttt{KnownCase} can fold constructor switches. However, \texttt{Polyvariance} duplicates higher-order functions per callsite under conservative size cutoffs even when callers pass identical closure variants, and \texttt{Contify} cannot inline functions called from multiple non-dominating contexts. Our \texttt{ConApp}-\texttt{PreFlatten} pass complements both by operating post-defunctionalization in \texttt{SSA} and emitting at most one specialized function per distinct constructor pattern across all callers.
```

---

### Tier 2: Strong Contextual & Foundational Additions

#### 5. Upgrading `layout-poly-paper` and `adt4hpc-paper` to Peer-Reviewed ICFP / ML Workshop Citations
- **References to Add:**
  1. **Eisenberg (ML '23)** — *Layout Polymorphism* (`eisenberg-layout-poly-2023`) & **Lorenzen, White, Dolan, Eisenberg, & Lindley (ICFP '24)** — *Oxidizing OCaml with Modal Memory Management* (`oxidizing-ocaml-2024`).
  2. **Baudon, Radanne, & Gonnord (ICFP '23)** — *Bit-Stealing Made Legal: Compilation for Custom Memory Representations of Algebraic Data Types (`Ribbit`)* (`baudon-ribbit-2023`).
- **Why it is valuable:**
  - Upgrades `layout-poly-paper` (currently a URL to a Jane Street tech talk) to the peer-reviewed ML '23 and ICFP '24 papers.
  - Pairs Thaïs Baudon's 2024 PhD dissertation (`adt4hpc-paper`) with its peer-reviewed ICFP '23 paper (`baudon-ribbit-2023`), and notes that Chapter 5 of `adt4hpc-paper` also explores AoS/SoA collection layouts for ADTs via user-specified layout descriptions.

#### 6. Shao & Appel (PLDI 1995) — *A Type-Based Compiler for Standard ML (FLINT)* & Tarditi et al. (PLDI 1996) — *TIL*
- **Where it fits:** Alongside `\citet{compiling-with-types}` in `related_work.tex` (lines 42–50).
- **Why it is valuable:**
  - `compiling-with-types` (Morrisett 1995, Chapter 5 & Section 8.5.4) already covers the TIL approach of flattening $n$-tuple arguments ($n < k$) and using dynamic `typecase` (`vararg`/`onearg`) for polymorphic/unknown argument types. Optionally citing **Tarditi et al. (PLDI '96)** (`til-paper`) adds the peer-reviewed conference paper for TIL, and citing **Shao & Appel (PLDI '95)** (`shao-appel-1995`) provides the SML/NJ counterpart that Morrisett explicitly contrasts with on pp. 70 & 81 (which uses static wrapper/coercion functions rather than runtime `typecase` at polymorphic boundaries).

#### 7. Boquist (1999) & Podlovics, Hruska, & Pénzes (2021) — *The GRIN Whole-Program Compiler*
- **Where it fits:** Section 1 (`ConApp` flattening discussion) in `related_work.tex`.
- **Why it is valuable:**
  - Outside the MLton/MPL family, **GRIN** is the primary example of a functional compiler that lowers both closures/thunks and algebraic data types via whole-program defunctionalization into uniform first-order tagged nodes (`ConApp`s) and `case` switches in an SSA-like IR, and then applies interprocedural arity raising and producer-consumer specialization to strip known constructor tags across function calls.

#### 8. Dolby & Chien (PLDI 2000) — *Automatic Object Inlining* & Budimlić & Kennedy (2001) — *Object Inlining in Java (`JaMake`)*
- **Where it fits:** `\section{\texttt{array}, \texttt{vector} Flattening}` in `related_work.tex`.
- **Why it is valuable:**
  - Provides the imperative/OO counterparts to `DeepFlatten` vs. `ShallowFlatten`:
    - **Dolby & Chien (2000)** is the OO analog of MLton's `DeepFlatten`: it inlines heap objects into arrays in-place (`AoP` $\to$ `AoS`), requiring whole-program interprocedural alias constraints so that no temporary copy allocations are ever introduced.
    - **Budimlić & Kennedy (2001)** (`JaMake`) is the OO analog of `ShallowFlatten`: it rewrites Java arrays of value-like objects (`Complex[]`) into either two parallel arrays (`SoA`) or a single length-$2n$ array (`AoS`), inserting pack/unpack operations around array accesses and relying on downstream scalar replacement to eliminate the temporary objects.

#### 9. Blelloch (1990) — *NESL Flattening* & Chakravarty et al. (2003, 2007) — *Data Parallel Haskell / `Data.Vector.Unboxed`*
- **Where it fits:** `\section{\texttt{array}, \texttt{vector} Flattening}` in `related_work.tex`.
- **Why it is valuable:**
  - Connects `ShallowFlatten`'s SoA mode ($\Phi_{\text{SoA}}$) both to its historical origin in NESL (`[(a, b)] -> ([a], [b])`, where your `quickhull` and `linearrec` benchmarks originated!) and to Haskell's type-family approach (`Data.Vector.Unboxed`, `Repa`, `Accelerate`), where SoA array representations are defined via library type families and rely on stream fusion + `SpecConstr` to eliminate intermediate tuple packs/unpacks.

---

### Tier 3: High-Impact Additions for `shallowflatten.tex` (`Limitations` Section)

#### 10. OpenJDK Project Valhalla (JEP 401: Value Classes and Objects) & Baker (1993) — *Equal Rights for Functional Objects (`egal`)*
- **Where it fits:** `latex/chapters/shallowflatten.tex` (`Section: Limitations`, lines 1105–1162) and/or `related_work.tex`.
- **Why it is high-value:**
  - In `shallowflatten.tex` (`Limitations`), you analyze three subtle consequences of `ShallowFlatten`:
    1. Breaking physical pointer identity (`MLton.eq`) on tuples read from a flattened array unless wrapped in a `ref` cell;
    2. Multi-word tearing / inability to use single-word atomic compare-and-swap (CAS) on flattened multi-element array slots;
    3. Need for a tuple width cutoff $W$ ($2 \le k \le W$).
  - **Baker (1993)** (`baker-egal-1993`) proves formally why immutable tuples in ML have value semantics (`egal`) rather than pointer identity (and why `ref` cells are the principled mechanism for identity).
  - **OpenJDK Project Valhalla (JEP 401)** (`jep401-valhalla`) encounters the **exact same three issues** when flattening arrays of `value class` objects in the JVM, and resolves them the exact same way: eliminating object identity (`==` compares by value unless wrapped in an identity reference), restricting atomic/non-tearable guarantees to hardware word limits, and enforcing a small element-width cutoff for array flattening.

---

## Consolidated BibTeX Entries for Recommended Additions

```bibtex
@article{procedure-cloning-1993,
  author    = {Cooper, Keith D. and Hall, Mary W. and Kennedy, Ken},
  title     = {A methodology for procedure cloning},
  journal   = {Computer Languages},
  volume    = {19},
  number    = {2},
  pages     = {105--118},
  year      = {1993},
  publisher = {Elsevier},
  doi       = {10.1016/0096-0551(93)90005-L}
}

@inproceedings{ureche-ildl-2015,
  author    = {Ureche, Vlad and Biboudis, Aggelos and Smaragdakis, Yannis and Odersky, Martin},
  title     = {Automating ad hoc data representation transformations},
  booktitle = {Proceedings of the 2015 ACM SIGPLAN International Conference on Object-Oriented Programming, Systems, Languages, and Applications (OOPSLA '15)},
  pages     = {733--752},
  year      = {2015},
  publisher = {ACM},
  doi       = {10.1145/2814270.2814283}
}

@inproceedings{futhark-pldi17,
  author    = {Henriksen, Troels and Serup, Niels G. W. and Elsman, Martin and Henglein, Fritz and Oancea, Cosmin E.},
  title     = {Futhark: Purely functional {GPU}-programming with nested parallelism and in-place array updates},
  booktitle = {Proceedings of the 38th ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI '17)},
  pages     = {556--571},
  year      = {2017},
  publisher = {ACM},
  doi       = {10.1145/3062341.3062354}
}

@phdthesis{henriksen-thesis-2017,
  author    = {Henriksen, Troels},
  title     = {Design and Implementation of the {Futhark} Programming Language},
  school    = {University of Copenhagen},
  year      = {2017},
  month     = dec
}

@article{polymorphic-splitting-1998,
  author    = {Wright, Andrew K. and Jagannathan, Suresh},
  title     = {Polymorphic splitting: An effective polyvariant flow analysis},
  journal   = {ACM Transactions on Programming Languages and Systems (TOPLAS)},
  volume    = {20},
  number    = {1},
  pages     = {166--207},
  year      = {1998},
  publisher = {ACM},
  doi       = {10.1145/271510.271512}
}

@inproceedings{contify-paper,
  author    = {Fluet, Matthew and Weeks, Stephen},
  title     = {Contification using dominators},
  booktitle = {Proceedings of the Sixth ACM SIGPLAN International Conference on Functional Programming (ICFP '01)},
  pages     = {2--13},
  year      = {2001},
  publisher = {ACM},
  doi       = {10.1145/507635.507639}
}

@inproceedings{eisenberg-layout-poly-2023,
  author    = {Eisenberg, Richard A.},
  title     = {Layout polymorphism: Using static computation to allow efficient polymorphism over variable representations},
  booktitle = {ACM SIGPLAN Workshop on ML (ML '23)},
  year      = {2023}
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
  doi       = {10.1145/3674642}
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
  doi       = {10.1145/3607858}
}

@inproceedings{shao-appel-1995,
  author    = {Shao, Zhong and Appel, Andrew W.},
  title     = {A type-based compiler for {Standard ML}},
  booktitle = {Proceedings of the ACM SIGPLAN 1995 Conference on Programming Language Design and Implementation (PLDI '95)},
  pages     = {116--129},
  year      = {1995},
  publisher = {ACM},
  doi       = {10.1145/207110.207123}
}

@inproceedings{til-paper,
  author    = {Tarditi, David and Morrisett, Greg and Cheng, Perry and Stone, Chris and Harper, Robert and Lee, Peter},
  title     = {{TIL}: A type-directed optimizing compiler for {ML}},
  booktitle = {Proceedings of the ACM SIGPLAN 1996 Conference on Programming Language Design and Implementation (PLDI '96)},
  pages     = {181--192},
  year      = {1996},
  publisher = {ACM},
  doi       = {10.1145/231379.231414}
}

@phdthesis{boquist-grin-thesis,
  author    = {Boquist, Urban},
  title     = {Code Optimisation Techniques for Lazy Functional Languages},
  school    = {Chalmers University of Technology},
  address   = {G{\"o}teborg, Sweden},
  year      = {1999},
  month     = apr
}

@article{modern-grin-2021,
  author    = {Podlovics, P{\'e}ter and Hruska, Csaba and P{\'e}nzes, Andor},
  title     = {A modern look at {GRIN}, an optimizing functional language back end},
  journal   = {Acta Cybernetica},
  volume    = {25},
  number    = {4},
  pages     = {847--876},
  year      = {2021},
  doi       = {10.14232/actacyb.282969}
}

@inproceedings{dolby-object-inlining-2000,
  author    = {Dolby, Julian and Chien, Andrew A.},
  title     = {An automatic object inlining optimization and its evaluation},
  booktitle = {Proceedings of the ACM SIGPLAN 2000 Conference on Programming Language Design and Implementation (PLDI '00)},
  pages     = {345--357},
  year      = {2000},
  publisher = {ACM},
  doi       = {10.1145/349299.349344}
}

@phdthesis{budimlic-thesis-2001,
  author    = {Budimli{\'c}, Zoran},
  title     = {Compiling {Java} for High Performance and the Internet},
  school    = {Rice University},
  year      = {2001}
}

@book{blelloch-vector-models-1990,
  author    = {Blelloch, Guy E.},
  title     = {Vector Models for Data-Parallel Computing},
  publisher = {MIT Press},
  address   = {Cambridge, MA},
  year      = {1990}
}

@inproceedings{dph-status-2007,
  author    = {Chakravarty, Manuel M. T. and Leshchinskiy, Roman and Peyton Jones, Simon and Keller, Gabriele and Marlow, Simon},
  title     = {{Data Parallel Haskell}: A status report},
  booktitle = {Proceedings of the ACM SIGPLAN Workshop on Declarative Aspects of Multicore Programming (DAMP '07)},
  pages     = {10--18},
  year      = {2007},
  publisher = {ACM}
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
  doi       = {10.1145/165507.165508}
}

@misc{jep401-valhalla,
  author       = {Smith, Dan and Rose, John},
  title        = {{JEP} 401: Value Classes and Objects (Preview)},
  howpublished = {OpenJDK Enhancement Proposal, \url{https://openjdk.org/jeps/401}},
  year         = {2025}
}
```
