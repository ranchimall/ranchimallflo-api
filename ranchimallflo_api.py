from collections import defaultdict
import sqlite3
import json
import os
import requests

from quart import jsonify, make_response, Quart, render_template, request, flash, redirect, url_for
from quart import Quart
from quart_cors import cors
import asyncio
from typing import Optional

from pybtc import verify_signature
from config import *
import parsing


app = Quart(__name__)
app = cors(app)


# FLO TOKEN APIs

@app.route('/api/v1.0/getTokenList', methods=['GET'])
async def getTokenList():
    filelist = []
    for item in os.listdir(os.path.join(dbfolder, 'tokens')):
        if os.path.isfile(os.path.join(dbfolder, 'tokens', item)):
            filelist.append(item[:-3])

    return jsonify(tokens=filelist, result='ok')


@app.route('/api/v1.0/getTokenInfo', methods=['GET'])
async def getTokenInfo():
    token = request.args.get('token')

    if token is None:
        return jsonify(result='error')

    dblocation = dbfolder + '/tokens/' + str(token) + '.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()
    else:
        return 'Token doesn\'t exist'
    c.execute('SELECT * FROM transactionHistory WHERE id=1')
    incorporationRow = c.fetchall()[0]
    c.execute('SELECT COUNT (DISTINCT address) FROM activeTable')
    numberOf_distinctAddresses = c.fetchall()[0][0]
    conn.close()
    return jsonify(result='ok', token=token, incorporationAddress=incorporationRow[1], tokenSupply=incorporationRow[3],
                   transactionHash=incorporationRow[6], blockchainReference=incorporationRow[7],
                   activeAddress_no=numberOf_distinctAddresses)


@app.route('/api/v1.0/getTokenTransactions', methods=['GET'])
async def getTokenTransactions():
    token = request.args.get('token')
    senderFloAddress = request.args.get('senderFloAddress')
    destFloAddress = request.args.get('destFloAddress')

    if token is None:
        return jsonify(result='error')

    dblocation = dbfolder + '/tokens/' + str(token) + '.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
    else:
        return 'Token doesn\'t exist'

    if senderFloAddress and not destFloAddress:
        c.execute(
            'SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference FROM transactionHistory WHERE sourceFloAddress="{}" ORDER BY id DESC LIMIT 100'.format(
                senderFloAddress))
    elif not senderFloAddress and destFloAddress:
        c.execute(
            'SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference FROM transactionHistory WHERE destFloAddress="{}" ORDER BY id DESC LIMIT 100'.format(
                destFloAddress))
    elif senderFloAddress and destFloAddress:
        c.execute(
            'SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference FROM transactionHistory WHERE sourceFloAddress="{}" AND destFloAddress="{}" ORDER BY id DESC LIMIT 100'.format(
                senderFloAddress, destFloAddress))

    else:
        c.execute(
            'SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference FROM transactionHistory ORDER BY id DESC LIMIT 100')
    latestTransactions = c.fetchall()
    conn.close()
    rowarray_list = []
    for row in latestTransactions:
        d = dict(zip(row.keys(), row))  # a dict with column names as keys
        rowarray_list.append(d)
    return jsonify(result='ok', transactions=rowarray_list)


@app.route('/api/v1.0/getTokenBalances', methods=['GET'])
async def getTokenBalances():
    token = request.args.get('token')
    if token is None:
        return jsonify(result='error')

    dblocation = dbfolder + '/tokens/' + str(token) + '.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()
    else:
        return 'Token doesn\'t exist'
    c.execute('SELECT address,SUM(transferBalance) FROM activeTable GROUP BY address')
    addressBalances = c.fetchall()

    returnList = []

    for address in addressBalances:
        tempdict = {}
        tempdict['floAddress'] = address[0]
        tempdict['balance'] = address[1]
        returnList.append(tempdict)

    return jsonify(result='ok', balances=returnList)


