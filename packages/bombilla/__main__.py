from .bombilla import Bombilla
import ipdb
import os


def main():
    bombilla = Bombilla.from_json(
        os.path.join(os.path.dirname(__file__), "./test_bombillas/default.json")
    )
    ipdb.set_trace()


if __name__ == "__main__":
    main()
