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


# helper functions
def retryRequest(tempserverlist, apicall):
    if len(tempserverlist)!=0:
        try:
            response = requests.get('{}api/{}'.format(tempserverlist[0], apicall))
        except:
            tempserverlist.pop(0)
            return retryRequest(tempserverlist, apicall)
        else:
            if response.status_code == 200:
                return json.loads(response.content)
            else:
                tempserverlist.pop(0)
                return retryRequest(tempserverlist, apicall)
    else:
        logger.error("None of the APIs are responding for the call {}".format(apicall))
        sys.exit(0)


def multiRequest(apicall, net):
    testserverlist = ['http://0.0.0.0:9000/', 'https://testnet.flocha.in/', 'https://testnet-flosight.duckdns.org/']
    mainserverlist = ['http://0.0.0.0:9001/', 'https://livenet.flocha.in/', 'https://testnet-flosight.duckdns.org/']
    if net == 'mainnet':
        return retryRequest(mainserverlist, apicall)
    elif net == 'testnet':
        return retryRequest(testserverlist, apicall)


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
        return jsonify(result='error', description='token doesn\'t exist')
    c.execute('SELECT * FROM transactionHistory WHERE id=1')
    incorporationRow = c.fetchall()[0]
    c.execute('SELECT COUNT (DISTINCT address) FROM activeTable')
    numberOf_distinctAddresses = c.fetchall()[0][0]
    c.execute('select max(id) from transactionHistory')
    numberOf_transactions = c.fetchall()[0][0]
    c.execute(
        'select contractName, contractAddress, blockNumber, blockHash, transactionHash from tokenContractAssociation')
    associatedContracts = c.fetchall()
    conn.close()

    associatedContractList = []
    for item in associatedContracts:
        tempdict = {}
        item = list(item)
        tempdict['contractName'] = item[0]
        tempdict['contractAddress'] = item[1]
        tempdict['blockNumber'] = item[2]
        tempdict['blockHash'] = item[3]
        tempdict['transactionHash'] = item[4]
        associatedContractList.append(tempdict)

    return jsonify(result='ok', token=token, incorporationAddress=incorporationRow[1], tokenSupply=incorporationRow[3],
                   transactionHash=incorporationRow[6], blockchainReference=incorporationRow[7],
                   activeAddress_no=numberOf_distinctAddresses, totalTransactions = numberOf_transactions, associatedSmartContracts=associatedContractList)


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
        return jsonify(result='error', description='token doesn\'t exist')

    if senderFloAddress and not destFloAddress:
        if limit is None:
            c.execute('SELECT jsonData, parsedFloData FROM transactionHistory WHERE sourceFloAddress="{}" ORDER BY id DESC LIMIT 100'.format(senderFloAddress))
        else:
            c.execute('SELECT jsonData, parsedFloData FROM transactionHistory WHERE sourceFloAddress="{}" ORDER BY id DESC LIMIT {}'.format(senderFloAddress,limit))
    elif not senderFloAddress and destFloAddress:
        if limit is None:
            c.execute(
            'SELECT jsonData, parsedFloData FROM transactionHistory WHERE destFloAddress="{}" ORDER BY id DESC LIMIT 100'.format(
                destFloAddress))
        else:
            c.execute(
            'SELECT jsonData, parsedFloData FROM transactionHistory WHERE destFloAddress="{}" ORDER BY id DESC LIMIT {}'.format(
                destFloAddress, limit))
    elif senderFloAddress and destFloAddress:
        if limit is None:
            c.execute(
            'SELECT jsonData, parsedFloData FROM transactionHistory WHERE sourceFloAddress="{}" AND destFloAddress="{}" ORDER BY id DESC LIMIT 100'.format(
                senderFloAddress, destFloAddress))
        else:
            c.execute(
            'SELECT jsonData, parsedFloData FROM transactionHistory WHERE sourceFloAddress="{}" AND destFloAddress="{}" ORDER BY id DESC LIMIT {}'.format(
                senderFloAddress, destFloAddress, limit))

    else:
        if limit is None:
            c.execute(
            'SELECT jsonData, parsedFloData FROM transactionHistory ORDER BY id DESC LIMIT 100')
        else:
            c.execute(
            'SELECT jsonData, parsedFloData FROM transactionHistory ORDER BY id DESC LIMIT {}'.format(limit))
    transactionJsonData = c.fetchall()
    conn.close()
    rowarray_list = {}
    for row in transactionJsonData:
        temp = {}
        temp['transactionDetails'] = json.loads(row[0])
        temp['parseResult'] = json.loads(row[1])
        rowarray_list[temp['transactionDetails']['txid']] = temp
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
        return jsonify(result='error', description='token doesn\'t exist')
    c.execute('SELECT address,SUM(transferBalance) FROM activeTable GROUP BY address')
    addressBalances = c.fetchall()

    returnList = {}

    for address in addressBalances:
        returnList[address[0]] = address[1]

    return jsonify(result='ok', token=token, balances=returnList)


