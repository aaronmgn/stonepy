# Security Policy

## Supported Versions

`stonepy` is pre-1.0 software. Security fixes are released only for the latest version
published on [PyPI](https://pypi.org/project/stonepy/).

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

Please report security vulnerabilities **privately** - do not open a public issue.

- Preferred: open a [private security advisory](https://github.com/aaronmgn/stonepy/security/advisories/new).
- Alternatively, email **aaron@dvops.io** with a description and a reproduction.

You can expect an acknowledgement within 5 business days. When a fix is ready, a new release
is published to PyPI and the advisory is disclosed.

## Handling Credentials

`stonepy` transmits StoneX credentials (username, password, app key, session token) to the
configured API host. The client redacts these values from its logs and exception output, but
you are responsible for storing them securely (for example in environment variables or a
secrets manager) and never committing them to source control.
