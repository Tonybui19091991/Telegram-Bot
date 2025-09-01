class BondingRuleChecker:
    def __init__(self):
        self.rules = []

        # Rule cơ bản
        self.add_rule(lambda t: t["holders"] > 30, "Holders > 30")
        self.add_rule(lambda t: t["topHolderPct"] < 40, "Top10 < 40% supply")
        self.add_rule(lambda t: t["transfers5m"] > 10, "Transfers 5m > 10")
        
        # Rule săn gem
        self.add_rule(lambda t: t.get("price_usd", 0) < 0.05, "Price < $0.05")
        self.add_rule(lambda t: t.get("marketcap", 0) < 50000, "MarketCap < 50k")

    def add_rule(self, func, description):
        self.rules.append((func, description))

    def evaluate(self, token):
        results, score = [], 0
        for func, desc in self.rules:
            if func(token):
                results.append(f"✅ {desc}")
                score += 1
            else:
                results.append(f"⚠️ {desc} (failed)")
        return score, results
