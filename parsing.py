import re
import arrow

marker = None
operation = None
address = None
amount = None

months = { 'jan' : 1,
'feb' : 2,
'mar' : 3,
'apr' : 4,
'may' : 5,
'jun' : 6,
'jul' : 7,
'aug' : 8,
'sep' : 9,
'oct' : 10,
'nov' : 11,
'dec' : 12 }


def isTransfer(text):
    wordlist = ['transfer','send','give'] # keep everything lowercase
    textList = text.split(' ')
    for word in wordlist:
        if word in textList:
            return True
    return False


def isIncorp(text):
    wordlist = ['incorporate','create','start'] # keep everything lowercase
    textList = text.split(' ')
    for word in wordlist:
        if word in textList:
            return True
    return False


def isSmartContract(text):
    textList = text.split(' ')
    for word in textList:
        if word == '':
            continue
        if word.endswith('@') and len(word) != 1:
            return word
    return False


def isSmartContractPay(text):
    wordlist = text.split(' ')
    if len(wordlist) != 2:
        return False
    smartContractTrigger = re.findall(r"smartContractTrigger:'.*'", text)[0].split('smartContractTrigger:')[1]
    smartContractTrigger = smartContractTrigger[1:-1]
    smartContractName = re.findall(r"smartContractName:.*@", text)[0].split('smartContractName:')[1]
    smartContractName = smartContractName[:-1]

    if smartContractTrigger and smartContractName:
        contractconditions = { 'smartContractTrigger':smartContractTrigger, 'smartContractName':smartContractName }
        return contractconditions
    else:
        return False


def extractAmount(text, marker):
    count = 0
    returnval = None
    splitText = text.split('userchoice')[0].split(' ')

    for word in splitText:
        word = word.replace(marker, '')
        try:
            float(word)
            count = count + 1
            returnval = float(word)
        except ValueError:
            pass

        if count > 1:
            return 'Too many'
    return returnval


def extractMarker(text):
    textList = text.split(' ')
    for word in textList:
        if word == '':
            continue
        if word.endswith('#') and len(word) != 1:
            return word
    return False


def extractInitTokens(text):
    base_units = {'thousand':10**3 , 'million':10**6 ,'billion':10**9, 'trillion':10**12}
    textList = text.split(' ')
    counter = 0
    value = None
    for idx,word in enumerate(textList):
        try:
            result = float(word)
            if textList[idx + 1] in base_units:
                value = result * base_units[textList[idx + 1]]
                counter = counter + 1
            else:
                value = result
                counter = counter + 1
        except:
            for unit in base_units:
                result = word.split(unit)
                if len(result) == 2 and result[1]=='' and result[0]!='':
                    try:
                        value = float(result[0])*base_units[unit]
                        counter = counter + 1
                    except:
                        continue

    if counter == 1:
        return value
    else:
        return None


def extractAddress(text):
    textList = text.split(' ')
    for word in textList:
        if word == '':
            continue
        if word[-1] == '$' and len(word) != 1:
            return word
    return None


def extractContractType(text):
    operationList = ['one-time-event*'] # keep everything lowercase
    count = 0
    returnval = None
    for operation in operationList:
        count = count + text.count(operation)
        if count > 1:
            return 'Too many'
        if count == 1 and (returnval is None):
            returnval = operation
    return returnval


def extractUserchoice(text):
    result = re.split('userchoice:\s*', text)
    if len(result) != 1 and result[1]!='':
        return result[1].strip().strip('"').strip("'")
    else:
        return None


def brackets_toNumber(item):
    return float(item[1:-1])


