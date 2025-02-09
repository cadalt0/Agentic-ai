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
            stdout, stderr = process.communicate(timeout=15)  # Add timeout to prevent hanging

            # Clean output: Remove any lines containing "error" or "warning"
            def clean_output(text):
                return "\n".join(
                    line for line in text.split("\n")
                    if not any(word in line.lower() for word in ["error", "warning"])
                ).strip()

            stdout_clean = clean_output(stdout)
            stderr_clean = clean_output(stderr)

            if stdout_clean:
                responses.append(f" ➜ {stdout_clean}")
            elif stderr_clean:  # If no stdout, but there's a cleaned stderr
                responses.append(f" ➜ {stderr_clean}")

        except subprocess.TimeoutExpired:
            responses.append(f" ➜ Process timeout")
        except FileNotFoundError:
            responses.append(f"{script} ➜ Script not found")
        except Exception as e:
            responses.append(f"{script} ➜ Unknown error occurred")

    # Ensure empty responses aren't returned
    return jsonify({"response": "\n".join(responses) or "No valid response from scripts."})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # Get PORT from Heroku
    app.run(host="0.0.0.0", port=port, debug=False)  # Bind to 0.0.0.0
