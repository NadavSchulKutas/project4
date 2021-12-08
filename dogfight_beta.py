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
    is_powerup = False

    def __init__(self, position0, velocity0, radius, world):
        self.radius = radius
        self.has_Shield = False
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
        if not self.has_Shield:
            self.hp -= 1
            if self.is_powerup == False:
                self.world.hpReport()
            if self.hp > 0: #If the shot doesn't kill, create some shrapnel (embers for ships, nothing for asteroids since they only have 1 hp)
                for x in range((self.hpMax - self.hp) * 2): #Produce more shrapnel as health decreases, always making at least one
                    self.SHRAPNEL_CLASS(self.position,self.world)
            else:
                if self.SHRAPNEL_CLASS == None:
                    '''Return None if the object doesn't create shrapnel when destroyed'''
                    return
                for x in range(self.SHRAPNEL_PIECES):
                    '''Otherwise, make objects in the object's shrapnel class at its position SHRAPNEL_PIECES number of times'''
                    self.SHRAPNEL_CLASS(self.position,self.world)
                self.leave()
        else:
            self.has_Shield = False

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
                    if t.is_powerup == True:
                        t.player_one = self.player_one
                    t.explode()
                    self.leave()
                    return

class Ship(Shootable):
    #Shootable variables
    hpMax = 7 #Max health. Getting shot removes 1 health. Players die when they are BELOW 0 health
    SHRAPNEL_CLASS  = Ember
    SHRAPNEL_PIECES = hpMax * 2 + 3 #Amount of shrapnel on kill is proportional to max health + a little extra
    iFrames = 10 #Number of i-frames given to player after a shot. Meant to be used with something like "if self.shotTimer > (self.shootDelay - self.iFrames):"
    shootDelay = 20 #Delay between shots

    #MovingBody variables
    START_X   = 5
    START_Y   = 5

    #Ship-exclusive variables
    #Turning Variables. Once we decide on keyboard movement these variables can be cleaned up
    TURNS_IN_360 = 20 #Currently Unused
    TURN_IMPULSE = 4 #How many impulse frames are added/subtracted for a turn input
    MAX_TURN = TURN_IMPULSE #Used, but redundant.
    TURN_MULTIPLIER = 4 #Used in determining how many degrees the ship should actually turn
    TURN_THRESHOLD = 6 #Unused

    THRUST_IMPULSE = 4 #previously IMPULSE_FRAMES
    ACCELERATION   = 0.05
    MAX_SPEED      = 2
    DRAG           = 0.05 #Amount of drag applied to a player who isn't inputting anything.
    SCALE = float(3) #Scale ship size

    def __init__(self, world, player_one):
        self.player_one = player_one
        self.shotTimer = 120 #Players can shoot two seconds after spawning
        self.hp = self.hpMax
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
        self.has_speedBoost = False
        self.has_Shield = False
        self.multiShot = 0 #Number of times the player will multishot
        self.times_multiShot = 0 #Counter to make sure that the player is multishotting the correct num of times

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
        if self.player_one == True:
            angle = self.angle * math.pi / 180.0
            return Vector2D(math.cos(angle), math.sin(angle))
        else:
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
        if self.lrImpulse < self.MAX_TURN: #Adds impulse if you aren't over the max impulse
            self.lrImpulse += self.TURN_IMPULSE
    def turn_right(self):
        #self.angle -= 360.0 / self.TURNS_IN_360
        if self.lrImpulse > 0:
            self.lrImpulse = 0
        if self.lrImpulse > -self.MAX_TURN:
            self.lrImpulse -= self.TURN_IMPULSE

    def speed_up(self):
        self.impulse = self.THRUST_IMPULSE

    def slow_down(self):
        self.velocity = self.velocity * (1 - self.DRAG)**2 #Apply a stronger drag to let players slow down

    def shoot(self): #The check for whether the player can shoot/resetting shotTimer is seperated from them actually shooting so that certain powerups let the player shoot multiple times without checks
        '''If need be, we can add self.player_one to the variables given to photon and then add code to it so that photons don't hit the player that created them '''
        if self.shotTimer == 0: #Prevent shooting too frequently
            self.shooting()
            self.times_multiShot = 0
            self.shotTimer = self.shootDelay
    def shooting(self):
        Photon(self, self.world, self.player_one, False)
        if self.has_reverseShot:
            Photon(self, self.world, self.player_one, True)

    def update(self):
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
        '''Turning:'''
        if self.lrImpulse > 0: #bring lrImpulse 1 closer to 0
            self.lrImpulse -= 1
        elif self.lrImpulse < 0:
            self.lrImpulse += 1

        self.angle += self.lrImpulse * self.TURN_MULTIPLIER #Change in angle slows down as ship loses lrImpulse
        '''if (self.lrImpulse**2)**0.5 <= self.TURN_THRESHOLD: #**2**0.5 makes sure that the number is always positive. Turn threshold sets a limit on how much you can turn in one frame, but still lets you have more impulse frames than the threshold.
            self.angle += self.lrImpulse * self.TURN_MULTIPLIER
        else:
            self.angle += (self.lrImpulse//self.MAX_TURN) * self.TURN_THRESHOLD * self.TURN_MULTIPLIER #(self.lrImpulse//self.MAX_TURN) will either be 1 or -1 depending on if lrImpulse is positive or negative '''

        '''Moving forward/Backwards:'''
        if self.has_speedBoost:
            speedboost = 2.0
        else:
            speedboost = 1.0
        if self.impulse > 0:
            self.impulse -= 1
            return self.get_heading() * self.ACCELERATION * speedboost * self.mBungee
        else:
            #return -self.velocity * self.DRAG * 2**-1 #if not accelerating, slow down ships equal to drag.
            return Vector2D(0.0,0.0)

    def trim_physics(self):
        MovingBody.trim_physics(self)
        m = self.velocity.magnitude()
        if m > self.MAX_SPEED:
            self.slow_down()

