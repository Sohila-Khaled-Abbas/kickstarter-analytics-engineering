# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | ✅ Active support   |
| 1.x     | ❌ End of life      |

## Reporting a Vulnerability

If you discover a security vulnerability within this project (e.g., accidentally committed credentials, sensitive data leaks, or insecure script practices), **please do not open a public GitHub Issue**.

Instead, report it privately via one of the following channels:

1. **GitHub Private Vulnerability Reporting** (preferred):  
   Navigate to the [Security tab](https://github.com/Sohila-Khaled-Abbas/kickstarter-analytics-engineering/security/advisories/new) and submit a private advisory.

2. **Email**: Contact the repository owner directly through their GitHub profile.

## Security Best Practices in This Repository

- **No credentials are ever committed**: API keys, database passwords, or personal tokens must be stored in `.env` files (which are `.gitignore`d) or GitHub Actions Secrets.
- **No raw personal data**: This repository works with publicly available Kickstarter scraped data only.
- **No binary blobs**: `.pbix` files (which can embed dataset snapshots) are excluded via `.gitignore`. Only PBIP text-format definitions are tracked.
- **Dependency pinning**: `requirements.txt` specifies minimum safe versions for all dependencies.

## Response Timeline

Reported vulnerabilities will be acknowledged within **72 hours** and resolved or addressed within **14 days** of confirmation.