# FLO address APIs

@app.route('/api/v1.0/getFloAddressInfo', methods=['GET'])
async def getFloAddressInfo():
    floAddress = request.args.get('floAddress')

    if floAddress is None:
        return jsonify(result='error', description='floAddress hasn\'t been passed')

    dblocation = dbfolder + '/system.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()
        c.execute('select token from tokenAddressMapping where tokenAddress="{}"'.format(floAddress))
        tokenNames = c.fetchall()

        c.execute(f"select contractName, status, tokenIdentification, contractType, transactionHash, blockNumber, blockHash from activecontracts where contractAddress='{floAddress}'")
        incorporatedContracts = c.fetchall()

        if len(tokenNames) != 0:
            detailList = {}

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
                    detailList[token] = tempdict

        else:
            # Address is not associated with any token
            return jsonify(result='error', description='FLO address is not associated with any tokens')

        if len(incorporatedContracts) != 0:
            incorporatedSmartContracts = []
            for contract in incorporatedContracts:
                tempdict = {}
                tempdict['contractName'] = contract[0]
                tempdict['contractAddress'] = floAddress
                tempdict['status'] = contract[1]
                tempdict['tokenIdentification'] = contract[2]
                tempdict['contractType'] = contract[3]
                tempdict['transactionHash'] = contract[4]
                tempdict['blockNumber'] = contract[5]
                tempdict['blockHash'] = contract[6]
                incorporatedSmartContracts.append(tempdict)

            return jsonify(result='ok', floAddress=floAddress, floAddressBalances=detailList, incorporatedSmartContracts=incorporatedContracts)
        else:
            return jsonify(result='ok', floAddress=floAddress, floAddressBalances=detailList,
                           incorporatedSmartContracts=None)


@app.route('/api/v1.0/getFloAddressBalance', methods=['GET'])
async def getAddressBalance():
    floAddress = request.args.get('floAddress')
    token = request.args.get('token')

    if floAddress is None:
        return jsonify(result='error', description='floAddress hasn\'t been passed')

    if token is None:
        dblocation = dbfolder + '/system.db'
        if os.path.exists(dblocation):
            conn = sqlite3.connect(dblocation)
            c = conn.cursor()
            c.execute('select token from tokenAddressMapping where tokenAddress="{}"'.format(floAddress))
            tokenNames = c.fetchall()

            if len(tokenNames) != 0:
                detailList = {}

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
                        detailList[token] = tempdict

                return jsonify(result='ok', floAddress=floAddress, floAddressBalances=detailList)

            else:
                # Address is not associated with any token
                return jsonify(result='error', description='FLO address is not associated with any tokens')
    else:
        dblocation = dbfolder + '/tokens/' + str(token) + '.db'
        if os.path.exists(dblocation):
            conn = sqlite3.connect(dblocation)
            c = conn.cursor()
        else:
            return jsonify(result='error', description='token doesn\'t exist')
        c.execute('SELECT SUM(transferBalance) FROM activeTable WHERE address="{}"'.format(floAddress))
        balance = c.fetchall()[0][0]
        conn.close()
        return jsonify(result='ok', token=token, floAddress=floAddress, balance=balance)


