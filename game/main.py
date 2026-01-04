import pygame
import asyncio
import math
import random
from array import array

# =========================================================
# My Teacher Is an Alien (Book 1 inspired) - Web-safe build
# - Pygbag / pygame-web friendly
# - No enemies, no shooting; choice-based selections
# - Multiple sprites (little people) + alien-teacher sprite
# - Safe audio: initializes ONLY after user input
# - Always-on debug HUD + crash overlay
# =========================================================

WIDTH, HEIGHT = 1000, 650
FPS = 60

# Bright, readable palette (avoid "looks black" issues)
BG_SCHOOLYARD = (40, 120, 70)
BG_CLASSROOM  = (55, 95, 140)
BG_HALLWAY    = (140, 85, 60)
BG_PLAN       = (95, 70, 140)
BG_FINALE     = (115, 60, 115)

WHITE = (245, 245, 245)
BLACK = (10, 10, 12)
YELLOW = (245, 220, 90)
CYAN = (90, 235, 235)
GREEN = (70, 200, 110)
BLUE = (70, 140, 235)
BROWN = (200, 135, 85)
PURPLE = (160, 110, 190)
GRAY = (210, 210, 210)

WORLD = pygame.Rect(0, 0, WIDTH, HEIGHT)

# ----------------------------
# Safe procedural audio helpers
# ----------------------------

def _clamp16(n: int) -> int:
    return max(-32768, min(32767, n))

def make_tone(freq_hz=440, ms=120, volume=0.18, sample_rate=44100, wave="sine"):
    """Create a simple mono tone as pygame.mixer.Sound without external files."""
    n_samples = int(sample_rate * (ms / 1000.0))
    buf = array("h")
    amp = int(32767 * volume)
    
    for i in range(n_samples):
        t = i / sample_rate
        if wave == "square":
            v = amp if math.sin(2 * math.pi * freq_hz * t) >= 0 else -amp
        elif wave == "triangle":
            phase = (freq_hz * t) % 1.0
            tri = 2.0 * abs(2.0 * phase - 1.0) - 1.0
            v = int(amp * tri)
        else:
            v = int(amp * math.sin(2 * math.pi * freq_hz * t))
        buf.append(_clamp16(v))
    
    return pygame.mixer.Sound(buffer=buf.tobytes())

def make_room_loop(freq=220, volume=0.08):
    return make_tone(freq_hz=freq, ms=1500, volume=volume, wave="triangle")

class AudioBank:
    """Audio that initializes ONLY after a user gesture."""
    def __init__(self):
        self.ready = False
        self.sfx_select = None
        self.sfx_interact = None
        self.music = {}
        self.current = None
    
    def init_if_needed(self):
        if self.ready:
            return
        try:
            # In browsers, audio often requires user gesture.
            pygame.mixer.pre_init(44100, -16, 1, 512)
            pygame.mixer.init()
            self.sfx_select = make_tone(880, ms=70, volume=0.22, wave="square")
            self.sfx_interact = make_tone(520, ms=70, volume=0.18, wave="triangle")
            self.music = {
                "schoolyard": make_room_loop(220),
                "classroom":  make_room_loop(246),
                "hallway":    make_room_loop(196),
                "plan_room":  make_room_loop(262),
                "finale":     make_room_loop(174),
            }
            self.ready = True
        except Exception:
            # If audio fails in web build, the game still works.
            self.ready = False

def play_select(self):
    if self.ready and self.sfx_select:
        self.sfx_select.play()

    def play_interact(self):
        if self.ready and self.sfx_interact:
            self.sfx_interact.play()

def start_music(self, scene):
    if not self.ready:
        return
        if self.current:
            self.current.stop()
    snd = self.music.get(scene)
        if snd:
            self.current = snd
            snd.play(loops=-1)

AUDIO = AudioBank()

# ----------------------------
# Text helpers
# ----------------------------

def draw_text(surf, text, x, y, color, font):
    surf.blit(font.render(text, True, color), (x, y))

def wrap_lines(text, max_width_px, font):
    words = text.split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if font.size(test)[0] <= max_width_px:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines

def clamp_rect(r):
    r.clamp_ip(WORLD)

# ----------------------------
# Sprite drawing
# ----------------------------

