# Project Context - dw-enel-databricks-like

## Current Task
Implemented Sprint 26: RAG Fine-tuning loop using Gemini as the teacher model.

## Key Decisions
- Created offline training loop: question generation -> critique -> boost calibration.
- Integrated Positive Cache to bypass RAG for known high-quality answers.
- Implemented dynamic card boosts loaded from JSON to avoid hardcoding weights.

## Next Steps
- Run Round 002 of adversarial training to further refine weights.
- Implement the "FeedbackReason" UI component in Streamlit for human feedback.
- Schedule the nightly evaluation via Airflow DAG.
