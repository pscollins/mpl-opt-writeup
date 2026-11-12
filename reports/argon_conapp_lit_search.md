# Literature Review: `ConApp` Flattening, Call-Pattern Specialization, Defunctionalization, and ADT Representation Optimizations

This report surveys academic papers and production compiler documentation relevant to your **`ConApp` Flattening** transformation (`PreFlatten` configured for constructor applications $\texttt{Flatten}_C$, combined with `KnownCase` and `Flatten`).

To make this directly actionable for your thesis (`latex/chapters/related_work.tex`, `latex/chapters/preflatten.tex`, and `latex/chapters/background.tex`), the literature is organized around the **five core technical dimensions** of `ConApp` flattening:
1. **Call-Pattern & Constructor Specialization (`SpecConstr`, Constructor Specialization, Supercompilation):** Duplicating/specializing functions when call-site arguments are statically known constructor applications (`ConApp`s), pushing constructor allocation into the callee so it cancels with `case` dispatch.
2. **Defunctionalization, Flow-Directed Closure Conversion, Polyvariance, and Contification:** How higher-order functions become `datatype` `ConApp`s and `case` dispatches in first-order SSA, and how `ConApp` `PreFlatten` compares to pre-closure-conversion `Polyvariance` and `Contify`.
3. **Whole-Program Node/Tag Elimination in Functional Backends (GRIN, STG, Worker/Wrapper for Sums & Products):** How other functional middle-ends/backends eliminate constructor tags and unbox constructor payloads across function calls.
4. **Interprocedural Branch / Switch Elimination, Procedure Cloning, and Basic Block Versioning:** How imperative, OO, and dynamic-language compilers specialize functions or basic blocks along incoming edges to fold tag checks (`KnownCase` / jump threading).
5. **Memory Layout & Bit-Level Representation Optimizations for Algebraic Data Types (ADTs):** Eliminating pointer indirections and tag words in ADTs (`LoCal`/Gibbon, `Ribbit`, MLKit bit-stealing, Rust niche layouts, OxCaml unboxed sums).
6. **Production Compiler Documentation & Pass Implementations:** Direct links to source code and pass documentation in **MLton**, **GHC**, **OCaml (Flambda 2 & OxCaml)**, **LLVM**, and **Rust (`rustc` MIR)**.

---

## 1. Call-Pattern & Constructor Specialization (Direct Analogs to `ConApp` `PreFlatten`)

These works are the closest direct counterparts in the functional compiler literature to how `ConApp` `PreFlatten` specializes functions on constructor applications at call sites and relies on downstream simplification (`KnownCase` + `Simplify` + `Flatten`) to eliminate both the constructor allocation and the `case` dispatch.

