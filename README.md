# 3D-Printer-Chess-Robot

This project converts a Cartesian 3D printer into a chess-playing robot.
The system detects human moves using computer vision and responds by moving chess pieces with an electromagnet mounted on the printer head.

The project integrates:

* Computer vision (OpenCV) for move detection
* Sunfish chess engine for AI
* OctoPrint API for controlling the 3D printer
* Electromagnet end-effector for pick-and-place manipulation

## System Architecture

Camera → Move Detection → Chess Engine → OctoPrint → 3D Printer Motion

The camera monitors the chessboard and detects when a human player makes a move.
The move is processed by the Sunfish chess engine, which computes a response.
The robot then moves the corresponding piece using the printer's X-Y-Z axes.

## Hardware Requirements

* Creality Ender-3 (or similar Cartesian 3D printer)
* OctoPrint server
* USB webcam mounted above the chessboard
* Electromagnet mounted on the print head
* Ferromagnetic chess pieces

## Software Requirements

Python libraries:

* numpy
* opencv-python
* requests

Install with:

pip install -r requirements.txt

## Configuration

Update the following values before running:

* OctoPrint IP address
* OctoPrint API key
* Camera stream address
* Chessboard square size
* Coordinates of square A1

## Running the Program

Start OctoPrint and ensure the webcam stream is active.

Run:

python main.py

The robot will wait for a player move and respond automatically.

## Disclaimer

This project modifies the behavior of a 3D printer for robotic manipulation.
Use at your own risk and ensure the printer is monitored during operation.
