from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QDateTime
from PyQt5.QtWidgets import QMessageBox,QMainWindow, QTableWidgetItem
from companies import Ui_Companies
from login import Ui_Login
from signup import Ui_Signup
import os,sys,json,glob
from client.contractnote import ContractNote
from client.bcosclient import BcosClient
from client.datatype_parser import DatatypeParser
from client.common.compiler import Compiler
from client.bcoserror import BcosException, BcosError
from client_config import client_config
from eth_utils import to_checksum_address
from eth_utils.hexadecimal import encode_hex
from eth_account.account import Account
from client.datatype_parser import DatatypeParser
from client.common.compiler import Compiler
from client.bcoserror import BcosException, BcosError
from client_config import client_config
    
if __name__ == "__main__":
    # 实例化client
    client = BcosClient()

    # 加载abi定义
    if os.path.isfile(client_config.solc_path) or os.path.isfile(client_config.solcjs_path):
        Compiler.compile_file("MySol.sol")
    abi_file = "MySol.abi"
    data_parser = DatatypeParser()
    data_parser.load_abi_file(abi_file)
    contract_abi = data_parser.contract_abi

    # 部署合约
    print("\n>>Deploy:---------------------------------------------------------------------")
    with open("MySol.bin", 'r') as load_f:
        contract_bin = load_f.read()
        load_f.close()
    result = client.deploy(contract_bin)
    print("deploy",result)
    print("new address : ",result["contractAddress"])
    contract_name =  os.path.splitext(os.path.basename(abi_file))[0]
    memo = "tx:"+result["transactionHash"]
    
    #将合约地址填入
    abi_file = "MySol.abi"
    data_parser = DatatypeParser()
    data_parser.load_abi_file(abi_file)
    contract_abi = data_parser.contract_abi
    client = BcosClient()
    to_address = result["contractAddress"]

    #链接前端
    app = QtWidgets.QApplication(sys.argv)
    login_window = Login()
    signup_window = Signup()
    company_window = Companies()
    login_window.show()
    #signup_window.show()
    app.exec_()
    client.finish()

