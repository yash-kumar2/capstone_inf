import streamlit as st
import psycopg

st.set_page_config(page_title="Invoice Auditor", layout="wide")


@st.cache_resource

def connect_db() -> psycopg.Connection:
    import os

    return psycopg.connect(
        dbname=os.getenv("POSTGRES_DB", "invoice_auditor"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )


st.title("AI Invoice Auditor")
st.sidebar.markdown("### Database")
st.sidebar.success("Database: connected")

try:
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT invoice_id, file_name, file_type, processing_status, detected_at FROM audit.invoice_audit ORDER BY detected_at DESC"
            )
            rows = cur.fetchall()
except Exception as exc:
    st.error(f"Database connection failed: {exc}")
    st.stop()

if not rows:
    st.info("No invoices detected yet.")
    st.stop()

st.subheader("Invoices")
columns = ["invoice_id", "file_name", "file_type", "processing_status", "detected_at"]
st.dataframe(rows, hide_index=True, use_container_width=True, column_order=columns)
