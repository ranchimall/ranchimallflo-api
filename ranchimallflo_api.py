from collections import defaultdict
import sqlite3
import json
import os
import requests
import sys
import time
from datetime import datetime
from quart import jsonify, make_response, Quart, render_template, request, flash, redirect, url_for, send_file
from quart_cors import cors
import asyncio
from typing import Optional
from config import *
import parsing
import subprocess
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import pyflo
from operator import itemgetter
import pdb
import ast
import time

app = Quart(__name__)
app.clients = set()
app = cors(app, allow_origin="*")

# Global values and configg
internalTransactionTypes = [ 'tokenswapDepositSettlement', 'tokenswapParticipationSettlement', 'smartContractDepositReturn']

if net == 'mainnet':
    is_testnet = False
elif net == 'testnet':
    is_testnet = True


# Validation functionss
def check_flo_address(floaddress, is_testnet=False):
    return pyflo.is_address_valid(floaddress, testnet=is_testnet)

def check_integer(value):
    return str.isdigit(value)

# Helper functions
def retryRequest(tempserverlist, apicall):
    if len(tempserverlist) != 0:
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
        print("None of the APIs are responding for the call {}".format(apicall))
        sys.exit(0)


def multiRequest(apicall, net):
    testserverlist = ['http://0.0.0.0:9000/', 'https://testnet.flocha.in/', 'https://testnet-flosight.duckdns.org/']
    mainserverlist = ['http://0.0.0.0:9001/', 'https://livenet.flocha.in/', 'https://testnet-flosight.duckdns.org/']
    if net == 'mainnet':
        return retryRequest(mainserverlist, apicall)
    elif net == 'testnet':
        return retryRequest(testserverlist, apicall)


def blockdetailhelper(blockdetail):
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
    return blockJson

def transactiondetailhelper(transactionHash):
    # check if legit transaction hash
    # open the latest block database
    conn = sqlite3.connect(os.path.join(dbfolder, 'latestCache.db'))
    c = conn.cursor()
    c.execute(f"SELECT jsonData, parsedFloData, transactionType, db_reference FROM latestTransactions WHERE transactionHash='{transactionHash}'")
    transactionJsonData = c.fetchall()
    return transactionJsonData

def update_transaction_confirmations(transactionJson):
    url = f"{apiUrl}api/v1/tx/{transactionJson['txid']}"
    response = requests.get(url)
    if response.status_code == 200:
        response_data = response.json()
        transactionJson['confirmations'] = response_data['confirmations']
    return transactionJson

def smartcontract_morph_helper(smart_contracts):
    contractList = []
    for idx, contract in enumerate(smart_contracts):
        contractDict = {}
        contractDict['contractName'] = contract[1]
        contractDict['contractAddress'] = contract[2]
        contractDict['status'] = contract[3]
        contractDict['contractType'] = contract[5]
        if contractDict['contractType'] in ['continuous-event', 'continuos-event']:
            contractDict['contractSubType'] = 'tokenswap'
            accepting_selling_tokens = ast.literal_eval(contract[4])
            contractDict['acceptingToken'] = accepting_selling_tokens[0]
            contractDict['sellingToken'] = accepting_selling_tokens[1]
            contractStructure = fetchContractStructure(contractDict['contractName'], contractDict['contractAddress'])
            if contractStructure['pricetype'] == 'dynamic':
                # temp fix
                if 'oracle_address' in contractStructure.keys():
                    contractDict['oracle_address'] = contractStructure['oracle_address']
                    contractDict['price'] = fetch_dynamic_swap_price(contractStructure, {'time': datetime.now().timestamp()})
            else:
                contractDict['price'] = contractStructure['price']
        elif contractDict['contractType'] == 'one-time-event':
            contractDict['tokenIdentification'] = contract[4]
            # pull the contract structure
            contractStructure = fetchContractStructure(contractDict['contractName'], contractDict['contractAddress'])
            # compare
            if 'payeeAddress' in contractStructure.keys():
                contractDict['contractSubType'] = 'time-trigger'
            else:
                choice_list = []
                for obj_key in contractStructure['exitconditions'].keys():
                    choice_list.append(contractStructure['exitconditions'][obj_key])
                contractDict['userChoices'] = choice_list
                contractDict['contractSubType'] = 'external-trigger'
                contractDict['expiryDate'] = contract[9]
            contractDict['closeDate'] = contract[10]

        contractDict['transactionHash'] = contract[6]
        contractDict['blockNumber'] = contract[7]
        contractDict['incorporationDate'] = contract[8]
        contractList.append(contractDict)
    return contractList

def smartContractInfo_output(contractName, contractAddress, contractType, subtype):
    if contractType == 'continuos-event' and contractType == 'tokenswap':
        pass
    elif contractType == 'one-time-event' and contractType == 'userchoice':
        pass
    elif contractType == 'one-time-event' and contractType == 'timetrigger':
        pass

def return_smart_contracts(connection, contractName=None, contractAddress=None):
    # find all the contracts details
    if contractName and contractAddress:
        connection.execute("SELECT * FROM activecontracts WHERE id IN (SELECT max(id) FROM activecontracts GROUP BY contractName, contractAddress) AND contractName=? AND contractAddress=?", (contractName, contractAddress))
    elif contractName and not contractAddress:
        connection.execute("SELECT * FROM activecontracts WHERE id IN (SELECT max(id) FROM activecontracts GROUP BY contractName, contractAddress) AND contractName=?", (contractName,))
    elif not contractName and contractAddress:
        connection.execute("SELECT * FROM activecontracts WHERE id IN (SELECT max(id) FROM activecontracts GROUP BY contractName, contractAddress) AND contractAddress=?", (contractAddress,))
    else:
        connection.execute("SELECT * FROM activecontracts WHERE id IN (SELECT max(id) FROM activecontracts GROUP BY contractName, contractAddress)")
    
    smart_contracts = connection.fetchall()
    return smart_contracts

def create_database_connection(type, parameters=None):
    if type == 'token':
        filelocation = os.path.join(dbfolder, 'tokens', parameters['token_name'])
    elif type == 'smart_contract':
        contractDbName = '{}-{}.db'.format(parameters['contract_name'].strip(), parameters['contract_address'].strip())
        filelocation = os.path.join(dbfolder, 'smartContracts', contractDbName)
    elif type == 'system_dbs':
        filelocation = os.path.join(dbfolder, 'system.db')
    elif type == 'latest_cache':
        filelocation = os.path.join(dbfolder, 'latestCache.db')
    
    conn = sqlite3.connect(filelocation)
    c = conn.cursor()
    return [conn, c]

def fetchContractStructure(contractName, contractAddress):
    # Make connection to contract database
    contractDbName = '{}-{}.db'.format(contractName.strip(),contractAddress.strip())
    filelocation = os.path.join(dbfolder, 'smartContracts', contractDbName)
    if os.path.isfile(filelocation):
        # fetch from contractStructure
        conn = sqlite3.connect(filelocation)
        c = conn.cursor()
        c.execute('SELECT attribute,value FROM contractstructure')
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
        del counter, conditionDict, c
        conn.close()

        if 'contractAmount' in contractStructure:
            contractStructure['contractAmount'] = float(contractStructure['contractAmount'])
        if 'payeeAddress' in contractStructure:
            contractStructure['payeeAddress'] = json.loads(contractStructure['payeeAddress'])
        if 'maximumsubscriptionamount' in contractStructure:
            contractStructure['maximumsubscriptionamount'] = float(contractStructure['maximumsubscriptionamount'])
        if 'minimumsubscriptionamount' in contractStructure:
            contractStructure['minimumsubscriptionamount'] = float(contractStructure['minimumsubscriptionamount'])
        if 'price' in contractStructure:
            contractStructure['price'] = float(contractStructure['price'])
        return contractStructure
    else:
        return 0

def fetchContractStatus(contractName, contractAddress):
    conn, c = create_database_connection('system_dbs')
    # select status from the last instance of activecontracts where match contractName and contractAddress
    c.execute(f'SELECT status FROM activecontracts WHERE contractName="{contractName}" AND contractAddress="{contractAddress}" ORDER BY id DESC LIMIT 1')
    status = c.fetchall()
    if len(status)==0:
        return None
    else:
        return status[0][0]

def extract_ip_op_addresses(transactionJson):
    sender_address = transactionJson['vin'][0]['addresses'][0]
    receiver_address = None
    for utxo in transactionJson['vout']:
        if utxo['scriptPubKey']['addresses'][0] == sender_address:
            continue
        receiver_address = utxo['scriptPubKey']['addresses'][0]
    return sender_address, receiver_address

def updatePrices():
    prices = {}
    # USD -> INR
    response = requests.get(f"https://api.exchangerate-api.com/v4/latest/usd")
    price = response.json()
    prices['USDINR'] = price['rates']['INR']

    # Blockchain stuff : BTC,FLO -> USD,INR
    # BTC->USD | BTC->INR
    response = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,flo&vs_currencies=usd,inr")
    price = response.json()
    prices['BTCUSD'] = price['bitcoin']['usd']
    prices['BTCINR'] = price['bitcoin']['inr']

    # FLO->USD | FLO->INR
    response = requests.get(f"https://api.coinlore.net/api/ticker/?id=67")
    price = response.json()
    prices["FLOUSD"] = float(price[0]['price_usd'])
    prices["FLOINR"] = float(prices["FLOUSD"]) * float(prices['USDINR'])

    # 3. update latest price data
    print('Prices updated at time: %s' % datetime.now())
    print(prices)

    conn = sqlite3.connect('system.db')
    c = conn.cursor()
    for pair in list(prices.items()):
        pair = list(pair)
        c.execute(f"UPDATE ratepairs SET price={pair[1]} WHERE ratepair='{pair[0]}'")
    conn.commit()

def fetch_dynamic_swap_price(contractStructure, blockinfo):
    oracle_address = contractStructure['oracle_address']
    # fetch transactions from the blockchain where from address : oracle-address... to address: contract address
    # find the first contract transaction which adheres to price change format
    # {"price-update":{"contract-name": "", "contract-address": "", "price": 3}}
    print(f'oracle address is : {oracle_address}')
    response = requests.get(f'{apiUrl}api/v1/address/{oracle_address}?details=txs')
    if response.status_code == 200:
        response = response.json()
        if 'txs' not in response.keys(): # API doesn't return 'transactions' key, if 0 txs present on address
            return float(contractStructure['price'])
        else:
            transactions = response['txs']
            for transaction in transactions:
                #transaction_response = requests.get(f'{apiUrl}api/v1/tx/{transaction_hash}')
                # if transaction_response.status_code == 200:
                floData = transaction['floData']
                # If the blocktime of the transaction is < than the current block time
                if transaction['time'] < blockinfo['time']:
                    # Check if flodata is in the format we are looking for
                    # ie. {"price-update":{"contract-name": "", "contract-address": "", "price": 3}}
                    # and receiver address should be contractAddress
                    try:
                        sender_address, receiver_address = find_sender_receiver(transaction)
                        assert receiver_address == contractStructure['contractAddress']
                        assert sender_address == oracle_address
                        floData = json.loads(floData)
                        # Check if the contract name and address are right
                        assert floData['price-update']['contract-name'] == contractStructure['contractName']
                        assert floData['price-update']['contract-address'] == contractStructure['contractAddress']
                        return float(floData['price-update']['price'])
                    except:
                        continue
                else:
                    continue
                # else:
                #     print('API error while fetch_dynamic_swap_price')
                #     return None
            return float(contractStructure['price'])
    else:
        print('API error while fetch_dynamic_swap_price')
        return None

