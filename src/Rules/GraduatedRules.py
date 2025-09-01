class GraduatedRuleChecker:
    def __init__(self):
        self.rules = []

        # Rule cơ bản
        self.add_rule(lambda t: t["holders"] > 1000, "Holders > 1000")
        self.add_rule(lambda t: t["topHolderPct"] < 20, "Top10 < 20% supply")
        
        # Rule an toàn
        self.add_rule(lambda t: t.get("marketcap", 0) > 1_000_000, "MarketCap > $1M")
        self.add_rule(lambda t: t.get("liquidity", 0) > 100_000, "Liquidity > $100k")
        self.add_rule(lambda t: t.get("volume_24h", 0) > 50_000, "Volume 24h > $50k")

    def add_rule(self, func, description):
        self.rules.append((func, description))

    def evaluate(self, token):
        results, score = [], 0
        for func, desc in self.rules:
            if func(token):
                results.append(f"✅ {desc}")
                score += 1
            else:
                results.append(f"⚠️ {desc} (fail)")
        return score, results
