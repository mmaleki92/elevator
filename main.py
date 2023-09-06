import sys
import pygame
import socket
import threading
from pygame.locals import *

class Elevator:
    def __init__(self, levels):
        self.levels = levels
        # Initialize elevator state variables
        self.position = 0.0
        self.door_position = 0.0
        self.direction = 0  # 0: stop, 1: up, -1: down
        self.speed = 0.0
        self.door_motor = 0  # 0: off, 1: opening, -1: closing
        self.motor_overheat = 0
        self.door_motor_overheat = 0
        self.defect = False
        self.door_defect = False
        # Initialize Pygame components for visualization
        self.init_pygame()

    def init_pygame(self):
        pygame.init()
        self.screen = pygame.display.set_mode((250, self.levels * 50))
        pygame.display.set_caption("Elevator Simulator")
        self.clock = pygame.time.Clock()
        self.all_sprites = pygame.sprite.Group()
        self.create_buttons()
        self.create_background()
        self.load_fonts()

    def create_buttons(self):
        # Create elevator buttons and lamps
        self.buttons = []
        for level in range(self.levels):
            button = ElevatorButton(level)
            lamp = Lamp(level)
            self.buttons.append(button)
            self.buttons.append(lamp)
            self.all_sprites.add(button, lamp)

    def create_background(self):
        # Create a simple background for visualization
        self.background = pygame.Surface(self.screen.get_size())
        self.background.fill((250, 250, 250))
        for level in range(self.levels):
            pygame.draw.rect(
                self.background,
                (0, 0, 255),
                (0, level * 50, 40, 50),
                3
            )

    def load_fonts(self):
        # Load fonts for rendering text
        self.font = pygame.font.Font("freesansbold.ttf", 13)

    def run_simulation(self):
        while not self.defect:
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.defect = True
                elif event.type == KEYDOWN and event.key == K_ESCAPE:
                    self.defect = True
            self.update()
            self.draw()

    def update(self):
        # Update elevator position and state
        if self.direction == 1:
            if self.speed < 0.01:
                self.speed += 0.0001
        elif self.direction == -1:
            if self.speed > -0.01:
                self.speed -= 0.0001
        else:
            if abs(self.speed) > 0.00001:
                self.speed -= 0.0001
            else:
                self.speed = 0.0

        # Update elevator position based on speed
        self.position += self.speed

        # Check for elevator position limits
        if self.position < 0.0:
            self.position = 0.0
            self.motor_overheat += 1
        elif self.position > 1.0:
            self.position = 1.0
            self.motor_overheat += 1

        # Update door status and motor
        if not self.door_defect:
            if self.door_motor == -1:
                self.door_position -= 0.01
            elif self.door_motor == 1:
                self.door_position += 0.01

            # Check for door position limits
            if self.door_position < 0.0:
                self.door_position = 0.0
                self.door_motor_overheat += 1
            elif self.door_position > 1.0:
                self.door_position = 1.0
                self.door_motor_overheat += 1

    def draw(self):
        # Draw elevator and buttons
        self.screen.blit(self.background, (0, 0))
        self.all_sprites.update()
        self.all_sprites.draw(self.screen)

        # Display elevator information
        self.display_info()

        pygame.display.flip()
        self.clock.tick(60)

    def display_info(self):
        # Display elevator information on the screen
        info_texts = [
            f"Current Level: {self.current_level()}",
            f"Door Open: {'Yes' if self.is_door_open() else 'No'}",
            f"Door Closed: {'Yes' if self.is_door_closed() else 'No'}",
            f"Safe to Open: {'Yes' if self.save_to_open_door() else 'No'}",
            f"Motor Status: {self.motor_status()}",
            f"Door Motor: {self.door_motor_status()}",
            f"Speed: {self.speed * 1000:.2f} mm/s",
            f"Door Defect: {'Yes' if self.is_door_defect() else 'No'}",
            f"Motor Defect: {'Yes' if self.is_defect() else 'No'}"
        ]

        y_offset = 5
        for text in info_texts:
            info_text = self.font.render(text, True, (10, 10, 10))
            self.screen.blit(info_text, (90, y_offset))
            y_offset += info_text.get_height() + 2

    def current_level(self):
        # Calculate and return the current level
        return int(self.position * (self.levels - 1) + 0.5)

    def is_defect(self):
        return self.defect

    def is_door_defect(self):
        return self.door_defect

    def is_door_closed(self):
        return self.door_position <= 0.1

    def is_door_open(self):
        return self.door_position >= 0.9

    def save_to_open_door(self):
        delta = int(self.position * (self.levels - 1)) - self.position * (self.levels - 1)
        return -0.04 < delta < 0.04

    def motor_status(self):
        if self.motor_overheat < 6:
            return "ok"
        elif self.motor_overheat < 60:
            return "overheating"
        else:
            self.defect = True
            return "broken"

    def door_motor_status(self):
        if self.door_motor_overheat < 6:
            return "ok"
        elif self.door_motor_overheat < 60:
            return "overheating"
        else:
            self.door_defect = True
            return "broken"

    def up(self):
        self.direction = 1

    def down(self):
        self.direction = -1

    def stop(self):
        self.direction = 0

    def door_open(self):
        self.door_motor = 1

    def door_close(self):
        self.door_motor = -1

    def door_stop(self):
        self.door_motor = 0

    def repair(self):
        self.motor_overheat = 0
        self.direction = 0
        self.speed = 0.0
        self.defect = False

    def repair_door(self):
        self.door_motor_overheat = 0
        self.door_motor = 0
        self.door_defect = False

    def lamp_on(self, name):
        for button in self.buttons:
            if isinstance(button, Lamp) and button.label == name:
                button.on()

    def lamp_off(self, name):
        for button in self.buttons:
            if isinstance(button, Lamp) and button.label == name:
                button.off()