def find_sender_receiver(transaction_data):
    # Create vinlist and outputlist
    vinlist = []
    querylist = []

    #totalinputval = 0
    #inputadd = ''

    # todo Rule 40 - For each vin, find the feeding address and the fed value. Make an inputlist containing [inputaddress, n value]
    for vin in transaction_data["vin"]:
        vinlist.append([vin["addresses"][0], float(vin["value"])])

    totalinputval = float(transaction_data["valueIn"])

    # todo Rule 41 - Check if all the addresses in a transaction on the input side are the same
    for idx, item in enumerate(vinlist):
        if idx == 0:
            temp = item[0]
            continue
        if item[0] != temp:
            print(f"System has found more than one address as part of vin. Transaction {transaction_data['txid']} is rejected")
            return 0

    inputlist = [vinlist[0][0], totalinputval]
    inputadd = vinlist[0][0]

    # todo Rule 42 - If the number of vout is more than 2, reject the transaction
    if len(transaction_data["vout"]) > 2:
        print(f"System has found more than 2 address as part of vout. Transaction {transaction_data['txid']} is rejected")
        return 0

    # todo Rule 43 - A transaction accepted by the system has two vouts, 1. The FLO address of the receiver
    #      2. Flo address of the sender as change address.  If the vout address is change address, then the other adddress
    #     is the recevier address

    outputlist = []
    addresscounter = 0
    inputcounter = 0
    for obj in transaction_data["vout"]:
        if obj["scriptPubKey"]["isAddress"] == True:
            addresscounter = addresscounter + 1
            if inputlist[0] == obj["scriptPubKey"]["addresses"][0]:
                inputcounter = inputcounter + 1
                continue
            outputlist.append([obj["scriptPubKey"]["addresses"][0], obj["value"]])

    if addresscounter == inputcounter:
        outputlist = [inputlist[0]]
    elif len(outputlist) != 1:
        print(f"Transaction's change is not coming back to the input address. Transaction {transaction_data['txid']} is rejected")
        return 0
    else:
        outputlist = outputlist[0]

    return inputlist[0], outputlist[0]

def fetch_contract_status_time_info(contractName, contractAddress):
    conn, c = create_database_connection('system_dbs')
    c.execute('SELECT status, incorporationDate, expiryDate, closeDate FROM activecontracts WHERE contractName=="{}" AND contractAddress=="{}" ORDER BY id DESC LIMIT 1'.format(contractName, contractAddress))
    contract_status_time_info = c.fetchall()
    return contract_status_time_info

def checkIF_commitee_trigger_tranasaction(transactionDetails):
    if transactionDetails[3] == 'trigger':
        pass

def transaction_post_processing(transactionJsonData):
    rowarray_list = []

    for row in transactionJsonData:
        transactions_object = {}
        parsedFloData = json.loads(row[1])
        transactionDetails = json.loads(row[0])
            
        if row[3] in internalTransactionTypes or (row[3]=='trigger' and row[8]!='committee'):
            internal_info = {}
            internal_info['senderAddress'] = row[4]
            internal_info['receiverAddress'] = row[5]
            internal_info['tokenAmount'] = row[6]
            internal_info['tokenIdentification'] = row[7]
            internal_info['contractName'] = parsedFloData['contractName']
            internal_info['transactionTrigger'] = transactionDetails['txid']
            internal_info['time'] = transactionDetails['time']
            internal_info['type'] = row[3]
            internal_info['onChain'] = False
            transactions_object = internal_info
        else:
            transactions_object = {**parsedFloData, **transactionDetails}
            transactions_object = update_transaction_confirmations(transactions_object)
            transactions_object['onChain'] = True
        
        rowarray_list.append(transactions_object)

    return rowarray_list

def fetch_token_transactions(token, senderFloAddress=None, destFloAddress=None, limit=None, use_and=False):
    dblocation = dbfolder + '/tokens/' + str(token) + '.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
    else:
        return jsonify(description="Token doesn't exist"), 404

    # Build the base SQL query
    query = f"SELECT jsonData, parsedFloData, time, transactionType, sourceFloAddress, destFloAddress, transferAmount, '{token}' AS token, '' AS transactionSubType FROM transactionHistory"

    # Build the WHERE clause based on conditions
    conditions = []
    parameters = {}

    if senderFloAddress and not destFloAddress:
        conditions.append('sourceFloAddress=:sender_flo_address')
        parameters['sender_flo_address'] = senderFloAddress

    elif not senderFloAddress and destFloAddress:
        conditions.append('destFloAddress=:dest_flo_address')
        parameters['dest_flo_address'] = destFloAddress

    elif senderFloAddress and destFloAddress:
        if use_and:
            conditions.append('sourceFloAddress=:sender_flo_address AND destFloAddress=:dest_flo_address')
        else:
            conditions.append('sourceFloAddress=:sender_flo_address OR destFloAddress=:dest_flo_address')
        parameters['sender_flo_address'] = senderFloAddress
        parameters['dest_flo_address'] = destFloAddress

    # Add the WHERE clause if conditions exist
    if conditions:
        query += ' WHERE {}'.format(' AND '.join(conditions))

    # Add the LIMIT clause if specified
    if limit is not None:
        query += ' LIMIT :limit'
        parameters['limit'] = limit

    # Execute the query with parameters
    c.execute(query, parameters)
    transactionJsonData = c.fetchall()
    conn.close()
    return transaction_post_processing(transactionJsonData)

def fetch_contract_transactions(contractName, contractAddress, _from=0, to=100):
    sc_file = os.path.join(dbfolder, 'smartContracts', '{}-{}.db'.format(contractName, contractAddress))
    conn = sqlite3.connect(sc_file)
    c = conn.cursor()
    # Find token db names and attach
    contractStructure = fetchContractStructure(contractName, contractAddress)

    if contractStructure['contractType'] == 'continuos-event':
        token1 = contractStructure['accepting_token']
        token2 = contractStructure['selling_token']
        token1_file = f"{dbfolder}/tokens/{token1}.db"
        token2_file = f"{dbfolder}/tokens/{token2}.db"
        conn.execute(f"ATTACH DATABASE '{token1_file}' AS token1db")
        conn.execute(f"ATTACH DATABASE '{token2_file}' AS token2db")

        transaction_query = f'''
        SELECT t1.jsonData, t1.parsedFloData, t1.time, t1.transactionType, t1.sourceFloAddress, t1.destFloAddress, t1.transferAmount, '{token1}' AS token, s.transactionSubType  
        FROM main.contractTransactionHistory AS s 
        INNER JOIN token1db.transactionHistory AS t1 
        ON t1.transactionHash = s.transactionHash 
        UNION 
        SELECT t2.jsonData, t2.parsedFloData, t2.time, t2.transactionType, t2.sourceFloAddress, t2.destFloAddress, t2.transferAmount, '{token2}' AS token, s.transactionSubType 
        FROM main.contractTransactionHistory AS s 
        INNER JOIN token2db.transactionHistory AS t2 
        ON t2.transactionHash = s.transactionHash 
        WHERE s.id BETWEEN {_from} AND {to}
        '''

        creation_tx_query = '''
        SELECT jsonData, parsedFloData, time, transactionType, sourceFloAddress, destFloAddress, transferAmount, '' AS token, transactionSubType 
        FROM contractTransactionHistory
        ORDER BY id
        LIMIT 1;
        '''

    elif contractStructure['contractType'] == 'one-time-event':
        token1 = contractStructure['tokenIdentification']
        token1_file = f"{dbfolder}/tokens/{token1}.db"
        conn.execute(f"ATTACH DATABASE '{token1_file}' AS token1db")

        transaction_query = f'''
        SELECT t1.jsonData, t1.parsedFloData, t1.time, t1.transactionType, t1.sourceFloAddress, t1.destFloAddress, t1.transferAmount, '{token1}' AS token, s.transactionSubType 
        FROM main.contractTransactionHistory AS s 
        INNER JOIN token1db.transactionHistory AS t1 
        ON t1.transactionHash = s.transactionHash 
        WHERE s.id BETWEEN {_from} AND {to}
        '''

        creation_tx_query = '''
        SELECT jsonData, parsedFloData, time, transactionType, sourceFloAddress, destFloAddress, transferAmount, '' AS token, transactionSubType 
        FROM contractTransactionHistory
        ORDER BY id
        LIMIT 1;
        '''

    c.execute(transaction_query)
    transactionJsonData = c.fetchall()

    c.execute(creation_tx_query)
    creation_tx = c.fetchall()
    transactionJsonData = creation_tx + transactionJsonData

    return transaction_post_processing(transactionJsonData)


def fetch_swap_contract_transactions(contractName, contractAddress, transactionHash=None):
    sc_file = os.path.join(dbfolder, 'smartContracts', '{}-{}.db'.format(contractName, contractAddress))
    conn = sqlite3.connect(sc_file)
    c = conn.cursor()
    # Find token db names and attach
    contractStructure = fetchContractStructure(contractName, contractAddress)
    token1 = contractStructure['accepting_token']
    token2 = contractStructure['selling_token']
    token1_file = f"{dbfolder}/tokens/{token1}.db"
    token2_file = f"{dbfolder}/tokens/{token2}.db"
    conn.execute(f"ATTACH DATABASE '{token1_file}' AS token1db")
    conn.execute(f"ATTACH DATABASE '{token2_file}' AS token2db")
    
    # Get data from db
    query = f'''
    SELECT t1.jsonData, t1.parsedFloData, t1.time, t1.transactionType, t1.sourceFloAddress, t1.destFloAddress, t1.transferAmount, '{token1}' AS token, t1.transactionSubType 
    FROM main.contractTransactionHistory AS s 
    INNER JOIN token1db.transactionHistory AS t1 
    ON t1.transactionHash = s.transactionHash AND s.transactionHash = '{transactionHash}'
    UNION 
    SELECT t2.jsonData, t2.parsedFloData, t2.time, t2.transactionType, t2.sourceFloAddress, t2.destFloAddress, t2.transferAmount, '{token2}' AS token, t2.transactionSubType 
    FROM main.contractTransactionHistory AS s 
    INNER JOIN token2db.transactionHistory AS t2 
    ON t2.transactionHash = s.transactionHash AND s.transactionHash = '{transactionHash}' '''

    '''if transactionHash:
        query += f" WHERE s.transactionHash = '{transactionHash}'"'''
    
    try:
        c.execute(query)
    except:
        pass
    
    transactionJsonData = c.fetchall()   
    return transaction_post_processing(transactionJsonData)

def sort_transactions(transactionJsonData):
    transactionJsonData = sorted(transactionJsonData, key=lambda x: x['time'], reverse=True)
    return transactionJsonData

