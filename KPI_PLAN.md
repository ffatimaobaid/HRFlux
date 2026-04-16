# KPI Reporting Implementation Plan

## Proposed Changes

1. **Backend Improvements (workflow_engine.py)**
   - Add `get_analytics_stats` to `LeaveWorkflowEngine` to calculate:
     - Average resolution time (days)
     - Resolution rate (%)
   - Add `get_ai_savings` to compute estimated HR hours saved.

2. **API Updates (main.py)**
   - Expand `/api/admin/stats` to include new analytics.

3. **Frontend Updates (admin/page.tsx)**
   - Add new cards to the dashboard for the new KPIs.
   - Style the cards to match the existing premium design.

## Verification
- Use `seed_data.py` to ensure there's enough data for meaningful numbers.
- Check the Admin Dashboard UI.
