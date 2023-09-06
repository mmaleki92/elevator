#!/usr/bin/env python
"""
ELSIM: The ultimate elevator simulator
visualizer of a really stupid elevator
you can control it's motors, for up and down and open/close door
however you need to check the sensors to see if doors are open or close or elevator 
is down or up, else you will destroy the elevator
there are also call buttons inside the elevator and up and down buttons at the doors,
which can be polled
The communication is done via one tcp-port
Author: Ulrich Norbisrath
This is a frontend I developed for my Systems Modeling course
"""
import sys
import threading
import socket
import pygame
from pygame.locals import *

if not pygame.font:
    print('Warning, fonts disabled')

if not pygame.mixer:
    print('Warning, sound disabled')

BUTTON_SIZE = 21
BUTTON_FONT_SIZE = 13

terminate = False

class Elevator(pygame.sprite.Sprite):
    width = 40
    height = 50
    levels = 2
    overheat_low = 6
    overheat_max = 60
    color = 200, 0, 0
    x_offset, y_offset = 5, 5
    door_motor = 0  # 0:off, 1:opening, -1: closing
    speed = 0  # [-0.01,0.01] from going down max speed to going up max speed
    maxspeed = 0.01
    speedstep = 0.0001
    direction = 0  # -1 down, 1 up, 0 stop
    position = 0  # [0,1] from down to up
    door_position = 0  # [0,1] closed to open
    defect = False  # Is elevator defect?
    door_defect = False  # Is elevator door defect?
    
    def is_defect(self):
        return self.defect
    def is_door_defect(self):
        return self.door_defect
    def is_door_closed(self):
        return self.door_position <= 0.1
    def is_door_open(self):
        return self.door_position >= 0.9
    def current_level(self):
        return int(self.position*(self.levels-1) + 0.5)
    def save_to_open_door(self):
        delta = int(self.position*(self.levels-1)) - \
                self.position*(self.levels-1)
        return delta < 0.04 and delta > -0.04
    def position_to_coordinate(self, position):
        return (self.levels - 1) * self.height * (1 - position) + self.y_offset
    def motor_status(self):
        if self.motor_overheat < self.overheat_low:
            return "ok"
        elif self.motor_overheat < self.overheat_max:
            return "overheating"
        else:
            self.defect = True
            return "broken"
    def door_motor_status(self):
        if self.door_motor_overheat < self.overheat_low:
            return "ok"
        elif self.door_motor_overheat < self.overheat_max:
            return "overheating"
        else:
            self.door_defect = True
            return "broken"
    def _draw_door(self):
        self.image.fill((0, 0, 0))
        door_width = (1 - self.door_position) * (self.width/2 - 5)
        pygame.draw.rect(self.image, self.color,
                         (0, 0, door_width + 6, self.height))
        pygame.draw.rect(self.image, self.color,
                         (self.width-door_width-4, 0, door_width+4, self.height))

    def __init__(self, levels):
        pygame.sprite.Sprite.__init__(self)  #call Sprite intializer
        self.levels = levels
        self.door_motor_overheat = 0
        self.motor_overheat = 0
        self.image = pygame.Surface((self.width, self.height))
        self._draw_door()
        self.rect = pygame.Rect(
                (self.x_offset, self.position_to_coordinate(self.position)),
                (self.width, self.height))
        self.speed = 0
        self.buttons = create_buttons(self)
        self.button_lamps = dict()
        self.button_states = dict()
        for (name, released, mouseover, pressed, (x, y)) in self.buttons:
            self.button_lamps[name] = False
            self.button_states[name] = False

    def update(self):
        # check updates of speed
        if self.direction == 1:
            if self.speed < self.maxspeed:
                self.speed += self.speedstep
        elif self.direction == -1:
            if self.speed > - self.maxspeed:
                self.speed -= self.speedstep
        else: # self.direction == 0
            if self.speed > 0.00001:
                self.speed -= self.speedstep
            elif self.speed < -0.00001:
                self.speed += self.speedstep
            else:
                self.speed = 0
        if not self.defect:
            # self.position += self.speed/self.height
            self.position += self.speed/self.levels
            # update position of elevator
            if self.position < 0:
                self.position = 0
                self.motor_overheat += 1
            elif self.position > 1:
                self.position = 1
                self.motor_overheat += 1
            else:
                # cool down
                if self.motor_overheat > 0:
                    self.motor_overheat -= 1
        self.rect.top = self.position_to_coordinate(self.position)
        if not self.door_defect:
            # check door_motor
            if self.door_motor == -1:
                self.door_position -= 0.01
            elif self.door_motor == 1:
                self.door_position += 0.01
            # update door
            if self.door_position < 0:
                self.door_position = 0
                self.door_motor_overheat += 1
            elif self.door_position > 1:
                self.door_position = 1
                self.door_motor_overheat += 1
            else:
                # cool down
                if self.door_motor_overheat > 0:
                    self.door_motor_overheat -= 1
        self._draw_door()

    def up(self):
        """Send elevator up. It will first accelerate a bit."""
        self.direction = 1
    def down(self):
        """Send elevator down. It will first accelerate a bit."""
        self.direction = -1
    def stop(self):
        """Stop elevator. It will first break a bit."""
        self.direction = 0
    def door_open(self):
        """Set door motor to open."""
        self.door_motor = 1
    def door_close(self):
        """Set door motor to close."""
        self.door_motor = -1
    def door_stop(self):
        """Stop door motor."""
        self.door_motor = 0
    def repair(self):
        """Repair the elevator motor."""
        self.motor_overheat = 0
        self.direction = 0
        self.speed = 0
        self.defect = False
    def repair_door(self):
        """ Repair the door motor."""
        self.door_motor_overheat = 0
        self.door_motor = 0
        self.door_defect = False
    def lamp_on(self, name):
        self.button_lamps[name] = True
    def lamp_off(self, name):
        self.button_lamps[name] = False
    def lamp(self, name):
        return self.button_lamps[name]

