// Jank http architecture:
// 
// on connect to a lobby, the server sends 'y' and 'playerID'
// whenever the server wants to send a message to a player, it puts it in a queue for that player
// the cliet repeatedly pings the server with a 'get message for playerID' request
// if that client's queue is empty, the server responds with 'y - no new message', otherwise it just sends the message at the top of the queue 
// 



const express = require('express')
const bodyParser = require('body-parser')
const lobbies = require('./lobbies')
const app = express()
const port = 3000



// parse application/x-www-form-urlencoded
app.use(bodyParser.urlencoded({ extended: false }))
// parse application/json
app.use(bodyParser.json())
// parse application/vnd.api+json as json
app.use(bodyParser.json({ type: 'application/vnd.api+json' }))


app.get('/', (req, res) => {
	res.send('Hello World!')
})

app.post('/listen', (req, res) => {
	const playerID = req.query.playerID
	console.log('player ' + playerID + ' is listening')
	
	message = lobbies.getNextMessageForPlayer(playerID)
	if (message && message != "") {
		console.log('Retrieving message for ' + playerID)
		console.log('\t' + message)
	}

	res.send(message)
})

app.post('/', (req, res) => {
	// res.write('Hello World!!!')
	// console.log(req.body)
	// console.log(req.params)
	// console.log(req.query)

	// // console.log(req)
	// connections.push(res)

	// connections.forEach(response => response.write('hi'))








	const message = req.query.message || ""
	const playerID = req.query.playerID
	console.log('recieved ' + message.toString() + " from " + playerID)
	try {
		const messageString = message.toString()
		const messageType = messageString.charAt(0)

		console.log('processing ' + messageType + ' message')
		switch(messageType) {
		case 'h': // new lobby
			const l_messageBody = JSON.parse(messageString.substring(1))
			if (lobbies.getLobbyByPlayerID(playerID)) {
				res.send('nAlready in another lobby') // fail message
				break
			}
			if (lobbies.lobbyNameTaken(l_messageBody.name)) {
				res.send('nName taken') // fail message
				break
			}
			newPlayerID = lobbies.addLobby(l_messageBody.name, playerID, l_messageBody.trial, l_messageBody.mods.sort().join(','))
			console.log('sending success message')
			res.send('yLobby Created'+newPlayerID) // success message
			break
		case 'j': // connect to lobby
			const c_messageBody = JSON.parse(messageString.substring(1))
			const lobby = lobbies.getLobbyByName(c_messageBody.name)
			if (!lobby) {
				res.send('nNo lobby with name') // fail message
				break
			}
			if (lobbies.getLobbyByPlayerID(playerID)) {
				res.send('nAlready in another lobby') // fail message
				break
			}
			if (lobby.playerIDs.length >= 2) {
				res.send('nLobby full') // fail message
				break
			}
			if (lobby.mods !== c_messageBody.mods.sort().join(',')) {
				res.send('nMismatching modlist') // fail message
				break
			}

			newPlayerID = lobbies.addPlayerToLobby(lobby, playerID) // sends success message
			response = lobbies.sendMessageToLobbyFromPlayerID(playerID, 'c') // 'player connected'
			lobbies.writeMessageToPlayer(newPlayerID, response)
			res.send('yLobby Joined'+newPlayerID) // success message
			break

		case 'r': // game ready to start
			// host is expected to send something like:
			// s{"seed": 12345, "char_selected": 3, "turn_mode": 2, "sp_strat": 1}

			// client:
			// s{"char_selected": 3}
		case 's':
			// game start
		case 'm':
			// chat message
		case 'b':
			// in-game purchase action
		case 'a': // game action
			response = lobbies.sendMessageToLobbyFromPlayerID(playerID, messageString)
			lobbies.writeMessageToPlayer(newPlayerID, response)
			res.send(response)
			break
		}

	} catch (e) {
		console.error(e)

		try {
			res.send('nServer Error')
		} catch (e2) {
			console.error(e2)
		}
	}





})

app.listen(port, () => {
	console.log(`Example app listening at http://localhost:${port}`)
})
