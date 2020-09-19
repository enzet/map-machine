from colour import Color


class MinMax:
    """
    Minimum and maximum.
    """
    def __init__(self, min_=None, max_=None):
        self.min_ = min_
        self.max_ = max_

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

    def center(self):
        return (self.min_ + self.max_) / 2

def is_bright(color: Color) -> bool:
    """
    Is color bright enough to have black outline instead of white.
    """
    return (
        0.2126 * color.red * 256 +
        0.7152 * color.green * 256 +
        0.0722 * color.blue * 256 > 200)
