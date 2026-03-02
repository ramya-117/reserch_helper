from flask import Flask, render_template, request, jsonify
from agent import run_research

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/research", methods=["POST"])
def research():
    data = request.get_json()
    topic = data.get("topic", "").strip()

    if not topic:
        return jsonify({"success": False, "error": "Please enter a research topic!"})

    try:
        result = run_research(topic)
        papers = result.get("papers", [])

        paper_list = []
        for p in papers:
            paper_list.append({
                "title":   p.get("title", ""),
                "authors": p.get("authors", ""),
                "journal": p.get("journal", ""),
                "year":    p.get("year", ""),
                "doi":     p.get("doi", "")
            })

        return jsonify({
            "success":    True,
            "topic":      topic,
            "papers":     paper_list,
            "outline":    result.get("outline", "")[:2000],
            "draft":      result.get("draft", "")[:3000],
            "email_sent": True
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
