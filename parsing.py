import pdb
import re
import arrow
import pyflo
import logging
import json

""" 
Find make lists of #, *, @ words 

If only 1 hash word and nothing else, then it is token related ( tokencreation or tokentransfer ) 

If @ is present, then we know it is smart contract related 
   @ (#)pre:       -  participation , deposit 
   @ * (#)pre:     -  one time event creation 
   @ * (# #)post:  -  token swap creation 
   @               -  trigger 

Check for 1 @ only 
Check for 1 # only 
Check for @ (#)pre: 
Check for @ * (#)pre: 
Check for @ * (# #)post: 

special_character_frequency = { 
    'precolon': { 
        '#':0, 
        '*':0,
        '@':0,
        ':':0
}

for word in allList:
    if word.endswith('#'):
        special_character_frequency['#'] = special_character_frequency['#'] + 1
    elif word.endswith('*'):
        special_character_frequency['*'] = special_character_frequency['*'] + 1
    elif word.endswith('@'):
        special_character_frequency['@'] = special_character_frequency['@'] + 1
    elif word.endswith(':'):
        special_character_frequency[':'] = special_character_frequency[':'] + 1

""" 

'''
def className(rawstring):
    # Create a list that contains @ , # , * and : ; in actual order of occurence with their words. Only : is allowed to exist without a word in front of it. 
    # Check for 1 @ only followed by :, and the class is trigger
    # Check for 1 # only, then the class is tokensystem
    # Check for @ in the first position, * in the second position, # in the third position and : in the fourth position, then class is one time event creation 
    # Check for @ in the first position, * in the second position and : in the third position, then hash is in 4th position, then hash in 5th position | Token swap creation 

    allList = findrules(rawstring,['#','*','@',':'])

    pattern_list1 = ['rmt@','rmt*',':',"rmt#","rmt#"]
    pattern_list2 = ['rmt#',':',"rmt@"]
    pattern_list3 = ['rmt#']
    pattern_list4 = ["rmt@","one-time-event*","floAddress$",':',"rupee#","bioscope#"]
    patternmatch = find_first_classification(pattern_list4, search_patterns)
    print(f"Patternmatch is {patternmatch}")


rawstring = "test rmt# rmt@ rmt* : rmt# rmt# test" 
#className(rawstring) '''

# Variable configurations 
search_patterns = {
    'tokensystem-C':{
        1:['#']
    },
    'smart-contract-creation-C':{
        1:['@','*','#','$',':'],
        2:['@','*','#','$',':','#']
    },
    'smart-contract-participation-deposit-C':{
        1:['#','@',':'],
        2:['#','@','$',':']
    },
    'userchoice-trigger':{
        1:['@'] 
    },
    'smart-contract-participation-ote-ce-C':{
        1:['#','@'],
        2:['#','@','$']
    },
    'smart-contract-creation-ce-tokenswap':{
        1:['@','*','$',':','#','#']
    }
}

conflict_matrix = {
    'tokensystem-C':{
        # Check for send, check for create, if both are there noise, else conflict resolved
        'tokentransfer',
        'tokencreation'
    },
    'smart-contract-creation-C':{
        # Check contract-conditions for userchoice, if present then userchoice contract, else time based contract
        'creation-one-time-event-userchoice',
        'creation-one-time-event-timebased'
    },
    'smart-contract-participation-deposit-C':{
        # Check *-word, its either one-time-event or a continuos-event
        'participation-one-time-event-userchoice',
        'deposit-continuos-event-tokenswap'
    },
    'smart-contract-participation-ote-ce-C':{
        # Check *-word, its either one-time-event or a continuos-event
        'participation-one-time-event-timebased',
        'participation-continuos-event-tokenswap'
    }
}

months = {
    'jan': 1,
    'feb': 2,
    'mar': 3,
    'apr': 4,
    'may': 5,
    'jun': 6,
    'jul': 7,
    'aug': 8,
    'sep': 9,
    'oct': 10,
    'nov': 11,
    'dec': 12
}

# HELPER FUNCTIONS 

# Find some value or return as noise 
def apply_rule1(*argv):
    a = argv[0](*argv[1:])
    if a is False:
        return False
    else:
        return a


def extract_substing_between(test_str, sub1, sub2):
    # getting index of substrings
    idx1 = test_str.index(sub1)
    idx2 = test_str.index(sub2)
    
    # length of substring 1 is added to
    # get string from next character
    res = test_str[idx1 + len(sub1) + 1: idx2]
    
    # return result
    return res

# StateF functions 
def isStateF(text):
    try:
        statef_string = extract_substing_between(text, 'statef', 'end-statef').strip()
        i=iter(statef_string.split(":"))
        statef_list = [":".join(x) for x in zip(i,i)]
        statef = {}
        for keyval in statef_list:
            keyval = keyval.split(':')
            statef[keyval[0]] = keyval[1]
        return statef
    except:
        return False


# conflict_list = [['userchoice','payeeaddress'],['userchoice','xxx']]
def resolve_incategory_conflict(input_dictionary , conflict_list):
    for conflict_pair in conflict_list:
        key0 = conflict_pair[0]
        key1 = conflict_pair[1]
        dictionary_keys = input_dictionary.keys()
        if (key0 in dictionary_keys and key1 in dictionary_keys) or (key0 not in dictionary_keys and key1 not in dictionary_keys):
            return False
        else:
            return True


def remove_empty_from_dict(d):
    if type(d) is dict:
        return dict((k, remove_empty_from_dict(v)) for k, v in d.items() if v and remove_empty_from_dict(v))
    elif type(d) is list:
        return [remove_empty_from_dict(v) for v in d if v and remove_empty_from_dict(v)]
    else:
        return d


