import pygame
import random
import math
import asyncio
from array import array

# ---------------------------------------------------------
# My Teacher Is an Alien (Final Fixed Version)
# ---------------------------------------------------------

WIDTH, HEIGHT = 1000, 650
FPS = 60

FONT = None
BIG = None
HUGE = None

WHITE = (245, 245, 245)
BLACK = (10, 10, 12)
DARK = (35, 35, 40)

BLUE = (70, 130, 180)     # player
GREEN = (60, 170, 90)     # kids
BROWN = (180, 120, 80)    # duncan
YELLOW = (230, 210, 80)   # props
PURPLE = (140, 90, 160)   # teacher accent
CYAN = (80, 220, 220)     # alien glow
SUIT = (60, 60, 70)       # teacher suit
PAPER = (210, 210, 210)

WORLD = pygame.Rect(0, 0, WIDTH, HEIGHT)

# ---------------- Audio (Procedural Music) ----------------

def _clamp16(n: int) -> int:
    return max(-32768, min(32767, n))

def generate_wave_buffer(freq_hz, ms, volume=0.25, sample_rate=44100, wave="sine"):
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
    return buf

def make_tone(freq_hz=440, ms=150, volume=0.25, wave="sine"):
    buf = generate_wave_buffer(freq_hz, ms, volume, wave=wave)
    return pygame.mixer.Sound(buffer=buf.tobytes())

def make_arpeggio(notes, ms_per_note=300, volume=0.15, wave="triangle"):
    full_buf = array("h")
    for freq in notes:
        full_buf.extend(generate_wave_buffer(freq, ms_per_note, volume, wave=wave))
        full_buf.extend(generate_wave_buffer(0, 20, 0)) 
    return pygame.mixer.Sound(buffer=full_buf.tobytes())

SFX_SELECT = None
SFX_INTERACT = None
ROOM_MUSIC = {}
_current_music = None

def start_room_music(scene_name: str):
    global _current_music
    if not pygame.mixer.get_init():
        return

    if _current_music is not None:
        _current_music.stop()

    snd = ROOM_MUSIC.get(scene_name)
    if snd:
        _current_music = snd
        snd.play(loops=-1)

# ---------------- Text helpers ----------------

def draw_text(surf, text, x, y, color=WHITE, font=None):
    img = font.render(text, True, color)
    surf.blit(img, (x, y))

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

# ---------------- Sprites ----------------

class Actor(pygame.sprite.Sprite):
    def __init__(self, name, kind, x, y, radius=16, color=BLUE, speed=3, wander=False):
        super().__init__()
        self.name = name
        self.kind = kind  # player / npc / prop
        self.radius = radius
        self.color = color
        self.speed = speed
        self.wander = wander
        self.vx = 0
        self.vy = 0
        self.timer = random.randint(30, 120)

        size = radius * 2 + 60
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))

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

class GameState:
    def __init__(self):
        self.mode = "title"  # title / play
        self.scene = "schoolyard"
        self.dialog_queue = []
        self.active_dialog = None
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

    def set_toast(self, msg, frames=180):
        self.toast = msg
        self.toast_timer = frames

    def push_dialog(self, d):
        self.dialog_queue.append(d)

    def next_dialog(self):
        if self.dialog_queue:
            self.active_dialog = self.dialog_queue.pop(0)
        else:
            self.active_dialog = None

state = GameState()

# ---------------- Drawing ----------------

