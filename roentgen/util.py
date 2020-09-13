class MinMax:
    """
    Minimum and maximum.
    """
    def __init__(self):
        self.min_ = None
        self.max_ = None

    def update(self, value):
        """
        Update minimum and maximum with new value.
        """
        self.min_ = value if not self.min_ or value < self.min_ else self.min_
        self.max_ = value if not self.max_ or value > self.max_ else self.max_

    def delta(self):
        """
        Difference between maximum and minimum.
        """
        return self.max_ - self.min_
