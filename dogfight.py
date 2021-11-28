'''This is where we're going to code our game (assuming you want to do it all in one file). It's just a copy of PlayAsteroids.py for now, but we'll change that as we develop the actual game'''

from tkinter import *
from Game import Game, Agent
from geometry import Point2D, Vector2D
import math
import random
import time

TIME_STEP = 0.5

class MovingBody(Agent):
    '''Parent class for anything that moves. Pretty sure these are all just default values in case the child class doesn't specify any of them.'''
    def __init__(self, p0, v0, world):
        self.velocity = v0
        self.accel    = Vector2D(0.0,0.0)
        Agent.__init__(self,p0,world)

    def color(self):
        return "#000080"

    def shape(self):
        p1 = self.position + Vector2D( 0.125, 0.125)
        p2 = self.position + Vector2D(-0.125, 0.125)
        p3 = self.position + Vector2D(-0.125,-0.125)
        p4 = self.position + Vector2D( 0.125,-0.125)
        return [p1,p2,p3,p4]

    def steer(self):
        return Vector2D(0.0)

    def update(self):
        self.position = self.position + self.velocity * TIME_STEP
        self.velocity = self.velocity + self.accel * TIME_STEP
        self.accel    = self.steer()
        self.world.trim(self)

class Shootable(MovingBody):
    '''Parent class for anything that can be shot'''
    SHRAPNEL_CLASS  = None
    SHRAPNEL_PIECES = 0
    WORTH           = 1

    def __init__(self, position0, velocity0, radius, world):
        self.radius = radius
        MovingBody.__init__(self, position0, velocity0, world)

    def is_hit_by(self, photon):
        if self.shotTimer > (self.shootDelay - self.iFrames): #Never get hit if you have i-frames or are the player who fired
            #print("dodged!") #Debugging
            return False
        '''Version where players could not shoot themselves
        if photon.player_one == self.player_one or self.shotTimer > (self.shootDelay - self.iFrames): #Never get hit if you have i-frames or are the player who fired
            #print("dodged!") #Debugging
            return False'''
        return ((self.position - photon.position).magnitude() < self.radius)

    def explode(self):
        self.world.score += self.WORTH
        self.hp -= 1
        if self.hp > 0: #If the shot doesn't kill, create half the normal number of shrapnel (embers for ships, nothing for asteroids since they only have 1 hp)
            for x in range(self.SHRAPNEL_PIECES // 2):
                self.SHRAPNEL_CLASS(self.position,self.world)
        else:
            if self.SHRAPNEL_CLASS == None:
                '''Return None if the object doesn't create shrapnel when destroyed'''
                return
            for x in range(self.SHRAPNEL_PIECES):
                '''Otherwise, make objects in the object's shrapnel class at its position SHRAPNEL_PIECES number of times'''
                self.SHRAPNEL_CLASS(self.position,self.world)
            self.leave()

class Ember(MovingBody):
    '''Little sparks that come off when an asteroid is destroyed'''
    INITIAL_SPEED = 2.0
    SLOWDOWN      = 0.2
    TOO_SLOW      = INITIAL_SPEED / 20.0

    def __init__(self, position0, world):
        velocity0 = Vector2D.random() * self.INITIAL_SPEED
        MovingBody.__init__(self, position0, velocity0, world)

    def color(self):
        white_hot  = "#FFFFFF"
        burning    = "#FF8080"
        smoldering = "#808040"
        speed = self.velocity.magnitude()
        if speed / self.INITIAL_SPEED > 0.5:
            return white_hot
        if speed / self.INITIAL_SPEED > 0.25:
            return burning
        return smoldering

    def steer(self):
        return -self.velocity.direction() * self.SLOWDOWN

    def update(self):
        MovingBody.update(self)
        if self.velocity.magnitude() < self.TOO_SLOW:
            self.leave()

class Photon(MovingBody):
    '''Projectiles that the player shoots out'''
    INITIAL_SPEED = 2.6
    LIFETIME      = 70 #Measured in tics, not distance travelled

    def __init__(self,source,world, player_one):
        self.player_one = player_one
        self.age  = 0
        v0 = source.get_heading() * self.INITIAL_SPEED
        '''v0 = source.velocity + (source.get_heading() * self.INITIAL_SPEED) #Photons inherit the player's momentum. When testing the game, we should try having a version where photons don't do this'''
        MovingBody.__init__(self, source.position, v0, world)

    def color(self):
        if self.player_one: #Player one is red
            return "#ffaaa1"
        return "#bcdcff"

    def update(self):
        MovingBody.update(self)
        self.age += 1
        if self.age >= self.LIFETIME:
            self.leave()
        else:
            targets = [a for a in self.world.agents if isinstance(a,Shootable)]
            for t in targets:
                if t.is_hit_by(self):
                    t.explode()
                    self.leave()
                    return

class Ship(Shootable):
    SHRAPNEL_CLASS  = Ember
    SHRAPNEL_PIECES = 8
    WORTH           = 1

    TURNS_IN_360   = 12
    IMPULSE_FRAMES = 4
    ACCELERATION   = 0.05
    MAX_SPEED      = 2.0

    START_X   = 5
    START_Y   = 5

    iFrames = 10 #Number of i-frames given to player after a shot. Meant to be used with something like "if self.shotTimer > (self.shootDelay - self.iFrames):"
    shootDelay = 20 #Delay between shots
    hpMax = 5 #Max health. Getting shot removes 1 health

    def __init__(self, world, player_one):
        self.player_one = player_one
        self.shotTimer = 0 #Players can shoot immediately after spawning
        self.hp = self.hpMax
        xoffset = -self.START_X if player_one else  self.START_X
        yoffset =  self.START_Y if player_one else -self.START_Y
        position0    = Point2D(xoffset, yoffset)
        velocity0    = Vector2D(0.0,0.0)
        self.speed   = 0.0
        self.angle   = 90.0
        self.impulse = 0
        radius = self.get_heading().magnitude()
        Shootable.__init__(self, position0, velocity0, radius, world)


    def color(self):
        if self.player_one: #Player one is red
            if self.shotTimer > (self.shootDelay - self.iFrames):
                return "#ffaaa1" #Players are a lighter color when invincible
            return "#f74830"
        else: #Player two is blue
            if self.shotTimer > (self.shootDelay - self.iFrames):
                return "#bcdcff"
            return "#3090f7"

    def get_heading(self):
        angle = self.angle * math.pi / 180.0
        return Vector2D(math.cos(angle), math.sin(angle))

    def turn_left(self):
        self.angle += 360.0 / self.TURNS_IN_360

    def turn_right(self):
        self.angle -= 360.0 / self.TURNS_IN_360

    def speed_up(self):
        self.impulse = self.IMPULSE_FRAMES

    def shoot(self):
        '''If need be, we can add self.player_one to the variables given to photon and then add code to it so that photons don't hit the player that created them '''
        if self.shotTimer == 0: #Prevent shooting too frequently
            Photon(self, self.world, self.player_one)
            self.shotTimer = self.shootDelay

    def update(self):
        if self.shotTimer > 0:
            self.shotTimer -= 1
        super().update()

    def shape(self):
        scale = 1.25 #Scale ship size
        h  = self.get_heading()
        hperp = h.perp()
        p1 = self.position + h * 1.5 * scale #making ships a little longer
        p2 = self.position + hperp * .5 * scale
        p3 = self.position - hperp * .5 * scale
        return [p1,p2,p3]

    def steer(self):
        if self.impulse > 0:
            self.impulse -= 1
            return self.get_heading() * self.ACCELERATION
        else:
            return Vector2D(0.0,0.0)

    def trim_physics(self):
        MovingBody.trim_physics(self)
        m = self.velocity.magnitude()
        if m > self.MAX_SPEED:
            self.velocity = self.velocity * (self.MAX_SPEED / m)
            self.impulse = 0

class PlayAsteroids(Game):

    DELAY_START      = 150
    MAX_ASTEROIDS    = 0 #Was 6. Wanted to stop asteroid spawning for testing. By the end of the project, we need to fully remove asteroid code.
    INTRODUCE_CHANCE = 0.01

    def __init__(self):
        Game.__init__(self,"ASTEROIDS!!!",60.0,45.0,800,600,topology='wrapped')

        self.number_of_asteroids = 0
        self.number_of_shrapnel = 0
        self.level = 1
        self.score = 0

        self.before_start_ticks = self.DELAY_START
        self.started = False

        self.ship_one = Ship(self, player_one=True)
        self.ship_two = Ship(self, player_one=False)

    def max_asteroids(self):
        return min(2 + self.level,self.MAX_ASTEROIDS)

    def handle_keypress(self,event):
        Game.handle_keypress(self,event)

        '''Player One controls: wasd + c to shoot '''
        if event.char == 'w':
            self.ship_one.speed_up()
        if event.char == 'a':
            self.ship_one.turn_left()
        elif event.char == 'd':
            self.ship_one.turn_right()
        if event.char == 'c':
            self.ship_one.shoot()

        '''Player Two controls: pl;' + , to shoot '''
        if event.char == 'p':
            self.ship_two.speed_up()
        if event.char == 'l':
            self.ship_two.turn_left()
        elif event.char == '\'':
            self.ship_two.turn_right()
        if event.char == ',':
            self.ship_two.shoot()

    def update(self):
        # Are we waiting to toss asteroids out?
        if self.before_start_ticks > 0:
            self.before_start_ticks -= 1
        else:
            self.started = True

        # Should we toss a new asteroid out?
        if self.started:
            tense = (self.number_of_asteroids >= self.max_asteroids())
            tense = tense or (self.number_of_shrapnel >= 2*self.level)
            if not tense and random.random() < self.INTRODUCE_CHANCE:
                LargeAsteroid(self)

        Game.update(self)

'''I don't know how useful the asteroid code is to us, but it's written so that there isn't any code that's needlessly repeated. The asteroid and shootable classes handle almost everything, while the child classes just specify the color, shrapnel pieces, and type of shrapnel. IDK how feasible it would be, but we could try to implement something similar with either powerups or with the photons our players will shoot (assuming that some powerups will change how the photons act) '''

'''
class Asteroid(Shootable):
    WORTH     = 5
    MIN_SPEED = 0.1
    MAX_SPEED = 0.3
    SIZE      = 3.0

    iFrames = 0 #Asteroids don't use these variables, but they're included to prevent crashes
    shootDelay = 0
    shotTimer = 0
    hp = 1

    def __init__(self, position0, velocity0, world):
        Shootable.__init__(self,position0, velocity0, self.SIZE, world)
        self.make_shape()

    def choose_velocity(self):
        return Vector2D.random() * random.uniform(self.MIN_SPEED,self.MAX_SPEED)

    def make_shape(self):
        angle = 0.0
        dA = 2.0 * math.pi / 15.0
        center = Point2D(0.0,0.0)
        self.polygon = []
        for i in range(15):
            if i % 3 == 0 and random.random() < 0.2:
                r = self.radius/2.0 + random.random() * 0.25
            else:
                r = self.radius - random.random() * 0.25
            dx = math.cos(angle)
            dy = math.sin(angle)
            angle += dA
            offset = Vector2D(dx,dy) * r
            self.polygon.append(offset)

    def shape(self):
        return [self.position + offset for offset in self.polygon]

class ParentAsteroid(Asteroid):
    def __init__(self,world):
        world.number_of_asteroids += 1
        velocity0 = self.choose_velocity()
        position0 = world.bounds.point_at(random.random(),random.random())
        if abs(velocity0.dx) >= abs(velocity0.dy):
            if velocity0.dx > 0.0:
                # LEFT SIDE
                position0.x = world.bounds.xmin
            else:
                # RIGHT SIDE
                position0.x = world.bounds.xmax
        else:
            if velocity0.dy > 0.0:
                # BOTTOM SIDE
                position0.y = world.bounds.ymin
            else:
                # TOP SIDE
                position0.y = world.bounds.ymax
        Asteroid.__init__(self,position0,velocity0,world)

    def explode(self):
        Asteroid.explode(self)
        self.world.number_of_asteroids -= 1

class ShrapnelAsteroid(Asteroid):
    def __init__(self, position0, world):
        world.number_of_shrapnel += 1
        velocity0 = self.choose_velocity()
        Asteroid.__init__(self, position0, velocity0, world)

    def explode(self):
        Asteroid.explode(self)
        self.world.number_of_shrapnel -= 1

class SmallAsteroid(ShrapnelAsteroid):
    WORTH           = 20
    MIN_SPEED       = Asteroid.MIN_SPEED * 2.0
    MAX_SPEED       = Asteroid.MAX_SPEED * 2.0
    SIZE            = Asteroid.SIZE / 2.0
    SHRAPNEL_CLASS  = Ember
    SHRAPNEL_PIECES = 8

    def color(self):
        return "#A8B0C0"

class MediumAsteroid(ShrapnelAsteroid):
    WORTH           = 10
    MIN_SPEED       = Asteroid.MIN_SPEED * math.sqrt(2.0)
    MAX_SPEED       = Asteroid.MAX_SPEED * math.sqrt(2.0)
    SIZE            = Asteroid.SIZE / math.sqrt(2.0)
    SHRAPNEL_CLASS  = SmallAsteroid
    SHRAPNEL_PIECES = 3

    def color(self):
        return "#7890A0"

class LargeAsteroid(ParentAsteroid):
    SHRAPNEL_CLASS  = MediumAsteroid
    SHRAPNEL_PIECES = 2

    def color(self):
        return "#9890A0"
'''

print("Player one (red): Press a and d to turn, w to create thrust, and c to shoot. \nPlayer two (blue): Press l and \' to turn, p to create thrust, and COMMA to shoot. \nPress q to quit.")
game = PlayAsteroids()
while not game.GAME_OVER:
    time.sleep(1.0/60.0)
    game.update()
