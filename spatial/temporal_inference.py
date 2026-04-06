def infer_values(lat, lon, year, memory):
    relevant = [
        r for r in memory
        if abs(r.lat - lat) < 0.1
        and abs(r.lon - lon) < 0.1
        and abs(r.year - year) < 20
    ]

    if not relevant:
        return ["Tradition"], 0.3

    values = []
    confidence = 0
    for r in relevant:
        values.extend(r.values)
        confidence += r.confidence

    return list(set(values)), confidence / len(relevant)
