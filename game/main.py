import pygame
import asyncio
import math
import random

# =========================================================
# My Teacher Is an Alien (Book 1 inspired) - NO AUDIO build
# - Pygbag/pygame-web friendly
# - Move + interact + 1/2/3 choices
# - Simple shapes (teacher-alien + little people)
# - No sound anywhere (removes browser audio bugs)
# - Debug HUD + crash overlay
# =========================================================

WIDTH, HEIGHT = 1000, 650
FPS = 60

WHITE = (245, 245, 245)
BLACK = (10, 10, 12)
GRAY  = (210, 210, 210)
YELLOW = (245, 220, 90)
CYAN   = (90, 235, 235)

GREEN = (70, 200, 110)
BLUE  = (70, 140, 235)
BROWN = (200, 135, 85)
PURPLE = (160, 110, 190)

BG_SCHOOLYARD = (40, 120, 70)
BG_CLASSROOM  = (55, 95, 140)
BG_HALLWAY    = (140, 85, 60)
BG_PLAN       = (95, 70, 140)
BG_FINALE     = (115, 60, 115)

WORLD = pygame.Rect(0, 0, WIDTH, HEIGHT)

# ----------------------------
# Helpers
# ----------------------------

def clamp_rect(r: pygame.Rect):
    r.clamp_ip(WORLD)

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

def draw_text(surf, text, x, y, color, font):
    surf.blit(font.render(text, True, color), (x, y))

# ----------------------------
# Sprite drawing
# ----------------------------