@app.route('/api/v1.0/getFloAddressDetails', methods=['GET'])
async def getFloAddressDetails():
    floAddress = request.args.get('floAddress')

    if floAddress is None:
        return jsonify(result='error', description='floAddress hasn\'t been passed')

    dblocation = dbfolder + '/system.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()
        c.execute('select token from tokenAddressMapping where tokenAddress="{}"'.format(floAddress))
        tokenNames = c.fetchall()

        if len(tokenNames) != 0:
            detailList = []

            for token in tokenNames:
                token = token[0]
                dblocation = dbfolder + '/tokens/' + str(token) + '.db'
                if os.path.exists(dblocation):
                    tempdict = {}
                    conn = sqlite3.connect(dblocation)
                    c = conn.cursor()
                    c.execute('SELECT SUM(transferBalance) FROM activeTable WHERE address="{}"'.format(floAddress))
                    balance = c.fetchall()[0][0]
                    tempdict['balance'] = balance
                    tempdict['token'] = token
                    detailList.append(tempdict)

            return jsonify(result='ok', floAddress=floAddress, floAddressDetails=detailList)

        else:
            # Address is not associated with any token
            return jsonify(result='error', description='FLO address is not associated with any tokens')


@app.route('/api/v1.0/getFloAddressBalance', methods=['GET'])
async def getAddressBalance():
    floAddress = request.args.get('floAddress')
    token = request.args.get('token')

    if floAddress is None or token is None:
        return jsonify(result='error')

    dblocation = dbfolder + '/tokens/' + str(token) + '.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()
    else:
        return 'Token doesn\'t exist'
    c.execute('SELECT SUM(transferBalance) FROM activeTable WHERE address="{}"'.format(floAddress))
    balance = c.fetchall()[0][0]
    conn.close()
    return jsonify(result='ok', token=token, floAddress=floAddress, balance=balance)


@app.route('/api/v1.0/getFloAddressTransactions', methods=['GET'])
async def getAddressTransactions():
    floAddress = request.args.get('floAddress')

    if floAddress is None:
        return jsonify(result='error', description='floAddress has not been passed')

    dblocation = dbfolder + '/system.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
    c = conn.cursor()
    c.execute('select token from tokenAddressMapping where tokenAddress="{}"'.format(floAddress))
    tokenNames = c.fetchall()

    if len(tokenNames) != 0:
        allTransactionList = []

    for token in tokenNames:
        token = token[0]
        dblocation = dbfolder + '/tokens/' + str(token) + '.db'
        if os.path.exists(dblocation):
            tempdict = {}
            conn = sqlite3.connect(dblocation)
            c = conn.cursor()
            c.execute('SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference FROM transactionHistory ORDER BY id DESC LIMIT 100')
            latestTransactions = c.fetchall()
            conn.close()

            rowarray_list = []
            for row in latestTransactions:
                row = list(row)
                d = {}
                d['blockNumber'] = row[0]
                d['sourceFloAddress'] = row[1]
                d['destFloAddress'] = row[2]
                d['transferAmount'] = row[3]
                d['blockchainReference'] = row[4]
                rowarray_list.append(d)

            tempdict['token'] = token
            tempdict['transactions'] = rowarray_list
            allTransactionList.append(tempdict)

    return jsonify(result='ok', floAddress=floAddress, allTransactions=allTransactionList)


# SMART CONTRACT APIs

