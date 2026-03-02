import os
import requests
import base64

def send_email(state: ResearchState):
    state["log"](f"📤 Sending email to {state['receiver_email']} via Resend...")

    try:
        api_key = os.getenv("RESEND_API_KEY")  # set this in Render dashboard
        url = "https://api.resend.com/emails"

        payload = {
            "from": "mahadevsputhri@yourdomain.com",  # must be verified in Resend
            "to": state["receiver_email"],
            "subject": f"🔬 Research Report: {state['topic']}",
            "html": state["email_body"]
        }

        # Attach DOCX if available
        if os.path.exists("published_research_paper.docx"):
            with open("published_research_paper.docx", "rb") as f:
                file_data = f.read()
            payload["attachments"] = [{
                "filename": "published_research_paper.docx",
                "content": base64.b64encode(file_data).decode("utf-8")
            }]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            state["log"](f"✅ Email sent to {state['receiver_email']}!")
        else:
            state["log"](f"❌ Email failed: {response.text}")

    except Exception as e:
        state["log"](f"❌ Email failed: {e}")
    return {}
