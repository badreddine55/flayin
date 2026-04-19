import pygame
import os
import math


class my_Drone:
    def __init__(self) -> None:
        self.drone_id: int = 0
        self.x: float = 0
        self.y: float = 0
        self.next_x: float = 0
        self.next_y: float = 0
        self.last_x: float = 0
        self.last_y: float = 0

        self.path: list = []
        self.hubs_position: dict[str, tuple] = {}

        # Screen transform — set by Game after compute_scale()
        self.mu: float = 1
        self.offset_x: float = 0
        self.offset_y: float = 0
        self.min_x: float = 0
        self.min_y: float = 0

        self.drone_pos: int = 1

    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        """Convert world coordinates to screen pixels."""
        sx = (wx - self.min_x) * self.mu + self.offset_x
        sy = (wy - self.min_y) * self.mu + self.offset_y
        return sx, sy

    def update(self, global_turn: int, global_count: int) -> None:
        movement_duration = 60

        t = global_count / movement_duration
        t = max(0.0, min(1.0, t))
        smooth_t = t * t * (3 - 2 * t)

        if self.drone_pos >= len(self.path):
            self.x = self.last_x + (self.next_x - self.last_x) * smooth_t
            self.y = self.last_y + (self.next_y - self.last_y) * smooth_t
            return

        if global_turn == self.path[self.drone_pos][1]:
            hub_id = self.path[self.drone_pos][0]
            hx, hy = self.hubs_position[hub_id]

            self.last_x = self.x
            self.last_y = self.y

            # Use world_to_screen instead of raw * mu
            self.next_x, self.next_y = self.world_to_screen(hx, hy)

            self.drone_pos += 1

        self.x = self.last_x + (self.next_x - self.last_x) * smooth_t
        self.y = self.last_y + (self.next_y - self.last_y) * smooth_t


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.WIDTH, self.HEIGHT = 2000, 1800
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Drone Simulation")
        self.clock = pygame.time.Clock()
        self.FPS = 60
        self.running = True
        self.data = None
        self.drones: list = []
        self.hubs_position: dict[str, tuple] = {}
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        self.HUB_RADIUS = 70
        self.DRONE_HALF = 50
        self.PADDING = max(self.HUB_RADIUS, self.DRONE_HALF) + 20  # 90px

        # These are computed in compute_bounds() / compute_scale()
        self.mu: float = 1
        self.offset_x: float = 0
        self.offset_y: float = 0
        self.min_x: float = 0
        self.min_y: float = 0
        self.max_x: float = 0
        self.max_y: float = 0

        self.global_turn = 0
        self.global_count = 0

        self.bg = pygame.image.load(
            "images/congruent_pentagon.png").convert_alpha()
        self.bg = pygame.transform.scale(self.bg, (self.WIDTH, self.HEIGHT))

        self.drone_default_image = pygame.image.load(
            "images/drone.png").convert_alpha()
        self.drone_default_image = pygame.transform.scale(
            self.drone_default_image, (100, 100))

        self.hub_font = pygame.font.SysFont("Arial", 50, bold=True)

    def __del__(self) -> None:
        pygame.quit()

    def compute_bounds(self) -> None:
        """Compute min/max of all hub world coordinates."""
        coords = [hub.coordinates for hub in self.data.zones]
        self.min_x = min(c[0] for c in coords)
        self.min_y = min(c[1] for c in coords)
        self.max_x = max(c[0] for c in coords)
        self.max_y = max(c[1] for c in coords)

    def compute_scale(self) -> None:
        """Fit the entire map inside the screen with padding."""
        usable_w = self.WIDTH - 2 * self.PADDING
        usable_h = self.HEIGHT - 2 * self.PADDING
        range_x = self.max_x - self.min_x
        range_y = self.max_y - self.min_y

        if range_x == 0 and range_y == 0:
            self.mu = min(usable_w, usable_h)
        elif range_x == 0:
            self.mu = usable_h / range_y
        elif range_y == 0:
            self.mu = usable_w / range_x
        else:
            self.mu = min(usable_w / range_x, usable_h / range_y)

        # Center the map in the remaining space after scaling
        self.offset_x = self.PADDING + (usable_w - range_x * self.mu) / 2
        self.offset_y = self.PADDING + (usable_h - range_y * self.mu) / 2

    def world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        """Convert world coordinates to screen pixels."""
        sx = int((wx - self.min_x) * self.mu + self.offset_x)
        sy = int((wy - self.min_y) * self.mu + self.offset_y)
        return sx, sy

    def set_data(self, data) -> None:
        self.data = data
        for hub in self.data.zones:
            self.hubs_position[hub.name] = hub.coordinates
        self.compute_bounds()
        self.compute_scale()

    def set_drones(self, drones) -> None:
        for drone in drones:
            my_drone = my_Drone()
            my_drone.path = drone.path
            my_drone.drone_id = drone.id
            my_drone.hubs_position = self.hubs_position

            # Pass the transform so the drone can call world_to_screen itself
            my_drone.mu = self.mu
            my_drone.offset_x = self.offset_x
            my_drone.offset_y = self.offset_y
            my_drone.min_x = self.min_x
            my_drone.min_y = self.min_y

            name = drone.path[0][0]
            wx, wy = self.hubs_position[name]
            sx, sy = self.world_to_screen(wx, wy)

            my_drone.x = sx
            my_drone.y = sy
            my_drone.next_x = sx
            my_drone.next_y = sy
            my_drone.last_x = sx
            my_drone.last_y = sy

            self.drones.append(my_drone)

    def update_turn(self) -> None:
        self.global_count += 1
        if self.global_count >= 60:
            self.global_count = 0
            self.global_turn += 1

    def run(self) -> None:
        while self.running:
            self.clock.tick(self.FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            self.update_turn()
            self.screen.blit(self.bg, (0, 0))

            
            # Draw hubs
            for hub in self.data.zones:
                
                sx, sy = self.world_to_screen(
                    hub.coordinates[0], hub.coordinates[1]
                )
                neighbors = self.data.get_neighbor_entries(hub)
                for entry in neighbors:
                    ex, ey = self.world_to_screen(entry.neighbor.coordinates[0], entry.neighbor.coordinates[1])

                    # Direction vector
                    dx = ex - sx
                    dy = ey - sy
                    length = math.hypot(dx, dy)
                    if length == 0:
                        continue

                    # Normalize
                    nx, ny = dx / length, dy / length
                    # Perpendicular
                    px, py = -ny, nx

                    # Shorten line so it starts/ends at hub edge
                    gap = self.HUB_RADIUS + 5
                    x1 = sx + nx * gap
                    y1 = sy + ny * gap
                    x2 = ex - nx * gap
                    y2 = ey - ny * gap

                    # Rail offset (distance between the two parallel lines)
                    rail = 6

                    # Draw shadow/background thick line
                    pygame.draw.line(self.screen, (60, 60, 60),
                        (int(x1), int(y1)), (int(x2), int(y2)), 10)

                    # Left rail
                    pygame.draw.line(self.screen, (180, 180, 180),
                                    (int(x1 + px * rail), int(y1 + py * rail)),
                                    (int(x2 + px * rail), int(y2 + py * rail)), 3)

                    # Right rail
                    pygame.draw.line(self.screen, (180, 180, 180),
                                    (int(x1 - px * rail), int(y1 - py * rail)),
                                    (int(x2 - px * rail), int(y2 - py * rail)), 3)
                pygame.draw.circle(
                    self.screen,
                    self.get_rgb(hub.color),
                    (sx, sy),
                    self.HUB_RADIUS
                )
                pygame.draw.circle(
                    self.screen,
                    (255, 255, 255),
                    (sx, sy),
                    self.HUB_RADIUS - 6,
                    width=4
                )
                label = self.hub_font.render("H", True, (255, 255, 255))
                label_rect = label.get_rect(center=(sx, sy))
                self.screen.blit(label, label_rect)
                


    
            # Draw drones
            for drone in self.drones:
                drone.update(self.global_turn, self.global_count)
                # drone.x/y are already screen coords — just center the image
                blit_x = int(drone.x) - self.drone_default_image.get_width() // 2
                blit_y = int(drone.y) - self.drone_default_image.get_height() // 2
                self.screen.blit(self.drone_default_image, (blit_x, blit_y))

            pygame.display.flip()

        pygame.quit()

    @staticmethod
    def get_rgb(color_name: str) -> tuple[int, int, int]:
        """Return an RGB tuple for a given color name."""
        colors = {
            "white": (255, 255, 255), "black": (0, 0, 0),
            "red": (255, 0, 0), "green": (0, 255, 0),
            "blue": (0, 0, 255), "yellow": (255, 255, 0),
            "cyan": (0, 255, 255), "magenta": (255, 0, 255),
            "gray": (128, 128, 128),
            "dark_gray": (64, 64, 64), "light_gray": (192, 192, 192),
            "orange": (255, 165, 0), "dark_orange": (255, 140, 0),
            "purple": (128, 0, 128), "violet": (238, 130, 238),
            "pink": (255, 192, 203), "hot_pink": (255, 105, 180),
            "brown": (139, 69, 19), "maroon": (128, 0, 0),
            "lime": (50, 205, 50), "dark_green": (0, 100, 0),
            "navy": (0, 0, 128), "sky_blue": (135, 206, 235),
            "teal": (0, 128, 128), "turquoise": (64, 224, 208),
            "gold": (255, 215, 0), "silver": (192, 192, 192),
            "beige": (245, 245, 220), "coral": (255, 127, 80),
            "salmon": (250, 128, 114), "indigo": (75, 0, 130),
            "olive": (128, 128, 0), "chocolate": (210, 105, 30),
            "crimson": (220, 20, 60), "khaki": (240, 230, 140),
            "lavender": (230, 230, 250),
        }
        return colors.get(color_name.lower(), (255, 255, 255))