from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import arweave
from arweave.arweave_lib import Wallet, Transaction
from arweave.transaction_uploader import get_uploader
import os
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000
ALLOWED_EXTENSIONS = {'txt', 'json'}
app.config['UPLOAD_FOLDER'] = "./../key/"
app.config['UPLOAD_DOC'] = "./../upload/"

wallet_file_path = "./key/key.json"
global wallet 
@app.route('/')
def upload_files():
    return render_template('login.html')
	
@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['file']
        #   global wallet_id
        #   wallet_id = f.filename
        #   print(wallet_id)
        try:
            global wallet 
            wallet = arweave.Wallet(wallet_file_path)
            file_name = secure_filename("key.json")
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], file_name))
            return render_template('logInProcess.html')
        except:
            return render_template("login.html")
        
        

@app.route("/wallet")
def load_wallet():
    global wallet
    data = {}
    data["balance"] = wallet.balance
    last_transaction_id = wallet.get_last_transaction_id()
    last_transaction = Transaction(wallet, id=last_transaction_id)
    status = last_transaction.get_status()
    data["last_id"] = last_transaction_id
    data["last_transaction_status"] = status
    data["address"] = wallet.address
    return render_template("main.html", data=data)




@app.route("/lastTransaction", methods=["GET"])
def load_last_transaction():
    global wallet 
    try:
        last_transaction_id = wallet.get_last_transaction_id()
        last_transaction = Transaction(wallet, id=last_transaction_id)
        status = last_transaction.get_status()
    except:
        status = "Error"
    data = {
        "id": last_transaction_id,
        "status": status
    }
    return jsonify(
        data
    ), 200


@app.route("/upload_doc", methods=["POST"])
def upload_doc():
    if request.method == 'POST':
        try:
            f = request.files['file']
            print(f.filename)
            file_name = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], file_name))
            wallet = arweave.Wallet(wallet_file_path)
            with open(os.path.join(app.config['UPLOAD_FOLDER'], file_name), "rb", buffering=0) as file_handler:
                tx = Transaction(wallet, file_handler=file_handler, file_path="./files_upload/values.json")
                tx.add_tag('Content-Type', 'application/json')
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
            # with open(os.path.join(app.config['UPLOAD_FOLDER'], file_name), 'r', encoding="latin-1") as mypdf:
            #     pdf_string_data = mypdf.read()
            #     transaction = Transaction(wallet, data=pdf_string_data)
            #     transaction.sign()
            #     transaction.send()
            return jsonify(
                    {
                        "status": "Transaction uploading",
                        "transaction_id": transaction.id
                    }
                ), 203
        except:
            return jsonify(
                    {
                        "status": "Server error"
                    }
                ), 503
    
    return jsonify(
        {
            "status": "Method not allow"
        }
    ), 403

@app.route("/test1", methods=["POST", "GET"])
def test():
    global wallet 
    # print(wallet.address)
    print(request.values)
    print(dict(request.values))
    return ""


if __name__ == '__main__':
   app.run(port=5000, debug = True)