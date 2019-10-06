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

from os import listdir
from os.path import isfile, join


app = Quart(__name__)
app.clients = set()
app = cors(app, allow_origin="*")


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
    c.execute('select max(id) from transactionHistory')
    numberOf_transactions = c.fetchall()[0][0]
    conn.close()
    return jsonify(result='ok', token=token, incorporationAddress=incorporationRow[1], tokenSupply=incorporationRow[3],
                   transactionHash=incorporationRow[6], blockchainReference=incorporationRow[7],
                   activeAddress_no=numberOf_distinctAddresses, totalTransactions = numberOf_transactions)


@app.route('/api/v1.0/getTokenTransactions', methods=['GET'])
async def getTokenTransactions():
    token = request.args.get('token')
    senderFloAddress = request.args.get('senderFloAddress')
    destFloAddress = request.args.get('destFloAddress')
    limit = request.args.get('limit')


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
        if limit is None:
            c.execute('SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference, transactionHash FROM transactionHistory WHERE sourceFloAddress="{}" ORDER BY id DESC LIMIT 100'.format(senderFloAddress))
        else:
            c.execute('SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference, transactionHash FROM transactionHistory WHERE sourceFloAddress="{}" ORDER BY id DESC LIMIT {}'.format(senderFloAddress,limit))
    elif not senderFloAddress and destFloAddress:
        if limit is None:
            c.execute(
            'SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference, transactionHash FROM transactionHistory WHERE destFloAddress="{}" ORDER BY id DESC LIMIT 100'.format(
                destFloAddress))
        else:
            c.execute(
            'SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference, transactionHash FROM transactionHistory WHERE destFloAddress="{}" ORDER BY id DESC LIMIT {}'.format(
                destFloAddress, limit))
    elif senderFloAddress and destFloAddress:
        if limit is None:
            c.execute(
            'SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference, transactionHash FROM transactionHistory WHERE sourceFloAddress="{}" AND destFloAddress="{}" ORDER BY id DESC LIMIT 100'.format(
                senderFloAddress, destFloAddress))
        else:
            c.execute(
            'SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference, transactionHash FROM transactionHistory WHERE sourceFloAddress="{}" AND destFloAddress="{}" ORDER BY id DESC LIMIT {}'.format(
                senderFloAddress, destFloAddress, limit))


    else:
        if limit is None:
            c.execute(
            'SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference, transactionHash FROM transactionHistory ORDER BY id DESC LIMIT 100')
        else:
            c.execute(
            'SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference, transactionHash FROM transactionHistory ORDER BY id DESC LIMIT {}'.format(limit))
    latestTransactions = c.fetchall()
    conn.close()
    rowarray_list = []
    for row in latestTransactions:
        d = dict(zip(row.keys(), row))  # a dict with column names as keys
        rowarray_list.append(d)
    return jsonify(result='ok', token=token, transactions=rowarray_list)


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

    return jsonify(result='ok', token=token, balances=returnList)


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
    limit = request.args.get('limit')

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
            if limit is None:
                c.execute('SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference, transactionHash FROM transactionHistory ORDER BY id DESC LIMIT 100')
            else:
                c.execute('SELECT blockNumber, sourceFloAddress, destFloAddress, transferAmount, blockchainReference, transactionHash FROM transactionHistory ORDER BY id DESC LIMIT {}'.format(limit))
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
                d['transactionHash'] = row[5]
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

        return jsonify(result='ok', contractName=contractName, contractAddress=contractAddress, contractInfo=returnval)

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

        return jsonify(result='ok', contractName=contractName, contractAddress=contractAddress, participantInfo=returnval)

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


@app.route('/api/v1.0/getSmartContractTransactions', methods=['GET'])
async def getsmartcontracttransactions():
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
        c.execute('select transactionHash from contractparticipants')
        result = c.fetchall()
        conn.close()
        returnval = {}
        for i,row in enumerate(result):
            row = list(row)
            transactionDetails = requests.get('https://ranchimallflo.duckdns.org/api/v1.0/getTransactionDetails/{}'.format(row[0]))
            transactionDetails = json.loads(transactionDetails.content)
            returnval[i] = transactionDetails

        return jsonify(result='ok', contractName=contractName, contractAddress=contractAddress, contractTransactions=returnval)

    else:
        return jsonify(result='error', details='Smart Contract with the given name doesn\'t exist')


@app.route('/api/v1.0/getBlockDetails', methods=['GET'])
async def getblockdetails():
    blockHash = request.args.get('blockHash')
    blockHeight = request.args.get('blockHeight')

    if blockHash is None and blockHeight is None:
        return jsonify(result='error', details='Pass either blockHash or blockHeight')

    elif blockHash is not None and blockHeight is not None:
        return jsonify(result='error', details='Pass either blockHash or blockHeight. Not both.')
    elif blockHash:
        blockdetails = requests.get('{}block/{}'.format(apiUrl,blockHash))
        blockdetails = json.loads(blockdetails.content)
        return jsonify(blockDetails=blockdetails, blockHash=blockHash)
    elif blockHeight:
        blockhash = requests.get('{}block-index/{}'.format(apiUrl,blockHeight))
        blockhash = json.loads(blockhash.content)

        blockdetails = requests.get('{}block/{}'.format(apiUrl,blockhash['blockHash']))
        blockdetails = json.loads(blockdetails.content)
        return jsonify(blockDetails=blockdetails, blockHeight=blockHeight)


