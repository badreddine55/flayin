import pygame

pygame.init()

screen = pygame.display.set_mode((1500, 800))
clock = pygame.time.Clock()

MOVEMENT_DURATION = 60  # frames per hub-to-hub segment

hubs = [
    (200, 120),
    (500, 300),
    (400, 200),
    (100, 560),
    (90, 220),
]

def update_drone_position(hub, next_hub, frame):
    t = frame / MOVEMENT_DURATION
    t = max(0.0, min(1.0, t))
    smooth_t = t * t * (3 - 2 * t)
    x1, y1 = hub
    x2, y2 = next_hub
    x = x1 + (x2 - x1) * smooth_t
    y = y1 + (y2 - y1) * smooth_t
    return x, y

hub_font = pygame.font.SysFont("Arial", 25, bold=True)
button_rect = pygame.Rect(700, 700, 200, 50)

frame_count = 0
current_index = 0
paused = False
pos = hubs[0]  # initialize so first frame is safe

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if button_rect.collidepoint(event.pos):
                paused = not paused

    screen.fill((15, 23, 42))

    # Draw edges
    for i in range(len(hubs)):
        next_i = (i + 1) % len(hubs)
        pygame.draw.line(screen, (100, 100, 100), hubs[i], hubs[next_i], 5)

    # Draw hubs
    for i, hub in enumerate(hubs):
        pygame.draw.circle(screen, (96, 165, 250), hub, 30)
        label = hub_font.render(f"D{i}", True, (255, 255, 255))
        screen.blit(label, label.get_rect(center=hub))

    # Update and draw drone
    hub = hubs[current_index]
    next_hub = hubs[(current_index + 1) % len(hubs)]

    if not paused:
        pos = update_drone_position(hub, next_hub, frame_count)
        frame_count += 1
        if frame_count >= MOVEMENT_DURATION:
            frame_count = 0
            current_index = (current_index + 1) % len(hubs)

    pygame.draw.circle(screen, (255, 0, 0), (int(pos[0]), int(pos[1])), 10)

    # Draw button
    pygame.draw.rect(screen, (0, 150, 255), button_rect)
    text = hub_font.render("Pause/Resume", True, (255, 255, 255))
    screen.blit(text, text.get_rect(center=button_rect.center))

    pygame.display.flip()
    clock.tick(60)