# Ranchi Mall FLO API
Ranchi Mall FLO Tokens and Smart Contract API

The above API provides details about the token and smart contract system on the FLO blockchain. 

## Running the API

### Pre-requisites 
1. flo-token-tracking database 
2. A FLO public-private key pair for the socket API - The public key will be put on the API and private key will be used to connect to the socket API by the client. The socket API provides live feed of new incoming blocks and transactions

### Installation
```
git clone https://github.com/ranchimall/ranchimallflo-api
cd ranchimallflo-api
python3 -m venv py3
source py3/bin/activate 
pip install requests quart quart_cors ecdsa config arrow
```
Create a **config.py** file inside the API folder, with the details mentioned in the pre-requisite
```
# Create a config file 
dbfolder = '< PATH TO YOUR FLO-TOKEN-TRACKING FOLDER >'
sse_pubKey = '< YOUR PUBLIC KEY FROM THE PUBLIC KEY PAIR >'
```

To start the API, execute the following from inside the folder
```
python ranchimallflo_api.py
```

## API HTTP Endpoints

### List of token names
Get a list of all the active tokens on FLO blockchain 
```
  /api/v1.0/getTokenList
```
Output:
```
{
  "result": "ok",
  "tokens": [
    "chainserve",
    "rupee",
    "rmt",
    "utopia"
    ]
}
```

### Information about a token
Get information about a token on the FLO blockchain 
```
  /api/v1.0/getTokenInfo?token=rmt
```
Output:
```
{
  "activeAddress_no": 25,
  "blockchainReference": "https://flosight.duckdns.org/tx/a74a03ec1e77fa50e0b586b1e9745225ad4f78ce96ca59d6ac025f8057dd095c",
  "incorporationAddress": "FKNW5eCCp2SnJMJ6pLLpUCvk5hAage8Jtk",
  "result": "ok",
  "token": "rmt",
  "tokenSupply": 21000000,
  "transactionHash": "a74a03ec1e77fa50e0b586b1e9745225ad4f78ce96ca59d6ac025f8057dd095c"
}
```

### Information about a token's transactions
Get information about a token's related transactions on the blockchain 
```
  /api/v1.0/getTokenTransactions?token=rmt
```
Optional URL parameters :
senderFloAddress
destFloAddress

Output:
```
{
"result": "ok",
"transactions": [
      {
      "blockNumber": 3454503,
      "blockchainReference": "https://flosight.duckdns.org/tx/b57cf412c8cb16e473d04bae44214705c64d2c25146be22695bf1ac36e166ee0",
      "destFloAddress": "FFXX4i986DzDYZsGYXoozm6714WHtHZSod",
      "sourceFloAddress": "F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1",
      "transferAmount": 0.00133333
      },
      {
      "blockNumber": 3454503,
      "blockchainReference": "https://flosight.duckdns.org/tx/b57cf412c8cb16e473d04bae44214705c64d2c25146be22695bf1ac36e166ee0",
      "destFloAddress": "FCMLYTNBUXiC8R3xwnGJVaDzoUYkJMqHKd",
      "sourceFloAddress": "F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1",
      "transfe},rAmount": 0.00133333
      }
   ]
}
```

### Information about a token's address balances 
Get information about a token's address balances
```
  /api/v1.0/getTokenBalances?token=rmt
```

Output:
```
{
  "balances": [
      {
          "balance": 0.0023333299999999998,
          "floAddress": "F6EMAHjivqrcrdAHNABq2R1FLNkx8xfEaT"
      },
      {
          "balance": 0.0023333299999999998,
          "floAddress": "F6WPx2WFdmVQ6AMutZ2FJzpyiwdxqLyd2z"
      },
      {
          "balance": 0.0023333299999999998,
          "floAddress": "F7k7bTPStxr6wKCzUNVW48j3N2tN3PVgxZ"
      }
  ],
  "result": "ok"
}
```

### Information about a FLO address 
Get information about a FLO address
```
  /api/v1.0/getFloAddressDetails?floAddress=F6WPx2WFdmVQ6AMutZ2FJzpyiwdxqLyd2z
```

Output:
```
{
      "floAddress": "F6WPx2WFdmVQ6AMutZ2FJzpyiwdxqLyd2z",
      "floAddressDetails": [
          {
          "balance": 0.0023333299999999998,
          "token": "rmt"
          }
      ],
      "result": "ok"
}
```