def extractContractConditions(text, contracttype, marker, blocktime):
    rulestext = re.split('contract-conditions:\s*', text)[-1]
    #rulelist = re.split('\d\.\s*', rulestext)
    rulelist = []
    numberList = re.findall(r'\(\d\d*\)', rulestext)

    for idx,item in enumerate(numberList):
        numberList[idx] = int(item[1:-1])

    numberList = sorted(numberList)
    for idx, item in enumerate(numberList):
        if numberList[idx] + 1 != numberList[idx + 1]:
            print('Contract condition numbers are not in order')
            return None
        if idx == len(numberList) - 2:
            break

    for i in range(len(numberList)):
        rule = rulestext.split('({})'.format(i+1))[1].split('({})'.format(i+2))[0]
        rulelist.append(rule.strip())

    if contracttype == 'one-time-event*':
        extractedRules = {}

        for rule in rulelist:
            if rule == '':
                continue
            elif rule[:10] == 'expirytime':
                expirytime = re.split('expirytime[\s]*=[\s]*', rule)[1].strip()

                try:
                    expirytime_split = expirytime.split(' ')
                    parse_string = '{}/{}/{} {}'.format(expirytime_split[3], months[expirytime_split[1]], expirytime_split[2], expirytime_split[4])
                    expirytime_object = arrow.get(parse_string, 'YYYY/M/D HH:mm:ss').replace(tzinfo=expirytime_split[5])
                    blocktime_object = arrow.get(blocktime)
                    if expirytime_object < blocktime_object:
                        print('Expirytime of the contract is earlier than the block it is incorporated in. This incorporation will be rejected ')
                        return None
                    extractedRules['expiryTime'] = expirytime
                except:
                    print('Expiry time not in right format')
                    return None

        for rule in rulelist:
            if rule=='':
                continue
            elif rule[:14] == 'contractamount':
                pattern = re.compile('[^contractamount\s*=\s*].*')
                searchResult = pattern.search(rule).group(0)
                contractamount = searchResult.split(marker)[0]
                try:
                    extractedRules['contractAmount'] = float(contractamount)
                except:
                    print("something is wrong with contract amount entered")
            elif rule[:11] == 'userchoices':
                pattern = re.compile('[^userchoices\s*=\s*].*')
                conditions = pattern.search(rule).group(0)
                conditionlist = conditions.split('|')
                extractedRules['userchoices'] = {}
                for idx, condition in enumerate(conditionlist):
                    extractedRules['userchoices'][idx] = condition.strip()
            elif rule[:25] == 'minimumsubscriptionamount':
                pattern = re.compile('[^minimumsubscriptionamount\s*=\s*].*')
                searchResult = pattern.search(rule).group(0)
                minimumsubscriptionamount = searchResult.split(marker)[0]
                try:
                    extractedRules['minimumsubscriptionamount'] = float(minimumsubscriptionamount)
                except:
                    print("something is wrong with minimum subscription amount entered")
            elif rule[:25] == 'maximumsubscriptionamount':
                pattern = re.compile('[^maximumsubscriptionamount\s*=\s*].*')
                searchResult = pattern.search(rule).group(0)
                maximumsubscriptionamount = searchResult.split(marker)[0]
                try:
                    extractedRules['maximumsubscriptionamount'] = float(maximumsubscriptionamount)
                except:
                    print("something is wrong with maximum subscription amount entered")
            elif rule[:12] == 'payeeAddress':
                pattern = re.compile('[^payeeAddress\s*=\s*].*')
                searchResult = pattern.search(rule).group(0)
                payeeAddress = searchResult.split(marker)[0]
                extractedRules['payeeAddress'] = payeeAddress


        if len(extractedRules)>1 and 'expiryTime' in extractedRules:
            return extractedRules
        else:
            return None
    return None


def extractTriggerCondition(text):
    searchResult = re.search('\".*\"', text)
    if searchResult is None:
        searchResult = re.search('\'.*\'', text)
        return searchResult
    return searchResult