class ElevatorButton(pygame.sprite.Sprite):
    def __init__(self, level):
        super().__init__()
        self.image = pygame.Surface((21, 21))
        self.rect = self.image.get_rect()
        self.rect.x = 170
        self.rect.y = 52 * (level + 1) - 21
        self.label = f"Level {level + 1}"
        self.font = pygame.font.Font("freesansbold.ttf", 13)
        self.state = "released"
        self.color = (210, 210, 210)
        self.pressed_color = (190, 190, 190)
        self.mouseover_color = (150, 150, 150)
        self.render_text()  # Moved render_text to __init__

    def render_text(self):
        text = self.font.render(self.label, True, (0, 0, 0))
        text_rect = text.get_rect(center=(10, 10))
        # Fill the button with the appropriate color based on the state
        if self.state == "pressed":
            self.image.fill(self.pressed_color)
        else:
            self.image.fill(self.color)
        self.image.blit(text, text_rect)

    def on(self):
        self.state = "pressed"
        self.render_text()  # Update the button color when pressed

    def off(self):
        self.state = "released"
        self.render_text()  # Update the button color when released
        


class Lamp(ElevatorButton):
    def on(self):
        self.state = "pressed"
        self.image.fill((255, 0, 0))
        self.render_text()


def serve_connection(conn, addr, elevator):
    conn.settimeout(1)
    while not elevator.is_defect():
        try:
            conn.send("# ")
            data = conn.recv(256)
            if not data:
                break
            command = data.strip()
            response = elevator.handle_command(command)
            conn.send(f"{response}\r\n")
        except socket.timeout:
            pass
    conn.close()


class ElevatorServer:
    def __init__(self, elevator, port=23300):
        self.elevator = elevator
        self.port = port
        self.terminate = False
        self.sock = None

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(1.0)
        self.sock.bind(("localhost", self.port))
        while not self.terminate:
            try:
                self.sock.listen(1)
                conn, addr = self.sock.accept()
                threading.Thread(target=serve_connection, args=(conn, addr, self.elevator)).start()
            except socket.timeout:
                pass

    def stop(self):
        self.terminate = True
        if self.sock:
            self.sock.close()


def main():
    levels = 10  # Change this to the desired number of levels
    elevator = Elevator(levels)
    elevator_server = ElevatorServer(elevator)
    elevator.run_simulation()
    elevator_server.start()
    elevator_server.stop()


if __name__ == '__main__':
    main()
