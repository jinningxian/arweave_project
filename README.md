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

### Request
`GET /`
return you to log in based on your token json key

`GET /wallet`
return you with last transaction info(id, status) and wallet balance

`GET /uploader`
allow server to read your token json key to redirect you to the wallet

`GET /lastTransaction`
return you with last transaction id and status 

`POST /upload_doc`
allow user to upload new documentation (developing, as the last transaction status is always pending might due to ineffective AR amount)
## Contributing