#公司功能窗口
class Companies(QMainWindow, Ui_Companies):
    def __init__(self, parent=None):
        super(Companies, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("Company")
        self.headers = ['债主','债务人','数额','债务状况','ddl']
        self.table_info_bor.setColumnCount(5) 
        self.table_info_bor.setHorizontalHeaderLabels(self.headers)

        self.table_info_lent.setColumnCount(5) 
        self.table_info_lent.setHorizontalHeaderLabels(self.headers)

        self.table_trans_bor.setColumnCount(5)
        self.table_trans_bor.setHorizontalHeaderLabels(self.headers)

        self.table_trans_lent.setColumnCount(5)
        self.table_trans_lent.setHorizontalHeaderLabels(self.headers)

        self.table_repay.setColumnCount(5)   
        self.table_repay.setHorizontalHeaderLabels(self.headers)
        self.btn_quit.clicked.connect(self.on_quit)
        #self.btn_reset_trans.clicked.connect(self.on_reset_transfer)
        self.btn_submit_trans.clicked.connect(self.on_submit_transfer)
        #self.btn_reset_fin.clicked.connect(self.on_reset_finance)
        self.btn_submit_fin.clicked.connect(self.on_submit_finance)
        #self.btn_reset_pur.clicked.connect(self.on_reset_purchase)
        self.btn_submit_pur.clicked.connect(self.on_submit_purchase)
        self.btn_ok_repay.clicked.connect(self.on_repay)

        self.btn_transfer.clicked.connect(self.transfer_view)
        self.btn_purchase.clicked.connect(self.purchase_view)
        self.btn_finance.clicked.connect(self.finance_view)
        self.btn_info.clicked.connect(self.info_view)
        self.btn_repay.clicked.connect(self.repay_view)

        self.table_info_bor.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.table_info_lent.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.table_trans_bor.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.table_trans_lent.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
    
    def set_basic_info(self, name):
        global client, contract_abi, to_address
   
        self.table_info_bor.setRowCount(0)
        self.table_info_lent.setRowCount(0)
        self.table_trans_bor.setRowCount(0)
        self.table_trans_lent.setRowCount(0)
        self.table_repay.setRowCount(0)
        self.set_table_info_bor_content(name)
        self.set_table_info_lent_content(name)
        self.set_table_trans_bor_content(name) 
        self.set_table_trans_lent_content(name)
        self.set_table_repay_content(name)
        self.company_name = name
        self.total_borrowed = 0
        self.total_lent = 0
        for i in range(self.table_info_bor.rowCount()):
            self.total_borrowed += int(self.table_info_bor.item(i,2).text())
        for i in range(self.table_info_lent.rowCount()):
            self.total_lent += int(self.table_info_lent.item(i,2).text())
        self.line_basic_borr.setText(str(self.total_borrowed))
        self.line_basic_lent.setText(str(self.total_lent))
        self.transfer_date.setDateTime(QDateTime.currentDateTime())
        self.finance_date.setDateTime(QDateTime.currentDateTime())
        self.purchase_date.setDateTime(QDateTime.currentDateTime())

    def set_table_trans_bor_content(self,name):
        # 调用合约函数 select_transaction
        result = client.call(to_address, contract_abi, "select_transaction", [name, 1])
        global client, contract_abi, to_address
        info_tuple = client.call(to_address, contract_abi, "select", [name, 1])
        print("receipt:",info_tuple)

        info_rows = len(info_tuple[0])
        for i in range(info_rows):
            row = self.table_trans_bor.rowCount()
            self.table_trans_bor.setRowCount(row + 1)
            self.table_trans_bor.setItem(row,0,QTableWidgetItem(info_tuple[1][i]))
            self.table_trans_bor.setItem(row,1,QTableWidgetItem(info_tuple[0][i]))
            self.table_trans_bor.setItem(row,2,QTableWidgetItem(str(info_tuple[2][i])))
            self.table_trans_bor.setItem(row,3,QTableWidgetItem(info_tuple[3][i]))
            self.table_trans_bor.setItem(row,4,QTableWidgetItem(info_tuple[4][i]))

    def set_table_info_bor_content(self,name):
        # 调用合约函数 select_transaction
        result = client.call(to_address, contract_abi, "select_transaction", [name, 1])
        global client, contract_abi, to_address
        info_tuple = client.call(to_address, contract_abi, "select", [name, 1])
        print("receipt:",info_tuple)

        info_rows = len(info_tuple[0])
        for i in range(info_rows):
            row = self.table_info_bor.rowCount()
            self.table_info_bor.setRowCount(row + 1)
            self.table_info_bor.setItem(row,0,QTableWidgetItem(info_tuple[1][i]))
            self.table_info_bor.setItem(row,1,QTableWidgetItem(info_tuple[0][i]))
            self.table_info_bor.setItem(row,2,QTableWidgetItem(str(info_tuple[2][i])))
            self.table_info_bor.setItem(row,3,QTableWidgetItem(info_tuple[3][i]))
            self.table_info_bor.setItem(row,4,QTableWidgetItem(info_tuple[4][i]))
    
    def set_table_trans_lent_content(self,name):
        global client, contract_abi, to_address
        info_tuple = client.call(to_address, contract_abi, "select", [name, 0])
        print("receipt:",info_tuple)
        # 调用合约函数 select_transaction
        result = client.call(to_address, contract_abi, "select_transaction", [name, 1])
        info_rows = len(info_tuple[0])
        for i in range(info_rows):
            row = self.table_trans_lent.rowCount()
            self.table_trans_lent.setRowCount(row + 1)
            self.table_trans_lent.setItem(row,0,QTableWidgetItem(info_tuple[1][i]))
            self.table_trans_lent.setItem(row,1,QTableWidgetItem(info_tuple[0][i]))
            self.table_trans_lent.setItem(row,2,QTableWidgetItem(str(info_tuple[2][i])))
            self.table_trans_lent.setItem(row,3,QTableWidgetItem(info_tuple[3][i]))
            self.table_trans_lent.setItem(row,4,QTableWidgetItem(info_tuple[4][i]))
    
    def set_table_info_lent_content(self,name):
        global client, contract_abi, to_address
        info_tuple = client.call(to_address, contract_abi, "select", [name, 0])
        print("receipt:",info_tuple)
    
        info_rows = len(info_tuple[0])
        for i in range(info_rows):
            row = self.table_info_lent.rowCount()
            self.table_info_lent.setRowCount(row + 1)
            self.table_info_lent.setItem(row,0,QTableWidgetItem(info_tuple[1][i]))
            self.table_info_lent.setItem(row,1,QTableWidgetItem(info_tuple[0][i]))
            self.table_info_lent.setItem(row,2,QTableWidgetItem(str(info_tuple[2][i])))
            self.table_info_lent.setItem(row,3,QTableWidgetItem(info_tuple[3][i]))
            self.table_info_lent.setItem(row,4,QTableWidgetItem(info_tuple[4][i]))

    def set_table_repay_content(self,name):
        global client, contract_abi, to_address
        info_tuple = client.call(to_address, contract_abi, "select", [name, 1])
        print("receipt:",info_tuple)
 
        info_rows = len(info_tuple[0])
        for i in range(info_rows):
            row = self.table_repay.rowCount()
            self.table_repay.setRowCount(row + 1)
            self.table_repay.setItem(row,0,QTableWidgetItem(info_tuple[0][i]))
            self.table_repay.setItem(row,1,QTableWidgetItem(info_tuple[1][i]))
            self.table_repay.setItem(row,2,QTableWidgetItem(str(info_tuple[2][i])))
            self.table_repay.setItem(row,3,QTableWidgetItem(info_tuple[3][i]))
            self.table_repay.setItem(row,4,QTableWidgetItem(info_tuple[4][i]))  
       
    def info_view(self):
        self.stackedWidget.setCurrentIndex(0)
        self.set_basic_info(self.company_name)
    def transfer_view(self):
        self.stackedWidget.setCurrentIndex(1)
        self.set_basic_info(self.company_name)
    def purchase_view(self):
        self.stackedWidget.setCurrentIndex(2)
    def finance_view(self):
        self.stackedWidget.setCurrentIndex(3)     
    def repay_view(self):
        self.stackedWidget.setCurrentIndex(4)
        self.set_basic_info(self.company_name)

    def on_quit(self):
        self.close()

    def on_reset_transfer(self):
        self.line_trans_from.clear()
        self.line_trans_to.clear()
        self.line_trans_amt.clear()

    def on_submit_transfer(self):
        global client, contract_abi, to_address
        if self.table_trans_lent.selectionModel().hasSelection() and self.table_trans_bor.selectionModel().hasSelection():
            row_lent = self.table_trans_lent.currentRow()
            row_bor = self.table_trans_bor.currentRow()
            _from = self.table_trans_lent.item(row_lent, 1).text()
            _due = self.table_trans_lent.item(row_lent, 4).text()
            _from_prev_amt = int(self.table_trans_lent.item(row_lent, 2).text())
            _to_prev_amt = int(self.table_trans_bor.item(row_bor, 2).text())
            _to = self.table_trans_bor.item(row_bor, 0).text()
            self.transfer_date.setDateTime(QDateTime.fromString(_due, 'yyyy/MM/dd hh:mm:ss'))
            _amt = int(self.line_trans_amt.text())
            print(_from,_to,_due,_amt)
            args = [_from, self.company_name, _to, _from_prev_amt, _to_prev_amt, _amt,_due]
            if self.table_trans_bor.item(row_bor, 3).text() == "authorized" and self.table_trans_lent.item(row_lent, 3).text() == "authorized":
                info_tuple = client.sendRawTransactionGetReceipt(to_address, contract_abi, "transfer", args)
                print("receipt:",info_tuple['output'])
                res = hex_to_signed(info_tuple['output'])
                if res == -3:
                    QMessageBox.warning(self,'Error','公司不存在!', QMessageBox.Ok)
                elif res == -1:
                    QMessageBox.warning(self,'Error','转让债务的数额不能比所选债务更大.', QMessageBox.Ok)
                elif res == 1:
                    QMessageBox.information(self,'Prompt','还债成功！', QMessageBox.Ok)
            else:
                QMessageBox.warning(self,'Error','只有银行确认过的债务才能!', QMessageBox.Ok)
        else:
            QMessageBox.warning(self,'Prompt','请选择要转让的债务!', QMessageBox.Ok)
        

    def on_reset_finance(self):
        self.line_fin_amt.clear()

    def on_submit_finance(self):
        _amt = int(self.line_fin_amt.text())
        _due = self.finance_date.dateTime().toString("yyyy/MM/dd hh:mm:ss")
        if _amt > (self.total_lent - self.total_borrowed):
            QMessageBox.warning(self,'Error',"你不想要贷这么多款，你最多可以贷款{}.".format(str(self.total_lent - self.total_borrowed)), QMessageBox.Ok)
        else:
            global client, contract_abi, to_address
            args = [self.company_name,"bank", _amt,_due]
            info_tuple = client.sendRawTransactionGetReceipt(to_address, contract_abi, "finance", args)
            QMessageBox.information(self,'Prompt','贷款成功', QMessageBox.Ok)

    def on_reset_purchase(self):
        self.line_pur_amt.clear()
        self.line_pur_from.clear()

    def on_submit_purchase(self):
        _amt = self.line_pur_amt.text()
        _due = self.purchase_date.dateTime().toString("yyyy/MM/dd hh:mm:ss")
        _from = self.line_pur_from.text()      
        global client, contract_abi, to_address
        args = [self.company_name , _from, int(_amt),_due]
        info_tuple = client.sendRawTransactionGetReceipt(to_address, contract_abi, "purchase", args)
        print("receipt:",info_tuple['output'])
        res = hex_to_signed(info_tuple['output'])
        if res == -3:
            QMessageBox.warning(self,'Error','公司不存在!', QMessageBox.Ok)
        elif res == 1:
            QMessageBox.information(self,'Prompt','成功下订单', QMessageBox.Ok)

    def on_repay(self):
        global client, contract_abi, to_address
        if self.table_repay.selectionModel().hasSelection():
            row = self.table_repay.currentRow()
            args = [self.table_repay.item(row, 0).text(), self.table_repay.item(row, 1).text(), \
                 int(self.table_repay.item(row, 2).text()),self.table_repay.item(row, 4).text()]
            print(args)
            if self.table_repay.item(row, 3).text() == "authorized":
                info_tuple = client.sendRawTransactionGetReceipt(to_address, contract_abi, "repay", args)
                print("receipt:",info_tuple)
                QMessageBox.information(self,'Prompt','成功转让债务', QMessageBox.Ok)
                self.table_repay.setRowCount(0)
                self.set_table_repay_content(self.company_name)
            else:
                QMessageBox.warning(self,'Error','只有认证的债务才能转让!', QMessageBox.Ok)
        else:
            QMessageBox.warning(self,'Prompt','请选择一条记录。', QMessageBox.Ok)

def hex_to_signed(source):
    """Convert a string hex value to a signed hexidecimal value.

    This assumes that source is the proper length, and the sign bit
    is the first bit in the first byte of the correct length.

    hex_to_signed("F") should return -1.
    hex_to_signed("0F") should return 15.
    """
    if not isinstance(source, str):
        raise ValueError("string type required")
    if 0 == len(source):
        raise ValueError("string is empty")
    source = source[2:]
    sign_bit_mask = 1 << (len(source)*4-1)
    other_bits_mask = sign_bit_mask - 1
    value = int(source, 16)
    return -(value & sign_bit_mask) | (value & other_bits_mask)

#注册窗口
class Signup(QMainWindow, Ui_Signup):
    def __init__(self, parent=None):
        super(Signup, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("Sign Up")
        self.btn_register.clicked.connect(self.on_press_register)
        self.btn_quit.clicked.connect(self.close)
	
    def on_press_register(self):
        name, password = self.line_name.text(), self.line_pwd.text()
        max_account_len = 20
        if len(name) > max_account_len:
            QMessageBox.warning(self, 'Error', '名字需要少于20个字符!')
            sys.exit(1)
        print("starting : {} {} ".format(name, password))
        ac = Account.create(password)
        print("new address :\t", ac.address)
        print("new privkey :\t", encode_hex(ac.key))
        print("new pubkey :\t", ac.publickey)

        kf = Account.encrypt(ac.privateKey, password)
        keyfile = "{}/{}.keystore".format(client_config.account_keyfile_path, name)
        print("save to file : [{}]".format(keyfile))
        with open(keyfile, "w") as dump_f:
            json.dump(kf, dump_f)
            dump_f.close()
        print(
            "INFO >> Read [{}] again after new account,address & keys in file:".format(keyfile))
        with open(keyfile, "r") as dump_f:
            keytext = json.load(dump_f)
            privkey = Account.decrypt(keytext, password)
            ac2 = Account.from_key(privkey)
            print("address:\t", ac2.address)
            print("privkey:\t", encode_hex(ac2.key))
            print("pubkey :\t", ac2.publickey)
            print("\naccount store in file: [{}]".format(keyfile))
            dump_f.close()

        global client, contract_abi, to_address
        args = [name, ac.address, 'Company']
        print(name)        
        receipt = client.sendRawTransactionGetReceipt(to_address,contract_abi,"register",args)
        print("receipt:",receipt['output'])


        QMessageBox.information(self,'Prompt','Successfully registered!', QMessageBox.Ok)

#登录窗口
class Login(QMainWindow, Ui_Login):
    def __init__(self, parent=None):
        super(Login, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("Log In")
        self.btn_login.clicked.connect(self.validate)
        self.btn_signup.clicked.connect(self.on_press_signup)

    def validate(self):
        name = self.line_name.text()
        password = self.line_pwd.text()
        keyfile = "{}/{}.keystore".format(client_config.account_keyfile_path, name)
        if os.path.exists(keyfile) is False:
            QMessageBox.warning(self,
                    "error",
                    "Name {} doesn't exists. Please register first.".format(name),
                    QMessageBox.Yes)
        else:
            print("name : {}, keyfile:{} ,password {}  ".format(name, keyfile, password))
            try:
                with open(keyfile, "r") as dump_f:
                    keytext = json.load(dump_f)
                    privkey = Account.decrypt(keytext, password)
                    ac2 = Account.from_key(privkey)
                    print("address:\t", ac2.address)
                    print("privkey:\t", encode_hex(ac2.key))
                    print("pubkey :\t", ac2.publickey)
                    company_window.show()
                    company_window.set_basic_info(name)
            except Exception as e:
                QMessageBox.warning(self,
                        "error",
                        ("Failed to load account info for [{}],"" error info: {}!").format(name, e),QMessageBox.Yes)

    def on_press_signup(self):
        signup_window.show()