### 1.1 Peyton Jones (2007) — *Call-Pattern Specialisation for Haskell Programs (`SpecConstr`)* *(New Reference — Closest Direct Match)*
- **Citation:** Simon Peyton Jones. In *Proceedings of the 12th ACM SIGPLAN International Conference on Functional Programming (ICFP '07)*, pp. 327–337, Freiburg, Germany, October 2007.
- **What it does:** Introduces GHC's `SpecConstr` pass. Standard strictness-driven worker/wrapper only unpacks arguments that a function evaluates strictly on *every* control-flow path, and cannot unpack multi-variant sum types (`datatype`s like `Option` / `Either` / closure environments) into a single worker signature. `SpecConstr` instead inspects call sites where arguments are explicit constructor applications (e.g., `f (Con1 a b)`). For each distinct call-site constructor pattern, it emits a specialized function `$sf a b` whose body begins by rebinding `let x = Con1 a b in <body of f>`, rewrites matching callers to invoke `$sf a b`, and then relies on GHC's existing simplifier (**case-of-known-constructor**) to fold `case x of Con1 a' b' -> ...` into a direct jump and eliminate the dead allocation `Con1 a b`.
- **Relevance to `ConApp` `PreFlatten`:**
  - **Identical Two-Step Mechanism:** Notice that `SpecConstr`'s mechanism—creating a specialized clone taking the constructor's payload arguments, inserting a re-binding constructor allocation at the entry of the clone (`let x = Con1 a b` $\leftrightarrow$ `bbBind: x = con Con1(t)`), and letting standard downstream passes (`KnownCase` / simplifier) fold the `case` and dead-code-eliminate the `ConApp`—is *architecturally identical* to `PreFlatten`!
  - **Iterative Specialization on Recursive Loops:** Like your iterative step in `PreFlatten` (Section 3.1 / Figure 3.9, where newly emitted specializations are re-analyzed so recursive calls inside `$sf` target `$sf` instead of `f`), `SpecConstr` specifically iterates specialization seeded from loop bodies and call sites to ensure recursive calls stay on the specialized fast path.
  - **Key Differences to Highlight in `related_work.tex`:**
    1. `SpecConstr` operates on a higher-order lazy Core IR and uses usage inspection inside the callee body to filter patterns, whereas `ConApp` `PreFlatten` operates on MLton/MaPLe's *defunctionalized, monomorphic first-order SSA*—meaning `ConApp` `PreFlatten` simultaneously optimizes **user-defined ADTs** and **defunctionalized closure environments** (`Env` datatypes) in one unified pass.
    2. In MaPLe/MLton, eliminating the `ConApp` wrapper exposes the underlying payload `tuple` to the global first-order `Flatten` pass (Figure 3.6), creating a cross-pass synergy between constructor specialization and global SSA tuple flattening.
- **Download / Source URLs:**
  - Microsoft Research Direct PDF: https://www.microsoft.com/en-us/research/wp-content/uploads/2016/07/specconstr.pdf
  - Microsoft Research Publication Page: https://www.microsoft.com/en-us/research/publication/call-pattern-specialisation-for-haskell-programs/
  - ACM Digital Library / DOI: https://doi.org/10.1145/1291151.1291200

### 1.2 Mogensen (1993) — *Constructor Specialization* *(New Reference)*
- **Citation:** Torben Æ. Mogensen. In *Proceedings of the 1993 ACM SIGPLAN Symposium on Partial Evaluation and Semantics-Based Program Manipulation (PEPM '93)*, pp. 22–32, Copenhagen, Denmark, June 1993.
- **What it does:** Formulates **constructor specialization** for a first-order subset of Standard ML with algebraic datatypes. When a constructor application `C(e)` is constructed and passed to functions that pattern-match on it, constructor specialization specializes both the functions and the datatype constructors with respect to statically known constructor tags and static sub-components, stripping away runtime constructor tags and unused `case` branches.
- **Relevance to `ConApp` `PreFlatten`:** Provides the classic partial-evaluation foundation for specializing first-order ML functions on known `datatype` constructors (`Flatten_C`).
- **Download / Source URLs:**
  - ACM Digital Library (Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/154630.154633
  - DOI Landing Page: https://doi.org/10.1145/154630.154633

### 1.3 Peyton Jones & Santos (1998) — *A Transformation-Based Optimiser for Haskell* & Santos (1995) — PhD Dissertation *(New References)*
- **Citations:**
  1. Simon L. Peyton Jones and André L. M. Santos. *A transformation-based optimiser for Haskell*. *Science of Computer Programming*, 32(1–3):3–47, September 1998.
  2. André L. M. Santos. *Compilation by Transformation in Non-Strict Functional Languages*. PhD Thesis, Department of Computing Science, University of Glasgow, Technical Report TR-1995-17, July 1995.
- **What they do:** Define the core local transformation rules of GHC's simplifier, most notably **case-of-known-constructor** (`case (C a b) of { C x y -> e1; ... } ==> e1[a/x, b/y]`) and **case-of-case** (floating a `case` evaluation inward into the branches of an inner `case` so that constructor allocations at the leaves of the inner `case` meet the outer `case` directly and cancel out).
- **Relevance to `ConApp` `PreFlatten`:**
  - Directly parallels how `PreFlatten` pushes `con C(t)` across a call boundary so that MLton's `KnownCase` pass (which is the SSA equivalent of case-of-known-constructor + case-of-case) can fold the `case` dispatch into a direct `goto`.
  - Also supports your core thesis philosophy: keeping interprocedural passes (`PreFlatten`) simple by designing them to expose opportunities for existing local cleanup passes (`KnownCase`, `Simplify`/`Shrink`).
- **Download / Source URLs:**
  - Microsoft Research Publication Page & PDF: https://www.microsoft.com/en-us/research/publication/a-transformation-based-optimiser-for-haskell/
  - Direct PDF Mirror (UT Tartu / Author Archive): https://courses.cs.ut.ee/2014/fop/fall/uploads/Main/transformation-based-optimiser.pdf
  - Elsevier ScienceDirect DOI: https://doi.org/10.1016/S0167-6423(97)00029-4

### 1.4 Maurer, Downen, Ariola, & Peyton Jones (2017) — *Compiling Without Continuations* *(New Reference)*
- **Citation:** Luke Maurer, Paul Downen, Zena M. Ariola, and Simon Peyton Jones. In *Proceedings of the 38th ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI '17)*, pp. 482–494, Barcelona, Spain, June 2017.
- **What it does:** Introduces explicit **join points** (lightweight local tail-called blocks/functions analogous to basic blocks in SSA) into GHC's direct-style Core IR. Shows that when recursive loops or branches return/pass algebraic data types (`Maybe`, `Either`, tuples) into a join point, pushing `case` dispatch across the join-point boundary (and specializing join points via `SpecConstr` + `KnownCase`) eliminates intermediate constructor allocations (`ConApp`s) inside loops without converting the entire compiler to CPS.
- **Relevance to `ConApp` `PreFlatten`:** Directly bridges the GHC transformation world (`SpecConstr` + `KnownCase`) and the MLton/MaPLe SSA world (`Contify` + `KnownCase` + `PreFlatten`). Notably, your `wc-input1` example in Chapter 6 (`case input1 ins of NONE => i | SOME c => loop ...`) is the exact `Maybe`/`option` loop pattern analyzed in this paper!
- **Download / Source URLs:**
  - Microsoft Research Direct PDF: https://www.microsoft.com/en-us/research/wp-content/uploads/2017/03/join-points-pldi17.pdf
  - Microsoft Research Publication Page: https://www.microsoft.com/en-us/research/publication/compiling-without-continuations/
  - ACM Open Access DOI: https://doi.org/10.1145/3062341.3062380

### 1.5 Jonsson & Nordlander (2009, 2010) — *Positive Supercompilation for a Higher-Order Call-by-Value Language* *(New Reference)*
- **Citation (Conference):** Peter A. Jonsson and Johan Nordlander. In *Proceedings of the 36th Annual ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages (POPL '09)*, pp. 277–288, Savannah, GA, January 2009.
- **Citation (Journal):** Peter A. Jonsson and Johan Nordlander. *Logical Methods in Computer Science (LMCS)*, Vol. 6, Issue 3, Paper 23, September 2010.
- **What it does:** Adapts positive supercompilation (Sørensen, Glück, & Jones 1996) to a **strict, call-by-value ML-like functional language** (preserving strict termination/effect semantics). When a function call receives a constructor application `f(C(x))`, the supercompiler drives/pushes the constructor context into `f`, folds the `case` on `C`, and memoizes/folds recursive calls to synthesize a specialized residual function taking `x` directly.
- **Relevance to `ConApp` `PreFlatten`:** Whereas classic supercompilation and deforestation (Wadler 1990) targeted lazy languages where arbitrary inlining is sound, Jonsson & Nordlander specifically address strict ML semantics and show how specializing functions on `ConApp` arguments eliminates intermediate ADT allocations across recursive calls.
- **Download / Source URLs:**
  - arXiv Open Access PDF: https://arxiv.org/pdf/1005.5278.pdf
  - LMCS Open Access Page: https://lmcs.episciences.org/1080
  - POPL '09 ACM DOI: https://doi.org/10.1145/1480881.1480916

---

## 2. Defunctionalization, Flow-Directed Closure Conversion, Polyvariance, and Contification (The MLton / SML Lineage)

In your `related_work.tex` (lines 19–39) and `background.tex` (Section `sec:background_polyvar`), you have `\hl{TODO}` markers discussing how MLton's defunctionalization and `Polyvariance` work and how `ConApp` `PreFlatten` relates to them. These papers give you the exact citations and technical details needed to complete that discussion.

### 2.1 Cejtin, Jagannathan, & Weeks (2000) — *Flow-Directed Closure Conversion for Typed Languages* *(Already in `references.bib` as `mlton-closure-paper`)*
- **Citation:** Henry Cejtin, Suresh Jagannathan, and Stephen Weeks. In *Programming Languages and Systems (ESOP 2000)*, LNCS vol. 1782, pp. 56–71, Springer, March 2000.
- **What it does:** Describes MLton's translation from higher-order `SXML` to first-order `SSA` via flow-directed defunctionalization. Uses a monovariant 0CFA (seeded after `Polyvariance`) to compute, for each higher-order call site and function-typed variable, the set of lambdas that may flow to it. Each merged flow set becomes a first-order `datatype` (`Env`), where each constructor tag identifies one lambda in the flow set and its payload is a tuple of the lambda's free variables; indirect calls become `case` dispatches on the `Env` tag.
- **Relevance to `ConApp` `PreFlatten`:** Whenever 0CFA merges two or more lambdas at a higher-order function parameter (because `Polyvariance` did not duplicate the higher-order function in `SXML`), `ClosureConvert` emits a multi-variant `datatype` and wraps closure arguments in `ConApp`s (`con xEnv_f(t)`). Your `ConApp` `PreFlatten` pass recovers precision *after* closure conversion in `SSA` by specializing the first-order function on the concrete constructor tag $\texttt{Flatten}_{\texttt{xEnv\_f}}$ passed at each call site!
- **Download / Source URLs:**
  - MLton Official References Archive (PDF): http://mlton.org/References.attachments/0003-esop.pdf
  - Purdue Author Archive (PDF): https://www.cs.purdue.edu/homes/suresh/papers/esop00.pdf
  - Springer DOI: https://doi.org/10.1007/3-540-46425-5_5

### 2.2 Wright & Jagannathan (1998) — *Polymorphic Splitting: An Effective Polyvariant Flow Analysis* *(New Reference — Explains MLton's `Polyvariance` Pass!)*
- **Citation:** Andrew K. Wright and Suresh Jagannathan. *ACM Transactions on Programming Languages and Systems (TOPLAS)*, 20(1):166–207, January 1998 (preliminary version in POPL '95: *Effective Flow Analysis for Avoiding Run-Time Checks*).
- **What it does:** Introduces **polymorphic splitting**, which achieves polyvariant control-flow analysis by duplicating/splitting `let`-bound functions for different call contexts before running a simple monovariant 0CFA.
- **Relevance to `ConApp` `PreFlatten` & `background.tex` / `related_work.tex`:**
  - **This is the theoretical foundation of MLton's `Polyvariance` pass** (co-designed by Suresh Jagannathan and Stephen Weeks). In MLton, instead of building a complex polyvariant $k$-CFA engine inside `ClosureConvert`, MLton runs `Polyvariance` on `SXML` (duplicating small higher-order functions at every call site) so that a fast monovariant 0CFA in `ClosureConvert` gets polyvariant precision.
  - **Why `ConApp` `PreFlatten` improves on `Polyvariance`:** As you note in `background.tex` (lines 2599–2606), `Polyvariance` in `SXML` blindly duplicates a higher-order function at *every* call site (bounded by a conservative size/call-count cutoff), even if multiple call sites pass the same closure constructor. By contrast, `ConApp` `PreFlatten` operates *after* defunctionalization in `SSA` and emits **at most one specialization per distinct constructor decision vector $\vec{d}$** (`(f, Flatten_C)`), sharing the specialized function across all callers that pass the same constructor `C`!
- **Download / Source URLs:**
  - Purdue Author Archive (TOPLAS '98 PDF): https://www.cs.purdue.edu/homes/suresh/papers/toplas98.pdf
  - Purdue Author Archive (POPL '95 PDF): https://www.cs.purdue.edu/homes/suresh/papers/popl95.pdf
  - ACM Digital Library DOI: https://doi.org/10.1145/271510.271512

### 2.3 Reynolds (1972, 1998) — *Definitional Interpreters for Higher-Order Programming Languages* & Danvy & Nielsen (2001) — *Defunctionalization at Work* *(New References)*
- **Citations:**
  1. John C. Reynolds. *Definitional Interpreters for Higher-Order Programming Languages*. In *Proceedings of the ACM Annual Conference (ACM '72)*, Vol. 2, pp. 717–740, August 1972. Reprinted with a foreword in *Higher-Order and Symbolic Computation (HOSC)*, 11(4):363–397, December 1998.
  2. Olivier Danvy and Lasse R. Nielsen. *Defunctionalization at Work*. In *Proceedings of the 3rd ACM SIGPLAN International Conference on Principles and Practice of Declarative Programming (PPDP '01)*, pp. 162–174, September 2001 (Extended version: BRICS Research Series RS-01-23, June 2001).
- **What they do:** Reynolds (1972) introduces **defunctionalization**—replacing first-class functions with first-order data type constructors (`ConApp`s carrying free variables) and a first-order `apply` dispatch function (`case`). Danvy & Nielsen (2001) systematically survey defunctionalization across compilers and program transformations, showing how inlining and specializing the `apply` dispatch on statically known constructors recovers direct first-order calls.
- **Download / Source URLs:**
  - Reynolds (1998 HOSC Reprint, CMU / Author Archive PDF): https://www.cs.cmu.edu/~crary/819-f09/Reynolds98.pdf
  - Danvy & Nielsen (2001 BRICS Technical Report RS-01-23 Full PDF): https://www.brics.dk/RS/01/23/BRICS-RS-01-23.pdf
  - Danvy & Nielsen ACM DOI: https://doi.org/10.1145/773184.773202

### 2.4 Bell, Bellegarde, & Hook (1997) — *Type-Driven Defunctionalization* & Tolmach & Oliva (1998) — *From ML to Ada: Strongly-Typed Language Interoperability via Source Translation* *(New References)*
- **Citations:**
  1. Jeffrey M. Bell, Françoise Bellegarde, and James Hook. *Type-Driven Defunctionalization*. In *Proceedings of the Second ACM SIGPLAN International Conference on Functional Programming (ICFP '97)*, pp. 25–37, Amsterdam, June 1997.
  2. Andrew Tolmach and Dino P. Oliva. *From ML to Ada: Strongly-Typed Language Interoperability via Source Translation*. *Journal of Functional Programming*, 8(4):367–412, July 1998.
- **What they do:** Preceded MLton by demonstrating whole-program monomorphisation + type-driven defunctionalization for ML. Tolmach & Oliva (1998) is explicitly cited by Cejtin, Jagannathan, & Weeks (2000) as the closest predecessor to MLton's compilation pipeline; notably, Tolmach & Oliva relied purely on type-based defunctionalization (merging all closures of the same ML arrow type into one giant datatype) and then used post-defunctionalization first-order specialization/inlining to eliminate the `ConApp` tags—which is very close in spirit to `ConApp` `PreFlatten`!
- **Download / Source URLs:**
  - Bell, Bellegarde, & Hook (OHSU Institutional Archive PDF): https://digitalcollections.ohsu.edu/record/2967/files/hook.bell_1997.pdf
  - Bell, Bellegarde, & Hook (ACM Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/258948.258953
  - Tolmach & Oliva (Portland State University Author Archive PS/PDF): https://web.cecs.pdx.edu/~apt/jfp98.ps / Cambridge Core DOI: https://doi.org/10.1017/S0956796898003086

### 2.5 Fluet & Weeks (2001) — *Contification Using Dominators* *(New Reference)*
- **Citation:** Matthew Fluet and Stephen Weeks. In *Proceedings of the Sixth ACM SIGPLAN International Conference on Functional Programming (ICFP '01)*, pp. 2–13, Florence, Italy, September 2001.
- **What it does:** Formalizes MLton's `Contify` pass on the first-order SSA IR. Identifies functions that always return to the same continuation/caller context (using a dominator-tree analysis on the call graph) and transforms them into local basic blocks (`goto` continuations) within the caller function.
- **Relevance to `ConApp` `PreFlatten`:**
  - Explains how MLton's SSA optimizer turns interprocedural control flow into intraprocedural basic-block transfers so local passes (`KnownCase`, `Simplify`, `Flatten`) can operate across former function boundaries.
  - When a function *cannot* be contified (because it is called from multiple non-dominating return contexts) or *cannot* be inlined (e.g., recursive functions or functions exceeding inline thresholds), `KnownCase` alone cannot see across the function call boundary. `ConApp` `PreFlatten` bridges that gap by specializing the function signature on the caller's `ConApp` tag!
- **Download / Source URLs:**
  - MLton Official References Archive (PDF): http://mlton.org/References.attachments/0109-icfp.pdf
  - Cornell Archive Mirror (PDF): https://www.cs.cornell.edu/andru/cs711/2002fa/reading/icfp01.pdf
  - ACM Open Access DOI: https://doi.org/10.1145/507635.507639

---

## 3. Whole-Program Defunctionalized Node Flattening & Unboxing in Functional Backends (GRIN & CPR)

### 3.1 Boquist (1999) — *Code Optimisation Techniques for Lazy Functional Languages* (The GRIN Compiler) & Podlovics, Hruska, & Pénzes (2021) — *A Modern Look at GRIN* *(New References — Remarkable Architectural Parallel!)*
- **Citations:**
  1. Urban Boquist and Thomas Johnsson. *The GRIN Project: A Highly Optimising Back End for Lazy Functional Languages*. In *Implementation of Functional Languages (IFL '96)*, LNCS vol. 1268, pp. 58–84, Springer, 1997.
  2. Urban Boquist. *Code Optimisation Techniques for Lazy Functional Languages*. PhD Thesis, Department of Computing Science, Chalmers University of Technology, April 1999.
  3. Péter Podlovics, Csaba Hruska, and Andor Pénzes. *A Modern Look at GRIN, an Optimizing Functional Language Back End*. *Acta Cybernetica*, 25(4):847–876, 2021.
- **What they do:** In the **GRIN (Graph Reduction Intermediate Notation)** whole-program compiler, all data constructors, closures, and thunks are lowered via whole-program defunctionalization (heap points-to analysis + `eval`/`apply` inlining) into uniform first-order tagged nodes (`C tag [x1, ..., xn]`—i.e., `ConApp`s) and `case` switches over node tags in a monomorphic SSA-like first-order IR. GRIN then runs a suite of small composable transformations:
  - **Arity Raising (Node Flattening):** When a function parameter or return value is determined to have a single known constructor tag `C` (or after specialization), GRIN strips the constructor tag `C` and passes the payload fields `x1, ..., xn` directly in registers.
  - **Case Hoisting / Case Simplification / Producer-Consumer Specialization:** Pushes node constructions into `case` consumers so that `case (C a b) of C x y -> ...` reduces to direct variable bindings without allocating or tagging the node.
- **Relevance to `ConApp` `PreFlatten`:** GRIN is one of the very few compilers outside MLton/MaPLe that compiles a functional language to a **whole-program, defunctionalized, first-order SSA-like IR** where closures and ADTs are both represented as `ConApp` nodes and optimized by stripping known constructor tags across function calls (`Arity Raising` + `Case Simplification`). Comparing MaPLe's `ConApp` `PreFlatten` + `KnownCase` + `Flatten` against GRIN's node-tag elimination and arity raising is an outstanding addition to `related_work.tex`.
- **Download / Source URLs:**
  - Boquist (1999 PhD Thesis Record & Full Text, Chalmers Repository): https://research.chalmers.se/publication/232335
  - Boquist & Johnsson (1996 IFL Paper PDF Mirror): https://github.com/grin-compiler/grin/raw/master/papers/boquist.pdf (and Boquist PhD Thesis PDF hosted by the GRIN project: https://github.com/grin-compiler/grin/raw/master/papers/phd.pdf)
  - Podlovics, Hruska, & Pénzes (2021 Open Access Journal PDF): https://cyber.bibl.u-szeged.hu/index.php/actacyb/article/view/282969/282221 (Landing page: https://doi.org/10.14232/actacyb.282969)

### 3.2 Baker-Finch, Glynn, & Peyton Jones (2004) — *Constructed Product Result Analysis for Haskell* & Graf, Peyton Jones, & Scott (2020) — *Lower Your Guards* *(New References)*
- **Citation:** Clem Baker-Finch, Kevin Glynn, and Simon Peyton Jones. *Journal of Functional Programming*, 14(2):211–245, March 2004.
- **What it does:** Formalizes **Constructed Product Result (CPR)** analysis in GHC, which complements argument worker/wrapper by unboxing *returned* constructor applications (`ConApp`s of single-constructor types and tuples) into unboxed tuples `(# a, b #)` returned in registers.
- **Relevance to `PreFlatten`:** In Section 3.3 (`Comparison with Flatten`, Figure 3.12a–b), you note that `PreFlatten` acts on *call arguments* (directed call edges) rather than *return edges*. Citing CPR analysis (Baker-Finch et al. 2004) alongside GHC's Unboxed Sums shows how return-edge constructor unboxing is handled via worker/wrapper return transformations.
- **Download / Source URLs:**
  - Microsoft Research Direct PDF: https://www.microsoft.com/en-us/research/wp-content/uploads/2004/03/cpr.pdf
  - Microsoft Research Publication Page: https://www.microsoft.com/en-us/research/publication/constructed-product-result-analysis-haskell/
  - Cambridge Core DOI: https://doi.org/10.1017/S0956796803004751

---

## 4. Interprocedural Branch Elimination, Procedure Cloning, and Basic Block Versioning (Imperative, OO, & Dynamic Compilers)

In `related_work.tex` (line 45), you already cite Melançon, Feeley, & Serrano (2024) (`bbv-paper`, *Static Basic Block Versioning*). The papers below provide the broader lineage in imperative, object-oriented, and dynamic compilers for **specializing functions or control-flow paths on statically known tags/constants at call sites so downstream conditional branches/switches fold away**.

### 4.1 Chambers & Ungar (1989, 1990) — *Customization* and *Iterative Type Analysis and Extended Message Splitting* *(New References)*
- **Citations:**
  1. Craig Chambers and David Ungar. *Customization: Optimizing Compiler Technology for SELF, a Dynamically-Typed Object-Oriented Programming Language*. In *Proceedings of the ACM SIGPLAN '89 Conference on Programming Language Design and Implementation (PLDI '89)*, pp. 146–160, June 1989.
  2. Craig Chambers and David Ungar. *Iterative Type Analysis and Extended Message Splitting: Optimizing Dynamically-Typed Object-Oriented Programs*. In *Proceedings of the ACM SIGPLAN '90 Conference on Programming Language Design and Implementation (PLDI '90)*, pp. 150–164, June 1990.
- **What they do:**
  - **Customization (PLDI '89):** Compiles multiple specialized copies of a method, each customized to a specific concrete receiver class/tag observed at call sites, turning dynamic dispatch inside the callee into statically bound jumps.
  - **Extended Message Splitting (PLDI '90):** When one incoming control-flow edge constructs an object with a known tag/map (`ConApp`) and merges with another edge where the tag is unknown, **splitting** duplicates the merge point and subsequent dispatch blocks so the known-tag path bypasses the tag check entirely.
- **Relevance to `ConApp` `PreFlatten` + `KnownCase`:**
  - **Customization** is the direct interprocedural ancestor of specializing a function on a concrete constructor tag $\texttt{Flatten}_C$ at a call site.
  - **Message Splitting** is the direct intraprocedural ancestor of MLton's `KnownCase` pass (and Basic Block Versioning, `bbv-paper`).
- **Download / Source URLs:**
  - PLDI '89 *Customization* (ACM Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/73141.74831
  - PLDI '90 *Iterative Type Analysis and Extended Message Splitting* (ACM Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/93542.93562

### 4.2 Cooper, Hall, & Kennedy (1992, 1993) — *A Methodology for Procedure Cloning* *(New Reference)*
- **Citation:** Keith D. Cooper, Mary W. Hall, and Ken Kennedy. *A Methodology for Procedure Cloning*. *Computer Languages*, 19(2):105–118, February 1993 (earlier version in *Proceedings of the 1992 IEEE International Conference on Computer Languages (ICCL '92)*, pp. 96–105, April 1992).
- **What it does:** Introduces the classic three-phase **procedure cloning** algorithm for imperative/Fortran compilers:
  1. Compute interprocedural descriptors (cloning vectors) describing relevant properties of arguments at each call site (e.g., constant values, alias/shape descriptors);
  2. Partition and merge equivalent descriptors so only one clone is emitted per distinct optimization outcome;
  3. Clone the procedures, redirect call sites, and iterate across the call graph.
- **Relevance to `PreFlatten`:** Your formalization of `PreFlatten` in Figure 3.11—computing per-callsite decision vectors $\vec{d} = \sigma(f, \texttt{callN}) \in \{\texttt{Preserve}, \texttt{Flatten}_C\}^n$, deduplicating clones across callers that share the same $\vec{d} \in \mathcal{D}(F_j)$, and iterating over newly emitted clones—is a clean, type-and-constructor-directed instantiation of Cooper, Hall, & Kennedy's procedure cloning framework!
- **Download / Source URLs:**
  - Rice University Technical Report `CRPC-TR92216` / Author Archive (PDF): https://scholarship.rice.edu/bitstream/handle/1911/96348/TR92-172.pdf (Landing page: https://scholarship.rice.edu/handle/1911/96348)
  - Elsevier DOI: https://doi.org/10.1016/0096-0551(93)90005-L

### 4.3 Bodík, Gupta, & Soffa (1997) — *Interprocedural Conditional Branch Elimination* *(New Reference)*
- **Citation:** Rastislav Bodík, Rajiv Gupta, and Mary Lou Soffa. In *Proceedings of the ACM SIGPLAN 1997 Conference on Programming Language Design and Implementation (PLDI '97)*, pp. 146–158, Las Vegas, NV, June 1997.
- **What it does:** Generalizes intraprocedural jump threading / branch elimination (Mueller & Whalley 1992, 1995) to **interprocedural control flow**. Detects when a conditional branch or switch inside a callee depends on a parameter whose value/tag is statically determined at a specific call site, and clones/separates the procedure entry path for that call site so the branch inside the callee is eliminated at compile time.
- **Relevance to `ConApp` `PreFlatten`:** In an imperative compiler where tagged unions are represented as a struct `{ int tag; void* payload; }`, passing a freshly constructed union (`tag = Con1`) to a function that switches on `tag` is an interprocedural conditional branch elimination problem. Bodík, Gupta, & Soffa solve this via interprocedural demand-driven slicing and procedure cloning; `ConApp` `PreFlatten` achieves the same result for ML `datatype`s with a purely local call-site check because SSA `ConApp` syntax makes constructor creation explicit at the call site.
- **Download / Source URLs:**
  - ACM Digital Library (Open Access PDF): https://dl.acm.org/doi/pdf/10.1145/258915.258929
  - DOI Landing Page: https://doi.org/10.1145/258915.258929

### 4.4 Chevalier-Boisvert & Feeley (2015) — *Simple and Effective Type Check Removal through Lazy Basic Block Versioning* *(New Reference — Companion to `bbv-paper`)*
- **Citation:** Maxime Chevalier-Boisvert and Marc Feeley. In *29th European Conference on Object-Oriented Programming (ECOOP 2015)*, LIPIcs vol. 37, pp. 101–123, Schloss Dagstuhl, July 2015.
- **What it does:** The foundational paper introducing **Basic Block Versioning (BBV)**, which duplicates basic blocks along incoming control-flow edges indexed by known variable tag/type shapes so downstream tag tests fold away without global control-flow analysis.
- **Relevance to `related_work.tex`:** You already cite the ahead-of-time follow-up `bbv-paper` (Melançon, Feeley, & Serrano, ECOOP 2024). Citing Chevalier-Boisvert & Feeley (2015) alongside it provides the origin of basic block versioning.
- **Download / Source URLs:**
  - arXiv Open Access PDF: https://arxiv.org/pdf/1411.0352.pdf
  - Dagstuhl DROPS Open Access PDF: https://drops.dagstuhl.de/storage/00lipics/lipics-vol037-ecoop2015/LIPIcs.ECOOP.2015.101/LIPIcs.ECOOP.2015.101.pdf
  - DOI: https://doi.org/10.4230/LIPIcs.ECOOP.2015.101

---

## 5. Algebraic Data Type (ADT) Memory Layout & Bit-Stealing Optimizations

In `related_work.tex` (lines 41–44), you discuss `local-paper` (Vollmer et al. 2019), `adt4hpc-paper` (Baudon 2024), and `double-steal-paper` (Elsman 2024). Below are the key companion papers and direct download URLs for that cluster, plus how they contrast with `ConApp` `PreFlatten`.

### 5.1 Baudon, Radanne, & Gonnord (2023) — *Bit-Stealing Made Legal: Compilation for Custom Memory Representations of Algebraic Data Types (`Ribbit`)* *(New Reference — Published Paper Behind `adt4hpc-paper`)*
- **Citation:** Thaïs Baudon, Gabriel Radanne, and Laure Gonnord. *Proceedings of the ACM on Programming Languages (PACMPL)*, Vol. 7, Issue ICFP, Article 216, pp. 789–816, August 2023.
- **What it does:** The peer-reviewed ICFP '23 paper from Thaïs Baudon's dissertation (`adt4hpc-paper`). Introduces `Ribbit`, a DSL and compiler transformation that packs ADT tags and nested constructor payloads into customized flat/bit-stolen memory layouts (inlining nested constructors, sharing tag bits in pointers/integers, and unpacking fields) while automatically rewriting pattern matches (`case` compilation) to operate on the packed representation.
- **Relevance to `related_work.tex`:** Currently `related_work.tex` groups `adt4hpc-paper` (Baudon 2024) with `local-paper` (Vollmer et al. 2019) as focusing on "serialized data on disk." While `local-paper` (Gibbon/LoCal) indeed unifies serialized/packed buffers with tree traversals, Baudon's `adt4hpc-paper` and ICFP '23 paper (`Ribbit`) actually focus on **custom in-memory bit-stealing and inline ADT representations** (closer to Elsman's `double-steal-paper`, but user-guided/verified via layout specifications rather than flow-specialized per call site like your `ConApp` `PreFlatten`). Updating that sentence in `related_work.tex` and citing Baudon et al. (ICFP 2023) will make your comparison even sharper and more accurate!
- **Download / Source URLs:**
  - HAL Inria Open Access Archive (PDF): https://inria.hal.science/hal-04165615/document (Landing page: https://inria.hal.science/hal-04165615)
  - Thaïs Baudon PhD Thesis (`adt4hpc-paper`, 2024, HAL Open Access PDF): https://theses.hal.science/tel-04661986/document
  - ACM Open Access DOI: https://doi.org/10.1145/3607858

### 5.2 Elsman (2024) — *Double-Ended Bit-Stealing for Algebraic Data Types* *(Already in `references.bib` as `double-steal-paper`)*
- **Citation:** Martin Elsman. *Proceedings of the ACM on Programming Languages (PACMPL)*, Vol. 8, Issue ICFP, Article 240, pp. 88–120, August 2024.
- **What it does:** Uses unused high-order and low-order bits of 64-bit machine words in the MLKit Standard ML compiler to pack constructor tags and unbox single-word/small ADT payloads into a single 64-bit word without breaking uniform polymorphism.
- **Download / Source URLs:**
  - ACM Open Access PDF: https://dl.acm.org/doi/pdf/10.1145/3674629
  - DOI Landing Page: https://doi.org/10.1145/3674629

### 5.3 Vollmer, Koparkar, Rainey, Sakka, Kulkarni, & Newton (2019) — *LoCal: A Language for Programs Operating on Serialized Data* *(Already in `references.bib` as `local-paper`)* & Vollmer et al. (2017) — *Compiling Tree Transforms to Operate on Packed Representations*
- **Citations:**
  1. Michael Vollmer, Sarah Spall, Berthold Reinwald, Milind Kulkarni, and Ryan R. Newton. *Compiling Tree Transforms to Operate on Packed Representations*. In *31st European Conference on Object-Oriented Programming (ECOOP 2017)*, LIPIcs vol. 74, Article 26, 2017.
  2. Michael Vollmer, Chaitanya Koparkar, Mike Rainey, Laith Sakka, Milind Kulkarni, and Ryan R. Newton. *LoCal: A Language for Programs Operating on Serialized Data*. In *Proceedings of the 40th ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI '19)*, pp. 48–62, June 2019.
- **Download / Source URLs:**
  - PLDI '19 `LoCal` Paper (arXiv Open Access PDF): https://arxiv.org/pdf/1904.06833.pdf
  - PLDI '19 ACM Open Access DOI: https://doi.org/10.1145/3314221.3314631
  - ECOOP '17 Gibbon Paper (Dagstuhl Open Access PDF): https://drops.dagstuhl.de/storage/00lipics/lipics-vol074-ecoop2017/LIPIcs.ECOOP.2017.26/LIPIcs.ECOOP.2017.26.pdf

---

## 6. How Other Production Compilers Handle `ConApp` Flattening & Known-Constructor Specialization (Official Documentation & Source Links)

### 6.1 MLton (`Polyvariance`, `ClosureConvert`, `Contify`, `KnownCase`, `SimplifyTypes`, `Useless`)
- **Documentation & Source URLs:**
  - `Polyvariance` Pass Docs (`SXML`): http://mlton.org/Polyvariance
  - `ClosureConvert` Pass Docs (`SXML -> SSA`): http://mlton.org/ClosureConvert
  - `Contify` Pass Docs (`SSA`): http://mlton.org/Contify
  - `KnownCase` Pass Docs (`SSA`): http://mlton.org/KnownCase
  - `SimplifyTypes` Pass Docs (`SSA` — turns 1-variant datatypes into transparent newtypes/tuples): http://mlton.org/SimplifyTypes
  - MLton Source (`known-case.fun`): https://github.com/MLton/mlton/blob/master/mlton/ssa/known-case.fun
  - MLton Source (`polyvariance.fun`): https://github.com/MLton/mlton/blob/master/mlton/xml/polyvariance.fun
- **How MLton handles `ConApp`s without `PreFlatten`:**
  - Before `SSA`, `Polyvariance` duplicates small higher-order functions in `SXML`. If all closures reaching a function parameter come from a single syntactic lambda, `ClosureConvert` produces a single-variant `datatype`, which `SimplifyTypes` collapses into a plain tuple so `Flatten` can unbox it.
  - Inside a single `SSA` function, `KnownCase` duplicates basic blocks when a `case` scrutinee's constructor is statically known on an incoming basic-block edge.
  - **What MLton misses (and `ConApp` `PreFlatten` fixes):** Once in `SSA`, MLton's `KnownCase` is strictly *intraprocedural*. If a `ConApp` (whether from a user `datatype` like `SOME x` or a multi-variant closure environment `Env`) is passed across a non-inlined, non-contified function call, neither `KnownCase` nor `Flatten` can eliminate the `ConApp` or flatten its payload tuple. `ConApp` `PreFlatten` bridges this interprocedural boundary.

### 6.2 Glasgow Haskell Compiler (GHC: `SpecConstr`, Case-of-Known-Constructor, Unboxed Sums `(# a | b #)`)
- **Documentation & Source URLs:**
  - GHC User's Guide — `-fspec-constr` & Optimization Flags: https://downloads.haskell.org/ghc/latest/docs/users_guide/using-optimisation.html#ghc-flag--fspec-constr
  - GHC User's Guide — Unboxed Sums (`-XUnboxedSums`, `(# t1 | t2 #)`): https://downloads.haskell.org/ghc/latest/docs/users_guide/exts/primitives.html#unboxed-sums
  - GHC Developer Wiki — `SpecConstr` Pass Design: https://gitlab.haskell.org/ghc/ghc/-/wikis/spec-constr
  - GHC Source (`GHC/Core/Opt/SpecConstr.hs`): https://gitlab.haskell.org/ghc/ghc/-/blob/master/compiler/GHC/Core/Opt/SpecConstr.hs
  - GHC Source (`GHC/Stg/Unarise.hs` — lowers unboxed sums and tuples to flat register args): https://gitlab.haskell.org/ghc/ghc/-/blob/master/compiler/GHC/Stg/Unarise.hs
- **How GHC handles `ConApp` flattening:**
  - **Interprocedural (`SpecConstr`):** Specializes recursive functions on constructor application arguments (`ConApp`s), passing the constructor fields as separate arguments and letting the Core simplifier fold `case`-of-known-constructor.
  - **Calling Convention (`UnboxedSums`):** Provides first-class unboxed sum types `(# a | b #)` that lower via `Unarise` into a flat tag register plus shared payload registers without heap allocation.

### 6.3 OCaml (`Flambda` / `Flambda 2` & Jane Street `OxCaml`)
- **Documentation & Source URLs:**
  - OCaml Manual — Flambda Optimizer (inlining, specialization, and block unboxing): https://ocaml.org/manual/latest/flambda.html
  - Flambda 2 Documentation & Architecture (`ocaml-flambda/flambda-backend`): https://github.com/ocaml-flambda/flambda-backend/tree/main/middle_end/flambda2
  - OxCaml Documentation — Unboxed Types & Layouts (including `or_null` unboxed `option`-like constructors): https://oxcaml.org/documentation/unboxed-types/
- **How OCaml handles `ConApp` flattening:**
  - **Flambda 2 (`Simplify` + Abstract Value Approximations):** Tracks exact variant tag and field approximations across CPS continuations and function inlining, folding switches (`KnownCase`) and eliminating dead variant block allocations when the variant does not escape.
  - **OxCaml (`or_null` and unboxed layouts):** Eliminates the boxed constructor allocation for `option`-like sum types (`Foo of t | Null`) by representing the tag as a null pointer bit-pattern while keeping `t` unboxed.

### 6.4 LLVM (`FunctionSpecialization`, `IPSCCP`, `JumpThreading`, `SROA`)
- **Documentation & Source URLs:**
  - LLVM `FunctionSpecialization` Pass (`llvm/lib/Transforms/IPO/FunctionSpecialization.cpp`): https://github.com/llvm/llvm-project/blob/main/llvm/lib/Transforms/IPO/FunctionSpecialization.cpp
  - LLVM `JumpThreading` Pass (`llvm/lib/Transforms/Scalar/JumpThreading.cpp`): https://github.com/llvm/llvm-project/blob/main/llvm/lib/Transforms/Scalar/JumpThreading.cpp
  - LLVM `ArgumentPromotion` Pass (`llvm/lib/Transforms/IPO/ArgumentPromotion.cpp`): https://github.com/llvm/llvm-project/blob/main/llvm/lib/Transforms/IPO/ArgumentPromotion.cpp
- **How LLVM handles `ConApp`-like tagged unions across calls:**
  - When a tagged union (e.g. a Rust `enum` or C++ `std::variant`/`std::optional`) is passed to a function, LLVM relies on a combination of **`SROA` / `ArgumentPromotion`** (to split `{ i8 tag, Payload }` into separate scalar/register parameters) and **`FunctionSpecialization` / `IPSCCP`** (to clone functions when a constant tag parameter is passed at a call site), followed by **`JumpThreading` / `SimplifyCFG`** (the intraprocedural equivalent of MLton's `KnownCase`) to fold the `switch` on the tag.
  - Because LLVM operates after high-level ADT structure has been lowered to raw bytes, stack `alloca`s, and `memcpy`s, LLVM often fails to specialize multi-word tagged unions unless the function is fully inlined—highlighting the advantage of running `ConApp` `PreFlatten` on a typed SSA IR where `ConApp` and `case` are still explicit primitives!

### 6.5 Rust (`rustc` MIR Optimizations: `JumpThreading`, `SROA`, and Niche/ScalarPair Enum Layouts)
- **Documentation & Source URLs:**
  - Rust Compiler Dev Guide — MIR Optimizations: https://rustc-dev-guide.rust-lang.org/mir/optimizations.html
  - `rustc` MIR `JumpThreading` (folds `SwitchInt` on known `enum` discriminants across basic blocks): https://github.com/rust-lang/rust/blob/master/compiler/rustc_mir_transform/src/jump_threading.rs
  - `rustc` Type Layout & Niche Optimization (`Variants::Multiple` & `PassMode::Pair`): https://doc.rust-lang.org/nightly/nightly-rustc/rustc_abi/index.html
- **How Rust handles `ConApp` (`enum` variant) overhead:**
  - **ABI Layout (`Scalar` / `ScalarPair` with Niches):** For small enums like `Option<&T>`, `Option<NonZeroU64>`, or `Result<u32, u32>`, `rustc` packs the variant discriminant and payload into 1 or 2 machine registers (`PassMode::Direct` / `PassMode::Pair`).
  - **MIR `JumpThreading`:** Tracks known discriminant values assigned via `AggregateKind::Adt` (`ConApp`) and threads jumps directly to the matching `SwitchInt` target arm (`KnownCase`).

---

## 7. Quick-Reference Guide for Updating `\section{ConApp Flattening}` in `latex/chapters/related_work.tex`

| Topic in `related_work.tex` | Papers to Cite | Key Point to Make in the Text |
| :--- | :--- | :--- |
| **Direct functional compiler analog to `ConApp` `PreFlatten`** | **Peyton Jones (2007)** (`specconstr-paper`); **Peyton Jones & Santos (1998)** (`ghc-optimiser-1998`); **Maurer et al. (2017)** (`join-points-2017`) | GHC's `SpecConstr` is the closest counterpart to `ConApp` `PreFlatten`: it specializes functions on call-site constructor patterns (`ConApp`s), rebinds the constructor at the entry of the specialized clone, and relies on `case`-of-known-constructor (`KnownCase`) to eliminate the allocation and dispatch. Unlike `SpecConstr` (which operates on higher-order lazy Core), `ConApp` `PreFlatten` runs on defunctionalized first-order SSA, simultaneously optimizing user ADTs and closure environments and exposing payload tuples to global `Flatten`. |
| **Defunctionalization, `Polyvariance`, and `Contify` (finishing the `\hl{TODO}` on lines 19–39)** | **Cejtin, Jagannathan, & Weeks (2000)** (`mlton-closure-paper`); **Wright & Jagannathan (1998)** (`polymorphic-splitting-1998`); **Reynolds (1972/1998)** (`reynolds-defunc`); **Tolmach & Oliva (1998)** (`tolmach-oliva-1998`); **Fluet & Weeks (2001)** (`contify-paper`) | MLton's `ClosureConvert` uses monovariant 0CFA after `Polyvariance` (polymorphic splitting) to defunctionalize closures into `Env` datatypes (`ConApp`s) and `case` dispatches. Whereas `Polyvariance` blindly duplicates higher-order functions per call site in `SXML`, `ConApp` `PreFlatten` specializes functions post-defunctionalization in `SSA` per distinct constructor tag $\texttt{Flatten}_C$, deduplicating clones across callers that pass the same closure variant. |
| **Whole-program first-order node/tag flattening** | **Boquist (1999)** (`boquist-grin-thesis`); **Podlovics, Hruska, & Pénzes (2021)** (`modern-grin-2021`) | Like MLton, the GRIN compiler defunctionalizes closures/thunks and ADTs into uniform tagged nodes (`ConApp`s) in a whole-program first-order IR, and eliminates known constructor tags across function calls via interprocedural arity raising and case simplification. |
| **Partial evaluation & supercompilation on constructors** | **Mogensen (1993)** (`mogensen-con-spec`); **Jonsson & Nordlander (2009)** (`cbv-supercomp-2009`) | Constructor specialization and call-by-value positive supercompilation also push constructor applications across function calls to fold `case` dispatches, though as heavyweight whole-program symbolic evaluation passes rather than a lightweight local call-site pass. |
| **Imperative/OO/Dynamic procedure cloning & branch/tag elimination** | **Cooper, Hall, & Kennedy (1993)** (`procedure-cloning-1993`); **Bodík, Gupta, & Soffa (1997)** (`interproc-branch-elim-1997`); **Chambers & Ungar (1989, 1990)** (`self-customization-1989`, `self-splitting-1990`); **Chevalier-Boisvert & Feeley (2015)** (`lbbv-2015`); **Melançon et al. (2024)** (`bbv-paper`) | Connects `PreFlatten`'s decision vectors $\vec{d}$ to Cooper et al.'s procedure cloning, Bodík et al.'s interprocedural conditional branch elimination, and Chambers & Ungar's customization + message splitting. |
| **ADT representation & bit-stealing (refining lines 41–44)** | **Baudon, Radanne, & Gonnord (2023)** (`ribbit-2023`); **Baudon (2024)** (`adt4hpc-paper`); **Elsman (2024)** (`double-steal-paper`); **Vollmer et al. (2019)** (`local-paper`) | Clarifies that `local-paper` (Gibbon/LoCal) packs recursive ADTs into serialized contiguous buffers, whereas `ribbit-2023`/`adt4hpc-paper` and `double-steal-paper` compact in-memory ADT tags via bit-stealing and layout descriptors rather than eliminating the ADT tag altogether via call-site specialization. |

---

## 8. Ready-to-Paste BibTeX Entries for `latex/references.bib`

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

@article{ghc-optimiser-1998,
  author    = {Peyton Jones, Simon L. and Santos, Andr{\'e} L. M.},
  title     = {A transformation-based optimiser for {Haskell}},
  journal   = {Science of Computer Programming},
  volume    = {32},
  number    = {1--3},
  pages     = {3--47},
  year      = {1998},
  publisher = {Elsevier},
  doi       = {10.1016/S0167-6423(97)00029-4},
  url       = {https://www.microsoft.com/en-us/research/publication/a-transformation-based-optimiser-for-haskell/}
}

@inproceedings{join-points-2017,
  author    = {Maurer, Luke and Downen, Paul and Ariola, Zena M. and Peyton Jones, Simon},
  title     = {Compiling without continuations},
  booktitle = {Proceedings of the 38th ACM SIGPLAN Conference on Programming Language Design and Implementation (PLDI '17)},
  pages     = {482--494},
  year      = {2017},
  publisher = {ACM},
  doi       = {10.1145/3062341.3062380},
  url       = {https://www.microsoft.com/en-us/research/wp-content/uploads/2017/03/join-points-pldi17.pdf}
}

@inproceedings{mogensen-con-spec,
  author    = {Mogensen, Torben {\AE}.},
  title     = {Constructor specialization},
  booktitle = {Proceedings of the 1993 ACM SIGPLAN Symposium on Partial Evaluation and Semantics-Based Program Manipulation (PEPM '93)},
  pages     = {22--32},
  year      = {1993},
  publisher = {ACM},
  doi       = {10.1145/154630.154633},
  url       = {https://dl.acm.org/doi/pdf/10.1145/154630.154633}
}

@inproceedings{cbv-supercomp-2009,
  author    = {Jonsson, Peter A. and Nordlander, Johan},
  title     = {Positive supercompilation for a higher order call-by-value language},
  booktitle = {Proceedings of the 36th Annual ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages (POPL '09)},
  pages     = {277--288},
  year      = {2009},
  publisher = {ACM},
  doi       = {10.1145/1480881.1480916},
  url       = {https://arxiv.org/pdf/1005.5278.pdf}
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
  doi       = {10.1145/271510.271512},
  url       = {https://www.cs.purdue.edu/homes/suresh/papers/toplas98.pdf}
}

@article{reynolds-defunc,
  author    = {Reynolds, John C.},
  title     = {Definitional interpreters for higher-order programming languages},
  journal   = {Higher-Order and Symbolic Computation},
  volume    = {11},
  number    = {4},
  pages     = {363--397},
  year      = {1998},
  note      = {Reprinted from the Proceedings of the 25th ACM National Conference, 1972},
  doi       = {10.1023/A:1010027404223},
  url       = {https://www.cs.cmu.edu/~crary/819-f09/Reynolds98.pdf}
}

@inproceedings{danvy-defunc-work,
  author    = {Danvy, Olivier and Nielsen, Lasse R.},
  title     = {Defunctionalization at work},
  booktitle = {Proceedings of the 3rd ACM SIGPLAN International Conference on Principles and Practice of Declarative Programming (PPDP '01)},
  pages     = {162--174},
  year      = {2001},
  publisher = {ACM},
  doi       = {10.1145/773184.773202},
  url       = {https://www.brics.dk/RS/01/23/BRICS-RS-01-23.pdf}
}

@inproceedings{bell-type-defunc-1997,
  author    = {Bell, Jeffrey M. and Bellegarde, Fran{\c{c}}oise and Hook, James},
  title     = {Type-driven defunctionalization},
  booktitle = {Proceedings of the Second ACM SIGPLAN International Conference on Functional Programming (ICFP '97)},
  pages     = {25--37},
  year      = {1997},
  publisher = {ACM},
  doi       = {10.1145/258948.258953},
  url       = {https://dl.acm.org/doi/pdf/10.1145/258948.258953}
}

@article{tolmach-oliva-1998,
  author    = {Tolmach, Andrew and Oliva, Dino P.},
  title     = {From {ML} to {Ada}: Strongly-typed language interoperability via source translation},
  journal   = {Journal of Functional Programming},
  volume    = {8},
  number    = {4},
  pages     = {367--412},
  year      = {1998},
  publisher = {Cambridge University Press},
  doi       = {10.1017/S0956796898003086}
}

@inproceedings{contify-paper,
  author    = {Fluet, Matthew and Weeks, Stephen},
  title     = {Contification using dominators},
  booktitle = {Proceedings of the Sixth ACM SIGPLAN International Conference on Functional Programming (ICFP '01)},
  pages     = {2--13},
  year      = {2001},
  publisher = {ACM},
  doi       = {10.1145/507635.507639},
  url       = {http://mlton.org/References.attachments/0109-icfp.pdf}
}

@phdthesis{boquist-grin-thesis,
  author    = {Boquist, Urban},
  title     = {Code Optimisation Techniques for Lazy Functional Languages},
  school    = {Chalmers University of Technology},
  address   = {G{\"o}teborg, Sweden},
  year      = {1999},
  month     = apr,
  url       = {https://research.chalmers.se/publication/232335}
}

@article{modern-grin-2021,
  author    = {Podlovics, P{\'e}ter and Hruska, Csaba and P{\'e}nzes, Andor},
  title     = {A modern look at {GRIN}, an optimizing functional language back end},
  journal   = {Acta Cybernetica},
  volume    = {25},
  number    = {4},
  pages     = {847--876},
  year      = {2021},
  doi       = {10.14232/actacyb.282969},
  url       = {https://cyber.bibl.u-szeged.hu/index.php/actacyb/article/view/282969/282221}
}

@article{cpr-paper-2004,
  author    = {Baker-Finch, Clem and Glynn, Kevin and Peyton Jones, Simon},
  title     = {Constructed product result analysis for {Haskell}},
  journal   = {Journal of Functional Programming},
  volume    = {14},
  number    = {2},
  pages     = {211--245},
  year      = {2004},
  publisher = {Cambridge University Press},
  doi       = {10.1017/S0956796803004751},
  url       = {https://www.microsoft.com/en-us/research/wp-content/uploads/2004/03/cpr.pdf}
}

@article{procedure-cloning-1993,
  author    = {Cooper, Keith D. and Hall, Mary W. and Kennedy, Ken},
  title     = {A methodology for procedure cloning},
  journal   = {Computer Languages},
  volume    = {19},
  number    = {2},
  pages     = {105--118},
  year      = {1993},
  publisher = {Elsevier},
  doi       = {10.1016/0096-0551(93)90005-L},
  url       = {https://scholarship.rice.edu/handle/1911/96348}
}

@inproceedings{interproc-branch-elim-1997,
  author    = {Bod{\'\i}k, Rastislav and Gupta, Rajiv and Soffa, Mary Lou},
  title     = {Interprocedural conditional branch elimination},
  booktitle = {Proceedings of the ACM SIGPLAN 1997 Conference on Programming Language Design and Implementation (PLDI '97)},
  pages     = {146--158},
  year      = {1997},
  publisher = {ACM},
  doi       = {10.1145/258915.258929},
  url       = {https://dl.acm.org/doi/pdf/10.1145/258915.258929}
}

@inproceedings{self-customization-1989,
  author    = {Chambers, Craig and Ungar, David},
  title     = {Customization: Optimizing compiler technology for {SELF}, a dynamically-typed object-oriented programming language},
  booktitle = {Proceedings of the ACM SIGPLAN '89 Conference on Programming Language Design and Implementation (PLDI '89)},
  pages     = {146--160},
  year      = {1989},
  publisher = {ACM},
  doi       = {10.1145/73141.74831},
  url       = {https://dl.acm.org/doi/pdf/10.1145/73141.74831}
}

@inproceedings{self-splitting-1990,
  author    = {Chambers, Craig and Ungar, David},
  title     = {Iterative type analysis and extended message splitting: Optimizing dynamically-typed object-oriented programs},
  booktitle = {Proceedings of the ACM SIGPLAN '90 Conference on Programming Language Design and Implementation (PLDI '90)},
  pages     = {150--164},
  year      = {1990},
  publisher = {ACM},
  doi       = {10.1145/93542.93562},
  url       = {https://dl.acm.org/doi/pdf/10.1145/93542.93562}
}

@inproceedings{lbbv-2015,
  author    = {Chevalier-Boisvert, Maxime and Feeley, Marc},
  title     = {Simple and effective type check removal through lazy basic block versioning},
  booktitle = {29th European Conference on Object-Oriented Programming (ECOOP 2015)},
  series    = {Leibniz International Proceedings in Informatics (LIPIcs)},
  volume    = {37},
  pages     = {101--123},
  year      = {2015},
  publisher = {Schloss Dagstuhl -- Leibniz-Zentrum f{\"u}r Informatik},
  doi       = {10.4230/LIPIcs.ECOOP.2015.101},
  url       = {https://arxiv.org/pdf/1411.0352.pdf}
}

@article{ribbit-2023,
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
  url       = {https://inria.hal.science/hal-04165615/document}
}
```
