# Product alignment audit

The existing frontend uses real backend records and weighted heuristic scores. Profiles, custom skills, resume review, matching, skill gaps, offers and analytics work and will be preserved. No connected external vacancy feed exists.

Problems: primary navigation puts CRUD and scoring screens before opportunity discovery; create job/company actions dominate; Drive Planner and Assistant are unavailable placeholders; dashboard repeats seven generic metrics and skill charts; job records lack provenance, availability and vacancy metadata; there is no interest/application stage.

Plan: reuse Job/Company, add nullable vacancy/source/date and open/closed metadata through additive SQLite migration, expose /api/v1/opportunities with filters and atomic JSON ingestion, and add a minimal persistent application stage linked to offers by student/job. Keep the original matching formula. Use a role view selector without claiming authentication. Make opportunities, Jobs for Me, opportunity details and suitable candidates prominent. Move company/job entry and imports to Admin Tools. Remove unavailable screens and duplicate metrics. Preserve the green/white responsive visual system and accessible forms.

Audit scope: HTML, CSS, app.js, workflows.js, backend models/schemas/routes/services, database initialization and seed, existing backend/browser tests and documentation. Existing data must survive migration. Existing unknown dates/vacancy counts remain unknown; demo data is not a live vacancy feed.
