# Telegram-to-Social Media Posting Automation Plan

## Goal

Send or forward a photo to the existing Telegram bot. The automation creates a caption based on the image and brand settings, shows a preview in Telegram, accepts edits, and only publishes after explicit approval to:

- Instagram
- Threads
- Facebook Page

This plan intentionally uses an **approval-first** workflow: nothing reaches a social platform until an approved Telegram action is recorded.

## Scope for version 1

- One image per post.
- One approved operator (the Telegram user ID is allow-listed).
- Immediate publishing after approval.
- A shared base caption, with platform-specific versions when required by length or formatting.
- Posting outcome and URLs/IDs returned to Telegram.

Later versions can add carousels, reels/videos, scheduled posts, multiple brands, approvals by a team, analytics, and content calendars.

## Proposed user flow

```text
You forward/send photo to Telegram bot
            |
            v
Bot validates sender and image, then stores original media
            |
            v
AI analyses image + brand brief and drafts captions
            |
            v
Bot sends preview with buttons:
[Approve & publish] [Edit caption] [Regenerate] [Cancel]
            |
      edit/regenerate loop
            |
            v
Approval is persisted, then a background job publishes independently
            |
            v
Bot reports success/failure separately for Instagram, Threads, Facebook
```

### Telegram interaction details

1. Receive `photo` (and optionally a text instruction such as `Use a professional tone`). Reject unsupported input with a clear message.
2. Download the highest-resolution Telegram image and save it in durable object storage.
3. Create a post record with status `DRAFT` and a random, non-guessable approval token.
4. Generate a structured result: `instagram_caption`, `threads_caption`, `facebook_caption`, `alt_text`, and a short image summary. Store it with the post record.
5. Return the image and caption preview to Telegram with inline buttons.
6. On **Edit caption**, collect the replacement text (or show a small Telegram web form if per-platform editing is needed), save it, and show preview again.
7. On **Regenerate**, accept an optional instruction (for example, “shorter, fewer hashtags”) and create a new draft; never overwrite the published audit record.
8. On **Approve & publish**, confirm the request comes from the allowed user and that the post is still pending. Atomically mark it `APPROVED` and enqueue one publish job.
9. The worker publishes each platform, records its platform post ID/URL/error, and sends a Telegram summary. A retry should only retry platforms that did not succeed.

## Architecture

| Component | Responsibility | Suggested choices |
| --- | --- | --- |
| Telegram adapter | Receives webhooks, validates secret, handles messages and inline button callbacks | Node.js + TypeScript with Telegraf, or Python with aiogram/FastAPI |
| Application API | Owns post state, approvals, caption generation and job creation | FastAPI or Express/NestJS |
| AI caption service | Vision analysis and caption generation from a controlled brand prompt | OpenAI Responses API with image input and structured JSON output |
| Media storage | Keeps the original image at a stable HTTPS URL for publishing APIs | Cloudflare R2, Amazon S3, or Google Cloud Storage |
| Database | Stores post state, captions, approvals, platform results and audit log | PostgreSQL |
| Queue + worker | Publishes asynchronously, retries temporary failures, prevents duplicate posts | Redis + BullMQ / Celery, or managed queue such as Cloud Tasks |
| Meta publisher | Calls official Meta/Threads APIs using stored tokens | Separate provider module per platform |
| Monitoring | Error alerts, job history and logs without exposing tokens or user media | Sentry + provider logs |

Use the official APIs; do not automate browser logins or scrape private endpoints. Browser automation is fragile and risks account restrictions.

## Platform requirements to confirm before coding

| Platform | Account/connection needed | Key implementation note |
| --- | --- | --- |
| Instagram | Professional account (Business or Creator) linked to a Facebook Page and Meta app | Publish through the Instagram Graph API; verify current media formats, permissions, API version and publishing limits. |
| Facebook Page | A Facebook Page you manage and a Meta app with approved page publishing access | Use a Page access token and Page publishing endpoint; publish the image and caption as a Page post. |
| Threads | Threads profile connected to the Meta developer app | Use the official Threads API publishing flow; verify image-post availability, scopes, rate limits and access requirements. |

Before development, create/use a Meta developer app, add the relevant products, connect the Instagram professional account and Facebook Page, create the Threads app connection, and complete any required Meta access review. Keep a test Page, test Instagram account and test Threads profile for development.

Media normally needs to be available from a stable HTTPS URL that Meta can fetch. Store the final normalized file in object storage; do not depend on Telegram's temporary download URL.

## Data model

### `posts`

| Field | Notes |
| --- | --- |
| `id` | UUID |
| `telegram_chat_id`, `telegram_user_id`, `telegram_message_id` | Source and authorization audit |
| `source_media_key`, `mime_type`, `sha256` | Object-storage reference and duplicate detection |
| `status` | `DRAFT`, `AWAITING_APPROVAL`, `APPROVED`, `PUBLISHING`, `PARTIAL_SUCCESS`, `PUBLISHED`, `FAILED`, `CANCELLED` |
| `caption_instagram`, `caption_threads`, `caption_facebook`, `alt_text` | Final approved content |
| `generation_prompt_version` | Enables reproducible prompt changes |
| `approved_at`, `approved_by` | Explicit human approval record |
| `idempotency_key` | Prevents repeated callback/job publishing |
| `created_at`, `updated_at` | Operational history |

### `publication_attempts`

