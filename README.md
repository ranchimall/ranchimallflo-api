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
  /api/v1.0/getLatestBlockDetails
```
Output:
```
{
    "latestBlocks": [
        {
            "bits": "1b1471d4",
            "chainwork": "00000000000000000000000000000000000000000000000099f3f203a3078115",
            "confirmations": 175091,
            "difficulty": 3205.485468631051,
            "hash": "c55d34d5efc558bcdfd1f63e6b4bcfe105f950ce2698033d4e6f0baac68840a6",
            "height": 3447073,
            "mediantime": 1558524867,
            "merkleroot": "5b87fee25703cb6ae2a3e8c8f5390070c940b26963cc2b31e7566185b0748b77",
            "nextblockhash": "f11c0f6cd958f3a769350c2436ea76f3f776d86a66fcdc180d90a5d09ce09cf0",
            "nonce": 1775056665,
            "previousblockhash": "58497e82453051744fcde4fef6ff755f750f668db61a7a5edca818e7c5e47df5",
            "size": 860,
            "strippedsize": 824,
            "time": 1558525219,
            "tx": [
                "38da76036d533967993e767702364cface0336609d9c9aa6cea05994514c1401",
                "ad50d8bffe7214473b6f8f454f55749d23a26ab3fc854d63e1ccc808045d98ba"
            ],
            "version": 536870912,
            "versionHex": "20000000",
            "weight": 3332
        },
        {
            "bits": "1b12a3cc",
            "chainwork": "00000000000000000000000000000000000000000000000099fd54362122a23e",
            "confirmations": 174907,
            "difficulty": 3515.85795445243,
            "hash": "042d8229355ab7256f8f4234f8385a6834d88c12fedd0f576f128234206f7633",
            "height": 3447257,
            "mediantime": 1558532349,
            "merkleroot": "85f9303ab800f686bcc58cd495fd4d45d462c8f37a279277504c7da02d062b7b",
            "nextblockhash": "8c1a4f8301bd594c4d3503b03d29fd007c75011dd9fafcd7f7abea340ee2ca92",
            "nonce": 1161774987,
            "previousblockhash": "b8d2570bec995696affca41eb3466477c7ead4372d809fff0d349a5894f8da9c",
            "size": 4448,
            "strippedsize": 4448,
            "time": 1558532628,
            "tx": [
                "ffbacc1ec3ffc5fa9390ff76e2705685bd1a9886c29295bdd2a993829cc2cf71",
                "dea1f346524565e9ef7ca68c5aea862edf30b096cc782983e05ce8cdd6827a86",
                "824db22bc0d2653f2bc9a6b475294760d7867bfbb8bad8b6b65dc49986735b2e",
                "e2b1b0a576765138e77ac86c87653617879c38670ff9b55f26cc2a057ba71935",
                "9698b7e50279f2bb0334984dac0a671417b7796e93c8115641ec3ee131805044",
                "aacb9a24d278102f4ab2c344211dac5a016968666f7a762b0a211f8b840ba17a",
                "aa710482732c50d18db41a8f8775ccf9244e7867fc80effc0868bb513f2cccb6",
                "761411f77ea5d1d11f988c98bbe2ad9f66ce4d5b327dfa7434cd7b4f2797dbab",
                "6ac7d43394de8dbeffc80609b2996e1626606c7fccca51b827f928b7162c60af",
                "016e0c62ce10114adf867c0d4ad24c45223e0a8e83ed6b78e91aead59437e1df",
                "5a36fce4646358c751b5403ec5c7465f1b11c8dca6d86e8a9cd4e26184e07b1a"
            ],
            "version": 536870912,
            "versionHex": "20000000",
            "weight": 17792
        },
        {
            "bits": "1b11db34",
            "chainwork": "00000000000000000000000000000000000000000000000099fe633b321afd59",
            "confirmations": 174886,
            "difficulty": 3670.14099816446,
            "hash": "9a7124bb45e489fbec02d41f7b22c7695493a70cc7fe97b864290e2727c6d7cc",
            "height": 3447278,
            "mediantime": 1558533117,
            "merkleroot": "a33fa061af2c67ba20a26718866dafb50ee96a4373a8bd2c364d377571779e4d",
            "nextblockhash": "b2188357cfef92e374aab9cbfdf6cf54b9d56edea4a1400a2047f2b7d2e8e0fc",
            "nonce": 1300764883,
            "previousblockhash": "c8ff8f84fd277e054f44885c7df7bf48d076a09b7595fd302b2d2598e2d4d2b1",
            "size": 1819,
            "strippedsize": 1819,
            "time": 1558533249,
            "tx": [
                "2682d8a248bef10bcf28f04625300e03c071fce346ec590401be2d9d4af5de02",
                "90197c5614d321d8ecc8d6073ca926b1c5d06d5dace0382e6572ef3d96db2239",
                "c928c63574c6c4280ad8d87fd0dfee128ce02b957c1d2cd5306fe33ecf922a3b",
                "79ae8f0a1ebcee00f534311046f4806cedc8e7db7db7ecd44f04c9986791cff4",
                "3520cda2de65249f7629683c4b8f3efb15479076fe9521250aba2f1abe3f2ce9"
            ],
            "version": 536870912,
            "versionHex": "20000000",
            "weight": 7276
        },
        {
            "bits": "1b1d5382",
            "chainwork": "000000000000000000000000000000000000000000000000a25b992cbf49685d",
            "confirmations": 119468,
            "difficulty": 2234.690981215679,
            "hash": "734a190218bcf6cb0abd1fb825ccf2cedb7b555e35a96673cb0c9ff214925f7a",
            "height": 3503146,
            "mediantime": 1561044091,
            "merkleroot": "4b26a4232d1a64d873f80f871cc54aaf12f7206b305796ad421adcb422d06943",
            "nextblockhash": "05edb88439a7fa74e649b4030c674053dada9b0044a793b8b0b9250326ec172e",
            "nonce": 282711878,
            "previousblockhash": "b4362a3fd0ba877f4aa4a8edded28816b2a19f11cb30a8374effedb966c23ffb",
            "size": 650,
            "strippedsize": 650,
            "time": 1561044213,
            "tx": [
                "bda24ce4a936d31bb1e3ede159303eb0beca9d3cd2c85e78e3e071be4b2512ca",
                "ebc99f41c4ccaea32bd9dbc251515838ba47660b7422c7cae39ee3e2ae0107fe"
            ],
            "version": 536870912,
            "versionHex": "20000000",
            "weight": 2600
        }
    ],
    "result": "ok"
}
```

### Latest Transactions details 
Get information about latest transactions 
```
  /api/v1.0/getLatestTransactionDetails