def draw_little_person(screen, x, y, body_color, scale=1.0):
    head_r = int(8 * scale)
    body_w = int(14 * scale)
    body_h = int(18 * scale)
    
    pygame.draw.circle(screen, (240, 220, 200), (x, y - 18), head_r)  # head
    pygame.draw.rect(screen, body_color, (x - body_w // 2, y - 10, body_w, body_h), border_radius=4)  # body
    pygame.draw.line(screen, BLACK, (x - 5, y + 8), (x - 8, y + 16), 2)  # legs
    pygame.draw.line(screen, BLACK, (x + 5, y + 8), (x + 8, y + 16), 2)

def draw_alien_teacher(screen, x, y, scale=1.0, with_pointer=True):
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
    pygame.draw.polygon(screen, GRAY, [(x - 10, y - 18), (x, y - 6), (x + 10, y - 18)])
    pygame.draw.polygon(screen, (170, 90, 190), [(x, y - 6), (x - 5, y + 8), (x + 5, y + 8)])
    
    # pointer
    if with_pointer:
        pygame.draw.line(screen, (190, 165, 120), (x + 18, y + 6), (x + 46, y - 8), 3)
        pygame.draw.circle(screen, (190, 165, 120), (x + 46, y - 8), 3)

# ----------------------------
# Game objects/state
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
        self.mode = "title"
        self.scene = "schoolyard"
        self.queue = []
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
        self.queue.append(d)
    
    def next(self):
        self.dialog = self.queue.pop(0) if self.queue else None
    
    def toast_msg(self, msg, frames=180):
        self.toast = msg
        self.toast_timer = frames

S = State()

player = None
actors = []
props = []

def scene_bg(scene):
    return {
        "schoolyard": BG_SCHOOLYARD,
        "classroom": BG_CLASSROOM,
        "hallway": BG_HALLWAY,
        "plan_room": BG_PLAN,
        "finale": BG_FINALE
    }.get(scene, (30, 30, 30))

def build_scene(scene):
    actors = []
    props = []
    
    player = Actor("You", "player", 120, HEIGHT // 2, BLUE, speed=4)
    actors.append(player)
    
    def npc(name, x, y, color, wander=True):
        a = Actor(name, "npc", x, y, color, speed=2, wander=wander)
        actors.append(a)
        props.append(a)
    
    def prop(name, x, y):
        a = Actor(name, "prop", x, y, YELLOW, speed=0, wander=False)
        actors.append(a)
        props.append(a)
    
    if scene == "schoolyard":
        npc("Susan Simmons", 320, 420, GREEN, wander=True)
        npc("Peter Thompson", 480, 260, (90, 210, 120), wander=True)
        npc("Duncan Dougal", 720, 460, BROWN, wander=True)
        prop("School Door", 920, 120)
    
    elif scene == "classroom":
        npc("Susan Simmons", 280, 440, GREEN, wander=True)
        npc("Peter Thompson", 410, 360, (90, 210, 120), wander=True)
        npc("Duncan Dougal", 640, 470, BROWN, wander=True)
        t = Actor("Mr. Smith (Broxholm)", "npc", 760, 200, PURPLE, speed=0, wander=False)
        actors.append(t); props.append(t)
        prop("Teacher Desk", 520, 520)
        prop("Hallway Door", 920, 120)
    
    elif scene == "hallway":
        npc("Susan Simmons", 240, 520, GREEN, wander=False)
        prop("Notice Board", 520, 260)
        prop("Storage Door", 900, 520)
        prop("Back to Class", 80, 120)
    
    elif scene == "plan_room":
        npc("Susan Simmons", 240, 520, GREEN, wander=False)
        npc("Peter Thompson", 320, 560, (90, 210, 120), wander=False)
        npc("Duncan Dougal", 410, 520, BROWN, wander=False)
        prop("Idea Board", 560, 260)
        prop("Auditorium Door", 920, 120)
        prop("Back Hall", 80, 120)
    
    elif scene == "finale":
        npc("Susan Simmons", 220, 560, GREEN, wander=False)
        npc("Peter Thompson", 300, 590, (90, 210, 120), wander=False)
        npc("Duncan Dougal", 390, 560, BROWN, wander=False)
        t = Actor("Mr. Smith (Broxholm)", "npc", 760, 230, PURPLE, speed=0, wander=False)
        actors.append(t); props.append(t)
        prop("Stage Control", 720, 520)
        prop("Big Reveal Spot", 920, 120)
    
    return player, actors, props

def set_scene(scene):
    global player, actors, props
    S.scene = scene
    player, actors, props = build_scene(scene)
    S.toast_msg(f"Entered: {scene.upper()}", 120)

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
        msg = ("Under the bright stage lights, the ‘normal teacher’ act slips—\n"
               "and something alien flashes through.\n\nTHE END")
    elif kind == "SAVE":
        msg = ("You protect your friends first. The truth is messy, but you stay together.\n\nTHE END")
    else:
        msg = ("You confront him directly. Terrifying… but honest.\n\nTHE END")
    
    S.push(DialogChoice(msg + "\n\nPress 1 to restart, or ESC to quit.",
                        ["Restart", "Restart", "Restart"],
                        lambda i: restart_game()))
    S.next()

def talk_to(name):
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
                                )); S.next()
    
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
                                )); S.next()
        
        elif name == "Duncan Dougal":
            def after(i):
                S.flags["met_duncan"] = True
                if i == 2:
                    bump_suspicion()
                S.toast_msg("Duncan: “I’m not scared… I just hate surprises.”", 220)
            S.push(DialogChoice(
                                "Duncan sizes you up. “What are YOU staring at?”",
                                ["Tell him nothing", "Ask him to help (carefully)", "Ask if he noticed the teacher"],
                                after
                                )); S.next()
        
        elif name == "School Door":
            if S.flags["met_susan"] and S.flags["met_peter"] and S.flags["met_duncan"]:
                S.push(DialogChoice(
                                    "The school door swings open. The air inside smells like pencils… and secrets.",
                                    ["Go in", "Go in", "Go in"],
                                    lambda i: (set_scene("classroom"),
                                               setattr(S, "objective", "Talk to Mr. Smith (Broxholm) and check the Teacher Desk."))
                                    )); S.next()
            else:
                S.toast_msg("Talk to Susan, Peter, and Duncan first.", 200)