### Information about a FLO address of a particular token 
Get information about a FLO address of a particular token 
```
  /api/v1.0/getFloAddressBalance?token=rmt&floAddress=F6WPx2WFdmVQ6AMutZ2FJzpyiwdxqLyd2z
```

Output:
```
{
      "balance": 0.0023333299999999998,
      "floAddress": "F6WPx2WFdmVQ6AMutZ2FJzpyiwdxqLyd2z",
      "result": "ok",
      "token": "rmt"
}
```

### Information about a FLO address's transactions 
Get information about a FLO address's transactions 
```
  /api/v1.0/getFloAddressTransactions?floAddress=F6WPx2WFdmVQ6AMutZ2FJzpyiwdxqLyd2z
```

Output:
```
{
"allTransactions": [
    {
        "token": "rmt",
        "transactions": [
            {
            "blockNumber": 3454503,
            "blockchainReference": "https://flosight.duckdns.org/tx/b57cf412c8cb16e473d04bae44214705c64d2c25146be22695bf1ac36e166ee0",
            "destFloAddress": "FFXX4i986DzDYZsGYXoozm6714WHtHZSod",
            "sourceFloAddress": "F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1",
            "transferAmount": 0.00133333
            },
            {
            "blockNumber": 3454503,
            "blockchainReference": "https://flosight.duckdns.org/tx/b57cf412c8cb16e473d04bae44214705c64d2c25146be22695bf1ac36e166ee0",
            "destFloAddress": "FCMLYTNBUXiC8R3xwnGJVaDzoUYkJMqHKd",
            "sourceFloAddress": "F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1",
            "transferAmount": 0.00133333
            }
        ]
    }
],
"floAddress": "F6WPx2WFdmVQ6AMutZ2FJzpyiwdxqLyd2z",
"result": "ok"
}
```

### Get list of all active smart contracts  
Get list of all active smart contracts 
```
  /api/v1.0/getSmartContractList
```
Optional parameters
contractName
contractAddress

Output:
```
{
    "result": "ok",
    "smartContracts": [
        {
            "contractAddress": "F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1",
            "contractName": "india-elections-2019",
            "expiryDate": "1558539107",
            "incorporationDate": "1557576932",
            "status": "closed",
            "transactionHash": "c6eb7adc731a60b2ffa0c48d0d72d33b2ec3a33e666156e729a63b25f6c5cd56"
        }
    ]
}
```

### Smart Contract's information  
Get information about a specified Smart Contract 
```
  /api/v1.0/getSmartContractInfo?contractName=india-elections-2019&contractAddress=F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1
```
Output:
```
{
    "contractInfo": {
        "contractAddress": "F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1",
        "contractAmount": "0.001",
        "contractName": "india-elections-2019",
        "contractType": "one-time-event",
        "expiryDate": "1558539107",
        "expiryTime": "wed may 22 2019 21:00:00 gmt+0530",
        "flodata": "Create Smart Contract with the name India-elections-2019@ of the type one-time-event* using the asset rmt# at the address F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1$ with contract-conditions: (1) contractAmount=0.001rmt (2) userChoices=Narendra Modi wins| Narendra Modi loses (3) expiryTime= Wed May 22 2019 21:00:00 GMT+0530",
        "incorporationDate": "1557576932",
        "numberOfParticipants": 16,
        "status": "closed",
        "tokenAmountDeposited": 0.016000000000000007,
        "tokenIdentification": "rmt",
        "userChoice": [
            "narendra modi wins",
            "narendra modi loses"
            ]
    },
    "result": "ok"
}
```