def create_background(screen):
    background = pygame.Surface(screen.get_size())
    background = background.convert()
    background.fill((250, 250, 250))
    return background


class Building(pygame.sprite.Sprite):
    def __init__(self, levels):
        pygame.sprite.Sprite.__init__(self)  #call Sprite intializer
        self.levels = levels
        self.image = pygame.Surface((Elevator.width + 3,
                                     Elevator.height*levels + 3))
        self.image.set_colorkey((0, 0, 0))
        self.rect = pygame.Rect(Elevator.x_offset-1, Elevator.y_offset-1,
                                Elevator.width, Elevator.height)
        for i in range(levels):
            pygame.draw.lines(self.image, (0, 0, 255),True,
                              [(1, i*Elevator.height+1),
                               (Elevator.width+1, i*Elevator.height+1),
                               (Elevator.width+1, (i+1)*Elevator.height+1),
                               (1, (i+1)*Elevator.height+1)], 3)

def draw_statistics(screen, elevator):
    font = pygame.font.Font("freesansbold.ttf", BUTTON_FONT_SIZE)
    outputlist = ["level %02d"       % elevator.current_level(),
                "door open: %s"    %(elevator.is_door_open() and "yes" or "no"),
                "door closed: %s"  %(elevator.is_door_closed() and "yes" or "no"),
                "save to open: %s" %(elevator.save_to_open_door() and "yes" or "no"),
                "motor status: %s" % elevator.motor_status(),
                "door motor: %s"   % elevator.door_motor_status(),
                "speed: %s"        %(elevator.speed*1000),
                "door defect: %s"  %(elevator.is_door_defect() and "yes" or "no"),
                "motor defect: %s" %(elevator.is_defect() and "yes" or "no"),
                ]
    y = elevator.y_offset
    for output in outputlist:
        text = font.render(output, 1, (10, 10, 10))
        textpos = text.get_rect(top=y,left=90)
        screen.blit(text, textpos)
        y += 2 + textpos.height

