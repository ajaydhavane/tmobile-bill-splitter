import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

from mail import Mail
from parser import parse_bills

# Set Page Config
st.set_page_config(page_title="T-Mobile Bill Splitter", page_icon="🧾", layout="wide")

USERS_FILE = Path("users.json")


def load_config():
    if not USERS_FILE.exists():
        USERS_FILE.write_text(json.dumps({"family_manager": {}, "users": {}}, indent=2))
    return json.loads(USERS_FILE.read_text())


def save_config(config: dict) -> None:
    USERS_FILE.write_text(json.dumps(config, indent=2))


def format_phone(phone: str) -> str:
    nums = re.sub(r"\D", "", phone)
    if len(nums) == 10:
        return f"({nums[:3]}) {nums[3:6]}-{nums[6:]}"
    return phone


try:
    config = load_config()
except Exception as e:
    st.error(f"Could not load users.json: {e}")
    st.stop()

# --- Sidebar: Settings ---
with st.sidebar:
    st.header("⚙️ Settings")

    with st.expander("👤 Family Manager"):
        manager = config.get("family_manager", {})
        mgr_email = st.text_input(
            "Email",
            value=manager.get("email", ""),
            key="mgr_email",
        )
        mgr_password = st.text_input(
            "App Password",
            value=manager.get("password", ""),
            type="password",
            key="mgr_pass",
        )
        if st.button("Save Manager", width="stretch"):
            config["family_manager"] = {"email": mgr_email, "password": mgr_password}
            save_config(config)
            st.success("Saved!")

    with st.expander("👥 Users"):
        users = config.get("users", {})

        for phone, info in list(users.items()):
            st.markdown(f"**{info.get('name', phone)}**")
            col1, col2, col3 = st.columns([2, 2, 1])
            new_phone = col1.text_input("Phone", value=phone, key=f"phone_{phone}")
            new_name = col1.text_input(
                "Name",
                value=info.get("name", ""),
                key=f"name_{phone}",
            )
            new_email = col2.text_input(
                "Email",
                value=info.get("email", ""),
                key=f"email_{phone}",
            )
            if col3.button("🗑️", key=f"del_{phone}"):
                del config["users"][phone]
                save_config(config)
                st.rerun()
            st.divider()

        st.markdown("**Add New User**")
        new_phone = st.text_input("Phone (e.g. (123) 456-7890)", key="new_phone")
        new_name = st.text_input("Name", key="new_name")
        new_email = st.text_input("Email", key="new_email")
        if st.button("➕ Add User", width="stretch"):
            if new_phone and new_name:
                formatted_p = format_phone(new_phone)
                config["users"][formatted_p] = {"name": new_name, "email": new_email}
                save_config(config)
                st.success(f"Added {new_name}")
                st.rerun()
            else:
                st.warning("Phone and Name are required.")

        if st.button("💾 Save All Users", width="stretch"):
            new_users = {}
            for phone, info in users.items():
                raw_phone = st.session_state.get(f"phone_{phone}", phone)
                formatted_phone = format_phone(raw_phone)
                if len(formatted_phone) != 14:
                    st.error(f"Invalid format for {raw_phone}. Please use 10 digits.")
                    st.stop()
                new_users[formatted_phone] = {
                    "name": st.session_state.get(f"name_{phone}", info.get("name", "")),
                    "email": st.session_state.get(
                        f"email_{phone}",
                        info.get("email", ""),
                    ),
                }
            config["users"] = new_users
            save_config(config)
            st.success("All users saved!")
            st.rerun()


st.title("🧾 T-Mobile Bill Splitter")
st.markdown("Upload your T-Mobile PDF to calculate shares and notify the group.")

# --- 1. File Upload ---
uploaded_files = st.file_uploader(
    "Drop PDF bills here",
    type="pdf",
    accept_multiple_files=True,
)

