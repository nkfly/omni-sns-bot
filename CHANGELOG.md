# Changelog

## 0.1.0 — 2026-11-02

- Bot entry point (`BOT_START_HERE.md`, `AGENTS.md`) and an operating loop that works for assistants with or without files, HTTP, a browser, or a scheduler.
- Account profile interview, voice extraction and presets, anti-AI writing guide (English, Traditional Chinese, Japanese), and a pre-draft self-check.
- Threads adapter: official API runbook checked against Meta's docs on 2026-11-02, browser fallback, quotas, approval levels, calendar, FAQ triage.
- Placeholder adapters for Reddit, Instagram, Facebook, and X, plus a guide for adding a platform.
- Fictional worked example (`examples/salty-pages`).
- Optional standard-library helpers to exchange a Threads token and publish a text post, without taking secrets on the command line.
