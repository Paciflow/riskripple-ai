# Security

## Secrets and credentials

- No AWS credentials, API keys, or secrets are hardcoded anywhere in this repo.
  AWS access is via the ambient AWS CLI/SDK credential chain (environment,
  `~/.aws/credentials`, or an execution role in Lambda).
- `SEC_EDGAR_CONTACT` is an environment variable with a placeholder default — not
  a secret, but a real contact should replace it before production ingestion
  volume (SEC's fair-access policy expects a genuine one).
- `.gitignore` excludes `.env`, `.env.local`, and `*.pem`.

## IAM

- Each Lambda function in the CDK stacks is granted only the specific
  read/write/invoke permissions it needs on the specific resources it uses (via
  `grantReadWrite` / `grantReadWriteData` scoped to each table/bucket), not
  account-wide access.
- The personal AWS account used during development is itself a useful security
  signal: its IAM user is explicitly restricted (Bedrock and CloudFormation
  access-denied — see `docs/KNOWN_LIMITATIONS.md`), confirming least-privilege is
  enforced at the account level too, not just assumed.

## Data handling

- S3 buckets use `S3_MANAGED` encryption and block all public access
  (`BlockPublicAccess.BLOCK_ALL`).
- DynamoDB tables have point-in-time recovery enabled.
- No PII is collected or stored; portfolios in the demo are fictional.

## Guardrails

- Bedrock Guardrails are not yet configured (requires a live Bedrock-enabled
  account to set up and test — see `docs/KNOWN_LIMITATIONS.md`). Planned
  safeguards: refuse to answer as personalized financial advice, refuse to
  execute or simulate real trade instructions, refuse to fabricate a citation.
  The last one is already partially enforced in code today via
  `validate_report_citations`, independent of Bedrock Guardrails.

## What's explicitly prohibited by design

- No code path executes a real trade or modifies a real brokerage/bank account.
- `StressScenario.is_hypothetical` is a field that can't be set to `False` by any
  caller in the current code (always `True` by default and never flipped),
  so a stress-test result can never silently masquerade as a real forecast.
