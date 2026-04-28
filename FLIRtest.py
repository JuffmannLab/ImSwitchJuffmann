import atexit

class Greeter:
    _registered = False  # ensure we only register once

    def __init__(self, name):
        self.name = name
        if not Greeter._registered:
            atexit.register(Greeter._on_exit)
            Greeter._registered = True

    @staticmethod
    def _on_exit():
        print("THE END")


def main():
    g1 = Greeter("Alice")
    g2 = Greeter("Bob")
    print("Doing work...")

if __name__ == "__main__":
    main()