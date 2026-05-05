## Martin Fowler — Refactoring & Enterprise Patterns

**Sources:**
- Martin Fowler, *Refactoring: Improving the Design of Existing Code* (2nd ed.), Addison-Wesley (2018)
- Martin Fowler, *Patterns of Enterprise Application Architecture*, Addison-Wesley (2002)

*Expert scored in `architecture-specialists.md`. Classification: Canonical (avg 4.8). Work scores for Refactoring and PoEAA are also canonical in `architecture-specialists.md` — Refactoring: Canonical (avg 4.75); PoEAA: Established (avg 4.25). Load canonical scores from that file; do not re-score independently.*

**Activation signals:** Code smell identification, refactoring strategy, legacy modernisation, enterprise patterns (Repository, Unit of Work, Domain Model, Transaction Script, Active Record), pattern recognition in existing codebases

**Role in site survey:** Pattern recognition — identifies which enterprise/application patterns are in use, detects code smells and structural drift.

**Key techniques to apply:**

- **Code smell catalogue** (Refactoring Ch. 3): Recognise structural problems — long methods, feature envy, data clumps, shotgun surgery, divergent change. Each smell has a corresponding refactoring.
- **Refactoring catalogue** (Refactoring Ch. 6-12): Named, mechanical transformations — extract method, move field, replace conditional with polymorphism. The name is the retrieval key; the steps are in training data.
- **Enterprise patterns** (PoEAA): Domain Model vs Transaction Script vs Active Record. The choice shapes the entire architecture. Repository pattern for data access abstraction. Unit of Work for transactional boundaries.
- **Strangler fig** (blog): Incremental replacement of legacy systems by routing requests to new implementations one feature at a time. Key migration pattern.
