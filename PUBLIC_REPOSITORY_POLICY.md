# Public Repository Policy

This repository is intentionally public.

## Allowed

Only information required to identify, package, validate and distribute the generic on-device model component may be committed.

## Prohibited

Do not commit:

- personal data or user-generated content;
- host-application source code;
- product-specific prompt text;
- product-specific evaluation scenarios;
- private roadmaps, design discussions or issue exports;
- credentials, keys, access tokens, certificates or secret values;
- internal hostnames, private endpoints or private repository URLs;
- local filesystem paths containing usernames;
- telemetry or logs copied from devices;
- screenshots containing account or device information.

## Local deny-list

Maintainers may create an untracked file named:

`.public-safety-denylist.txt`

with one forbidden term per line. The public-safety checker will fail if any listed term appears in tracked content. This file is deliberately ignored by Git and must never be committed.

Run before publishing:

```bash
python3 scripts/check_public_safety.py
```

A passing automated check is not a substitute for human review.
