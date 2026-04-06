"""
Simulated Cyber Incident Diagnosis Environment

A distributed service mesh where hidden cascading failures
must be diagnosed under a tight query budget with one
unreliable monitoring source.

This environment is structurally isomorphic to C6 but uses
a completely different domain vocabulary. DEIC should transfer
with zero code changes to core.py.
"""

import random


SERVICE_NAMES = [
    "auth-svc", "payment-svc", "inventory-svc", "shipping-svc",
    "notification-svc", "search-svc", "analytics-svc", "gateway-svc"
]

MONITOR_NAMES = ["prometheus-east", "prometheus-west", "datadog-central"]


class CyberEpisodeConfig:
    """Fully specifies one incident diagnosis episode."""

    def __init__(self, seed, n_services=8):
        rng = random.Random(seed)

        self.services = SERVICE_NAMES[:n_services]
        self.baseline_latency = {svc: rng.randint(10, 200) for svc in self.services}

        # Hidden: which upstream dependency failed, affecting a random subset
        shuffled = list(self.services)
        rng.shuffle(shuffled)
        self.affected_group = shuffled[:4]
        self.unaffected_group = shuffled[4:]

        # Hidden: severity of the cascading failure (latency multiplier)
        self.severity_multiplier = rng.choice([1.5, 2.0, 3.0, 5.0])

        # One monitor has a stale cache and reports pre-incident baselines
        self.faulty_monitor = rng.choice(MONITOR_NAMES)

        # Query budget: 8 diagnostic traces before failover timer expires
        self.max_queries = 8

        self.seed = seed


class CyberIncidentEnvironment:
    """
    Architecture-agnostic cyber diagnosis environment.

    At episode start:
    - 4 random services experience a latency spike (multiplier)
    - 3 monitors observe the true post-incident latencies
    - 1 monitor has stale cache (reports baseline latencies)
    - The operator has exactly max_queries diagnostic probes
    """

    def __init__(self, config: CyberEpisodeConfig):
        self.config = config
        self.rng = random.Random(config.seed + 5000)

        # True post-incident state
        self.true_latency = {}
        for svc in config.services:
            if svc in config.affected_group:
                self.true_latency[svc] = int(
                    config.baseline_latency[svc] * config.severity_multiplier
                )
            else:
                self.true_latency[svc] = config.baseline_latency[svc]

        # Monitor views
        self.monitor_views = {}
        for mon in MONITOR_NAMES:
            if mon == config.faulty_monitor:
                # Stale cache: reports baseline
                self.monitor_views[mon] = dict(config.baseline_latency)
            else:
                # Live: reports true post-incident
                self.monitor_views[mon] = dict(self.true_latency)

        self.turn = 0
        self.terminated = False

    def get_services(self):
        return list(self.config.services)

    def get_monitors(self):
        return list(MONITOR_NAMES)

    def get_baseline_latency(self):
        return dict(self.config.baseline_latency)

    def get_true_state(self):
        return dict(self.true_latency)

    def query(self, monitor, service):
        """Issue a diagnostic probe: ask a monitor for a service's latency."""
        if self.terminated:
            return {"error": "Incident already resolved or timed out."}

        self.turn += 1
        if self.turn > self.config.max_queries:
            self.terminated = True
            return {"status": "timeout"}

        if monitor not in MONITOR_NAMES:
            return {"error": f"Unknown monitor: {monitor}"}
        if service not in self.config.services:
            return {"error": f"Unknown service: {service}"}

        return {
            "monitor": monitor,
            "service": service,
            "reported_latency": self.monitor_views[monitor][service],
            "status": "ok"
        }

    def submit_diagnosis(self, proposed_latency):
        """Submit the operator's diagnosis of current service latencies."""
        self.terminated = True
        diff = {}
        for svc in self.config.services:
            if proposed_latency.get(svc) != self.true_latency[svc]:
                diff[svc] = {
                    "expected": self.true_latency[svc],
                    "received": proposed_latency.get(svc)
                }
        return {
            "correct": len(diff) == 0,
            "errors": diff,
            "queries_used": self.turn
        }


def generate_cyber_episodes(n, seed_offset=0):
    return [CyberEpisodeConfig(seed=seed_offset + i) for i in range(n)]
