from flask import Flask, render_template, request, jsonify
import subprocess

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")  # Serve the frontend

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "")

    if not user_input:
        return jsonify({"response": "Please enter a message!"})

    scripts = ["3x.py", "2x.py", "5x.py" ,"7x.py"]  # Your script names
    responses = []

    for script in scripts:
        try:
            process = subprocess.Popen(
                ["python", script, user_input],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()

            # Clean output
            def clean_output(text):
                return "\n".join(
                    line for line in text.split("\n")
                    if not any(word in line.lower() for word in ["error", "warning"])
                ).strip()

            stdout_clean = clean_output(stdout)
            if stdout_clean:
                responses.append(f" ➜ {stdout_clean}")

        except Exception as e:
            responses.append(f"{script} ➜ Error: {e}")

    return jsonify({"response": "\n".join(responses) or "No response from scripts."})

if __name__ == "__main__":
    app.run(debug=True)