def process_committee_flodata(flodata):
    flo_address_list = []
    try:
        contract_committee_actions = flodata['token-tracker']['contract-committee']
    except KeyError:
        print('Flodata related to contract committee')
    else:
        # Adding first and removing later to maintain consistency and not to depend on floData for order of execution
        for action in contract_committee_actions.keys():
            if action == 'add':
                for floid in contract_committee_actions[f'{action}']:
                    flo_address_list.append(floid)

        for action in contract_committee_actions.keys():
            if action == 'remove':
                for floid in contract_committee_actions[f'{action}']:
                    flo_address_list.remove(floid)
    finally:
        return flo_address_list


def refresh_committee_list(admin_flo_id, api_url, blocktime):
    committee_list = []
    latest_param = 'true'
    mempool_param = 'false'
    init_id = None

    def process_transaction(transaction_info):
        if 'isCoinBase' in transaction_info or transaction_info['vin'][0]['addresses'][0] != admin_flo_id or transaction_info['blocktime'] > blocktime:
            return
        try:
            tx_flodata = json.loads(transaction_info['floData'])
            committee_list.extend(process_committee_flodata(tx_flodata))
        except:
            pass

    def send_api_request(url):
        response = requests.get(url, verify=API_VERIFY)
        if response.status_code == 200:
            return response.json()
        else:
            print('Response from the Flosight API failed')
            sys.exit(0)

    url = f'{api_url}api/v1/address/{admin_flo_id}?details=txs'
    response = send_api_request(url)
    for transaction_info in response.get('txs', []):
        process_transaction(transaction_info)

    while 'incomplete' in response:
        url = f'{api_url}api/v1/address/{admin_flo_id}/txs?latest={latest_param}&mempool={mempool_param}&before={init_id}'
        response = send_api_request(url)
        for transaction_info in response.get('items', []):
            process_transaction(transaction_info)
        if 'incomplete' in response:
            init_id = response['initItem']

    return committee_list


@app.route('/')
async def welcome_msg():
    return jsonify('Welcome to RanchiMall FLO Api v2')


@app.route('/api/v1.0/getSystemData', methods=['GET'])
async def systemData():
    # query for the number of flo addresses in tokenAddress mapping
    conn = sqlite3.connect(os.path.join(dbfolder, 'system.db'))
    c = conn.cursor()
    tokenAddressCount = c.execute('select count(distinct tokenAddress) from tokenAddressMapping').fetchall()[0][0]
    tokenCount = c.execute('select count(distinct token) from tokenAddressMapping').fetchall()[0][0]
    contractCount = c.execute('select count(distinct contractName) from contractAddressMapping').fetchall()[0][0]
    lastscannedblock = int(c.execute("select value from systemData where attribute=='lastblockscanned'").fetchall()[0][0])
    conn.close()

    # query for total number of validated blocks
    conn = sqlite3.connect(os.path.join(dbfolder, 'latestCache.db'))
    c = conn.cursor()
    validatedBlockCount = c.execute('select count(distinct blockNumber) from latestBlocks').fetchall()[0][0]
    validatedTransactionCount = c.execute('select count(distinct transactionHash) from latestTransactions').fetchall()[0][0]
    conn.close()
    return jsonify(systemAddressCount=tokenAddressCount, systemBlockCount=validatedBlockCount, systemTransactionCount=validatedTransactionCount, systemSmartContractCount=contractCount, systemTokenCount=tokenCount, lastscannedblock=lastscannedblock, result='ok')


@app.route('/api/v1.0/broadcastTx/<raw_transaction_hash>')
async def broadcastTx(raw_transaction_hash):
    p1 = subprocess.run(['flo-cli',f"-datadir={FLO_DATA_DIR}",'sendrawtransaction',raw_transaction_hash], capture_output=True)
    return jsonify(args=p1.args,returncode=p1.returncode,stdout=p1.stdout.decode(),stderr=p1.stderr.decode())


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
        return jsonify(result='error', description='token name hasnt been passed')
    
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
    c.execute('select contractName, contractAddress, blockNumber, blockHash, transactionHash from tokenContractAssociation')
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

    return jsonify(result='ok', token=token, incorporationAddress=incorporationRow[1], tokenSupply=incorporationRow[3], time=incorporationRow[6], blockchainReference=incorporationRow[7], activeAddress_no=numberOf_distinctAddresses, totalTransactions=numberOf_transactions, associatedSmartContracts=associatedContractList)


@app.route('/api/v1.0/getTokenTransactions', methods=['GET'])
async def getTokenTransactions():
    token = request.args.get('token')
    senderFloAddress = request.args.get('senderFloAddress')
    destFloAddress = request.args.get('destFloAddress')
    limit = request.args.get('limit')

    if token is None:
        return jsonify(result='error', description='token name hasnt been passed')
    
    dblocation = dbfolder + '/tokens/' + str(token) + '.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
    else:
        return jsonify(result='error', description='token doesn\'t exist')
    
    if senderFloAddress and not destFloAddress:
        if limit is None:
            c.execute('SELECT jsonData, parsedFloData FROM transactionHistory WHERE sourceFloAddress="{}" ORDER BY id DESC'.format(senderFloAddress))
        else:
            c.execute('SELECT jsonData, parsedFloData FROM transactionHistory WHERE sourceFloAddress="{}" ORDER BY id DESC LIMIT {}'.format(senderFloAddress, limit))
    elif not senderFloAddress and destFloAddress:
        if limit is None:
            c.execute('SELECT jsonData, parsedFloData FROM transactionHistory WHERE destFloAddress="{}" ORDER BY id DESC'.format(destFloAddress))
        else:
            c.execute('SELECT jsonData, parsedFloData FROM transactionHistory WHERE destFloAddress="{}" ORDER BY id DESC LIMIT {}'.format(destFloAddress, limit))
    elif senderFloAddress and destFloAddress:
        if limit is None:
            c.execute('SELECT jsonData, parsedFloData FROM transactionHistory WHERE sourceFloAddress="{}" AND destFloAddress="{}" ORDER BY id DESC'.format(senderFloAddress, destFloAddress))
        else:
            c.execute('SELECT jsonData, parsedFloData FROM transactionHistory WHERE sourceFloAddress="{}" AND destFloAddress="{}" ORDER BY id DESC LIMIT {}'.format(senderFloAddress, destFloAddress, limit))

    else:
        if limit is None:
            c.execute('SELECT jsonData, parsedFloData FROM transactionHistory ORDER BY id DESC')
        else:
            c.execute('SELECT jsonData, parsedFloData FROM transactionHistory ORDER BY id DESC LIMIT {}'.format(limit))
    transactionJsonData = c.fetchall()
    conn.close()
    rowarray_list = {}
    for row in transactionJsonData:
        transactions_object = {}
        transactions_object['transactionDetails'] = json.loads(row[0])
        transactions_object['transactionDetails'] = update_transaction_confirmations(transactions_object['transactionDetails'])
        transactions_object['parsedFloData'] = json.loads(row[1])
        rowarray_list[transactions_object['transactionDetails']['txid']] = transactions_object
    return jsonify(result='ok', token=token, transactions=rowarray_list)


@app.route('/api/v1.0/getTokenBalances', methods=['GET'])
async def getTokenBalances():
    token = request.args.get('token')
    if token is None:
        return jsonify(result='error', description='token name hasnt been passed')
    
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


# FLO Address APIs
@app.route('/api/v1.0/getFloAddressInfo', methods=['GET'])
async def getFloAddressInfo():
    floAddress = request.args.get('floAddress')
    if floAddress is None:
        return jsonify(description='floAddress hasn\'t been passed'), 400 
    
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
            return jsonify(result='ok', floAddress=floAddress, floAddressBalances=detailList, incorporatedSmartContracts=None)


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
            c.execute(
                'select token from tokenAddressMapping where tokenAddress="{}"'.format(floAddress))
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
        c.execute(
            'SELECT SUM(transferBalance) FROM activeTable WHERE address="{}"'.format(floAddress))
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
            c.execute('SELECT token FROM tokenAddressMapping WHERE tokenAddress="{}"'.format(floAddress))
            tokenNames = c.fetchall()
    else:
        dblocation = dbfolder + '/tokens/' + str(token) + '.db'
        if os.path.exists(dblocation):
            tokenNames = [[str(token), ]]
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
                    c.execute('SELECT jsonData, parsedFloData FROM transactionHistory WHERE sourceFloAddress="{}" OR destFloAddress="{}" ORDER BY id DESC'.format(floAddress, floAddress))
                else:
                    c.execute('SELECT jsonData, parsedFloData FROM transactionHistory WHERE sourceFloAddress="{}" OR destFloAddress="{}" ORDER BY id DESC LIMIT {}'.format(floAddress, floAddress, limit))
                transactionJsonData = c.fetchall()
                conn.close()

                for row in transactionJsonData:
                    transactions_object = {}
                    transactions_object['transactionDetails'] = json.loads(row[0])
                    transactions_object['transactionDetails'] = update_transaction_confirmations(transactions_object['transactionDetails'])
                    transactions_object['parsedFloData'] = json.loads(row[1])
                    allTransactionList[transactions_object['transactionDetails']['txid']] = transactions_object

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
        return jsonify(result='error', description='Smart Contract\'s name hasn\'t been passed')

    if contractAddress is None:
        return jsonify(result='error', description='Smart Contract\'s address hasn\'t been passed')

    contractDbName = '{}-{}.db'.format(contractName.strip(),contractAddress.strip())
    filelocation = os.path.join(dbfolder, 'smartContracts', contractDbName)

    if os.path.isfile(filelocation):
        # Make db connection and fetch data
        conn = sqlite3.connect(filelocation)
        c = conn.cursor()
        c.execute('SELECT attribute,value FROM contractstructure')
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
                        if triggerntype[0] == 'trigger' and triggerntype[1] is None:
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
                    return jsonify(result='error', description='There is more than 1 trigger in the database for the smart contract. Please check your code, this shouldnt happen')
        
        return jsonify(result='ok', contractName=contractName, contractAddress=contractAddress, contractInfo=returnval)

    else:
        return jsonify(result='error', details='Smart Contract with the given name doesn\'t exist')


