import streamlit as st
import hmac


def check_password() -> bool:
    """
    Returns True if the user has entered a valid username + password.
    Credentials are stored in st.secrets["credentials"].
    Blocks the app and shows a login form until authenticated.
    """

    # Already authenticated this session
    if st.session_state.get("authenticated"):
        return True

    # ---- Login form ----
    st.markdown(
        """
        <style>
            .login-container {
                max-width: 400px;
                margin: 80px auto;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    st.title("🔐 Sign In")
    st.markdown("Enter your credentials to access the dashboard.")

    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Sign In", type="primary"):
        _validate_login(username, password)

    if st.session_state.get("login_failed"):
        st.error("❌ Invalid username or password.")

    st.markdown("</div>", unsafe_allow_html=True)

    return False


def _validate_login(username: str, password: str) -> None:
    """Check username + password against st.secrets credentials."""

    credentials = st.secrets.get("credentials", {})
    stored_password = credentials.get(username)

    if stored_password is None:
        # Username not found — use a dummy compare to prevent timing attacks
        hmac.compare_digest("dummy", "dummy")
        st.session_state["login_failed"] = True
        return

    # Constant-time comparison to prevent timing attacks
    if hmac.compare_digest(stored_password, password):
        st.session_state["authenticated"] = True
        st.session_state["username"] = username
        st.session_state["login_failed"] = False
        st.rerun()
    else:
        st.session_state["login_failed"] = True


def logout() -> None:
    """Clear authentication state."""
    for key in ["authenticated", "username", "login_failed"]:
        st.session_state.pop(key, None)
    st.rerun()