def draw_little_person(screen, x, y, body_color, scale=1.0):
    head_r = int(8 * scale)
    body_w = int(14 * scale)
    body_h = int(18 * scale)
    pygame.draw.circle(screen, (235, 220, 200), (x, y - 18), head_r)
    pygame.draw.rect(screen, body_color, (x - body_w // 2, y - 10, body_w, body_h), border_radius=4)
    pygame.draw.line(screen, BLACK, (x - 5, y + 8), (x - 8, y + 16), 2)
    pygame.draw.line(screen, BLACK, (x + 5, y + 8), (x + 8, y + 16), 2)

def draw_alien_teacher(screen, x, y, scale=1.0, with_pointer=True):
    head_w = int(34 * scale)
    head_h = int(46 * scale)
    pygame.draw.ellipse(screen, (120, 220, 140), (x - head_w//2, y - 62, head_w, head_h))
    pygame.draw.ellipse(screen, BLACK, (x - 14, y - 52, 12, 20))
    pygame.draw.ellipse(screen, BLACK, (x + 2,  y - 52, 12, 20))
    pygame.draw.circle(screen, CYAN, (x - 9, y - 42), 2)
    pygame.draw.circle(screen, CYAN, (x + 9, y - 42), 2)
    pygame.draw.line(screen, (120, 220, 140), (x - 6, y - 62), (x - 18, y - 82), 3)
    pygame.draw.circle(screen, CYAN, (x - 18, y - 82), 5)
    pygame.draw.line(screen, (120, 220, 140), (x + 6, y - 62), (x + 18, y - 82), 3)
    pygame.draw.circle(screen, CYAN, (x + 18, y - 82), 5)
    suit_w = int(40 * scale)
    suit_h = int(44 * scale)
    pygame.draw.rect(screen, SUIT, (x - suit_w//2, y - 18, suit_w, suit_h), border_radius=8)
    pygame.draw.polygon(screen, PAPER, [(x - 10, y - 18), (x, y - 6), (x + 10, y - 18)])
    pygame.draw.polygon(screen, PURPLE, [(x, y - 6), (x - 5, y + 8), (x + 5, y + 8)])
    pygame.draw.rect(screen, PAPER, (x - 16, y - 4, 14, 8), border_radius=2)
    pygame.draw.line(screen, BLACK, (x - 15, y), (x - 4, y), 1)
    if with_pointer:
        pygame.draw.line(screen, (180, 160, 120), (x + 18, y + 6), (x + 46, y - 8), 3)
        pygame.draw.circle(screen, (180, 160, 120), (x + 46, y - 8), 3)

def draw_prop(screen, x, y, r, color):
    pygame.draw.circle(screen, color, (x, y), r)

def draw_actor(screen, a: Actor):
    x, y = a.rect.center
    r = a.radius
    if a.name == "Mr. Smith":
        draw_alien_teacher(screen, x, y, scale=1.0, with_pointer=True)
    elif a.kind in ("player", "npc"):
        body_color = a.color
        draw_little_person(screen, x, y, body_color, scale=1.0)
        pygame.draw.circle(screen, (0, 0, 0), (x, y - 28), 2)
    else:
        draw_prop(screen, x, y, r, a.color)

# ---------------- UI ----------------

def draw_title_screen(screen):
    screen.fill((15, 18, 22))
    cx, cy = WIDTH // 2, HEIGHT // 2 + 40
    draw_alien_teacher(screen, cx, cy, scale=2.1, with_pointer=False)
    title = "MY TEACHER IS AN ALIEN"
    draw_text(screen, title, cx - HUGE.size(title)[0] // 2, 40, WHITE, HUGE)
    byline = "by Cody"
    draw_text(screen, byline, cx - BIG.size(byline)[0] // 2, 115, (230, 210, 120), BIG)
    sub = "Choice-based mystery adventure"
    draw_text(screen, sub, cx - FONT.size(sub)[0] // 2, 160, (220, 220, 220), FONT)
    draw_text(screen, "ENTER = Start    |    ESC = Quit",
              cx - FONT.size("ENTER = Start    |    ESC = Quit")[0] // 2, HEIGHT - 120,
              (230, 210, 120), FONT)
    draw_text(screen, "Move: WASD/Arrows  •  Interact: E  •  Choose: 1/2/3",
              cx - FONT.size("Move: WASD/Arrows  •  Interact: E  •  Choose: 1/2/3")[0] // 2,
              HEIGHT - 90, (200, 200, 200), FONT)

def draw_dialog(screen):
    if not state.active_dialog:
        return
    box_w = WIDTH - 80
    box_h = 220
    box_x = 40
    box_y = HEIGHT - box_h - 30
    pygame.draw.rect(screen, (10, 10, 12), (box_x, box_y, box_w, box_h), border_radius=14)
    pygame.draw.rect(screen, (220, 220, 220), (box_x, box_y, box_w, box_h), width=2, border_radius=14)
    lines = wrap_lines(state.active_dialog.prompt, box_w - 40, FONT)
    y = box_y + 18
    for line in lines[:7]:
        draw_text(screen, line, box_x + 20, y, WHITE, FONT)
        y += 24
    y += 6
    for i, ch in enumerate(state.active_dialog.choices):
        draw_text(screen, f"{i+1}) {ch}", box_x + 20, y, (230, 210, 120), FONT)
        y += 26
    draw_text(screen, "Press 1/2/3 to choose", box_x + box_w - 240, box_y + box_h - 30, (200, 200, 200), FONT)

def draw_ui(screen, player, props):
    pygame.draw.rect(screen, DARK, (0, 0, WIDTH, 70))
    draw_text(screen, f"Scene: {state.scene.upper()}", 14, 10, WHITE, BIG)
    draw_text(screen, f"Objective: {state.objective}", 14, 42, (220, 220, 220), FONT)
    s = state.flags["suspicious"]
    draw_text(screen, f"Suspicion: {s}/4", WIDTH - 180, 24, (230, 210, 120), FONT)
    if state.toast_timer > 0:
        pygame.draw.rect(screen, BLACK, (12, 78, WIDTH - 24, 32), border_radius=8)
        draw_text(screen, state.toast, 24, 84, (240, 240, 240), FONT)
    if not state.active_dialog:
        nearest, d = nearest_interactable(player, props)
        if nearest and d <= 100:
            pygame.draw.rect(screen, BLACK, (12, HEIGHT - 52, WIDTH - 24, 40), border_radius=10)
            draw_text(screen, f"Press E to interact with: {nearest.name}", 24, HEIGHT - 42, (240, 240, 240), FONT)

def update_toast():
    if state.toast_timer > 0:
        state.toast_timer -= 1
        if state.toast_timer <= 0:
            state.toast = ""

# ---------------- Scenes ----------------

def build_scene(scene_name):
    all_sprites = pygame.sprite.Group()
    props = []
    player = Actor("You", "player", 120, HEIGHT // 2, radius=16, color=BLUE, speed=4)
    all_sprites.add(player)

    def npc(name, x, y, color=GREEN, wander=False):
        a = Actor(name, "npc", x, y, radius=16, color=color, speed=2, wander=wander)
        all_sprites.add(a)
        props.append(a)
        return a

    def prop(name, x, y, radius=26, color=YELLOW):
        a = Actor(name, "prop", x, y, radius=radius, color=color, speed=0, wander=False)
        all_sprites.add(a)
        props.append(a)
        return a

    if scene_name == "schoolyard":
        npc("Susan Simmons", 330, 420, color=GREEN, wander=True)
        npc("Peter Thompson", 470, 260, color=(90, 200, 120), wander=True)
        npc("Duncan Dougal", 720, 460, color=BROWN, wander=True)
        prop("School Door", 920, 120, radius=34)

    elif scene_name == "classroom":
        npc("Susan Simmons", 280, 440, color=GREEN, wander=True)
        npc("Peter Thompson", 410, 360, color=(90, 200, 120), wander=True)
        npc("Duncan Dougal", 640, 470, color=BROWN, wander=True)
        teacher = Actor("Mr. Smith", "npc", 760, 200, radius=20, color=PURPLE, speed=0)
        all_sprites.add(teacher)
        props.append(teacher)
        prop("Teacher Desk", 520, 520, radius=26)
        prop("Hallway Door", 920, 120, radius=34)

    elif scene_name == "hallway":
        npc("Susan Simmons", 240, 520, color=GREEN, wander=False)
        prop("Notice Board", 520, 260, radius=26)
        prop("Storage Door", 900, 520, radius=30)
        prop("Back to Class", 80, 120, radius=28)

    elif scene_name == "plan_room":
        npc("Susan Simmons", 240, 520, color=GREEN, wander=False)
        npc("Peter Thompson", 320, 560, color=(90, 200, 120), wander=False)
        npc("Duncan Dougal", 410, 520, color=BROWN, wander=False)
        prop("Idea Board", 560, 260, radius=30)
        prop("Auditorium Door", 920, 120, radius=34)
        prop("Back Hall", 80, 120, radius=28)

    elif scene_name == "finale":
        npc("Susan Simmons", 220, 560, color=GREEN, wander=False)
        npc("Peter Thompson", 300, 590, color=(90, 200, 120), wander=False)
        npc("Duncan Dougal", 390, 560, color=BROWN, wander=False)
        teacher = Actor("Mr. Smith", "npc", 760, 230, radius=20, color=PURPLE, speed=0)
        all_sprites.add(teacher)
        props.append(teacher)
        prop("Stage Control", 720, 520, radius=28)
        prop("Big Reveal Spot", 920, 120, radius=38)

    return player, all_sprites, props

def nearest_interactable(player, props):
    best = None
    best_d = 10**9
    px, py = player.rect.center
    for o in props:
        ox, oy = o.rect.center
        d = math.hypot(px - ox, py - oy)
        if d < best_d:
            best_d = d
            best = o
    return best, best_d

def set_scene(new_scene):
    global player, all_sprites, props
    state.scene = new_scene
    player, all_sprites, props = build_scene(state.scene)
    state.set_toast(f"Entered: {new_scene.upper()}", 150)
    start_room_music(new_scene)

# ---------------- Story logic ----------------

def bump_suspicion():
    state.flags["suspicious"] = min(4, state.flags["suspicious"] + 1)

def begin_game():
    state.mode = "play"
    state.scene = "schoolyard"
    state.objective = "Talk to Susan, Peter, and Duncan. Then enter the School Door."
    set_scene("schoolyard")
    state.push_dialog(DialogChoice(
        "It’s a regular school morning… except something about your new teacher feels wrong. "
        "Not ‘strict’ wrong. More like ‘not from here’ wrong.",
        ["Okay…", "That’s impossible.", "Let’s pay attention."],
        lambda idx: None
    ))
    state.next_dialog()

def restart_game():
    global state
    state = GameState()
    begin_game()

def interact():
    nearest, d = nearest_interactable(player, props)
    if nearest and d <= 100:
        if SFX_INTERACT:
            SFX_INTERACT.play()
        talk_to(nearest.name)
    else:
        state.set_toast("Nothing close enough (get closer!)", 120)

def talk_to(name):
    # --- SCHOOLYARD ---
    if state.scene == "schoolyard":
        if name == "Susan Simmons":
            def after(i):
                state.flags["met_susan"] = True
                if i in (0, 1): bump_suspicion()
                state.set_toast("Susan: “We need proof… and we need to be careful.”", 200)
            state.push_dialog(DialogChoice(
                "Susan looks like she’s already solving something. “You feel it too, right?”",
                ["Ask what she noticed", "Agree and watch together", "Say she’s overreacting"],
                after
            ))
            state.next_dialog()

        elif name == "Peter Thompson":
            def after(i):
                state.flags["met_peter"] = True
                if i == 1: bump_suspicion()
                state.set_toast("Peter: “This is either nothing… or the biggest thing ever.”", 220)
            state.push_dialog(DialogChoice(
                "Peter grins nervously. “This might be the most interesting day ever.”",
                ["Tell him to stay calm", "Ask what he saw", "Ask him to help investigate"],
                after
            ))
            state.next_dialog()

        elif name == "Duncan Dougal":
            def after(i):
                state.flags["met_duncan"] = True
                if i == 1: state.flags["got_help"] = True
                if i == 2: bump_suspicion()
                state.set_toast("Duncan: “I’m not scared… I just hate surprises.”", 220)
            state.push_dialog(DialogChoice(
                "Duncan sizes you up. “What are YOU staring at?”",
                ["Tell him nothing", "Ask him to help (carefully)", "Ask if he noticed the teacher"],
                after
            ))
            state.next_dialog()

        elif name == "School Door":
            if state.flags["met_susan"] and state.flags["met_peter"] and state.flags["met_duncan"]:
                state.push_dialog(DialogChoice(
                    "The school door swings open. The air inside smells like pencils… and secrets.",
                    ["Go in", "Go in", "Go in"],
                    lambda idx: (set_scene("classroom"), setattr(state, "objective", "In class: talk to Mr. Smith and check the Teacher Desk."))
                ))
                state.next_dialog()
            else:
                state.set_toast("Talk to Susan, Peter, and Duncan first.", 200)

    # --- CLASSROOM ---
    elif state.scene == "classroom":
        if name == "Mr. Smith":
            def after(i):
                state.flags["met_teacher"] = True
                if i in (0, 2): bump_suspicion()
                state.set_toast("Mr. Smith: “Observe carefully… and learn quickly.”", 220)
                state.objective = "Find a clue (Teacher Desk) and get into the hallway."
            state.push_dialog(DialogChoice(
                "Mr. Smith writes one word on the board: “OBSERVE.” Then he turns too smoothly.",
                ["Ask if he’s ‘normal’", "Act like everything’s fine", "Stay quiet and watch"],
                after
            ))
            state.next_dialog()

        elif name == "Teacher Desk":
            if not state.flags["found_clue"]:
                def after(i):
                    if i == 0:
                        state.flags["found_clue"] = True
                        bump_suspicion()
                        state.set_toast("You find a stamped slip with star-like marks. CLUE found.", 240)
                    elif i == 1:
                        state.flags["learned_schedule"] = True
                        bump_suspicion()
                        state.set_toast("You overhear a strange ‘selection’ list being mentioned.", 240)
                    else:
                        state.set_toast("You close the desk quietly.", 180)
                    state.objective = "Head to the hallway."
                state.push_dialog(DialogChoice(
                    "The teacher’s desk drawer sticks for a second… then opens.",
                    ["Search carefully for anything odd", "Listen first, then peek", "Close it—too risky"],
                    after
                ))
                state.next_dialog()
            else:
                state.set_toast("You already searched the desk.", 160)

        elif name == "Hallway Door":
            state.push_dialog(DialogChoice(
                "The hallway feels louder than it should be. Like the building is whispering.",
                ["Go out", "Go out", "Go out"],
                lambda idx: (set_scene("hallway"), setattr(state, "objective", "Check the Notice Board and decide your next move."))
            ))
            state.next_dialog()

        elif name in ("Susan Simmons", "Peter Thompson", "Duncan Dougal"):
            state.set_toast(f"{name} is watching the teacher closely.", 150)

    # --- HALLWAY ---
    elif state.scene == "hallway":
        if name == "Notice Board":
            def after(i):
                if i == 0:
                    state.flags["learned_schedule"] = True
                    bump_suspicion()
                    state.set_toast("A posted schedule has odd symbols. Like it’s coded.", 240)
                elif i == 1:
                    state.flags["got_help"] = True
                    state.set_toast("You wave Susan closer. She nods like she expected this.", 220)
                else:
                    state.set_toast("You step away before anyone notices you staring.", 180)

                if state.flags["found_clue"] and state.flags["learned_schedule"]:
                    state.objective = "Go to the Storage Door to regroup."
                else:
                    state.objective = "You need more: find a clue AND learn what the symbols mean."
            state.push_dialog(DialogChoice(
                "The notice board is covered in papers. One page has markings that don’t look like school stuff.",
                ["Study the weird page", "Wave Susan over", "Back away"],
                after
            ))
            state.next_dialog()

        elif name == "Storage Door":
            if state.flags["found_clue"] and state.flags["learned_schedule"]:
                state.push_dialog(DialogChoice(
                    "The storage door is usually locked… but today it opens. Like it was waiting.",
                    ["Go in", "Go in", "Go in"],
                    lambda idx: (set_scene("plan_room"), setattr(state, "objective", "Make a plan together (Idea Board)."))
                ))
                state.next_dialog()
            else:
                state.set_toast("You’re not ready. You need more evidence first.", 220)

        elif name == "Back to Class":
            state.push_dialog(DialogChoice(
                "Go back to class?",
                ["Yes", "Yes", "Yes"],
                lambda idx: (set_scene("classroom"), setattr(state, "objective", "Find a clue (Teacher Desk) and return."))
            ))
            state.next_dialog()

        elif name == "Susan Simmons":
             state.set_toast("Susan is waiting for you to check the Notice Board.", 150)

    # --- PLAN ROOM ---
    elif state.scene == "plan_room":
        if name == "Idea Board":
            def after(i):
                state.flags["made_plan"] = True
                state.flags["ready_finale"] = True
                if i == 0: state.set_toast("Plan: Controlled distraction to force the truth out.", 240)
                elif i == 1: state.set_toast("Plan: Public confrontation—no hiding.", 240)
                else: state.set_toast("Plan: Bait-and-reveal—make him slip.", 240)
                state.objective = "Go to the Auditorium Door."
            state.push_dialog(DialogChoice(
                "You huddle up. Susan wants proof. Peter wants bold action. Duncan wants it over with.",
                ["Susan plan: controlled distraction", "Peter plan: public confrontation", "Duncan plan: bait-and-reveal"],
                after
            ))
            state.next_dialog()

        elif name == "Auditorium Door":
            if state.flags["ready_finale"]:
                state.push_dialog(DialogChoice(
                    "The auditorium is empty… but it feels like a stage waiting for one moment.",
                    ["Enter", "Enter", "Enter"],
                    lambda idx: (set_scene("finale"), setattr(state, "objective", "Trigger Stage Control, then go to Big Reveal Spot."))
                ))
                state.next_dialog()
            else:
                state.set_toast("You’re not ready yet. Make a plan first.", 200)

        elif name == "Back Hall":
            state.push_dialog(DialogChoice(
                "Go back to the hallway?",
                ["Yes", "Yes", "Yes"],
                lambda idx: (set_scene("hallway"), setattr(state, "objective", "Finish gathering info, then regroup at Storage Door."))
            ))
            state.next_dialog()

        elif name in ("Susan Simmons", "Peter Thompson", "Duncan Dougal"):
             state.set_toast("Everyone is arguing about the plan. Check the Idea Board.", 150)

    # --- FINALE ---
    elif state.scene == "finale":
        if name == "Stage Control":
            def after(i):
                state.objective = "IT'S TIME! Go to the Big Reveal Spot center stage."
                state.set_toast("You cut the audio... the hologram flickers!", 240)
                
            state.push_dialog(DialogChoice(
                "A stage control panel. One switch labeled: “AUDIO / LIGHTS / HOLO.”",
                ["FLIP THE SWITCH NOW!", "Wait... no, do it NOW.", "Signal friends, then FLIP IT."],
                after
            ))
            state.next_dialog()

        elif name == "Big Reveal Spot":
            # No flag checks. Just trigger.
            def after(i):
                if i == 0: ending("REVEAL")
                elif i == 1: ending("SAVE")
                else: ending("BOLD")
            state.push_dialog(DialogChoice(
                "The lights are off. The audio is dead. The teacher is glitching.",
                ["Point and shout: 'LOOK!'", "Grab your friends and run", "Walk up and poke him"],
                after
            ))
            state.next_dialog()

        elif name == "Mr. Smith":
            state.push_dialog(DialogChoice(
                "Mr. Smith is staring at the dark stage controls. He looks... worried.",
                ["Grin at him", "Stay back", "Yell 'Gotcha!'"],
                lambda i: state.set_toast("Mr. Smith: “Technical difficulties...”", 200)
            ))
            state.next_dialog()
        
        elif name in ("Susan Simmons", "Peter Thompson", "Duncan Dougal"):
             state.set_toast(f"{name} is waiting for you to flip the switch!", 150)

def ending(kind):
    if kind == "REVEAL":
        msg = (
            "You force the moment into the open. Under bright lights, the ‘normal’ act slips—"
            "and something alien flashes through.\n\n"
            "People gasp. Adults freeze. But you did it: the truth is public.\n"
            "Whatever happens next… you changed the story."
        )
    elif kind == "SAVE":
        msg = (
            "You choose people over proof. You pull your friends away first, even if the truth is messier.\n\n"
            "You don’t get a perfect ‘gotcha’ moment… but you keep everyone together."
        )
    else:
        msg = (
            "You step forward and confront him. It’s terrifying—but honest.\n\n"
            "For one heartbeat, the ‘teacher’ looks almost impressed.\n"
            "Courage is a kind of intelligence."
        )

    # FIX: DO NOT CALL next_dialog() HERE.
    # try_choice() will call next_dialog() after this function returns,
    # which will pop this dialog off the queue and show it.
    state.push_dialog(DialogChoice(
        msg + "\n\n(THE END)  Press 1 to restart, or ESC to quit.",
        ["Restart", "Restart", "Restart"],
        lambda idx: restart_game()
    ))

# ---------------- Movement & Input ----------------

def handle_player_movement(keys):
    if state.active_dialog:
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
    if not state.active_dialog:
        return
    idx = None
    if key == pygame.K_1: idx = 0
    elif key == pygame.K_2: idx = 1
    elif key == pygame.K_3: idx = 2
    if idx is None:
        return
    if idx >= len(state.active_dialog.choices):
        return

    if SFX_SELECT:
        SFX_SELECT.play()

    # logic: run the callback
    state.active_dialog.on_choose(idx)
    # logic: advance to the next dialog in queue
    state.next_dialog()

def draw_background(screen):
    if state.scene == "schoolyard":
        screen.fill((25, 50, 40))
    elif state.scene == "classroom":
        screen.fill((30, 45, 55))
    elif state.scene == "hallway":
        screen.fill((45, 35, 35))
    elif state.scene == "plan_room":
        screen.fill((30, 30, 45))
    else:
        screen.fill((35, 25, 40))

    for x in range(0, WIDTH, 80):
        pygame.draw.line(screen, (0, 0, 0), (x, 72), (x, HEIGHT), 1)

# ---------------- Pygbag async main ----------------

async def main():
    global FONT, BIG, HUGE
    global player, all_sprites, props
    global SFX_SELECT, SFX_INTERACT, ROOM_MUSIC

    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT))
    screen = pygame.display.get_surface()
    pygame.display.set_caption("My Teacher Is an Alien - Text Adventure")

    pygame.font.init()
    FONT = pygame.font.Font(None, 24)
    BIG = pygame.font.Font(None, 40)
    HUGE = pygame.font.Font(None, 64)

    # Audio Init with Arpeggios
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
        SFX_SELECT = make_tone(880, ms=80, volume=0.25, wave="square")
        SFX_INTERACT = make_tone(440, ms=70, volume=0.20, wave="triangle")

        # Create simple musical loops
        ROOM_MUSIC = {
            "schoolyard": make_arpeggio([220, 261, 330, 261], ms_per_note=350, volume=0.10),
            "classroom":  make_arpeggio([246, 293, 246, 196], ms_per_note=400, volume=0.10),
            "hallway":    make_arpeggio([196, 220, 196, 164], ms_per_note=400, volume=0.10),
            "plan_room":  make_arpeggio([262, 330, 392, 330], ms_per_note=300, volume=0.10),
            "finale":     make_arpeggio([146, 174, 146, 130], ms_per_note=250, volume=0.12),
        }
    except Exception:
        SFX_SELECT = None
        SFX_INTERACT = None
        ROOM_MUSIC = {}

    clock = pygame.time.Clock()
    player, all_sprites, props = build_scene(state.scene)

    running = True
    while running:
        clock.tick(FPS)
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                if state.mode == "title":
                    if event.key == pygame.K_RETURN:
                        begin_game()
                    continue

                if event.key == pygame.K_e and not state.active_dialog:
                    interact()

                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    try_choice(event.key)

        if state.mode == "title":
            draw_title_screen(screen)
            pygame.display.flip()
            await asyncio.sleep(0)
            continue

        handle_player_movement(keys)
        for a in all_sprites:
            if isinstance(a, Actor):
                a.update()

        update_toast()

        draw_background(screen)
        for a in all_sprites:
            draw_actor(screen, a)

        draw_ui(screen, player, props)
        draw_dialog(screen)

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())