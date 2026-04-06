class UserFeedback:
    def __init__(self, lat, lon, values, rating, correction=None):
        self.lat = lat
        self.lon = lon
        self.values = values
        self.rating = rating
        self.correction = correction

def update_memory(memory, feedback):
    if feedback.rating >= 4:
        memory.store(
            feedback.lat,
            feedback.lon,
            feedback.values,
            confidence=0.9
        )
    else:
        memory.store(
            feedback.lat,
            feedback.lon,
            feedback.correction or feedback.values,
            confidence=0.4
        )
