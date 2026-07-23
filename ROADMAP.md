# Product Roadmap & Future Enhancements

This document tracks the planned features and architectural upgrades for the AI Logistics Name Matcher, transitioning it from a backend pipeline into a full enterprise SaaS application.

## Phase 1: Dynamic User Configuration
* **UI Controls**: Add Streamlit sidebar widgets to allow users to override config defaults per-session.
* **Tunable AI Strictness**: A slider to adjust the `vector_quality_threshold` dynamically before running the pipeline.
* **Batch Size Selection**: Let users choose their AI batch size based on their current API tier limits.

## Phase 2: Database Integration
* **Persistent Storage**: Connect the app to a lightweight database (e.g., Supabase, Firebase, or a hidden Google Sheet) to replace the static `.json` and `.yaml` files.
* **Master Account CRM**: Allow users to add, edit, or delete Master Accounts directly from the UI, instantly syncing with the database without needing to re-upload Excel files.

## Phase 3: The Enterprise Admin Dashboard
* **Hidden Route**: Create a password-protected `/admin` multi-page route in Streamlit.
* **Analytics & Quota Tracking**: Monitor total records processed, deterministic success rates, and total AI API calls made.
* **Global Settings Manager**: Allow admins to permanently change global thresholds (e.g., updating the default model to `gemini-4.0-flash` or changing the global `vector_quality_threshold`) directly from the UI.

## Phase 4: Human-in-the-Loop & Continuous Learning (RLHF)
* **Audit Log Review**: A feed in the Admin Dashboard showing all ambiguous records the AI processed that week.
* **Correction Engine**: A button for admins to flag and correct an AI false positive or false negative.
* **RLHF Loop**: When an admin corrects a mistake, the new alias is permanently injected into the Vector Database. The tool continuously learns from its mistakes, so a name matched incorrectly on Monday is caught deterministically on Tuesday.
