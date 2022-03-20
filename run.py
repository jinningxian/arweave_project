from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import arweave
from arweave.arweave_lib import Wallet, Transaction
from arweave.transaction_uploader import get_uploader
import os
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000
ALLOWED_EXTENSIONS = {'txt', 'json'}
app.config['UPLOAD_FOLDER'] = "./key/"
app.config['UPLOAD_DOC'] = "./upload/"

wallet_file_path = "./key/key.json"

@app.route('/')
def upload_files():
   return render_template('upload.html')
	
@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
   if request.method == 'POST':
      f = request.files['file']
      print(f.filename)
      file_name = secure_filename("key.json")
      f.save(os.path.join(app.config['UPLOAD_FOLDER'], file_name))
      return render_template('upload_scc.html')

@app.route("/wallet")
def load_wallet():
    data = {}
    wallet = arweave.Wallet(wallet_file_path)
    data["balance"] = wallet.balance
    last_transaction_id = wallet.get_last_transaction_id()
    last_transaction = Transaction(wallet, id=last_transaction_id)
    status = last_transaction.get_status()
    data["last_id"] = last_transaction_id
    data["last_transaction_status"] = status
    # print(wallet)
    return render_template("main.html", data=data)

@app.route("/lastTransaction", methods=["GET"])
def load_last_transaction():
    wallet = arweave.Wallet(wallet_file_path)
    print("1")
    try:
        last_transaction_id = wallet.get_last_transaction_id()
        print("2")
        last_transaction = Transaction(wallet, id=last_transaction_id)
        print("3")
        status = last_transaction.get_status()
        print("4")
    except:
        print("5")
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
            with open(os.path.join(app.config['UPLOAD_FOLDER'], file_name), 'r', encoding="latin-1") as mypdf:
                pdf_string_data = mypdf.read()
                transaction = Transaction(wallet, data=pdf_string_data)
                transaction.sign()
                transaction.send()
            return jsonify(
                    {
                        "status": "Transaction uploading",
                        "transaction_id": transaction.id
                    }
                ), 403
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



if __name__ == '__main__':
   app.run(debug = True)