def outputreturn(*argv):
    if argv[0] == 'noise':
        parsed_data = {'type': 'noise'}
        return parsed_data
    elif argv[0] == 'token_incorporation':
        parsed_data = {
            'type': 'tokenIncorporation',
            'flodata': argv[1], #string 
            'tokenIdentification': argv[2], #hashList[0][:-1] 
            'tokenAmount': argv[3], #initTokens
            'stateF': argv[4]
            }
        return parsed_data
    elif argv[0] == 'token_transfer':
        parsed_data = {
            'type': 'transfer', 
            'transferType': 'token', 
            'flodata': argv[1], #string
            'tokenIdentification': argv[2], #hashList[0][:-1]
            'tokenAmount': argv[3], #amount
            'stateF': argv[4]
            }
        return parsed_data
    elif argv[0] == 'one-time-event-userchoice-smartcontract-incorporation':
        parsed_data = {
            'type': 'smartContractIncorporation', 
            'contractType': 'one-time-event',
            'tokenIdentification': argv[1], #hashList[0][:-1] 
            'contractName': argv[2], #atList[0][:-1]
            'contractAddress': argv[3], #contractaddress[:-1] 
            'flodata': argv[4], #string
            'contractConditions': {
                'contractAmount' : argv[5],
                'minimumsubscriptionamount' : argv[6],
                'maximumsubscriptionamount' : argv[7],
                'userchoices' : argv[8],
                'expiryTime' : argv[9]
            },
            'stateF': argv[10]
        }
        return remove_empty_from_dict(parsed_data)
    elif argv[0] == 'one-time-event-userchoice-smartcontract-participation':
        parsed_data = {
            'type': 'transfer', 
            'transferType': 'smartContract', 
            'flodata': argv[1], #string
            'tokenIdentification': argv[2], #hashList[0][:-1]
            'operation': 'transfer', 
            'tokenAmount': argv[3], #amount 
            'contractName': argv[4], #atList[0][:-1]
            'contractAddress': argv[5],
            'userChoice': argv[6], #userChoice
            'stateF': argv[7]
            }
        return remove_empty_from_dict(parsed_data)
    elif argv[0] == 'one-time-event-userchoice-smartcontract-trigger':
        parsed_data = {
            'type': 'smartContractPays', 
            'contractName': argv[1], #atList[0][:-1] 
            'triggerCondition': argv[2], #triggerCondition.group().strip()[1:-1]
            'stateF': argv[3]
            }
        return parsed_data
    elif argv[0] == 'one-time-event-time-smartcontract-incorporation':
        parsed_data = {
            'type': 'smartContractIncorporation', 
            'contractType': 'one-time-event',
            'tokenIdentification': argv[1], #hashList[0][:-1] 
            'contractName': argv[2], #atList[0][:-1]
            'contractAddress': argv[3], #contractaddress[:-1] 
            'flodata': argv[4], #string
            'contractConditions': {
                'contractAmount' : argv[5],
                'minimumsubscriptionamount' : argv[6],
                'maximumsubscriptionamount' : argv[7],
                'payeeAddress' : argv[8],
                'expiryTime' : argv[9]
            },
            'stateF': argv[10]
        }
        return remove_empty_from_dict(parsed_data)
    elif argv[0] == 'continuos-event-token-swap-incorporation':
        parsed_data = {
            'type': 'smartContractIncorporation', 
            'contractType': 'continuos-event',
            'tokenIdentification': argv[1], #hashList[0][:-1] 
            'contractName': argv[2], #atList[0][:-1]
            'contractAddress': argv[3], #contractaddress[:-1] 
            'flodata': argv[4], #string
            'contractConditions': {
                'subtype' : argv[5], #tokenswap
                'accepting_token' : argv[6],
                'selling_token' : argv[7],
                'pricetype' : argv[8],
                'price' : argv[9],
            },
            'stateF': argv[10]
        }
        return parsed_data
    elif argv[0] == 'continuos-event-token-swap-deposit':
        parsed_data = {
            'type': 'smartContractDeposit',
            'tokenIdentification': argv[1], #hashList[0][:-1]
            'depositAmount': argv[2], #depositAmount 
            'contractName': argv[3], #atList[0][:-1] 
            'flodata': argv[4], #string
            'depositConditions': {
                'expiryTime' : argv[5]
            },
            'stateF': argv[6]
        }
        return parsed_data
    elif argv[0] == 'smart-contract-one-time-event-continuos-event-participation':
        parsed_data = {
            'type': 'transfer', 
            'transferType': 'smartContract', 
            'flodata': argv[1], #string 
            'tokenIdentification': argv[2], #hashList[0][:-1] 
            'tokenAmount': argv[3], #amount 
            'contractName': argv[4], #atList[0][:-1] 
            'contractAddress': argv[5],
            'stateF': argv[6]
            }
        return remove_empty_from_dict(parsed_data)
    elif argv[0] == 'nft_create':
        parsed_data = {
            'type': 'nftIncorporation',
            'flodata': argv[1], #string 
            'tokenIdentification': argv[2], #hashList[0][:-1] 
            'tokenAmount': argv[3], #initTokens,
            'nftHash': argv[4], #nftHash
            'stateF': argv[5]
            }
        return parsed_data
    elif argv[0] == 'nft_transfer':
        parsed_data = {
            'type': 'transfer',
            'transferType': 'nft',
            'flodata': argv[1], #string 
            'tokenIdentification': argv[2], #hashList[0][:-1] 
            'tokenAmount': argv[3], #initTokens,
            'stateF': argv[4]
            }
        return parsed_data
    elif argv[0] == 'infinite_token_create':
        parsed_data = {
            'type': 'infiniteTokenIncorporation',
            'flodata': argv[1], #string 
            'tokenIdentification': argv[2], #hashList[0][:-1] 
            'stateF': argv[3]
            }
        return parsed_data


def extract_specialcharacter_words(rawstring, special_characters):
    wordList = []
    for word in rawstring.split(' '):
        if (len(word) not in [0,1] or word==":") and word[-1] in special_characters:
            wordList.append(word)
    return wordList