@app.route('/api/v1.0/getSmartContractList', methods=['GET'])
async def getContractList():
    contractName = request.args.get('contractName')
    contractAddress = request.args.get('contractAddress')

    conn = sqlite3.connect(os.path.join(dbfolder, 'system.db'))
    c = conn.cursor()

    contractList = []

    if contractName and contractAddress:
        c.execute('select * from activecontracts where contractName="{}" and contractAddress="{}"'.format(contractName, contractAddress))
        allcontractsDetailList = c.fetchall()
        for idx, contract in enumerate(allcontractsDetailList):
            contractDict = {}
            contractDict['contractName'] = contract[1]
            contractDict['contractAddress'] = contract[2]
            contractDict['status'] = contract[3]
            contractDict['transactionHash'] = contract[4]
            contractDict['incorporationDate'] = contract[5]
            if contract[6]:
                contractDict['expiryDate'] = contract[6]
            if contract[7]:
                contractDict['closeDate'] = contract[7]

            contractList.append(contractDict)

    elif contractName and not contractAddress:
        c.execute('select * from activecontracts where contractName="{}"'.format(contractName))
        allcontractsDetailList = c.fetchall()
        for idx, contract in enumerate(allcontractsDetailList):
            contractDict = {}
            contractDict['contractName'] = contract[1]
            contractDict['contractAddress'] = contract[2]
            contractDict['status'] = contract[3]
            contractDict['transactionHash'] = contract[4]
            contractDict['incorporationDate'] = contract[5]
            if contract[6]:
                contractDict['expiryDate'] = contract[6]
            if contract[7]:
                contractDict['closeDate'] = contract[7]

            contractList.append(contractDict)

    elif not contractName and contractAddress:
        c.execute('select * from activecontracts where contractAddress="{}"'.format(contractAddress))
        allcontractsDetailList = c.fetchall()
        for idx, contract in enumerate(allcontractsDetailList):
            contractDict = {}
            contractDict['contractName'] = contract[1]
            contractDict['contractAddress'] = contract[2]
            contractDict['status'] = contract[3]
            contractDict['transactionHash'] = contract[4]
            contractDict['incorporationDate'] = contract[5]
            if contract[6]:
                contractDict['expiryDate'] = contract[6]
            if contract[7]:
                contractDict['closeDate'] = contract[7]

            contractList.append(contractDict)

    else:
        c.execute('select * from activecontracts')
        allcontractsDetailList = c.fetchall()
        for idx, contract in enumerate(allcontractsDetailList):
            contractDict = {}
            contractDict['contractName'] = contract[1]
            contractDict['contractAddress'] = contract[2]
            contractDict['status'] = contract[3]
            contractDict['transactionHash'] = contract[4]
            contractDict['incorporationDate'] = contract[5]
            if contract[6]:
                contractDict['expiryDate'] = contract[6]
            if contract[7]:
                contractDict['closeDate'] = contract[7]

            contractList.append(contractDict)

    return jsonify(smartContracts=contractList, result='ok')


@app.route('/api/v1.0/getSmartContractInfo', methods=['GET'])
async def getContractInfo():
    contractName = request.args.get('contractName')
    contractAddress = request.args.get('contractAddress')

    if contractName is None:
        return jsonify(result='error', details='Smart Contract\'s name hasn\'t been passed')

    if contractAddress is None:
        return jsonify(result='error', details='Smart Contract\'s address hasn\'t been passed')

    contractDbName = '{}-{}.db'.format(contractName.strip(), contractAddress.strip())
    filelocation = os.path.join(dbfolder, 'smartContracts', contractDbName)

    if os.path.isfile(filelocation):
        # Make db connection and fetch data
        conn = sqlite3.connect(filelocation)
        c = conn.cursor()
        c.execute(
            'SELECT attribute,value FROM contractstructure')
        result = c.fetchall()

        returnval = {'userChoice': []}
        temp = 0
        for row in result:
            if row[0] == 'exitconditions':
                if temp == 0:
                    returnval["userChoice"] = [row[1]]
                    temp = temp + 1
                else:
                    returnval['userChoice'].append(row[1])
                continue
            returnval[row[0]] = row[1]

        c.execute('select count(participantAddress) from contractparticipants')
        noOfParticipants = c.fetchall()[0][0]
        returnval['numberOfParticipants'] = noOfParticipants

        c.execute('select sum(tokenAmount) from contractparticipants')
        totalAmount = c.fetchall()[0][0]
        returnval['tokenAmountDeposited'] = totalAmount
        conn.close()

        conn = sqlite3.connect(os.path.join(dbfolder, 'system.db'))
        c = conn.cursor()
        c.execute('select status, incorporationDate, expiryDate, closeDate from activecontracts where contractName=="{}" and contractAddress=="{}"'.format(contractName.strip(), contractAddress.strip()))
        results = c.fetchall()

        if len(results) == 1:
            for result in results:
                returnval['status'] = result[0]
                returnval['incorporationDate'] = result[1]
                if result[2]:
                    returnval['expiryDate'] = result[2]
                if result[3]:
                    returnval['closeDate'] = result[3]

        return jsonify(result='ok', contractInfo=returnval)

    else:
        return jsonify(result='error', details='Smart Contract with the given name doesn\'t exist')