elif S.scene == "classroom":
    if name == "Mr. Smith (Broxholm)":
        def after(i):
            S.flags["met_teacher"] = True
            bump_suspicion()
            S.toast_msg("Mr. Smith: “Observe carefully… and learn quickly.”", 220)
            S.objective = "Find a clue (Teacher Desk) and go to the hallway."
            S.push(DialogChoice(
                                "Mr. Smith writes one word on the board: “OBSERVE.” Then he turns too smoothly.",
                                ["Ask a careful question", "Act normal", "Stay quiet and watch"],
                                after
                                )); S.next()
        
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
                                    ["Search carefully", "Look for a schedule clue", "Close it—too risky"],
                                    after
                                    )); S.next()
            else:
                S.toast_msg("You already searched the desk.", 160)

    elif name == "Hallway Door":
        S.push(DialogChoice(
                            "The hallway feels louder than it should be. Like the building is whispering.",
                            ["Go out", "Go out", "Go out"],
                            lambda i: (set_scene("hallway"),
                                       setattr(S, "objective", "Check the Notice Board and decide your next move."))
                            )); S.next()

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
                    S.toast_msg("You step away before anyone notices.", 180)
                
                if S.flags["found_clue"] and S.flags["learned_schedule"]:
                    S.objective = "Go to the Storage Door to regroup."
                else:
                    S.objective = "You need more: find a clue AND study the symbols."
        S.push(DialogChoice(
                            "The notice board is covered in papers. One page has markings that don’t look like school stuff.",
                            ["Study the weird page", "Wave Susan over", "Back away"],
                            after
                            )); S.next()
            
                            elif name == "Storage Door":
                                if S.flags["found_clue"] and S.flags["learned_schedule"]:
                                    S.push(DialogChoice(
                                                        "The storage door is usually locked… but today it opens. Like it was waiting.",
                                                        ["Go in", "Go in", "Go in"],
                                                        lambda i: (set_scene("plan_room"),
                                                                   setattr(S, "objective", "Make a plan together (Idea Board)."))
                                                        )); S.next()
                                        else:
                                            S.toast_msg("Not ready. You need more evidence first.", 220)
                                                
                                                elif name == "Back to Class":
                                                    S.push(DialogChoice(
                                                                        "Go back to class?",
                                                                        ["Yes", "Yes", "Yes"],
                                                                        lambda i: (set_scene("classroom"),
                                                                                   setattr(S, "objective", "Find a clue (Teacher Desk) and return."))
                                                                        )); S.next()

elif S.scene == "plan_room":
    if name == "Idea Board":
        def after(i):
            S.flags["made_plan"] = True
            S.flags["ready_finale"] = True
            bump_suspicion()
            S.objective = "Go to the Auditorium Door."
                S.toast_msg("Plan locked in. Time for the auditorium.", 220)
            S.push(DialogChoice(
                                "You huddle up and decide how to force the truth out.",
                                ["Controlled distraction", "Public confrontation", "Bait-and-reveal"],
                                after
                                )); S.next()
                
                elif name == "Auditorium Door":
                                if S.flags["ready_finale"]:
                S.push(DialogChoice(
                                    "The auditorium is empty… but it feels like a stage waiting for one moment.",
                                    ["Enter", "Enter", "Enter"],
                                    lambda i: (set_scene("finale"),
                                               setattr(S, "objective", "Use Stage Control, then go to Big Reveal Spot."))
                                    )); S.next()
                else:
                    S.toast_msg("Make a plan first (Idea Board).", 200)

    elif name == "Back Hall":
        S.push(DialogChoice(
                            "Go back to the hallway?",
                            ["Yes", "Yes", "Yes"],
                            lambda i: (set_scene("hallway"),
                                       setattr(S, "objective", "Finish gathering info, then regroup."))
                            )); S.next()

elif S.scene == "finale":
    if name == "Stage Control":
        def after(i):
            bump_suspicion()
            S.toast_msg("Lights shift. The ‘normal’ act feels thinner.", 240)
            S.push(DialogChoice(
                                "A stage control panel. One switch labeled: “AUDIO / LIGHTS.”",
                                ["Flip it now", "Wait for him to approach", "Signal your friends first"],
                                after
                                )); S.next()
        
        elif name == "Big Reveal Spot":
            # FIX: allow reveal if suspicion is high AND (made_plan OR ready_finale)
            if S.flags["suspicious"] >= 3 and (S.flags["made_plan"] or S.flags["ready_finale"]):
                def after(i):
                    if i == 0: ending("REVEAL")
                    elif i == 1: ending("SAVE")
                    else: ending("BOLD")
                S.push(DialogChoice(
                                    "This is it. Time to reveal the truth.",
                                    ["Reveal him publicly", "Protect your friends first", "Confront him directly"],
                                    after
                                    )); S.next()
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
                                )); S.next()

# ----------------------------
# Controls
# ----------------------------

def handle_player_movement(keys):
    if S.dialog:
        return
    dx = dy = 0
    if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx -= player.speed
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += player.speed
    if keys[pygame.K_UP] or keys[pygame.K_w]: dy -= player.speed
    if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy += player.speed
    player.rect.x += dx
    player.rect.y += dy
    clamp_rect(player.rect)