# Combine test
def parse_flodata(string, blockinfo):

    # todo Rule 20 - remove 'text:' from the start of flodata if it exists
    if string[0:5] == 'text:':
        string = string.split('text:')[1]

    # todo Rule 21 - Collapse multiple spaces into a single space in the whole of flodata
    # todo Rule 22 - convert flodata to lowercase to make the system case insensitive
    nospacestring = re.sub(' +', ' ', string)
    cleanstring = nospacestring.lower()

    # todo Rule 23 - Count number of words ending with @ and #
    atList = []
    hashList = []

    for word in cleanstring.split(' '):
        if word.endswith('@') and len(word) != 1:
            atList.append(word)
        if word.endswith('#') and len(word) != 1:
            hashList.append(word)

    # todo Rule 24 - Reject the following conditions - a. number of # & number of @ is equal to 0 then reject
    # todo Rule 25 - If number of # or number of @ is greater than 1, reject
    # todo Rule 25.a - If a transaction is rejected, it means parsed_data type is noise
    # Filter noise first - check if the words end with either @ or #
    if (len(atList)==0 and len(hashList)==0) or len(atList)>1 or len(hashList)>1:
        parsed_data = {'type': 'noise'}

    # todo Rule 26 - if number of # is 1 and number of @ is 0, then check if its token creation or token transfer transaction

    elif len(hashList)==1 and len(atList)==0:
        # Passing the above check means token creation or transfer
        incorporation = isIncorp(cleanstring)
        transfer = isTransfer(cleanstring)

        # todo Rule 27 - if (neither token incorporation and token transfer) OR both token incorporation and token transfer, reject
        if (not incorporation and not transfer) or (incorporation and transfer):
            parsed_data = {'type': 'noise'}

        # todo Rule 28 - if token creation and not token transfer then it is confirmed that is it a token creation transaction
        # todo Rule 29 - Extract total number of tokens issued, if its not mentioned then reject
        elif incorporation and not transfer:
            initTokens = extractInitTokens(cleanstring)
            if initTokens is not None:
                parsed_data = {'type': 'tokenIncorporation', 'flodata': string, 'tokenIdentification': hashList[0][:-1],
                           'tokenAmount': initTokens}
            else:
                parsed_data = {'type': 'noise'}

        # todo Rule 30 - if not token creation and is token transfer then then process it for token transfer rules
        # todo Rule 31 - Extract number of tokens to be sent and the address to which to be sent, both data is mandatory
        elif not incorporation and transfer:
            amount = extractAmount(cleanstring, hashList[0][:-1])
            if None not in [amount]:
                parsed_data = {'type': 'transfer', 'transferType': 'token', 'flodata': string,
                           'tokenIdentification': hashList[0][:-1],
                           'tokenAmount': amount}
            else:
                parsed_data = {'type': 'noise'}

    # todo Rule 32 - if number of # is 1 and number of @ is 1, then process for smart contract transfer or creation
    elif len(hashList)==1 and len(atList)==1:
        # Passing the above check means Smart Contract creation or transfer
        incorporation = isIncorp(cleanstring)
        transfer = isTransfer(cleanstring)

        # todo Rule 33 - if a confusing smart contract command is given, like creating and sending at the same time, or no
        if (not incorporation and not transfer) or (incorporation and transfer):
            parsed_data = {'type': 'noise'}

        # todo Rule 34 - if incorporation and not transfer, then extract type of contract, address of the contract and conditions of the contract. Reject if any of those is not present
        elif incorporation and not transfer:
            contracttype = extractContractType(cleanstring)
            contractaddress = extractAddress(nospacestring)
            contractconditions = extractContractConditions(cleanstring, contracttype, marker=hashList[0][:-1], blocktime=blockinfo['time'])

            if None not in [contracttype, contractaddress, contractconditions]:
                parsed_data = {'type': 'smartContractIncorporation', 'contractType': contracttype[:-1],
                           'tokenIdentification': hashList[0][:-1], 'contractName': atList[0][:-1],
                           'contractAddress': contractaddress[:-1], 'flodata': string,
                           'contractConditions': contractconditions}
            else:
                parsed_data = {'type': 'noise'}

        # todo Rule 35 - if it is not incorporation and it is transfer, then extract smart contract amount to be locked and userPreference. If any of them is missing, then reject
        elif not incorporation and transfer:
            # We are at the send/transfer of smart contract
            amount = extractAmount(cleanstring, hashList[0][:-1])
            userChoice = extractUserchoice(cleanstring)
            contractaddress = extractAddress(nospacestring)
            if None not in [amount, userChoice]:
                parsed_data = {'type': 'transfer', 'transferType': 'smartContract', 'flodata': string,
                           'tokenIdentification': hashList[0][:-1],
                           'operation': 'transfer', 'tokenAmount': amount, 'contractName': atList[0][:-1],
                           'userChoice': userChoice}
                if contractaddress:
                    parsed_data['contractAddress'] = contractaddress[:-1]
            else:
                parsed_data = {'type': 'noise'}


    # todo Rule 36 - Check for only a single @ and the substring "smart contract system says" in flodata, else reject
    elif (len(hashList)==0 and len(atList)==1):
        # Passing the above check means Smart Contract pays | exitcondition triggered from the committee
        # todo Rule 37 - Extract the trigger condition given by the committee. If its missing, reject
        triggerCondition = extractTriggerCondition(cleanstring)
        if triggerCondition is not None:
            parsed_data = {'type': 'smartContractPays', 'contractName': atList[0][:-1], 'triggerCondition': triggerCondition.group().strip()[1:-1]}
        else:
            parsed_data = {'type':'noise'}
    else:
        parsed_data = {'type': 'noise'}

    return parsed_data
