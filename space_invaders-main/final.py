import pygame
from pygame import mixer
from pygame.locals import *
import random
import json
import os

# Initialize Pygame and mixer
pygame.mixer.pre_init(44100, -16, 2, 512)
mixer.init()
pygame.init()

# Define constants
FPS = 60
SCREEN_WIDTH, SCREEN_HEIGHT = 600, 800
RED, GREEN, WHITE, BLUE, YELLOW = (255, 0, 0), (0, 255, 0), (255, 255, 255), (0, 0, 255), (255, 255, 0)

# Setup screen and clock
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Space Invaders')
clock = pygame.time.Clock()

# Define fonts
font20 = pygame.font.SysFont('Constantia', 20)
font30 = pygame.font.SysFont('Constantia', 30)
font40 = pygame.font.SysFont('Constantia', 40)

# Helper functions for sound
def load_sound(file_path, volume=0.25):
    try:
        sound = pygame.mixer.Sound(file_path)
        sound.set_volume(volume)
        return sound
    except: return None

def load_music(file_path, volume=0.1):
    try:
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.set_volume(volume)
        return True
    except: return False

def play_sound(sound):
    if sound: sound.play()

# Load sounds
explosion_fx = load_sound("img/explosion.mp3")
explosion2_fx = load_sound("img/explosion2.mp3")
laser_fx = load_sound("img/laser.mp3")
powerup_fx = load_sound("img/powerup.mp3")

# Load and play background music
if load_music("img/background_music.mp3"):
    pygame.mixer.music.play(-1)

# Game variables
rows, cols = 5, 5
alien_cooldown = 1000
last_alien_shot = pygame.time.get_ticks()
countdown = 3
last_count = pygame.time.get_ticks()
game_over = 0
score = 0
high_score = 0
level = 1
powerup_chance = 0.1

# Load high score
def load_high_score():
    global high_score
    try:
        if os.path.exists("highscore.json"):
            with open("highscore.json", "r") as f:
                data = json.load(f)
                high_score = data.get("high_score", 0)
    except: high_score = 0

def save_high_score(score):
    global high_score
    if score > high_score:
        high_score = score
        try:
            with open("highscore.json", "w") as f:
                json.dump({"high_score": high_score}, f)
        except: pass

load_high_score()

# Load background
try:
    bg = pygame.image.load("img/bg.png")
except:
    bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    bg.fill((0, 0, 50))

# Pause menu background
pause_bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
pause_bg.set_alpha(200)
pause_bg.fill((0, 0, 0))

def draw_bg():
    screen.blit(bg, (0, 0))

def draw_text(text, font, text_col, x, y):
    img = font.render(text, True, text_col)
    screen.blit(img, img.get_rect(center=(x, y)))

