"""
Copyright Act 1956 — Search Agent UI
Queries the deployed AgentCore runtime.
"""
import boto3
import json
import uuid
import streamlit as st

AGENT_ARN = "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/CopyrightActAgent_CopyrightActAgent-gCQPEN6NmY"
REGION = "us-west-2"

st.set_page_config(page_title="Copyright Act 1956 — Search", page_icon="📜", layout="wide")

st.title("📜 Copyright Act 1956 — Search Agent")
st.caption(
    "Powered by Amazon Bedrock AgentCore · "
    "[Source: legislation.gov.uk](https://www.legislation.gov.uk/ukpga/Eliz2/4-5/74/contents/enacted) "
    "— Open Government Licence v3.0"
)
st.warning(
    "⚠️ This tool is for **informational purposes only** and does **not** constitute legal advice. "
    "Please consult a qualified legal professional for any legal matters.",
    icon="⚠️",
)


@st.cache_resource
def get_client():
    return boto3.client("bedrock-agentcore", region_name=REGION)


if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4()) + "-extra-chars-for-length"

# Sidebar
with st.sidebar:
    st.header("About")
    st.markdown(
        "This agent searches all **51 sections** and **9 schedules** of the "
        "UK Copyright Act 1956 using semantic search powered by "
        "Amazon Bedrock Knowledge Bases."
    )
    st.divider()
    st.markdown("**Example queries:**")
    st.markdown("- What is fair dealing for criticism?")
    st.markdown("- What are the penalties for copyright infringement?")
    st.markdown("- Who owns copyright in works made during employment?")
    st.markdown("- What does the Act say about sound recordings?")
    st.markdown("- How long does copyright last?")
    st.divider()
    if st.button("🔄 New conversation"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4()) + "-extra-chars-for-length"
        st.rerun()

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask about the Copyright Act 1956..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            client = get_client()
            payload = json.dumps({"prompt": prompt})
            
            status = st.status("Searching the Copyright Act 1956...", expanded=False)
            
            response = client.invoke_agent_runtime(
                agentRuntimeArn=AGENT_ARN,
                runtimeSessionId=st.session_state.session_id,
                payload=payload,
                qualifier="DEFAULT",
            )
            
            status.update(label="Generating response...", state="running")
            placeholder = st.empty()
            full = ""
            raw = response["response"].read().decode("utf-8")
            for line in raw.split("\n"):
                if line.startswith("data: "):
                    chunk = line[6:]
                    if chunk.startswith('"') and chunk.endswith('"'):
                        chunk = json.loads(chunk)
                    full += chunk
                    placeholder.markdown(full + "▌")
            placeholder.markdown(full)
            status.update(label="Done", state="complete")
            st.session_state.messages.append({"role": "assistant", "content": full})
        except Exception as e:
            err = f"Error querying agent: {e}"
            st.error(err)
            st.session_state.messages.append({"role": "assistant", "content": err})
