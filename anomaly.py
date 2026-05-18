import numpy as np

class AnomalyDetector:
    def __init__(self, threshold=2):
        self.threshold = threshold  # Z-score threshold

    def detect(self, rewards):
        if len(rewards) < 5:
            return False, None  # Not enough data

        mean = np.mean(rewards)
        std = np.std(rewards)

        if std == 0:
            return False, None

        z_scores = [(r - mean) / std for r in rewards]

        anomalies = [i for i, z in enumerate(z_scores) if abs(z) > self.threshold]

        return len(anomalies) > 0, anomalies