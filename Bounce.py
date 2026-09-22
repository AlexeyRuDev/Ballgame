from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle, Triangle, Line
from kivy.core.window import Window
from kivy.config import Config
import math
import random

# Настройка окна ДО импорта App
Config.set('graphics', 'orientation', 'landscape')
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '600')

# --- НАСТРОЙКИ ---
GRAVITY = 0.6
MAX_SPEED = 6
ACCELERATION = 0.4
FRICTION = 0.85
INITIAL_JUMP_VEL = 8
JUMP_HOLD_THRUST = 0.4
MAX_JUMP_VEL = 16
BOUNCINESS = 0.55
MIN_BOUNCE_VEL = 2.5

# Цвета (Kivy использует 0-1 вместо 0-255)
BG_COLOR = (135/255, 206/255, 235/255)
GROUND_COLOR = (34/255, 139/255, 34/255)
SPIKE_COLOR = (178/255, 34/255, 34/255)
BALL_COLOR = (227/255, 38/255, 54/255)
HIGHLIGHT_COLOR = (1, 1, 1)
TUNNEL_COLOR = (80/255, 80/255, 80/255)


class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-5, -1)
        self.life = random.randint(15, 30)
        self.max_life = self.life
        self.radius = random.randint(2, 4)
        self.color = random.choice([
            (200/255, 200/255, 200/255),
            (150/255, 150/255, 150/255),
            (100/255, 100/255, 100/255)
        ])

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.3
        self.life -= 1


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 20
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.is_holding_jump = False
        self.alive = True
        self.won = False
        self.can_jump = False
        
        # Анимация
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.target_scale_x = 1.0
        self.target_scale_y = 1.0
        self.rotation = 0.0
        self.particles = []
    
    def spawn_impact_particles(self, impact_strength):
        count = int(impact_strength * 1.5)
        count = max(3, min(count, 15))
        for _ in range(count):
            p = Particle(
                self.x + random.uniform(-self.radius, self.radius),
                self.y + self.radius - 5
            )
            self.particles.append(p)
    
    def update(self, platforms, spikes, goal, keys):
        if not self.alive or self.won:
            return
        
        # Горизонтальное движение с инерцией
        if keys['left']:
            self.vx -= ACCELERATION
        elif keys['right']:
            self.vx += ACCELERATION
        else:
            self.vx *= FRICTION
            if abs(self.vx) < 0.1:
                self.vx = 0
        
        # Ограничение скорости
        if self.vx > MAX_SPEED:
            self.vx = MAX_SPEED
        elif self.vx < -MAX_SPEED:
            self.vx = -MAX_SPEED
        
        # Вращение
        if self.on_ground or self.can_jump:
            self.rotation += self.vx * 0.05
        else:
            self.rotation += self.vx * 0.02
        
        # Прыжок (в Kivy Y идёт вверх, поэтому vy отрицательный для прыжка)
        if keys['jump']:
            if self.on_ground or self.can_jump:
                self.vy = INITIAL_JUMP_VEL  # Положительный для прыжка вверх
                self.on_ground = False
                self.can_jump = False
                self.is_holding_jump = True
                self.target_scale_x = 0.8
                self.target_scale_y = 1.3
            elif self.is_holding_jump:
                self.vy += JUMP_HOLD_THRUST
                if self.vy > MAX_JUMP_VEL:
                    self.vy = MAX_JUMP_VEL
                    self.is_holding_jump = False
        else:
            self.is_holding_jump = False
        
        # Гравитация (в Kivy отрицательная, тянет вниз)
        self.vy -= GRAVITY
        if self.vy < -20:
            self.vy = -20
        
        # Анимация в полёте
        if not self.on_ground and not self.can_jump:
            if self.vy > 2:
                self.target_scale_x = 0.85
                self.target_scale_y = 1.2
            elif self.vy < -2:
                self.target_scale_x = 1.1
                self.target_scale_y = 0.95
        
        # Движение и коллизии по X
        self.x += self.vx
        was_on_ground = self.on_ground
        self.on_ground = False
        
        for rect in platforms:
            if self.check_collision(rect):
                if self.vx > 0:
                    self.x = rect['left'] - self.radius
                elif self.vx < 0:
                    self.x = rect['right'] + self.radius
                self.vx = 0
        
        # Движение и коллизии по Y
        self.y += self.vy
        for rect in platforms:
            if self.check_collision(rect):
                if self.vy < 0:  # Падает вниз
                    self.y = rect['top'] + self.radius
                    impact_strength = abs(self.vy)
                    
                    if impact_strength >= MIN_BOUNCE_VEL:
                        self.vy = impact_strength * BOUNCINESS
                        self.on_ground = False
                        self.can_jump = True
                        
                        squash = min(impact_strength / 15, 0.4)
                        self.target_scale_x = 1.0 + squash
                        self.target_scale_y = 1.0 - squash
                        
                        if impact_strength > 4:
                            self.spawn_impact_particles(impact_strength)
                    else:
                        self.vy = 0
                        self.on_ground = True
                        self.can_jump = True
                        
                        if impact_strength > 1:
                            squash = min(impact_strength / 15, 0.2)
                            self.target_scale_x = 1.0 + squash
                            self.target_scale_y = 1.0 - squash
                            self.spawn_impact_particles(impact_strength * 0.5)
                
                elif self.vy > 0:  # Летит вверх
                    self.y = rect['bottom'] - self.radius
                    self.vy = 0
        
        if self.on_ground and not was_on_ground:
            self.target_scale_x = 1.0
            self.target_scale_y = 1.0
        
        # Плавная интерполяция масштаба
        lerp_speed = 0.2
        self.scale_x += (self.target_scale_x - self.scale_x) * lerp_speed
        self.scale_y += (self.target_scale_y - self.scale_y) * lerp_speed
        
        if (self.on_ground or self.can_jump) and not self.is_holding_jump:
            self.target_scale_x += (1.0 - self.target_scale_x) * 0.15
            self.target_scale_y += (1.0 - self.target_scale_y) * 0.15
        
        # Обновление частиц
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)
        
        # Проверка шипов
        for rect in spikes:
            if self.check_collision(rect):
                self.alive = False
        
        # Проверка финиша
        if self.x + self.radius > goal['left']:
            self.won = True
        
        # Падение в пропасть (в Kivy Y=0 внизу)
        if self.y < -100:
            self.alive = False
    
    def check_collision(self, rect):
        closest_x = max(rect['left'], min(self.x, rect['right']))
        closest_y = max(rect['bottom'], min(self.y, rect['top']))
        dist_x = self.x - closest_x
        dist_y = self.y - closest_y
        return (dist_x**2 + dist_y**2) < (self.radius**2)


