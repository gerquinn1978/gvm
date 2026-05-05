## Ross Anderson & Michal Zalewski — Security

**Sources:**
- Ross Anderson, *Security Engineering* (3rd ed.), Wiley (2020)
- Michal Zalewski, *The Tangled Web: A Guide to Securing Modern Web Applications*, No Starch Press (2011)
- Andrew Hoffman, *Web Application Security*, O'Reilly (2020)
- OWASP Top 10 (owasp.org/Top10/)
- OWASP Application Security Verification Standard (ASVS)

**Expert scores:**

| Expert | A | P | B | Ad | C | Avg | Tier |
|---|---|---|---|---|---|---|---|
| Ross Anderson | 5 | 5 | 5 | 5 | 4 | **4.8** | **Canonical** |
| Michal Zalewski | 4 | 3 | 2 | 3 | 3 | **3.0** | **Recognised** |
| Andrew Hoffman | 3 | 3 | 3 | 2 | 4 | **3.0** | **Recognised** |
| OWASP | 5 | 4 | 4 | 5 | 5 | **4.6** | **Canonical** |

| Work | S | De | C | I | Avg | Tier |
|---|---|---|---|---|---|---|
| Anderson, *Security Engineering* 3rd ed | 3 | 5 | 5 | 5 | **4.5** | **Canonical** |
| Zalewski, *The Tangled Web* | 5 | 5 | 2 | 4 | **4.0** | **Established** |
| Hoffman, *Web Application Security* | 4 | 3 | 4 | 2 | **3.25** | **Recognised** |
| OWASP, *Top 10* | 4 | 3 | 5 | 5 | **4.25** | **Established** |
| OWASP, *ASVS* | 5 | 4 | 5 | 4 | **4.5** | **Canonical** |

**Evidence (Anderson):** Authority — leading academic; Cambridge/Edinburgh; Royal Academy. Breadth — cryptography, auth, network, economics, psychology. Work Depth — 1,200 pages. Work Currency — 3rd ed 2020.

**Evidence (Zalewski):** Authority — Google staff security engineer; created AFL fuzzer. Work Specificity — browser security model at implementation precision. Work Depth — systematic browser-by-browser analysis.

**Evidence (Hoffman):** Currency — 2020; covers SPA, API security, JWT.

**Evidence (OWASP):** Authority — global standard; referenced in PCI-DSS, ISO 27001, NIST. Adoption — cited by every cloud provider. *ASVS* Specificity — 286 testable verification requirements.

**Activation signals:** Authentication, authorization, user input handling, credential storage, external data rendering, cookie/session management, iframe embedding, WebSocket communication, file uploads, API design

**Key principles to apply:**

- **Threat modeling before design** (Anderson, Ch. 1-2): Identify who the adversaries are, what they want, and what they can do. The spec should define the threat model — not just "we need auth" but "we need to prevent session hijacking via XSS and CSRF because cookies carry auth state."
- **Same-origin policy and its exceptions** (Zalewski, Ch. 9-11): The browser's security model. Understand what `sandbox`, `allow-same-origin`, `SameSite`, `httpOnly`, and `Secure` cookie attributes actually do. Specs involving iframes, cookies, or cross-origin requests must define the exact security attributes.
- **Defence in depth** (Anderson, Ch. 2): No single control should be the only barrier. Authentication at the API, authorization on the resource, validation on the input, sanitisation on the output. Each layer assumes the others have failed.
- **Input validation at every boundary** (Hoffman, Ch. 3-5): Validate length, type, and allowed values at the system boundary (user input, API responses, WebSocket messages). Internal code can trust validated data. Never trust data that crosses a boundary — including data from your own database if it originally came from user input.
- **CSRF requires explicit mitigation** (Zalewski, Ch. 9): Cookie-based authentication is vulnerable to CSRF by design. `SameSite=Lax` is partial mitigation. Full protection requires a synchronised token or custom request header validated server-side.
- **Output encoding, not input filtering** (OWASP): For XSS prevention, encode output for the context (HTML, JS, URL, CSS) rather than filtering input. React's JSX handles this for text content, but `dangerouslySetInnerHTML`, `srcdoc`, and template engines bypass it.
- **Principle of least privilege** (Anderson, Ch. 4): Grant the minimum permissions necessary. Iframe sandboxes should start with `sandbox=""` and add only the permissions required. API tokens should have scoped permissions. Database connections should use the least-privileged role.

**When specifying security concerns:**
- Define the threat model: who are the adversaries? What assets are protected?
- Specify authentication mechanism with exact cookie attributes (httpOnly, Secure, SameSite, Path, Domain)
- Specify CSRF protection strategy
- Define input validation rules at every system boundary
- Specify iframe sandbox permissions if rendering external/user-influenced content
- Define what data is sensitive and how it's protected in transit and at rest
- Specify rate limiting and account lockout policies

**When reviewing code:**
- Check OWASP Top 10 and CWE-25 against every system boundary
- Verify cookie attributes match the spec
- Verify iframe sandbox is least-privilege
- Check for race conditions in auth flows (concurrent token refresh)
- Verify no secrets in logs, URLs, or client-side state
- Check input length limits on user-facing text fields