@app.route('/api/v1.0/getFloAddressTransactions', methods=['GET'])
async def getFloAddressTransactions():
    floAddress = request.args.get('floAddress')
    token = request.args.get('token')
    limit = request.args.get('limit')

    if floAddress is None:
        return jsonify(result='error', description='floAddress has not been passed')

    if token is None:
        dblocation = dbfolder + '/system.db'
        if os.path.exists(dblocation):
            conn = sqlite3.connect(dblocation)
            c = conn.cursor()
            c.execute('select token from tokenAddressMapping where tokenAddress="{}"'.format(floAddress))
            tokenNames = c.fetchall()
    else:
        dblocation = dbfolder + '/tokens/' + str(token) + '.db'
        if os.path.exists(dblocation):
            tokenNames = [[str(token),]]
        else:
            return jsonify(result='error', description='token doesn\'t exist')


    if len(tokenNames) != 0:
        allTransactionList = {}

        for tokenname in tokenNames:
            tokenname = tokenname[0]
            dblocation = dbfolder + '/tokens/' + str(tokenname) + '.db'
            if os.path.exists(dblocation):
                tempdict = {}
                conn = sqlite3.connect(dblocation)
                c = conn.cursor()
                if limit is None:
                    c.execute('SELECT jsonData, parsedFloData FROM transactionHistory WHERE sourceFloAddress="{}" OR destFloAddress="{}" ORDER BY id DESC LIMIT 100'.format(floAddress, floAddress))
                else:
                    c.execute('SELECT jsonData, parsedFloData FROM transactionHistory WHERE sourceFloAddress="{}" OR destFloAddress="{}" ORDER BY id DESC LIMIT {}'.format(floAddress, floAddress, limit))
                transactionJsonData = c.fetchall()
                conn.close()

                for row in transactionJsonData:
                    temp = {}
                    temp['transactionDetails'] = json.loads(row[0])
                    temp['parseResult'] = json.loads(row[1])
                    allTransactionList[temp['transactionDetails']['txid']] = temp

        if token is None:
            return jsonify(result='ok', floAddress=floAddress, transactions=allTransactionList)
        else:
            return jsonify(result='ok', floAddress=floAddress, transactions=allTransactionList, token=token)
    else:
        return jsonify(result='error', description='No token transactions present present on this address')


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
            contractDict['tokenIdentification'] = contract[4]
            contractDict['contractType'] = contract[5]
            contractDict['transactionHash'] = contract[6]
            contractDict['blockNumber'] = contract[7]
            contractDict['incorporationDate'] = contract[8]
            if contract[9]:
                contractDict['expiryDate'] = contract[9]
            if contract[10]:
                contractDict['closeDate'] = contract[10]

            contractList.append(contractDict)

    elif contractName and not contractAddress:
        c.execute('select * from activecontracts where contractName="{}"'.format(contractName))
        allcontractsDetailList = c.fetchall()
        for idx, contract in enumerate(allcontractsDetailList):
            contractDict = {}
            contractDict['contractName'] = contract[1]
            contractDict['contractAddress'] = contract[2]
            contractDict['status'] = contract[3]
            contractDict['tokenIdentification'] = contract[4]
            contractDict['contractType'] = contract[5]
            contractDict['transactionHash'] = contract[6]
            contractDict['blockNumber'] = contract[7]
            contractDict['incorporationDate'] = contract[8]
            if contract[9]:
                contractDict['expiryDate'] = contract[9]
            if contract[10]:
                contractDict['closeDate'] = contract[10]

            contractList.append(contractDict)

    elif not contractName and contractAddress:
        c.execute('select * from activecontracts where contractAddress="{}"'.format(contractAddress))
        allcontractsDetailList = c.fetchall()
        for idx, contract in enumerate(allcontractsDetailList):
            contractDict = {}
            contractDict['contractName'] = contract[1]
            contractDict['contractAddress'] = contract[2]
            contractDict['status'] = contract[3]
            contractDict['tokenIdentification'] = contract[4]
            contractDict['contractType'] = contract[5]
            contractDict['transactionHash'] = contract[6]
            contractDict['blockNumber'] = contract[7]
            contractDict['incorporationDate'] = contract[8]
            if contract[9]:
                contractDict['expiryDate'] = contract[9]
            if contract[10]:
                contractDict['closeDate'] = contract[10]

            contractList.append(contractDict)

    else:
        c.execute('select * from activecontracts')
        allcontractsDetailList = c.fetchall()
        for idx, contract in enumerate(allcontractsDetailList):
            contractDict = {}
            contractDict['contractName'] = contract[1]
            contractDict['contractAddress'] = contract[2]
            contractDict['status'] = contract[3]
            contractDict['tokenIdentification'] = contract[4]
            contractDict['contractType'] = contract[5]
            contractDict['transactionHash'] = contract[6]
            contractDict['blockNumber'] = contract[7]
            contractDict['incorporationDate'] = contract[8]
            if contract[9]:
                contractDict['expiryDate'] = contract[9]
            if contract[10]:
                contractDict['closeDate'] = contract[10]

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

        contractStructure = {}
        conditionDict = {}
        counter = 0
        for item in result:
            if list(item)[0] == 'exitconditions':
                conditionDict[counter] = list(item)[1]
                counter = counter + 1
            else:
                contractStructure[list(item)[0]] = list(item)[1]
        if len(conditionDict) > 0:
            contractStructure['exitconditions'] = conditionDict
        del counter, conditionDict

        returnval = contractStructure
        returnval['userChoice'] = contractStructure['exitconditions']
        returnval.pop('exitconditions')


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

        if returnval['status'] == 'closed':
            conn = sqlite3.connect(filelocation)
            c = conn.cursor()
            if returnval['contractType'] == 'one-time-event':
                # pull out trigger information
                # check if the trigger was succesful or failed
                c.execute(
                    f"select transactionType, transactionSubType from contractTransactionHistory where transactionType='trigger'")
                triggerntype = c.fetchall()

                if len(triggerntype) == 1:
                    triggerntype = list(triggerntype[0])

                    returnval['triggerType'] = triggerntype[1]

                    if 'userChoice' in returnval:
                        # Contract is of the type external trigger
                        if triggerntype[0]=='trigger' and triggerntype[1] is None:
                            # this is a normal trigger

                            # find the winning condition
                            c.execute('select userchoice from contractparticipants where winningAmount is not null limit 1')
                            returnval['winningChoice'] = c.fetchall()[0][0]
                            # find the winning participants
                            c.execute(
                                'select participantAddress, winningAmount from contractparticipants where winningAmount is not null')
                            winnerparticipants = c.fetchall()

                            returnval['numberOfWinners'] = len(winnerparticipants)

                else:
                    return jsonify(result='error', details='There is more than 1 trigger in the database for the smart contract. Please check your code, this shouldnt happen')


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
            'SELECT attribute,value FROM contractstructure')
        result = c.fetchall()

        contractStructure = {}
        conditionDict = {}
        counter = 0
        for item in result:
            if list(item)[0] == 'exitconditions':
                conditionDict[counter] = list(item)[1]
                counter = counter + 1
            else:
                contractStructure[list(item)[0]] = list(item)[1]
        if len(conditionDict) > 0:
            contractStructure['exitconditions'] = conditionDict
        del counter, conditionDict

        if 'exitconditions' in contractStructure:
            # contract is of the type external trigger
            # check if the contract has been closed
            c.execute('select * from contractTransactionHistory where transactionType="trigger"')
            trigger = c.fetchall()

            if len(trigger) == 1:
                c.execute(
                    'SELECT id,participantAddress, tokenAmount, userChoice, transactionHash, winningAmount FROM contractparticipants')
                result = c.fetchall()
                conn.close()
                returnval = {}
                for row in result:
                    returnval[row[1]] = {'participantFloAddress': row[1], 'tokenAmount': row[2], 'userChoice': row[3],
                                         'transactionHash': row[4], 'winningAmount': row[5]}

                return jsonify(result='ok', contractName=contractName, contractAddress=contractAddress,
                               participantInfo=returnval)
            elif len(trigger) == 0:
                c.execute(
                    'SELECT id,participantAddress, tokenAmount, userChoice, transactionHash FROM contractparticipants')
                result = c.fetchall()
                conn.close()
                returnval = {}
                for row in result:
                    returnval[row[1]] = {'participantFloAddress': row[1], 'tokenAmount': row[2], 'userChoice': row[3],
                                         'transactionHash': row[4]}

                return jsonify(result='ok', contractName=contractName, contractAddress=contractAddress,
                               participantInfo=returnval)
            else:
                return jsonify(result='error', description='More than 1 trigger present. This is unusual, please check your code')

        elif 'payeeAddress' in contractStructure:
            # contract is of the type internal trigger
            c.execute(
                'SELECT id,participantAddress, tokenAmount, userChoice, transactionHash FROM contractparticipants')
            result = c.fetchall()
            conn.close()
            returnval = {}
            for row in result:
                returnval[row[1]] = {'participantFloAddress': row[1], 'tokenAmount': row[2], 'userChoice': row[3],
                                     'transactionHash': row[4]}

            return jsonify(result='ok', contractName=contractName, contractAddress=contractAddress,
                           participantInfo=returnval)
    else:
        return jsonify(result='error', details='Smart Contract with the given name doesn\'t exist')