@app.route('/api/v1.0/getSmartContractParticipants', methods=['GET'])
async def getcontractparticipants():
    contractName = request.args.get('contractName')
    contractAddress = request.args.get('contractAddress')

    if contractName is None:
        return jsonify(result='error', description='Smart Contract\'s name hasn\'t been passed')

    if contractAddress is None:
        return jsonify(result='error', description='Smart Contract\'s address hasn\'t been passed')

    contractName = contractName.strip()
    contractAddress = contractAddress.strip()
    filelocation = os.path.join(dbfolder, 'smartContracts', '{}-{}.db'.format(contractName, contractAddress))

    if os.path.isfile(filelocation):
        # Make db connection and fetch data
        contractStructure = fetchContractStructure(contractName, contractAddress)
        conn, c = create_database_connection('smart_contract', {'contract_name': contractName, 'contract_address': contractAddress})        
        
        if 'exitconditions' in contractStructure:
            # contract is of the type external trigger
            # check if the contract has been closed
            c.execute('select * from contractTransactionHistory where transactionType="trigger"')
            trigger = c.fetchall()

            if len(trigger) == 1:
                c.execute('select value from contractstructure where attribute="tokenIdentification"')
                token = c.fetchall()
                token = token[0][0]
                c.execute('SELECT id,participantAddress, tokenAmount, userChoice, transactionHash, winningAmount FROM contractparticipants')
                result = c.fetchall()
                conn.close()
                returnval = {}
                for row in result:
                    returnval[row[1]] = {'participantFloAddress': row[1], 'tokenAmount': row[2], 'userChoice': row[3],
                                         'transactionHash': row[4], 'winningAmount': row[5], 'tokenIdentification': token}

            elif len(trigger) == 0:
                c.execute('SELECT id,participantAddress, tokenAmount, userChoice, transactionHash FROM contractparticipants')
                result = c.fetchall()
                conn.close()
                returnval = {}
                for row in result:
                    returnval[row[1]] = {'participantFloAddress': row[1], 'tokenAmount': row[2], 'userChoice': row[3], 'transactionHash': row[4]}

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

        elif contractStructure['contractType'] == 'continuos-event' and contractStructure['subtype'] == 'tokenswap':
            c.execute('SELECT * FROM contractparticipants')
            contract_participants = c.fetchall()
            returnval = {}
            for row in contract_participants:
                returnval[row[1]] = {
                                        'participantFloAddress': row[1], 
                                        'participationAmount': row[2], 
                                        'swapPrice': float(row[3]),
                                        'transactionHash': row[4],
                                        'blockNumber': row[5],
                                        'blockHash': row[6],
                                        'swapAmount': row[7]
                                    }
            conn.close()
        
        return jsonify(result='ok', contractName=contractName, contractAddress=contractAddress, participantInfo=returnval)
    else:
        return jsonify(result='error', description='Smart Contract with the given name doesn\'t exist')


@app.route('/api/v1.0/getParticipantDetails', methods=['GET'])
async def getParticipantDetails():
    floAddress = request.args.get('floAddress')
    contractName = request.args.get('contractName')
    contractAddress = request.args.get('contractAddress')

    if floAddress is None:
        return jsonify(result='error', description='FLO address hasn\'t been passed')
    dblocation = os.path.join(dbfolder, 'system.db')

    if (contractName and contractAddress is None) or (contractName is None and contractAddress):
        return jsonify(result='error', description='pass both, contractName and contractAddress as url parameters')

    #if os.path.isfile(dblocation) and os.path.isfile(contract_db):
    if os.path.isfile(dblocation):
        # Make db connection and fetch data
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()

        if contractName is not None:
            c.execute(f'SELECT * FROM contractAddressMapping WHERE address="{floAddress}" AND addressType="participant" AND contractName="{contractName}" AND contractAddress="{contractAddress}"')
        else:
            c.execute(f'SELECT * FROM contractAddressMapping WHERE address="{floAddress}" AND addressType="participant"')
        participant_address_contracts = c.fetchall()

        if len(participant_address_contracts) != 0:
            participationDetailsList = []
            for contract in participant_address_contracts:
                detailsDict = {}
                contract_db = os.path.join(dbfolder, 'smartContracts', f"{contract[3]}-{contract[4]}.db")
                # Make db connection and fetch contract structure
                conn = sqlite3.connect(contract_db)
                c = conn.cursor()

                # Get details of the type of Smart Contract 
                c.execute('SELECT attribute,value FROM contractstructure')
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

                if contractStructure['contractType']=='continuos-event' and contractStructure['subtype']=='tokenswap':
                    # normal result + swap details 
                    # what is a api detail 
                    c.execute('SELECT * FROM contractparticipants WHERE participantAddress=?',(floAddress,))
                    participant_details = c.fetchall()

                    if len(participant_details) > 0:
                        participationList = []
                        for participation in participant_details:
                            c.execute("SELECT value FROM contractstructure WHERE attribute='selling_token'")
                            structure = c.fetchall()
                            detailsDict['participationAddress'] = floAddress
                            detailsDict['participationAmount'] = participation[2]
                            detailsDict['receivedAmount'] = float(participation[3])
                            detailsDict['participationToken'] = contractStructure['accepting_token']
                            detailsDict['receivedToken'] = contractStructure['selling_token']
                            detailsDict['swapPrice_received_to_participation'] = float(participation[7])
                            detailsDict['transactionHash'] = participation[4]
                            detailsDict['blockNumber'] = participation[5]
                            detailsDict['blockHash'] = participation[6]
                            participationList.append(detailsDict)

                    participationDetailsList.append(participationList)
          
                elif contractStructure['contractType']=='one-time-event' and 'payeeAddress' in contractStructure.keys():
                    # normal results 
                    conn = sqlite3.connect(dblocation)
                    c = conn.cursor()
                    detailsDict = {}
                    detailsDict['contractName'] = contract[3]
                    detailsDict['contractAddress'] = contract[4]
                    detailsDict['tokenAmount'] = contract[5]
                    detailsDict['transactionHash'] = contract[6]

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
                    contractDbName = '{}-{}.db'.format(detailsDict['contractName'].strip(), detailsDict['contractAddress'].strip())
                    filelocation = os.path.join(dbfolder, 'smartContracts', contractDbName)
                    if os.path.isfile(filelocation):
                        # Make db connection and fetch data
                        conn = sqlite3.connect(filelocation)
                        c = conn.cursor()
                        c.execute('SELECT attribute,value FROM contractstructure')
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

                        if 'payeeAddress' in contractStructure:
                            # contract is of the type external trigger
                            # check if the contract has been closed
                            c.execute(f"SELECT tokenAmount FROM contractparticipants where participantAddress='{floAddress}'")
                            result = c.fetchall()
                            conn.close()
                            detailsDict['tokenAmount'] = result[0][0]

                elif contractStructure['contractType']=='one-time-event' and 'exitconditions' in contractStructure.keys():
                    # normal results + winning/losing details 
                    conn = sqlite3.connect(dblocation)
                    c = conn.cursor()
                    detailsDict = {}
                    detailsDict['contractName'] = contract[3]
                    detailsDict['contractAddress'] = contract[4]
                    detailsDict['tokenAmount'] = contract[5]
                    detailsDict['transactionHash'] = contract[6]

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
                    contractDbName = '{}-{}.db'.format(detailsDict['contractName'].strip(), detailsDict['contractAddress'].strip())
                    filelocation = os.path.join(dbfolder, 'smartContracts', contractDbName)
                    if os.path.isfile(filelocation):
                        # Make db connection and fetch data
                        conn = sqlite3.connect(filelocation)
                        c = conn.cursor()
                        c.execute('SELECT attribute,value FROM contractstructure')
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

                            if detailsDict['status'] == 'closed':
                                c.execute(f"SELECT userChoice, winningAmount FROM contractparticipants where participantAddress='{floAddress}'")
                                result = c.fetchall()
                                conn.close()
                                detailsDict['userChoice'] = result[0][0]
                                detailsDict['winningAmount'] = result[0][1]
                            else:
                                c.execute(f"SELECT userChoice FROM contractparticipants where participantAddress='{floAddress}'")
                                result = c.fetchall()
                                conn.close()
                                detailsDict['userChoice'] = result[0][0]

                    participationDetailsList.append(detailsDict)
                        
            return jsonify(result='ok', floAddress=floAddress, type='participant', participatedContracts=participationDetailsList)

        else:
            return jsonify(result='error', description='Address hasn\'t participated in any other contract')
    else:
        return jsonify(result='error', description='System error. System db is missing')


@app.route('/api/v1.0/getSmartContractTransactions', methods=['GET'])
async def getsmartcontracttransactions():
    contractName = request.args.get('contractName')
    contractAddress = request.args.get('contractAddress')

    if contractName is None:
        return jsonify(result='error', description='Smart Contract\'s name hasn\'t been passed')

    if contractAddress is None:
        return jsonify(result='error', description='Smart Contract\'s address hasn\'t been passed')

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
            transactions_object = {}
            transactions_object['transactionDetails'] = json.loads(item[0])
            transactions_object['transactionDetails'] = update_transaction_confirmations(transactions_object['transactionDetails'])
            transactions_object['parsedFloData'] = json.loads(item[1])
            returnval[transactions_object['transactionDetails']['txid']] = transactions_object

        return jsonify(result='ok', contractName=contractName, contractAddress=contractAddress, contractTransactions=returnval)

    else:
        return jsonify(result='error', description='Smart Contract with the given name doesn\'t exist')


@app.route('/api/v1.0/getBlockDetails/<blockdetail>', methods=['GET'])
async def getblockdetails(blockdetail):
    blockJson = blockdetailhelper(blockdetail)
    if len(blockJson) != 0:
        blockJson = json.loads(blockJson[0][0])
        return jsonify(result='ok', blockDetails=blockJson)
    else:
        return jsonify(result='error', description='Block doesn\'t exist in database')


@app.route('/api/v1.0/getTransactionDetails/<transactionHash>', methods=['GET'])
async def gettransactiondetails(transactionHash):
    transactionJsonData = transactiondetailhelper(transactionHash)
    if len(transactionJsonData) != 0:
        transactionJson = json.loads(transactionJsonData[0][0])
        transactionJson = update_transaction_confirmations(transactionJson)
        parseResult = json.loads(transactionJsonData[0][1])
        return jsonify(parsedFloData=parseResult, transactionDetails=transactionJson, transactionHash=transactionHash, result='ok')
    else:
        return jsonify(result='error', description='Transaction doesn\'t exist in database')


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
            tx_parsed_details['transactionDetails'] = update_transaction_confirmations(tx_parsed_details['transactionDetails'])
            tx_parsed_details['parsedFloData'] = json.loads(item[5])
            tx_parsed_details['parsedFloData']['transactionType'] = item[4]
            tx_parsed_details['transactionDetails']['blockheight'] = int(item[2])
            tempdict[json.loads(item[3])['txid']] = tx_parsed_details
    else:
        c.execute('''SELECT * FROM latestTransactions WHERE blockNumber IN (SELECT DISTINCT blockNumber FROM latestTransactions ORDER BY blockNumber DESC) ORDER BY id ASC;''')
        latestTransactions = c.fetchall()
        c.close()
        tempdict = {}
        for idx, item in enumerate(latestTransactions):
            item = list(item)
            tx_parsed_details = {}
            tx_parsed_details['transactionDetails'] = json.loads(item[3])
            tx_parsed_details['transactionDetails'] = update_transaction_confirmations(tx_parsed_details['transactionDetails'])
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


@app.route('/api/v1.0/getBlockTransactions/<blockdetail>', methods=['GET'])
async def getblocktransactions(blockdetail):
    blockJson = blockdetailhelper(blockdetail)
    if len(blockJson) != 0:
        blockJson = json.loads(blockJson[0][0])
        blocktxlist = blockJson['tx']
        blocktxs = {}
        for i in range(len(blocktxlist)):
            temptx = transactiondetailhelper(blocktxlist[i])                        
            transactionJson = json.loads(temptx[0][0])
            transactionJson = update_transaction_confirmations(transactionJson)
            parseResult = json.loads(temptx[0][1])
            blocktxs[blocktxlist[i]] = {
                "parsedFloData" : parseResult,
                "transactionDetails" : transactionJson
            }
        return jsonify(result='ok', transactions=blocktxs, blockKeyword=blockdetail)
    else:
        return jsonify(result='error', description='Block doesn\'t exist in database')