@app.route('/api/v1.0/getTransactionDetails/<transactionHash>', methods=['GET'])
async def gettransactiondetails(transactionHash):
    transactionDetails = requests.get('{}tx/{}'.format(apiUrl,transactionHash))
    transactionDetails = json.loads(transactionDetails.content)

    if (len(transactionDetails['vin'])!=1) and (len(transactionDetails['vout']) not in [1,2]):
        return jsonify(result='error', details='Transaction doesnt exist as part of the Token and Smart Contract system')

    flodata = transactionDetails['floData']

    blockdetails = requests.get('{}block/{}'.format(apiUrl,transactionDetails['blockhash']))
    blockdetails = json.loads(blockdetails.content)

    parseResult = parsing.parse_flodata(flodata, blockdetails)

    # now check what kind of transaction it is and if it exists in our database

    if parseResult["type"] == "noise":
        return jsonify(result='error', description='Transaction is of the type noise')

    elif parseResult["type"] == "tokenIncorporation":
        # open db of the token specified and check if the transaction exists there
        dblocation = os.path.join(dbfolder, 'tokens' , parseResult['tokenIdentification']+'.db')
        print(dblocation)

        if os.path.isfile(dblocation):
            # Make db connection and fetch data
            conn = sqlite3.connect(dblocation)
            c = conn.cursor()
            temp = c.execute('select transactionHash from transactionHistory where transactionHash="{}"'.format(transactionHash)).fetchall()

            if len(temp) == 0:
                return jsonify(result='error', details='Transaction doesnt exist as part of the Token and Smart Contract system')
            elif len(temp) > 1:
                return jsonify(result='error', details='More than 2 instances of this txid exists in the db. This is unusual, please report to the developers. https://github.com/ranchimall/floscout')


    elif parseResult["type"] == "transfer":
        if parseResult["transferType"] == "token":
            # open db of the token specified and check if the transaction exists there
            dblocation = os.path.join(dbfolder, 'tokens' , parseResult['tokenIdentification']+'.db')
            print(dblocation)

            if os.path.isfile(dblocation):
                # Make db connection and fetch data
                conn = sqlite3.connect(dblocation)
                c = conn.cursor()
                temp = c.execute('select transactionHash from transactionHistory where transactionHash="{}"'.format(transactionHash)).fetchall()

                if len(temp) == 0:
                    return jsonify(result='error', details='Transaction doesnt exist as part of the Token and Smart Contract system')
                elif len(temp) > 1:
                    return jsonify(result='error', details='More than 2 instances of this txid exists in the db. This is unusual, please report to the developers. https://github.com/ranchimall/floscout')

        elif parseResult["transferType"] == "smartContract":
            # find the address of smart contract
            contractAddress = None

            for voutItem in transactionDetails['vout']:
                if voutItem['scriptPubKey']['addresses'][0] != transactionDetails['vin'][0]['addr']:
                    contractAddress = voutItem['scriptPubKey']['addresses'][0];

            # open db of the contract specified and check if the transaction exists there
            dblocation = os.path.join(dbfolder, 'smartContracts' , parseResult['contractName'] + '-' + contractAddress + '.db')
            print(dblocation)

            if os.path.isfile(dblocation):
                # Make db connection and fetch data
                conn = sqlite3.connect(dblocation)
                c = conn.cursor()
                temp = c.execute('select transactionHash from contractparticipants where transactionHash="{}"'.format(transactionHash)).fetchall()

                if len(temp) == 0:
                    return jsonify(result='error', details='Transaction doesnt exist as part of the Token and Smart Contract system')
                elif len(temp) > 1:
                    return jsonify(result='error', details='More than 2 instances of this txid exists in the db. This is unusual, please report to the developers. https://github.com/ranchimall/floscout')

    elif parseResult["type"] == "smartContractIncorporation":
        print('smart contract incorporation')

    elif parseResult["type"] == "smartContractPays":
        print('smart contract pays')


    return jsonify(parsedFloData=parseResult, transactionDetails=transactionDetails, transactionHash=transactionHash, result='ok')


@app.route('/api/v1.0/getVscoutDetails', methods=['GET'])
async def getVscoutDetails():
    latestBlock = requests.get('{}blocks?limit=1'.format(apiUrl))
    latestBlock = json.loads(latestBlock)

    # get details of the last s4 blocks
    blockurl = '{}block/{}'.format(apiUrl,latestBlock["blocks"]['hash'])
    blockdetails = requests.get('{}block/{}'.format(apiUrl,latestBlock["blocks"]['hash']))
    block4details = json.loads(blockdetails)
    return jsonify(block4details)


