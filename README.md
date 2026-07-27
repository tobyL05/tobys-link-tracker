# toby's link tracker

A simple self-hosted link redirector with click tracking and webhook notifications.

### Prerequisites

- python and `uv`
- GCP project
- gcloud CLI

### Installation

- Clone the repository and `cd` into it.
- Create a `.env` following `.env.example`.
- Run `uv run infra.py --apply` to provision the cloud function + database, and install the `links` CLI tool.
- Run `links` in your terminal.

> The default webhook setup is for a Discord channel — see [Webhooks](#webhooks) below for more info.

### Usage

```
❯ links
? What do you want to do? (Use arrow keys)
   List
 » Create
   Edit
   Delete

❯ links
? What do you want to do? Create
? URL: https://tobylau.xyz
? Description: Sam Altman (Founder @ OpenAI) opened your resume!
? ID (leave empty to generate): openai

Generated tracked link https://<link to cloud function>/openai
```

<img width="618" height="69" alt="Screenshot 2026-07-26 at 21 24 16" src="https://github.com/user-attachments/assets/266f9f33-7883-44b3-b0eb-eb2a70eb1ed8" />

### Webhooks

Depending on your webhook, you may need to modify `_notify()` in `main.py` to match the expected request format.

For broader webhook support (Slack, Telegram, etc.) without hand-rolling each provider's payload shape, consider swapping `_notify()` for [`apprise`](https://github.com/caronc/apprise).

### How it works

Visiting the tracked link spins up an instance of the cloud function, grabs the URL path, and:

- fetches the actual URL + attached label
- sends the attached label to the webhook
- redirects the user to the URL

If the URL path does not exist in firestore, the user is redirected to the default URL. Webhook notifications are also sent when the URL path isn't found in firestore.

<img width="1922" height="1020" alt="image" src="https://github.com/user-attachments/assets/50e00006-154e-4e4b-8c2f-b06f022000e3" />
