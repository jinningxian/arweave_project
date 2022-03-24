# arweave_project

arweave_project is a Python project is built on arweave-python-client and Flask 

## Before you run run.py 

Use the package manager [pip]

```bash
pip install arweave-python-client==1.0.18
pip install -U Flask
```

## Usage
```bash
python run.py
```

## Request
### for anonymous
`GET /`

redirect you to log in page (log in by key file), remove previous 
[for security concern]

`GET /uploader` or `POST /uploader` 

allow server to read your token json key to redirect you to the wallet; if success log in, you will go to wallet page; otherwise, you will return to log in page 

### for login user only

`GET /wallet`

return you with last transaction info(id, status) and wallet balance, wallet id

`GET /lastTransaction`

return you with last transaction id and status; if status is pending, which means we could not find the record in database (either transaction is still uploading or transaction doesn't upload)

`GET /upload`

redirect to upload new documentation/transaction page 


`POST /upload`

allow user to upload new documentation/transaction (developing, as the last transaction status is always pending might due to ineffective AR amount)

`GET /search`

redirect to search for existed documentation/transaction page

`POST /search`

## Things to Make IMPROVEMENT
1. wallet loading is slow `GET /uploader` or `POST /uploader` , due to verify the wallet key
2. get wallet balance and generate last transaction information is slow `GET /wallet` [if record is not found, the time of searching is longer]
3. always need to keep track the transaction `POST /upload`, it might take longer time to upload your transaction; same for `POST /search`
if documentation/record existed, it will return message with the link (with transaction record); otherwise, it will show the user with "We could not find your data" with return message