@app.route('/api/v1.0/categoriseString/<urlstring>')
async def categoriseString(urlstring):
    # check if the hash is of a transaction
    response = requests.get('{}api/v1/tx/{}'.format(apiUrl, urlstring))
    if response.status_code == 200:
        return jsonify(type='transaction')
    else:
        response = requests.get('{}api/v1/block/{}'.format(apiUrl, urlstring))
        if response.status_code == 200:
            return jsonify(type='block')
        else:
            # check urlstring is a token name
            tokenfolder = os.path.join(dbfolder, 'tokens')
            onlyfiles = [f[:-3]
                         for f in os.listdir(tokenfolder) if os.path.isfile(os.path.join(tokenfolder, f))]
            
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
    c.execute('SELECT * FROM activecontracts')
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


###################
###  VERSION 2  ###
###################

@app.route('/api/v2/info', methods=['GET'])
async def info():
    # query for the number of flo addresses in tokenAddress mapping
    conn = sqlite3.connect(os.path.join(dbfolder, 'system.db'))
    c = conn.cursor()
    tokenAddressCount = c.execute('SELECT COUNT(distinct tokenAddress) FROM tokenAddressMapping').fetchall()[0][0]
    tokenCount = c.execute('SELECT COUNT(distinct token) FROM tokenAddressMapping').fetchall()[0][0]
    contractCount = c.execute('SELECT COUNT(distinct contractName) FROM contractAddressMapping').fetchall()[0][0]
    lastscannedblock = int(c.execute("SELECT value FROM systemData WHERE attribute=='lastblockscanned'").fetchall()[0][0])
    conn.close()
    
    # query for total number of validated blocks
    conn = sqlite3.connect(os.path.join(dbfolder, 'latestCache.db'))
    c = conn.cursor()
    validatedBlockCount = c.execute('SELECT COUNT(distinct blockNumber) FROM latestBlocks').fetchall()[0][0]
    validatedTransactionCount = c.execute('SELECT COUNT(distinct transactionHash) FROM latestTransactions').fetchall()[0][0]
    conn.close()
    
    return jsonify(systemAddressCount=tokenAddressCount, systemBlockCount=validatedBlockCount, systemTransactionCount=validatedTransactionCount, systemSmartContractCount=contractCount, systemTokenCount=tokenCount, lastscannedblock=lastscannedblock), 200


@app.route('/api/v2/broadcastTx/<raw_transaction_hash>')
async def broadcastTx_v2(raw_transaction_hash):
    p1 = subprocess.run(['flo-cli','sendrawtransaction',raw_transaction_hash], capture_output=True)
    return jsonify(args=p1.args,returncode=p1.returncode,stdout=p1.stdout.decode(),stderr=p1.stderr.decode()), 200


# FLO TOKEN APIs
@app.route('/api/v2/tokenList', methods=['GET'])
async def tokenList():
    filelist = []
    for item in os.listdir(os.path.join(dbfolder, 'tokens')):
        if os.path.isfile(os.path.join(dbfolder, 'tokens', item)):
            filelist.append(item[:-3])
    return jsonify(tokens=filelist), 200


@app.route('/api/v2/tokenInfo/<token>', methods=['GET'])
async def tokenInfo(token):
    if token is None:
        return jsonify(description='Token name hasnt been passed'), 400
    
    # todo : input validation
    dblocation = dbfolder + '/tokens/' + str(token) + '.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()
    else:
        return jsonify(description="Token doesn't exist"), 404
    c.execute('SELECT * FROM transactionHistory WHERE id=1')
    incorporationRow = c.fetchall()[0]
    c.execute('SELECT COUNT (DISTINCT address) FROM activeTable')
    numberOf_distinctAddresses = c.fetchall()[0][0]
    c.execute('SELECT MAX(id) FROM transactionHistory')
    numberOf_transactions = c.fetchall()[0][0]
    c.execute('SELECT contractName, contractAddress, blockNumber, blockHash, transactionHash FROM tokenContractAssociation')
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

    return jsonify(token=token, incorporationAddress=incorporationRow[1], tokenSupply=incorporationRow[3], time=incorporationRow[6], blockchainReference=incorporationRow[7], activeAddress_no=numberOf_distinctAddresses, totalTransactions=numberOf_transactions, associatedSmartContracts=associatedContractList), 200 


@app.route('/api/v2/tokenTransactions/<token>', methods=['GET'])
async def tokenTransactions(token):
    if token is None:
        return jsonify(description='Token name hasnt been passed'), 400 

    # Input validations
    senderFloAddress = request.args.get('senderFloAddress')
    if senderFloAddress is not None and not check_flo_address(senderFloAddress, is_testnet):
        return jsonify(description='senderFloAddress validation failed'), 400
    destFloAddress = request.args.get('destFloAddress')
    if destFloAddress is not None and not check_flo_address(destFloAddress, is_testnet):
        return jsonify(description='destFloAddress validation failed'), 400
    limit = request.args.get('limit')
    if limit is not None and not check_integer(limit):
        return jsonify(description='limit validation failed'), 400
    use_AND = request.args.get('use_AND')
    if use_AND is not None and use_AND not in [True, False]:
        return jsonify(description='use_AND validation failed'), 400
    
    _from = int(request.args.get('_from', 1))  # Get page number, default is 1
    to = int(request.args.get('to', 100))  # Get limit, default is 10

    if _from<1:
        return jsonify(description='_from validation failed'), 400
    if to<1:
        return jsonify(description='to validation failed'), 400
    
    filelocation = os.path.join(dbfolder, 'tokens', f'{token}.db')

    if os.path.isfile(filelocation):
        transactionJsonData = fetch_token_transactions(token, senderFloAddress, destFloAddress, limit, use_AND)
        sortedFormattedTransactions = sort_transactions(transactionJsonData)
        return jsonify(token=token, transactions=sortedFormattedTransactions), 200
    else:
        return jsonify(description='Token with the given name doesn\'t exist'), 404


@app.route('/api/v2/tokenBalances/<token>', methods=['GET'])
async def tokenBalances(token):
    if token is None:
        return jsonify(description='Token name hasnt been passed'), 400

    dblocation = dbfolder + '/tokens/' + str(token) + '.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()
    else:
        return jsonify(description="Token doesn't exist"), 404
    c.execute('SELECT address,SUM(transferBalance) FROM activeTable GROUP BY address')
    addressBalances = c.fetchall()
    returnList = {}
    for address in addressBalances:
        returnList[address[0]] = address[1]

    return jsonify(token=token, balances=returnList), 200


# FLO Address APIs
@app.route('/api/v2/floAddressInfo/<floAddress>', methods=['GET'])
async def floAddressInfo(floAddress):
    if floAddress is None:
        return jsonify(description='floAddress hasn\'t been passed'), 400
    # input validation
    if not check_flo_address(floAddress, is_testnet):
        return jsonify(description='floAddress validation failed'), 400 

    dblocation = dbfolder + '/system.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()
        c.execute(f'SELECT token FROM tokenAddressMapping WHERE tokenAddress="{floAddress}"')
        tokenNames = c.fetchall()
        c.execute(f"SELECT contractName, status, tokenIdentification, contractType, transactionHash, blockNumber, blockHash FROM activecontracts WHERE contractAddress='{floAddress}'")
        incorporatedContracts = c.fetchall()
        detailList = None
        if len(tokenNames) != 0:
            detailList = {}
            for token in tokenNames:
                token = token[0]
                dblocation = dbfolder + '/tokens/' + str(token) + '.db'
                if os.path.exists(dblocation):
                    tempdict = {}
                    conn = sqlite3.connect(dblocation)
                    c = conn.cursor()
                    c.execute(f'SELECT SUM(transferBalance) FROM activeTable WHERE address="{floAddress}"')
                    balance = c.fetchall()[0][0]
                    tempdict['balance'] = balance
                    tempdict['token'] = token
                    detailList[token] = tempdict
        #else:
        #    # Address is not associated with any token
        #    return jsonify(description='FLO address is not associated with any tokens'), 404
        
        incorporatedSmartContracts = None
        if len(incorporatedContracts) > 0:
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
            
        return jsonify(floAddress=floAddress, floAddressBalances=detailList, incorporatedSmartContracts=incorporatedSmartContracts), 200


@app.route('/api/v2/floAddressBalance/<floAddress>', methods=['GET'])
async def floAddressBalance(floAddress):
    if floAddress is None:
        return jsonify(description='floAddress hasn\'t been passed'), 400
    # input validation
    if not check_flo_address(floAddress, is_testnet):
        return jsonify(description='floAddress validation failed'), 400 
    
    token = request.args.get('token')
    if token is None:
        dblocation = dbfolder + '/system.db'
        if os.path.exists(dblocation):
            conn = sqlite3.connect(dblocation)
            c = conn.cursor()
            c.execute(f'SELECT token FROM tokenAddressMapping WHERE tokenAddress="{floAddress}"')
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
                        c.execute(f'SELECT SUM(transferBalance) FROM activeTable WHERE address="{floAddress}"')
                        balance = c.fetchall()[0][0]
                        tempdict['balance'] = balance
                        tempdict['token'] = token
                        detailList[token] = tempdict
                return jsonify(floAddress=floAddress, floAddressBalances=detailList), 200
            else:
                # Address is not associated with any token
                return jsonify(floAddress=floAddress, floAddressBalances={}), 200
    else:
        dblocation = dbfolder + '/tokens/' + str(token) + '.db'
        if os.path.exists(dblocation):
            conn = sqlite3.connect(dblocation)
            c = conn.cursor()
        else:
            return jsonify(description="Token doesn't exist"), 404
        c.execute(f'SELECT SUM(transferBalance) FROM activeTable WHERE address="{floAddress}"')
        balance = c.fetchall()[0][0]
        conn.close()
        return jsonify(floAddress=floAddress, token=token, balance=balance), 200


@app.route('/api/v2/floAddressTransactions/<floAddress>', methods=['GET'])
async def floAddressTransactions(floAddress):
    if floAddress is None:
        return jsonify(description='floAddress has not been passed'), 400
    if not check_flo_address(floAddress, is_testnet):
        return jsonify(description='floAddress validation failed'), 400 
    limit = request.args.get('limit')
    if limit is not None and not check_integer(limit):
        return jsonify(description='limit validation failed'), 400
    
    token = request.args.get('token')
    if token is None:
        dblocation = dbfolder + '/system.db'
        if os.path.exists(dblocation):
            conn = sqlite3.connect(dblocation)
            c = conn.cursor()
            c.execute('SELECT token FROM tokenAddressMapping WHERE tokenAddress="{}"'.format(floAddress))
            tokenNames = c.fetchall()
    else:
        dblocation = dbfolder + '/tokens/' + str(token) + '.db'
        if os.path.exists(dblocation):
            tokenNames = [[str(token), ]]
        else:
            return jsonify(description="Token doesn't exist"), 404
        
    if len(tokenNames) != 0:
        allTransactionList = []
        for tokenname in tokenNames:
            tokenname = tokenname[0]
            transactionJsonData = fetch_token_transactions(tokenname, senderFloAddress=floAddress, destFloAddress=floAddress, limit=limit)
            allTransactionList = allTransactionList + transactionJsonData 
        
        sortedFormattedTransactions = sort_transactions(allTransactionList)
        if token is None:
            return jsonify(floAddress=floAddress, transactions=sortedFormattedTransactions), 200
        else:
            return jsonify(floAddress=floAddress, transactions=sortedFormattedTransactions, token=token), 200
    else:
        return jsonify(floAddress=floAddress, transactions=[], token=token), 200


