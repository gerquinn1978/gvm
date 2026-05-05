# Stack Tooling Reference

Per-technology commands for dependency verification, linting, static analysis, formatting, property-based testing, and mutation testing. Used by `/gvm-build` during quality pipeline steps and by `/gvm-test` for optional mutation testing on critical-path code.

## How This File Is Used

1. `/gvm-tech-spec` decides the technology stack
2. `/gvm-build` reads this file and matches the project's stack to entries below
3. For each quality step, the matching commands are run via the Bash tool
4. If the project's stack has no entry here, the **Discovery Process** (bottom of file) activates

## Credential Scanning (All Stacks)

Credential scanning is language-agnostic — run on every chunk regardless of stack.

```bash
# Preferred: gitleaks (fast, low false-positive rate, JSON output)
gitleaks detect --source {project_root} --no-git -f json

# Alternative: trufflehog (deeper analysis, slower)
trufflehog filesystem {project_root} --json
```
Install: `brew install gitleaks` or `go install github.com/gitleaks/gitleaks/v8@latest`

If neither tool is available, use grep as a fallback:
```bash
# Catches common patterns — high false-positive rate but better than nothing
grep -rn -E '(password|secret|api_key|token|credential)\s*=\s*["\x27][^"\x27]{8,}' {files}
grep -rn -E '(AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|sk-[a-zA-Z0-9]{48})' {files}
```

Any detection is a hard block. Remove the credential and replace with an environment variable or config lookup before proceeding.

---

## Command Conventions

- All commands target **chunk files only**, not the entire codebase (use `{files}` placeholder)
- Exit code 0 = pass, non-zero = fail
- Commands assume tools are installed. If a tool is missing, attempt auto-install using the install command. If install fails (permissions, network), note in handover and proceed — do not block the build
- Security findings at HIGH or CRITICAL severity block progression
- Complexity findings are flagged to the user but do not block

---

## Python

### Dependency Verification
```bash
# For each NEW import added in this chunk:
python3 -c "import {package}"
# Exit code 0 = package exists. Non-zero = possibly hallucinated.
```

### Lint & Format
```bash
ruff check --fix {files}
ruff format {files}
```
Install: `pip install ruff`

### Static Analysis — Security
```bash
bandit -r {files} -f json
```
Install: `pip install bandit`

### Static Analysis — Complexity
```bash
radon cc -s -n C {files}
```
Install: `pip install radon`

### Static Analysis — Type Checking
```bash
mypy {files} --ignore-missing-imports
```
Install: `pip install mypy`

### Property-Based Testing
```python
from hypothesis import given, strategies as st

@given(st.integers(), st.integers())
def test_addition_commutative(a, b):
    assert add(a, b) == add(b, a)
```
Install: `pip install hypothesis`

### Mutation Testing
```bash
mutmut run --paths-to-mutate {files}
mutmut results
```
Install: `pip install mutmut`

---

## TypeScript / JavaScript

### Dependency Verification
```bash
# For each NEW require/import added in this chunk:
node -e "require('{package}')"
# Exit code 0 = package exists. Non-zero = possibly hallucinated.
```

### Lint & Format
```bash
npx tsc --noEmit          # type check (TypeScript only)
npx prettier --write {files}
```

### Static Analysis — Security
```bash
npx eslint --plugin security {files}
```
Install: `npm install -D eslint-plugin-security`

### Static Analysis — Complexity
```bash
npx eslint --rule 'complexity: [error, 10]' {files}
```

### Property-Based Testing
```typescript
import * as fc from 'fast-check';

test('sort is idempotent', () => {
  fc.assert(fc.property(fc.array(fc.integer()), (arr) => {
    const sorted = sort(arr);
    expect(sort(sorted)).toEqual(sorted);
  }));
});
```
Install: `npm install -D fast-check`

### Mutation Testing
```bash
npx stryker run
```
Install: `npm install -D @stryker-mutator/core @stryker-mutator/typescript-checker @stryker-mutator/jest-runner`
Config: `npx stryker init` generates `stryker.config.mjs`

---

## Go

### Dependency Verification
```bash
go build ./...
# Compilation failure on missing packages is the verification.
```

### Lint & Format
```bash
gofmt -w {files}
go vet ./...
```

### Static Analysis — Security
```bash
gosec -fmt json ./...
```
Install: `go install github.com/securego/gosec/v2/cmd/gosec@latest`

### Static Analysis — Complexity
```bash
gocyclo -over 10 {files}
```
Install: `go install github.com/fzipp/gocyclo/cmd/gocyclo@latest`

### Static Analysis — General
```bash
staticcheck ./...
```
Install: `go install honnef.co/go/tools/cmd/staticcheck@latest`

