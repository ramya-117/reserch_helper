from flask import Flask, render_template, request, jsonify, send_file
import threading
import uuid
import os
from agent import run_research_agent

app = Flask(__name__)

# Store job statuses in memory
jobs = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/run", methods=["POST"])
def run():
    data = request.json
    topic = data.get("topic", "").strip()
    email = data.get("email", "").strip()

    if not topic or not email:
        return jsonify({"error": "Topic and email are required."}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running", "logs": [], "done": False, "error": None}

    def task():
        try:
            logs = []
            run_research_agent(topic, email, log_callback=lambda msg: logs.append(msg))
            jobs[job_id]["status"] = "done"
            jobs[job_id]["logs"] = logs
            jobs[job_id]["done"] = True
        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)
            jobs[job_id]["done"] = True

    threading.Thread(target=task).start()
    return jsonify({"job_id": job_id})

@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    port = int(os.environ.get("PORT", 7860))