if uploaded_files:
    # Reset bill_df when files change
    files_key = tuple(f.name for f in uploaded_files)
    if st.session_state.get("files_key") != files_key:
        st.session_state["files_key"] = files_key
        st.session_state.pop("bill_df", None)

    with st.status("Parsing PDFs...", expanded=False) as status:
        try:
            all_extracted_users = parse_bills(uploaded_files, config)
        except Exception as e:
            st.error(f"Error parsing PDFs: {e}")
            all_extracted_users = []
        status.update(label="Parsing complete!", state="complete")

    if all_extracted_users:
        st.subheader("1. Review Extracted Charges")
        df = pd.DataFrame([vars(u) for u in all_extracted_users])
        column_mapping = {
            "name": "User",
            "plan": "Plan Cost",
            "equipment": "Equipment",
            "services": "Services",
            "one_time_charges": "Extra Charges",
            "total": "Total Amount",
        }
        df = df.rename(columns=column_mapping)

        charge_cols = ["Plan Cost", "Equipment", "Services", "Extra Charges"]

        if "bill_df" not in st.session_state:
            st.session_state["bill_df"] = df

        render_df = st.session_state["bill_df"].copy()
        render_df[charge_cols] = render_df[charge_cols].round(2)
        render_df["Total Amount"] = render_df[charge_cols].sum(axis=1).round(2)

        edited_df = st.data_editor(
            render_df,
            width="stretch",
            disabled=["User", "Total Amount"],
            hide_index=True,
            column_config={
                col: st.column_config.NumberColumn(format="%.2f")
                for col in [
                    "Plan Cost",
                    "Equipment",
                    "Services",
                    "Extra Charges",
                    "Total Amount",
                ]
            },
        )

        # Replace None with 0, recalculate totals, rerun if anything changed
        cleaned = edited_df.copy()
        cleaned[charge_cols] = cleaned[charge_cols].replace({None: 0.0}).fillna(0.0)
        cleaned["Total Amount"] = cleaned[charge_cols].sum(axis=1).round(2)
        if not cleaned.equals(st.session_state["bill_df"]):
            st.session_state["bill_df"] = cleaned
            st.rerun()

        st.divider()
        st.subheader("2. Compose Email")

        subject = st.text_input("Subject", value="T-Mobile Bill Breakdown")
        email_intro = st.text_area(
            "Intro Text",
            value="Hi everyone, here are your individual shares for the current period:",
            height=80,
        )

        # --- HTML Email Generation (fully inlined for Gmail compatibility) ---
        def build_email_html(df: pd.DataFrame, intro: str) -> str:
            th_style = 'style="font-family:Arial,sans-serif;font-size:14px;color:#222;background-color:#ffffff;padding:10px 12px;border-bottom:2px solid #333;text-align:left;font-weight:bold;"'
            td_style = 'style="font-family:Arial,sans-serif;font-size:14px;color:#444;background-color:#ffffff;padding:10px 12px;border-bottom:1px solid #dddddd;"'

            header_cells = "".join(f"<th {th_style}>{col}</th>" for col in df.columns)
            rows = ""
            for _, row in df.iterrows():
                formatted_cells = []
                for val in row:
                    if isinstance(val, (int, float)):
                        formatted_cells.append(f"<td {td_style}>{val:.2f}</td>")
                    else:
                        formatted_cells.append(f"<td {td_style}>{val}</td>")
                rows += f"<tr>{''.join(formatted_cells)}</tr>"

            return f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;background-color:#ffffff;padding:16px;">
                <p style="font-family:Arial,sans-serif;font-size:14px;color:#444;">{intro}</p>
                <table style="width:100%;border-collapse:collapse;margin-top:16px;" cellpadding="0" cellspacing="0">
                    <thead><tr>{header_cells}</tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
            """

        full_html = build_email_html(cleaned, email_intro)

        st.divider()
        st.subheader("3. Finalize")

        with st.expander("Preview Email"):
            st.markdown(full_html, unsafe_allow_html=True)

        if st.button("🚀 Send Emails to Everyone", width="stretch"):
            with st.spinner("Dispatching..."):
                mailer = Mail(config, subject, full_html)
                success, msg = mailer.send()
                if success:
                    st.success(f"Sent: {msg}")
                else:
                    st.error(msg)
    else:
        st.warning(
            "No users found in the bill. Make sure phone numbers in Settings match the PDF."
        )
