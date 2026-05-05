# TypeScript

### Dan Abramov / React Core Team — React Patterns
**Sources:**
- React official documentation (react.dev), especially "Thinking in React" and "Server Components"
- Dan Abramov, blog posts on React philosophy (overreacted.io)

> **Expert Score — Dan Abramov**
> Authority=5 · Publication=4 · Breadth=4 · Adoption=5 · Currency=5 → **4.6 — Canonical**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | react.dev | 5 | 4 | 5 | 5 | **4.75** | Canonical |
> | overreacted.io | 3 | 5 | 3 | 4 | **3.75** | Established |
>
> Evidence: Authority — React core team; co-authored Hooks; led react.dev. Adoption — React dominant frontend framework. Work(react.dev) Currency — maintained for React 18/19.


**Key principles to apply in specs:**
- **Component composition** (docs: Thinking in React): Break UI into a component hierarchy based on the single responsibility principle. The spec should define the component tree.
- **Server vs Client Components** (docs: Server Components): Default to server components. Use client components only for interactivity. The spec should mark which components need client-side state.
- **State lifting** (docs: Managing State): State should live at the lowest common ancestor of the components that need it. The spec should identify where state lives.
- **Unidirectional data flow**: Data flows down through props, events flow up through callbacks. The spec should describe the data flow for each major feature.
- **Effects are for synchronisation** (docs: Synchronizing with Effects): useEffect is for syncing with external systems, not for derived state or event handling.

### Kent C. Dodds — Testing & Component Patterns
**Sources:**
- Kent C. Dodds, *Testing Library* (testing-library.com)
- Kent C. Dodds, *Epic React* workshop series

> **Expert Score — Kent C. Dodds**
> Authority=4 · Publication=3 · Breadth=3 · Adoption=5 · Currency=4 → **3.8 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | Testing Library | 5 | 4 | 5 | 5 | **4.75** | Canonical |
> | Epic React | 4 | 4 | 4 | 3 | **3.75** | Established |
>
> Evidence: Adoption — 18M+ weekly npm downloads. Work(TL) Influence — displaced Enzyme.


**Key principles to apply in specs:**
- **Test user behaviour, not implementation** (Testing Library philosophy): Tests should interact with components the way users do — find by role, label, text, not by class or ID.
- **Render, then assert** (Testing Library): The testing approach for each component: render with props, simulate user interaction, assert on the result.
- **Compound components** (Epic React): For complex UI elements, use the compound component pattern — a parent provides context, children consume it.
- **Custom hooks for shared logic** (Epic React): Extract shared stateful logic into custom hooks. The spec should identify where custom hooks are warranted.

### Robin Wieruch — React Ecosystem
**Source:** Robin Wieruch, *The Road to React* (2024), blog posts (robinwieruch.de)

> **Expert Score — Robin Wieruch**
> Authority=3 · Publication=3 · Breadth=4 · Adoption=3 · Currency=5 → **3.6 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | *Road to React* 2024 | 4 | 3 | 5 | 3 | **3.75** | Established |
>
> Evidence: Currency — 2024; annually updated.


**Key principles to apply in specs:**
- **Data fetching patterns**: TanStack Query (React Query) for server state, or SWR. The spec should specify the data fetching strategy.
- **State management**: For most apps, React's built-in state + context is sufficient. Zustand for complex client state. Redux only if you have specific time-travel/middleware needs.
- **Project structure**: Feature-based organisation over layer-based. Group by feature (auth/, search/, brochure/) not by type (components/, hooks/, services/).

### Dan Vanderkam — TypeScript
**Source:** Dan Vanderkam, *Effective TypeScript* (2nd ed.), O'Reilly (2024)

> **Expert Score — Dan Vanderkam**
> Authority=4 · Publication=5 · Breadth=3 · Adoption=4 · Currency=5 → **4.2 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | *Effective TypeScript* 2nd ed. | 5 | 5 | 5 | 5 | **5.0** | Canonical |
>
> Evidence: Publication — O'Reilly 2nd ed 2024. Work Specificity — 83 actionable items. Work Depth — comprehensive type system. Work Currency — TypeScript 5.x.


**Key principles to apply in specs:**
- **Types as documentation** (Items 1-5): TypeScript types are the spec's API contracts made executable. Define interfaces for all component props, API responses, and shared data.
- **Prefer interfaces over type aliases** (Item 13): For object shapes that others will extend, use interfaces.
- **Narrow types** (Items 22-23): Use discriminated unions and literal types rather than broad types. `status: 'pending' | 'running' | 'complete'` not `status: string`.
- **Avoid any** (Items 38-43): `unknown` is almost always better than `any`. The spec should define strict types.
