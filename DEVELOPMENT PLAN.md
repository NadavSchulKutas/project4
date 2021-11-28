### Things to Add:
* Scoring (maybe look at PlayPong.py)
* Respawning
* Power-Ups (see "smart power-up spawning" below)
* ~~Hit detection~~
* ~~delay between shots~~
* ~~Shooting gives a couple i-frames~~

### Code "Features":
* No cap on acceleration (ignore for now)
* Because photon velocity is inherited, players moving fast enough can create photons that wrap around the screen and shoot them in the back

### Finalized Ideas:
* Two players each control a ship and fight each other. 
* Destroying the opponent scores you one point.
* The game is over once one player reaches a certain number of points (easy to adjust)

### Proposed Ideas:
* 11 points to win
* Maybe include some obstacles in the environment that block players/their shots.
  * If included, we could have a pool of level layouts with a random wone being chosen every round.
* **Smart power-up spawning**: Instead of being truly random, power-up spawns are affected by the game state. They tend to spawn between both players in a favorable position (a little closer) for the losing player. The worse a player is losing, the more underdog spawning comes into effect.
* Map border beings to shrink if a match has gone on for too long.
  * Alternatively (or additionally), power-ups always spawning near the middle should encourage aggression.
