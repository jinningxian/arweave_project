from asyncio.log import logger
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import arweave
from arweave.arweave_lib import Wallet, Transaction
from arweave.transaction_uploader import get_uploader
import os
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000
ALLOWED_EXTENSIONS = {'txt', 'json'}
app.config['KEY'] = "./key/"
app.config['UPLOAD_DOC'] = "./upload/"

wallet_file_path = "./key/key.json"
global wallet 
@app.route('/')
def upload_files():
    os.remove(os.path.join(app.config['KEY'], "key.json"))
    return render_template('login.html')
	
@app.route('/uploader', methods = ['GET', 'POST'])
def key_logIn():
    if request.method == 'POST':
        file = request.files['file']
        #   global wallet_id
        #   wallet_id = f.filename
        #   print(wallet_id)
        try:
            file_name = secure_filename("key.json")
            file.save(os.path.join(app.config['KEY'], file_name))
            global wallet 
            wallet = arweave.Wallet(wallet_file_path)
            return render_template('logInProcess.html')
        except Exception as e:
            print(e)
            return render_template("login.html")
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

#data uploading might take around 5-20 mins 
@app.route("/upload", methods=["POST"])
def upload_doc():
    if request.method == 'POST':
        try:
            f = request.files['file']
            print(f.filename)
            file_name = secure_filename(f.filename)
            
            f.save("./upload/"+ file_name)
            file_path_root = "./upload/"+ file_name
            print(file_path_root)

            global wallet
            with open(file_path_root, "rb", buffering=0) as file_handler:
                tx = Transaction(wallet, file_handler=file_handler, file_path=file_path_root)
                tx.add_tag('Content-Type', 'application/json')
                tx.sign()
                print("Sign")
                uploader = get_uploader(tx, file_handler)
                print("uploading")
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
            data = {
                        "status": "Transaction uploading",
                        "transaction_id": tx.id,
                        "URL": "https://viewblock.io/arweave/tx/"+tx.id
                    }
            os.remove(file_path_root)

        except Exception as e:
            data = {
                        "status": "Server error",
                        "detail": e
                    }
    else:
        data = {
            "status": "Method not allow"
            }
    return render_template("upload_doc.html", data=data)
@app.route("/upload")
def upload_doc_logging():
    global wallet
    data = {"Status": "Prepare your document to upload"}
    return render_template("upload_doc.html", data = data)


@app.route("/search", methods=["GET"])
def load_search():
    data = {}
    data["Status"] = "Enter your ID to search"
    return render_template("get_transaction.html",data=data)

@app.route("/search", methods=["POST"])
def do_search():
    data = {}
    global wallet
    id = dict(request.values)["id"]
    tx = Transaction(wallet, id=id)
    try:
        result = tx.get_status()
        info = "Your data has been upload, you can click the link: https://viewblock.io/arweave/tx/"+str(id)
        # data["info"] = str(tx.get_status())
        print(result)
        data["Status"] = info
        if(result== "PENDING"):
            data["Status"] = "Your data is still uploading, please wait for next 10 mins"
    except:
        # data["info"] =  None  
        data["Status"] = "We could not find your data "
    return render_template("get_transaction.html",data=data)
@app.route("/test1", methods=["POST", "GET"])
def test():
    global wallet 
    # print(wallet.address)
    print(request.values)
    print(dict(request.values))
    token = dict(request.values)["token"]
    transaction = Transaction(wallet, id=token)
    try:
        status = transaction.get_status()
        data = transaction.get_data()
    except:
        status = {}
        data = ""
    return jsonify({
        "status": status
    })


if __name__ == '__main__':
   app.run(port=5000, debug = True)