# Vercel Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the WeChat content AI workstation reproducible locally and deployable on Vercel for cloud demonstration.

**Architecture:** Add a thin Vercel Python entrypoint that reuses the existing local `WorkbenchHandler`. Keep local SQLite and uploads unchanged while mapping Vercel database/uploads to `/tmp` for serverless execution.

**Tech Stack:** Python standard library, SQLite, Vercel Python Serverless Functions, DeepSeek API through environment variables.

---

### Task 1: Vercel Entrypoint

**Files:**
- Create: `api/index.py`
- Modify: `wechat_ai/web.py`

- [x] Create a Python serverless handler that imports the project root and reuses `WorkbenchHandler`.
- [x] Initialize SQLite in `/tmp/wechat_ai_vercel.db`.
- [x] Set Vercel upload directory to `/tmp/wechat_ai_uploads`.

### Task 2: Project Configuration

**Files:**
- Create: `vercel.json`
- Create: `requirements.txt`
- Modify: `.env.example`

- [x] Route all requests to `api/index.py`.
- [x] Declare no third-party dependencies for the current MVP.
- [x] Document Vercel and local environment variables.

### Task 3: Documentation

**Files:**
- Create: `README.md`
- Create: `docs/vercel-deployment.md`

- [x] Explain local startup.
- [x] Explain Vercel deployment.
- [x] Map scoring dimensions to system behavior: process, standard output, reproducibility.

### Task 4: Verification

**Files:**
- Modify: `tests/test_core.py`

- [x] Add tests for Vercel config and serverless initialization.
- [x] Run `python -m unittest tests.test_core -v`.