### Smart Contract's participants  
Get information about a specified Smart Contract's participants 
```
  /api/v1.0/getSmartContractParticipants?contractName=india-elections-2019&contractAddress=F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1
```
Output:
```
{
    "participantInfo": {
        "1": {
            "participantFloAddress": "FGyDAHZ3AU5TqRV2zrTju9DBCbKWZtearf",
            "tokenAmount": 0.001,
            "transactionHash": "26f08763cd177e2d55080041637527a7769eb3507b023a25bc9edbe8649c2fe2",
            "userChoice": "narendra modi wins",
            "winningAmount": 0.00133333
        },
        "2": {
            "participantFloAddress": "F6WPx2WFdmVQ6AMutZ2FJzpyiwdxqLyd2z",
            "tokenAmount": 0.001,
            "transactionHash": "511f16a69c5f62ad1cce70a2f9bfba133589e3ddc560d406c4fbf3920eae8469",
            "userChoice": "narendra modi wins",
            "winningAmount": 0.00133333
        },
        "3": {
            "participantFloAddress": "FEDUxQPznerYapqhdiBDT54rGhAdRikqJA",
            "tokenAmount": 0.001,
            "transactionHash": "e92bf6a8bddf177a5e2d793fa86c7ad059c89157f683f90f02b3590c0e4282c5",
            "userChoice": "narendra modi wins",
            "winningAmount": 0.00133333
        }
    },
    "result": "ok"
}
```

### Smart Contract's participant details   
Get information about a specified Smart Contract's participants 
```
  /api/v1.0/getSmartContractParticipantDetails?floAddress=
```
Output:
```
{
    "participantInfo": {
        "1": {
            "participantFloAddress": "FGyDAHZ3AU5TqRV2zrTju9DBCbKWZtearf",
            "tokenAmount": 0.001,
            "transactionHash": "26f08763cd177e2d55080041637527a7769eb3507b023a25bc9edbe8649c2fe2",
            "userChoice": "narendra modi wins",
            "winningAmount": 0.00133333
        },
        "2": {
            "participantFloAddress": "F6WPx2WFdmVQ6AMutZ2FJzpyiwdxqLyd2z",
            "tokenAmount": 0.001,
            "transactionHash": "511f16a69c5f62ad1cce70a2f9bfba133589e3ddc560d406c4fbf3920eae8469",
            "userChoice": "narendra modi wins",
            "winningAmount": 0.00133333
        },
        "3": {
            "participantFloAddress": "FEDUxQPznerYapqhdiBDT54rGhAdRikqJA",
            "tokenAmount": 0.001,
            "transactionHash": "e92bf6a8bddf177a5e2d793fa86c7ad059c89157f683f90f02b3590c0e4282c5",
            "userChoice": "narendra modi wins",
            "winningAmount": 0.00133333
        }
    },
    "result": "ok"
}
```

### Block details     
Get information about a block by specifying its blockno 
```
  /api/v1.0/getBlockDetails/<blockno>
```
Output:
```
{
    "bits": 486729686,
    "chainwork": "000000000000000000000000000000000000000000000000000001e1750030bd",
    "confirmations": 3615543,
    "difficulty": 3455,
    "hash": "50694aafcfbf72e687f15e00b17cf4603797414d49169c1674a7bf60dd1f2173",
    "height": 1524,
    "isMainChain": true,
    "merkleroot": "7caf89db3ac334a98023952370e2e73058e1437e34e3a6d5500e66f388d7c3e3",
    "nextblockhash": "6924186cb0235373d2daa2ee6e07319c92fc617bb72a86c64b22832b721ac060",
    "nonce": 1557664000,
    "poolInfo": {},
    "previousblockhash": "9c90782124c5c074def3191bcf059db0df2c40c642645290c216b8fceed85e63",
    "reward": 100,
    "size": 604,
    "time": 1371543439,
    "tx": [
        "7caf89db3ac334a98023952370e2e73058e1437e34e3a6d5500e66f388d7c3e3"
        ],
    "version": 1
}
```

