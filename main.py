import os
from flask import Flask, render_template, request, jsonify
import subprocess

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")  # Serve the frontend

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()

    if not user_input:
        return jsonify({"response": "Please enter a message!"})

    scripts = ["3x.py", "2x.py", "5x.py", "7x.py"]  # Your script names
    responses = []

    for script in scripts:
        try:
            process = subprocess.Popen(
                ["python", script, user_input],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=10)  # Add timeout to prevent hanging

            # Clean output
            def clean_output(text):
                return "\n".join(
                    line for line in text.split("\n")
                    if not any(word in line.lower() for word in ["error", "warning"])
                ).strip()

            stdout_clean = clean_output(stdout)
            if stdout_clean:
                responses.append(f" ➜ {stdout_clean}")
            elif stderr:
                responses.append(f"{script} ➜ Error: {stderr.strip()}")

        except subprocess.TimeoutExpired:
            responses.append(f"{script} ➜ Error: Process timeout")
        except FileNotFoundError:
            responses.append(f"{script} ➜ Error: Script not found")
        except Exception as e:
            responses.append(f"")

    return jsonify({"response": "\n".join(responses) or "No response from scripts."})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # Get PORT from Heroku
    app.run(host="0.0.0.0", port=port, debug=False)  # Bind to 0.0.0.0