class PowerUp(Shootable):
    SCALE = 1 #size
    is_powerup = True
    COLOR = "#ffffff"

    #Shootable variables included to prevent errors within Shootable functions
    SHRAPNEL_CLASS  = Ember
    SHRAPNEL_PIECES = 2
    iFrames = 0
    shootDelay = 0
    shotTimer = 0
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
class SpeedBoost(PowerUp):
    COLOR = "#f9e79f"
    def explode(self):
        if self.player_one:
            self.world.ship_one.has_speedBoostShot = True
        else:
            self.world.ship_two.has_speedBoostShot = True
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
    COLOR = "#bb8fce"
    def explode(self):
        if self.player_one:
            self.world.ship_one.multiShot += 1
        else:
            self.world.ship_two.multiShot += 1
        super().explode()

class PlayDogfight(Game):
    MIN_DELAY = 180 #minimum delay before spawning a power-up
    MAX_DELAY = 800 #maximum delay before spawning a power-up
    DELAY_START = 0 #300 #Additional delay when game is started

    hpScale = 3 #Make the hp bars wider/narrower

    worldW = 60.0 #world width
    worldH = 45.0 #world height
    def __init__(self):
        Game.__init__(self,"Dogfight!",self.worldW,self.worldH,800,600,topology='wrapped',console_lines=5)

        self.before_powerup = self.DELAY_START #just wanna make this random
        self.powerup_started = False

        self.ship_one = Ship(self, player_one=True)
        self.ship_two = Ship(self, player_one=False)

        self.report("Player one (red): Press a and d to turn, w to accelerate, d to deccelerate, and c to shoot.")
        self.report("Player two (blue): Mouse to move and / to shoot.")
        self.report("Press q to quit.")
        self.report("[" + "█" *self.ship_one.hpMax*self.hpScale + "] VS [" + "█" *self.ship_one.hpMax*self.hpScale + "]")

    def hpReport(self):
        self.report()
        self.report()
        self.report("[" + " " *(self.ship_one.hpMax - self.ship_one.hp)*self.hpScale + "█" *self.ship_one.hp*self.hpScale + "] VS [" + "█" *self.ship_two.hp*self.hpScale + " " *(self.ship_two.hpMax - self.ship_two.hp)*self.hpScale + "]")
        if (self.ship_one.hp == 0):
            self.report("PLAYER TWO WINS!!!")
        if (self.ship_two.hp == 0):
            self.report("PLAYER ONE WINS!!!")
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

        '''Player Two Mouse Controls: Click to shoot NOT FUNCTIONING
        Game.handle_mouse_press(self, event)
        if self.mouse_down:
            self.ship_two.shoot()'''

        '''Player Two controls: pl;' + / to shoot'''
        if event.char == '/':
            self.ship_two.shoot()
        '''if event.char == 'p':
            self.ship_two.speed_up()
        elif event.char == ';':
            self.ship_two.slow_down()
        if event.char == 'l':
            self.ship_two.turn_left()
        elif event.char == '\'':
            self.ship_two.turn_right()'''

    def update(self):
        # Are we waiting to spawn power-ups?
        if self.before_powerup > 0:
            self.before_powerup -= 1
        elif self.powerup_started == False:
            self.powerup_started = True
            self.before_powerup = random.randint(self.MIN_DELAY, self.MAX_DELAY)
        else:
            spawnChoice = random.randint(1, 4)
            if spawnChoice == 1:
                ReverseLaser(self)
            if spawnChoice == 2:
                SpeedBoost(self)
            if spawnChoice == 3:
                MultiShot(self)
            if spawnChoice == 4:
                Shield(self)
            self.before_powerup = random.randint(self.MIN_DELAY, self.MAX_DELAY)

        Game.update(self)

game = PlayDogfight()
while not game.GAME_OVER:
    time.sleep(1.0/60.0)
    game.update()