def draw_score():
    score_panel = pygame.Surface((SCREEN_WIDTH, 60))
    score_panel.set_alpha(150)
    score_panel.fill((0, 0, 0))
    screen.blit(score_panel, (0, 0))
    
    score_text = font20.render(f'Score: {score}', True, WHITE)
    high_score_text = font20.render(f'High: {high_score}', True, WHITE)
    level_text = font20.render(f'Level: {level}', True, WHITE)
    
    screen.blit(score_text, (20, 20))
    screen.blit(level_text, (SCREEN_WIDTH // 2 - level_text.get_width() // 2, 20))
    screen.blit(high_score_text, (SCREEN_WIDTH - high_score_text.get_width() - 20, 20))

# Game classes
class PowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y, type):
        pygame.sprite.Sprite.__init__(self)
        self.type = type
        self.image = pygame.Surface((20, 20))
        
        if type == "health":
            self.image.fill(GREEN)
            pygame.draw.circle(self.image, WHITE, (10, 10), 8, 2)
            pygame.draw.line(self.image, WHITE, (10, 5), (10, 15), 2)
            pygame.draw.line(self.image, WHITE, (5, 10), (15, 10), 2)
        elif type == "speed":
            self.image.fill(BLUE)
            pygame.draw.polygon(self.image, WHITE, [(10, 5), (7, 10), (13, 10), (10, 15)])
        elif type == "rapid_fire":
            self.image.fill(YELLOW)
            pygame.draw.line(self.image, WHITE, (5, 5), (5, 15), 2)
            pygame.draw.line(self.image, WHITE, (10, 5), (10, 15), 2)
            pygame.draw.line(self.image, WHITE, (15, 5), (15, 15), 2)
            
        self.rect = self.image.get_rect()
        self.rect.center = [x, y]
        self.speed = 2
        
    def update(self):
        self.rect.y += self.speed
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()

class Spaceship(pygame.sprite.Sprite):
    def __init__(self, x, y, health):
        pygame.sprite.Sprite.__init__(self)
        try:
            self.image = pygame.image.load("img/spaceship.png")
        except:
            self.image = pygame.Surface((50, 50))
            self.image.fill((0, 200, 0))
            pygame.draw.polygon(self.image, (200, 200, 200), [(25, 0), (0, 50), (50, 50)])
            
        self.rect = self.image.get_rect()
        self.rect.center = [x, y]
        self.health_start = health
        self.health_remaining = health
        self.last_shot = pygame.time.get_ticks()
        self.speed = 8
        self.cooldown = 500
        self.power_timer = 0
        self.rapid_fire = False
        self.speed_boost = False

    def update(self):
        time_now = pygame.time.get_ticks()
        if self.power_timer > 0 and time_now > self.power_timer:
            self.power_timer = 0
            if self.rapid_fire:
                self.cooldown = 500
                self.rapid_fire = False
            if self.speed_boost:
                self.speed = 8
                self.speed_boost = False

        game_over = 0

        # Movement
        key = pygame.key.get_pressed()
        if key[pygame.K_LEFT] and self.rect.left > 0:
            self.rect.x -= self.speed
        if key[pygame.K_RIGHT] and self.rect.right < SCREEN_WIDTH:
            self.rect.x += self.speed

        # Shooting
        if key[pygame.K_SPACE] and time_now - self.last_shot > self.cooldown:
            play_sound(laser_fx)
            bullet = Bullets(self.rect.centerx, self.rect.top)
            bullet_group.add(bullet)
            self.last_shot = time_now
            
            if self.rapid_fire:
                bullet_group.add(Bullets(self.rect.centerx - 20, self.rect.top))
                bullet_group.add(Bullets(self.rect.centerx + 20, self.rect.top))

        # Collision mask
        self.mask = pygame.mask.from_surface(self.image)

        # Health bar
        pygame.draw.rect(screen, RED, (self.rect.x, (self.rect.bottom + 10), self.rect.width, 15))
        if self.health_remaining > 0:
            pygame.draw.rect(screen, GREEN, (self.rect.x, (self.rect.bottom + 10), 
                            int(self.rect.width * (self.health_remaining / self.health_start)), 15))
        elif self.health_remaining <= 0:
            explosion_group.add(Explosion(self.rect.centerx, self.rect.centery, 3))
            play_sound(explosion2_fx)
            self.kill()
            game_over = -1
            save_high_score(score)
            
        return game_over

    def apply_powerup(self, powerup_type):
        play_sound(powerup_fx)
        if powerup_type == "health" and self.health_remaining < self.health_start:
            self.health_remaining += 1
        elif powerup_type == "speed":
            self.speed = 12
            self.speed_boost = True
            self.power_timer = pygame.time.get_ticks() + 5000
        elif powerup_type == "rapid_fire":
            self.cooldown = 200
            self.rapid_fire = True
            self.power_timer = pygame.time.get_ticks() + 5000

class Bullets(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        try:
            self.image = pygame.image.load("img/bullet.png")
        except:
            self.image = pygame.Surface((5, 15))
            self.image.fill((255, 255, 0))
            
        self.rect = self.image.get_rect()
        self.rect.center = [x, y]

    def update(self):
        self.rect.y -= 5
        if self.rect.bottom < 0:
            self.kill()
            
        if pygame.sprite.spritecollide(self, alien_group, True):
            global score
            score += 10
            self.kill()
            play_sound(explosion_fx)
            explosion_group.add(Explosion(self.rect.centerx, self.rect.centery, 2))
            
            if random.random() < powerup_chance:
                powerup_type = random.choice(["health", "speed", "rapid_fire"])
                powerup_group.add(PowerUp(self.rect.centerx, self.rect.centery, powerup_type))

class Aliens(pygame.sprite.Sprite):
    def __init__(self, x, y, alien_type, row, col):
        pygame.sprite.Sprite.__init__(self)
        self.alien_type = alien_type
        self.row, self.col = row, col
        
        try:
            self.image = pygame.image.load(f"img/alien{alien_type}.png")
        except:
            self.image = pygame.Surface((40, 40))
            color = (100 + alien_type * 30, 50, 150 - alien_type * 20)
            self.image.fill(color)
            pygame.draw.circle(self.image, WHITE, (10, 15), 5)
            pygame.draw.circle(self.image, WHITE, (30, 15), 5)
            pygame.draw.rect(self.image, WHITE, (10, 25, 20, 5))
            
        self.rect = self.image.get_rect()
        self.rect.center = [x, y]
        
        # Different aliens have different health
        self.health = 3 if alien_type == 5 else 1

class AlienGroup:
    def __init__(self):
        self.move_direction = 1
        self.move_counter = 0
        
    def update(self):
        all_aliens = alien_group.sprites()
        if not all_aliens:
            return
            
        # Check boundaries
        leftmost = min(alien.rect.left for alien in all_aliens)
        rightmost = max(alien.rect.right for alien in all_aliens)
        
        move_down = False
        if rightmost >= SCREEN_WIDTH or leftmost <= 0:
            self.move_direction *= -1
            move_down = True
        
        # Move aliens
        for alien in all_aliens:
            alien.rect.x += self.move_direction
            if move_down:
                alien.rect.y += 10

class Alien_Bullets(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        try:
            self.image = pygame.image.load("img/alien_bullet.png")
        except:
            self.image = pygame.Surface((5, 15))
            self.image.fill((255, 0, 0))
            
        self.rect = self.image.get_rect()
        self.rect.center = [x, y]

    def update(self):
        self.rect.y += 2
        if self.rect.top > SCREEN_HEIGHT:
            self.kill()
            
        if pygame.sprite.spritecollide(self, spaceship_group, False, pygame.sprite.collide_mask):
            self.kill()
            play_sound(explosion2_fx)
            spaceship.health_remaining -= 1
            explosion_group.add(Explosion(self.rect.centerx, self.rect.centery, 1))

class Explosion(pygame.sprite.Sprite):
    def __init__(self, x, y, size):
        pygame.sprite.Sprite.__init__(self)
        self.images = []
        
        image_loaded = True
        for num in range(1, 6):
            try:
                img = pygame.image.load(f"img/exp{num}.png")
                img = pygame.transform.scale(img, (size * 20, size * 20))
                self.images.append(img)
            except:
                image_loaded = False
                break
        
        if not image_loaded:
            self.images = []
            for alpha in range(0, 255, 51):
                surf = pygame.Surface((size * 20, size * 20), pygame.SRCALPHA)
                pygame.draw.circle(surf, (255, 200, 50, 255 - alpha), (size * 10, size * 10), size * 10)
                pygame.draw.circle(surf, (255, 50, 0, 255 - alpha), (size * 10, size * 10), size * 7)
                self.images.append(surf)
                
        self.index = 0
        self.image = self.images[self.index]
        self.rect = self.image.get_rect()
        self.rect.center = [x, y]
        self.counter = 0

    def update(self):
        explosion_speed = 3
        self.counter += 1

        if self.counter >= explosion_speed and self.index < len(self.images) - 1:
            self.counter = 0
            self.index += 1
            self.image = self.images[self.index]

        if self.index >= len(self.images) - 1 and self.counter >= explosion_speed:
            self.kill()

# Create sprite groups
spaceship_group = pygame.sprite.Group()
bullet_group = pygame.sprite.Group()
alien_group = pygame.sprite.Group()
alien_bullet_group = pygame.sprite.Group()
explosion_group = pygame.sprite.Group()
powerup_group = pygame.sprite.Group()
alien_controller = AlienGroup()

def create_aliens():
    global cols
    
    max_alien_width = 80
    max_possible_cols = SCREEN_WIDTH // max_alien_width
    cols = min(cols, max_possible_cols)
    
    spacing_x = SCREEN_WIDTH / (cols + 1)
    
    for row in range(rows):
        for col in range(cols):
            alien_type = 5 if row == 0 and level >= 3 else (row % 4) + 1
            alien_x = spacing_x * (col + 1)
            alien_y = 100 + row * 70
            
            alien_group.add(Aliens(alien_x, alien_y, alien_type, row, col))

def draw_message_box(message_list, y_pos=None):
    if y_pos is None:
        y_pos = SCREEN_HEIGHT // 2 - (len(message_list) * 40) // 2
    
    msg_bg = pygame.Surface((SCREEN_WIDTH - 100, len(message_list) * 50 + 40))
    msg_bg.set_alpha(200)
    msg_bg.fill((0, 0, 0))
    
    msg_bg_rect = msg_bg.get_rect(center=(SCREEN_WIDTH // 2, y_pos + (len(message_list) * 50) // 2))
    screen.blit(msg_bg, msg_bg_rect)
    
    for i, (msg, font_obj, color) in enumerate(message_list):
        draw_text(msg, font_obj, color, SCREEN_WIDTH // 2, y_pos + i * 50)

def draw_powerup_indicators():
    if hasattr(spaceship, 'rapid_fire') and spaceship.rapid_fire:
        indicator = pygame.Surface((120, 25))
        indicator.set_alpha(200)
        indicator.fill(YELLOW)
        screen.blit(indicator, (10, 70))
        power_text = font20.render("Rapid Fire", True, (0, 0, 0))
        screen.blit(power_text, (20, 72))
        
    if hasattr(spaceship, 'speed_boost') and spaceship.speed_boost:
        indicator = pygame.Surface((120, 25))
        indicator.set_alpha(200)
        indicator.fill(BLUE)
        screen.blit(indicator, (10, 100))
        power_text = font20.render("Speed Boost", True, (0, 0, 0))
        screen.blit(power_text, (20, 102))

def toggle_music():
    global muted
    muted = not muted
    pygame.mixer.music.pause() if muted else pygame.mixer.music.unpause()

# Create player
spaceship = Spaceship(int(SCREEN_WIDTH / 2), SCREEN_HEIGHT - 100, 3)
spaceship_group.add(spaceship)
create_aliens()

# Game state variables
paused = False
show_controls = False
muted = False

# Game loop
run = True
while run:
    clock.tick(FPS)
    draw_bg()

    if paused:
        if show_controls:
            screen.blit(pause_bg, (0, 0))
            controls = [
                ('CONTROLS', font40, WHITE),
                ('LEFT/RIGHT: Move ship', font30, WHITE),
                ('SPACE: Fire', font30, WHITE),
                ('P: Pause/Resume', font30, WHITE),
                ('M: Toggle Music', font30, WHITE),
                ('R: Restart (when game over)', font30, WHITE),
                ('GREEN: Health', font30, GREEN),
                ('BLUE: Speed', font30, BLUE),
                ('YELLOW: Rapid Fire', font30, YELLOW),
                ('Press B to go back', font30, WHITE)
            ]
            draw_message_box(controls, 150)
        else:
            screen.blit(pause_bg, (0, 0))
            pause_menu = [
                ('PAUSED', font40, WHITE),
                ('Press P to resume', font30, WHITE),
                ('Press C to view controls', font30, WHITE),
                ('Press M to toggle music', font30, WHITE),
                ('Press Q to quit', font30, WHITE)
            ]
            draw_message_box(pause_menu)
        
    elif countdown == 0:
        # Draw sprite groups
        spaceship_group.draw(screen)
        bullet_group.draw(screen)
        explosion_group.draw(screen)
        
        if game_over == 0:
            alien_group.draw(screen)
            alien_bullet_group.draw(screen)
        
        powerup_group.draw(screen)
        
        # Alien shooting logic
        time_now = pygame.time.get_ticks()
        if (time_now - last_alien_shot > alien_cooldown and len(alien_bullet_group) < 5 
            and len(alien_group) > 0 and game_over == 0):
            attacking_alien = random.choice(alien_group.sprites())
            alien_bullet_group.add(Alien_Bullets(attacking_alien.rect.centerx, attacking_alien.rect.bottom))
            last_alien_shot = time_now

        # Check for level completion
        if len(alien_group) == 0:
            game_over = 1

        if game_over == 0:
            game_over = spaceship.update()

            # Check for powerup collisions
            for powerup in powerup_group:
                if pygame.sprite.collide_mask(powerup, spaceship):
                    spaceship.apply_powerup(powerup.type)
                    powerup.kill()

            alien_controller.update()
            bullet_group.update()
            alien_bullet_group.update()
            powerup_group.update()
            draw_powerup_indicators()
        else:
            if game_over == -1:
                game_over_msgs = [
                    ('GAME OVER!', font40, WHITE),
                    (f'Your score: {score}', font30, WHITE),
                    ('Press R to restart', font30, WHITE)
                ]
                draw_message_box(game_over_msgs)
                save_high_score(score)
            if game_over == 1:
                level_complete_msgs = [
                    ('LEVEL COMPLETE!', font40, WHITE),
                    ('Press N for next level', font30, WHITE),
                    ('Press R to restart', font30, WHITE)
                ]
                draw_message_box(level_complete_msgs)
        
    if countdown > 0:
        countdown_msgs = [
            (f'LEVEL {level}', font40, WHITE),
            ('GET READY!', font40, WHITE),
            (str(countdown), font40, WHITE)
        ]
        draw_message_box(countdown_msgs)
        
        count_timer = pygame.time.get_ticks()
        if count_timer - last_count > 1000:
            countdown -= 1
            last_count = count_timer

    explosion_group.update()

    if countdown == 0 or paused:
        draw_score()

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p and game_over == 0:
                paused = not paused
                show_controls = False
            if event.key == pygame.K_m:
                toggle_music()
            if event.key == pygame.K_c and paused:
                show_controls = True
            if event.key == pygame.K_b and show_controls:
                show_controls = False
            if event.key == pygame.K_q and paused:
                run = False
            if event.key == pygame.K_r and (game_over != 0):
                # Reset game
                game_over, score, level, countdown = 0, 0, 1, 3
                last_count = pygame.time.get_ticks()
                alien_cooldown = 1000
                rows, cols = 5, 5
                alien_controller = AlienGroup()
                
                spaceship = Spaceship(int(SCREEN_WIDTH / 2), SCREEN_HEIGHT - 100, 3)
                spaceship_group.empty()
                spaceship_group.add(spaceship)
                
                # Clear all groups
                alien_group.empty()
                bullet_group.empty()
                alien_bullet_group.empty()
                explosion_group.empty()
                powerup_group.empty()
                create_aliens()
                
            if event.key == pygame.K_n and game_over == 1:
                # Next level
                game_over = 0
                level += 1
                countdown = 3
                last_count = pygame.time.get_ticks()
                
                # Increase difficulty
                alien_cooldown = max(300, alien_cooldown - 100)
                
                if level > 2:
                    max_alien_width = 80
                    max_possible_cols = SCREEN_WIDTH // max_alien_width
                    cols = min(10, min(5 + level // 2, max_possible_cols))
                    rows = min(8, 5 + level // 3)
                
                alien_controller = AlienGroup()
                
                # Clear relevant groups
                alien_group.empty()
                bullet_group.empty()
                alien_bullet_group.empty()
                explosion_group.empty()
                powerup_group.empty()
                create_aliens()

    pygame.display.update()

pygame.quit()