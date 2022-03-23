from asyncio.log import logger
import arweave
from arweave.arweave_lib import Wallet, Transaction
from arweave.transaction_uploader import get_uploader

wallet_file_path = "./token_used/arweave-key-GyltZDFsi09RVhGPoKKsIClHJ6-69yKdKz-mXFAS8fE.json"
wallet = arweave.Wallet(wallet_file_path)


# from arweave.arweave_lib import Wallet, Transaction
# from arweave.transaction_uploader import get_uploader

wallet = Wallet(wallet_file_path)

with open("./msg.txt", "rb", buffering=0) as file_handler:
    tx = Transaction(wallet, file_handler=file_handler, file_path="./msg.txt")
    tx.add_tag('Content-Type', 'application/text')
    tx.sign()

    uploader = get_uploader(tx, file_handler)

    while not uploader.is_complete:
        uploader.upload_chunk()

        logger.info("{}% complete, {}/{}".format(
            uploader.pct_complete, uploader.uploaded_chunks, uploader.total_chunks
        ))
        print("{}% complete, {}/{}".format(
            uploader.pct_complete, uploader.uploaded_chunks, uploader.total_chunks
        ))



# def getBalance(wallet_file_path):



# balance =  wallet.balance

# last_transaction = wallet.get_last_transaction_id()
# print(last_transaction, balance)
# wallet = Wallet(wallet_file_path)
# with open('nft.png', 'r', encoding="latin-1") as mypdf:
#     pdf_string_data = mypdf.read()
#     transaction = Transaction(wallet, data=pdf_string_data)
#     transaction.sign()
#     transaction.send()

#     print(transaction)

# tx = Transaction(wallet, id="x36ycSi3MMX9fWJwJ67mkNkyUeubyi0rMt9GDGAuUw30mfYNe0lnoA==")
# tx.get_transaction()