# SMART CONTRACT APIs
@app.route('/api/v2/smartContractList', methods=['GET'])
async def getContractList_v2():
    contractName = request.args.get('contractName')
    if contractName is not None:
        contractName = contractName.strip().lower()

    # todo - Add validation for contractAddress and contractName to prevent SQL injection attacks
    contractAddress = request.args.get('contractAddress')
    if contractAddress is not None:
        contractAddress = contractAddress.strip()
        if not check_flo_address(contractAddress, is_testnet):
            return jsonify(description='contractAddress validation failed'), 400
    
    contractList = []
    conn = sqlite3.connect(os.path.join(dbfolder, 'system.db'))
    c = conn.cursor()
    smart_contracts = return_smart_contracts(c, contractName, contractAddress)
    smart_contracts_morphed = smartcontract_morph_helper(smart_contracts)
    conn.close()

    committeeAddressList = refresh_committee_list(APP_ADMIN, apiUrl, int(time.time()))

    return jsonify(smartContracts=smart_contracts_morphed, smartContractCommittee=committeeAddressList), 200


@app.route('/api/v2/smartContractInfo', methods=['GET'])
async def getContractInfo_v2():
    contractName = request.args.get('contractName')
    contractAddress = request.args.get('contractAddress')
    
    if contractName is None:
        return jsonify(description='Smart Contract\'s name hasn\'t been passed'), 400
    contractName = contractName.strip().lower()
    
    if contractAddress is None:
        return jsonify(description='Smart Contract\'s address hasn\'t been passed'), 400
    contractAddress = contractAddress.strip()
    if not check_flo_address(contractAddress, is_testnet):
        return jsonify(description='contractAddress validation failed'), 400
    
    contractStructure = fetchContractStructure(contractName, contractAddress)
    if contractStructure:
        returnval = contractStructure
        # Categorize into what type of contract it is right now 
        if contractStructure['contractType'] == 'continuos-event' and contractStructure['subtype'] == 'tokenswap':
            conn, c = create_database_connection('smart_contract', {'contract_name': contractName, 'contract_address': contractAddress})

            c.execute('SELECT COUNT(participantAddress), SUM(tokenAmount), SUM(winningAmount) FROM contractparticipants')
            participation_details = c.fetchall()

            c.execute('SELECT depositAmount FROM contractdeposits')
            deposit_details = c.fetchall()

            returnval['numberOfParticipants'] = participation_details[0][0]
            returnval['totalParticipationAmount'] = participation_details[0][1]
            returnval['totalHonorAmount'] = participation_details[0][2]
            c.execute('SELECT COUNT(DISTINCT transactionHash) FROM contractdeposits')
            returnval['numberOfDeposits'] = c.fetchall()[0][0]
            c.execute('SELECT SUM(depositBalance) AS totalDepositBalance FROM contractdeposits c1 WHERE id = ( SELECT MAX(id) FROM contractdeposits c2 WHERE c1.transactionHash = c2.transactionHash);')
            returnval['currentDepositBalance'] = c.fetchall()[0][0]
            # todo - add code to token tracker to save continuos event subtype KEY as contractSubtype as part of contractStructure and remove the following line
            returnval['contractSubtype'] = 'tokenswap'
            returnval['priceType'] = returnval['pricetype']
            if returnval['pricetype'] not in ['predetermined']:
                returnval['price'] = fetch_dynamic_swap_price(contractStructure, {'time': datetime.now().timestamp()})
            returnval['acceptingToken'] = returnval['accepting_token']
            returnval['sellingToken'] = returnval['selling_token']
            
        elif contractStructure['contractType'] == 'one-time-event' and 'exitconditions' in contractStructure.keys():
            choice_list = []
            for obj_key in contractStructure['exitconditions'].keys():
                choice_list.append(contractStructure['exitconditions'][obj_key])
            returnval['userChoices'] = choice_list
            returnval.pop('exitconditions')

            contract_status_time_info = fetch_contract_status_time_info(contractName, contractAddress)
            if len(contract_status_time_info) == 1:
                for status_time_info in contract_status_time_info:
                    returnval['status'] = status_time_info[0]
                    returnval['incorporationDate'] = status_time_info[1]
                    if status_time_info[2]:
                        returnval['expiryDate'] = status_time_info[2]
                    if status_time_info[3]:
                        returnval['closeDate'] = status_time_info[3]
            # todo - add code to token tracker to save one-time-event subtype as part of contractStructure and remove the following line
            returnval['contractSubtype'] = 'external-trigger'
        elif contractStructure['contractType'] == 'one-time-event' and 'payeeAddress' in contractStructure.keys():
            contract_status_time_info = fetch_contract_status_time_info(contractName, contractAddress)
            if len(contract_status_time_info) == 1:
                for status_time_info in contract_status_time_info:
                    returnval['status'] = status_time_info[0]
                    returnval['incorporationDate'] = status_time_info[1]
                    if status_time_info[2]:
                        returnval['expiryDate'] = status_time_info[2]
                    if status_time_info[3]:
                        returnval['closeDate'] = status_time_info[3]
            returnval['contractSubtype'] = 'time-trigger'

        return jsonify(contractName=contractName, contractAddress=contractAddress, contractInfo=returnval), 200
    else:
        return jsonify(details="Smart Contract with the given name doesn't exist"), 404


@app.route('/api/v2/smartContractParticipants', methods=['GET'])
async def getcontractparticipants_v2():
    contractName = request.args.get('contractName')
    if contractName is None:
        return jsonify(description='Smart Contract\'s name hasn\'t been passed'), 400
    contractName = contractName.strip().lower()

    contractAddress = request.args.get('contractAddress')
    if contractAddress is None:
        return jsonify(description='Smart Contract\'s address hasn\'t been passed'), 400 
    contractAddress = contractAddress.strip()
    if not check_flo_address(contractAddress, is_testnet):
        return jsonify(description='contractAddress validation failed'), 400
    
    filelocation = os.path.join(dbfolder, 'smartContracts', '{}-{}.db'.format(contractName, contractAddress))
    if os.path.isfile(filelocation):
        # Make db connection and fetch data
        contractStructure = fetchContractStructure(contractName, contractAddress)
        contractStatus = fetchContractStatus(contractName, contractAddress)
        conn, c = create_database_connection('smart_contract', {'contract_name': contractName, 'contract_address': contractAddress})
        if 'exitconditions' in contractStructure:
            # contract is of the type external trigger
            # check if the contract has been closed
            if contractStatus == 'closed':
                token = contractStructure['tokenIdentification']
                c.execute('SELECT id, participantAddress, tokenAmount, userChoice, transactionHash, winningAmount FROM contractparticipants')
                result = c.fetchall()
                returnval = []
                for row in result:
                    # Check value of winning amount
                    c.execute(f'SELECT winningAmount FROM contractwinners WHERE referenceTxHash="{row[4]}"')
                    participant_winningAmount = c.fetchall()
                    if participant_winningAmount != []:
                        participant_winningAmount = participant_winningAmount[0][0]
                    else:
                        participant_winningAmount = 0
                    participation = {'participantFloAddress': row[1], 'tokenAmount': row[2], 'userChoice': row[3], 'transactionHash': row[4], 'winningAmount': participant_winningAmount, 'tokenIdentification': token}
                    returnval.append(participation)
            else:
                c.execute('SELECT id, participantAddress, tokenAmount, userChoice, transactionHash FROM contractparticipants')
                result = c.fetchall()
                conn.close()
                returnval = []
                for row in result:
                    participation = {'participantFloAddress': row[1], 'tokenAmount': row[2], 'userChoice': row[3], 'transactionHash': row[4]}
                    returnval.append(participation)
            return jsonify(contractName=contractName, contractAddress=contractAddress, contractType=contractStructure['contractType'], contractSubtype='external-trigger', participantInfo=returnval), 200
        elif 'payeeAddress' in contractStructure:
            # contract is of the type internal trigger
            c.execute('SELECT id, participantAddress, tokenAmount, userChoice, transactionHash FROM contractparticipants')
            result = c.fetchall()
            conn.close()
            returnval = []
            for row in result:
                participation = {'participantFloAddress': row[1], 'tokenAmount': row[2], 'transactionHash': row[4]}
                returnval.append(participation)
            return jsonify(contractName=contractName, contractAddress=contractAddress, contractType=contractStructure['contractType'], contractSubtype='time-trigger', participantInfo=returnval), 200
        elif contractStructure['contractType'] == 'continuos-event' and contractStructure['subtype'] == 'tokenswap':
            c.execute('SELECT * FROM contractparticipants')
            contract_participants = c.fetchall()
            returnval = []
            for row in contract_participants:
                participation = {
                                    'participantFloAddress': row[1], 
                                    'participationAmount': row[2], 
                                    'swapPrice': float(row[3]),
                                    'transactionHash': row[4],
                                    'blockNumber': row[5],
                                    'blockHash': row[6],
                                    'swapAmount': row[7]
                                }
                returnval.append(participation)
            conn.close()
            return jsonify(contractName=contractName, contractAddress=contractAddress, contractType=contractStructure['contractType'], contractSubtype=contractStructure['subtype'], participantInfo=returnval), 200
    else:
        return jsonify(description='Smart Contract with the given name doesn\'t exist'), 404


