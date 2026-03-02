from flask import Flask, render_template, request, jsonify
from agent import run_research

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/research", methods=["POST"])
def research():
    data  = request.get_json()
    topic = data.get("topic", "").strip()
    email = data.get("email", "").strip()

    if not topic:
        return jsonify({"success": False, "error": "Please enter a research topic!"})
    if not email or "@" not in email:
        return jsonify({"success": False, "error": "Please enter a valid email!"})

    try:
        result = run_research(topic, email)
        paper_list = [{"title": p.get("title",""), "authors": p.get("authors",""),
                       "journal": p.get("journal",""), "year": p.get("year",""),
                       "doi": p.get("doi","")} for p in result.get("papers", [])]
        return jsonify({"success": True, "topic": topic, "email": email,
                        "papers": paper_list, "outline": result.get("outline","")[:2000],
                        "draft": result.get("draft","")[:3000],
                        "email_sent": result.get("email_sent", False)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)

```
gunicorn app:app