@app.route('/api/v1.0/getLatestTransactionDetails', methods=['GET'])
async def getLatestTransactionDetails():

    numberOfLatestBlocks = request.args.get('numberOfLatestBlocks')

    dblocation = dbfolder + '/latestCache.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()
    else:
        return 'Latest transactions db doesn\'t exist. This is unusual, please report on https://github.com/ranchimall/ranchimallflo-api'

    if numberOfLatestBlocks is not None:
        c.execute('SELECT * FROM latestTransactions WHERE blockNumber IN (SELECT DISTINCT blockNumber FROM latestTransactions ORDER BY blockNumber DESC LIMIT {}) ORDER BY id ASC;'.format(int(numberOfLatestBlocks)))
        latestTransactions = c.fetchall()
        c.close()
        tempdict = []
        for idx, item in enumerate(latestTransactions):
            item = list(item)
            tx_parsed_details = {}
            tx_parsed_details['transactionDetails'] = json.loads(item[3])
            tx_parsed_details['parsedFloData'] = json.loads(item[5])
            tx_parsed_details['parsedFloData']['transactionType'] = item[4]
            tx_parsed_details['transactionDetails']['blockheight'] = int(item[2])
            tempdict.append(tx_parsed_details)
    else:
        c.execute('''SELECT * FROM latestTransactions WHERE blockNumber IN (SELECT DISTINCT blockNumber FROM latestTransactions ORDER BY blockNumber DESC LIMIT 100) ORDER BY id ASC;''')
        latestTransactions = c.fetchall()
        c.close()
        tempdict = []
        for idx, item in enumerate(latestTransactions):
            item = list(item)
            tx_parsed_details = {}
            tx_parsed_details['transactionDetails'] = json.loads(item[3])
            tx_parsed_details['parsedFloData'] = json.loads(item[5])
            tx_parsed_details['parsedFloData']['transactionType'] = item[4]
            tx_parsed_details['transactionDetails']['blockheight'] = int(item[2])
            tempdict.append(tx_parsed_details)
    return jsonify(result='ok', latestTransactions=tempdict)


@app.route('/api/v1.0/getLatestBlockDetails', methods=['GET'])
async def getLatestBlockDetails():

    limit = request.args.get('limit')

    dblocation = dbfolder + '/latestCache.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()
    else:
        return 'Latest transactions db doesn\'t exist. This is unusual, please report on https://github.com/ranchimall/ranchimallflo-api'

    if limit is None:
        c.execute('''SELECT * FROM ( SELECT * FROM latestBlocks ORDER BY blockNumber DESC LIMIT 4) ORDER BY id ASC;''')
    else:
        int(limit)
        c.execute('SELECT * FROM ( SELECT * FROM latestBlocks ORDER BY blockNumber DESC LIMIT {}) ORDER BY id ASC;'.format(limit))
    latestBlocks = c.fetchall()
    c.close()
    tempdict = []
    for idx, item in enumerate(latestBlocks):
        tempdict.append(json.loads(item[3]))
    return jsonify(result='ok', latestBlocks=tempdict)


@app.route('/api/v1.0/categoriseString/<urlstring>')
async def categoriseString(urlstring):

    # check if the hash is of a transaction
    response = requests.get('{}tx/{}'.format(apiUrl,urlstring))
    if response.status_code == 200:
        return jsonify(type='transaction')
    else:
        response = requests.get('{}block/{}'.format(apiUrl,urlstring))
        if response.status_code == 200:
            return jsonify(type='block')
        else:
            # check urlstring is a token name
            tokenfolder = os.path.join(dbfolder, 'tokens')
            onlyfiles = [f[:-3] for f in listdir(tokenfolder) if isfile(join(tokenfolder, f))]

            if urlstring.lower() in onlyfiles:
                return jsonify(type='token')
            else:
                contractfolder = os.path.join(dbfolder, 'system.db')
                conn = sqlite3.connect(contractfolder)
                conn.row_factory = lambda cursor, row: row[0]
                c = conn.cursor()
                contractList = c.execute('select contractname from activeContracts').fetchall()

                if urlstring.lower() in contractList:
                    return jsonify(type='smartContract')
                else:
                    return jsonify(type='noise')


@app.route('/api/v1.0/getTokenSmartContractList', methods=['GET'])
async def getTokenSmartContractList():
    # list of tokens
    filelist = []
    for item in os.listdir(os.path.join(dbfolder, 'tokens')):
        if os.path.isfile(os.path.join(dbfolder, 'tokens', item)):
            filelist.append(item[:-3])

    # list of smart contracts
    conn = sqlite3.connect(os.path.join(dbfolder, 'system.db'))
    c = conn.cursor()

    contractList = []

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

    return jsonify(tokens=filelist, smartContracts=contractList, result='ok')


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
    data = await request.get_json()
    for queue in app.clients:
        await queue.put(data['message'])
    return jsonify(True)


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
    app.run(debug=True,host='0.0.0.0', port=5009)