@app.route('/api/v2/participantDetails/<floAddress>', methods=['GET'])
async def participantDetails(floAddress):
    if floAddress is None:
        return jsonify(description='FLO address hasn\'t been passed'), 400
    if not check_flo_address(floAddress, is_testnet):
        return jsonify(description='floAddress validation failed'), 400
    
    contractName = request.args.get('contractName')
    contractAddress = request.args.get('contractAddress')

    # Url param checking
    if contractName is None and contractAddress is None:
        return jsonify(description='Pass both, contractName and contractAddress as url parameters'), 400
    elif contractName is None:
        return jsonify(description='Pass contractName as url parameter'), 400
    else:
        return jsonify(description='Pass contractAddress as url parameter'), 400
    
    if not check_flo_address(contractAddress, is_testnet):
        return jsonify(description='contractAddress validation failed'), 400
    
    contractName = contractName.strip().lower()
    contractAddress = contractAddress.strip()

    systemdb_location = os.path.join(dbfolder, 'system.db')
    if os.path.isfile(systemdb_location):
        # Make db connection and fetch data
        systemdb_conn = sqlite3.connect(systemdb_location)
        c = systemdb_conn.cursor()
        if contractName is not None:
            c.execute(f'SELECT * FROM contractAddressMapping WHERE address="{floAddress}" AND addressType="participant" AND contractName="{contractName}" AND contractAddress="{contractAddress}"')
        else:
            c.execute(f'SELECT * FROM contractAddressMapping WHERE address="{floAddress}" AND addressType="participant"')
        participant_address_contracts = c.fetchall()
        
        if len(participant_address_contracts) != 0:
            participationDetailsList = []
            for contract in participant_address_contracts:
                detailsDict = {}
                contract_db = os.path.join(dbfolder, 'smartContracts', f"{contract[3]}-{contract[4]}.db")
                # Make db connection and fetch contract structure
                contractdb_conn = sqlite3.connect(contract_db)
                contract_c = contractdb_conn.cursor()
                # Get details of the type of Smart Contract 
                contract_c.execute('SELECT attribute,value FROM contractstructure')
                result = contract_c.fetchall()

                contractStructure = fetchContractStructure(contract[3], contract[4])
                contractDbName = '{}-{}.db'.format(contract[3], contract[4])

                if contractStructure['contractType']=='continuos-event' and contractStructure['subtype']=='tokenswap':
                    # normal result + swap details 
                    # what is a api detail 
                    contract_c.execute('SELECT * FROM contractparticipants WHERE participantAddress=?',(floAddress,))
                    participant_details = contract_c.fetchall()
                    if len(participant_details) > 0:
                        participationList = []
                        for participation in participant_details:
                            detailsDict['participationAddress'] = floAddress
                            detailsDict['participationAmount'] = participation[2]
                            detailsDict['receivedAmount'] = float(participation[3])
                            detailsDict['participationToken'] = contractStructure['accepting_token']
                            detailsDict['receivedToken'] = contractStructure['selling_token']
                            detailsDict['swapPrice_received_to_participation'] = float(participation[7])
                            detailsDict['transactionHash'] = participation[4]
                            detailsDict['blockNumber'] = participation[5]
                            detailsDict['blockHash'] = participation[6]
                            participationList.append(detailsDict)
                    participationDetailsList.append(participationList)

                elif contractStructure['contractType']=='one-time-event' and 'payeeAddress' in contractStructure.keys():
                    # normal results 
                    detailsDict = {}
                    detailsDict['contractName'] = contract[3]
                    detailsDict['contractAddress'] = contract[4]
                    detailsDict['tokenAmount'] = contract[5]
                    detailsDict['transactionHash'] = contract[6]

                    c.execute(f"SELECT status, tokenIdentification, contractType, blockNumber, blockHash, incorporationDate, expiryDate, closeDate FROM activecontracts WHERE contractName='{detailsDict['contractName']}' AND contractAddress='{detailsDict['contractAddress']}'")
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
                    filelocation = os.path.join(dbfolder, 'smartContracts', contractDbName)
                    if os.path.isfile(filelocation):
                        if 'payeeAddress' in contractStructure:
                            # contract is of the type external trigger
                            # check if the contract has been closed
                            contract_c.execute(f"SELECT tokenAmount FROM contractparticipants WHERE participantAddress='{floAddress}'")
                            result = contract_c.fetchall()
                            detailsDict['tokenAmount'] = result[0][0]

                elif contractStructure['contractType']=='one-time-event' and 'exitconditions' in contractStructure.keys():
                    # normal results + winning/losing details 
                    detailsDict = {}
                    detailsDict['contractName'] = contract[3]
                    detailsDict['contractAddress'] = contract[4]
                    detailsDict['tokenAmount'] = contract[5]
                    detailsDict['transactionHash'] = contract[6]

                    c.execute(f"SELECT status, tokenIdentification, contractType, blockNumber, blockHash, incorporationDate, expiryDate, closeDate FROM activecontracts WHERE contractName='{detailsDict['contractName']}' AND contractAddress='{detailsDict['contractAddress']}'")
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
                    filelocation = os.path.join(dbfolder, 'smartContracts', contractDbName)
                    if os.path.isfile(filelocation):
                        # Make db connection and fetch data
                        contract_c.execute('SELECT attribute,value FROM contractstructure')
                        result = contract_c.fetchall()
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
                            if detailsDict['status'] == 'closed':
                                contract_c.execute(f"SELECT userChoice, winningAmount FROM contractparticipants WHERE participantAddress='{floAddress}'")
                                result = contract_c.fetchall()
                                detailsDict['userChoice'] = result[0][0]
                                detailsDict['winningAmount'] = result[0][1]
                            else:
                                contract_c.execute(f"SELECT userChoice FROM contractparticipants WHERE participantAddress='{floAddress}'")
                                result = contract_c.fetchall()
                                detailsDict['userChoice'] = result[0][0]
                    participationDetailsList.append(detailsDict)
                        
            return jsonify(floAddress=floAddress, type='participant', participatedContracts=participationDetailsList), 200
        else:
            return jsonify(description="Address hasn't participated in any other contract"), 404
    else:
        return jsonify(description='System error. System.db is missing. This is unusual, please report on https://github.com/ranchimall/ranchimallflo-api'), 500


@app.route('/api/v2/smartContractTransactions', methods=['GET'])
async def smartcontracttransactions():
    contractName = request.args.get('contractName')
    if contractName is None:
        return jsonify(description='Smart Contract\'s name hasn\'t been passed'), 400
    contractName = contractName.strip().lower()
    contractAddress = request.args.get('contractAddress')
    if contractAddress is None:
        return jsonify(description='Smart Contract\'s address hasn\'t been passed'), 400
    contractAddress = contractAddress.strip()
    if not check_flo_address(contractAddress, is_testnet):
        return jsonify(description='contractAddress validation failed'), 400
    
    _from = int(request.args.get('_from', 1))  # Get page number, default is 1
    to = int(request.args.get('to', 100))  # Get limit, default is 10

    if _from<1:
        return jsonify(description='_from validation failed'), 400
    if to<1:
        return jsonify(description='to validation failed'), 400
    
    contractDbName = '{}-{}.db'.format(contractName, contractAddress)
    filelocation = os.path.join(dbfolder, 'smartContracts', contractDbName)

    if os.path.isfile(filelocation):
        # Make db connection and fetch data
        transactionJsonData = fetch_contract_transactions(contractName, contractAddress, _from, to)
        transactionJsonData = sort_transactions(transactionJsonData)
        return jsonify(contractName=contractName, contractAddress=contractAddress, contractTransactions=transactionJsonData), 200
    else:
        return jsonify(description='Smart Contract with the given name doesn\'t exist'), 404


# todo - add options to only ask for active/consumed/returned deposits
@app.route('/api/v2/smartContractDeposits', methods=['GET'])
async def smartcontractdeposits():
    # todo - put validation for transactionHash
    contractName = request.args.get('contractName')
    if contractName is None:
        return jsonify(description='Smart Contract\'s name hasn\'t been passed'), 400
    contractName = contractName.strip().lower()
    
    contractAddress = request.args.get('contractAddress')
    if contractAddress is None:
        return jsonify(description='Smart Contract\'s address hasn\'t been passed'), 400
    contractAddress = contractAddress.strip()
    if not check_flo_address(contractAddress, is_testnet):
        return jsonify(description='contractAddress validation failed'), 400

    contractDbName = '{}-{}.db'.format(contractName, contractAddress)
    filelocation = os.path.join(dbfolder, 'smartContracts', contractDbName)
    if os.path.isfile(filelocation):
        # active deposits 
        conn = sqlite3.connect(filelocation)
        c = conn.cursor()
        c.execute('''SELECT depositorAddress, transactionHash, status, depositBalance FROM contractdeposits 
                    WHERE (transactionHash, id) IN (SELECT transactionHash, MAX(id) FROM contractdeposits GROUP BY transactionHash) 
                    ORDER BY id DESC; ''')
        
        distinct_deposits = c.fetchall()
        deposit_info = []
        for a_deposit in distinct_deposits:
            #c.execute(f"SELECT depositBalance FROM contractdeposits WHERE (transactionHash, id) IN (SELECT transactionHash, MIN(id) FROM contractdeposits GROUP BY transactionHash );")
            c.execute(f"SELECT depositBalance, unix_expiryTime FROM contractdeposits WHERE transactionHash=='{a_deposit[1]}' ORDER BY id LIMIT 1")
            original_deposit_balance = c.fetchall()
            obj = {
                'depositorAddress': a_deposit[0],
                'transactionHash': a_deposit[1],
                'status': a_deposit[2],
                'originalBalance': original_deposit_balance[0][0],
                'currentBalance': a_deposit[3],
                'time': original_deposit_balance[0][1]
            }
            deposit_info.append(obj)
        c.execute('SELECT SUM(depositBalance) AS totalDepositBalance FROM contractdeposits c1 WHERE id = ( SELECT MAX(id) FROM contractdeposits c2 WHERE c1.transactionHash = c2.transactionHash);')
        currentDepositBalance = c.fetchall()[0][0]
        return jsonify(currentDepositBalance=currentDepositBalance, depositInfo=deposit_info), 200
    else:
        return jsonify(description='Smart Contract with the given name doesn\'t exist'), 404


@app.route('/api/v2/blockDetails/<blockHash>', methods=['GET'])
async def blockdetails(blockHash):
    # todo - validate blockHash
    blockJson = blockdetailhelper(blockHash)
    if len(blockJson) != 0:
        blockJson = json.loads(blockJson[0][0])
        return jsonify(blockDetails=blockJson), 200
    else:
        return jsonify(description='Block doesn\'t exist in database'), 404


