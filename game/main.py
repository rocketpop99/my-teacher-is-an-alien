import asyncio
import pygame

# ==========================================
# THE "NUCLEAR" TEST
# If this doesn't run, the issue is not the code,
# it is the server or Pygbag installation.
# ==========================================

WIDTH = 1000
HEIGHT = 650

async def main():
    print("--- NUCLEAR TEST STARTING ---")
    pygame.init()
    
    # Force a specific window size
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Nuclear Test")
    
    # Create a simple surface (The Player)
    player = pygame.Surface((50, 50))
    player.fill((0, 255, 0)) # Green Square
    
    x, y = 100, 100
    vx, vy = 4, 4
    
    clock = pygame.time.Clock()
    
    print("--- ENTERING MAIN LOOP ---")
    
    running = True
    while running:
        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Allow quitting via keyboard to test input
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
    
        # 2. Update Logic (Bouncing Ball)
        x += vx
        y += vy
        
        # Bounce off walls
        if x < 0 or x > WIDTH - 50:
            vx *= -1
if y < 0 or y > HEIGHT - 50:
    vy *= -1
        
        # 3. Draw Everything
        screen.fill((50, 50, 50)) # Dark Gray Background
        
        # Draw the green player
        screen.blit(player, (x, y))
        
        # Draw a center reference circle (No assets needed)
        pygame.draw.circle(screen, (255, 0, 0), (WIDTH//2, HEIGHT//2), 20)
        
        # 4. Flip Display
        pygame.display.flip()
        
        # 5. Cap FPS
        clock.tick(60)
        
        # 6. CRITICAL FOR WEB: Yield control to browser
        await asyncio.sleep(0)
    
    print("--- TEST FINISHED ---")
    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())
