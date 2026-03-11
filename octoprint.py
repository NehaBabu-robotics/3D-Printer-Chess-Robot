import requests
import time


class Octoprint:

    def __init__(self,
                 host='http://192.168.178.39',
                 api_key='',
                 a1=(26,38),
                 field_size=27,
                 min_z=53,
                 z_up=80,
                 z_park=150):

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

    def home(self):

        command = {'command': 'home', 'axes': 'x,y,z'}
        requests.post(self.printhead, headers=self.headers, json=command)

        time.sleep(10)


    def park(self):

        command = {'command': 'jog','z': self.z_park,'absolute': True}
        requests.post(self.printhead, headers=self.headers, json=command)

        command = {'command': 'jog','x': 220,'y': 220,'absolute': True}
        requests.post(self.printhead, headers=self.headers, json=command)


    def move_square(self, x, y):

        px = self.a1[0] + (x-1)*self.field_size
        py = self.a1[1] + (y-1)*self.field_size

        command = {'command':'jog','x':px,'y':py,'absolute':True}
        requests.post(self.printhead, headers=self.headers, json=command)


    def move_down(self):

        command = {'command':'jog','z':self.min_z,'absolute':True}
        requests.post(self.printhead, headers=self.headers, json=command)


    def move_up(self):

        command = {'command':'jog','z':self.z_up,'absolute':True}
        requests.post(self.printhead, headers=self.headers, json=command)


    def magnet_on(self):

        command = {"commands":["M106"]}
        requests.post(self.command, headers=self.headers, json=command)


    def magnet_off(self):

        command = {"commands":["M107"]}
        requests.post(self.command, headers=self.headers, json=command)


    def pick_piece(self,x,y):

        self.move_square(x,y)
        time.sleep(1)

        self.move_down()
        time.sleep(1)

        self.magnet_on()
        time.sleep(1)

        self.move_up()


    def place_piece(self,x,y):

        self.move_square(x,y)
        time.sleep(1)

        self.move_down()
        time.sleep(1)

        self.magnet_off()
        time.sleep(1)

        self.move_up()


    def from_to(self,x0,y0,x1,y1,pawn=False):

        self.pick_piece(x0,y0)
        self.place_piece(x1,y1)
        self.park()


    def remove(self,x,y,pawn=False):

        self.pick_piece(x,y)

        command = {'command':'jog','x':0,'y':0,'absolute':True}
        requests.post(self.printhead, headers=self.headers, json=command)

        time.sleep(1)

        self.move_down()
        self.magnet_off()
        self.move_up()
