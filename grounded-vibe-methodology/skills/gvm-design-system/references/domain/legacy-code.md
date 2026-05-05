## Michael Feathers — Legacy Code & Testability

**Source:** Michael Feathers, *Working Effectively with Legacy Code*, Prentice Hall (2004)

**Expert scores:**

| Expert | A | P | B | Ad | C | Avg | Tier |
|---|---|---|---|---|---|---|---|
| Michael Feathers | 4 | 3 | 3 | 4 | 3 | **3.4** | **Recognised** |

| Work | S | De | C | I | Avg | Tier |
|---|---|---|---|---|---|---|
| Feathers, *Working Effectively with Legacy Code* | 5 | 5 | 3 | 4 | **4.25** | **Established** |

**Evidence:** Authority — created legacy code assessment discipline. Adoption — required at ThoughtWorks. Work Specificity — named techniques per dependency pattern. Work Depth — 400+ pages C++, Java, C#.

**Activation signals:** Legacy codebase assessment, testability analysis, introducing tests to untested code, seam identification, change risk evaluation, characterisation testing

**Role in site survey:** Legacy assessment — identifies seams, characterises testability, evaluates coupling and change risk.

**Key techniques to apply:**

- **The Legacy Code Dilemma** (Ch. 2): To change code safely you need tests, but to add tests you often need to change code. Breaking this cycle is the central challenge.
- **Seam identification** (Ch. 4): A seam is a place where behaviour can be altered without editing the code at that point. Object seams, preprocessing seams, and link seams. Finding seams is the first step to testability.
- **Characterisation tests** (Ch. 13): Tests that document what the code actually does (not what it should do). Write these before refactoring to detect unintended changes.
- **Sprout method/class** (Ch. 6): When you need to add new behaviour to untested code, write the new code in a new method or class that can be tested independently, then call it from the legacy code.
- **Wrap method/class** (Ch. 7): Wrap existing behaviour to add pre/post processing without modifying the original code. Preserves existing behaviour while adding new capabilities.
- **Breaking dependencies** (Ch. 9-24): Techniques for making tightly coupled code testable — extract interface, parameterise constructor, subclass and override method. Each technique targets a specific dependency pattern.
