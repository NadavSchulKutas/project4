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
    is_powerup = False

    def __init__(self, position0, velocity0, radius, world):
        self.radius = radius
        self.has_Shield = False
        MovingBody.__init__(self, position0, velocity0, world)

    def is_hit_by(self, photon):
        if photon.player_one == self.player_one and self.is_powerup == False: #Players can't shoot themselves
            return False
        return ((self.position - photon.position).magnitude() < self.radius)

    def explode(self):
        if self.has_Shield:
            self.has_Shield = False
            #print("Shielded!") #Debugging
            self.SHRAPNEL_CLASS(self.position,self.world)
        else:
            self.hp -= 1
            if self.is_powerup == False:
                self.world.hpReport()
            if self.hp > 0: #If the shot doesn't kill, create some shrapnel (embers for ships, nothing for asteroids since they only have 1 hp)
                for x in range(self.hpMax - self.hp): #Produce more shrapnel as health decreases, always making at least one
                    self.SHRAPNEL_CLASS(self.position,self.world)
            else:
                if self.SHRAPNEL_CLASS == None:
                    '''Return None if the object doesn't create shrapnel when destroyed'''
                    return
                for x in range(self.SHRAPNEL_PIECES):
                    '''Otherwise, make objects in the object's shrapnel class at its position SHRAPNEL_PIECES number of times'''
                    self.SHRAPNEL_CLASS(self.position,self.world)
                self.world.ship_two.freeze_blue()
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
    LIFETIME      = 30 #Measured in tics, not distance travelled

    def __init__(self,source,world, player_one, reverse):
        if reverse:
            self.reversed = -1.0
        else:
            self.reversed = 1.0
        self.player_one = player_one
        self.age  = 0
        v0 = source.get_heading() * self.INITIAL_SPEED * self.reversed
        '''v0 = source.velocity + (source.get_heading() * self.INITIAL_SPEED) * self.reversed #Photons inherit the player's momentum. When testing the game, we should try having a version where photons don't do this'''
        MovingBody.__init__(self, source.position, v0, world)

    def color(self):
        if self.player_one: #Player one is red
            return "#ffaaa1"
        return "#93c5fc"

    def shape(self):
        if self.player_one:
            p1 = self.position + Vector2D( 0, 0.4)
            p2 = self.position + Vector2D(-0.4, 0)
            p3 = self.position + Vector2D(0,-0.4)
            p4 = self.position + Vector2D( 0.4,0)
            return [p1,p2,p3,p4]
        else:
            p1 = self.position + Vector2D( 0.125, 0.125)
            p2 = self.position + Vector2D(-0.125, 0.125)
            p3 = self.position + Vector2D(-0.125,-0.125)
            p4 = self.position + Vector2D( 0.125,-0.125)
            return [p1,p2,p3,p4]

    def update(self):
        MovingBody.update(self)
        self.age += 1
        if self.age >= self.LIFETIME:
            self.leave()
        else:
            targets = [a for a in self.world.agents if isinstance(a,Shootable)]
            for t in targets:
                if t.is_hit_by(self):
                    if t.is_powerup == True:
                        t.player_one = self.player_one
                    t.explode()
                    self.leave()
                    return

