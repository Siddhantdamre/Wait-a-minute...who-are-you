"""
Simulated Clinical Deterioration Monitoring Environment

A hospital ward where hidden patient deterioration must be
diagnosed under a tight query budget with one nurse station
reporting stale vitals.

KEY DIFFERENCE FROM C6/CYBER:
- The number of deteriorating patients is NOT fixed at 4.
- It varies randomly from 2 to 6 per episode.
- This breaks DEIC's group_size=4 assumption.
"""

import random


PATIENT_IDS = [
    "bed-1A", "bed-1B", "bed-2A", "bed-2B",
    "bed-3A", "bed-3B", "bed-4A", "bed-4B"
]

STATION_NAMES = ["station-north", "station-south", "station-east"]


class ClinicalEpisodeConfig:
    """Fully specifies one deterioration monitoring episode."""

    def __init__(self, seed, n_patients=8):
        rng = random.Random(seed)

        self.patients = PATIENT_IDS[:n_patients]
        self.baseline_vitals = {p: rng.randint(60, 120) for p in self.patients}

        # Hidden: which patients are deteriorating (variable group size 2-6)
        n_deteriorating = rng.randint(2, 6)
        shuffled = list(self.patients)
        rng.shuffle(shuffled)
        self.deteriorating = shuffled[:n_deteriorating]
        self.stable = shuffled[n_deteriorating:]

        # Hidden: severity of deterioration (vitals multiplier)
        self.severity = rng.choice([1.3, 1.8, 2.5])

        # One station has delayed vitals (reports baseline)
        self.faulty_station = rng.choice(STATION_NAMES)

        # Query budget
        self.max_queries = 8

        self.seed = seed


class ClinicalEnvironment:
    """
    At episode start:
    - A variable number (2-6) of patients experience vital sign spikes
    - 2 stations observe true post-deterioration vitals
    - 1 station has stale/delayed readings (reports baseline)
    - The charge nurse has max_queries chart review queries
    """

    def __init__(self, config: ClinicalEpisodeConfig):
        self.config = config
        self.rng = random.Random(config.seed + 7000)

        # True post-deterioration vitals
        self.true_vitals = {}
        for p in config.patients:
            if p in config.deteriorating:
                self.true_vitals[p] = int(
                    config.baseline_vitals[p] * config.severity
                )
            else:
                self.true_vitals[p] = config.baseline_vitals[p]

        # Station views
        self.station_views = {}
        for st in STATION_NAMES:
            if st == config.faulty_station:
                self.station_views[st] = dict(config.baseline_vitals)
            else:
                self.station_views[st] = dict(self.true_vitals)

        self.turn = 0
        self.terminated = False

    def get_patients(self):
        return list(self.config.patients)

    def get_stations(self):
        return list(STATION_NAMES)

    def get_baseline_vitals(self):
        return dict(self.config.baseline_vitals)

    def get_true_state(self):
        return dict(self.true_vitals)

    def query(self, station, patient):
        if self.terminated:
            return {"error": "Episode already concluded."}

        self.turn += 1
        if self.turn > self.config.max_queries:
            self.terminated = True
            return {"status": "timeout"}

        if station not in STATION_NAMES:
            return {"error": f"Unknown station: {station}"}
        if patient not in self.config.patients:
            return {"error": f"Unknown patient: {patient}"}

        return {
            "station": station,
            "patient": patient,
            "reported_vitals": self.station_views[station][patient],
            "status": "ok"
        }

    def submit_assessment(self, proposed_vitals):
        self.terminated = True
        diff = {}
        for p in self.config.patients:
            if proposed_vitals.get(p) != self.true_vitals[p]:
                diff[p] = {
                    "expected": self.true_vitals[p],
                    "received": proposed_vitals.get(p)
                }
        return {
            "correct": len(diff) == 0,
            "errors": diff,
            "queries_used": self.turn
        }


def generate_clinical_episodes(n, seed_offset=0):
    return [ClinicalEpisodeConfig(seed=seed_offset + i) for i in range(n)]
