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
    # Find all .png files that are not _speaking or _active frames
    base_files = glob.glob(os.path.join(image_dir, "*.png"))
    
    for base_path in base_files:
        filename = os.path.basename(base_path)
        if "_speaking" in filename or "_active" in filename:
            continue  # Skip speaking/active frames, pair them later
        
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
        print(f"Loaded emotion: {emotion_name}")
    
    return emotions

def load_listening(image_dir):
    """
    Load listening state frames:
      listening.png (base)
      listening_active.png (active, optional - will reuse base if missing)
    Returns: (base_surface, active_surface) or None if not found
    """
    base_path = os.path.join(image_dir, "listening.png")
    active_path = os.path.join(image_dir, "listening_active.png")
    
    if not os.path.exists(base_path):
        print("Warning: listening.png not found")
        return None
    
    base = pygame.image.load(base_path).convert_alpha()
    base = pygame.transform.smoothscale(base, SCREEN_SIZE)
    
    if os.path.exists(active_path):
        active = pygame.image.load(active_path).convert_alpha()
        active = pygame.transform.smoothscale(active, SCREEN_SIZE)
    else:
        active = base  # Reuse base if active frame missing
    
    print("Loaded listening state")
    return (base, active)

def main():
    pygame.init()
    screen = pygame.display.set_mode(SCREEN_SIZE)
    pygame.display.set_caption("Emotion Display Test")
    clock = pygame.time.Clock()

    # Automatically load all emotions and listening state
    emotions = load_emotions(IMAGE_DIR)
    listening_frames = load_listening(IMAGE_DIR)
    
    if not emotions:
        print(f"ERROR: No emotion images found in {IMAGE_DIR}")
        sys.exit(1)
    
    # Current state
    emotion_list = sorted(emotions.keys())
    current_idx = 0
    current_emotion = emotion_list[current_idx]
    is_speaking = False
    is_listening = False
    show_alt = False
    last_toggle = pygame.time.get_ticks()

    print(f"\nLoaded {len(emotions)} emotions: {', '.join(emotion_list)}")
    print("\nControls:")
    print("  L         - Toggle listening")
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
                elif event.key == pygame.K_l:
                    is_listening = not is_listening
                    show_alt = False
                    print(f"Listening: {is_listening}")
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

        # Toggle logic for active states
        if is_listening or is_speaking:
            now = pygame.time.get_ticks()
            if now - last_toggle >= TOGGLE_MS:
                last_toggle = now
                show_alt = not show_alt

        # Draw priority: listening > speaking > normal emotion
        screen.fill((0, 0, 0))
        
        if is_listening and listening_frames:
            # Show listening state (overrides emotion)
            base, active = listening_frames
            frame = active if show_alt else base
            state_text = "listening"
        elif is_speaking:
            # Show speaking animation
            base, speaking = emotions[current_emotion]
            frame = speaking if show_alt else base
            state_text = f"{current_emotion} (speaking)"
        else:
            # Show normal emotion
            base, _ = emotions[current_emotion]
            frame = base
            state_text = current_emotion
        
        screen.blit(frame, (0, 0))
        
        # Display current state (optional, for debugging)
        font = pygame.font.Font(None, 24)
        text = font.render(state_text, True, (255, 255, 0))
        screen.blit(text, (10, 10))
        
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()

if __name__ == "__main__":
    main()