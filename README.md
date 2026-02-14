# ARCADE MATRIX

Personal project to practice hdl with amaranth.

## What I have

* 12 8x8 Matrix displays, each driven by one MAX7219 with SPI. They are connected in a chain, so that the data shifts throughout all the ICs at each clock edge, until a load pin is set.

* 8 buttons in a matrix connexion: 2 columns (outputs) and 4 rows (inputs)
(I know it only saves 2 pins but it's only for fun). 4 buttons per player (up, down, left and right)

## Initial idea

* IP core to handle the SPI communication with the chain of ICs. Receives the data with a FIFO, and has registers to configure CPOL, CPHA, CLKDIV, WORDSIZE (maybe).

* IP core to handle the matrix keyboard and spit out the state of each button at any time.

* IP core to debounce the buttons (I still have to figure out if it has to go before or after the matrix keyboard IP core).

* IP core with the arcade game: receives the button data, and outputs information about the items in the screen. I'll try with the pong game first. The output will be the position of each player's bar and the ball.

* IP core that translates the output of the arcade game to matrix display. Maybe I could make it have memory about the state of the screen to know which lines of the matrices don't need to be updated, to speed up the screen writting.
