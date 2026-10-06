# Security Policy

## Supported versions

Security fixes are made on the latest version on the `main` branch. Please update before reporting.

## Reporting a vulnerability

Please do not open a public issue for a security problem.

Report it privately through GitHub: open the **Security** tab of this repository and choose **Report a vulnerability**. Include:

- What the problem is and where in the code it is
- Steps to reproduce it
- What an attacker could do with it

You can expect an acknowledgement within a few days. This is a volunteer project, so fixes are made on a best-effort basis. Please give the maintainer reasonable time to fix the problem before sharing details publicly.

## What counts

Examples of problems worth reporting:

- Writing or deleting files outside the intended folders, for example through crafted file names
- Leaking the Groq API key, `credentials.json` or `token.json`
- Running unintended commands through file names, links or API responses
- Requesting more Google Drive access than needed

## If you committed a secret by accident

Deleting the file or commit is not enough, because the secret stays in git history. Revoke it right away:

- **Groq API key:** delete it at https://console.groq.com/keys and create a new one
- **Google OAuth client:** delete or rotate it in the Google Cloud Console, and remove the app's access at https://myaccount.google.com/permissions

Then remove the secret from the repository history before pushing again.

## Notes for users

- Audio and transcripts are sent to Groq. Do not process recordings you are not allowed to share with a third party.
- The tool asks for read-only Google Drive access.
- Keep `.env`, `credentials.json` and `token.json` private.
