# toby's link tracker

A free, self-hosted link shortener for your own domain, with click tracking and notifications.

## Prerequisites

- python and `uv`
- GCP project
- gcloud CLI

## Installation

- Clone the repository and `cd` into it.
- Create a `.env` following `.env.example`.
- Run `uv run infra.py --apply` to provision the cloud function, database, and install the `links` CLI tool.
- Run `links` in your terminal.

> The default webhook setup is for a Discord channel — see [Webhooks](#webhooks) below for more info.

## Usage

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

❯ links
? What do you want to do? List
ID      URL                  label                           Clicks  Created     Last Opened
──────  ───────────────────  ──────────────────────────────  ──────  ──────────  ───────────
openai  https://tobylau.xyz  Sam Altman (Founder @ OpenAI)…  1       2026-07-27  2026-07-27
```
<img width="1258" height="128" alt="image" src="https://github.com/user-attachments/assets/ae9d1976-e283-407d-9d35-5de18b7aaed9" />

### Preview Mode

To test a tracked link, add a `?preview=true` query param. This will open the link in preview mode, which triggers the webhook notification but adds a [PREVIEW] prefix to the message and doesn't update the click count or last opened.

<img width="1366" height="138" alt="image" src="https://github.com/user-attachments/assets/7505657b-4136-40b1-9a18-955a69ea5cb8" />

### Webhooks

Depending on your webhook, you may need to modify `_notify()` in `main.py` to match the expected request format.

For broader webhook support (Slack, Telegram, etc.) without hand-rolling each provider's payload shape, consider swapping `_notify()` for [`apprise`](https://github.com/caronc/apprise).

## How it works

Visiting the tracked link spins up an instance of the Cloud Run service (if no instances are available), grabs the URL path, and:

- fetches the actual URL + attached label
- sends the attached label to the webhook
- redirects the user to the URL

If the URL path does not exist in Firestore, the user is redirected to the default URL. Since cloud services are pay-per-use, hosting is effectively free for personal use. 

Cold starts will inevitably add some latency, which I found to be negligible. Comparable to a network blip. You could also have the Cloud Run service maintain 1 available instance at all times, but this defeats the serverless/free self-hosting purpose of the tracker.

<img width="1922" height="1020" alt="image" src="https://github.com/user-attachments/assets/50e00006-154e-4e4b-8c2f-b06f022000e3" />