class BounceGame(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Игровые объекты
        self.player = None
        self.platforms = []
        self.spikes = []
        self.goal = None
        self.camera_x = 0
        
        # Управление
        self.keys = {'left': False, 'right': False, 'jump': False}
        self.touch_start_x = None
        
        # Размеры уровня
        self.level_width = 4000
        self.ground_y = 50  # В Kivy земля внизу экрана
        
        # Создаём уровень
        self.create_level()
        self.reset_game()
        
        # Запускаем игровой цикл
        Clock.schedule_interval(self.update, 1/60.0)
        
        # Привязываемся к клавиатуре
        Window.bind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)
    
    def create_level(self):
        # Платформы (координаты в системе Kivy: Y=0 внизу)
        self.platforms = [
            # Начало (земля)
            {'left': 0, 'bottom': 0, 'right': 400, 'top': 50},
            {'left': 500, 'bottom': 50, 'right': 600, 'top': 70},
            {'left': 700, 'bottom': 0, 'right': 900, 'top': 50},
            # Тоннель
            {'left': 1000, 'bottom': 100, 'right': 1600, 'top': 120},  # Пол
            {'left': 1000, 'bottom': 250, 'right': 1600, 'top': 270},  # Потолок
            # После тоннеля
            {'left': 1700, 'bottom': 0, 'right': 2000, 'top': 50},
            {'left': 2100, 'bottom': 100, 'right': 2250, 'top': 120},
            {'left': 2350, 'bottom': 0, 'right': 2750, 'top': 50},
            {'left': 2850, 'bottom': 70, 'right': 2950, 'top': 90},
            {'left': 3050, 'bottom': 150, 'right': 3150, 'top': 170},
            {'left': 3250, 'bottom': 0, 'right': 4000, 'top': 50},
        ]
        
        # Шипы
        self.spikes = [
            {'left': 400, 'bottom': 50, 'right': 500, 'top': 70, 'direction': 'up'},
            {'left': 900, 'bottom': 50, 'right': 1000, 'top': 70, 'direction': 'up'},
            {'left': 2000, 'bottom': 50, 'right': 2100, 'top': 70, 'direction': 'up'},
            {'left': 2750, 'bottom': 50, 'right': 2850, 'top': 70, 'direction': 'up'},
            # Шипы в тоннеле
            {'left': 1100, 'bottom': 230, 'right': 1180, 'top': 250, 'direction': 'down'},
            {'left': 1300, 'bottom': 230, 'right': 1380, 'top': 250, 'direction': 'down'},
            {'left': 1500, 'bottom': 230, 'right': 1560, 'top': 250, 'direction': 'down'},
            {'left': 1050, 'bottom': 120, 'right': 1110, 'top': 140, 'direction': 'up'},
            {'left': 1200, 'bottom': 120, 'right': 1280, 'top': 140, 'direction': 'up'},
            {'left': 1400, 'bottom': 120, 'right': 1460, 'top': 140, 'direction': 'up'},
        ]
        
        # Финиш
        self.goal = {'left': 3900, 'bottom': 50, 'right': 3950, 'top': 150}
    
    def reset_game(self):
        self.player = Player(100, 100)  # Стартуем выше земли
        self.camera_x = 0
    
    def on_key_down(self, window, key, scancode, codepoint, modifier):
        if key == 276 or key == 1000:  # Left / A
            self.keys['left'] = True
        elif key == 275 or key == 1001:  # Right / D
            self.keys['right'] = True
        elif key == 273 or key == 1002:  # Up / W / Space
            self.keys['jump'] = True
        elif key == 27:  # Escape
            App.get_running_app().stop()
        elif key == 114:  # R
            self.reset_game()
    
    def on_key_up(self, window, key, scancode):
        if key == 276 or key == 1000:
            self.keys['left'] = False
        elif key == 275 or key == 1001:
            self.keys['right'] = False
        elif key == 273 or key == 1002:
            self.keys['jump'] = False
    
    def on_touch_down(self, touch):
        if touch.y < self.height / 3:
            self.keys['jump'] = True
            self.touch_start_x = touch.x
        elif touch.x < self.width / 2:
            self.keys['left'] = True
        else:
            self.keys['right'] = True
    
    def on_touch_up(self, touch):
        self.keys['jump'] = False
        self.keys['left'] = False
        self.keys['right'] = False
        self.touch_start_x = None
    
    def on_touch_move(self, touch):
        if self.touch_start_x is not None:
            if touch.x < self.touch_start_x - 50:
                self.keys['left'] = True
                self.keys['right'] = False
            elif touch.x > self.touch_start_x + 50:
                self.keys['right'] = True
                self.keys['left'] = False
    
    def update(self, dt):
        if self.player:
            self.player.update(self.platforms, self.spikes, self.goal, self.keys)
            
            # Камера следует за игроком
            target_camera_x = self.player.x - self.width / 2
            target_camera_x = max(0, min(target_camera_x, self.level_width - self.width))
            self.camera_x += (target_camera_x - self.camera_x) * 0.1
        
        # Перерисовка
        self.canvas.clear()
        with self.canvas:
            # Фон
            Color(*BG_COLOR)
            Rectangle(pos=(0, 0), size=self.size)
            
            # Облака (параллакс)
            Color(1, 1, 1, 0.5)
            for i in range(5):
                cx = (i * 600 - self.camera_x * 0.5) % (self.width + 200)
                Ellipse(pos=(cx, self.height - 100 - i*30), size=(80, 40))
                Ellipse(pos=(cx + 30, self.height - 110 - i*30), size=(60, 30))
            
            # Тоннель
            Color(*TUNNEL_COLOR)
            Rectangle(pos=(1000 - self.camera_x, 100), size=(600, 20))
            Rectangle(pos=(1000 - self.camera_x, 250), size=(600, 20))
            Color(0.2, 0.2, 0.2)
            Line(rectangle=(1000 - self.camera_x, 100, 600, 20), width=3)
            Line(rectangle=(1000 - self.camera_x, 250, 600, 20), width=3)
            
            # Платформы (кроме тоннеля)
            for rect in self.platforms:
                if 1000 <= rect['left'] <= 1600 and rect['bottom'] in [100, 250]:
                    continue
                x = rect['left'] - self.camera_x
                y = rect['bottom']
                w = rect['right'] - rect['left']
                h = rect['top'] - rect['bottom']
                Color(*GROUND_COLOR)
                Rectangle(pos=(x, y), size=(w, h))
                Color(0, 0.4, 0)
                Line(rectangle=(x, y, w, h), width=3)
            
            # Шипы
            for spike in self.spikes:
                x = spike['left'] - self.camera_x
                num_spikes = (spike['right'] - spike['left']) // 20
                
                Color(*SPIKE_COLOR)
                if spike['direction'] == 'up':
                    for i in range(num_spikes):
                        px = x + i * 20
                        Triangle(
                            points=[
                                px, spike['bottom'],
                                px + 10, spike['top'],
                                px + 20, spike['bottom']
                            ]
                        )
                else:  # down
                    for i in range(num_spikes):
                        px = x + i * 20
                        Triangle(
                            points=[
                                px, spike['top'],
                                px + 10, spike['bottom'],
                                px + 20, spike['top']
                            ]
                        )
            
            # Финиш
            Color(0.4, 0.4, 0.4)
            fx = self.goal['left'] - self.camera_x
            Rectangle(pos=(fx + 10, self.goal['bottom']), size=(5, self.goal['top'] - self.goal['bottom']))
            Color(1, 0.84, 0)
            Triangle(
                points=[
                    fx + 15, self.goal['top'] - 40,
                    fx + 50, self.goal['top'] - 20,
                    fx + 15, self.goal['top']
                ]
            )
            
            # Игрок
            if self.player and self.player.alive:
                screen_x = self.player.x - self.camera_x
                screen_y = self.player.y
                
                # Тень
                height_above_ground = max(0, screen_y - self.ground_y)
                shadow_scale = max(0.3, 1.0 - height_above_ground / 300)
                shadow_alpha = 80 * shadow_scale / 255
                Color(0, 0, 0, shadow_alpha)
                shadow_w = self.player.radius * 2.4 * shadow_scale
                Ellipse(
                    pos=(screen_x - shadow_w/2, self.ground_y - 3),
                    size=(shadow_w, 6)
                )
                
                # Частицы
                for p in self.player.particles:
                    alpha = p.life / p.max_life
                    Color(*p.color, alpha)
                    r = p.radius * alpha
                    if r > 0:
                        Ellipse(
                            pos=(p.x - self.camera_x - r, p.y - r),
                            size=(r*2, r*2)
                        )
                
                # Шарик
                w = int(self.player.radius * 2 * self.player.scale_x)
                h = int(self.player.radius * 2 * self.player.scale_y)
                Color(*BALL_COLOR)
                Ellipse(
                    pos=(screen_x - w/2, screen_y - h/2),
                    size=(w, h)
                )
                Color(150/255, 20/255, 30/255)
                Line(ellipse=(screen_x - w/2, screen_y - h/2, w, h), width=2)
                
                # Блик
                highlight_dist = self.player.radius * 0.4
                hx = screen_x + math.cos(self.player.rotation) * highlight_dist * self.player.scale_x
                hy = screen_y + math.sin(self.player.rotation) * highlight_dist * self.player.scale_y - self.player.radius * 0.2
                highlight_r = max(2, int(5 * min(self.player.scale_x, self.player.scale_y)))
                Color(*HIGHLIGHT_COLOR)
                Ellipse(
                    pos=(hx - highlight_r, hy - highlight_r),
                    size=(highlight_r*2, highlight_r*2)
                )


class BounceApp(App):
    def build(self):
        Window.clearcolor = BG_COLOR
        return BounceGame()


if __name__ == '__main__':
    BounceApp().run()