@app.route('/api/v1.0/getParticipantDetails', methods=['GET'])
async def getParticipantDetails():
    floAddress = request.args.get('floAddress')
    contractName = request.args.get('contractName')
    contractAddress = request.args.get('contractAddress')

    if floAddress is None:
        return jsonify(result='error', details='FLO address hasn\'t been passed')
    dblocation = os.path.join(dbfolder, 'system.db')

    if (contractName and contractAddress is None) or (contractName is None and contractAddress):
        return jsonify(result='error', details='pass both, contractName and contractAddress as url parameters')

    if os.path.isfile(dblocation):
        # Make db connection and fetch data
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()

        # Check if its a participant address
        queryString = f"SELECT id, address,contractName, contractAddress, tokenAmount, transactionHash, blockNumber, blockHash FROM contractAddressMapping where address='{floAddress}' and addressType='participant'"
        c.execute(queryString)
        result = c.fetchall()
        if len(result) != 0:
            participationDetailsList = []
            for row in result:
                detailsDict = {}
                detailsDict['contractName'] = row[2]
                detailsDict['contractAddress'] = row[3]
                detailsDict['tokenAmount'] = row[4]
                detailsDict['transactionHash'] = row[5]

                c.execute(f"select status, tokenIdentification, contractType, blockNumber, blockHash, incorporationDate, expiryDate, closeDate from activecontracts where contractName='{detailsDict['contractName']}' and contractAddress='{detailsDict['contractAddress']}'")
                temp = c.fetchall()
                detailsDict['status'] = temp[0][0]
                detailsDict['tokenIdentification'] = temp[0][1]
                detailsDict['contractType'] = temp[0][2]
                detailsDict['blockNumber'] = temp[0][3]
                detailsDict['blockHash'] = temp[0][4]
                detailsDict['incorporationDate'] = temp[0][5]
                if temp[0][6]:
                    detailsDict['expiryDate'] = temp[0][6]
                if temp[0][7]:
                    detailsDict['closeDate'] = temp[0][7]

                # check if the contract has been closed
                contractDbName = '{}-{}.db'.format(detailsDict['contractName'].strip(),
                                                   detailsDict['contractAddress'].strip())
                filelocation = os.path.join(dbfolder, 'smartContracts', contractDbName)
                if os.path.isfile(filelocation):
                    # Make db connection and fetch data
                    conn = sqlite3.connect(filelocation)
                    c = conn.cursor()
                    c.execute(
                        'SELECT attribute,value FROM contractstructure')
                    result = c.fetchall()

                    contractStructure = {}
                    conditionDict = {}
                    counter = 0
                    for item in result:
                        if list(item)[0] == 'exitconditions':
                            conditionDict[counter] = list(item)[1]
                            counter = counter + 1
                        else:
                            contractStructure[list(item)[0]] = list(item)[1]
                    if len(conditionDict) > 0:
                        contractStructure['exitconditions'] = conditionDict
                    del counter, conditionDict


                    if 'exitconditions' in contractStructure:
                        # contract is of the type external trigger
                        # check if the contract has been closed
                        c.execute('select * from contractTransactionHistory where transactionType="trigger"')
                        trigger = c.fetchall()

                        if detailsDict['status']=='closed':
                            c.execute(
                                f"SELECT userChoice, winningAmount FROM contractparticipants where participantAddress='{floAddress}'")
                            result = c.fetchall()
                            conn.close()
                            detailsDict['userChoice'] = result[0][0]
                            detailsDict['winningAmount'] = result[0][1]
                        else:
                            c.execute(
                                f"SELECT userChoice FROM contractparticipants where participantAddress='{floAddress}'")
                            result = c.fetchall()
                            conn.close()
                            detailsDict['userChoice'] = result[0][0]

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
        c.execute('select jsonData, parsedFloData from contractTransactionHistory')
        result = c.fetchall()
        conn.close()
        returnval = {}

        for item in result:
            temp = {}
            temp['transactionDetails'] = json.loads(item[0])
            temp['parseResult'] = json.loads(item[1])
            returnval[temp['transactionDetails']['txid']] = temp

        return jsonify(result='ok', contractName=contractName, contractAddress=contractAddress, contractTransactions=returnval)

    else:
        return jsonify(result='error', details='Smart Contract with the given name doesn\'t exist')


