import pygame
import os
import sys
import glob

SCREEN_SIZE = (320, 240)
IMAGE_DIR = "src/Display"
TOGGLE_MS = 1500  # Frame toggle interval (milliseconds)

def load_emotions(image_dir):
    """
    Automatically load all emotion images
    Naming convention: <emotion>.png (static) and <emotion>_speaking.png (speaking)
    Returns: {emotion_name: (base_surface, speaking_surface)}
    """
    emotions = {}
    # Find all .png files that are not _speaking frames
    base_files = glob.glob(os.path.join(image_dir, "*.png"))
    
    for base_path in base_files:
        filename = os.path.basename(base_path)
        if "_speaking" in filename:
            continue  # Skip speaking frames, pair them later
        
        emotion_name = os.path.splitext(filename)[0]  # e.g. "happy"
        speaking_path = os.path.join(image_dir, f"{emotion_name}_speaking.png")
        
        # Load and scale
        base = pygame.image.load(base_path).convert_alpha()
        base = pygame.transform.smoothscale(base, SCREEN_SIZE)
        
        if os.path.exists(speaking_path):
            speaking = pygame.image.load(speaking_path).convert_alpha()
            speaking = pygame.transform.smoothscale(speaking, SCREEN_SIZE)
        else:
            speaking = base  # Reuse static frame if no speaking frame exists
        
        emotions[emotion_name] = (base, speaking)
        print(f"Loaded: {emotion_name}")
    
    return emotions

def main():
    pygame.init()
    screen = pygame.display.set_mode(SCREEN_SIZE)
    pygame.display.set_caption("Emotion Display Test")
    clock = pygame.time.Clock()

    # Automatically load all emotions
    emotions = load_emotions(IMAGE_DIR)
    
    if not emotions:
        print(f"ERROR: No emotion images found in {IMAGE_DIR}")
        sys.exit(1)
    
    # Current state
    emotion_list = sorted(emotions.keys())
    current_idx = 0
    current_emotion = emotion_list[current_idx]
    is_speaking = False
    show_alt = False
    last_toggle = pygame.time.get_ticks()

    print(f"\nLoaded {len(emotions)} emotions: {', '.join(emotion_list)}")
    print("\nControls:")
    print("  SPACE     - Toggle speaking")
    print("  LEFT/RIGHT - Switch emotion")
    print("  ESC       - Quit")
    print(f"\nCurrent: {current_emotion}")

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    is_speaking = not is_speaking
                    show_alt = False
                    print(f"Speaking: {is_speaking}")
                elif event.key == pygame.K_RIGHT:
                    current_idx = (current_idx + 1) % len(emotion_list)
                    current_emotion = emotion_list[current_idx]
                    print(f"Current: {current_emotion}")
                    show_alt = False
                elif event.key == pygame.K_LEFT:
                    current_idx = (current_idx - 1) % len(emotion_list)
                    current_emotion = emotion_list[current_idx]
                    print(f"Current: {current_emotion}")
                    show_alt = False

        # Toggle logic
        if is_speaking:
            now = pygame.time.get_ticks()
            if now - last_toggle >= TOGGLE_MS:
                last_toggle = now
                show_alt = not show_alt

        # Draw current emotion
        base, speaking = emotions[current_emotion]
        frame = speaking if (is_speaking and show_alt) else base
        screen.fill((0, 0, 0))
        screen.blit(frame, (0, 0))
        
        # Display current emotion name (optional, for debugging)
        font = pygame.font.Font(None, 24)
        text = font.render(f"{current_emotion} {'(speaking)' if is_speaking else ''}", 
                          True, (255, 255, 0))
        screen.blit(text, (10, 10))
        
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()

if __name__ == "__main__":
    main()