def extract_contract_conditions(text, contract_type, marker=None, blocktime=None):
    try:
        rulestext = extract_substing_between(text, 'contract-conditions', 'end-contract-conditions')
    except:
        return False
    if rulestext.strip()[0] == ':':
        rulestext = rulestext.strip()[1:].strip()
    #rulestext = re.split('contract-conditions:\s*', text)[-1]
    # rulelist = re.split('\d\.\s*', rulestext)
    rulelist = []
    numberList = re.findall(r'\(\d\d*\)', rulestext)

    for idx, item in enumerate(numberList):
        numberList[idx] = int(item[1:-1])

    numberList = sorted(numberList)
    for idx, item in enumerate(numberList):
        if numberList[idx] + 1 != numberList[idx + 1]:
            logger.info('Contract condition numbers are not in order')
            return False
        if idx == len(numberList) - 2:
            break

    for i in range(len(numberList)):
        rule = rulestext.split('({})'.format(i + 1))[1].split('({})'.format(i + 2))[0]
        rulelist.append(rule.strip())

    if contract_type == 'one-time-event':
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
                        logger.info('Expirytime of the contract is earlier than the block it is incorporated in. This incorporation will be rejected ')
                        return False
                    extractedRules['expiryTime'] = expirytime
                except:
                    logger.info('Error parsing expiry time')
                    return False

        for rule in rulelist:
            if rule == '':
                continue
            elif rule[:14] == 'contractamount':
                pattern = re.compile('(^contractamount\s*=\s*)(.*)')
                searchResult = pattern.search(rule).group(2)
                contractamount = searchResult.split(marker)[0]
                try:
                    extractedRules['contractAmount'] = float(contractamount)
                except:
                    logger.info("Contract amount entered is not a decimal")
            elif rule[:11] == 'userchoices':
                pattern = re.compile('(^userchoices\s*=\s*)(.*)')
                conditions = pattern.search(rule).group(2)
                conditionlist = conditions.split('|')
                extractedRules['userchoices'] = {}
                for idx, condition in enumerate(conditionlist):
                    extractedRules['userchoices'][idx] = condition.strip()
            elif rule[:25] == 'minimumsubscriptionamount':
                pattern = re.compile('(^minimumsubscriptionamount\s*=\s*)(.*)')
                searchResult = pattern.search(rule).group(2)
                minimumsubscriptionamount = searchResult.split(marker)[0]
                try:
                    extractedRules['minimumsubscriptionamount'] = float(minimumsubscriptionamount)
                except:
                    logger.info("Minimum subscription amount entered is not a decimal")
            elif rule[:25] == 'maximumsubscriptionamount':
                pattern = re.compile('(^maximumsubscriptionamount\s*=\s*)(.*)')
                searchResult = pattern.search(rule).group(2)
                maximumsubscriptionamount = searchResult.split(marker)[0]
                try:
                    extractedRules['maximumsubscriptionamount'] = float(maximumsubscriptionamount)
                except:
                    logger.info("Maximum subscription amount entered is not a decimal")
            elif rule[:12] == 'payeeaddress':
                pattern = re.compile('(^payeeaddress\s*=\s*)(.*)')
                searchResult = pattern.search(rule).group(2)
                payeeAddress = searchResult.split(marker)[0]
                extractedRules['payeeAddress'] = payeeAddress

        if len(extractedRules) > 1 and 'expiryTime' in extractedRules:
            return extractedRules
        else:
            return False

    elif contract_type == 'continuous-event':
        extractedRules = {}
        for rule in rulelist:
            if rule == '':
                continue
            elif rule[:7] == 'subtype':
                # todo : recheck the regular expression for subtype, find an elegant version which covers all permutations and combinations
                pattern = re.compile('(^subtype\s*=\s*)(.*)')
                subtype = pattern.search(rule).group(2)
                extractedRules['subtype'] = subtype
            elif rule[:15] == 'accepting_token':
                pattern = re.compile('(?<=accepting_token\s=\s)(.*)(?<!#)')
                accepting_token = pattern.search(rule).group(1)
                extractedRules['accepting_token'] = accepting_token
            elif rule[:15] == 'acceptingToken':
                pattern = re.compile('(?<=acceptingToken\s=\s)(.*)(?<!#)')
                accepting_token = pattern.search(rule).group(1)
                extractedRules['accepting_token'] = accepting_token
            elif rule[:13] == 'selling_token':
                pattern = re.compile('(?<=selling_token\s=\s)(.*)(?<!#)')
                selling_token = pattern.search(rule).group(1)
                extractedRules['selling_token'] = selling_token
            elif rule[:13] == 'sellingToken':
                pattern = re.compile('(?<=sellingToken\s=\s)(.*)(?<!#)')
                selling_token = pattern.search(rule).group(1)
                extractedRules['selling_token'] = selling_token
            elif rule[:9] == 'pricetype':
                pattern = re.compile('(^pricetype\s*=\s*)(.*)')
                priceType = pattern.search(rule).group(2)
                priceType = priceType.replace("'","").replace('"', '')
                extractedRules['priceType'] = priceType
            elif rule[:5] == 'price':
                pattern = re.compile('(^price\s*=\s*)(.*)')
                price = pattern.search(rule).group(2)
                if price[0]=="'" or price[0]=='"':
                    price = price[1:]
                if price[-1]=="'" or price[-1]=='"':
                    price = price[:-1]
                extractedRules['price'] = float(price)
            elif rule[:9].lower() == 'direction':
                pattern = re.compile('(?<=direction\s=\s)(.*)')
                direction = pattern.search(rule).group(1)
                extractedRules['direction'] = direction
        
        if len(extractedRules) > 1:
            return extractedRules
        else:
            return False
    return False


def extract_tokenswap_contract_conditions(processed_text, contract_type, contract_token):
    rulestext = re.split('contract-conditions:\s*', processed_text)[-1]
    rulelist = []
    numberList = re.findall(r'\(\d\d*\)', rulestext)

    for idx, item in enumerate(numberList):
        numberList[idx] = int(item[1:-1])

    numberList = sorted(numberList)
    for idx, item in enumerate(numberList):
        if numberList[idx] + 1 != numberList[idx + 1]:
            logger.info('Contract condition numbers are not in order')
            return False
        if idx == len(numberList) - 2:
            break

    for i in range(len(numberList)):
        rule = rulestext.split('({})'.format(i + 1))[1].split('({})'.format(i + 2))[0]
        rulelist.append(rule.strip())

    if contract_type == 'continuous-event':
        extractedRules = {}
        for rule in rulelist:
            if rule == '':
                continue
            elif rule[:7] == 'subtype':
                # todo : recheck the regular expression for subtype, find an elegant version which covers all permutations and combinations
                pattern = re.compile('(^subtype\s*=\s*)(.*)')
                searchResult = pattern.search(rule).group(2)
                subtype = searchResult.split(marker)[0]
                #extractedRules['subtype'] = rule.split('=')[1].strip()
                extractedRules['subtype'] = subtype
            elif rule[:15] == 'accepting_token':
                pattern = re.compile('(?<=accepting_token\s=\s).*(?<!#)')
                accepting_token = pattern.search(rule).group(0)
                extractedRules['accepting_token'] = accepting_token
            elif rule[:13] == 'selling_token':
                pattern = re.compile('(?<=selling_token\s=\s).*(?<!#)')
                selling_token = pattern.search(rule).group(0)
                extractedRules['selling_token'] = selling_token
            elif rule[:9].lower() == 'pricetype':
                pattern = re.compile('[^pricetype\s*=\s*].*')
                priceType = pattern.search(rule).group(0)
                extractedRules['priceType'] = priceType
            elif rule[:5] == 'price':
                pattern = re.compile('[^price\s*=\s*].*')
                price = pattern.search(rule).group(0)
                if price[0]=="'" or price[0]=='"':
                    price = price[1:]
                if price[-1]=="'" or price[-1]=='"':
                    price = price[:-1]
                extractedRules['price'] = float(price)
            elif rule[:9].lower() == 'direction':
                pattern = re.compile('(?<=direction\s=\s).*')
                direction = pattern.search(rule).group(0)
                extractedRules['direction'] = direction

        if len(extractedRules) > 1:
            return extractedRules
        else:
            return False
    
    return False


