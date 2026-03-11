from sunfish import Position, initial, Searcher, print_pos, MATE_LOWER, render
import re
import time

from octoprint import Octoprint
import secrets
from moveDetection import MoveDetector


def parse_move(move):
    xf = ord(move[0]) - ord('a') + 1
    yf = int(move[1])
    xt = ord(move[2]) - ord('a') + 1
    yt = int(move[3])
    return xf, yf, xt, yt


def main():

    # Camera stream from OctoPrint webcam
    md = MoveDetector('http://192.168.178.39/webcam/?action=stream')

    # Connect to printer
    o = Octoprint(api_key=secrets.api_key)

    print("Welcome to 3D Printer Chess")

    s = input("Home the printer? (y/n): ")

    if s.lower() == 'y':
        o.home()

    o.park()

    # Sunfish board history
    hist = [Position(initial, 0, (True, True), (True, True), 0, 0)]

    searcher = Searcher()

    print("Game started")

    while True:

        print_pos(hist[-1])

        # Check if player is checkmated
        if hist[-1].score <= -MATE_LOWER:
            print("You lost")
            break

        print("Waiting for your move...")

        move = None

        while move not in hist[-1].gen_moves():

            detected_move = md.getMove()

            match = re.match(r'([a-h][1-8])([a-h][1-8])', detected_move)

            if match:
                move = (match.group(1), match.group(2))
                move = (move[0], move[1])

                move = ((ord(move[0][0]) - ord('a'), int(move[0][1]) - 1),
                        (ord(move[1][0]) - ord('a'), int(move[1][1]) - 1))
            else:
                print("Invalid move detected")

        hist.append(hist[-1].move(move))

        print_pos(hist[-1].rotate())

        # Check if robot is checkmated
        if hist[-1].score <= -MATE_LOWER:
            print("You won")
            break

        start = time.time()

        for depth, move, score in searcher.search(hist[-1], hist):

            if time.time() - start > 1:
                break

        smove = render(119 - move[0]) + render(119 - move[1])

        print("Robot move:", smove)

        hist.append(hist[-1].move(move))

        xf, yf, xt, yt = parse_move(smove)

        # Send move to printer
        o.from_to(xf, yf, xt, yt)


if __name__ == "__main__":
    main()