@app.route('/api/v2/transactionDetails/<transactionHash>', methods=['GET'])
async def transactiondetails1(transactionHash):
    # todo - validate transactionHash
    transactionJsonData = transactiondetailhelper(transactionHash)

    if len(transactionJsonData) != 0:
        transactionJson = json.loads(transactionJsonData[0][0])
        transactionJson = update_transaction_confirmations(transactionJson)
        parseResult = json.loads(transactionJsonData[0][1])
        operation = transactionJsonData[0][2]
        db_reference = transactionJsonData[0][3]
        sender_address, receiver_address = extract_ip_op_addresses(transactionJson)

        mergeTx = {**parseResult, **transactionJson}
        # TODO (CRITICAL): Write conditions to include and filter on chain and offchain transactions   
        mergeTx['onChain'] = True 
        
        operationDetails = {}
        if operation == 'smartContractDeposit':
            # open the db reference and check if there is a deposit return 
            conn = sqlite3.connect(f"{dbfolder}/smartContracts/{db_reference}.db")
            c = conn.cursor()
            c.execute("SELECT depositAmount, blockNumber FROM contractdeposits WHERE status='deposit-return' AND transactionHash=?",(transactionJson['txid'],))
            returned_deposit_tx = c.fetchall()
            if len(returned_deposit_tx) == 1:
                operationDetails['returned_depositAmount'] = returned_deposit_tx[0][0]
                operationDetails['returned_blockNumber'] = returned_deposit_tx[0][1]
            c.execute("SELECT depositAmount, blockNumber FROM contractdeposits WHERE status='deposit-honor' AND transactionHash=?",(transactionJson['txid'],))
            deposit_honors = c.fetchall()
            operationDetails['depositHonors'] = {}
            operationDetails['depositHonors']['list'] = []
            operationDetails['depositHonors']['count'] = len(deposit_honors)
            for deposit_honor in deposit_honors:
                operationDetails['depositHonors']['list'].append({'honor_amount':deposit_honor[0],'blockNumber':deposit_honor[1]})

            c.execute("SELECT depositBalance FROM contractdeposits WHERE id=(SELECT max(id) FROM contractdeposits WHERE transactionHash=?)",(transactionJson['txid'],))
            depositBalance = c.fetchall()
            operationDetails['depositBalance'] = depositBalance[0][0]
            operationDetails['consumedAmount'] = parseResult['depositAmount'] - operationDetails['depositBalance']

        elif operation == 'tokenswap-participation':
            conn = sqlite3.connect(f"{dbfolder}/smartContracts/{db_reference}.db")
            c = conn.cursor()
            c.execute('SELECT tokenAmount, winningAmount, userChoice FROM contractparticipants WHERE transactionHash=?',(transactionJson['txid'],))
            swap_amounts = c.fetchall()
            c.execute("SELECT value FROM contractstructure WHERE attribute='selling_token'")
            structure = c.fetchall()
            operationDetails['participationAmount'] = swap_amounts[0][0]
            operationDetails['receivedAmount'] = swap_amounts[0][1]
            operationDetails['participationToken'] = parseResult['tokenIdentification']
            operationDetails['receivedToken'] = structure[0][0]
            operationDetails['swapPrice_received_to_participation'] = float(swap_amounts[0][2])

        elif operation == 'smartContractPays':
            # Find what happened because of the trigger 
            # Find who 
            conn = sqlite3.connect(f"{dbfolder}/smartContracts/{db_reference}.db")
            c = conn.cursor()
            c.execute('SELECT participantAddress, tokenAmount, userChoice, winningAmount FROM contractparticipants WHERE winningAmount IS NOT NULL')
            winner_participants = c.fetchall()
            if len(winner_participants) != 0:
                operationDetails['total_winners'] = len(winner_participants)
                operationDetails['winning_choice'] = winner_participants[0][2]
                operationDetails['winner_list'] = []
                for participant in winner_participants:
                    winner_details = {}
                    winner_details['participantAddress'] = participant[0]
                    winner_details['participationAmount'] = participant[1]
                    winner_details['winningAmount'] = participant[3]
                    operationDetails['winner_list'].append(winner_details)

        elif operation == 'ote-externaltrigger-participation':
            # Find if this guy has won 
            conn = sqlite3.connect(f"{dbfolder}/smartContracts/{db_reference}.db")
            c = conn.cursor()
            c.execute('SELECT winningAmount FROM contractparticipants WHERE transactionHash=?',(transactionHash,))
            winningAmount = c.fetchall()
            if winningAmount[0][0] is not None:
                operationDetails['winningAmount'] = winningAmount[0][0]
        
        elif operation == 'tokenswapParticipation':
            contractName, contractAddress = db_reference.rsplit('-',1)
            conn = sqlite3.connect(f"{dbfolder}/smartContracts/{db_reference}.db")
            c = conn.cursor()            
            txhash_txs = fetch_swap_contract_transactions(contractName, contractAddress, transactionHash)
            mergeTx['subTransactions'] = []
            for transaction in txhash_txs:
                if transaction['onChain'] == False:
                    mergeTx['subTransactions'].append(transaction)
        
        mergeTx['operation'] = operation
        mergeTx['operationDetails'] = operationDetails
        return jsonify(mergeTx), 200
    else:
        return jsonify(description='Transaction doesn\'t exist in database'), 404


@app.route('/api/v2/latestTransactionDetails', methods=['GET'])
async def latestTransactionDetails():
    limit = request.args.get('limit')
    if limit is not None and not check_integer(limit):
        return jsonify(description='limit validation failed'), 400

    dblocation = dbfolder + '/latestCache.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()
    else:
        return jsonify(description='Latest transactions db doesn\'t exist. This is unusual, please report on https://github.com/ranchimall/ranchimallflo-api'), 500

    if limit is not None:
        c.execute('SELECT * FROM latestTransactions WHERE blockNumber IN (SELECT DISTINCT blockNumber FROM latestTransactions ORDER BY blockNumber DESC LIMIT {}) ORDER BY id DESC;'.format(int(limit)))
    else:
        c.execute('''SELECT * FROM latestTransactions WHERE blockNumber IN (SELECT DISTINCT blockNumber FROM latestTransactions ORDER BY blockNumber DESC) ORDER BY id DESC;''')
    latestTransactions = c.fetchall()
    c.close()
    tx_list = []
    for idx, item in enumerate(latestTransactions):
        item = list(item)
        tx_parsed_details = {}
        tx_parsed_details['transactionDetails'] = json.loads(item[3])
        tx_parsed_details['transactionDetails'] = update_transaction_confirmations(tx_parsed_details['transactionDetails'])
        tx_parsed_details['parsedFloData'] = json.loads(item[5])
        tx_parsed_details['parsedFloData']['transactionType'] = item[4]
        tx_parsed_details['transactionDetails']['blockheight'] = int(item[2])
        tx_parsed_details = {**tx_parsed_details['transactionDetails'], **tx_parsed_details['parsedFloData']}
        # TODO (CRITICAL): Write conditions to include and filter on chain and offchain transactions
        tx_parsed_details['onChain'] = True
        tx_list.append(tx_parsed_details)
    return jsonify(latestTransactions=tx_list), 200


@app.route('/api/v2/latestBlockDetails', methods=['GET'])
async def latestBlockDetails():
    limit = request.args.get('limit')
    if limit is not None and not check_integer(limit):
        return jsonify(description='limit validation failed'), 400

    dblocation = dbfolder + '/latestCache.db'
    if os.path.exists(dblocation):
        conn = sqlite3.connect(dblocation)
        c = conn.cursor()
    else:
        return jsonify(description='Latest transactions db doesn\'t exist. This is unusual, please report on https://github.com/ranchimall/ranchimallflo-api'), 404

    if limit is None:
        c.execute('''SELECT jsonData FROM ( SELECT * FROM latestBlocks ORDER BY blockNumber DESC LIMIT 4) ORDER BY id DESC;''')
    else:
        c.execute(f'SELECT jsonData FROM ( SELECT * FROM latestBlocks ORDER BY blockNumber DESC LIMIT {limit}) ORDER BY id DESC;')
    latestBlocks = c.fetchall()
    c.close()
    
    templst = []
    for idx, item in enumerate(latestBlocks):
        templst.append(json.loads(item[0]))
        
    return jsonify(latestBlocks=templst), 200


@app.route('/api/v2/blockTransactions/<blockHash>', methods=['GET'])
async def blocktransactions(blockHash):
    blockJson = blockdetailhelper(blockHash)
    if len(blockJson) != 0:
        blockJson = json.loads(blockJson[0][0])
        blocktxlist = blockJson['txs']
        blocktxs = []
        for i in range(len(blocktxlist)):
            temptx = transactiondetailhelper(blocktxlist[i]['txid'])                        
            transactionJson = json.loads(temptx[0][0])
            parseResult = json.loads(temptx[0][1])
            blocktxs.append({**parseResult , **transactionJson})

            # TODO (CRITICAL): Write conditions to include and filter on chain and offchain transactions
            #blocktxs['onChain'] = True
        return jsonify(transactions=blocktxs, blockKeyword=blockHash), 200
    else:
        return jsonify(description='Block doesn\'t exist in database'), 404


@app.route('/api/v2/categoriseString/<urlstring>')
async def categoriseString_v2(urlstring):
    # check if the hash is of a transaction
    response = requests.get('{}api/v1/tx/{}'.format(apiUrl, urlstring))
    if response.status_code == 200:
        return jsonify(type='transaction'), 200
    else:
        response = requests.get('{}api/v1/block/{}'.format(apiUrl, urlstring))
        if response.status_code == 200:
            return jsonify(type='block'), 200
        else:
            # check urlstring is a token name
            tokenfolder = os.path.join(dbfolder, 'tokens')
            onlyfiles = [f[:-3]
                         for f in os.listdir(tokenfolder) if os.path.isfile(os.path.join(tokenfolder, f))]
            if urlstring.lower() in onlyfiles:
                return jsonify(type='token'), 200
            else:
                systemdb = os.path.join(dbfolder, 'system.db')
                conn = sqlite3.connect(systemdb)
                conn.row_factory = lambda cursor, row: row[0]
                c = conn.cursor()
                contractList = c.execute('select contractname from activeContracts').fetchall()

                if urlstring.lower() in contractList:
                    return jsonify(type='smartContract'), 200
                else:
                    return jsonify(type='noise'), 200


@app.route('/api/v2/tokenSmartContractList', methods=['GET'])
async def tokenSmartContractList():
    # list of tokens
    filelist = []
    for item in os.listdir(os.path.join(dbfolder, 'tokens')):
        if os.path.isfile(os.path.join(dbfolder, 'tokens', item)):
            filelist.append(item[:-3])

    # list of smart contracts
    contractName = request.args.get('contractName')
    if contractName is not None:
        contractName = contractName.strip().lower()

    # todo - Add validation for contractAddress and contractName to prevent SQL injection attacks
    contractAddress = request.args.get('contractAddress')
    if contractAddress is not None:
        contractAddress = contractAddress.strip()
        if not check_flo_address(contractAddress, is_testnet):
            return jsonify(description='contractAddress validation failed'), 400
    conn = sqlite3.connect(os.path.join(dbfolder, 'system.db'))
    c = conn.cursor()
    smart_contracts = return_smart_contracts(c, contractName, contractAddress)
    smart_contracts_morphed = smartcontract_morph_helper(smart_contracts)
    conn.close()

    committeeAddressList = refresh_committee_list(APP_ADMIN, apiUrl, int(time.time()))
    return jsonify(tokens=filelist, smartContracts=smart_contracts_morphed, smartContractCommittee=committeeAddressList), 200


class ServerSentEvent:
    def __init__(
            self,
            data: str,
            *,
            event: Optional[str] = None,
            id: Optional[int] = None,
            retry: Optional[int] = None,
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

@app.route('/api/v2/prices', methods=['GET'])
async def priceData():
    # read system.db for price data
    conn = sqlite3.connect('system.db')
    c = conn.cursor()
    ratepairs = c.execute('select ratepair, price from ratepairs')
    ratepairs = ratepairs.fetchall()
    prices = {}
    for ratepair in ratepairs:
        ratepair = list(ratepair)
        prices[ratepair[0]] = ratepair[1]
    return jsonify(prices=prices), 200


#######################
#######################

# if system.db isn't present, initialize it
if not os.path.isfile(f"system.db"):
    # create an empty db
    conn = sqlite3.connect('system.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE ratepairs (id integer primary key, ratepair text, price real)''')
    c.execute("INSERT INTO ratepairs(ratepair, price) VALUES ('BTCBTC', 1)")
    c.execute("INSERT INTO ratepairs(ratepair, price) VALUES ('BTCUSD', -1)")
    c.execute("INSERT INTO ratepairs(ratepair, price) VALUES ('BTCINR', -1)")
    c.execute("INSERT INTO ratepairs(ratepair, price) VALUES ('FLOUSD', -1)")
    c.execute("INSERT INTO ratepairs(ratepair, price) VALUES ('FLOINR', -1)")
    c.execute("INSERT INTO ratepairs(ratepair, price) VALUES ('USDINR', -1)")
    conn.commit()
    conn.close()

    # update the prices once
    updatePrices()

# assign a scheduler for updating prices in the background
scheduler = BackgroundScheduler()
scheduler.add_job(func=updatePrices, trigger="interval", seconds=7200)
scheduler.start()
# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    app.run(debug=debug_status, host=HOST, port=PORT)
