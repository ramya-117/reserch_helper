import re
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from docx import Document
import io

# ─────────────────────────────────────────
# CREDENTIALS (only sender is fixed)
# ─────────────────────────────────────────
GROQ_API_KEY   = "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"
EMAIL_SENDER   = "mahadevsputhri@gmail.com"
EMAIL_PASSWORD = "trsi ximj dxym wjoh"

# ─────────────────────────────────────────
# LLM
# ─────────────────────────────────────────
llm = ChatOpenAI(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    temperature=0.3,
)

# ─────────────────────────────────────────
# STATE
# ─────────────────────────────────────────
class ResearchState(TypedDict):
    topic: str
    email: str
    papers: List[dict]
    summaries: List[str]
    outline: str
    draft: str
    references: List[str]
    email_body: str

# ─────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────
def clean_abstract(text: str) -> str:
    if not text:
        return "Abstract not available."
    return re.sub("<.*?>", "", text)

# ─────────────────────────────────────────
# 1. SEARCH PAPERS
# ─────────────────────────────────────────
def search_published_papers(state: ResearchState):
    url = "https://api.crossref.org/works"
    params = {"query": state["topic"], "rows": 5, "sort": "relevance"}
    try:
        response = requests.get(url, params=params, timeout=15)
        items = response.json().get("message", {}).get("items", [])
    except Exception:
        return {"papers": [], "references": []}

    papers, references = [], []
    for paper in items:
        title       = paper.get("title", ["Untitled"])[0]
        year        = paper.get("issued", {}).get("date-parts", [[None]])[0][0]
        journal     = paper.get("container-title", ["Unknown Journal"])[0] if paper.get("container-title") else "Unknown Journal"
        doi         = paper.get("DOI", "")
        abstract    = clean_abstract(paper.get("abstract", ""))
        authors     = [f"{a.get('family','')} {a.get('given','')}" for a in paper.get("author", [])]
        authors_str = ", ".join(authors) if authors else "Unknown Author"

        papers.append({
            "title": title, "abstract": abstract, "year": year,
            "journal": journal, "authors": authors_str, "doi": doi
        })
        references.append(
            f"{authors_str} ({year}). {title}. {journal}. https://doi.org/{doi}"
        )

    return {"papers": papers, "references": references}

# ─────────────────────────────────────────
# 2. SUMMARIZE PAPERS
# ─────────────────────────────────────────
def summarize_papers(state: ResearchState):
    summaries = []
    for paper in state["papers"]:
        prompt = f"""
You are an academic research assistant. Summarize this paper.

Structure:
1. KEY CONTRIBUTION: What is the main contribution?
2. METHODOLOGY: What methods were used?
3. KEY FINDINGS: What are the main results?
4. LIMITATIONS: What are the limitations?

Title: {paper['title']}
Authors: {paper['authors']}
Journal: {paper['journal']} ({paper['year']})
Abstract: {paper['abstract']}
"""
        response = llm.invoke(prompt)
        summaries.append(f"Paper: {paper['title']}\n{response.content}")
    return {"summaries": summaries}

# ─────────────────────────────────────────
# 3. GENERATE OUTLINE
# ─────────────────────────────────────────
def generate_outline(state: ResearchState):
    summaries_text = "\n\n---\n\n".join(state["summaries"])
    prompt = f"""
You are an expert academic researcher. Create a structured research paper outline.

Topic: {state['topic']}
Literature Review Summaries:
{summaries_text}

Include: Introduction, Literature Review, Methodology, Results, Conclusion, Future Work.
"""
    response = llm.invoke(prompt)
    return {"outline": response.content}

# ─────────────────────────────────────────
# 4. WRITE DRAFT
# ─────────────────────────────────────────
def write_draft(state: ResearchState):
    prompt = f"""
You are a senior academic researcher. Write a complete formal research paper.

Topic: {state['topic']}
Outline: {state['outline']}

Instructions:
- APA-style in-text citations
- Formal academic tone
- Full paragraphs only
- Minimum 1000 words
- Include abstract at the beginning
"""
    response = llm.invoke(prompt)
    return {"draft": response.content}

# ─────────────────────────────────────────
# 5. BUILD DOCX IN MEMORY
# ─────────────────────────────────────────
_docx_store = {}

def export_doc(state: ResearchState):
    doc = Document()
    doc.add_heading(state["topic"], level=1)
    doc.add_heading("Research Paper", level=2)
    doc.add_paragraph(state["draft"])
    doc.add_heading("Literature Review Summaries", level=2)
    for summary in state["summaries"]:
        doc.add_paragraph(summary)
        doc.add_paragraph("")
    doc.add_heading("References", level=2)
    for ref in state["references"]:
        doc.add_paragraph(ref)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    _docx_store["buffer"] = buffer.getvalue()
    return {}

