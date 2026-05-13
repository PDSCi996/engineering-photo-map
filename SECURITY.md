# Security Policy

## Reporting a Vulnerability

Please open a private security advisory or contact the maintainers through the preferred project channel. Do not include real `.env` files, real photos, database dumps, logs, reports, backups, tokens, passwords, internal IP addresses, or private deployment URLs in public issues.

## Sensitive Data Rules

Never commit:

- `.env` or other real environment files
- `data/`, uploaded photos, thumbnails, previews, exports, or backups
- PostgreSQL, SQLite, or other database files
- Logs and diagnostic reports from real deployments
- Real domains, private IPs, public ports, tokens, passwords, or Portainer credentials

Use `.env.example`, `.env.production.example`, or `.env.synology.example` as templates only, and replace all secrets before deployment.