class Ship(Shootable):
    #Shootable variables
    hpMax = 15 #Max health. Getting shot removes 1 health. Players die when they are BELOW 0 health
    SHRAPNEL_CLASS  = Ember
    SHRAPNEL_PIECES = hpMax * 2 #Amount of shrapnel on kill is proportional to max health so that the hits before tge kill don't send out more shrapnel
    colorFrames = 10 #How long player color is changed after a shot.

    #MovingBody variables
    START_X   = 18
    START_Y   = 10

    #Ship-exclusive variables
    TURN_IMPULSE = 6 #How many impulse frames are added/subtracted for a turn input
    TURN_MULTIPLIER = 4 #Used in determining how many degrees the ship should actually turn
    THRUST_IMPULSE = 4 #previously IMPULSE_FRAMES
    ACCELERATION   = 0.05
    MAX_SPEED      = 2
    DRAG           = 0.05 #Amount of drag applied to a player who isn't inputting anything.

    def __init__(self, world, player_one):
        self.player_one = player_one
        self.shotTimer = 120 #Players can shoot two seconds after spawning
        self.shootDelay = 20 #Delay between shots
        if not self.player_one:
            self.hpMax = 5
        self.hp = self.hpMax
        self.SCALE = float(3) #Scale ship size
        if not self.player_one:
            self.SCALE = self.SCALE * 2.0/3.0
        xoffset = -self.START_X if player_one else  self.START_X
        yoffset =  self.START_Y if player_one else -self.START_Y
        position0    = Point2D(xoffset, yoffset)
        velocity0    = Vector2D(0.0,0.0)
        self.angle   = 90.0
        self.impulse = 0
        self.lrImpulse = 0
        self.mBungee = 1.0 #How much the ship will spring back to the mouse (like there's a bungee cord between them). 1 by default for non-mouse controls
        radius = 1.2 * self.SCALE #Hitboxes are circular. Since the ships are taller than they are wide, hitboxes will be slightly too short and wide. I tried to strike a balance between too big/small with 1.2, since the ship's length is 1.5
        Shootable.__init__(self, position0, velocity0, radius, world)

        '''Power-up variables'''
        self.has_reverseShot = False
        self.has_Shield = False
        self.multiShot = 0 #Number of times the player will multishot
        self.times_multiShot = 0 #Counter to make sure that the player is multishotting the correct num of times

    def color(self):
        if self.player_one: #Player one is red
            if self.has_Shield == True or self.shotTimer > (self.shootDelay - self.colorFrames):
                return "#ffaaa1" #Players are a lighter color when invincible
            return "#f74830"
        else: #Player two is blue
            if self.has_Shield == True or self.shotTimer > (self.shootDelay - self.colorFrames):
                return "#93c5fc"
            return "#2888ee"

    def freeze_blue(self): #Save the last position of the mouse when player 1 dies so that player 2 can be properly frozen
        self.freeze = Vector2D(self.world.mouse_position.x - self.position.x, self.world.mouse_position.y - self.position.y) #Draw a line between mouse at that moment and ship at that moment

    def get_heading(self):
        if self.player_one:
            angle = self.angle * math.pi / 180.0
            return Vector2D(math.cos(angle), math.sin(angle))
        else:
            if self.world.ship_one.hp == 0:
                mouseShip = self.freeze
            else: #Stop tracking the mouse position if player one has died
                mouseShip = Vector2D(self.world.mouse_position.x - self.position.x, self.world.mouse_position.y - self.position.y) #Draw a line between mouse and ship
            msMagnitude = mouseShip.magnitude()
            mouseShip = mouseShip * msMagnitude**-1 #makes the magnitude of the vector 1, which is necessary for other code to work because magnitude affects how large the ship is drawn.

            #Accelerate ship
            self.speed_up()
            self.mBungee = msMagnitude ** 0.5 #The further the mouse is from the ship, the faster it will move later in the code. The **0.5 is so that the ship doesn't go too fast and isn't too reactive.
            if self.velocity.magnitude() > self.MAX_SPEED: #I made my own speedcap because the existing one doesn't work
                self.slow_down()
            return mouseShip

    def turn_left(self):
        #self.angle += 360.0 / self.TURNS_IN_360
        if self.lrImpulse < 0: #Cancels turn in opposite direction
            self.lrImpulse = 0
        self.lrImpulse = self.TURN_IMPULSE
    def turn_right(self):
        #self.angle -= 360.0 / self.TURNS_IN_360
        if self.lrImpulse > 0:
            self.lrImpulse = 0
        self.lrImpulse = -self.TURN_IMPULSE

    def speed_up(self):
        self.impulse = self.THRUST_IMPULSE

    def slow_down(self):
        self.velocity = self.velocity * (1 - self.DRAG)**2 #Apply a stronger drag to let players slow down

    def shoot(self): #The check for whether the player can shoot/resetting shotTimer is seperated from them actually shooting so that multishot lets the player shoot multiple times without checks
        if self.shotTimer == 0 and self.world.ship_one.hp != 0 and self.world.ship_two.hp != 0: #Prevent shooting too frequently
            self.shooting()
            self.times_multiShot = 0
            self.shotTimer = self.shootDelay
    def shooting(self):
        Photon(self, self.world, self.player_one, False)
        if self.has_reverseShot:
            Photon(self, self.world, self.player_one, True)

    def update(self):
        if (float(self.hp) * 0.4 <= float(self.hpMax)):
            self.shootDelay = 10
        if self.shotTimer > 0:
            self.shotTimer -= 1
        if self.multiShot > 0 and self.shotTimer == self.shootDelay - 4 *(self.times_multiShot+1) and self.times_multiShot < self.multiShot:
            '''If the player has collected at least one multishot and it's been 4 frames since their last shot/multiShot and they haven't shot all of their multishots... '''
            self.shooting() #shoot once
            self.times_multiShot += 1 #increase the counter by one
        super().update()

    def shape(self):
        h  = self.get_heading()
        hperp = h.perp()
        p1 = self.position + h * 1.5 * self.SCALE #making ships a little longer
        p2 = self.position + hperp * .5 * self.SCALE
        p3 = self.position - hperp * .5 * self.SCALE
        return [p1,p2,p3]

    def steer(self):
        '''End of Game:'''
        if self.world.ship_one.hp == 0 or self.world.ship_two.hp == 0:
            self.slow_down()
            return Vector2D(0.0,0.0)

        '''Turning:'''
        if self.lrImpulse > 0: #bring lrImpulse 1 closer to 0
            self.lrImpulse -= 1
        elif self.lrImpulse < 0:
            self.lrImpulse += 1
        self.angle += self.lrImpulse * self.TURN_MULTIPLIER #Change in angle slows down as ship loses lrImpulse

        '''Moving forward/Backwards:'''
        if self.impulse > 0:
            self.impulse -= 1
            return self.get_heading() * self.ACCELERATION * self.mBungee
        else:
            #return -self.velocity * self.DRAG * 2**-1 #if not accelerating, slow down ships equal to drag.
            return Vector2D(0.0,0.0)

    def trim_physics(self):
        MovingBody.trim_physics(self)
        m = self.velocity.magnitude()
        if m > self.MAX_SPEED:
            self.slow_down()