```
Output:
```
{
    "latestTransactions": [
        {
            "parsedFloData": {
                "contractName": "india-elections-2019",
                "flodata": "send 0.001 rmt# to india-elections-2019@ to FLO address F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1 with the userchoice:'narendra modi wins'",
                "operation": "transfer",
                "tokenAmount": 0.001,
                "tokenIdentification": "rmt",
                "transactionType": "transfer",
                "transferType": "smartContract",
                "type": "transfer",
                "userChoice": "narendra modi wins"
            },
            "transactionDetails": {
                "blockhash": "9a7124bb45e489fbec02d41f7b22c7695493a70cc7fe97b864290e2727c6d7cc",
                "blockheight": 3447278,
                "blocktime": 1558533249,
                "confirmations": 174886,
                "floData": "send 0.001 rmt# to india-elections-2019@ to FLO address F7osBpjDDV1mSSnMNrLudEQQ3cwDJ2dPR1 with the userchoice:'narendra modi wins'",
                "hash": "3520cda2de65249f7629683c4b8f3efb15479076fe9521250aba2f1abe3f2ce9",
                "hex": "020000000126130ca39fc381791c053582a8af6694be3b0937d3723672cf3d49c3306c43d8000000006b483045022100f090fe20e4b525b699f580d62375f515a7d2d6daa9b9e10d80521d7d4f0bbe0d02203da43d9343b9c8edd9a65eec15e9a3094b19b2cc5bfe26985350fa006812cccf012102097cd225015f274dcc7d6a482b4a93c89467b7dc3a6c43451bf0203775e2af85ffffffff02a0860100000000001976a91415b3eb460d593f74775167d589a3a443eb78b55b88ac50c30000000000001976a9146a5d78edcec0d27ee30a0bdf8ae2b2a9312cffa288ac000000008373656e6420302e30303120726d742320746f20696e6469612d656c656374696f6e732d323031394020746f20464c4f20616464726573732046376f7342706a444456316d53536e4d4e724c7564455151336377444a3264505231207769746820746865207573657263686f6963653a276e6172656e647261206d6f64692077696e7327",
                "locktime": 0,
                "size": 358,
                "time": 1558533249,
                "txid": "3520cda2de65249f7629683c4b8f3efb15479076fe9521250aba2f1abe3f2ce9",
                "version": 2,
                "vin": [
                    {
                        "scriptSig": {
                            "asm": "3045022100f090fe20e4b525b699f580d62375f515a7d2d6daa9b9e10d80521d7d4f0bbe0d02203da43d9343b9c8edd9a65eec15e9a3094b19b2cc5bfe26985350fa006812cccf[ALL] 02097cd225015f274dcc7d6a482b4a93c89467b7dc3a6c43451bf0203775e2af85",
                            "hex": "483045022100f090fe20e4b525b699f580d62375f515a7d2d6daa9b9e10d80521d7d4f0bbe0d02203da43d9343b9c8edd9a65eec15e9a3094b19b2cc5bfe26985350fa006812cccf012102097cd225015f274dcc7d6a482b4a93c89467b7dc3a6c43451bf0203775e2af85"
                        },
                        "sequence": 4294967295,
                        "txid": "d8436c30c3493dcf723672d337093bbe9466afa88235051c7981c39fa30c1326",
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
                            "reqSigs": 1,
                            "type": "pubkeyhash"
                        },
                        "value": 0.001
                    },
                    {
                        "n": 1,
                        "scriptPubKey": {
                            "addresses": [
                                "FFXX4i986DzDYZsGYXoozm6714WHtHZSod"
                            ],
                            "asm": "OP_DUP OP_HASH160 6a5d78edcec0d27ee30a0bdf8ae2b2a9312cffa2 OP_EQUALVERIFY OP_CHECKSIG",
                            "hex": "76a9146a5d78edcec0d27ee30a0bdf8ae2b2a9312cffa288ac",
                            "reqSigs": 1,
                            "type": "pubkeyhash"
                        },
                        "value": 0.0005
                    }
                ],
                "vsize": 358
            }
        },
        {
            "parsedFloData": {
                "flodata": "Incorporate 10 million tokens for Utopia#",
                "tokenAmount": 10000000,
                "tokenIdentification": "utopia",
                "transactionType": "tokenIncorporation",
                "type": "tokenIncorporation"
            },
            "transactionDetails": {
                "blockhash": "734a190218bcf6cb0abd1fb825ccf2cedb7b555e35a96673cb0c9ff214925f7a",
                "blockheight": 3503146,
                "blocktime": 1561044213,
                "confirmations": 119468,
                "floData": "Incorporate 10 million tokens for Utopia#",
                "hash": "ebc99f41c4ccaea32bd9dbc251515838ba47660b7422c7cae39ee3e2ae0107fe",
                "hex": "0200000002dd3f9d64f87cadf1ab603a7d34a5b331bb4ac2611350ca7584ebf00353c0d3e4010000006a47304402205b9ffe2ae901c1c62f21409d68bf4f18f94ce4c482569ed5f6c21aa15257a3a402203f85f0b04d8982bb09e8852a7f88169dbd9fb404144c5048846b796a96edf24f012102cc5eaa7bd1c37ebf8483c014d38a1608d06cf6be6d61bae64b697725bae7696bffffffffe900e5690d95dbc12800799d786236af2a22ab6aafcb9f9a734a161ff9c61479000000006b483045022100a6c13e00f1fb53122424c35c581628830cf3b0cfab600397e7d3b6dd6d8aa89a022071add87aaa08239f30d58f2991525c66888e1f3fb8d52eec3c72c1871cced50f012102cc5eaa7bd1c37ebf8483c014d38a1608d06cf6be6d61bae64b697725bae7696bffffffff0220a10700000000001976a914868190f1c3c9839fc34f994a44898739624fcfbc88ace00f9700000000001976a914b9d8e7f578161fb3fa16a061abe412926cbfc85488ac0000000029496e636f72706f72617465203130206d696c6c696f6e20746f6b656e7320666f722055746f70696123",
                "locktime": 0,
                "size": 415,
                "time": 1561044213,
                "txid": "ebc99f41c4ccaea32bd9dbc251515838ba47660b7422c7cae39ee3e2ae0107fe",
                "version": 2,
                "vin": [
                    {
                        "scriptSig": {
                            "asm": "304402205b9ffe2ae901c1c62f21409d68bf4f18f94ce4c482569ed5f6c21aa15257a3a402203f85f0b04d8982bb09e8852a7f88169dbd9fb404144c5048846b796a96edf24f[ALL] 02cc5eaa7bd1c37ebf8483c014d38a1608d06cf6be6d61bae64b697725bae7696b",
                            "hex": "47304402205b9ffe2ae901c1c62f21409d68bf4f18f94ce4c482569ed5f6c21aa15257a3a402203f85f0b04d8982bb09e8852a7f88169dbd9fb404144c5048846b796a96edf24f012102cc5eaa7bd1c37ebf8483c014d38a1608d06cf6be6d61bae64b697725bae7696b"
                        },
                        "sequence": 4294967295,
                        "txid": "e4d3c05303f0eb8475ca501361c24abb31b3a5347d3a60abf1ad7cf8649d3fdd",
                        "vout": 1
                    },
                    {
                        "scriptSig": {
                            "asm": "3045022100a6c13e00f1fb53122424c35c581628830cf3b0cfab600397e7d3b6dd6d8aa89a022071add87aaa08239f30d58f2991525c66888e1f3fb8d52eec3c72c1871cced50f[ALL] 02cc5eaa7bd1c37ebf8483c014d38a1608d06cf6be6d61bae64b697725bae7696b",
                            "hex": "483045022100a6c13e00f1fb53122424c35c581628830cf3b0cfab600397e7d3b6dd6d8aa89a022071add87aaa08239f30d58f2991525c66888e1f3fb8d52eec3c72c1871cced50f012102cc5eaa7bd1c37ebf8483c014d38a1608d06cf6be6d61bae64b697725bae7696b"
                        },
                        "sequence": 4294967295,
                        "txid": "7914c6f91f164a739a9fcbaf6aab222aaf3662789d790028c1db950d69e500e9",
                        "vout": 0
                    }
                ],
                "vout": [
                    {
                        "n": 0,
                        "scriptPubKey": {
                            "addresses": [
                                "FJ6KDvWCeaiNdger53eWCwiLSZgjEPMHxf"
                            ],
                            "asm": "OP_DUP OP_HASH160 868190f1c3c9839fc34f994a44898739624fcfbc OP_EQUALVERIFY OP_CHECKSIG",
                            "hex": "76a914868190f1c3c9839fc34f994a44898739624fcfbc88ac",
                            "reqSigs": 1,
                            "type": "pubkeyhash"
                        },
                        "value": 0.005
                    },
                    {
                        "n": 1,
                        "scriptPubKey": {
                            "addresses": [
                                "FNmnKBw4PuXMdPoCv6v8DvnEKS3bM5W6eX"
                            ],
                            "asm": "OP_DUP OP_HASH160 b9d8e7f578161fb3fa16a061abe412926cbfc854 OP_EQUALVERIFY OP_CHECKSIG",
                            "hex": "76a914b9d8e7f578161fb3fa16a061abe412926cbfc85488ac",
                            "reqSigs": 1,
                            "type": "pubkeyhash"
                        },
                        "value": 0.099
                    }
                ],
                "vsize": 415
            }
        }
    ],
    "result": "ok"
}
```
