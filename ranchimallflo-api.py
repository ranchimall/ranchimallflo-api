from flask import render_template, flash, redirect, url_for, request, jsonify
from collections import defaultdict
import sqlite3
import json
import os
from flask import Flask

dbfolder = ''
app = Flask(__name__)

@app.route('/api/v1.0/getsmartContractlist', methods=['GET'])
def getcontractlist():
    '''token = request.args.get('token')

    if token is None:
        return jsonify(result='error')'''
    filelist = []
    for item in os.listdir(os.path.join(dbfolder,'smartContracts')):
        if os.path.isfile(os.path.join(dbfolder, 'smartContracts', item)):
            filelist.append(item[:-3])

    return jsonify(smartContracts = filelist, result='ok')

@app.route('/api/v1.0/getsmartContractinfo', methods=['GET'])
def getcontractinfo():
    name = request.args.get('name')
    contractAddress = request.args.get('contractAddress')

    if name is None:
        return jsonify(result='error', details='Smart Contract\'s name hasn\'t been passed')

    if contractAddress is None:
        return jsonify(result='error', details='Smart Contract\'s address hasn\'t been passed')

    contractName = '{}-{}.db'.format(name.strip(),contractAddress.strip())
    filelocation = os.path.join(dbfolder,'smartContracts', contractName)

    if os.path.isfile(filelocation):
        #Make db connection and fetch data
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
        return jsonify(result='ok', contractInfo=returnval)

    else:
        return jsonify(result='error', details='Smart Contract with the given name doesn\'t exist')

    #return jsonify('smartContracts' : filelist, result='ok')

@app.route('/api/v1.0/getsmartContractparticipants', methods=['GET'])
def getcontractparticipants():
    name = request.args.get('name')
    contractAddress = request.args.get('contractAddress')

    if name is None:
        return jsonify(result='error', details='Smart Contract\'s name hasn\'t been passed')

    if contractAddress is None:
        return jsonify(result='error', details='Smart Contract\'s address hasn\'t been passed')

    contractName = '{}-{}.db'.format(name.strip(),contractAddress.strip())
    filelocation = os.path.join(dbfolder,'smartContracts', contractName)

    if os.path.isfile(filelocation):
        #Make db connection and fetch data
        conn = sqlite3.connect(filelocation)
        c = conn.cursor()
        c.execute(
            'SELECT id,participantAddress, tokenAmount, userChoice FROM contractparticipants')
        result = c.fetchall()
        conn.close()
        returnval = {}
        for row in result:
            returnval[row[0]] = [row[1],row[2],row[3]]

        return jsonify(result='ok', participantInfo=returnval)

    else:
        return jsonify(result='error', details='Smart Contract with the given name doesn\'t exist')

@app.route('/api/v1.0/getParticipantDetails', methods=['GET'])
def getParticipantDetails():
    floaddress = request.args.get('floaddress')

    if name is floaddress:
        return jsonify(result='error', details='FLO address hasn\'t been passed')

    filelocation = os.path.join(dbfolder,'system.db')

    if os.path.isfile(filelocation):
        #Make db connection and fetch data
        conn = sqlite3.connect(filelocation)
        c = conn.cursor()
        c.execute(
            'SELECT id,participantAddress, tokenAmount, userChoice FROM contractparticipants')
        result = c.fetchall()
        conn.close()
        returnval = {}
        for row in result:
            returnval[row[0]] = [row[1],row[2],row[3]]

        return jsonify(result='ok', participantInfo=returnval)

    else:
        return jsonify(result='error', details='Smart Contract with the given name doesn\'t exist')


@app.route('/test')
def test():
    return render_template('test.html')

if __name__ == "__main__":
    app.run(debug=True)