### Transaction details     
Get information about a transaction 
```
  /api/v1.0/getTransactionDetails/<transactionHash>
```
Output:
```
{
    "parsingDetails": {
      "contractName": "india-elections-2019",
      "flodata": "send 0.001 rmt# to india-elections-2019@ to FLO address F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1 with the userchoice:'narendra modi wins''",
      "operation": "transfer",
      "tokenAmount": 0.001,
      "tokenIdentification": "rmt",
      "transferType": "smartContract",
      "type": "transfer",
      "userChoice": "narendra modi wins"
      },
      "transactionDetails": {
      "blockhash": "042d8229355ab7256f8f4234f8385a6834d88c12fedd0f576f128234206f7633",
      "blockheight": 3447257,
      "blocktime": 1558532628,
      "confirmations": 169813,
      "fees": 0.0005,
      "floData": "send 0.001 rmt# to india-elections-2019@ to FLO address F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1 with the userchoice:'narendra modi wins''",
      "locktime": 0,
      "size": 506,
      "time": 1558532628,
      "txid": "5a36fce4646358c751b5403ec5c7465f1b11c8dca6d86e8a9cd4e26184e07b1a",
      "valueIn": 0.0025,
      "valueOut": 0.002,
      "version": 2,
      "vin": [
      {
      "addr": "FCMLYTNBUXiC8R3xwnGJVaDzoUYkJMqHKd",
      "confirmations": null,
      "doubleSpentTxID": null,
      "isConfirmed": null,
      "n": 0,
      "scriptSig": {
      "asm": "3044022002f365ccbf0142f23a54a0c05c782f7d35bf10019a259ba089bc6892071121fc022031a128bd67155bdfc92c3b5329ad5f94541a940ec361f59623aa9b2db4434c1501 021df9a231a28e4a7f913ec8fe1e9c6e77b8672553d12ac3125c4976e184d76dc2",
      "hex": "473044022002f365ccbf0142f23a54a0c05c782f7d35bf10019a259ba089bc6892071121fc022031a128bd67155bdfc92c3b5329ad5f94541a940ec361f59623aa9b2db4434c150121021df9a231a28e4a7f913ec8fe1e9c6e77b8672553d12ac3125c4976e184d76dc2"
      },
      "sequence": 4294967295,
      "txid": "e4ee5448dac2f378b65c7ec7ddd596e329510ef22175940d7e447b5d60df75ae",
      "unconfirmedInput": null,
      "value": 0.0005,
      "valueSat": 50000,
      "vout": 1
      },
      {
      "addr": "FCMLYTNBUXiC8R3xwnGJVaDzoUYkJMqHKd",
      "confirmations": null,
      "doubleSpentTxID": null,
      "isConfirmed": null,
      "n": 1,
      "scriptSig": {
      "asm": "3045022100abbe2a0c5a6efc88ee619b58ee2ae4d38cc46dd42c79fd4db2391fe1b76dfaed022078ad9c2fa6a712dc51efbc586298ed813dd37ce4d209a38fe313f494079e301901 021df9a231a28e4a7f913ec8fe1e9c6e77b8672553d12ac3125c4976e184d76dc2",
      "hex": "483045022100abbe2a0c5a6efc88ee619b58ee2ae4d38cc46dd42c79fd4db2391fe1b76dfaed022078ad9c2fa6a712dc51efbc586298ed813dd37ce4d209a38fe313f494079e30190121021df9a231a28e4a7f913ec8fe1e9c6e77b8672553d12ac3125c4976e184d76dc2"
      },
      "sequence": 4294967295,
      "txid": "5e67fee05ed5f6598a85e8fb12e207183bc4441c8f81d54b89ce6bfd196c5fdf",
      "unconfirmedInput": null,
      "value": 0.002,
      "valueSat": 200000,
      "vout": 0
      }
      ],
      "vout": [
      {
      "n": 0,
      "scriptPubKey": {
      "addresses": [
      "F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1"
      ],
      "asm": "OP_DUP OP_HASH160 15b3eb460d593f74775167d589a3a443eb78b55b OP_EQUALVERIFY OP_CHECKSIG",
      "hex": "76a91415b3eb460d593f74775167d589a3a443eb78b55b88ac",
      "type": "pubkeyhash"
      },
      "spentHeight": null,
      "spentIndex": null,
      "spentTxId": null,
      "value": "0.00100000"
      },
      {
      "n": 1,
      "scriptPubKey": {
      "addresses": [
      "FCMLYTNBUXiC8R3xwnGJVaDzoUYkJMqHKd"
      ],
      "asm": "OP_DUP OP_HASH160 478827032c14de407edb37c91830bc18954a7a53 OP_EQUALVERIFY OP_CHECKSIG",
      "hex": "76a914478827032c14de407edb37c91830bc18954a7a5388ac",
      "type": "pubkeyhash"
      },
      "spentHeight": null,
      "spentIndex": null,
      "spentTxId": null,
      "value": "0.00100000"
      }
      ]
    }
}
```