### Property-Based Testing
```go
import "pgregory.net/rapid"

func TestSortIdempotent(t *testing.T) {
    rapid.Check(t, func(t *rapid.T) {
        s := rapid.SliceOf(rapid.Int()).Draw(t, "s")
        sort.Ints(s)
        sorted := make([]int, len(s))
        copy(sorted, s)
        sort.Ints(sorted)
        if !reflect.DeepEqual(s, sorted) {
            t.Fatal("sort is not idempotent")
        }
    })
}
```
Install: `go get pgregory.net/rapid`

### Mutation Testing
```bash
go-mutesting {files}
```
Install: `go install github.com/zimmski/go-mutesting/cmd/go-mutesting@latest`

---

## Rust

### Dependency Verification
```bash
cargo check
# Compilation failure on missing crates is the verification.
```

### Lint & Format
```bash
cargo fmt -- --check {files}
cargo clippy -- -D warnings
```

### Static Analysis — Security
```bash
cargo audit
```
Install: `cargo install cargo-audit`

### Static Analysis — Unsafe Code
```bash
# clippy catches most unsafe patterns; for deeper analysis:
cargo geiger
```
Install: `cargo install cargo-geiger`

### Property-Based Testing
```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn sort_preserves_length(ref v in prop::collection::vec(any::<i32>(), 0..100)) {
        let mut sorted = v.clone();
        sorted.sort();
        prop_assert_eq!(sorted.len(), v.len());
    }
}
```
Install: Add `proptest = "1"` to `[dev-dependencies]` in Cargo.toml

### Mutation Testing
```bash
cargo mutants --file {files}
```
Install: `cargo install cargo-mutants`

---

## Java

### Dependency Verification
```bash
# Maven:
mvn compile -pl {module}
# Gradle:
gradle compileJava
# Compilation failure on missing dependencies is the verification.
```

### Lint & Format
```bash
# Checkstyle (if configured in project):
mvn checkstyle:check
# Or standalone:
java -jar checkstyle.jar -c /google_checks.xml {files}
```

### Static Analysis — Security
```bash
# SpotBugs with FindSecBugs plugin:
mvn spotbugs:check
```
Install: Add `com.github.spotbugs:spotbugs-maven-plugin` to pom.xml

### Static Analysis — Complexity
```bash
# PMD:
mvn pmd:check
# Or standalone:
pmd check -d {files} -R rulesets/java/design.xml -f json
```

### Property-Based Testing
```java
import net.jqwik.api.*;

@Property
void sortPreservesLength(@ForAll List<Integer> list) {
    List<Integer> sorted = new ArrayList<>(list);
    Collections.sort(sorted);
    Assertions.assertEquals(list.size(), sorted.size());
}
```
Install: Add `net.jqwik:jqwik:1.8+` to test dependencies

### Mutation Testing
```bash
# Maven:
mvn org.pitest:pitest-maven:mutationCoverage
# Gradle:
gradle pitest
```
Install: Add `org.pitest:pitest-maven:1.15+` plugin to pom.xml (or `info.solidsoft.pitest` Gradle plugin)

---

## C# / .NET

### Dependency Verification
```bash
dotnet build
# Build failure on missing packages is the verification.
```

### Lint & Format
```bash
dotnet format {files}
```

### Static Analysis — Security
```bash
dotnet tool run security-scan {project}
# Or:
dotnet list package --vulnerable
```
Install: `dotnet tool install --global security-scan`

### Static Analysis — General
```bash
dotnet build /p:TreatWarningsAsErrors=true
```

### Property-Based Testing
```csharp
using FsCheck;
using FsCheck.Xunit;

[Property]
public Property SortPreservesLength(List<int> list) =>
    (list.OrderBy(x => x).Count() == list.Count).ToProperty();
```
Install: `dotnet add package FsCheck.Xunit`

### Mutation Testing
```bash
dotnet stryker
```
Install: `dotnet tool install -g dotnet-stryker`
Config: `dotnet stryker init` generates `stryker-config.json`

---

## Ruby

### Dependency Verification
```bash
ruby -c {files}        # syntax check
bundle exec ruby -e "require '{gem}'"
```

### Lint & Format
```bash
rubocop -a {files}
```
Install: `gem install rubocop`

### Static Analysis — Security
```bash
brakeman -q -f json     # Rails projects
bundler-audit check     # dependency vulnerabilities
```
Install: `gem install brakeman bundler-audit`

### Property-Based Testing
```ruby
require 'rantly/rspec_extensions'

it 'sort preserves length' do
  property_of { array { integer } }.check { |arr|
    expect(arr.sort.length).to eq(arr.length)
  }
end
```
Install: `gem install rantly`

### Mutation Testing
```bash
bundle exec mutant run --use rspec -- 'YourClass'
```
Install: `gem install mutant mutant-rspec`

---

## PHP

### Dependency Verification
```bash
php -l {files}          # syntax check
composer validate
```

### Lint & Format
```bash
php-cs-fixer fix {files}
```
Install: `composer global require friendsofphp/php-cs-fixer`