class PowerUp(Shootable):
    SCALE = 1.25
    is_powerup = True
    COLOR = "#ffffff"

    #Shootable variables included to prevent errors within Shootable functions
    SHRAPNEL_CLASS  = Ember
    SHRAPNEL_PIECES = 2
    hp = 1

    def __init__(self, world):
        self.world = world
        self.START_X = random.randrange(-self.world.worldW//2.0, self.world.worldW//2.0) #spawn locations are a random coordinate in the world. Integer division used to avoid error in random.py
        self.START_Y = random.randrange(-self.world.worldH//2.0, self.world.worldH//2.0)
        position = Point2D(self.START_X, self.START_Y)
        radius = self.SCALE
        self.player_one = True

        Shootable.__init__(self, position, Vector2D(0.0,0.0), radius, world)

    def shape(self):
        p1 = self.position + Vector2D( 0.0, self.SCALE)
        p2 = self.position + Vector2D(-self.SCALE, 0.0)
        p3 = self.position + Vector2D(0.0,-self.SCALE)
        p4 = self.position + Vector2D( self.SCALE,0.0)
        return [p1,p2,p3,p4]

    def color(self):
        return self.COLOR
class ReverseLaser(PowerUp):
    COLOR = "#48c9b0"
    def explode(self):
        if self.player_one:
            self.world.ship_one.has_reverseShot = True
        else:
            self.world.ship_two.has_reverseShot = True
        super().explode()
class Shield(PowerUp):
    COLOR = "#e5e7e9"
    def explode(self):
        if self.player_one:
            self.world.ship_one.has_Shield = True
        else:
            self.world.ship_two.has_Shield = True
        super().explode()
class MultiShot(PowerUp):
    COLOR = "#ad4ad7"
    def explode(self):
        if self.player_one:
            self.world.ship_one.multiShot += 1
        else:
            self.world.ship_two.multiShot += 1
        super().explode()

class PlayDogfight(Game):
    MIN_DELAY = 90 #minimum delay before spawning a power-up
    MAX_DELAY = 400 #maximum delay before spawning a power-up

    hpScale = 3 #Make the hp bars wider/narrower

    worldW = 60.0 #world width
    worldH = 45.0 #world height
    def __init__(self):
        Game.__init__(self,"Dogfight!",self.worldW,self.worldH,800,600,topology='wrapped',console_lines=6)

        self.before_powerup = random.randint(self.MIN_DELAY, self.MAX_DELAY) #just wanna make this random

        self.ship_one = Ship(self, player_one=True)
        self.ship_two = Ship(self, player_one=False)

        self.report("Player one (red): Press a and d to turn, w to accelerate, d to deccelerate, and c to shoot.")
        self.report("Player two (blue): Mouse to move and ] to shoot.")
        self.report("Press q to quit.")
        self.report("Shoot the diamond-shaped power-ups to collect them.")
        self.report("[" + "█" *self.ship_one.hpMax*self.hpScale + "] VS [" + "█" *self.ship_two.hpMax*self.hpScale + "]")

    def hpReport(self):
        self.report()
        self.report()
        self.report("[" + " " *(self.ship_one.hpMax - self.ship_one.hp)*self.hpScale + "█" *self.ship_one.hp*self.hpScale + "] VS [" + "█" *self.ship_two.hp*self.hpScale + " " *(self.ship_two.hpMax - self.ship_two.hp)*self.hpScale + "]")
        if (self.ship_one.hp == 0):
            self.report("PLAYER TWO WINS!!!")
            self.report("Press q to quit.")
        if (self.ship_two.hp == 0):
            self.report("PLAYER ONE WINS!!!")
            self.report("Press q to quit.")
        self.report()
        self.report()

    def handle_keypress(self,event):
        Game.handle_keypress(self,event)

        '''Player One controls: wasd + c to shoot '''
        if event.char == 'w':
            self.ship_one.speed_up()
        elif event.char == 's':
            self.ship_one.slow_down()
        if event.char == 'a':
            self.ship_one.turn_left()
        elif event.char == 'd':
            self.ship_one.turn_right()
        if event.char == 'c':
            self.ship_one.shoot()

        '''Player Two controls: mouse to move (in get_heading) and ] to shoot'''
        if event.char == ']':
            self.ship_two.shoot()

    def update(self):
        # Are we waiting to spawn power-ups?
        if self.before_powerup > 0:
            self.before_powerup -= 1
        elif self.ship_one.hp != 0 and self.ship_two.hp != 0: #Don't spawn powerups if one player is dead
            spawnChoice = random.randint(1, 3)
            if spawnChoice == 1:
                ReverseLaser(self)
            if spawnChoice == 2:
                MultiShot(self)
            if spawnChoice == 3:
                Shield(self)
            self.before_powerup = random.randint(self.MIN_DELAY, self.MAX_DELAY)

        Game.update(self)

game = PlayDogfight()
while not game.GAME_OVER:
    time.sleep(1.0/60.0)
    game.update()
