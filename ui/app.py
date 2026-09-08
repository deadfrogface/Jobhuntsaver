"""Streamlit local GUI for Jobhuntsaver."""

from __future__ import annotations

import sys
from pathlib import Path

# Fix import path: remove current dir, prioritize workspace root
workspace_root = Path(__file__).parent.parent.resolve()
sys.path = [str(workspace_root)] + [p for p in sys.path if p not in ('', str(Path(__file__).parent))]

import io
import pandas as pd
import streamlit as st

from app.main import run_pipeline
from core.config import load_config
from core.database import Database
from core.models import JobStatus


def _db() -> Database:
    config = load_config()
    return Database(config.db_path)

def main() -> None:
    st.set_page_config(page_title="Jobhuntsaver", layout="wide")
    st.title("Jobhuntsaver")
    st.caption("Lokale Jobsuche & Bewerbungshilfe für Deutschland")

    config = load_config()
    db = _db()
    stats = db.dashboard_stats()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Heute gefunden", stats["jobs_found_today"])
    c2.metric("Neu", stats["new_today"])
    c3.metric("Matches ≥75%", stats["matches_ge_75"])
    c4.metric("Beworben", stats["applications_today"])
    c5.metric("Needs Review", stats["needs_review"])
    c6.metric("Fehler / CAPTCHA", f"{stats['errors']} / {stats['captcha']}")

    with st.sidebar:
        st.header("Aktionen")
        if st.button("Suche starten (search_only)", type="primary"):
            with st.spinner("Suche läuft…"):
                result = run_pipeline(config, mode="search_only")
            st.success(f"Fertig: {result}")
            st.rerun()
        st.write(f"Modus: `{config.settings.mode}`")
        st.write(f"Dry run: `{config.settings.dry_run}`")
        st.divider()
        st.subheader("Quellenstatus")
        for row in db.list_source_status():
            st.write(f"**{row['source']}**: {row['status']} ({row.get('jobs_found', 0)})")
            if row.get("message"):
                st.caption(row["message"][:120])

    st.subheader("Filter")
    f1, f2, f3, f4 = st.columns(4)
    min_match = f1.number_input("Min. Match", 0, 100, int(config.settings.minimum_match_for_dashboard))
    max_dist = f2.number_input("Max. Distanz km", 1, 200, int(config.profile.location.max_distance_km))
    status = f3.multiselect(
        "Status",
        [s.value for s in JobStatus],
        default=[],
    )
    remote = f4.multiselect("Arbeitsmodell", ["onsite", "hybrid", "remote", "unknown"], default=[])
    f5, f6, f7 = st.columns(3)
    company_q = f5.text_input("Firma")
    title_q = f6.text_input("Titel")
    source_q = f7.text_input("Quelle")

    jobs = db.list_jobs(
        min_match=min_match,
        max_distance=float(max_dist),
        statuses=status or None,
        hide_applied=config.settings.hide_already_applied,
        hide_duplicates=config.settings.hide_duplicates,
        remote_types=remote or None,
        source=source_q or None,
        company_query=company_q or None,
        title_query=title_q or None,
    )

    rows = [
        {
            "Match": j.match_score,
            "Titel": j.title,
            "Firma": j.company,
            "Ort": j.city or j.address,
            "Distanz": j.distance_km,
            "Modell": j.remote_type,
            "Gehalt": j.salary_text,
            "Quelle": j.source,
            "Datum": j.published_at or j.discovered_at,
            "Status": j.status,
            "ID": j.id,
        }
        for j in jobs
    ]
    df = pd.DataFrame(rows)
    st.dataframe(df.drop(columns=["ID"]) if not df.empty else df, use_container_width=True, hide_index=True)

    if not df.empty:
        selected = st.selectbox("Job-Details", options=df["ID"].tolist(), format_func=lambda i: next(f"{r['Match']}% — {r['Titel']} @ {r['Firma']}" for r in rows if r["ID"] == i))
        job = db.get_job(selected)
        if job:
            st.markdown(f"### {job.title}")
            st.write(f"**{job.company}** · {job.city or job.address} · {job.distance_km} km · {job.remote_type}")
            st.write(f"Match: **{job.match_score}%** · ATS: `{job.ats_type}` · Status: `{job.status}`")
            st.write("Warum passend:")
            for r in job.match_reasons:
                st.write(f"- {r}")
            st.write("Mögliche Probleme:")
            for r in job.rejection_reasons:
                st.write(f"- {r}")
            with st.expander("Beschreibung"):
                st.write(job.description or "(keine Beschreibung)")
            b1, b2, b3, b4, b5, b6 = st.columns(6)
            if b1.button("Interessant"):
                db.update_job_status(job.id, JobStatus.INTERESTING.value)
                st.rerun()
            if b2.button("Ignorieren"):
                db.update_job_status(job.id, JobStatus.IGNORED.value)
                st.rerun()
            if b3.button("Als beworben"):
                db.update_job_status(job.id, JobStatus.APPLIED.value)
                st.rerun()
            if b4.button("Needs Review"):
                db.update_job_status(job.id, JobStatus.NEEDS_REVIEW.value)
                st.rerun()
            if b5.link_button("Original öffnen", job.url or job.application_url or "https://example.com"):
                pass
            st.caption(f"Bewerbungs-URL: {job.application_url or job.url}")

            # Export
            export_df = df.drop(columns=["ID"])
            csv = export_df.to_csv(index=False).encode("utf-8")
            st.download_button("CSV exportieren", csv, "jobs.csv", "text/csv")
            buf = io.BytesIO()
            export_df.to_excel(buf, index=False)
            st.download_button(
                "Excel exportieren",
                buf.getvalue(),
                "jobs.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


if __name__ == "__main__":
    main()
