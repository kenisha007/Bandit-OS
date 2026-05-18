from flask import Flask, request, jsonify
from pymongo import MongoClient
from bandit import ThompsonSampling
from datetime import datetime
from anomaly import AnomalyDetector
from dotenv import load_dotenv
import os

app = Flask(__name__)

# Load environment variables
load_dotenv()

# MongoDB Connection (SAFE)
mongo_uri = os.getenv("MONGO_URI")

if not mongo_uri:
    raise ValueError("MONGO_URI not found. Add it in .env file.")

client = MongoClient(mongo_uri)
db = client["bandit_os"]
experiments_col = db["experiments"]
clicks_col = db["clicks"]

# Active experiments stored in memory
active_experiments = {}
detector = AnomalyDetector()

@app.route("/create_experiment", methods=["POST"])
def create_experiment():
    data = request.json
    exp_id = data["experiment_id"]
    variants = data["variants"]
    
    # Create bandit
    active_experiments[exp_id] = ThompsonSampling(variants)
    
    # Store in MongoDB
    experiments_col.insert_one({
        "experiment_id": exp_id,
        "variants": variants,
        "status": "running",
        "created_at": datetime.now(),
        "traffic_split": {v: 50 for v in variants}
    })
    
    return jsonify({"message": f"Experiment {exp_id} created", "variants": variants})

@app.route("/assign_variant", methods=["GET"])
def assign_variant():
    exp_id = request.args.get("experiment_id")
    
    if exp_id not in active_experiments:
        return jsonify({"error": "Experiment not found"}), 404
    
    bandit = active_experiments[exp_id]
    variant = bandit.select_variant()
    
    return jsonify({
        "experiment_id": exp_id,
        "assigned_variant": variant,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/record_click", methods=["POST"])
def record_click():
    data = request.json
    exp_id = data["experiment_id"]
    variant = data["variant"]
    reward = data["reward"]  # 1 = clicked, 0 = ignored
    
    if exp_id not in active_experiments:
        return jsonify({"error": "Experiment not found"}), 404
    
    bandit = active_experiments[exp_id]
    
    # Update bandit with reward
    bandit.update(variant, reward)
    
    # Get updated traffic split
    traffic_split = bandit.get_traffic_split()
    
    # Check for winner
    winner, confidence = bandit.get_winner()
    
    # Store click event in MongoDB
    clicks_col.insert_one({
        "experiment_id": exp_id,
        "variant": variant,
        "reward": reward,
        "traffic_split": traffic_split,
        "timestamp": datetime.now()
    })
    
    # Update experiment in MongoDB
    experiments_col.update_one(
        {"experiment_id": exp_id},
        {"$set": {
            "traffic_split": traffic_split,
            "winner": winner,
            "confidence": confidence,
            "status": "completed" if winner else "running"
        }}
    )
    
    return jsonify({
        "traffic_split": traffic_split,
        "winner": winner,
        "confidence": round(confidence * 100, 1) if confidence else None
    })

@app.route("/experiment_status", methods=["GET"])
def experiment_status():
    exp_id = request.args.get("experiment_id")
    exp = experiments_col.find_one({"experiment_id": exp_id}, {"_id": 0})
    if not exp:
        return jsonify({"error": "Not found"}), 404
    return jsonify(exp)

@app.route("/analytics", methods=["GET"])
def analytics():
    exp_id = request.args.get("experiment_id")

    clicks = list(clicks_col.find(
        {"experiment_id": exp_id},
        {"_id": 0}
    ))

    rewards = [c["reward"] for c in clicks]

    is_anomaly, indices = detector.detect(rewards)

    return jsonify({
        "clicks": clicks,
        "anomaly": is_anomaly,
        "indices": indices
    })

if __name__ == "__main__":
    app.run(debug=True)