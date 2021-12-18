
/*
type Lobby = {
	name: string,
	playerIDs: [string]
	trialSelected: int (-1 - ~4)
	mods: [string]
}
*/

// import { v4 as uuidv4 } from 'uuid';


const lobbies = []
const lobbiesByPlayerID ={}
const playerMessagesQueue = {}

module.exports.initializePlayer = (playerID) => {
	playerMessagesQueue[playerID] = []
}
module.exports.endPlayer = (playerID) => {
	delete playerMessagesQueue[playerID]
	delete lobbiesByPlayerID[playerID]
}


module.exports.addLobby = (name, hostPlayerID, trial, mods) => {
	console.log('creating lobby ' + name)
	module.exports.initializePlayer(hostPlayerID)

	lobbies.push({
		name,
		playerIDs: [hostPlayerID],
		trialSelected: trial,
		mods
	})

	lobbiesByPlayerID[hostPlayerID] = lobbies[lobbies.length-1]
	return hostPlayerID
}

module.exports.addPlayerToLobby = (lobby, playerID) => {
	console.log('adding player to lobby ' + lobby.name)
	module.exports.initializePlayer(playerID)
	lobby.playerIDs.push(playerID)
	lobbiesByPlayerID[playerID] = lobby

	return playerID
}




module.exports.getLobbyByPlayerID = (playerID) => {
	return lobbiesByPlayerID[playerID]
}

module.exports.getLobbyByName = (name) => {
	const candidates = lobbies.filter(lobby => lobby.name === name)
	candidates.push(null)
	return candidates[0]
}

module.exports.lobbyNameTaken = (name) => {
	return module.exports.getLobbyByName(name) !== null
}

module.exports.getOtherPlayersByPlayerID = (playerID) => {
	const lobby = module.exports.getLobbyByPlayerID(playerID)
	if (!lobby) {
		return null
	}

	return lobby.playerIDs.filter(otherPlayerID => otherPlayerID !== playerID)
}








module.exports.closeLobby = (lobby) => {
	if (lobby) {
		console.log('Closing lobby ' + lobby.name)

		lobby.playerIDs.forEach(playerID => {
			module.exports.writeMessageToPlayer(playerID, 'd') // player disconnected message
			module.exports.removeConnection(playerID)
		})

		// lobbies.remove(lobby)
		const index = lobbies.indexOf(lobby);
		if (index > -1) {
			lobbies.splice(index, 1);
		}
	}
}

module.exports.closeLobbyByPlayerID = (playerID) => {
	module.exports.closeLobby(module.exports.getLobbyByPlayerID(playerID))
}




module.exports.sendMessageToLobbyFromPlayerID = (playerID, messageString) => {
	const players = module.exports.getOtherPlayersByPlayerID(playerID)
	if (players == null) {
		console.log('sending fail not in lobby')
		return ('nNot in lobby') // fail message
	}
	if (players.length == 0) {
		console.log('sending fail empty lobby')
		return ('nEmpty lobby') // fail message
	}

	console.log('forwarding to ' + players.length + ' connections')
	players.forEach(playerID => {
		module.exports.writeMessageToPlayer(playerID, messageString)
	})
	console.log('sending success message')
	return ('y') // success message
}

module.exports.writeMessageToPlayer = (playerID, message) => {
	console.log(`writing message to player:\n\tplayer:${playerID}\n\t${message}`)
	return playerMessagesQueue[playerID].push(message)
}

module.exports.getNextMessageForPlayer = (playerID) => {
	const messageQueue = playerMessagesQueue[playerID]
	if (messageQueue !== undefined && messageQueue.length > 0)
		return messageQueue.shift() 
	return ''
}