@app.route('/api/v1.0/getSmartContractParticipants', methods=['GET'])
async def getcontractparticipants():
    contractName = request.args.get('contractName')
    contractAddress = request.args.get('contractAddress')

    if contractName is None:
        return jsonify(result='error', details='Smart Contract\'s name hasn\'t been passed')

    if contractAddress is None:
        return jsonify(result='error', details='Smart Contract\'s address hasn\'t been passed')

    contractDbName = '{}-{}.db'.format(contractName.strip(), contractAddress.strip())
    filelocation = os.path.join(dbfolder, 'smartContracts', contractDbName)

    if os.path.isfile(filelocation):
        # Make db connection and fetch data
        conn = sqlite3.connect(filelocation)
        c = conn.cursor()
        c.execute(
            'SELECT id,participantAddress, tokenAmount, userChoice, transactionHash, winningAmount FROM contractparticipants')
        result = c.fetchall()
        conn.close()
        returnval = {}
        for row in result:
            returnval[row[0]] = {'participantFloAddress': row[1], 'tokenAmount': row[2], 'userChoice': row[3], 'transactionHash': row[4], 'winningAmount': row[5]}

        return jsonify(result='ok', participantInfo=returnval)

    else:
        return jsonify(result='error', details='Smart Contract with the given name doesn\'t exist')


@app.route('/api/v1.0/getParticipantDetails', methods=['GET'])
async def getParticipantDetails():
    floAddress = request.args.get('floAddress')

    if floAddress is None:
        return jsonify(result='error', details='FLO address hasn\'t been passed')
    dblocation = os.path.join(dbfolder, 'system.db')

    print(dblocation)

    if os.path.isfile(dblocation):
        # Make db connection and fetch data
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()

        # Check if its a contract address
        c.execute("select contractAddress from activecontracts")
        activeContracts = c.fetchall()
        activeContracts = list(zip(*activeContracts))

        if floAddress in list(activeContracts[0]):
            c.execute("select contractName from activecontracts where contractAddress=='" + floAddress + "'")
            contract_names = c.fetchall()

            if len(contract_names) != 0:

                contractlist = []

                for contract_name in contract_names:
                    contractName = '{}-{}.db'.format(contract_name[0].strip(), floAddress.strip())
                    filelocation = os.path.join(dbfolder, 'smartContracts', contractName)

                    if os.path.isfile(filelocation):
                        # Make db connection and fetch data
                        conn = sqlite3.connect(filelocation)
                        c = conn.cursor()
                        c.execute(
                            'SELECT attribute,value FROM contractstructure')
                        result = c.fetchall()

                        returnval = {'exitconditions': []}
                        temp = 0
                        for row in result:
                            if row[0] == 'exitconditions':
                                if temp == 0:
                                    returnval["exitconditions"] = [row[1]]
                                    temp = temp + 1
                                else:
                                    returnval['exitconditions'].append(row[1])
                                continue
                            returnval[row[0]] = row[1]

                        c.execute('select count(participantAddress) from contractparticipants')
                        noOfParticipants = c.fetchall()[0][0]
                        returnval['numberOfParticipants'] = noOfParticipants

                        c.execute('select sum(tokenAmount) from contractparticipants')
                        totalAmount = c.fetchall()[0][0]
                        returnval['tokenAmountDeposited'] = totalAmount
                        conn.close()

                        contractlist.append(returnval)

                return jsonify(result='ok', floAddress=floAddress, type='contract', contractList=contractlist)

        # Check if its a participant address
        queryString = "SELECT id, participantAddress,contractName, contractAddress, tokenAmount, transactionHash FROM contractParticipantMapping where participantAddress=='" + floAddress + "'"
        c.execute(queryString)
        result = c.fetchall()
        conn.close()
        if len(result) != 0:
            participationDetailsList = []
            for row in result:
                detailsDict = {}
                detailsDict['contractName'] = row[2]
                detailsDict['contractAddress'] = row[3]
                detailsDict['tokenAmount'] = row[4]
                detailsDict['transactionHash'] = row[5]
                participationDetailsList.append(detailsDict)
            return jsonify(result='ok', floAddress=floAddress, type='participant', participatedContracts=participationDetailsList)
        else:
            return jsonify(result='error', details='Address hasn\'t participanted in any other contract')
    else:
        return jsonify(result='error', details='System error. System db is missing')


