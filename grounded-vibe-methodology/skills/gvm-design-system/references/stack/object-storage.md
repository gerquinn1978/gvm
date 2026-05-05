# Object Storage

### MinIO — S3-Compatible Object Storage
**Source:** MinIO official documentation (min.io/docs), design guides, and blog

> **Expert Score — MinIO**
> Authority=4 · Publication=3 · Breadth=4 · Adoption=4 · Currency=5 → **4.0 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | docs | 5 | 3 | 5 | 3 | **4.0** | Established |
>
> Evidence: Adoption — 1M+ Docker Hub downloads/month. Work Specificity — bucket design, lifecycle, presigned URLs.


**Key principles to apply in specs:**
- **Bucket design**: Define bucket naming and structure. Typically one bucket per object type (brochures, cached data, user uploads) or per environment. Avoid deeply nested pseudo-directory structures — use flat key namespaces with meaningful prefixes.
- **Object key naming**: Use structured key names that encode metadata: `{user_id}/{run_id}/brochure.html` or `cache/{locale}/{area_slug}/{data_type}.json`. Keys should be scannable by prefix for listing operations.
- **Lifecycle policies**: Define TTLs per bucket or prefix. Cached external data may expire (matching the caching strategy from the data model spec); generated brochures may be retained longer.
- **Presigned URLs**: For serving brochures and reports to users without exposing storage credentials. The spec should define which objects are served via presigned URLs vs proxied through the API.
- **Versioning**: Enable bucket versioning for objects that may be regenerated (brochures across reruns). The spec should define which buckets need versioning.
- **S3 API compatibility**: MinIO implements the S3 API. The spec should use S3 SDK patterns (boto3 for Python, aws-sdk for TypeScript) for portability. Avoid MinIO-specific APIs unless required.
- **Multipart upload**: For large objects (brochures with embedded images), define the multipart upload threshold and chunk size.

**When specifying object storage:**
- Define buckets, key naming conventions, and access patterns
- Specify lifecycle policies per bucket
- Define which objects need versioning
- Specify access method: presigned URL, API proxy, or direct
- Define backup and retention policies
