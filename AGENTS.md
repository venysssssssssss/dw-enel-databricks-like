# AGENTS.md

## Role

Act as a senior software engineer and senior data engineer.
Optimize for correctness, maintainability, safety, and low-risk delivery.

## Rules

- Plan briefly for non-trivial work; execute directly for trivial work.
- Replan when assumptions fail or complexity rises.
- Surface risks, constraints, and assumptions early.
- Prefer autonomous execution for low-risk, reversible work.
- Never delete important code, data, or files without explicit permission.

## Repository Discipline

- Never invent repository facts or contracts.
- Verify names, interfaces, call sites, configs, tests, and docs before editing.
- Prefer minimal, reversible diffs.
- Preserve architecture unless change has clear technical value.

## Engineering

- Prefer simple, root-cause fixes.
- Follow SOLID when useful; avoid needless abstraction.
- Keep boundaries explicit; avoid hidden side effects and unnecessary global state.
- Preserve backward compatibility unless explicitly allowed.

## Python

- Target Python 3.12.
- Use type hints in non-trivial code.
- Write actionable errors and structured logs.
- Avoid broad `except` unless justified and debuggable.

## Data

- Build idempotent, restartable pipelines.
- Validate schema, types, required columns, and invariants at boundaries.
- Prefer DuckDB for set-based transforms when appropriate.
- Track row counts, duration, rejects, and run status when relevant.

## Validation

- Work is incomplete until validated.
- Add or update tests for behavior changes when feasible.
- Use pytest for Python.
- Validate the changed path first.
- If validation cannot run, state that explicitly.
- For data changes, check schema, row counts, and key edge cases.

## Docs and Delivery

- Update docs when behavior or contracts change.
- Keep docs aligned with implementation.
- Summarize what changed, why, validation performed, and residual risks.

@RTK.md


<claude-mem-context>
# Memory Context

# [dw-enel-databricks-like] recent context, 2026-04-23 11:43am GMT-3

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 50 obs (29,132t read) | 733,410t work | 96% savings