def extract_deposit_conditions(text, blocktime=None):
    rulestext = re.split('deposit-conditions:\s*', text)[-1]
    # rulelist = re.split('\d\.\s*', rulestext)
    rulelist = []
    numberList = re.findall(r'\(\d\d*\)', rulestext)
    for idx, item in enumerate(numberList):
        numberList[idx] = int(item[1:-1])

    numberList = sorted(numberList)
    for idx, item in enumerate(numberList):
        if len(numberList) > 1 and numberList[idx] + 1 != numberList[idx + 1]:
            logger.info('Deposit condition numbers are not in order')
            return False
        if idx == len(numberList) - 2:
            break

    for i in range(len(numberList)):
        rule = rulestext.split('({})'.format(i + 1))[1].split('({})'.format(i + 2))[0]
        rulelist.append(rule.strip())

    # elif contracttype == 'continuous-event*':
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
                    logger.info('Expirytime of the contract is earlier than the block it is incorporated in. This incorporation will be rejected ')
                    return False
                extractedRules['expiryTime'] = expirytime
            except:
                logger.info('Error parsing expiry time')
                return False

    """for rule in rulelist:
        if rule == '':
            continue
        elif rule[:7] == 'subtype':
            subtype=rule[8:]
            #pattern = re.compile('[^subtype\s*=\s*].*')
            #searchResult = pattern.search(rule).group(0)
            #contractamount = searchResult.split(marker)[0]
            extractedRules['subtype'] = subtype    """

    if len(extractedRules) > 0:
        return extractedRules
    else:
        return False


def extract_special_character_word(special_character_list, special_character):
    for word in special_character_list:
        if word.endswith(special_character):
            return word[:-1]
    return False


def extract_NFT_hash(clean_text):
    nft_hash = re.search(r"(?:0[xX])?[0-9a-fA-F]{64}",clean_text)
    if nft_hash is None:
        return False
    else:
        return nft_hash.group(0)


def find_original_case(contract_address, original_text):
    dollar_word = extract_specialcharacter_words(original_text,["$"])
    if len(dollar_word)==1 and dollar_word[0][:-1].lower()==contract_address:
        return dollar_word[0][:-1]
    else:
        None


def find_word_index_fromstring(originaltext, word):
    lowercase_text = originaltext.lower()
    result = lowercase_text.find(word)
    return originaltext[result:result+len(word)]


def find_first_classification(parsed_word_list, search_patterns):
    for first_classification in search_patterns.keys():
        counter = 0
        for key in search_patterns[first_classification].keys():
            if checkSearchPattern(parsed_word_list, search_patterns[first_classification][key]):
                return {'categorization':f"{first_classification}",'key':f"{key}",'pattern':search_patterns[first_classification][key], 'wordlist':parsed_word_list}
    return {'categorization':"noise"}


def sort_specialcharacter_wordlist(inputlist):
    weight_values = {
        '@': 5,
        '*': 4,
        '#': 3,
        '$': 2
    }
    
    weightlist = []
    for word in inputlist:
        if word.endswith("@"):
            weightlist.append(5)
        elif word.endswith("*"):
            weightlist.append(4)
        elif word.endswith("#"):
            weightlist.append(4)
        elif word.endswith("$"):
            weightlist.append(4)


def firstclassification_rawstring(rawstring):
    specialcharacter_wordlist = extract_specialcharacter_words(rawstring,['@','*','$','#',':'])    
    first_classification = find_first_classification(specialcharacter_wordlist, search_patterns)
    return first_classification


def checkSearchPattern(parsed_list, searchpattern):
    if len(parsed_list)!=len(searchpattern):
        return False
    else:
        for idx,val in enumerate(parsed_list):
            if not parsed_list[idx].endswith(searchpattern[idx]):
                return False
        return True


def extractAmount_rule_new(text):
    base_units = {'thousand': 10 ** 3, 'k': 10 ** 3, 'million': 10 ** 6, 'm': 10 ** 6, 'billion': 10 ** 9, 'b': 10 ** 9, 'trillion': 10 ** 12, 'lakh':10 ** 5, 'crore':10 ** 7, 'quadrillion':10 ** 15}
    amount_tuple = re.findall(r'\b(-?[.\d]+)\s*(thousand|million|billion|trillion|m|b|t|k|lakh|crore|quadrillion)*\b', text)
    if len(amount_tuple) > 1 or len(amount_tuple) == 0:
        return False
    else:
        amount_tuple_list = list(amount_tuple[0])
        extracted_amount = float(amount_tuple_list[0])
        extracted_base_unit = amount_tuple_list[1]
        if extracted_base_unit in base_units.keys():
            extracted_amount = float(extracted_amount) * base_units[extracted_base_unit]
        return extracted_amount

def extractAmount_rule_new1(text, split_word=None, split_direction=None):
    base_units = {'thousand': 10 ** 3, 'k': 10 ** 3, 'million': 10 ** 6, 'm': 10 ** 6, 'billion': 10 ** 9, 'b': 10 ** 9, 'trillion': 10 ** 12, 'lakh':10 ** 5, 'crore':10 ** 7, 'quadrillion':10 ** 15}
    if split_word and split_direction:
        if split_direction=='pre':
            text = text.split(split_word)[0]
        if split_direction=='post':
            text = text.split(split_word)[1]

    # appending dummy because the regex does not recognize a number at the start of a string
    # text = f"dummy {text}"
    text = text.replace("'", "")
    text = text.replace('"', '')
    amount_tuple = re.findall(r'\b(-?[.\d]+)\s*(thousand|million|billion|trillion|m|b|t|k|lakh|crore|quadrillion)*\b', text)
    if len(amount_tuple) > 1 or len(amount_tuple) == 0:
        return False
    else:
        amount_tuple_list = list(amount_tuple[0])
        extracted_amount = float(amount_tuple_list[0])
        extracted_base_unit = amount_tuple_list[1]
        if extracted_base_unit in base_units.keys():
            extracted_amount = float(extracted_amount) * base_units[extracted_base_unit]
        return extracted_amount