def serve_connection( conn, addr, elevator):
    global terminate
    
    release_connection = threading.Lock()
    release_connection.acquire()
    
    conn.settimeout(1)
    
    def help():
        keys = flist.keys()
        keys.sort()
        return "Possible commands: %s"%", ".join(keys)
    
    def button_states_list():
        keys = elevator.button_states.keys()
        keys.sort()
        lines = []
        for key in keys:
            lines.append("%s:%s"%(key, elevator.button_states[key] and "pressed" or "released"))
        return "\r\n".join(lines)
        
    def quit():
        global terminate
        terminate = True
        return "OK"
    
    def end_connection():
        release_connection.release()

    # concat two statements
    def concat(f,s):
        f()
        return s
    
    # returns a functional operator for returning ok and executing something
    def ok(f):
        return lambda: concat(f, "OK")
    
    # return functor for returning yes or no depending of result of function
    def yesno(f):
        return (lambda: f() and "yes" or "no")
    
    flist = {
        "up": ok(elevator.up),
        "down": ok(elevator.down),
        "stop": ok(elevator.stop),
        "open door": ok(elevator.door_open),
        "close door": ok(elevator.door_close),
        "stop door": ok(elevator.door_stop),
        "repair": ok(elevator.repair),
        "repair door": ok(elevator.repair_door),
        "level?": elevator.current_level,
        "door open?": yesno(elevator.is_door_open),
        "door closed?": yesno(elevator.is_door_closed),
        "save to open?": yesno(elevator.save_to_open_door),
        "defect?": yesno(lambda: elevator.defect),
        "door defect?": yesno(lambda: elevator.door_defect),
        "motor status?": elevator.motor_status,
        "door motor?": elevator.door_motor_status,
        "speed?": lambda: "%s"%(elevator.speed*1000),
        "buttons?": button_states_list,
        "help": help,
        "terminate": quit,
        "exit": ok(end_connection)
    }
    
    # add controls for lamps
    for (name, released, mouseover, pressed,(x, y)) in elevator.buttons:
        flist["lamp %s?"%name] = lambda x=name: elevator.lamp(x) and "on" or "off"
        flist["lamp %s on"%name] = ok(lambda x=name: elevator.lamp_on(x))
        flist["lamp %s off"%name] = ok(lambda x=name: elevator.lamp_off(x))
        #flist["button %s?"%name] = lambda x=name: elevator.button(x) and "pressed" or "released"

    while not terminate and release_connection.locked():
        try:
            conn.send("# ")
        except socket.timeout as msg:
            pass

        data = ""
        while not terminate and release_connection.locked():
            try:
                data += conn.recv(256)
                if data[-1] == "\n": # got a line
                    data = data.strip()
                    if not data:
                        break
                    if data in flist:
                        conn.send(f"{flist[data]()}\r\n")
                        break
                    else:
                        conn.send("unknown command\r\n")
                        break
            except socket.timeout as msg:
                pass
    conn.close()


def ip_server(port, elevator):
    """Server which listens on a port."""
    global terminate
    host = "localhost"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0) # one second timeout
    s.bind((host, port))
    while not terminate:
        try:
            s.listen(1)
            conn, addr = s.accept()
            print('Connected by', addr)
            threading.Thread(target=serve_connection, args=(conn, addr, elevator)).start()

        except socket.timeout as msg:
            #print "Timeout:", msg
            pass

def generate_button( name, label, xy):
    (x,y) = xy
    font = pygame.font.Font("freesansbold.ttf", BUTTON_FONT_SIZE)
    # released button
    released = pygame.Surface((BUTTON_SIZE,BUTTON_SIZE))
    released.fill((210, 210, 210))
    pygame.draw.lines(released, (0, 0, 0),True,
                      [(0, 0), (BUTTON_SIZE-1, 0),
                       (BUTTON_SIZE-1, BUTTON_SIZE-1), (0, BUTTON_SIZE-1)], 1)
    pygame.draw.lines(released,(0, 0, 0), True,
                      [(2, 2), (BUTTON_SIZE-3, 2),
                       (BUTTON_SIZE-3,BUTTON_SIZE-3), (2, BUTTON_SIZE-3)], 1)
    text = font.render(label, True,(0, 0, 0))
    textpos = text.get_rect(centerx=10, centery=10)
    released.blit(text, textpos)
    
    # mouseover-button
    mouseover = pygame.Surface((BUTTON_SIZE, BUTTON_SIZE))
    mouseover.fill((150, 150, 150))
    pygame.draw.lines(mouseover, (0,0,0), True,
                      [(0, 0), (BUTTON_SIZE-1, 0),
                       (BUTTON_SIZE-1, BUTTON_SIZE-1), (0,BUTTON_SIZE-1)], 1)
    pygame.draw.lines(mouseover, (0,0,0), True,
                      [(2,2), (BUTTON_SIZE-3, 2),
                       (BUTTON_SIZE-3,BUTTON_SIZE-3),(2,BUTTON_SIZE-3)], 1)
    text = font.render(label,True,(0,0,0))
    textpos = text.get_rect(centerx=10,centery=10)
    mouseover.blit(text, textpos)
    
    # pressed button
    pressed = pygame.Surface((BUTTON_SIZE,BUTTON_SIZE))
    pressed.fill((190,190,190))
    pygame.draw.lines(pressed,(0,0,0),True,
                      [(0,0),(BUTTON_SIZE-1,0),
                       (BUTTON_SIZE-1,BUTTON_SIZE-1),(0,BUTTON_SIZE-1)], 1)
    pygame.draw.lines(pressed,(0,0,0),True,
                      [(1,1),(BUTTON_SIZE-2,1),
                       (BUTTON_SIZE-2,BUTTON_SIZE-2),(1,BUTTON_SIZE-2)], 1)
    text = font.render(label,True,(0,0,0))
    textpos = text.get_rect(centerx=BUTTON_SIZE/2,centery=BUTTON_SIZE/2)
    pressed.blit(text, textpos)
    
    return name,released,mouseover,pressed, (x,y)