### Static Analysis — Security
```bash
# Psalm with taint analysis:
vendor/bin/psalm --taint-analysis {files}
```
Install: `composer require --dev vimeo/psalm`

### Static Analysis — General
```bash
vendor/bin/phpstan analyse {files} --level max
```
Install: `composer require --dev phpstan/phpstan`

### Property-Based Testing
```php
use Eris\Generator;
use Eris\TestTrait;

public function testSortPreservesLength() {
    $this->forAll(Generator\seq(Generator\int()))
        ->then(function ($arr) {
            sort($arr);
            $this->assertCount(count($arr), $arr);
        });
}
```
Install: `composer require --dev giorgiosironi/eris`

### Mutation Testing
```bash
vendor/bin/infection --threads=4
```
Install: `composer require --dev infection/infection`
Config: `vendor/bin/infection --init` generates `infection.json5`

---

## Swift

### Dependency Verification
```bash
swift build
# Build failure on missing packages is the verification.
```

### Lint & Format
```bash
swiftlint lint {files}
swift-format -i {files}
```
Install: `brew install swiftlint swift-format`

### Static Analysis — General
```bash
swiftlint analyze {files}
```

### Property-Based Testing
```swift
import SwiftCheck

property("sort preserves length") <- forAll { (arr: [Int]) in
    return arr.sorted().count == arr.count
}
```
Install: Add `SwiftCheck` via Swift Package Manager

### Mutation Testing
No widely adopted mutation testing tool exists for Swift. Use the Discovery Process to evaluate emerging options, or skip mutation testing for Swift projects.

---

## Kotlin

### Dependency Verification
```bash
gradle compileKotlin
# Build failure on missing dependencies is the verification.
```

### Lint & Format
```bash
ktlint --format {files}
```
Install: `brew install ktlint` or `curl -sSLO https://github.com/pinterest/ktlint/releases/latest/download/ktlint`

### Static Analysis — General
```bash
detekt --input {files} --report json:detekt-report.json
```
Install: Add `io.gitlab.arturbosch.detekt` plugin to build.gradle

### Property-Based Testing
```kotlin
// Uses jqwik (same as Java — runs on JVM)
import net.jqwik.api.*

@Property
fun sortPreservesLength(@ForAll list: List<Int>): Boolean =
    list.sorted().size == list.size
```
Install: Add `net.jqwik:jqwik-kotlin:1.8+` to test dependencies

### Mutation Testing
```bash
# Uses pitest (same as Java — runs on JVM)
# Maven:
mvn org.pitest:pitest-maven:mutationCoverage
# Gradle:
gradle pitest
```
Install: Add `org.pitest:pitest-maven:1.15+` plugin (or `info.solidsoft.pitest` Gradle plugin) with `pitest-kotlin` plugin for Kotlin-specific mutators

---

## Discovery Process for Unknown Stacks

When `/gvm-build` encounters a technology not listed above:

1. **Identify the language/framework** from the tech spec and project files
2. **Research the standard toolchain** — look for:
   - The language's built-in verification (e.g., `go vet`, `cargo check`, `dotnet build`)
   - The most widely adopted linter (look for the one with the most GitHub stars / package downloads)
   - The most widely adopted security scanner (prefer tools maintained by security-focused organisations)
   - A complexity checker if one exists
   - A mutation testing framework if one exists (optional — not all languages have mature options)
3. **Test the commands** — run each candidate command on the project to verify it works
4. **Add the entry** to this file following the template below
5. **Note in the build handover** that a new stack was discovered and tooling was added

### Template for New Stacks

```markdown
## [Language/Framework]

### Dependency Verification
\`\`\`bash
[command to verify imports/dependencies exist]
\`\`\`

### Lint & Format
\`\`\`bash
[primary linter command]
[formatter command]
\`\`\`
Install: `[install command]`

### Static Analysis — Security
\`\`\`bash
[security scanner command]
\`\`\`
Install: `[install command]`

### Static Analysis — Complexity
\`\`\`bash
[complexity checker command]
\`\`\`
Install: `[install command]`

### Property-Based Testing
\`\`\`[language]
[example using the language's property-based testing library]
\`\`\`
Install: `[install command]`

### Mutation Testing
\`\`\`bash
[mutation testing command]
\`\`\`
Install: `[install command]`
(If no mature mutation testing tool exists for this stack, note that and skip.)
```

### Selection Criteria for Discovered Tools

When choosing tools for an unlisted stack, prefer:
- **Built-in over third-party** (e.g., `go vet` over a third-party Go linter)
- **Widely adopted over niche** (measured by downloads, GitHub stars, adoption by major projects)
- **Actively maintained** (last release within 12 months)
- **Low false-positive rate** (tools that cry wolf get ignored)
- **JSON output available** (for structured reporting in handovers)
