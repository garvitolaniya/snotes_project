# File: model.py
# Location: snotes_project/snotes_reader/model.py

from collections import namedtuple

SdocPoint = namedtuple('SdocPoint', ['x', 'y', 'pressure', 'timestamp'])

class SdocStroke:
    def __init__(self):
        self.color = None
        self.width = None
        self.points = []

class SdocPage:
    def __init__(self):
        self.strokes = []

class SdocDocument:
    def __init__(self):
        self.pages = []