@app.route('/api/v1.0/getBlockDetails/<blockno>', methods=['GET'])
async def getblockdetails(blockno):
    blockhash = requests.get('https://flosight.duckdns.org/api/block-index/{}'.format(blockno))
    blockhash = json.loads(blockhash.content)

    blockdetails = requests.get('https://flosight.duckdns.org/api/block/{}'.format(blockhash['blockHash']))
    blockdetails = json.loads(blockdetails.content)

    return jsonify(blockdetails)


@app.route('/api/v1.0/getTransactionDetails/<transactionHash>', methods=['GET'])
async def gettransactiondetails(transactionHash):
    transactionDetails = requests.get('https://flosight.duckdns.org/api/tx/{}'.format(transactionHash))
    transactionDetails = json.loads(transactionDetails.content)

    flodata = transactionDetails['floData']

    blockdetails = requests.get('https://flosight.duckdns.org/api/block/{}'.format(transactionDetails['blockhash']))
    blockdetails = json.loads(blockdetails.content)

    parseResult = parsing.parse_flodata(flodata, blockdetails)
    return jsonify(parsingDetails=parseResult, transactionDetails=transactionDetails)


@app.route('/test')
async def test():
    return render_template('test.html')


class ServerSentEvent:

    def __init__(
            self,
            data: str,
            *,
            event: Optional[str]=None,
            id: Optional[int]=None,
            retry: Optional[int]=None,
    ) -> None:
        self.data = data
        self.event = event
        self.id = id
        self.retry = retry

    def encode(self) -> bytes:
        message = f"data: {self.data}"
        if self.event is not None:
            message = f"{message}\nevent: {self.event}"
        if self.id is not None:
            message = f"{message}\nid: {self.id}"
        if self.retry is not None:
            message = f"{message}\nretry: {self.retry}"
        message = f"{message}\r\n\r\n"
        return message.encode('utf-8')


@app.route('/', methods=['GET'])
async def index():
    return await render_template('index.html')


@app.route('/', methods=['POST'])
async def broadcast():
    signature = request.headers.get('Signature')
    data = await request.get_json()
    if verify_signature(signature.encode(), sse_pubKey, data['message'].encode()):
        for queue in app.clients:
            await queue.put(data['message'])
        return jsonify(True)
    else:
        return jsonify(False)


@app.route('/sse')
async def sse():
    queue = asyncio.Queue()
    app.clients.add(queue)

    async def send_events():
        while True:
            try:
                data = await queue.get()
                event = ServerSentEvent(data)
                yield event.encode()
            except asyncio.CancelledError as error:
                app.clients.remove(queue)

    response = await make_response(
        send_events(),
        {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Transfer-Encoding': 'chunked',
        },
    )
    response.timeout = None
    return response

if __name__ == "__main__":
    app.run(debug=True, port=5010)
