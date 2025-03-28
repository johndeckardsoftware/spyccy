#
# dummy for pygame module not found
#
class mixer:
    def __init__(self):
        pass
    def init():
        print("pygame not installed. run 'pip install pygame' to install it")
        pass
    class Sound:
        def __init__(self, wave):
            self.wave = wave

        def play(self, loop):
            pass
