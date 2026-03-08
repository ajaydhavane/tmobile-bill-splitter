import pandas as pd
import streamlit as st

from config import format_phone, load_config, save_config, valid_email, valid_phone
from mail import Mail, build_email_html
from parser import parse_bills


def update_bill_totals() -> None:
    if "bill_editor" in st.session_state and "bill_df" in st.session_state:
        edits = st.session_state["bill_editor"]["edited_rows"]
        df = st.session_state["bill_df"]

        charge_cols = ["Plan Cost", "Equipment", "Services", "Extra Charges"]

        for row_idx, changes in edits.items():
            for col, val in changes.items():
                df.at[row_idx, col] = float(val) if val is not None else 0.0
            df.at[row_idx, "Total Amount"] = df.loc[row_idx, charge_cols].sum().round(2)
        st.session_state["bill_df"] = df


def clear_bill_data() -> None:
    if "bill_df" in st.session_state:
        del st.session_state["bill_df"]


def render_sidebar(config: dict) -> None:
    with st.sidebar:
        st.header("⚙️ Settings")

        with st.expander("👤 Family Manager"):
            manager = config.get("family_manager", {})
            mgr_email = st.text_input(
                "Email",
                value=manager.get("email", ""),
                key="mgr_email",
                help="Email address used to send bill breakdown email",
            )
            mgr_password = st.text_input(
                "Email App Password",
                value=manager.get("password", ""),
                type="password",
                key="mgr_pass",
            )
            st.caption(
                "[How do I get an App Password?](https://support.google.com/accounts/answer/185833)",
            )
            if st.button("💾 Save Manager", width="stretch"):
                config["family_manager"] = {
                    "email": mgr_email,
                    "password": mgr_password,
                }
                save_config(config)
                st.success("Saved!")

        with st.expander("👥 Users", expanded=True):
            users = config.get("users", {})

            h1, h2, h3, h4 = st.columns([2.5, 2.5, 3.5, 1])
            h1.caption("Name")
            h2.caption("Phone")
            h3.caption("Email")
            h4.write("")

            for phone, info in list(users.items()):
                col1, col2, col3, col4 = st.columns([2.5, 2.5, 3.5, 1])
                col1.text_input(
                    "Name",
                    value=info.get("name", ""),
                    key=f"name_{phone}",
                    label_visibility="collapsed",
                )
                col2.text_input(
                    "Phone",
                    value=phone,
                    key=f"phone_{phone}",
                    label_visibility="collapsed",
                )
                col3.text_input(
                    "Email",
                    value=info.get("email", ""),
                    key=f"email_{phone}",
                    label_visibility="collapsed",
                )

                if col4.button("🗑️", key=f"del_{phone}"):
                    del config["users"][phone]
                    save_config(config)
                    clear_bill_data()
                    st.rerun()

            st.divider()

            st.markdown("**Add New User**")
            with st.form("add_user_form", clear_on_submit=True):
                n_phone = st.text_input("Phone", placeholder="(123) 456-7890")
                n_name = st.text_input("Name", placeholder="Name")
                n_email = st.text_input("Email", placeholder="email@example.com")
                submit = st.form_submit_button("➕ Add User", width="stretch")

                if submit and n_phone and n_name:
                    if not valid_phone(n_phone) or not valid_email(n_email):
                        st.error("Invalid phone number or email.")
                    else:
                        formatted_phone = format_phone(n_phone)
                        config["users"][formatted_phone] = {
                            "name": n_name,
                            "email": n_email,
                        }
                        save_config(config)
                        clear_bill_data()
                        st.rerun()

            if st.button("💾 Save All Changes", width="stretch"):
                new_users = {}
                for phone, info in users.items():
                    raw_phone = st.session_state.get(f"phone_{phone}", phone)
                    email = info.get("email", "")
                    if not valid_phone(raw_phone) or not valid_email(email):
                        st.error(f"Invalid phone number {raw_phone} or email {email}.")
                        st.stop()
                    formatted_phone = format_phone(raw_phone)
                    new_users[formatted_phone] = {
                        "name": st.session_state.get(
                            f"name_{phone}", info.get("name", ""),
                        ),
                        "email": st.session_state.get(
                            f"email_{phone}", info.get("email", ""),
                        ),
                    }
                config["users"] = new_users
                save_config(config)
                clear_bill_data()
                st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="T-Mobile Bill Splitter", page_icon="🧾", layout="wide",
    )
    try:
        config = load_config()
    except Exception as e:
        st.error(f"Could not load users.json: {e}")
        st.stop()

    render_sidebar(config)

    st.title("🧾 T-Mobile Bill Splitter")
    st.markdown("Upload your T-Mobile PDF to calculate shares and notify the group.")

    uploaded_files = st.file_uploader(
        "Drop PDF bills here",
        type="pdf",
        accept_multiple_files=True,
    )

    if uploaded_files:
        files_key = tuple(f.name for f in uploaded_files)
        if st.session_state.get("files_key") != files_key:
            st.session_state["files_key"] = files_key
            st.session_state.pop("bill_df", None)

        if "bill_df" not in st.session_state:
            with st.status("Parsing PDFs...", expanded=False) as status:
                try:
                    all_extracted_users = parse_bills(uploaded_files, config)
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
                    st.session_state["bill_df"] = df
                except Exception as e:
                    st.error(f"Error parsing PDFs: {e}")
                status.update(label="Parsing complete!", state="complete")

        if "bill_df" in st.session_state:
            st.subheader("1. Review Extracted Charges")

            st.data_editor(
                st.session_state["bill_df"],
                width="stretch",
                disabled=["User", "Total Amount"],
                hide_index=True,
                key="bill_editor",
                on_change=update_bill_totals,
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

            st.divider()
            st.subheader("2. Compose Email")

            subject = st.text_input("Subject", value="T-Mobile Bill Breakdown")
            email_intro = st.text_area(
                "Intro Text",
                value="Hi everyone, here are your individual shares for the current period:",
                height=80,
            )

            full_html = build_email_html(st.session_state["bill_df"], email_intro)

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


if __name__ == "__main__":
    main()
