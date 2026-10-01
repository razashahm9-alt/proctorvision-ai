# Security Policy

## Supported version

The current supported demonstration baseline is version 0.8.x.

## Private demonstration checklist

- Use HTTPS and secure WebSockets for every internet deployment.
- Set a long random `PROCTORVISION_ACCESS_TOKEN` outside source control.
- Set `PROCTORVISION_SECURE_COOKIES=true` behind HTTPS.
- Keep `.env`, SQLite data, evidence images and exports private.
- Restrict the deployment to one instance unless persistence/state is redesigned.
- Apply operating-system, Python and Node security updates before deployment.
- Rotate the temporary access token after a supervisor demonstration.
- Remove or sanitize demonstration evidence before publishing the repository.

The included access gate is intended for a private single-reviewer demo. It is
not institutional authentication, authorization, audit identity, brute-force
protection or multi-tenant isolation.

## Reporting

Do not open a public issue containing access tokens, participant images, database
files or session exports. Contact the project owner privately with a minimal
reproduction and redact personal data.
