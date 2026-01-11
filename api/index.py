import os
import uuid
import subprocess
import zipfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_TMP = "/tmp"


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Flask + nd-sdk running on Vercel 🚀"
    })


# ---------- Helpers ----------

def run_nd_sdk(yaml_path, work_dir):
    """
    Run nd-sdk generate command
    """
    result = subprocess.run(
        ["nd-sdk", "generate", "-c", yaml_path],
        cwd=work_dir,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return result.stdout


def folder_preview(base_path):
    """
    Generate metadata preview of folder
    """
    tree = []
    total_files = 0
    total_dirs = 0

    for root, dirs, files in os.walk(base_path):
        rel_path = os.path.relpath(root, base_path)
        total_dirs += len(dirs)
        total_files += len(files)

        tree.append({
            "path": rel_path if rel_path != "." else "/",
            "dirs": dirs,
            "files": files
        })

    return {
        "total_folders": total_dirs,
        "total_files": total_files,
        "structure": tree
    }


def zip_folder(folder_path, zip_path):
    """
    Zip generated folder
    """
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, folder_path)
                zipf.write(abs_path, rel_path)


# ---------- Main API ----------

@app.route("/generate", methods=["POST"])
def generate():
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(BASE_TMP, job_id)
    os.makedirs(job_dir, exist_ok=True)

    yaml_path = os.path.join(job_dir, "input.yaml")

    # ---- Read YAML ----
    if "file" in request.files:
        request.files["file"].save(yaml_path)
    elif request.is_json and "yaml" in request.json:
        with open(yaml_path, "w") as f:
            f.write(request.json["yaml"])
    else:
        return jsonify({"error": "YAML file or yaml field required"}), 400

    try:
        # ---- Run nd-sdk ----
        run_nd_sdk(yaml_path, job_dir)

        generated_dir = os.path.join(job_dir, "generated")
        if not os.path.exists(generated_dir):
            return jsonify({"error": "nd-sdk did not generate output"}), 500

        # ---- Preview ----
        preview = folder_preview(generated_dir)

        # ---- Zip ----
        zip_path = os.path.join(job_dir, "output.zip")
        zip_folder(generated_dir, zip_path)

        # ---- Response ----
        return jsonify({
            "job_id": job_id,
            "preview": preview,
            "download_url": f"/download/{job_id}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download/<job_id>", methods=["GET"])
def download(job_id):
    zip_path = os.path.join(BASE_TMP, job_id, "output.zip")

    if not os.path.exists(zip_path):
        return jsonify({"error": "File not found"}), 404

    return send_file(
        zip_path,
        as_attachment=True,
        download_name="generated.zip"
    )


# IMPORTANT:
# Do NOT use app.run()
# Vercel will import `app` automatically