def extract_userchoice(text):
    result = re.split('userchoice:\s*', text)
    if len(result) != 1 and result[1] != '':
        return result[1].strip().strip('"').strip("'")
    else:
        return False


def findWholeWord(w):
    return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search


def check_flo_address(floaddress, is_testnet):
    if pyflo.is_address_valid(floaddress, testnet=is_testnet):
        return floaddress
    else:
        return False


def extract_trigger_condition(text):
    searchResult = re.search('\".*\"', text)
    if searchResult is None:
        searchResult = re.search('\'.*\'', text)

    if searchResult is not None:
        return searchResult.group().strip()[1:-1]
    else: 
        return False


# Regex pattern for Smart Contract and Token name ^[A-Za-z][A-Za-z0-9_-]*[A-Za-z0-9]$
def check_regex(pattern, test_string):
    matched = re.match(pattern, test_string)
    is_match = bool(matched)
    return is_match


def check_existence_of_keyword(inputlist, keywordlist):
    for word in keywordlist:
       if not word in inputlist:
           return False
    return True


def check_word_existence_instring(word, text):
    word_exists = re.search(fr"\b{word}\b",text)
    if word_exists is None:
        return False
    else:
        return word_exists.group(0)

send_category = ['transfer', 'send', 'give']  # keep everything lowercase
create_category = ['incorporate', 'create', 'start']  # keep everything lowercase
deposit_category = ['submit','deposit']


def truefalse_rule2(rawstring, permitted_list, denied_list):
    # Find transfer , send , give
    foundPermitted = None 
    foundDenied = None

    for word in permitted_list:
        if findWholeWord(word)(rawstring):
            foundPermitted = word
            break

    for word in denied_list:
        if findWholeWord(word)(rawstring):
            foundDenied = word
            break
    
    if (foundPermitted is not None) and (foundDenied is None):
        return True
    else:
        return False


def selectCategory(rawstring, category1, category2):
    foundCategory1 = None
    foundCategory2 = None

    for word in category1:
        if findWholeWord(word)(rawstring):
            foundCategory1 = word
            break

    for word in category2:
        if findWholeWord(word)(rawstring):
            foundCategory2 = word
            break
        
    if ((foundCategory1 is not None) and (foundCategory2 is not None)) or ((foundCategory1 is None) and (foundCategory2 is None)):
        return False
    elif foundCategory1 is not None:
        return 'category1'
    elif foundCategory2 is not None:
        return 'category2'


def select_category_reject(rawstring, category1, category2, reject_list):
    foundCategory1 = None 
    foundCategory2 = None 
    rejectCategory = None 

    for word in category1:
        if findWholeWord(word)(rawstring):
            foundCategory1 = word
            break

    for word in category2:
        if findWholeWord(word)(rawstring):
            foundCategory2 = word
            break

    for word in reject_list:
        if findWholeWord(word)(rawstring):
            rejectCategory = word
            break
        
    if ((foundCategory1 is not None) and (foundCategory2 is not None)) or ((foundCategory1 is None) and (foundCategory2 is None)) or (rejectCategory is not None):
        return False
    elif foundCategory1 is not None:
        return 'category1'
    elif foundCategory2 is not None:
        return 'category2'
  

def text_preprocessing(original_text):
    # strip white spaces at the beginning and end 
    processed_text = original_text.strip()
    # remove tab spaces
    processed_text = re.sub('\t', ' ', processed_text)
    # remove new lines/line changes 
    processed_text = re.sub('\n', ' ', processed_text)
    # add a white space after every special character found 
    processed_text = re.sub("contract-conditions:", "contract-conditions: ", processed_text)
    processed_text = re.sub("deposit-conditions:", "deposit-conditions: ", processed_text)
    processed_text = re.sub("userchoice:", "userchoice: ", processed_text)
    # remove extra whitespaces in between
    processed_text = ' '.join(processed_text.split())
    processed_text = re.sub(' +', ' ', processed_text)
    clean_text = processed_text
    # make everything lowercase 
    processed_text = processed_text.lower()

    return clean_text,processed_text


# TODO - REMOVE SAMPLE TEXT 
text_list = [
    "create 500 million rmt#",

    "transfer 200 rmt#",

    "Create Smart Contract with the name India-elections-2019@ of the type one-time-event* using the asset rmt# at the address F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1$ with contract-conditions: (1) contractAmount=0.001rmt (2) userChoices=Narendra Modi wins| Narendra Modi loses (3) expiryTime= Wed May 22 2019 21:00:00 GMT+0530",

    "send 0.001 rmt# to india-elections-2019@ to FLO address F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1 with the userchoice:'narendra modi wins'",

    "india-elections-2019@ winning-choice:'narendra modi wins'",

    "Create Smart Contract with the name India-elections-2019@ of the type one-time-event* using the asset rmt# at the address F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1$ with contract-conditions: (1) contractAmount=0.001rmt (2) expiryTime= Wed May 22 2019 21:00:00 GMT+0530",

    "send 0.001 rmt# to india-elections-2019@ to FLO address F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1",

    "Create Smart Contract with the name swap-rupee-bioscope@ of the type continuous-event* at the address oRRCHWouTpMSPuL6yZRwFCuh87ZhuHoL78$ with contract-conditions : (1) subtype = tokenswap (2) accepting_token = rupee# (3) selling_token = bioscope# (4) price = '15' (5) priceType = ‘predetermined’ (6) direction = oneway",
    
    "Deposit 15 bioscope# to swap-rupee-bioscope@ its FLO address being oRRCHWouTpMSPuL6yZRwFCuh87ZhuHoL78$ with deposit-conditions: (1) expiryTime= Wed Nov 17 2021 21:00:00 GMT+0530 ",

    "Send 15 rupee# to swap-rupee-article@ its FLO address being FJXw6QGVVaZVvqpyF422Aj4FWQ6jm8p2dL$",

    "send 0.001 rmt# to india-elections-2019@ to FLO address F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1 with the userchoice:'narendra modi wins'"
]

