# This is the main file that runs the chess game loop, integrating the Sunfish chess engine,
# the OctoPrint API for controlling the 3D printer, and the MoveDetector for vision-based move detection.

from sunfish import Position, initial, Searcher, print_pos, MATE_LOWER, render
from sunfish import parse, Move
import re
import time

from octoprint import Octoprint
import secrets
from moveDetection import MoveDetector

import cv2

# This function translates a move string like 'e2e4' into the corresponding physical coordinates
# on the chessboard. It assumes the printer's coordinate system is aligned such that:
# - 'a1' corresponds to (x=26, y=38) in printer coordinates (these are the 'a1' values in Octoprint's __init__)
# - Each file (a-h) corresponds to a step of 'field_size' in the x direction, and each rank (1-8) corresponds to a step of 'field_size' in the y direction.
def parse_move(move):
    xf = ord(move[0]) - ord('a') + 1
    yf = int(move[1])
    xt = ord(move[2]) - ord('a') + 1
    yt = int(move[3])
    return xf, yf, xt, yt


def main():

    # Connect to printer
    o = Octoprint(api_key=secrets.api_key)
    o.connect()

    # M203 sets the Maximum Feedrate (Units are mm/s, NOT mm/min!)
    # 200 mm/s is roughly F12000
    o.send_command("M203 X500 Y500 Z30") 

    # M201 sets Maximum Acceleration
    o.send_command("M201 X2500 Y2500 Z250")

    print("Welcome to 3D Printer Chess")

    s = input("Home the printer? (y/n): ")

    if s.lower() == 'y':
        o.home()
        o.park()
        time.sleep(35)
        # o.wait_while_busy()

    print("Printer parked. Starting vision...")

    # Camera stream from OctoPrint webcam
    md = MoveDetector('http://localhost:8080/?action=stream')

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

        # Before waiting for move
        print("It is White's turn.")
        # If the printed list shows 'h7h6', your engine is definitely flipped.
        print(f"Legal moves: {[render(119-m[0])+render(119-m[1]) for m in hist[-1].gen_moves()]}")

        print("Waiting for your move...")

        # We render moves directly from the engine without flipping coordinates
        legal_moves_list = [render(m[0]) + render(m[1]) for m in hist[-1].gen_moves()]
        print(f"DEBUG: Internal Legal Moves: {legal_moves_list}")

        move = None

        while True: # Changed from 'while move not in...' to allow for debugging
            detected_move, final_frame = md.getMove()
            print(f"DEBUG: Vision detected move string: {detected_move}")

            match = re.match(r'([a-h][1-8])([a-h][1-8])', detected_move)

            if match:
                # 1. Get the raw squares from vision (e.g., 'd2', 'd4')
                v_start = match.group(1)
                v_end = match.group(2)

                # 2. Use Sunfish's own 'parse' function to get the 120-cell indices
                # We must account for the fact that the engine 'rotates' the board 
                # based on whose turn it is (even/odd moves in history).
                idx_start = parse(v_start)
                idx_end = parse(v_end)
                
                # If it's an odd ply (Black's turn), Sunfish expects flipped indices
                if len(hist) % 2 == 1:
                    idx_start = 119 - idx_start
                    idx_end = 119 - idx_end

                # 3. Create a Move namedtuple (Sunfish moves are: Move(i, j, prom))
                m_obj = Move(idx_start, idx_end, "")
                
                print(f"DEBUG: Sunfish indices for {v_start}{v_end}: {m_obj}")

                # 4. CHECK LEGALITY
                if m_obj in hist[-1].gen_moves():
                    move = m_obj # Now 'move' is the correct object for hist[-1].move(move)
                    print("DEBUG: Move Accepted!")
                    break 
                else:
                    print(f"DEBUG: Move {v_start}{v_end} is ILLEGAL.")
                    # Let's print the actual indices the engine is looking for:
                    print(f"DEBUG: Engine wants one of: {list(hist[-1].gen_moves())}")
            else:
                print(f"DEBUG: Could not parse {detected_move} as a chess move.")

        hist.append(hist[-1].move(move))

        # ADD THIS: Reset the vision baseline so it knows where pieces are NOW
        md.lastPosition = {
            key: md.getBox(final_frame, point)
            for (key, point) in md.fieldPositions.items()
        }

        # Robot thinking starts here
        start = time.time()
        best_move = None
        
        for depth, gamma, score, move_obj in searcher.search(hist):
            if move_obj:
                best_move = move_obj
            if time.time() - start > 1:
                break

        if best_move:
            # This is the move from the engine's CURRENT perspective
            # (If it's Black's turn, Sunfish sees the board flipped)
            smove_engine = render(best_move.i) + render(best_move.j)
            
            # This is the move in PHYSICAL coordinates (White's perspective)
            # We use this for the printer/robot path
            smove_physical = render(119 - best_move.i) + render(119 - best_move.j)
            
            print(f"Robot thinks move is: {smove_engine}")
            print(f"Robot physical move: {smove_physical}")

            # 1. Look at the destination square based on the engine's move.j
            # This index is guaranteed to match the engine's current board array
            target_piece = hist[-1].board[best_move.j]
            
            print(f"DEBUG: Engine index {best_move.j} shows piece: '{target_piece}'")

            # 2. In Sunfish, if it is the moving player's turn, 
            # OPPONENT pieces are always lowercase.
            if target_piece.islower() and target_piece not in ('.', '#'): 
                print(f"!!! Capture detected on {smove_physical[2:]} !!!")
                
                # Get physical coordinates for the 'to' square
                _, _, xt, yt = parse_move("a1" + smove_physical[2:]) 
                
                print(f"Removing piece at {xt}, {yt}")
                o.remove(xt, yt)
                time.sleep(6) 

            # 3. Proceed with Move
            hist.append(hist[-1].move(best_move))
            xf, yf, xt, yt = parse_move(smove_physical)
            
            print(f"--- ROBOT EXECUTION ---")
            o.from_to(xf, yf, xt, yt)

            # Wait for the physical move to complete
            print("Waiting for printer to finish...")
            time.sleep(10) # Give the printer plenty of time to finish and the head to park

            # CAPTURE FRESH BASELINE (The single source of truth)
            cap = cv2.VideoCapture(md.path)
            success, fresh_img = cap.read()
            cap.release()
            
            if success:
                # Use absolute resize to match MoveDetector logic
                fresh_frame = cv2.resize(fresh_img, (md.width, md.height))
                md.lastPosition = {
                    key: md.getBox(fresh_frame, point)
                    for (key, point) in md.fieldPositions.items()
                }
                print("Baseline reset. Human turn starting now...")
            else:
                print("WARNING: Could not grab fresh frame after robot move!")


if __name__ == "__main__":
    main()