def draw_little_person(screen, x, y, body_color, scale=1.0):
    head_r = int(8 * scale)
    body_w = int(14 * scale)
    body_h = int(18 * scale)
    
    # head
    pygame.draw.circle(screen, (240, 220, 200), (x, y - 18), head_r)
    # body
    pygame.draw.rect(screen, body_color, (x - body_w // 2, y - 10, body_w, body_h), border_radius=4)
    # legs
    pygame.draw.line(screen, BLACK, (x - 5, y + 8), (x - 8, y + 16), 2)
    pygame.draw.line(screen, BLACK, (x + 5, y + 8), (x + 8, y + 16), 2)

def draw_alien_teacher(screen, x, y, scale=1.0, with_pointer=True):
    # Teacher-alien: suit + tie + antenna + pointer
    head_w = int(34 * scale)
    head_h = int(46 * scale)
    
    # head
    pygame.draw.ellipse(screen, (120, 230, 150), (x - head_w//2, y - 62, head_w, head_h))
    # eyes
    pygame.draw.ellipse(screen, BLACK, (x - 14, y - 52, 12, 20))
    pygame.draw.ellipse(screen, BLACK, (x + 2,  y - 52, 12, 20))
    pygame.draw.circle(screen, CYAN, (x - 9, y - 42), 2)
    pygame.draw.circle(screen, CYAN, (x + 9, y - 42), 2)
    
    # antenna
    pygame.draw.line(screen, (120, 230, 150), (x - 6, y - 62), (x - 18, y - 82), 3)
    pygame.draw.circle(screen, CYAN, (x - 18, y - 82), 5)
    pygame.draw.line(screen, (120, 230, 150), (x + 6, y - 62), (x + 18, y - 82), 3)
    pygame.draw.circle(screen, CYAN, (x + 18, y - 82), 5)
    
    # suit
    suit_w = int(40 * scale)
    suit_h = int(44 * scale)
    pygame.draw.rect(screen, (55, 55, 70), (x - suit_w//2, y - 18, suit_w, suit_h), border_radius=8)
    
    # collar + tie
    pygame.draw.polygon(screen, (220, 220, 220), [(x - 10, y - 18), (x, y - 6), (x + 10, y - 18)])
    pygame.draw.polygon(screen, (170, 90, 190), [(x, y - 6), (x - 5, y + 8), (x + 5, y + 8)])
    
    # pointer
    if with_pointer:
        pygame.draw.line(screen, (190, 165, 120), (x + 18, y + 6), (x + 46, y - 8), 3)
        pygame.draw.circle(screen, (190, 165, 120), (x + 46, y - 8), 3)

# ----------------------------
# Game objects
# ----------------------------

class Actor:
    def __init__(self, name, kind, x, y, color, speed=3, wander=False):
        self.name = name
        self.kind = kind  # player / npc / prop
        self.color = color
        self.speed = speed
        self.wander = wander
        self.rect = pygame.Rect(0, 0, 40, 40)
        self.rect.center = (x, y)
        self.vx = 0
        self.vy = 0
        self.timer = random.randint(30, 120)
    
    def update(self):
        if self.kind == "npc" and self.wander:
            self.timer -= 1
            if self.timer <= 0:
                self.timer = random.randint(40, 140)
                self.vx = random.choice([-1, 0, 1]) * 2
                self.vy = random.choice([-1, 0, 1]) * 2
            self.rect.x += self.vx
            self.rect.y += self.vy
            clamp_rect(self.rect)

class DialogChoice:
    def __init__(self, prompt, choices, on_choose):
        self.prompt = prompt
        self.choices = choices
        self.on_choose = on_choose

class State:
    def __init__(self):
        self.mode = "title"         # title / play
        self.scene = "schoolyard"   # schoolyard/classroom/hallway/plan_room/finale
        self.dialog_queue = []
        self.dialog = None
        self.toast = ""
        self.toast_timer = 0
        self.objective = "Press ENTER to start."
        
        self.flags = {
            "met_susan": False,
            "met_peter": False,
            "met_duncan": False,
            "met_teacher": False,
            "suspicious": 0,
            "found_clue": False,
            "learned_schedule": False,
            "got_help": False,
            "made_plan": False,
            "ready_finale": False,
}
    
    def push(self, d):
        self.dialog_queue.append(d)
    
    def next(self):
        self.dialog = self.dialog_queue.pop(0) if self.dialog_queue else None
    
    def toast_msg(self, msg, frames=180):
        self.toast = msg
        self.toast_timer = frames

S = State()

# ----------------------------
# Scene building
# ----------------------------

def build_scene(scene):
    actors = []
    props = []
    
    player = Actor("You", "player", 120, HEIGHT // 2, BLUE, speed=4)
    actors.append(player)
    
    def npc(name, x, y, color, wander=True):
        a = Actor(name, "npc", x, y, color, speed=2, wander=wander)
        actors.append(a)
        props.append(a)
        return a
    
    def prop(name, x, y, color=YELLOW):
        a = Actor(name, "prop", x, y, color, speed=0, wander=False)
        actors.append(a)
        props.append(a)
        return a
    
    if scene == "schoolyard":
        npc("Susan Simmons", 320, 420, GREEN, wander=True)
        npc("Peter Thompson", 480, 260, (90, 210, 120), wander=True)
        npc("Duncan Dougal", 720, 460, BROWN, wander=True)
        prop("School Door", 920, 120, YELLOW)
    
    elif scene == "classroom":
        npc("Susan Simmons", 280, 440, GREEN, wander=True)
        npc("Peter Thompson", 410, 360, (90, 210, 120), wander=True)
        npc("Duncan Dougal", 640, 470, BROWN, wander=True)
        # teacher
        t = Actor("Mr. Smith (Broxholm)", "npc", 760, 200, PURPLE, speed=0, wander=False)
        actors.append(t)
        props.append(t)
        prop("Teacher Desk", 520, 520, YELLOW)
        prop("Hallway Door", 920, 120, YELLOW)
    
    elif scene == "hallway":
        npc("Susan Simmons", 240, 520, GREEN, wander=False)
        prop("Notice Board", 520, 260, YELLOW)
        prop("Storage Door", 900, 520, YELLOW)
        prop("Back to Class", 80, 120, YELLOW)
    
    elif scene == "plan_room":
        npc("Susan Simmons", 240, 520, GREEN, wander=False)
        npc("Peter Thompson", 320, 560, (90, 210, 120), wander=False)
        npc("Duncan Dougal", 410, 520, BROWN, wander=False)
        prop("Idea Board", 560, 260, YELLOW)
        prop("Auditorium Door", 920, 120, YELLOW)
        prop("Back Hall", 80, 120, YELLOW)
    
    elif scene == "finale":
        npc("Susan Simmons", 220, 560, GREEN, wander=False)
        npc("Peter Thompson", 300, 590, (90, 210, 120), wander=False)
        npc("Duncan Dougal", 390, 560, BROWN, wander=False)
        t = Actor("Mr. Smith (Broxholm)", "npc", 760, 230, PURPLE, speed=0, wander=False)
        actors.append(t)
        props.append(t)
        prop("Stage Control", 720, 520, YELLOW)
        prop("Big Reveal Spot", 920, 120, YELLOW)
    
    return player, actors, props

player, actors, props = build_scene(S.scene)

def set_scene(scene):
    global player, actors, props
    S.scene = scene
    player, actors, props = build_scene(scene)
    S.toast_msg(f"Entered: {scene.upper()}", 120)
    AUDIO.start_music(scene)

def nearest_interactable():
    best = None
    best_d = 10**9
    px, py = player.rect.center
    for o in props:
        ox, oy = o.rect.center
        d = math.hypot(px - ox, py - oy)
        if d < best_d:
            best_d, best = d, o
    return best, best_d

# ----------------------------
# Story logic
# ----------------------------

def bump_suspicion():
    S.flags["suspicious"] = min(4, S.flags["suspicious"] + 1)

def begin_game():
    S.mode = "play"
    S.objective = "Talk to Susan, Peter, and Duncan. Then enter the School Door."
    set_scene("schoolyard")
    S.push(DialogChoice(
                        "It’s a regular school morning… except something about your new teacher feels wrong.\n"
                        "Not ‘strict’ wrong. More like ‘not from here’ wrong.",
                        ["Okay…", "That’s impossible.", "Let’s pay attention."],
                        lambda i: None
                        ))
    S.next()

def restart_game():
    global S
    S = State()
    begin_game()

def ending(kind):
    if kind == "REVEAL":
        msg = ("You force the moment into the open. Under bright lights, the ‘normal’ act slips—"
               "and something alien flashes through.\n\nTHE END")
    elif kind == "SAVE":
        msg = ("You choose your friends first. You don’t get a perfect ‘gotcha,’ but you stay together.\n\nTHE END")
    else:
        msg = ("You confront him directly. It’s terrifying—but honest.\n\nTHE END")
    
    S.push(DialogChoice(msg + "\n\nPress 1 to restart, or ESC to quit.",
                        ["Restart", "Restart", "Restart"],
                        lambda i: restart_game()))
    S.next()

def talk_to(name):
    # SCHOOLYARD
    if S.scene == "schoolyard":
        if name == "Susan Simmons":
            def after(i):
                S.flags["met_susan"] = True
                if i in (0, 1):
                    bump_suspicion()
                S.toast_msg("Susan: “We need proof… and we need to be careful.”", 200)
            S.push(DialogChoice(
                                "Susan looks like she’s already solving something. “You feel it too, right?”",
                                ["Ask what she noticed", "Agree and watch together", "Say she’s overreacting"],
                                after
                                ))
            S.next()
    
        elif name == "Peter Thompson":
            def after(i):
                S.flags["met_peter"] = True
                if i == 1:
                    bump_suspicion()
                S.toast_msg("Peter: “This is either nothing… or the biggest thing ever.”", 220)
            S.push(DialogChoice(
                                "Peter grins nervously. “This might be the most interesting day ever.”",
                                ["Tell him to stay calm", "Ask what he saw", "Ask him to help investigate"],
                                after
                                ))
            S.next()
        
        elif name == "Duncan Dougal":
            def after(i):
                S.flags["met_duncan"] = True
                if i == 1:
                    S.flags["got_help"] = True
                if i == 2:
                    bump_suspicion()
                S.toast_msg("Duncan: “I’m not scared… I just hate surprises.”", 220)
            S.push(DialogChoice(
                                "Duncan sizes you up. “What are YOU staring at?”",
                                ["Tell him nothing", "Ask him to help (carefully)", "Ask if he noticed the teacher"],
                                after
                                ))
            S.next()
        
        elif name == "School Door":
            if S.flags["met_susan"] and S.flags["met_peter"] and S.flags["met_duncan"]:
                S.push(DialogChoice(
                                    "The school door swings open. The air inside smells like pencils… and secrets.",
                                    ["Go in", "Go in", "Go in"],
                                    lambda i: (set_scene("classroom"),
                                               setattr(S, "objective", "Talk to Mr. Smith (Broxholm) and check the Teacher Desk."))
                                    ))
                S.next()
            else:
                S.toast_msg("Talk to Susan, Peter, and Duncan first.", 200)

# CLASSROOM
elif S.scene == "classroom":
    if name == "Mr. Smith (Broxholm)":
        def after(i):
            S.flags["met_teacher"] = True
            if i in (0, 2):
                bump_suspicion()
                S.toast_msg("Mr. Smith: “Observe carefully… and learn quickly.”", 220)
                S.objective = "Find a clue (Teacher Desk) and go to the hallway."
            S.push(DialogChoice(
                                "Mr. Smith writes one word on the board: “OBSERVE.” Then he turns too smoothly.",
                                ["Ask if he’s ‘normal’", "Act like everything’s fine", "Stay quiet and watch"],
                                after
                                ))
                    S.next()
                
                elif name == "Teacher Desk":
                    if not S.flags["found_clue"]:
                def after(i):
                    if i == 0:
                        S.flags["found_clue"] = True
                        bump_suspicion()
                        S.toast_msg("You find a stamped slip with star-like marks. CLUE found.", 240)
                    elif i == 1:
                        S.flags["learned_schedule"] = True
                        bump_suspicion()
                        S.toast_msg("You notice a weird ‘selection list’ idea in the papers.", 240)
                    else:
                        S.toast_msg("You close the desk quietly.", 180)
                    S.objective = "Head to the hallway."
                S.push(DialogChoice(
                                    "The teacher’s desk drawer sticks for a second… then opens.",
                                    ["Search carefully for anything odd", "Listen first, then peek", "Close it—too risky"],
                                    after
                                    ))
                        S.next()
                            else:
                                S.toast_msg("You already searched the desk.", 160)
                            
                            elif name == "Hallway Door":
                                S.push(DialogChoice(
                                                    "The hallway feels louder than it should be. Like the building is whispering.",
                                                    ["Go out", "Go out", "Go out"],
                                                    lambda i: (set_scene("hallway"),
                                                               setattr(S, "objective", "Check the Notice Board and decide your next move."))
                                                    ))
                                S.next()

# HALLWAY
elif S.scene == "hallway":
    if name == "Notice Board":
        def after(i):
            if i == 0:
                S.flags["learned_schedule"] = True
                bump_suspicion()
                S.toast_msg("A posted schedule has odd symbols. Like it’s coded.", 240)
                elif i == 1:
                    S.flags["got_help"] = True
                    S.toast_msg("Susan nods. “Okay. We do this smart.”", 220)
                else:
                    S.toast_msg("You step away before anyone notices you staring.", 180)
                
                if S.flags["found_clue"] and S.flags["learned_schedule"]:
                    S.objective = "Go to the Storage Door to regroup."
                else:
                    S.objective = "You need more: find a clue AND study the symbols."
        S.push(DialogChoice(
                            "The notice board is covered in papers. One page has markings that don’t look like school stuff.",
                            ["Study the weird page", "Wave Susan over", "Back away"],
                            after
                            ))
            S.next()
                
                            elif name == "Storage Door":
                                if S.flags["found_clue"] and S.flags["learned_schedule"]:
                                    S.push(DialogChoice(
                                                        "The storage door is usually locked… but today it opens. Like it was waiting.",
                                                        ["Go in", "Go in", "Go in"],
                                                        lambda i: (set_scene("plan_room"),
                                                                   setattr(S, "objective", "Make a plan together (Idea Board)."))
                                                        ))
                                    S.next()
                                        else:
                                            S.toast_msg("Not ready. You need more evidence first.", 220)
                                                
                                                elif name == "Back to Class":
                                                    S.push(DialogChoice(
                                                                        "Go back to class?",
                                                                        ["Yes", "Yes", "Yes"],
                                                                        lambda i: (set_scene("classroom"),
                                                                                   setattr(S, "objective", "Find a clue (Teacher Desk) and return."))
                                                                        ))
                                                    S.next()

# PLAN ROOM
elif S.scene == "plan_room":
    if name == "Idea Board":
        def after(i):
            S.flags["made_plan"] = True
            S.flags["ready_finale"] = True
            bump_suspicion()
            S.objective = "Go to the Auditorium Door."
                S.toast_msg("Plan locked in. Time for the auditorium.", 220)
            S.push(DialogChoice(
                                "You huddle up. Susan wants proof. Peter wants bold action. Duncan wants it over with.",
                                ["Controlled distraction", "Public confrontation", "Bait-and-reveal"],
                                after
                                ))
                    S.next()
                
                elif name == "Auditorium Door":
                    if S.flags["ready_finale"]:
                S.push(DialogChoice(
                                    "The auditorium is empty… but it feels like a stage waiting for one moment.",
                                    ["Enter", "Enter", "Enter"],
                                    lambda i: (set_scene("finale"),
                                               setattr(S, "objective", "Use Stage Control, then go to Big Reveal Spot."))
                                    ))
        S.next()
            else:
                S.toast_msg("Make a plan first (Idea Board).", 200)

elif name == "Back Hall":
    S.push(DialogChoice(
                        "Go back to the hallway?",
                        ["Yes", "Yes", "Yes"],
                        lambda i: (set_scene("hallway"),
                                   setattr(S, "objective", "Finish gathering info, then regroup."))
                        ))
                        S.next()
                        
                        # FINALE
                        elif S.scene == "finale":
                            if name == "Stage Control":
                                def after(i):
                                    bump_suspicion()
                                    S.toast_msg("Lights shift. The ‘normal’ act feels thinner.", 240)
                                        S.push(DialogChoice(
                                                            "A stage control panel. One switch labeled: “AUDIO / LIGHTS.”",
                                                            ["Flip it now", "Wait for him to approach", "Signal your friends first"],
                                                            after
                                                            ))
                                        S.next()
                                            
                                            elif name == "Big Reveal Spot":
                                                # FIX: allow reveal if suspicion is high AND (made_plan OR ready_finale)
                                                if S.flags["suspicious"] >= 3 and (S.flags["made_plan"] or S.flags["ready_finale"]):
                                                    def after(i):
                                                        if i == 0:
                                                            ending("REVEAL")
                                                                elif i == 1:
                                                                    ending("SAVE")
                                                                        else:
                                                                            ending("BOLD")
                                                                                S.push(DialogChoice(
                                                                                                    "This is it. If you’re right, the truth comes out. If you’re wrong… awkward.",
                                                                                                    ["Reveal him publicly", "Protect your friends first", "Confront him directly"],
                                                                                                    after
                                                                                                    ))
                                                                                S.next()
                                                                                    else:
                                                                                        S.toast_msg(f"Not ready: suspicion={S.flags['suspicious']} made_plan={S.flags['made_plan']} ready_finale={S.flags['ready_finale']}", 260)
                                                                                            
                                                                                            elif name == "Mr. Smith (Broxholm)":
                                                                                                def after(i):
                                                                                                    bump_suspicion()
                                                                                                    S.toast_msg("Mr. Smith: “Observation is… instructive.”", 220)
                                                                                                        S.push(DialogChoice(
                                                                                                                            "He stands too calmly for an empty auditorium.",
                                                                                                                            ["Ask what he is", "Ask what he wants", "Say nothing and watch"],
                                                                                                                            after
                                                                                                                            ))
                                                                                                        S.next()

# ----------------------------
# Input + movement
# ----------------------------

def handle_player_movement(keys):
    if S.dialog:
        return
    dx = dy = 0
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        dx -= player.speed
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        dx += player.speed
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        dy -= player.speed
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        dy += player.speed
    player.rect.x += dx
    player.rect.y += dy
    clamp_rect(player.rect)

def try_choice(key):
    if not S.dialog:
        return
    idx = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}.get(key)
    if idx is None or idx >= len(S.dialog.choices):
        return
    AUDIO.play_select()
    S.dialog.on_choose(idx)
    S.next()

def interact():
    obj, d = nearest_interactable()
    if obj and d <= 85:
        AUDIO.play_interact()
        talk_to(obj.name)
    else:
        S.toast_msg("Nothing to interact with nearby.", 120)

# ----------------------------
# Rendering
# ----------------------------

def scene_bg(scene):
    if scene == "schoolyard":
        return BG_SCHOOLYARD
    if scene == "classroom":
        return BG_CLASSROOM
    if scene == "hallway":
        return BG_HALLWAY
    if scene == "plan_room":
        return BG_PLAN
    return BG_FINALE

def draw_title(screen, FONT, BIG, HUGE):
    screen.fill((20, 24, 30))
    cx, cy = WIDTH // 2, HEIGHT // 2 + 50
    draw_alien_teacher(screen, cx, cy, scale=2.2, with_pointer=False)
    
    title = "MY TEACHER IS AN ALIEN"
    draw_text(screen, title, cx - HUGE.size(title)[0] // 2, 50, WHITE, HUGE)
    
    byline = "by Cody"
    draw_text(screen, byline, cx - BIG.size(byline)[0] // 2, 130, YELLOW, BIG)
    
    draw_text(screen, "ENTER = Start   |   ESC = Quit", cx - FONT.size("ENTER = Start   |   ESC = Quit")[0] // 2,
              HEIGHT - 105, GRAY, FONT)
              draw_text(screen, "Move: WASD/Arrows  •  Interact: E  •  Choose: 1/2/3",
                        cx - FONT.size("Move: WASD/Arrows  •  Interact: E  •  Choose: 1/2/3")[0] // 2,
                        HEIGHT - 75, GRAY, FONT)

def draw_actors(screen):
    for a in actors:
        x, y = a.rect.center
        if a.name.startswith("Mr. Smith"):
            draw_alien_teacher(screen, x, y, scale=1.0, with_pointer=True)
        elif a.kind in ("player", "npc"):
            draw_little_person(screen, x, y, a.color, scale=1.0)
        else:
            # prop
            pygame.draw.circle(screen, a.color, (x, y), 18)
            pygame.draw.circle(screen, BLACK, (x, y), 18, 2)

def draw_ui(screen, FONT, BIG):
    # top bar
    pygame.draw.rect(screen, (18, 18, 20), (0, 0, WIDTH, 82))
    pygame.draw.rect(screen, (255, 255, 255), (0, 0, WIDTH, 82), 2)
    
    draw_text(screen, f"Scene: {S.scene.upper()}", 14, 10, WHITE, BIG)
    draw_text(screen, f"Objective: {S.objective}", 14, 52, GRAY, FONT)
    
    draw_text(screen, f"Suspicion: {S.flags['suspicious']}/4", WIDTH - 210, 52, YELLOW, FONT)
    
    # toast
    if S.toast_timer > 0:
        pygame.draw.rect(screen, (0, 0, 0), (12, 92, WIDTH - 24, 34), border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), (12, 92, WIDTH - 24, 34), 2, border_radius=8)
        draw_text(screen, S.toast, 22, 100, WHITE, FONT)
    
    # interact hint
    if not S.dialog:
        obj, d = nearest_interactable()
        if obj and d <= 85:
            pygame.draw.rect(screen, (0, 0, 0), (12, HEIGHT - 52, WIDTH - 24, 40), border_radius=10)
            pygame.draw.rect(screen, (255, 255, 255), (12, HEIGHT - 52, WIDTH - 24, 40), 2, border_radius=10)
            draw_text(screen, f"Press E to interact with: {obj.name}", 22, HEIGHT - 42, WHITE, FONT)

def draw_dialog(screen, FONT):
    if not S.dialog:
        return
    box = pygame.Rect(40, HEIGHT - 250, WIDTH - 80, 210)
    pygame.draw.rect(screen, (0, 0, 0), box, border_radius=14)
    pygame.draw.rect(screen, (255, 255, 255), box, 2, border_radius=14)

lines = wrap_lines(S.dialog.prompt, box.width - 40, FONT)
y = box.y + 16
    for line in lines[:7]:
        draw_text(screen, line, box.x + 20, y, WHITE, FONT)
        y += 24

y += 8
    for i, ch in enumerate(S.dialog.choices):
        draw_text(screen, f"{i+1}) {ch}", box.x + 20, y, YELLOW, FONT)
        y += 26

# ----------------------------
# Main loop (with crash overlay)
# ----------------------------

async def main():
    global player, actors, props
    
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT))
    screen = pygame.display.get_surface()
    pygame.display.set_caption("My Teacher Is an Alien - by Cody")
    
    pygame.font.init()
    FONT = pygame.font.Font(None, 24)
    BIG  = pygame.font.Font(None, 40)
    HUGE = pygame.font.Font(None, 64)
    
    clock = pygame.time.Clock()
    
    # NOTE: audio is NOT initialized here. Only after user presses a key.
    running = True
    
    while running:
        try:
            clock.tick(FPS)
            keys = pygame.key.get_pressed()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                
                    # First user gesture: safe time to init audio
                    AUDIO.init_if_needed()
                    AUDIO.start_music(S.scene)
                    
                    if S.mode == "title":
                        if event.key == pygame.K_RETURN:
                            begin_game()
                        continue
    
        if event.key == pygame.K_e and not S.dialog:
            interact()
                
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    try_choice(event.key)
        
            # update
            if S.toast_timer > 0:
                S.toast_timer -= 1
                if S.toast_timer <= 0:
                    S.toast = ""

if S.mode == "title":
    draw_title(screen, FONT, BIG, HUGE)
    # always-on debug text so we know loop is alive
    draw_text(screen, "DEBUG: title loop running", 14, HEIGHT - 28, (200, 255, 200), FONT)
        pygame.display.flip()
        await asyncio.sleep(0)
        continue
            
            handle_player_movement(keys)
            for a in actors:
                a.update()
        
            # draw
            screen.fill(scene_bg(S.scene))
            draw_actors(screen)
            draw_ui(screen, FONT, BIG)
            draw_dialog(screen, FONT)
            
            # always-on debug HUD (prevents “it’s black” ambiguity)
            dbg = f"DEBUG mode={S.mode} scene={S.scene} dialog={'Y' if S.dialog else 'N'} audio={'Y' if AUDIO.ready else 'N'}"
            draw_text(screen, dbg, 14, HEIGHT - 28, (255, 255, 255), FONT)
            
            pygame.display.flip()
        await asyncio.sleep(0)
        
        except Exception as e:
            # Crash overlay
            screen.fill((20, 0, 0))
            pygame.draw.rect(screen, (0, 0, 0), (30, 30, WIDTH - 60, HEIGHT - 60), border_radius=12)
            pygame.draw.rect(screen, (255, 255, 255), (30, 30, WIDTH - 60, HEIGHT - 60), 2, border_radius=12)
            draw_text(screen, "CRASH", 60, 60, (255, 180, 180), HUGE)
            msg = f"{type(e).__name__}: {e}"
            for i, line in enumerate(wrap_lines(msg, WIDTH - 140, FONT)[:12]):
                draw_text(screen, line, 60, 140 + i * 28, WHITE, FONT)
            draw_text(screen, "Open DevTools Console (F12) for details.", 60, HEIGHT - 90, GRAY, FONT)
            pygame.display.flip()
            await asyncio.sleep(0)

pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())