def create_buttons(elevator):
    """Create a list of buttons in the states name,released,
    mouseover, pressed."""
    button_list = []
    # up buttons
    for i in range(elevator.levels-1):
        button_list.append( generate_button("up %d"%(elevator.levels-i-1),"^",
                        (elevator.x_offset + elevator.width + 5,
                          elevator.y_offset + elevator.height*(i+1) + 2) ) )
        button_list.append( generate_button("down %d"%(elevator.levels-i),"v",
                        (elevator.x_offset + elevator.width + 5,
                         elevator.y_offset + elevator.height*i + 27) ) )
        button_list.append( generate_button("level %d"%(elevator.levels-i),
                                            "%d"%(elevator.levels-i),
                        (225,elevator.y_offset + elevator.height*i + 18) ) )
    button_list.append( generate_button("level 1","1",
                    (225,elevator.y_offset + elevator.height*(elevator.levels-1) + 18) ) )
    return button_list

def main(*arg):
    """this function is called when the program starts.
       it initializes everything it needs, then runs in
       a loop until the function returns."""
    global terminate
    
    if len(arg) == 2:
        levels = int(arg[0])
        port = int(arg[1])
    else:
        port = 23300
        levels = 10
    
    if levels<3:
        levels = 3 # minimum
    #Initialize Everything
    pygame.init()
    screen = pygame.display.set_mode((250, levels * Elevator.height + 2*Elevator.y_offset))
    pygame.display.set_caption("Ulno's Elevator Simulator")
    pygame.mouse.set_visible(1)

    #Create The Background
    background = create_background(screen)

    #Prepare Game Objects
    clock = pygame.time.Clock()
    elevator = Elevator( levels )
    building = Building( levels )
    allsprites = pygame.sprite.RenderPlain(elevator)

    threading.Thread(target=ip_server,args=(port, elevator)).start()

    while not terminate:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == QUIT:
                terminate = True
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                terminate = True
            elif event.type == MOUSEBUTTONDOWN:
                #elevator.rect.move_ip(100,100)
                pass
        
        allsprites.update()

        #Draw Everything
        screen.blit(background, (0, 0))
        allsprites.draw(screen)
        # behind building
        screen.blit(building.image,building.rect)
        # draw statistics
        draw_statistics(screen, elevator)
        # buttons
        mousex,mousey = pygame.mouse.get_pos()
        mousebutton1 = pygame.mouse.get_pressed()[0]
        for (name,released,mouseover,pressed,(x,y)) in elevator.buttons:
            if Rect((x,y),(BUTTON_SIZE,BUTTON_SIZE)).collidepoint(mousex,mousey):
                if mousebutton1:
                    elevator.button_states[name] = True
                    buttonshape = pressed
                else:
                    buttonshape = mouseover
                    elevator.button_states[name] = False
            else:
                buttonshape = released
                elevator.button_states[name] = False
            screen.blit(buttonshape,(x,y))
            # check if lamp is on and draw it
            if elevator.button_lamps[name]:
                pygame.draw.lines(screen,(255,0,0),True,
                      [(x-1,y-1),(x+BUTTON_SIZE,y-1),
                       (x+BUTTON_SIZE,y+BUTTON_SIZE),(x-1,y+BUTTON_SIZE)], 1)
                
        # swich screen-buffers
        pygame.display.flip()


#this calls the 'main' function when this script is executed
if __name__ == '__main__':
    main(*(sys.argv)[1:])
