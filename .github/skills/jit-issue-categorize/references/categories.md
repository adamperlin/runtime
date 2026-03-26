# JIT Issue Categories and Themes

This reference defines the canonical lists of **categories** and **themes** used
to classify JIT (`area-CodeGen-coreclr`) issues in `dotnet/runtime`.

- A **category** describes *what kind of work* the issue represents.
- A **theme** describes *which JIT subsystem or area* the issue relates to.

Every issue must be assigned exactly one category and at least one theme.

---

## Categories

| Category | Description |
|----------|-------------|
| `cq` | Code quality -- the JIT produces suboptimal machine code for a given pattern. |
| `basic-cq` | Basic code quality -- simple, low-hanging missed optimizations. |
| `correctness` | The JIT produces incorrect results, crashes, asserts, or miscompiles. |
| `performance` | Runtime performance regression or improvement opportunity. |
| `throughput` | JIT compilation throughput -- CPU time or memory consumed during JIT invocation. |
| `implementation` | Request to implement a new feature or add support for a construct. |
| `proposal` | API or design proposal for a new capability. |
| `design` | Architectural or design discussion, RFC, or refactoring plan. |
| `planning` | Tracking issue, roadmap item, or planning discussion. |
| `eng-sys` | Engineering systems: CI, dev tooling, testing infrastructure, code analysis. |
| `documentation` | Documentation improvements (code comments, design docs, READMEs). |
| `testing` | Test coverage, test infrastructure, or stress testing improvements. |
| `question` | A question about JIT behavior, not a bug or feature request. |
| `reach` | Stretch goal or long-term aspirational improvement. |
| `security` | Security-related issue (CVE, vulnerability, hardening). |

### How to pick a category

1. Check the issue's existing GitHub labels first (`bug` -> `correctness`,
   `tenet-performance` -> `performance`, `api-suggestion` -> `proposal`,
   `question` -> `question`, `documentation` -> `documentation`).
2. Read the issue title and body for signal words (see the heuristics table in
   `SKILL.md`).
3. If the issue describes wrong output or a crash, use `correctness`.
4. If the issue describes suboptimal codegen without a correctness problem,
   use `cq` (or `basic-cq` if it is a simple, well-understood missed
   optimization).
5. If the issue is about JIT compilation speed or memory, use `throughput`.
6. When in doubt between `implementation` and `proposal`, use `proposal` if
   there is an API surface change, `implementation` otherwise.

---

## Themes

Themes map to JIT subsystems, optimization passes, or cross-cutting concerns.
An issue may relate to multiple themes -- list the most specific one first.

The following is the complete list of valid themes:

- md-arrays
- cse
- super-pmi
- redundant-branches
- loop-opt
- lower
- expression-opts
- vector-codegen
- basic-cq
- tiering
- gc-info
- optimization
- jit-ee-interface
- stack-allocation
- addressing-modes
- register-allocator
- profile-feedback
- floating-point
- delegates
- ir
- assertion-prop
- memory-usage
- codegen
- calling-convention
- bitset
- benchmarks
- tail-call
- inlining
- ready-to-run
- importer
- bounds-checks
- big-bets
- build
- throughput
- structs
- intrinsics
- devirtualization
- eh
- value-numbering
- div-mod-rem
- emitter
- runtime
- pinning
- testing
- debug-dumps
- generics
- zero-init
- pinvoke
- verification
- type-intrinsics
- block-layout
- null-checks
- block-opts
- alignment
- needs-triage
- managed-c++
- ssa
- asmdiffs
- dead-code
- altjit
- hardware-intrinsics
- jit-block-layout
- liveness
- prolog-epilog
- range-check
- gc-stress
- osr
- jit-coding-style
- debug-info
- boxing
- copy-prop
- ngen
- barriers
- msil
- minopts
- morph
- switches
- volatile
- varargs
- flowgraph
- large-methods
- helpers
- range-checks
- invalid-il
- long-type
- ref-counts
- interpreter

### How to pick a theme

1. Check the issue's existing GitHub labels -- many JIT issues already carry
   theme-equivalent labels (e.g., `optimization-inlining` -> `inlining`).
2. Scan the issue title and body for subsystem names.
3. If the issue spans multiple subsystems, list the primary one first,
   separated by semicolons in the CSV output.
4. Use `needs-triage` only as a last resort when no theme can be determined.
