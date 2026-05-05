# Boundary Discovery Heuristics

Source-scan signatures for `/gvm-walking-skeleton` Phase 2 (Discovery), per
walking-skeleton ADR-402. Each H2 declares a language; bullets group patterns
by category. Backtick-quoted substrings inside each bullet are the scan tokens
that `_discovery.py` searches for.

The format is parsed mechanically: any line beginning `- <label>:` is treated
as a category line, and every backtick-delimited substring on that line is a
scan token. Prose between bullets is ignored.

Categories map to `BoundaryCandidate.type` per walking-skeleton ADR-403:

- `HTTP outbound` → `http_api`
- `Database` → `database`
- `Cloud SDK` → `cloud_sdk`
- `Filesystem` → `filesystem`
- `Subprocess` → `subprocess`
- `Email` → `email`

## Python

- HTTP outbound: `requests.`, `httpx.`, `urllib.request`, `aiohttp.`
- Database: `psycopg2.`, `sqlalchemy.`, `sqlite3.connect`, `pymongo.`
- Cloud SDK: `boto3.`, `google.cloud.`, `azure.`
- Filesystem: `open(`, `pathlib.Path(`
- Subprocess: `subprocess.run`, `subprocess.Popen`
- Email: `smtplib.`, `sendgrid.`, `mailgun.`

## TypeScript

- HTTP outbound: `fetch(`, `axios.`, `got.`
- Database: `prisma.`, `pg.`, `mongoose.`, `knex.`
- Cloud SDK: `@aws-sdk/`, `@google-cloud/`, `@azure/`

## Go

- HTTP outbound: `http.Get`, `http.Post`, `http.NewRequest`
- Database: `database/sql`, `mongo.Connect`

## Adding a language

Append a new H2 with one or more category bullets in the shape above. Patterns
must be unambiguous strings — they are matched literally (after `re.escape`),
not as regex. Per walking-skeleton ADR-402 the heuristic file is project-extensible;
projects may shadow this file by placing a copy at `<project_root>/.gvm/boundary-discovery.md`
when downstream chunks add that override path.