text_list1 = [

    'create usd# as infinite-token',
    'transfer 10 usd#',

    'Create 100 albumname# as NFT with 2CF24DBA5FB0A30E26E83B2AC5B9E29E1B161E5C1FA7425E73043362938B9824 as asset hash',
    'Transfer 10 albumname# nft',

    'Create 400 rmt#',
    'Transfer 20 rmt#'
]

text_list2 = [
    '''Create Smart Contract with the name swap-rupee-bioscope@ of the type continuous-event* 
    at the address stateF=bitcoin_price_source:bitpay:usd_inr_exchange_source:bitpay end-stateF oYzeeUBWRpzRuczW6myh2LHGnXPyR2Bc6k$ with contract-conditions :
    (1) subtype = tokenswap
    (2) accepting_token = rupee#
    (3) selling_token = sreeram#
    (4) price = "15"
    (5) priceType="predetermined" end-contract-conditions''',

    '''
    Create a smart contract of the name simple-crowd-fund@ of the type one-time-event* using asset bioscope# at the FLO address oQkpZCBcAWc945viKqFmJVbVG4aKY4V3Gz$ with contract-conditions:(1) expiryTime= Tue Sep 13 2022 16:10:00 GMT+0530  (2) payeeAddress=oQotdnMBAP1wZ6Kiofx54S2jNjKGiFLYD7 end-contract-conditions
    ''',

    '''
    Create a smart contract of the name simple-crowd-fund@ of the type one-time-event* using asset bioscope# at the FLO address oQkpZCBcAWc945viKqFmJVbVG4aKY4V3Gz$ with contract-conditions:(1) expiryTime= Tue Sep 13 2022 16:10:00 GMT+0530  (2) payeeAddress=oU412TvcMe2ah2xzqFpA95vBJ1RoPZY1LR:10:oVq6QTUeNLh8sapQ6J6EjMQMKHxFCt3uAq:20:oLE79kdHPEZ2bxa3PwtysbJeLo9hvPgizU:60:ocdCT9RAzWVsUncMu24r3HXKXFCXD7gTqh:10 end-contract-conditions
    ''', 
    '''
    Create a smart contract of the name simple-crowd-fund@ of the type one-time-event* using asset bioscope# at the FLO address oQkpZCBcAWc945viKqFmJVbVG4aKY4V3Gz$ with contract-conditions:(1) expiryTime= Tue Sep 13 2022 16:10:00 GMT+0530  (2) payeeAddress=oU412TvcMe2ah2xzqFpA95vBJ1RoPZY1LR end-contract-conditions
    ''',
    '''
    Create a smart contract of the name all-crowd-fund-7@ of the type one-time-event* using asset bioscope# at the FLO address oYX4GvBYtfTBNyUFRCdtYubu7ZS4gchvrb$ with contract-conditions:(1) expiryTime= Sun Nov 15 2022 12:30:00 GMT+0530 (2) payeeAddress=oQotdnMBAP1wZ6Kiofx54S2jNjKGiFLYD7:10:oMunmikKvxsMSTYzShm2X5tGrYDt9EYPij:20:oRpvvGEVKwWiMnzZ528fPhiA2cZA3HgXY5:30:oWpVCjPDGzaiVfEFHs6QVM56V1uY1HyCJJ:40 (3) minimumsubscriptionamount=1 (5) contractAmount=0.6 end-contract-conditions
    ''',
    '''
    Create a smart contract of the name all-crowd-fund-7@ of the type one-time-event* using asset bioscope# at the FLO address oYX4GvBYtfTBNyUFRCdtYubu7ZS4gchvrb$ with contract-conditions:(1) expiryTime= Sun Nov 15 2022 12:30:00 GMT+0530 (2) payeeAddress=oQotdnMBAP1wZ6Kiofx54S2jNjKGiFLYD7:0:oMunmikKvxsMSTYzShm2X5tGrYDt9EYPij:30:oRpvvGEVKwWiMnzZ528fPhiA2cZA3HgXY5:30:oWpVCjPDGzaiVfEFHs6QVM56V1uY1HyCJJ:40 (3) minimumsubscriptionamount=1 (4) contractAmount=0.6 end-contract-conditions
    ''',
    '''send 0.02 bioscope# to twitter-survive@ to FLO address oVbebBNuERWbouDg65zLfdataWEMTnsL8r with the userchoice: survives''',
    '''
    Create a smart contract of the name twitter-survive@ of the type one-time-event* using asset bioscope# at the FLO address oVbebBNuERWbouDg65zLfdataWEMTnsL8r$ with contract-conditions:(1) expiryTime= Sun Nov 15 2022 14:55:00 GMT+0530  (2) userchoices= survives | dies (3) minimumsubscriptionamount=0.04 (4) maximumsubscriptionamount=1 (5) contractAmount=0.02 end-contract-conditions
    ''',
    '''
    create 0 teega# 
    '''
]


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')