# ─────────────────────────────────────────
# 6. PREPARE EMAIL HTML
# ─────────────────────────────────────────
def prepare_email(state: ResearchState):
    papers    = state["papers"]
    summaries = state["summaries"]
    rows = ""
    for i, (paper, summary) in enumerate(zip(papers, summaries)):
        contribution = ""
        for line in summary.split("\n"):
            if "KEY CONTRIBUTION" in line.upper():
                contribution = line.replace("1.", "").replace("KEY CONTRIBUTION:", "").strip()
                break
        bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
        rows += f"""
        <tr style="background:{bg}">
            <td style="padding:12px;font-weight:bold;color:#2c3e50;">[{i+1}] {paper['title']}</td>
        </tr>
        <tr style="background:{bg}">
            <td style="padding:0 12px 12px 12px;color:#555;font-size:13px;">
                👤 <b>Authors:</b> {paper['authors']}<br>
                📰 <b>Journal:</b> {paper['journal']} ({paper['year']})<br>
                🔗 <b>DOI:</b> <a href="https://doi.org/{paper['doi']}">https://doi.org/{paper['doi']}</a><br>
                💡 <b>Key Contribution:</b> {contribution}
            </td>
        </tr>"""

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;color:#333;">
        <div style="background:#2c3e50;color:white;padding:20px;border-radius:8px 8px 0 0;">
            <h1 style="margin:0;font-size:22px;">🔬 AI Research Agent Report</h1>
            <p style="margin:5px 0 0;opacity:0.8;">Automated Literature Review & Summary</p>
        </div>
        <div style="background:#ecf0f1;padding:15px;">
            <p style="margin:0;"><b>📌 Topic:</b> {state['topic']}</p>
            <p style="margin:5px 0 0;"><b>📚 Papers Analyzed:</b> {len(papers)}</p>
        </div>
        <div style="padding:20px 0;">
            <h2 style="color:#2c3e50;border-bottom:2px solid #3498db;padding-bottom:5px;">📄 Paper Summaries</h2>
            <table width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #ddd;border-radius:6px;">
                {rows}
            </table>
        </div>
        <div style="padding:0 0 20px 0;">
            <h2 style="color:#2c3e50;border-bottom:2px solid #3498db;padding-bottom:5px;">📋 Research Outline</h2>
            <div style="background:#f4f4f4;padding:15px;border-radius:6px;white-space:pre-wrap;font-size:13px;">
{state['outline'][:1500]}...
            </div>
        </div>
        <div style="background:#2ecc71;color:white;padding:15px;border-radius:6px;text-align:center;">
            ✅ Full research paper attached as <b>research_paper.docx</b>
        </div>
        <div style="text-align:center;padding:15px;color:#aaa;font-size:12px;">
            Generated by AI Research Agent • Groq LLaMA-3 & Crossref API
        </div>
    </body></html>"""
    return {"email_body": html}

# ─────────────────────────────────────────
# 7. SEND EMAIL — to user's email
# ─────────────────────────────────────────
def send_email(state: ResearchState):
    user_email = state["email"]   # ← user typed this in the UI
    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"🔬 Research Report: {state['topic']}"
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = user_email
        msg.attach(MIMEText(state["email_body"], "html"))

        if "buffer" in _docx_store:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(_docx_store["buffer"])
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment; filename=research_paper.docx")
            msg.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, user_email, msg.as_string())

        return {"email_sent": True}
    except Exception as e:
        return {"email_sent": False, "error": str(e)}

# ─────────────────────────────────────────
# BUILD WORKFLOW
# ─────────────────────────────────────────
def build_workflow():
    workflow = StateGraph(ResearchState)
    workflow.add_node("search",        search_published_papers)
    workflow.add_node("summarize",     summarize_papers)
    workflow.add_node("outline",       generate_outline)
    workflow.add_node("write",         write_draft)
    workflow.add_node("export",        export_doc)
    workflow.add_node("prepare_email", prepare_email)
    workflow.add_node("send_email",    send_email)
    workflow.set_entry_point("search")
    workflow.add_edge("search",        "summarize")
    workflow.add_edge("summarize",     "outline")
    workflow.add_edge("outline",       "write")
    workflow.add_edge("write",         "export")
    workflow.add_edge("export",        "prepare_email")
    workflow.add_edge("prepare_email", "send_email")
    workflow.add_edge("send_email",    END)
    return workflow.compile()

# ─────────────────────────────────────────
# MAIN — called by app.py
# ─────────────────────────────────────────
def run_research(topic: str, email: str) -> dict:
    _docx_store.clear()
    app = build_workflow()
    result = app.invoke({
        "topic": topic,
        "email": email,
        "papers": [],
        "summaries": [],
        "outline": "",
        "draft": "",
        "references": [],
        "email_body": ""
    })
    return result
