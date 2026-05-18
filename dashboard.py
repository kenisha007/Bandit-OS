import streamlit as st
import requests
import pandas as pd

BASE_URL = "http://127.0.0.1:5000"


def safe_json(response):
    """Parse JSON safely and show a helpful error if Flask is not running."""
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        st.error(
            f"❌ Could not parse response from Flask backend.\n\n"
            f"**HTTP status:** {response.status_code}\n\n"
            f"**Raw response:** `{response.text[:300] or '(empty)'}`\n\n"
            "Make sure `app.py` is running (`python app.py`) before using this dashboard."
        )
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        return None


def check_backend():
    """Return True if the Flask backend is reachable."""
    try:
        requests.get(BASE_URL, timeout=2)
        return True
    except requests.exceptions.ConnectionError:
        return False


# ── Backend health banner ──────────────────────────────────────────────────────
if not check_backend():
    st.warning(
        "⚠️ Flask backend is not running at `http://127.0.0.1:5000`. "
        "Start it with `python app.py` in a separate terminal, then refresh."
    )

st.title("BanditOS Dashboard")

# ── Create Experiment ──────────────────────────────────────────────────────────
st.header("Create Experiment")
exp_id = st.text_input("Experiment ID")
variants = st.text_input("Variants (comma separated, e.g. A,B)")

if st.button("Create"):
    if not exp_id or not variants:
        st.warning("Please fill in both Experiment ID and Variants.")
    else:
        try:
            response = requests.post(
                f"{BASE_URL}/create_experiment",
                json={
                    "experiment_id": exp_id,
                    "variants": [v.strip() for v in variants.split(",")],
                },
                timeout=5,
            )
            data = safe_json(response)
            if data is not None:
                st.success(f"✅ {data.get('message', 'Created!')}")
                st.json(data)
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to Flask backend. Is `python app.py` running?")

# ── Assign Variant ─────────────────────────────────────────────────────────────
st.header("Assign Variant")
assign_exp = st.text_input("Experiment ID for assignment")

if st.button("Assign"):
    if not assign_exp:
        st.warning("Please enter an Experiment ID.")
    else:
        try:
            response = requests.get(
                f"{BASE_URL}/assign_variant",
                params={"experiment_id": assign_exp},
                timeout=5,
            )
            data = safe_json(response)
            if data is not None:
                if "error" in data:
                    st.error(data["error"])
                else:
                    st.success(f"Assigned variant: **{data.get('assigned_variant')}**")
                    st.json(data)
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to Flask backend.")

# ── Record Click ───────────────────────────────────────────────────────────────
st.header("Record Click")
click_exp = st.text_input("Experiment ID for click")
variant = st.text_input("Variant (A/B)")
reward = st.selectbox("Reward", [0, 1])

if st.button("Submit Click"):
    if not click_exp or not variant:
        st.warning("Please fill in Experiment ID and Variant.")
    else:
        try:
            response = requests.post(
                f"{BASE_URL}/record_click",
                json={"experiment_id": click_exp, "variant": variant, "reward": reward},
                timeout=5,
            )
            data = safe_json(response)
            if data is not None:
                if "error" in data:
                    st.error(data["error"])
                else:
                    st.success("Click recorded!")
                    st.json(data)
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to Flask backend.")

# ── Experiment Status ──────────────────────────────────────────────────────────
st.header("Check Status")
status_exp = st.text_input("Experiment ID for status")

if st.button("Check"):
    if not status_exp:
        st.warning("Please enter an Experiment ID.")
    else:
        try:
            response = requests.get(
                f"{BASE_URL}/experiment_status",
                params={"experiment_id": status_exp},
                timeout=5,
            )
            data = safe_json(response)
            if data is not None:
                if "error" in data:
                    st.error(data["error"])
                else:
                    st.json(data)
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to Flask backend.")

# ── Analytics ──────────────────────────────────────────────────────────────────
st.header("📊 Analytics")
analytics_exp = st.text_input("Experiment ID for analytics", key="analytics_input")

if st.button("Load Analytics"):
    if not analytics_exp:
        st.warning("Please enter an Experiment ID.")
    else:
        try:
            status_res = requests.get(
                f"{BASE_URL}/experiment_status",
                params={"experiment_id": analytics_exp},
                timeout=5,
            )
            data = safe_json(status_res)
            if data is not None:
                if "error" in data:
                    st.error(data["error"])
                elif "traffic_split" in data:
                    traffic = data["traffic_split"]
                    df = pd.DataFrame(
                        {"Variant": list(traffic.keys()), "Traffic %": list(traffic.values())}
                    )
                    st.subheader("Traffic Split")
                    st.bar_chart(df.set_index("Variant"))
                else:
                    st.error("No traffic data found for this experiment.")
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to Flask backend.")

# ── Click Data ─────────────────────────────────────────────────────────────────
clicks_exp = st.text_input("Experiment ID for clicks", key="clicks_input")

if st.button("Load Click Data"):
    if not clicks_exp:
        st.warning("Please enter an Experiment ID.")
    else:
        try:
            res = requests.get(
                f"{BASE_URL}/analytics",
                params={"experiment_id": clicks_exp},
                timeout=5,
            )
            response_data = safe_json(res)
            if response_data is not None:
                data = response_data.get("clicks", [])
                if len(data) > 0:
                    df = pd.DataFrame(data)
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df = df.sort_values("timestamp")

                    st.subheader("Click Data Table")
                    st.write(df)

                    summary = df.groupby("variant")["reward"].sum()
                    st.subheader("Total Clicks per Variant")
                    st.bar_chart(summary)

                    st.subheader("📈 Click Trend Over Time")
                    trend = (
                        df.groupby(["timestamp", "variant"])["reward"]
                        .sum()
                        .unstack()
                        .fillna(0)
                    )
                    st.line_chart(trend)

                    if response_data.get("anomaly"):
                        st.error("🚨 Anomaly Detected in Click Behavior!")
                    else:
                        st.success("✅ No Anomaly Detected")
                else:
                    st.warning("No click data yet for this experiment.")
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to Flask backend.")