### Latest Blocks details 
Get information about latest blocks 
```
  /api/v1.0/getLatestBlockDetails/<blockno>
```
Output:
```
{
    "bits": 486730121,
    "chainwork": "000000000000000000000000000000000000000000000000000007a879245c83",
    "confirmations": 3612882,
    "difficulty": 3326,
    "hash": "1505dff5d42ec30639c37740078f0378eb0abf859412082073ba6f3cc799c234",
    "height": 5234,
    "isMainChain": true,
    "merkleroot": "347bffbe1e6f4e3c227558d55ff7a37f22ef890e1b7504cfc9bf5188dcb5aa5e",
    "nextblockhash": "4c1cfcf2575a814b388668fa12815eb757b5f44323e79dd8fcbb2f366c96cb08",
    "nonce": 3145073920,
    "poolInfo": {},
    "previousblockhash": "ea8ad584fec1af50ef98569d95dcc6ee9555f87e50d9d9aa46a72e7cf9dfbf2c",
    "reward": 100,
    "size": 192,
    "time": 1371693986,
    "tx": [
        "347bffbe1e6f4e3c227558d55ff7a37f22ef890e1b7504cfc9bf5188dcb5aa5e"
        ],
    "version": 1
}
```

### Latest Transactions details 
Get information about latest blocks 
```
  /api/v1.0/getLatestTransactionDetails/<transactionHash>
```
Output:
```
{
"parsingDetails": {
"flodata": "create 1 billion rupee#",
"tokenAmount": 1000000000,
"tokenIdentification": "rupee",
"type": "tokenIncorporation"
},
"transactionDetails": {
"blockhash": "550e516d62e06013f7691eb58a139a393b6514571a6d252fd62557262884666c",
"blockheight": 3609700,
"blocktime": 1566643220,
"confirmations": 8417,
"fees": 0.0005,
"floData": "create 1 billion rupee#",
"locktime": 0,
"size": 249,
"time": 1566643220,
"txid": "e6338071b4247003e16aae50e2696d42f42df116b928122bd94c3c718fbd70bc",
"valueIn": 1,
"valueOut": 0.9995,
"version": 2,
"vin": [
{
"addr": "FQ5EZGMYXa1s2mLsdPrs3Y41nQffaAyBVV",
"confirmations": null,
"doubleSpentTxID": null,
"isConfirmed": null,
"n": 0,
"scriptSig": {
"asm": "304402207677f26362c0fa07c31a54e1f79e8b8d1d5918c20243ebd5e8b0fb21a56bba33022013fed7f459a10db9e39c5970ce198bc07efcf28f572c79f6640e115f8ca7581b01 02c5db0639bd937227c4b00d4f9de475a0e68a75d07e2987b744e9a9096381a6e9",
"hex": "47304402207677f26362c0fa07c31a54e1f79e8b8d1d5918c20243ebd5e8b0fb21a56bba33022013fed7f459a10db9e39c5970ce198bc07efcf28f572c79f6640e115f8ca7581b012102c5db0639bd937227c4b00d4f9de475a0e68a75d07e2987b744e9a9096381a6e9"
},
"sequence": 4294967295,
"txid": "40cf13ae30a2357b86462edca0345697666839ce5ba3cdf12e173535d88a2778",
"unconfirmedInput": null,
"value": 1,
"valueSat": 100000000,
"vout": 0
}
],
"vout": [
{
"n": 0,
"scriptPubKey": {
"addresses": [
"F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1"
],
"asm": "OP_DUP OP_HASH160 15b3eb460d593f74775167d589a3a443eb78b55b OP_EQUALVERIFY OP_CHECKSIG",
"hex": "76a91415b3eb460d593f74775167d589a3a443eb78b55b88ac",
"type": "pubkeyhash"
},
"spentHeight": null,
"spentIndex": null,
"spentTxId": null,
"value": "0.00100000"
},
{
"n": 1,
"scriptPubKey": {
"addresses": [
"FQ5EZGMYXa1s2mLsdPrs3Y41nQffaAyBVV"
],
"asm": "OP_DUP OP_HASH160 c81e026ffa6313d1263eb081fb6bdef9b38ed3a1 OP_EQUALVERIFY OP_CHECKSIG",
"hex": "76a914c81e026ffa6313d1263eb081fb6bdef9b38ed3a188ac",
"type": "pubkeyhash"
},
"spentHeight": null,
"spentIndex": null,
"spentTxId": null,
"value": "0.99850000"
}
]
}
}
```
