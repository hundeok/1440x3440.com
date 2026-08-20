import pygame
import sys

pygame.init()
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
clock = pygame.time.Clock()

color = (255, 0, 0)
fs = False

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_f:
            print("Toggling FS")
            pygame.display.toggle_fullscreen()
            fs = not fs
        elif event.type == pygame.VIDEORESIZE:
            print(f"Resize to {event.w}x{event.h}")
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

    screen.fill(color)
    pygame.draw.rect(screen, (0, 255, 0), (100, 100, screen.get_width()-200, screen.get_height()-200))
    pygame.display.flip()
    clock.tick(60)
