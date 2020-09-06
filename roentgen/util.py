class MinMax:
    def __init__(self):
        self.min_ = None
        self.max_ = None

    def add(self, value):
        self.min_ = value if not self.min_ or value < self.min_ else self.min_
        self.max_ = value if not self.max_ or value > self.max_ else self.max_