def try_choice(key):
    if not S.dialog:
        return
    idx = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}.get(key)
    if idx is None or idx >= len(S.dialog.choices):
        return
    S.dialog.on_choose(idx)
    S.next()

def interact():
    obj, d = nearest_interactable()
    if obj and d <= 85:
        talk_to(obj.name)
    else:
        S.toast_msg("Nothing to interact with nearby.", 120)

# ----------------------------
# Drawing
# ----------------------------

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
            pygame.draw.circle(screen, a.color, (x, y), 18)
            pygame.draw.circle(screen, BLACK, (x, y), 18, 2)

def draw_ui(screen, FONT, BIG):
    pygame.draw.rect(screen, (18, 18, 20), (0, 0, WIDTH, 82))
    pygame.draw.rect(screen, WHITE, (0, 0, WIDTH, 82), 2)
    draw_text(screen, f"Scene: {S.scene.upper()}", 14, 10, WHITE, BIG)
    draw_text(screen, f"Objective: {S.objective}", 14, 52, GRAY, FONT)
    draw_text(screen, f"Suspicion: {S.flags['suspicious']}/4", WIDTH - 210, 52, YELLOW, FONT)
    
    if S.toast_timer > 0:
        pygame.draw.rect(screen, BLACK, (12, 92, WIDTH - 24, 34), border_radius=8)
        pygame.draw.rect(screen, WHITE, (12, 92, WIDTH - 24, 34), 2, border_radius=8)
        draw_text(screen, S.toast, 22, 100, WHITE, FONT)
    
    if not S.dialog:
        obj, d = nearest_interactable()
        if obj and d <= 85:
            pygame.draw.rect(screen, BLACK, (12, HEIGHT - 52, WIDTH - 24, 40), border_radius=10)
            pygame.draw.rect(screen, WHITE, (12, HEIGHT - 52, WIDTH - 24, 40), 2, border_radius=10)
            draw_text(screen, f"Press E to interact with: {obj.name}", 22, HEIGHT - 42, WHITE, FONT)

def draw_dialog(screen, FONT):
    if not S.dialog:
        return
    box = pygame.Rect(40, HEIGHT - 250, WIDTH - 80, 210)
    pygame.draw.rect(screen, BLACK, box, border_radius=14)
    pygame.draw.rect(screen, WHITE, box, 2, border_radius=14)

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
# Main (with crash overlay)
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
    
    # create initial scene objects
    set_scene("schoolyard")
    
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
                    
                    if S.mode == "title" and event.key == pygame.K_RETURN:
                        begin_game()
                    
                    if S.mode == "play":
                        if event.key == pygame.K_e and not S.dialog:
                            interact()
                        if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                            try_choice(event.key)

    # timers
    if S.toast_timer > 0:
        S.toast_timer -= 1
            if S.toast_timer <= 0:
                S.toast = ""
            
            # update actors
            if S.mode == "play":
                handle_player_movement(keys)
                for a in actors:
                    a.update()

        # draw
        if S.mode == "title":
            draw_title(screen, FONT, BIG, HUGE)
            else:
                screen.fill(scene_bg(S.scene))
                draw_actors(screen)
                draw_ui(screen, FONT, BIG)
                draw_dialog(screen, FONT)

# debug HUD (always visible)
dbg = f"DEBUG mode={S.mode} scene={S.scene} dialog={'Y' if S.dialog else 'N'}"
    draw_text(screen, dbg, 12, HEIGHT - 26, WHITE, FONT)
    
    pygame.display.flip()
        await asyncio.sleep(0)
        
        except Exception as e:
            # crash overlay
            screen.fill((30, 0, 0))
            pygame.draw.rect(screen, BLACK, (30, 30, WIDTH - 60, HEIGHT - 60), border_radius=12)
            pygame.draw.rect(screen, WHITE, (30, 30, WIDTH - 60, HEIGHT - 60), 2, border_radius=12)
            draw_text(screen, "CRASH", 60, 60, (255, 180, 180), HUGE)
            msg = f"{type(e).__name__}: {e}"
            for i, line in enumerate(wrap_lines(msg, WIDTH - 140, FONT)[:12]):
                draw_text(screen, line, 60, 140 + i * 28, WHITE, FONT)
            pygame.display.flip()
            await asyncio.sleep(0)

pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())