@app.route('/api/v1.0/getBlockDetails/<blockdetail>', methods=['GET'])
async def getblockdetails(blockdetail):

    if blockdetail.isdigit():
        blockHash = None
        blockHeight = int(blockdetail)
    else:
        blockHash = str(blockdetail)
        blockHeight = None

    # open the latest block database
    conn = sqlite3.connect(os.path.join(dbfolder, 'latestCache.db'))
    c = conn.cursor()

    if blockHash:
        c.execute(f"select jsonData from latestBlocks where blockHash='{blockHash}'")
    elif blockHeight:
        c.execute(f"select jsonData from latestBlocks where blockNumber='{blockHeight}'")

    blockJson = c.fetchall()
    if len(blockJson) != 0:
        blockJson = json.loads(blockJson[0][0])
        return jsonify(result='ok', blockDetails=blockJson)
    else:
        return jsonify(result='error', details='Block doesn\'t exist in database')


@app.route('/api/v1.0/getTransactionDetails/<transactionHash>', methods=['GET'])
async def gettransactiondetails(transactionHash):

    # open the latest block database
    conn = sqlite3.connect(os.path.join(dbfolder, 'latestCache.db'))
    c = conn.cursor()

    c.execute(f"select jsonData,parsedFloData from latestTransactions where transactionHash='{transactionHash}'")
    transactionJsonData = c.fetchall()

    if len(transactionJsonData) != 0:
        transactionJson = json.loads(transactionJsonData[0][0])
        parseResult = json.loads(transactionJsonData[0][1])

        return jsonify(parsedFloData=parseResult, transactionDetails=transactionJson, transactionHash=transactionHash, result='ok')
    else:
        return jsonify(result='error', details='Transaction doesn\'t exist in database')


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
        tempdict = {}
        for idx, item in enumerate(latestTransactions):
            item = list(item)
            tx_parsed_details = {}
            tx_parsed_details['transactionDetails'] = json.loads(item[3])
            tx_parsed_details['parsedFloData'] = json.loads(item[5])
            tx_parsed_details['parsedFloData']['transactionType'] = item[4]
            tx_parsed_details['transactionDetails']['blockheight'] = int(item[2])
            tempdict[json.loads(item[3])['txid']] = tx_parsed_details
    else:
        c.execute('''SELECT * FROM latestTransactions WHERE blockNumber IN (SELECT DISTINCT blockNumber FROM latestTransactions ORDER BY blockNumber DESC LIMIT 100) ORDER BY id ASC;''')
        latestTransactions = c.fetchall()
        c.close()
        tempdict = {}
        for idx, item in enumerate(latestTransactions):
            item = list(item)
            tx_parsed_details = {}
            tx_parsed_details['transactionDetails'] = json.loads(item[3])
            tx_parsed_details['parsedFloData'] = json.loads(item[5])
            tx_parsed_details['parsedFloData']['transactionType'] = item[4]
            tx_parsed_details['transactionDetails']['blockheight'] = int(item[2])
            tempdict[json.loads(item[3])['txid']] = tx_parsed_details
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
    tempdict = {}
    for idx, item in enumerate(latestBlocks):
        tempdict[json.loads(item[3])['hash']] = json.loads(item[3])
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
        contractDict['tokenIdentification'] = contract[4]
        contractDict['contractType'] = contract[5]
        contractDict['transactionHash'] = contract[6]
        contractDict['blockNumber'] = contract[7]
        contractDict['blockHash'] = contract[8]
        contractDict['incorporationDate'] = contract[9]
        if contract[10]:
            contractDict['expiryDate'] = contract[10]
        if contract[11]:
            contractDict['closeDate'] = contract[11]

        contractList.append(contractDict)

    return jsonify(tokens=filelist, smartContracts=contractList, result='ok')


@app.route('/api/v1.0/getSystemData', methods=['GET'])
async def systemData():

    # query for the number of flo addresses in tokenAddress mapping
    conn = sqlite3.connect(os.path.join(dbfolder, 'system.db'))
    c = conn.cursor()
    tokenAddressCount = c.execute('select count(distinct tokenAddress) from tokenAddressMapping').fetchall()[0][0]
    tokenCount = c.execute('select count(distinct token) from tokenAddressMapping').fetchall()[0][0]
    contractCount = c.execute('select count(distinct contractName) from contractAddressMapping').fetchall()[0][0]
    conn.close()

    # query for total number of validated blocks
    conn = sqlite3.connect(os.path.join(dbfolder, 'latestCache.db'))
    c = conn.cursor()
    validatedBlockCount = c.execute('select count(distinct blockNumber) from latestBlocks').fetchall()[0][0]
    validatedTransactionCount = c.execute('select count(distinct transactionHash) from latestTransactions').fetchall()[0][0]
    conn.close()

    return jsonify(systemAddressCount=tokenAddressCount, systemBlockCount=validatedBlockCount, systemTransactionCount=validatedTransactionCount , systemSmartContractCount=contractCount, systemTokenCount=tokenCount, result='ok')



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
