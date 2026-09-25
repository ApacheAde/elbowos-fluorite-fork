#!/usr/bin/env python3
"""Fluorite Fork — neon lightning-fork arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "FLUORITE FORK"
HANDLE = "x.com/ElbowOS"

VOID = (6, 4, 18)
INK = (16, 10, 42)
MINT = (72, 255, 210)
MAG = (255, 48, 168)
GOLD = (255, 210, 70)
LIME = (170, 255, 80)
ICE = (180, 220, 255)
VIO = (140, 90, 255)
CREAM = (255, 246, 232)
NAVY = (22, 16, 56)


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "col", "r")

    def __init__(self, x, y, vx, vy, life, col, r=4):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.col, self.r = life, col, r


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 56)
        self.font_md = pygame.font.Font(None, 42)
        self.font_sm = pygame.font.Font(None, 30)
        self.screen = None
        if not record:
            self.screen = pygame.display.set_mode((W, H))
            pygame.display.set_caption(TITLE)
        self.reset()

    def reset(self) -> None:
        self.t = 0.0
        self.score = 0
        self.miss = 0
        self.lane = 2
        self.lanes = 5
        self.y = 240.0
        self.speed = 420.0
        self.nodes: list[tuple] = []
        self.sparks: list[Spark] = []
        self.pops: list[tuple] = []
        self.trail: list[tuple] = []
        self.stars = [(random.randint(0, W), random.randint(0, H), random.random()) for _ in range(80)]
        self.running = True
        self.flash = 0.0
        self.fork_cd = 0.0
        self._seed_nodes()

    def lx(self, i: int) -> float:
        return 140 + i * 200

    def _seed_nodes(self) -> None:
        self.nodes.clear()
        for row in range(8):
            y = 380 + row * 180
            for i in range(self.lanes):
                kind = random.choices(("orb", "spine", "empty"), weights=(4, 2, 3))[0]
                if kind != "empty":
                    self.nodes.append((i, y, kind, random.random() * math.tau))

    def burst(self, x, y, col, n=16) -> None:
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(80, 480)
            self.sparks.append(Spark(x, y, math.cos(a) * sp, math.sin(a) * sp,
                                     random.uniform(0.16, 0.48), col, random.randint(3, 7)))

    def fork(self, d: int) -> None:
        if self.fork_cd > 0:
            return
        nxt = max(0, min(self.lanes - 1, self.lane + d))
        if nxt == self.lane:
            return
        self.lane = nxt
        self.fork_cd = 0.08
        self.burst(self.lx(self.lane), self.y, MINT, 10)

    def update(self, dt: float) -> None:
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.fork_cd = max(0.0, self.fork_cd - dt)
        if self.record:
            self.autoplay(dt)
        self.speed = 400 + 90 * math.sin(self.t * 0.7) + self.t * 8
        self.y += self.speed * dt
        if self.y > 1680:
            self.y = 260
            self._seed_nodes()
            self.burst(self.lx(self.lane), self.y, GOLD, 18)
        self.trail.append((self.lx(self.lane), self.y))
        self.trail = self.trail[-28:]
        keep = []
        for i, y, kind, ph in self.nodes:
            if abs(y - self.y) < 28 and i == self.lane:
                if kind == "orb":
                    self.score += 1
                    self.pops.append(("FORK +1", self.lx(i), y - 30, 0.7, GOLD))
                    self.burst(self.lx(i), y, LIME, 20)
                    self.flash = 0.12
                    continue
                if kind == "spine":
                    self.miss += 1
                    self.pops.append(("VOID", self.lx(i), y - 30, 0.7, MAG))
                    self.burst(self.lx(i), y, MAG, 18)
                    self.flash = 0.16
                    continue
            if y > self.y - 40:
                keep.append((i, y, kind, ph + dt * 4))
        self.nodes = keep
        if len(self.nodes) < 10:
            y = max((n[1] for n in self.nodes), default=self.y) + 180
            for i in range(self.lanes):
                kind = random.choices(("orb", "spine", "empty"), weights=(4, 2, 3))[0]
                if kind != "empty":
                    self.nodes.append((i, y + random.randint(-20, 20), kind, random.random()))
        sparks = []
        for sp in self.sparks:
            sp.x += sp.vx * dt
            sp.y += sp.vy * dt
            sp.life -= dt
            if sp.life > 0:
                sparks.append(sp)
        self.sparks = sparks[-240:]
        self.pops = [(a, x, y - 55 * dt, life - dt, c) for a, x, y, life, c in self.pops if life - dt > 0]

    def autoplay(self, dt: float) -> None:
        ahead = [n for n in self.nodes if n[1] > self.y + 20]
        orbs = [n for n in ahead if n[2] == "orb" and n[1] < self.y + 420]
        spines = {n[0] for n in ahead if n[2] == "spine" and n[1] < self.y + 220}
        target = self.lane
        if orbs:
            orbs.sort(key=lambda n: (n[1], abs(n[0] - self.lane)))
            target = orbs[0][0]
        elif spines and self.lane in spines:
            opts = [i for i in range(self.lanes) if i not in spines]
            if opts:
                target = min(opts, key=lambda i: abs(i - self.lane))
        if target > self.lane:
            self.fork(1)
        elif target < self.lane:
            self.fork(-1)

    def draw(self, s: pygame.Surface) -> None:
        s.fill(VOID)
        for sx, sy, tw in self.stars:
            yy = int((sy + self.t * (8 + tw * 22)) % H)
            c = 50 + int(tw * 90)
            pygame.draw.circle(s, (c // 4, c // 3, c), (sx, yy), 1 + int(tw * 2))
        pygame.draw.rect(s, INK, pygame.Rect(40, 150, W - 80, H - 270), border_radius=32)
        pygame.draw.rect(s, NAVY, pygame.Rect(40, 150, W - 80, H - 270), 3, border_radius=32)
        glow = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(self.lanes):
            x = int(self.lx(i))
            pygame.draw.line(s, (40, 28, 88), (x, 200), (x, 1720), 6)
            pulse = 80 + int(40 * math.sin(self.t * 3 + i))
            pygame.draw.line(glow, (90, 60, 180, pulse), (x, 200), (x, 1720), 18)
        for a, b in zip(self.trail, self.trail[1:]):
            pygame.draw.line(glow, (*MINT, 90), (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), 16)
            pygame.draw.line(s, ICE, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), 5)
        s.blit(glow, (0, 0))
        for i, y, kind, ph in self.nodes:
            x = int(self.lx(i))
            r = 18 + int(4 * math.sin(ph))
            if kind == "orb":
                pygame.draw.circle(s, GOLD, (x, int(y)), r + 8)
                pygame.draw.circle(s, LIME, (x, int(y)), r)
                pygame.draw.circle(s, CREAM, (x - 4, int(y) - 5), 5)
            else:
                pts = [(x, int(y) - 22), (x + 16, int(y) + 10), (x, int(y) + 6), (x - 16, int(y) + 10)]
                pygame.draw.polygon(s, MAG, pts)
                pygame.draw.polygon(s, CREAM, pts, 2)
        hx, hy = int(self.lx(self.lane)), int(self.y)
        pygame.draw.circle(s, MINT, (hx, hy), 28)
        pygame.draw.circle(s, ICE, (hx, hy), 16)
        pygame.draw.circle(s, CREAM, (hx - 5, hy - 6), 5)
        for k in range(3):
            a = self.t * 8 + k * math.tau / 3
            pygame.draw.circle(s, VIO, (int(hx + math.cos(a) * 34), int(hy + math.sin(a) * 34)), 4)
        for sp in self.sparks:
            pygame.draw.circle(s, sp.col, (int(sp.x), int(sp.y)), max(1, int(sp.r * sp.life / 0.4)))
        if self.flash > 0:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((180, 255, 220, int(50 * self.flash / 0.16)))
            s.blit(veil, (0, 0))
        title = self.font_lg.render(TITLE, True, GOLD)
        s.blit(title, title.get_rect(center=(W // 2, 52)))
        handle = self.font_sm.render(HANDLE, True, MINT)
        s.blit(handle, handle.get_rect(center=(W // 2, 102)))
        s.blit(self.font_md.render(f"CHARGE  {self.score}", True, LIME), (64, 1788))
        s.blit(self.font_md.render(f"VOID  {self.miss}", True, MAG), (W - 280, 1788))
        hint = self.font_sm.render("fork the bolt onto fluorite orbs", True, CREAM)
        s.blit(hint, hint.get_rect(center=(W // 2, 1844)))
        for tag, x, y, life, col in self.pops:
            img = self.font_md.render(tag, True, col)
            s.blit(img, img.get_rect(center=(int(x), int(y))))
        foot = self.font_sm.render("A/D or arrows fork   R reset   ESC quit", True, (190, 170, 210))
        s.blit(foot, foot.get_rect(center=(W // 2, H - 24)))

    def handle(self, ev) -> None:
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.running = False
            elif ev.key == pygame.K_r:
                self.reset()
            elif ev.key in (pygame.K_a, pygame.K_LEFT):
                self.fork(-1)
            elif ev.key in (pygame.K_d, pygame.K_RIGHT):
                self.fork(1)

    def play(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                self.handle(ev)
            self.update(dt)
            self.draw(self.surf)
            self.screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    play = "--play" in sys.argv
    if record or not play:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record or not play)
    if record or not play:
        out = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/FLUORITE_FORK_ElbowOS.mp4")
        g.record_mp4(out)
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