file_handler = logging.FileHandler('tracking.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

def parse_flodata(text, blockinfo, net):
    if net == 'testnet':
        is_testnet = True
    else:
        is_testnet = False

    if text == '':
        return outputreturn('noise')

    clean_text, processed_text = text_preprocessing(text)
    # System state 
    print("Processing stateF")
    stateF_mapping = isStateF(processed_text) 
    first_classification = firstclassification_rawstring(processed_text)
    parsed_data = None 

    if first_classification['categorization'] == 'tokensystem-C':
        # Resolving conflict for 'tokensystem-C' 
        tokenname = first_classification['wordlist'][0][:-1]
        if not check_regex("^[A-Za-z][A-Za-z0-9_-]*[A-Za-z0-9]$", tokenname):
            return outputreturn('noise')

        isNFT = check_word_existence_instring('nft', processed_text)           

        isInfinite = check_word_existence_instring('infinite-token', processed_text)
        tokenamount = apply_rule1(extractAmount_rule_new, processed_text)
 
        ## Cannot be NFT and normal token and infinite token. Find what are the conflicts 
        # if its an NFT then tokenamount has to be integer and infinite keyword should not be present 
        # if its a normal token then isNFT and isInfinite should be None/False and token amount has to be present 
        # if its an infinite token then tokenamount should be None and isNFT should be None/False
        # The supply of tokenAmount cannot be 0 

        ##################################################
        
        if (not tokenamount and not isInfinite) or (isNFT and not tokenamount.is_integer() and not isInfinite) or (isInfinite and tokenamount is not False and isNFT is not False) or tokenamount<=0:
            return outputreturn('noise')
        operation = apply_rule1(selectCategory, processed_text, send_category, create_category)
        if operation == 'category1' and tokenamount is not None:
            if isNFT:
                return outputreturn('nft_transfer',f"{processed_text}", f"{tokenname}", tokenamount, stateF_mapping)
            else:
                return outputreturn('token_transfer',f"{processed_text}", f"{tokenname}", tokenamount, stateF_mapping)
        elif operation == 'category2':
            if isInfinite:
                return outputreturn('infinite_token_create',f"{processed_text}", f"{tokenname}", stateF_mapping)
            else:
                if tokenamount is None:
                    return outputreturn('noise')
                if isNFT:
                    nft_hash = extract_NFT_hash(clean_text)
                    if nft_hash is False:
                        return outputreturn('noise')
                    return outputreturn('nft_create',f"{processed_text}", f"{tokenname}", tokenamount, f"{nft_hash}", stateF_mapping)
                else:
                    return outputreturn('token_incorporation',f"{processed_text}", f"{first_classification['wordlist'][0][:-1]}", tokenamount, stateF_mapping)
        else:
            return outputreturn('noise')

    if first_classification['categorization'] == 'smart-contract-creation-C':
        # Resolving conflict for 'smart-contract-creation-C'
        operation = apply_rule1(selectCategory, processed_text, create_category, send_category+deposit_category)
        if not operation:
            return outputreturn('noise') 

        contract_type = extract_special_character_word(first_classification['wordlist'],'*')
        if not check_existence_of_keyword(['one-time-event'],[contract_type]):
            return outputreturn('noise') 

        contract_name = extract_special_character_word(first_classification['wordlist'],'@')
        if not check_regex("^[A-Za-z][A-Za-z0-9_-]*[A-Za-z0-9]$", contract_name):
            return outputreturn('noise') 

        contract_token = extract_special_character_word(first_classification['wordlist'],'#')
        if not check_regex("^[A-Za-z][A-Za-z0-9_-]*[A-Za-z0-9]$", contract_token):
            return outputreturn('noise') 

        contract_address = extract_special_character_word(first_classification['wordlist'],'$')
        contract_address = find_original_case(contract_address, clean_text)
        if not check_flo_address(contract_address, is_testnet):
            return outputreturn('noise') 

        contract_conditions = extract_contract_conditions(processed_text, contract_type, contract_token, blocktime=blockinfo['time'])
        if contract_conditions == False or not resolve_incategory_conflict(contract_conditions,[['userchoices','payeeAddress']]):
            return outputreturn('noise') 
        else:
            contractAmount = ''
            if 'contractAmount' in contract_conditions.keys():
                contractAmount = contract_conditions['contractAmount']
                try:
                    if float(contractAmount)<=0:
                        return outputreturn('noise') 
                except:
                    return outputreturn('noise')
            minimum_subscription_amount = ''
            if 'minimumsubscriptionamount' in contract_conditions.keys():
                minimum_subscription_amount = contract_conditions['minimumsubscriptionamount']
                try:
                    if float(minimum_subscription_amount)<=0:
                        return outputreturn('noise')
                except:
                    return outputreturn('noise')
            maximum_subscription_amount = ''
            if 'maximumsubscriptionamount' in contract_conditions.keys():
                maximum_subscription_amount = contract_conditions['maximumsubscriptionamount']
                try:
                    if float(maximum_subscription_amount)<=0:
                        return outputreturn('noise')
                except:
                    return outputreturn('noise')

            if 'userchoices' in contract_conditions.keys():
                return outputreturn('one-time-event-userchoice-smartcontract-incorporation',f"{contract_token}", f"{contract_name}", f"{contract_address}", f"{clean_text}", f"{contractAmount}", f"{minimum_subscription_amount}" , f"{maximum_subscription_amount}", f"{contract_conditions['userchoices']}", f"{contract_conditions['expiryTime']}", stateF_mapping)
            elif 'payeeAddress' in contract_conditions.keys():
                contract_conditions['payeeAddress'] = find_word_index_fromstring(clean_text,contract_conditions['payeeAddress'])
                # check if colon exists in the payeeAddress string
                if ':' in contract_conditions['payeeAddress']:
                    colon_split = contract_conditions['payeeAddress'].split(':')
                    if len(colon_split)%2 != 0:
                        return outputreturn('noise')
                    split_total = 0 
                    payeeAddress_split_dictionary = {}
                    for idx, item in enumerate(colon_split):
                        if idx%2 == 0:
                            # check if floid 
                            if not check_flo_address(item, is_testnet):
                                return outputreturn('noise')
                        if idx%2 == 1:
                            # check if number
                            try:
                                item = float(item)
                                if item <= 0:
                                    return outputreturn('noise')
                                payeeAddress_split_dictionary[colon_split[idx-1]] = item
                                split_total += item
                            except:
                                return outputreturn('noise')
                    if split_total != 100:
                        return outputreturn('noise')
                    else:
                        contract_conditions['payeeAddress'] = payeeAddress_split_dictionary
                        return outputreturn('one-time-event-time-smartcontract-incorporation',f"{contract_token}", f"{contract_name}", f"{contract_address}", f"{clean_text}", f"{contractAmount}", f"{minimum_subscription_amount}" , f"{maximum_subscription_amount}", contract_conditions['payeeAddress'], f"{contract_conditions['expiryTime']}", stateF_mapping)
                else:  
                    if not check_flo_address(contract_conditions['payeeAddress'], is_testnet):
                        return outputreturn('noise')
                    else:
                        contract_conditions['payeeAddress'] = {f"{contract_conditions['payeeAddress']}":100}
                        return outputreturn('one-time-event-time-smartcontract-incorporation',f"{contract_token}", f"{contract_name}", f"{contract_address}", f"{clean_text}", f"{contractAmount}", f"{minimum_subscription_amount}" , f"{maximum_subscription_amount}", contract_conditions['payeeAddress'], f"{contract_conditions['expiryTime']}", stateF_mapping)

    if first_classification['categorization'] == 'smart-contract-participation-deposit-C':
        # either participation of one-time-event contract or 
        operation = apply_rule1(select_category_reject, processed_text, send_category, deposit_category, create_category)
        if not operation:
            return outputreturn('noise')
        else:
            tokenname = first_classification['wordlist'][0][:-1]
            if not check_regex("^[A-Za-z][A-Za-z0-9_-]*[A-Za-z0-9]$", tokenname):
                return outputreturn('noise')
        
            contract_name = extract_special_character_word(first_classification['wordlist'],'@')
            if not check_regex("^[A-Za-z][A-Za-z0-9_-]*[A-Za-z0-9]$", contract_name):
                return outputreturn('noise')

            contract_address = extract_special_character_word(first_classification['wordlist'],'$')
            if contract_address is False:
                contract_address = '' 
            else:
                contract_address = find_original_case(contract_address, clean_text)
                if not check_flo_address(contract_address, is_testnet):
                    return outputreturn('noise') 

            if operation == 'category1':
                tokenamount = apply_rule1(extractAmount_rule_new1, processed_text, 'userchoice:', 'pre')
                if not tokenamount:
                    return outputreturn('noise')
                try:
                    if float(tokenamount)<=0:
                        return outputreturn('noise')
                except:
                    return outputreturn('noise')
                userchoice = extract_userchoice(processed_text)
                # todo - do we need more validations for user choice?
                if not userchoice:
                    return outputreturn('noise')

                return outputreturn('one-time-event-userchoice-smartcontract-participation',f"{clean_text}", f"{tokenname}", tokenamount, f"{contract_name}", f"{contract_address}", f"{userchoice}", stateF_mapping)

            elif operation == 'category2':
                tokenamount = apply_rule1(extractAmount_rule_new1, processed_text, 'deposit-conditions:', 'pre')
                if not tokenamount:
                    return outputreturn('noise')
                try:
                    if float(tokenamount)<=0:
                        return outputreturn('noise')
                except:
                    return outputreturn('noise')
                deposit_conditions = extract_deposit_conditions(processed_text, blocktime=blockinfo['time'])
                if not deposit_conditions:
                    return outputreturn("noise")
                return outputreturn('continuos-event-token-swap-deposit', f"{tokenname}", tokenamount, f"{contract_name}", f"{clean_text}", f"{deposit_conditions['expiryTime']}", stateF_mapping)

    if first_classification['categorization'] == 'smart-contract-participation-ote-ce-C':
        # There is no way to properly differentiate between one-time-event-time-trigger participation and token swap participation 
        # so we merge them in output return 
        tokenname = first_classification['wordlist'][0][:-1]
        if not check_regex("^[A-Za-z][A-Za-z0-9_-]*[A-Za-z0-9]$", tokenname):
            return outputreturn('noise')

        tokenamount = apply_rule1(extractAmount_rule_new1, processed_text)
        if not tokenamount:
            return outputreturn('noise')
        try:
            if float(tokenamount)<=0:
                return outputreturn('noise')
        except:
            return outputreturn('noise')
        
        contract_name = extract_special_character_word(first_classification['wordlist'],'@')
        if not check_regex("^[A-Za-z][A-Za-z0-9_-]*[A-Za-z0-9]$", contract_name):
            return outputreturn('noise')
        
        contract_address = extract_special_character_word(first_classification['wordlist'],'$')
        if contract_address is False:
            contract_address = '' 
        else:
            contract_address = find_original_case(contract_address, clean_text)
            if not check_flo_address(contract_address, is_testnet):
                return outputreturn('noise') 

        return outputreturn('smart-contract-one-time-event-continuos-event-participation', f"{clean_text}", f"{tokenname}", tokenamount, f"{contract_name}", f"{contract_address}", stateF_mapping)

    if first_classification['categorization'] == 'userchoice-trigger':
        contract_name = extract_special_character_word(first_classification['wordlist'],'@')
        if not check_regex("^[A-Za-z][A-Za-z0-9_-]*[A-Za-z0-9]$", contract_name):
            return outputreturn('noise')

        trigger_condition = extract_trigger_condition(processed_text)
        if not trigger_condition:
            return outputreturn('noise')
        return outputreturn('one-time-event-userchoice-smartcontract-trigger', f"{contract_name}", f"{trigger_condition}", stateF_mapping)

    if first_classification['categorization'] == 'smart-contract-creation-ce-tokenswap':
        operation = apply_rule1(selectCategory, processed_text, create_category, send_category+deposit_category)
        if operation != 'category1':
            return outputreturn('noise') 

        contract_type = extract_special_character_word(first_classification['wordlist'],'*')
        if not check_existence_of_keyword(['continuous-event'],[contract_type]):
            return outputreturn('noise') 

        contract_name = extract_special_character_word(first_classification['wordlist'],'@')
        if not check_regex("^[A-Za-z][A-Za-z0-9_-]*[A-Za-z0-9]$", contract_name):
            return outputreturn('noise') 

        contract_token = extract_special_character_word(first_classification['wordlist'],'#')
        if not check_regex("^[A-Za-z][A-Za-z0-9_-]*[A-Za-z0-9]$", contract_token):
            return outputreturn('noise') 

        contract_address = extract_special_character_word(first_classification['wordlist'],'$')
        contract_address = find_original_case(contract_address, clean_text)
        if not check_flo_address(contract_address, is_testnet):
            return outputreturn('noise') 

        contract_conditions = extract_contract_conditions(processed_text, contract_type, contract_token, blocktime=blockinfo['time'])
        if contract_conditions == False:
            return outputreturn('noise')
        # todo - Add checks for token swap extract contract conditions 
        try:
            assert contract_conditions['subtype'] == 'tokenswap'
            assert check_regex("^[A-Za-z][A-Za-z0-9_-]*[A-Za-z0-9]$", contract_conditions['accepting_token'])
            assert check_regex("^[A-Za-z][A-Za-z0-9_-]*[A-Za-z0-9]$", contract_conditions['selling_token'])
            if contract_conditions['priceType']=="'determined'" or contract_conditions['priceType']=='"determined"' or contract_conditions['priceType']=="determined" or contract_conditions['priceType']=="'predetermined'" or contract_conditions['priceType']=='"predetermined"' or contract_conditions['priceType']=="predetermined" or contract_conditions['priceType']=="dynamic":
                assert float(contract_conditions['price'])>0
            else:
                #assert check_flo_address(find_original_case(contract_conditions['priceType'], clean_text), is_testnet)
                assert contract_conditions['priceType'] == 'statef'
        except AssertionError: 
            return outputreturn('noise')
        return outputreturn('continuos-event-token-swap-incorporation', f"{contract_token}", f"{contract_name}", f"{contract_address}", f"{clean_text}", f"{contract_conditions['subtype']}", f"{contract_conditions['accepting_token']}", f"{contract_conditions['selling_token']}", f"{contract_conditions['priceType']}", f"{contract_conditions['price']}", stateF_mapping)
    
    return outputreturn('noise')