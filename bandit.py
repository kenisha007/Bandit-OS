import numpy as np

class ThompsonSampling:
    def __init__(self, variants):
        # Each variant starts with Beta(1,1) — no evidence yet
        self.variants = variants
        self.alpha = {v: 1 for v in variants}  # wins + 1
        self.beta = {v: 1 for v in variants}   # losses + 1

    def select_variant(self):
        # Sample from each variant's Beta distribution
        # Variant with highest sample gets the traffic
        samples = {
            v: np.random.beta(self.alpha[v], self.beta[v])
            for v in self.variants
        }
        return max(samples, key=samples.get)

    def update(self, variant, reward):
        # reward = 1 if user clicked, 0 if they didn't
        if reward == 1:
            self.alpha[variant] += 1
        else:
            self.beta[variant] += 1

    def get_traffic_split(self):
        # Returns current traffic % for each variant
        total = sum(self.alpha[v] + self.beta[v] - 2 for v in self.variants)
        if total == 0:
            return {v: 100 / len(self.variants) for v in self.variants}
        return {
            v: round((self.alpha[v] + self.beta[v] - 2) / total * 100, 1)
            for v in self.variants
        }

    def get_winner(self):
        # Declare winner if confidence > 95%
        samples = [
            np.random.beta(self.alpha[v], self.beta[v])
            for v in self.variants
        ]
        total_samples = 1000
        wins = {v: 0 for v in self.variants}
        for _ in range(total_samples):
            sampled = {
                v: np.random.beta(self.alpha[v], self.beta[v])
                for v in self.variants
            }
            winner = max(sampled, key=sampled.get)
            wins[winner] += 1
        probabilities = {v: wins[v] / total_samples for v in self.variants}
        for v in self.variants:
            if probabilities[v] >= 0.95:
                return v, probabilities[v]
        return None, None