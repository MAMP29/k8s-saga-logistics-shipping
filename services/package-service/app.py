from flask import Flask, request, jsonify
import uuid
import os

app = Flask(__name__)

packages = []

@app.route('/create_package', methods=['POST'])
def create_package():
    package_id = f"PKG-{uuid.uuid4().hex[:6].upper()}"
    package = {"packageId": package_id, "status": "PACKAGED"}
    packages.append(package)
    return jsonify({"package": package}), 201

@app.route('/cancel_package', methods=['POST'])
def cancel_package():
    data = request.get_json()
    package_id = data.get("packageId")
    for p in packages:
        if p["packageId"] == package_id:
            p["status"] = "CANCELLED"
            return jsonify({"package": p}), 200
    return jsonify({"error": "Package not found"}), 404

@app.route('/packages', methods=['GET'])
def get_packages():
    return jsonify({"packages": packages}), 200

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

if __name__ == '__main__':
    port = int(os.getenv("SERVICE_PORT", 5003))
    app.run(host='0.0.0.0', port=port)