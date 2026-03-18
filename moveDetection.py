from matplotlib.pyplot import gray
import numpy as np
import cv2
import math
import json
import os


class MoveDetector:
    """
    Detects a chess move from a camera stream.
    The detector finds the chessboard squares and monitors them for changes.
    """

    def __init__(self, path):
        self.path = path
        cap = cv2.VideoCapture(self.path)

        # Resize so width becomes ~320px
        # self.resize = 320 / cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.resize = 1.0 # Keep original resolution for better noise detection
        self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) * self.resize)
        self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) * self.resize)

        # Board column labels
        self.abc = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

        # self.fieldPositions = self.detectSquares()
        self.fieldPositions = self.load_manual_grid()
        self.avgNoise = self.estimateNoise()


    def load_manual_grid(self):
        if os.path.exists('grid_config.json'):
            with open('grid_config.json', 'r') as f:
                print("LOCKED: Using manual grid calibration.")
                return json.load(f)
        else:
            print("WARNING: No manual grid found. Defaulting to auto-detect.")
            return self.detectSquares()
        

    def detectSquares(self):
        """
        Detect chessboard square centers using edge and line detection.
        """

        cap = cv2.VideoCapture(self.path)
        _, frame = cap.read()

        editedFrame = cv2.resize(frame, (0, 0), fx=self.resize, fy=self.resize)

        gray = cv2.cvtColor(editedFrame, cv2.COLOR_BGR2GRAY)
        # 11 is the block size, 2 is the constant subtracted from the mean
        # thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        #                         cv2.THRESH_BINARY_INV, 11, 2)

        # We ignore the leftmost 20% and rightmost 10% of the image 
        # to avoid the printer screen and table clutter.
        margin_left = int(self.width * 0.3)
        margin_right = int(self.width * 0.7)

        # Ignore the bottom 15% of the frame (where the structure is)
        bottom_limit = int(self.height * 0.74)
        upper_limit = int(self.height * 0.03)

        gray_cropped = gray[upper_limit:bottom_limit, margin_left:margin_right]
        # tresh_cropped = thresh[:, margin_left:margin_right]

        # --- CALIBRATION BLOCK ---
        # Show the cropped image to the user
        cv2.imshow("CALIBRATION: Is the board centered?", gray_cropped)
        print("Check the 'CALIBRATION' window. Is the board fully visible without the printer frame?")
        print("Press any key to continue or Ctrl+C to stop and adjust margins.")
        cv2.waitKey(0) 
        cv2.destroyWindow("CALIBRATION: Is the board centered?")
        # --- END CALIBRATION BLOCK ---

        edges = cv2.Canny(gray_cropped, 150, 200)
        # edges = cv2.Canny(gray_cropped, 150, 200)

        # Detect board grid lines
        v_lines_part1 = cv2.HoughLines(edges, 1, np.pi / 180, 30, None, 0, 0, 0, 0.05*np.pi)
        v_lines_part2 = cv2.HoughLines(edges, 1, np.pi / 180, 30, None, 0, 0, 0.95*np.pi, np.pi)
        h_lines_raw = cv2.HoughLines(edges, 1, np.pi / 180, 30, None, 0, 0, 0.45*np.pi, 0.55*np.pi)

        # Helper to safely clean and combine line arrays
        def clean_lines(lines_list):
            valid_lines = [l for l in lines_list if l is not None]
            if not valid_lines:
                return None
            return np.concatenate(valid_lines, axis=0)

        combined_vert = clean_lines([v_lines_part1, v_lines_part2])
        
        # Convert to Cartesian coordinates
        vertLines = self.getCoords(combined_vert, offset_x=margin_left)
        horLines = self.getCoords(h_lines_raw, offset_x=margin_left)

        maxY = 0
        upperLine = None
        minY = 2*self.height
        lowerLine = None

        for line in horLines:
            avgY = line[0][1] + line[1][1]

            if avgY > maxY:
                maxY = avgY
                lowerLine = line

            if avgY < minY:
                minY = avgY
                upperLine = line

        maxX = 0
        leftLine = None
        minX = 2*self.width
        rightLine = None

        for line in vertLines:
            avgX = line[0][0] + line[1][0]

            if avgX > maxX:
                maxX = avgX
                rightLine = line

            if avgX < minX:
                minX = avgX
                leftLine = line

        # Board corners
        intersect1 = self.getIntersection(upperLine, rightLine)
        intersect2 = self.getIntersection(upperLine, leftLine)
        intersect3 = self.getIntersection(lowerLine, rightLine)
        intersect4 = self.getIntersection(lowerLine, leftLine)

        fieldPositions = dict()

        stepLeft, offsetLeft = self.calcStep((intersect2, intersect4), 8)
        stepRight, offsetRight = self.calcStep((intersect1, intersect3), 8)

        # Define the 4 corners of your board from your intersection points
        # [TopRight, TopLeft, BottomRight, BottomLeft]
        pts1 = np.float32([intersect1, intersect2, intersect3, intersect4])
        
        # Define where those points SHOULD be in a perfect square (320x320)
        pts2 = np.float32([[320, 0], [0, 0], [320, 320], [0, 320]])

        # Calculate the transformation matrix
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        inv_matrix = cv2.getPerspectiveTransform(pts2, pts1)

        fieldPositions = {}
        for i in range(8):
            for j in range(8):
                # Calculate centers in the "perfect square"
                virt_x = (j * 40) + 22
                virt_y = (i * 40) + 22
                
                # Transform back to the camera's tilted perspective
                p = np.array([[[virt_x, virt_y]]], dtype='float32')
                dst = cv2.perspectiveTransform(p, inv_matrix)
                
                # Change this:
                # fieldPositions[self.abc[j] + str(i+1)] = dst[0][0].astype(int)

                # To this:
                fieldPositions[self.abc[j] + str(8-i)] = dst[0][0].astype(int)

        cap.release()

        for label, (px, py) in fieldPositions.items():
            # Draw a small circle and the coordinate label (e.g., "e2")
            cv2.circle(editedFrame, (px, py), 5, (0, 255, 0), -1)
            cv2.putText(editedFrame, label, (px, py), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 0), 1)

        cv2.imshow("Board Detection", editedFrame)
        
        print("Inspection Mode: Check the green dots. Press 'q' to continue.")
        
        while True:
            key = cv2.waitKey(0) & 0xFF
            if key == ord('q'):
                break
        
        cv2.destroyAllWindows()
        return fieldPositions

    def estimateNoise(self, noiseSpan=10):
        """
        Estimate background noise level of the camera.
        """

        noise = []

        cap = cv2.VideoCapture(self.path)

        _, prevFrame = cap.read()
        prevFrame = cv2.resize(prevFrame, (0,0), fx=self.resize, fy=self.resize)

        for i in range(noiseSpan):

            _, frame = cap.read()
            frame = cv2.resize(frame, (0,0), fx=self.resize, fy=self.resize)

            noise.append(cv2.absdiff(frame, prevFrame))

            prevFrame = frame

        cap.release()

        return np.mean(noise)
    
    def show_diff_map(self, lastFrame, crntFrame):
        # 1. Compute absolute difference
        diff = cv2.absdiff(lastFrame, crntFrame)
        
        # 2. Convert to grayscale
        gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        
        # 3. Apply threshold (values above 25 turn white, else black)
        _, thresh = cv2.threshold(gray_diff, 25, 255, cv2.THRESH_BINARY)
        
        # 4. Blur it slightly to reduce "camera snow"
        thresh = cv2.GaussianBlur(thresh, (5, 5), 0)
        
        cv2.imshow("Difference Map (White = Motion)", thresh)

    def getMove(self):
        """
        Wait for a move and return it as chess notation (example: e2e4).
        """

        stillCounter = 0
        hasMoved = False
        result = "none"

        cap = cv2.VideoCapture(self.path)

        # Initialize baseline - ENSURE RESIZE HERE
        _, first_frame = cap.read()
        prevFrame = cv2.resize(first_frame, (self.width, self.height)) # Use absolute dims

        lastPosition = {
            key: self.getBox(prevFrame, point)
            for (key, point) in self.fieldPositions.items()
        }

        while True:

            success, frame = cap.read()
            if not success: continue
            
            # This is your RAW data from the camera
            frame = cv2.resize(frame, (self.width, self.height)) # Use absolute dims
            
            # 1. DO THE MATH FIRST (No dots drawn yet)
            # Use raw_frame for both noise calculation and the Difference Map
            # self.show_diff_map(prevFrame, frame) 
            
            crntNoise = np.mean(cv2.absdiff(frame, prevFrame))

            # 2. CREATE A DISPLAY COPY
            # We only draw dots on this copy for the human to see
            display_frame = frame.copy()

            for box_name, coords in self.fieldPositions.items():
                cv2.circle(display_frame, tuple(coords), 3, (0, 255, 0), -1)
                # # Adding the label helps confirm the grid is still aligned
                # cv2.putText(display_frame, box_name, tuple(coords), 
                #             cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 0), 1)

            # cv2.imshow("Chess Cam (Human View)", display_frame)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break

            crntNoise = np.mean(cv2.absdiff(frame, prevFrame))
            # print(f"Noise: {crntNoise:.4f} | Target: {self.avgNoise:.4f}")

            if abs(crntNoise - self.avgNoise) < 1: # Tolerance threshold increased from 0.5 to 1
                stillCounter += 1
                # if stillCounter % 5 == 0: 
                #     print(f"Stillness detected! Counter: {stillCounter}/30")
            else:
                stillCounter = 0
                if abs(crntNoise - self.avgNoise) > 2.0: # Only count as a move if noise is significant
                    hasMoved = True

            # print("Stillness reached! Calculating differences...")

            if stillCounter > 30 and hasMoved:

                # 1. Capture current patches
                crntPosition = {key: self.getBox(frame, point) for (key, point) in self.fieldPositions.items()}

                # 2. Calculate change from baseline
                change = {}
                for key in self.fieldPositions:
                    box_baseline = lastPosition[key]
                    box_current = crntPosition[key]

                    # SAFETY CHECK: If a box is empty, skip it to prevent AxisError
                    if box_baseline.size == 0 or box_current.size == 0:
                        print(f"WARNING: Square {key} is out of camera bounds!")
                        change[key] = 0
                        continue

                    diff = cv2.absdiff(box_current, box_baseline)
                    
                    # Calculate variance of the mean
                    val = np.var(np.mean(diff, (0, 1)))
                    change[key] = val if val > 1.0 else 0

                candidates = sorted(change.keys(), key=lambda x: change[x], reverse=True)

                if len(candidates) >= 2:
                    c1, c2 = candidates[0], candidates[1]
                    
                    # Create a combined image showing the two top candidates
                    # [Square 1 Before | Square 1 After]
                    # [Square 2 Before | Square 2 After]
                    row1 = np.hstack((lastPosition[c1], crntPosition[c1]))
                    row2 = np.hstack((lastPosition[c2], crntPosition[c2]))
                    debug_view = np.vstack((row1, row2))
                    
                    # Resize so it's easier to see
                    debug_view = cv2.resize(debug_view, (400, 400), interpolation=cv2.INTER_NEAREST)
                    
                    cv2.imshow(f"Debug: {c1} vs {c2}", debug_view)
                    print(f"Showing patches for {c1} and {c2}. Press any key on the image to continue.")
                    cv2.waitKey(0) # Pause so you can inspect the images

                    # Compare brightness: Lower mean = Darker = Piece is there (Destination)
                    m0 = np.mean(crntPosition[candidates[0]])
                    m1 = np.mean(crntPosition[candidates[1]])

                    if m0 < m1: # candidate 0 is darker
                        result = candidates[1] + candidates[0]
                    else:
                        result = candidates[0] + candidates[1]
                
                print(f"Move detected: {result}")
                break # Exit the loop

            prevFrame = frame.copy()

        cap.release()

        # Update the baseline so the next move starts fresh
        # self.lastFrame = frame.copy()
        
        return result, frame

    def getBox(self, image, position, size=20):
        """
        Extract a small image patch around a board square with boundary safety.
        """
        (x, y) = position
        
        # Ensure coordinates stay within the frame size [0 to height/width]
        y1, y2 = max(0, y - size), min(image.shape[0], y + size)
        x1, x2 = max(0, x - size), min(image.shape[1], x + size)
        
        patch = image[y1:y2, x1:x2]
        return patch

    def getCoords(self, lines, offset_x=0):
        """
        Convert polar line coordinates to Cartesian points.
        """

        result = []

        if lines is not None:

            for i in range(len(lines)):

                rho = lines[i][0][0]
                theta = lines[i][0][1]

                a = math.cos(theta)
                b = math.sin(theta)

                x0 = a * rho
                y0 = b * rho

                if 0.4*np.pi < theta < 0.6*np.pi:

                    pt1 = (self.width,
                           int(y0 - (((x0-self.width)/(-b))*(a))))

                    pt2 = (0,
                           int(y0 - ((x0/(-b))*(a))))

                else:

                    pt1 = (int(x0 - ((y0-self.height)/a)*(-b)),
                           self.height)

                    pt2 = (int(x0 - (y0/a)*(-b)),
                           0)
                pt1 = (pt1[0] + offset_x, pt1[1])
                pt2 = (pt2[0] + offset_x, pt2[1])

                result.append((pt1, pt2))

        return result

    def getIntersection(self, line1, line2):
        """
        Compute intersection of two lines.
        """

        (x1,y1) = line1[0]
        (x2,y2) = line1[1]
        (x3,y3) = line2[0]
        (x4,y4) = line2[1]

        denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)

        x = ((x1*y2-y1*x2)*(x3-x4) -
             (x1-x2)*(x3*y4-y3*x4)) / denom

        y = ((x1*y2-y1*x2)*(y3-y4) -
             (y1-y2)*(x3*y4-y3*x4)) / denom

        return (int(x), int(y))

    def calcStep(self, line, nrParts):
        """
        Calculate square spacing along a line.
        """

        step = (
            (line[1][0]-line[0][0]) / nrParts,
            (line[1][1]-line[0][1]) / nrParts
        )

        offset = (step[0]/2, step[1]/2)

        return np.array(step), np.array(offset)


if __name__ == "__main__":

    md = MoveDetector('http://192.168.178.39/webcam/?action=stream')

    while True:
        print(md.getMove())

        if input() == 'q':
            break