### Apr 16, 2026
S18 Continue Sprint 17 development — RAG regional scope constraint (CE/SP only) with quality improvements and evaluation framework (Apr 16, 8:59 AM)
S19 Test validation for deterministic card boost system and individual client query refusal (Apr 16, 9:32 PM)
S20 Fix RAG agent returning placeholder responses instead of actual CE/SP complaint statistics (Apr 16, 11:29 PM)
### Apr 17, 2026
S21 Sprint 17.1 MVP Delivery - Remove Individual Client Blocking, Add Installation/Monthly Cards, SP N1 Parity (Apr 17, 8:58 AM)
193 9:47a 🔵 RAG corpus contains 18 data cards with CE region complaint intelligence
194 " 🟣 RAG query pipeline routes CE/SP regional queries with semantic card boosting
195 9:50a 🔵 RAG system validated with 94 passing unit tests
196 9:51a 🟣 Added test coverage for CE total complaints card boosting logic
197 " 🟣 Added test coverage for CE total complaints data card generation
198 9:52a 🔴 Fixed regex pattern for CE total refaturamento card boosting
199 " 🔵 Full unit test suite validates RAG sprint integration with 203 passing tests
200 3:13p 🔵 RAG system architecture blocks individual client/installation queries
201 3:14p 🔵 Silver dataset contains individual installation and order identifiers
202 3:15p 🔵 Silver CSV contains detailed customer notes with embedded PII and product information
203 " 🔵 Silver CSV schema includes 24 columns with individual identifiers and extracted PII fields
204 " ⚖️ Planning to enable individual installation/client queries for ENEL MVP demo
205 3:16p 🔵 VIEW_REGISTRY confirmed to lack per-installation and granular monthly aggregation views
206 " 🔵 Sprint 17 planning document outlines RAG quality improvements for CE/SP scope
207 3:18p ⚖️ Sprint 17.1 plan formalized: remove individual client blocking and add granular data cards for MVP
S22 Complete implementation of graphite premium design system from Refactor.html into Streamlit dashboard frontend with oklch color space migration (Apr 17, 3:25 PM)
208 7:45p 🔵 Sprint 17.1 RAG system requirements and Refactor.html UI design analyzed
209 " 🔵 Current Streamlit frontend architecture mapped
210 7:46p 🔵 Complete Streamlit application structure and integration points identified
211 7:47p 🔵 Comprehensive Streamlit frontend architecture documented via parallel exploration agents
212 7:51p ⚖️ Sprint 17.2 Frontend Refactor plan created with complete implementation roadmap
213 8:00p 🔄 Streamlit theme system migrated to oklch color space with graphite design tokens
214 " 🟣 Dashboard sidebar redesigned with graphite component system and visual preset selector
215 8:01p 🔄 Chat interface completely rewritten with graphite premium design and custom message bubbles
216 " 🔵 Test suite identified 3 expected failures after graphite refactor completion
S23 Refactor Streamlit BI/MIS to absorb MIS Aconchegante design excellence, fix skeleton loading and button visibility bugs (Apr 17, 8:03 PM)
### Apr 18, 2026
217 1:23a 🔵 Streamlit BI/MIS frontend refactor scope identified
218 1:24a 🔵 Reference design system analyzed for Streamlit migration
219 " 🔵 Current Streamlit dashboard architecture analyzed
S24 Sprint 17.3: Absorb Aconchegante premium design patterns into Streamlit BI/MIS dashboard and fix frontend bugs (skeleton infinite loading, button visibility) (Apr 18, 1:25 AM)
220 1:27a 🔵 Current MIS executive layer implementation analyzed
221 1:28a 🔵 Additional dashboard layer implementations analyzed
222 " ⚖️ Sprint 17.3 refactor work organized into 5 implementation tasks
223 " 🔴 Skeleton infinite loading bug fixed with clearable placeholder pattern
224 1:30a 🔄 Premium UI components and button fixes integrated into theme system
225 " 🔄 Skeleton CSS consolidated into theme with accessibility improvements
226 " 🟣 Premium component library created with Python helpers for Aconchegante patterns
227 1:32a 🟣 MIS layer upgraded with premium components and native DOM pareto
228 " 🟣 Governance layer upgraded with health cards and status-based coloring
229 1:33a 🟣 Taxonomy layer enhanced with topic pills and premium narrative
230 " 🔄 LayerNarrative renderer upgraded to story block styling with backward compatibility
S25 Commit Sprint 17.3 frontend changes including Aconchegante design patterns and bug fixes (Apr 18, 1:36 AM)
231 1:45a ✅ Uncommitted changes spanning design system, data plane, and RAG enhancements
S26 Sprint 17.4: Apply MIS BI Aconchegante redesign to Streamlit interface, fix sidebar Manual preset bug, add chat agent spoilers and thinking animations (Apr 18, 1:45 AM)
232 10:57a 🔵 Aconchegante design system specification reviewed
233 " ⚖️ Sprint 17.4 task created for Aconchegante design migration
234 10:58a 🔴 Sidebar preset toggle bug fixed with session state tracking
235 10:59a 🟣 Agent step spoilers visual component added to chat
236 11:00a 🔄 Chat input bar redesigned with premium sticky styling
237 11:01a 🔵 MIS BI Aconchegante Design System Tokens Identified
238 11:02a 🟣 Sprint 17.4: Chat Agent Spoilers, Sidebar Fix, and Aconchegante Design Integration
239 11:13a 🟣 Live Agent Pipeline Animations with Streaming Spoilers
240 11:14a 🔄 Independent Slot Rendering for Smooth Agent Pipeline Animations
241 11:15a 🔄 Performance Optimization and Bug Fixes for Agent Pipeline Streaming
242 11:25a ⚖️ Iframe-based Thinking Component with Autonomous JavaScript State Machine
S27 Complete iframe-based thinking panel architecture by replacing remaining `_paint_thinking()` calls with iframe re-mounts for live mode and done mode (Apr 18, 11:28 AM)
**Investigated**: Examined two remaining `_paint_thinking()` calls at lines 1123 and 1165 in apps/streamlit/layers/chat.py that were incompatible with the new iframe-based architecture where JavaScript autonomously handles visual updates

**Learned**: Iframe-based thinking panel requires three render stages: (1) initial mount with placeholder data when pipeline starts, (2) re-mount with actual passage doc_ids when LLM step begins to show real sources cycling in trace, and (3) final swap to "done" mode with all steps checkmarked and metrics stamp showing total time, tokens, and first-token latency. Python only provides data via `_thinking_component_html()` parameters; JavaScript state machine inside iframe autonomously advances steps and animates without Python intervention, preventing DOM destruction and animation restarts

**Completed**: Replaced line 1123 `_paint_thinking()` call with iframe re-mount using `_thinking_component_html(passages=passages)` to show actual doc_ids in LLM step trace. Replaced line 1165 `_paint_thinking()` call with iframe swap to done mode using `_thinking_component_html(passages=passages, done=True, total_time_ms=elapsed, first_token_ms=first_token_ms, tokens=len(accumulated))` to display completion state with metrics. Syntax validation passed. Task #2 marked completed. Dual-graph edit registered for chat.py

**Next Steps**: Pending tasks from original user request: (1) Fix SIDEBAR bugs where switching from Manual to another status prevents returning to Manual, (2) Review and potentially improve chat input bar styling beyond current CSS implementation


Access 733k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>