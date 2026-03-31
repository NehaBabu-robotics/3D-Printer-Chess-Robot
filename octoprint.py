import requests
import time


class Octoprint:

    def __init__(self,
                 host='http://localhost:5000/',
                 api_key='',
                 a1=(26,38),
                 field_size=27,
                 min_z=8,
                 z_up=40,
                 z_park=40):

        self.base_url = host
        self.api_key = api_key

        self.headers = {
            'Content-Type': 'application/json',
            'X-Api-Key': self.api_key
        }

        self.printhead = self.base_url + '/api/printer/printhead'
        self.command = self.base_url + '/api/printer/command'

        self.a1 = a1
        self.field_size = field_size
        self.min_z = min_z
        self.z_up = z_up
        self.z_park = z_park

    def connect(self):
        """Tells OctoPrint to connect to the printer via serial."""
        url = self.base_url + '/api/connection'
        payload = {
            "command": "connect",
            "port": "/dev/ttyUSB0", # This is common for Ender 3, or leave out for 'AUTO'
            "baudrate": 115200,
            "save": True,
            "autoconnect": True
        }
        response = requests.post(url, headers=self.headers, json=payload)
        
        # Give it a few seconds to initialize the handshake
        print("Connecting to printer...")
        time.sleep(5)
        return response
    
    def wait_while_busy(self):
        print("--- ENTERING WAIT_WHILE_BUSY ---")
        # Ensure a gap so OctoPrint sees the new commands
        time.sleep(2.0) 
        
        idle_confirmations = 0
        while idle_confirmations < 4: # Increased to 4 for extra safety
            url = self.base_url + '/api/printer'
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                state = response.json()['state']['text']
                # DEBUG PRINT: This will tell us exactly what's happening
                print(f"[DEBUG] Printer State: '{state}' | Idle Count: {idle_confirmations}")
                
                if state == "Operational":
                    idle_confirmations += 1
                elif "Error" in state:
                    print("!!! PRINTER ERROR DETECTED !!!")
                    break
                else:
                    # If it says 'Busy', 'Printing', or 'Finishing'
                    idle_confirmations = 0
            else:
                print(f"[DEBUG] API Error: {response.status_code}")
            
            time.sleep(0.5)
        print("--- EXITING WAIT_WHILE_BUSY: PRINTER READY ---")

    def home(self):
        print("Homing to physical switches...")
        # We send G28 followed by M400 (Wait)
        command_h = {"commands": ["G28", "M400"]}
        requests.post(self.command, headers=self.headers, json=command_h)
        # No more fixed time.sleep(10) needed here; wait_while_busy handles it!

    def park(self):
        print(f"Parking at X220 Y220 Z{self.z_park}...")

        self.send_command([
            f"G1 Z{self.z_park} F5000",
            "G1 X0 Y220 F12000",
            "M400"
        ])



    def move_square(self, x, y):

        px = self.a1[0] + (x-1)*self.field_size
        px += 3
        py = self.a1[1] + (y-1)*self.field_size
        py -= 10

        # command = {'command':'jog','x':px,'y':py,'absolute':True}
        # requests.post(self.printhead, headers=self.headers, json=command)
        self.send_command(f"G1 X{px} Y{py} F12000")


    def move_down(self):
        # F1200 is 20mm/s. Adjust higher if your printer allows.
        # command = {"commands": [f"G1 Z{self.min_z} F3000"]}
        # requests.post(self.command, headers=self.headers, json=command)

        self.send_command(f"G1 Z{self.min_z} F5000")

    def move_up(self):
        # command = {"commands": [f"G1 Z{self.z_up} F3000"]}
        # requests.post(self.command, headers=self.headers, json=command)

        self.send_command(f"G1 Z{self.z_up} F5000")


    # def magnet_on(self):
    #     print("Magnet: ON")
    #     command = {"commands":["M106"]}
    #     requests.post(self.command, headers=self.headers, json=command)


    # def magnet_off(self):
    #     print("Magnet: OFF")
    #     command = {"commands":["M107"]}
    #     requests.post(self.command, headers=self.headers, json=command)

    def magnet_on(self):
        print("Magnet: ON")
        # S255 is full power for the fan port
        self.send_command("M106 S255")

    def magnet_off(self):
        print("Magnet: OFF")
        # S0 turns the fan port voltage to 0
        self.send_command("M106 S0")


    def pick_piece(self,x,y):

        self.move_square(x,y)
        time.sleep(1)

        self.move_down()
        time.sleep(2)

        self.magnet_on()
        time.sleep(1)

        self.move_up()


    def drop_piece(self,x,y):

        self.move_square(x,y)
        time.sleep(1)

        self.move_down()
        time.sleep(1)

        self.magnet_off()
        time.sleep(1)

        self.move_up()

    # def pick_piece(self, x, y):
    #     # 1. Move to position at safe height
    #     # (Assuming x, y are translated to mm by your coordinate logic)
    #     self.send_command(f"G1 X{x} Y{y} F3000")
    #     self.send_command("M400") # Wait for arrival
        
    #     # 2. Lower to the piece
    #     self.send_command(f"G1 Z{self.min_z} F1500") # Lower Z
    #     self.send_command("M400")
        
    #     # 3. ENGAGE MAGNET
    #     self.magnet_on()
    #     time.sleep(0.5) # Short pause to let magnetic field stabilize
        
    #     # 4. Lift back up
    #     self.send_command(f"G1 Z{self.z_up} F1500")
    #     self.send_command("M400")

    # def drop_piece(self, x, y):
    #     # 1. Move to target at safe height
    #     self.send_command(f"G1 X{x} Y{y} F3000")
    #     self.send_command("M400")
        
    #     # 2. Lower to the board
    #     self.send_command(f"G1 Z{self.min_z} F1500")
    #     self.send_command("M400")
        
    #     # 3. DISENGAGE MAGNET
    #     self.magnet_off()
    #     time.sleep(0.5) # Let the piece settle
        
    #     # 4. Lift back up
    #     self.send_command(f"G1 Z{self.z_up} F1500")
    #     self.send_command("M400")


    def from_to(self,x0,y0,x1,y1,pawn=False):

        self.pick_piece(x0,y0)
        self.drop_piece(x1,y1)
        self.park()


    def remove(self,x,y,pawn=False):

        self.pick_piece(x,y)

        command = {'command':'jog','x':0,'y':0,'absolute':True}
        requests.post(self.printhead, headers=self.headers, json=command)

        time.sleep(1)

        self.magnet_off()


    def send_command(self, gcode):
        """Sends a raw G-code command or list of commands to the printer."""
        # Wrap in a list if it's just a single string
        commands = [gcode] if isinstance(gcode, str) else gcode
        payload = {"commands": commands}
        response = requests.post(self.command, headers=self.headers, json=payload)
        return response
