# File: model.py
# Location: snotes_project/snotes_reader/model.py

class SdocPoint:
    """Represents a single point in a stroke with coordinates, pressure, and timestamp."""
    def __init__(self, x: float = 0.0, y: float = 0.0, pressure: float = 0.0, timestamp: float = 0.0):
        self.x = x
        self.y = y
        self.pressure = pressure
        self.timestamp = timestamp

class SdocStroke:
    """Represents a single stroke (continuous line) in the document."""
    def __init__(self):
        self.points = []

class SdocPage:
    """Represents a single page in the document containing strokes."""
    def __init__(self):
        self.strokes = []

class SdocDocument:
    """Represents a complete Samsung Notes document."""
    def __init__(self):
        self.pages = []