One row per post/platform/attempt: platform name, status, request idempotency key, external post ID/URL, safe error code/message, attempt count, timestamps and retry time.

### `audit_events`

Append-only history of upload, caption generation, caption edits, regeneration, approval, cancellation, publish attempt, success and failure.

## Caption generation design

Create a versioned brand configuration instead of embedding brand instructions in code:

```yaml
brand_voice: warm, clear, expert but not salesy
audience: [describe target audience]
language: en
required_cta: "..."
forbidden_claims: ["guaranteed", "#competitor"]
hashtag_policy: 3-6 relevant tags, no repeated tag blocks
instagram_max_chars: [set policy]
threads_max_chars: [set policy]
facebook_max_chars: [set policy]
```

The AI should return validated JSON, not free-form prose. Include image-derived facts only when visible; do not invent product prices, locations, offers, people’s identities, or claims. If the image is ambiguous, the draft should request a human instruction rather than guess.

## Reliability and safety requirements

- Allow-list Telegram user IDs and validate the Telegram webhook secret token.
- Keep all secrets in a managed secret store/environment variables; never put bot tokens, Meta tokens or OpenAI keys in source control or Telegram messages.
- Encrypt sensitive tokens at rest and use least-privilege Meta permissions.
- Verify the approval callback against `post_id`, allowed user ID, current status and expiration. A button press must be idempotent.
- Treat approval as immutable for that draft. Any content change returns it to `AWAITING_APPROVAL`.
- Use a queue, exponential backoff and a dead-letter/review state for transient platform failures.
- Publish each platform with a per-platform idempotency key. Never resend a known successful publication.
- Normalize image type/size and validate aspect ratio before approval; display specific instructions if a platform cannot accept it.
- Add rate limiting and antivirus/content checks as appropriate for the deployment.
- Log IDs and outcomes, not access tokens or full customer content. Set retention rules for stored media.

## Delivery phases

### Phase 0 — Accounts and decisions

1. Confirm target accounts, exact brand voice, caption language, approval users and whether all three platforms always publish together.
2. Create a Meta developer app and connect the Instagram professional account, Facebook Page and Threads account.
3. Obtain the required scopes/tokens and confirm app-review requirements with Meta's current documentation.
4. Choose hosting, database and object storage. For a small dependable deployment, use a managed Postgres, Redis/queue and S3-compatible storage.

**Exit condition:** test credentials can publish a manually prepared image to each test account through the official API.

### Phase 1 — Telegram draft and approval MVP

1. Add webhook endpoint and Telegram update validation.
2. Implement allow-listed photo intake and durable media upload.
3. Add database schema, post state machine and audit events.
4. Implement caption generation using a versioned brand prompt and JSON validation.
5. Implement Telegram preview plus Approve, Edit, Regenerate and Cancel callbacks.
6. Write unit tests for authorization, duplicate callbacks, invalid transitions and edit-to-reapproval behavior.

**Exit condition:** a photo produces a draft, can be edited/regenerated, and only an approved user can move it to `APPROVED`.

### Phase 2 — Publishing integrations

1. Build one isolated publisher adapter per platform.
2. Start with Facebook Page, then Instagram, then Threads; test each against the dedicated test account.
3. Add job queue, idempotency, retry policy and per-platform status tracking.
4. Send a final Telegram result with individual platform links or actionable errors.
5. Add integration tests with mocked API responses plus a manual test checklist for real sandbox/test accounts.

**Exit condition:** one approved photo publishes exactly once to all three platforms and a simulated failure produces a partial-success report without duplicating the others.

### Phase 3 — Production hardening

1. Deploy HTTPS webhook/API and worker separately; configure health checks and alerting.
2. Move tokens to a managed secret service; add token-expiry/reauthorization alerts.
3. Set media retention/deletion policy and backup database records.
4. Create an operations dashboard or admin command for failed and queued posts.
5. Complete Meta access review if needed, switch to production credentials, and run a monitored launch.

**Exit condition:** one week of successful monitored use, with recoverable failures and an audit trail.

## Acceptance tests

- An allowed user can forward one photo and receives a caption draft with preview controls.
- A non-allowed user cannot create or approve a post.
- Editing any caption removes prior approval and requires a new approval.
- Pressing Approve twice, webhook redelivery, or worker retry does not create duplicate social posts.
- A Facebook/Instagram/Threads failure is reported separately and can be retried safely.
- Meta token expiry, invalid media, and API rate-limit errors produce human-readable Telegram guidance.
- No secret appears in logs, source control, database error messages or Telegram responses.

## Suggested first implementation backlog

1. Document target account IDs and brand prompt in a local `.env.example` and `brand-config.yaml` (without real secrets).
2. Scaffold the Telegram webhook service and PostgreSQL schema.
3. Implement photo-to-object-storage flow and `posts` state machine.
4. Implement the AI caption draft and Telegram approval loop.
5. Implement/test the Facebook Page publisher.
6. Add Instagram and Threads publishers after their credentials and API access are verified.
7. Add queue, retries, alerts and production deployment.

## Open decisions

- Preferred stack: Python/FastAPI or Node.js/TypeScript?
- Is a single caption acceptable, or should each platform have separately editable copy?
- Should approval publish immediately or offer a scheduled time?
- Do you need only images now, or reels/videos and multi-image posts from the start?
- Will this be for one personal brand or multiple client accounts?

